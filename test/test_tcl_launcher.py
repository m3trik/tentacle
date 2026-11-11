#!/usr/bin/python
# coding=utf-8
"""Tests for the one launcher and the shared activation-key contract (``tentacle.tcl``).

``Tcl.launch`` defers through the host toolkit's adapter (``Tcl.ADAPTERS``) and ``Tcl.build``
makes ONE ``uitk.MarkingMenu(host=...)`` for every host; what is pinned here is that path (from
a stub toolkit, so no DCC is needed), key normalization, the chord table and host detection --
plus, by source, that nothing re-grows a per-host subclass or a per-host table.

**These must pass in a plain interpreter AND inside a live DCC**, since tentacle's canonical run is
``run_tests.py --in-maya``. That rules out the obvious-looking approach of faking the host via
``sys.modules``: under Maya, ``maya.cmds`` genuinely IS present and detection correctly answers
"maya" no matter what a test injects. Tests wanting a specific host therefore narrow ``Tcl.HOSTS``
or stub ``host()``, and module stand-ins are real ``types.ModuleType`` objects (see ``_fake_bpy``).
"""

import contextlib
import io
import os
import subprocess
import sys
import types
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest import mock

# Ensure the package root is importable
ROOT = Path(__file__).resolve().parent.parent
PKG = ROOT / "tentacle"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tentacle.tcl import Tcl  # noqa: E402


def _fake_bpy():
    """A stand-in ``bpy`` that survives being imported.

    A bare ``MagicMock`` is NOT usable here: inside Maya, PySide6's ``shibokensupport`` installs an
    import hook that reads ``__name__`` off every imported module, and MagicMock raises
    AttributeError for it — so the mock blew up at ``import bpy`` in the canonical in-Maya run
    while passing everywhere else. A real module object has the dunders any import hook expects.
    """
    module = types.ModuleType("bpy")
    module.app = mock.MagicMock()
    module.app.background = False  # a Blender with a UI, unless a test says otherwise
    return module


class TestActivationKeyContract(unittest.TestCase):
    """``qt_key_name`` — the normalization every fork shares."""

    def test_bare_key_gains_qt_prefix(self):
        self.assertEqual(Tcl.qt_key_name("Z"), "Key_Z")
        self.assertEqual(Tcl.qt_key_name("Space"), "Key_Space")

    def test_qt_named_key_passes_through(self):
        """Already-normalized names must not be double-prefixed."""
        self.assertEqual(Tcl.qt_key_name("Key_Z"), "Key_Z")
        self.assertEqual(Tcl.qt_key_name("Key_F11"), "Key_F11")

    def test_none_resolves_to_the_default_key(self):
        """None is the 'caller didn't choose' value — the single default applies."""
        self.assertEqual(Tcl.qt_key_name(None), f"Key_{Tcl.DEFAULT_KEY}")

    def test_default_key_is_bare(self):
        """DEFAULT_KEY feeds qt_key_name, so a Key_-prefixed default would double-prefix."""
        self.assertFalse(Tcl.DEFAULT_KEY.startswith("Key_"))


class TestChordBindings(unittest.TestCase):
    """``chord_bindings`` — the default chord→menu table."""

    def test_common_chords_present_and_keyed_to_the_activation_key(self):
        b = Tcl.chord_bindings("Z", "maya#startmenu")
        self.assertEqual(b["Key_Z"], "hud#startmenu")
        self.assertEqual(b["Key_Z|LeftButton"], "cameras#startmenu")
        self.assertEqual(b["Key_Z|MiddleButton"], "editors#startmenu")
        self.assertEqual(b["Key_Z|RightButton"], "main#startmenu")
        self.assertEqual(b["Key_Z|LeftButton|RightButton"], "maya#startmenu")

    def test_chord_target_is_the_only_per_dcc_difference(self):
        """Maya and Blender forks must differ in exactly one binding."""
        maya = Tcl.chord_bindings("Z", "maya#startmenu")
        blender = Tcl.chord_bindings("Z", "blender#startmenu")
        differing = {k for k in maya if maya[k] != blender.get(k)}
        self.assertEqual(differing, {"Key_Z|LeftButton|RightButton"})

    def test_no_chord_target_leaves_the_both_button_gesture_unbound(self):
        """Max has no native-menu page; binding it to a dead target is worse than not binding."""
        b = Tcl.chord_bindings("Z")
        self.assertNotIn("Key_Z|LeftButton|RightButton", b)
        self.assertEqual(len(b), 4)

    def test_key_is_normalized(self):
        """A bare or Qt-named key must produce the same table."""
        self.assertEqual(
            Tcl.chord_bindings("Z", "maya#startmenu"),
            Tcl.chord_bindings("Key_Z", "maya#startmenu"),
        )

    def test_default_key_applies_when_unspecified(self):
        self.assertEqual(Tcl.chord_bindings(), Tcl.chord_bindings(Tcl.DEFAULT_KEY))


class TestSharedRoots(unittest.TestCase):
    """``register_shared`` — the composed ``slots/`` and the shared tools'
    ``ui/tools/`` + ``slots/tools/`` pair, sticky in any host, minus the tools the
    host does not serve (``slots.tools.HOSTS``)."""

    @staticmethod
    def _registered(context_tags=frozenset()):
        """The tool registration's kwargs on a switchboard of *context_tags*."""
        sb = mock.Mock(context_tags=set(context_tags))
        Tcl.register_shared(sb)
        return sb.register.call_args.kwargs

    def test_registers_the_composed_slots(self):
        sb = mock.Mock(context_tags=set())
        Tcl.register_shared(sb)
        first = sb.register.call_args_list[0].kwargs
        self.assertEqual(first, {"slot_location": first["slot_location"]})
        self.assertEqual(Path(first["slot_location"]), PKG / "slots")

    def test_registers_the_flat_tool_pair_under_the_panel_tag(self):
        from uitk import UiHandler

        kwargs = self._registered()
        ui, slots = PKG / "ui" / "tools", PKG / "slots" / "tools"
        self.assertTrue(ui.is_dir() and slots.is_dir())
        self.assertEqual(Path(kwargs["ui_location"]), ui)
        self.assertEqual(Path(kwargs["slot_location"]), slots)
        self.assertFalse(kwargs.get("recursive"), "flat: no folder per tool")
        self.assertEqual(kwargs["tags"], {UiHandler.PANEL_TAG})

    def test_a_host_registers_only_the_tools_it_serves(self):
        """A one-host tool's .ui and Slots module both stay out of the other host
        (``"<tool>.*"``), so nothing there can offer it."""
        from tentacle.slots.tools import HOSTS

        # Every tool serves both hosts today: a one-host row per host stands in.
        rows = {"calculator": ("maya",), "naming": ("blender",)}
        patched = mock.patch.dict(HOSTS, rows)
        patched.start()
        self.addCleanup(patched.stop)
        left_out_anywhere = 0
        for host in ("maya", "blender"):
            with self.subTest(host=host):
                left_out = sorted(t for t, hosts in HOSTS.items() if host not in hosts)
                left_out_anywhere += len(left_out)
                self.assertEqual(
                    self._registered({host})["exclude"],
                    [f"{t}.*" for t in left_out] or None,
                )
                self.assertEqual(Tcl.unserved_tools({host}), left_out)
        self.assertTrue(left_out_anywhere, "the check is vacuous: no host leaves a tool out")

    def test_a_contextless_switchboard_registers_every_tool(self):
        """uitk's rule: no context tags, no filtering (a bare test or dev switchboard)."""
        self.assertIsNone(self._registered()["exclude"])
        self.assertEqual(Tcl.unserved_tools(None), [])

    def test_each_one_host_tool_is_a_tool_and_names_real_hosts(self):
        """A stale row (a renamed tool, a misspelt host) would silently serve everywhere."""
        from tentacle.slots.tools import HOSTS

        tools = {p.stem for p in (PKG / "ui" / "tools").glob("*.ui")}
        for tool, hosts in HOSTS.items():
            with self.subTest(tool=tool):
                self.assertIn(tool, tools)
                self.assertTrue(set(hosts) and set(hosts) <= set(Tcl.HOSTS), hosts)
                self.assertLess(
                    set(hosts) & set(Tcl.ENGINES), set(Tcl.ENGINES), "serves both: no row"
                )

    def test_the_one_build_registers_it_once(self):
        """Read off the source: ``Tcl.build`` registers the shared roots, once, for every
        host -- no entry point of a host's own does it again."""
        import ast

        for module in sorted(PKG.glob("tcl*.py")):
            tree = ast.parse(module.read_text(encoding="utf-8"))
            calls = [
                ast.unparse(node)
                for node in ast.walk(tree)
                if isinstance(node, ast.Call)
                and ast.unparse(node.func).endswith(".register_shared")
            ]
            expected = ["cls.register_shared(menu.sb)"] if module.name == "tcl.py" else []
            self.assertEqual(calls, expected, module.name)


class TestRenamedPanels(unittest.TestCase):
    """``register_shared`` hands the tools' ``slots.tools.RENAMED_FROM`` to uitk's
    ``PanelRenames.carry`` (its own suite pins the carry): the DCC Bridge keeps
    what users saved under the Blender and Maya Bridges, the Workspaces panel what
    they saved under the Workspace Map and the Workspace Editor."""

    #: The former panels' widget names as the saved-names baseline froze them
    #: (their ``.ui`` files are gone). A root's name stores nothing: the window
    #: takes the panel's.
    FORMER_WIDGETS = {
        "blender_bridge": ["QtUi", "b000", "central_widget", "cmb000", "footer",
                           "grp_process", "header", "output_grp", "txt000"],
        "maya_bridge": ["QtUi", "b000", "central_widget", "cmb000", "footer",
                        "grp_process", "header", "output_grp", "txt000"],
        "workspace_map": ["b000", "b001", "b002", "footer", "groupBox", "groupBox_2",
                          "header", "label", "label_2", "tree000", "txt000", "txt001",
                          "workspace_map"],
        "workspace_editor": ["QtUi", "central_widget", "footer", "header", "tbl000",
                             "txt000"],
    }
    ROOTS = {"QtUi", "workspace_map"}

    @staticmethod
    def _ui_names(tool):
        root = ET.parse(PKG / "ui" / "tools" / f"{tool}.ui").getroot()
        return {w.get("name") for w in root.iter("widget")}

    def test_each_tool_is_a_tool_and_each_former_panel_is_gone(self):
        from tentacle.slots.tools import RENAMED_FROM

        tools = {p.stem for p in (PKG / "ui" / "tools").glob("*.ui")}
        slots = {p.stem for p in (PKG / "slots" / "tools").glob("*.py")}
        for tool, formers in RENAMED_FROM.items():
            with self.subTest(tool=tool):
                self.assertIn(tool, tools)
                self.assertIn(tool, slots)
                for former in formers:
                    self.assertNotIn(former, tools | slots)

    def test_the_former_panels_widget_names_live_on_in_their_tool(self):
        """Saved names keep their spelling: every widget a former panel stored
        values under is in its tool's ``.ui``, renamed only where declared."""
        from tentacle.slots.tools import RENAMED_FROM

        self.assertEqual(
            set(self.FORMER_WIDGETS),
            {former for formers in RENAMED_FROM.values() for former in formers},
        )
        for tool, formers in RENAMED_FROM.items():
            names = self._ui_names(tool)
            for former, renamed in formers.items():
                for widget in set(self.FORMER_WIDGETS[former]) - self.ROOTS:
                    with self.subTest(former=former, widget=widget):
                        self.assertIn(renamed.get(widget, widget), names)

    def test_each_former_panel_names_the_host_it_served(self):
        """``RENAMED_HOSTS`` keeps two formers' kept names in separate stores
        (``check_saved_names.py`` reads it): a row per former, real hosts."""
        from tentacle.slots.tools import RENAMED_FROM, RENAMED_HOSTS

        formers = {former for names in RENAMED_FROM.values() for former in names}
        self.assertEqual(set(RENAMED_HOSTS), formers)
        for former, hosts in RENAMED_HOSTS.items():
            with self.subTest(former=former):
                self.assertTrue(set(hosts) and set(hosts) <= set(Tcl.HOSTS), hosts)

    def test_registration_carries_the_former_panels_first(self):
        from uitk import PanelRenames

        from tentacle.slots.tools import RENAMED_FROM

        sb = mock.Mock(context_tags={"maya"})
        order = []
        sb.register.side_effect = lambda **kw: order.append("register")
        with mock.patch.object(
            PanelRenames, "carry", side_effect=lambda *a, **k: order.append("carry")
        ) as carry:
            Tcl.register_shared(sb)
        carry.assert_called_once_with(sb, RENAMED_FROM)
        self.assertEqual(order[0], "carry")


class TestHostDetection(unittest.TestCase):
    """``host`` — which DCC is running this process.

    These must hold in EVERY interpreter, including inside a real DCC: tentacle's canonical suite
    runs in a live Maya, where ``maya.cmds`` is genuinely present and detection correctly answers
    "maya" no matter what a test injects. So a test that wants a specific host narrows the host
    TABLE (the class's own config) rather than trying to fake the ambient environment out from
    under itself.
    """

    def test_host_table_maps_each_dcc_to_its_marker_module(self):
        """Environment-independent: the probe strings themselves."""
        self.assertEqual(Tcl.HOSTS, {"maya": "maya.cmds", "blender": "bpy"})

    def test_host_table_checks_maya_first(self):
        """Order is load-bearing — a mayapy with a pip-installed ``bpy`` must read as Maya."""
        self.assertEqual(list(Tcl.HOSTS), ["maya", "blender"])

    def test_every_host_has_a_toolkit(self):
        """The host name names its toolkit -- and through it, its adapter."""
        self.assertEqual(set(Tcl.HOSTS), set(Tcl.ENGINES))

    def test_detects_the_host_from_sys_modules(self):
        for name, probe in Tcl.HOSTS.items():
            with self.subTest(host=name):
                with (
                    mock.patch.object(Tcl, "HOSTS", {name: probe}),
                    mock.patch.dict(sys.modules, {probe: mock.MagicMock()}),
                ):
                    self.assertEqual(Tcl.host(), name)

    def test_reports_the_actual_host_of_this_interpreter(self):
        """Whatever is really running us — None in plain python, the DCC when hosted."""
        expected = next(
            (name for name, probe in Tcl.HOSTS.items() if probe in sys.modules), None
        )
        self.assertEqual(Tcl.host(), expected)


class _Adapter:
    """A host adapter that records the launch's deferral instead of scheduling it."""

    def __init__(self):
        self.deferred = []

    def defer(self, fn):
        self.deferred.append(fn)
        return None


class TestLaunchDispatch(unittest.TestCase):
    """``launch`` — defers the ONE build through the host's adapter, forwarding the caller's
    arguments."""

    def setUp(self):
        """Clear the once-per-process banner latch.

        ``Tcl.banner`` emits once per interpreter (see its docstring). Without this reset the
        FIRST banner test to run would latch it and every later one would assert against an
        empty buffer — or, worse, pass vacuously because ``banner()`` returns None both when
        it is suppressed and when it fails.
        """
        from tentacle.tcl import _TclInternal

        self.addCleanup(setattr, _TclInternal, "_BANNERED", False)
        _TclInternal._BANNERED = False

    def _launch_in(self, host, **kwargs):
        """Run launch() as if hosted by ``host``; return (the adapter, what ``build`` got).

        Detection is stubbed rather than simulated — inside a live Maya (the canonical suite's
        interpreter) the real ``host()`` always and correctly answers "maya", and what these
        tests are about is the dispatch, not the detection (covered by TestHostDetection).
        """
        adapter, built = _Adapter(), []
        with (
            mock.patch.object(Tcl, "host", classmethod(lambda cls: host)),
            mock.patch.object(
                Tcl, "host_adapter", classmethod(lambda cls, h: adapter)
            ),
            mock.patch.object(
                Tcl,
                "build",
                classmethod(lambda cls, *a, **kw: built.append((a, kw)) or "menu"),
            ),
            contextlib.redirect_stdout(io.StringIO()),
        ):
            self.assertIsNone(Tcl.launch(**kwargs))
            self.assertEqual(built, [], "the build must wait for the adapter's deferral")
            self.assertEqual(len(adapter.deferred), 1, "one deferral per launch")
            self.assertEqual(adapter.deferred[0](), "menu")
        self.assertEqual(len(built), 1, "one menu per launch")
        return adapter, built[0]

    def test_each_host_defers_one_build_through_its_adapter(self):
        for host in Tcl.HOSTS:
            with self.subTest(host=host):
                adapter, (args, kwargs) = self._launch_in(host)
                self.assertEqual(args, (host,))
                self.assertIs(kwargs["adapter"], adapter)

    def test_key_show_is_forwarded(self):
        self.assertEqual(self._launch_in("blender", key_show="F11")[1][1]["key_show"], "F11")

    def test_unset_key_show_reaches_build_as_none(self):
        """None lets ``build`` apply the default chain (``TENTACLE_KEY``, then the shipped
        default, a persisted key over both)."""
        self.assertIsNone(self._launch_in("maya")[1][1]["key_show"])

    def test_extra_kwargs_are_forwarded(self):
        kwargs = self._launch_in("maya", key_show="Z", log_level="DEBUG")[1][1]
        self.assertEqual(kwargs["log_level"], "DEBUG")

    def test_an_immediate_host_hands_the_menu_back(self):
        """A host whose ``defer`` runs now (a mayapy with no idle queue) returns the menu."""

        class Now(_Adapter):
            def defer(self, fn):
                return fn()

        with (
            mock.patch.object(Tcl, "host", classmethod(lambda cls: "maya")),
            mock.patch.object(Tcl, "host_adapter", classmethod(lambda cls, h: Now())),
            mock.patch.object(Tcl, "build", classmethod(lambda cls, *a, **kw: "menu")),
            contextlib.redirect_stdout(io.StringIO()),
        ):
            self.assertEqual(Tcl.launch(), "menu")

    def test_launch_issues_the_startup_banner(self):
        """The banner moved off ``import tentacle`` (imports must be side-effect free) onto
        the launch path — so a real launch must still print it."""
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            with mock.patch.object(Tcl, "host", classmethod(lambda cls: "maya")):
                with mock.patch.object(
                    Tcl, "host_adapter", classmethod(lambda cls, host: _Adapter())
                ):
                    Tcl.launch()
        self.assertIn("tentacle v", buf.getvalue())

    def test_banner_never_blocks_a_launch(self):
        """A banner failure must not stop the DCC from starting."""
        with mock.patch.object(Tcl, "BANNER", "{no_such_placeholder}"):
            self.assertIsNone(Tcl.banner())

    def test_banner_emits_once_per_process(self):
        """The retired ``import tentacle`` call ran once per interpreter; the latch reproduces
        that, which is what lets every entry point call ``banner()`` unconditionally."""
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            first = Tcl.banner()
            second = Tcl.banner()
        self.assertIsNotNone(first, "the first call must emit")
        self.assertIsNone(second, "the second call must be suppressed")
        self.assertEqual(buf.getvalue().count("You are using"), 1)

    def test_banner_force_overrides_the_latch(self):
        Tcl.banner()
        with contextlib.redirect_stdout(io.StringIO()) as buf:
            self.assertIsNotNone(Tcl.banner(force=True))
        self.assertIn("You are using", buf.getvalue())

    def test_blender_addon_entry_banners_without_going_through_launch(self):
        """Blender's add-on contract requires module-scope entries, so ``tcl_blender.launch``
        is reachable WITHOUT ``Tcl.launch`` — the path the in-repo console harness drives
        (test/blender/console_dock_check.py asserts the banner reaches the captured console).
        Pinned by source because constructing the Qt host needs a live Blender."""
        src = (PKG / "tcl_blender.py").read_text(encoding="utf-8")
        launch_body = src.split("    def launch(**kwargs):", 1)[1].split(
            "    @staticmethod", 1
        )[0]
        self.assertIn(
            "Tcl.banner()",
            launch_body,
            "BlenderHost.launch must banner: it is an entry point in its own right",
        )

    def test_no_host_raises_with_a_usable_message(self):
        with mock.patch.object(Tcl, "host", classmethod(lambda cls: None)):
            with self.assertRaises(RuntimeError) as ctx:
                Tcl.launch()
        self.assertIn("no supported DCC host", str(ctx.exception))
        self.assertNotIn("Max", str(ctx.exception))


class TestHeadlessLaunch(unittest.TestCase):
    """A host with no GUI to build for (``mayapy`` / ``maya -batch``, ``blender --background``)
    is a quiet no-op, decided BEFORE the toolkit is imported: ``userSetup.py`` runs in every
    headless Maya session -- every test chunk included -- and importing mayatk's root there
    costs a third of a second for nothing (batch has no GUI Qt; building a QWidget on Maya's
    non-GUI stub takes the interpreter down natively)."""

    def _probe_module(self, host, headless):
        if host == "maya":
            module = types.ModuleType("maya.cmds")
            module.about = lambda batch=False: headless if batch else None
            return "maya.cmds", module
        module = _fake_bpy()
        module.app.background = headless
        return "bpy", module

    def test_a_headless_launch_imports_no_toolkit(self):
        engines = set(Tcl.ENGINES.values())
        for host in Tcl.HOSTS:
            with self.subTest(host=host):
                name, module = self._probe_module(host, headless=True)
                resolved = []
                before = set(sys.modules)
                with (
                    mock.patch.object(Tcl, "host", classmethod(lambda cls, h=host: h)),
                    mock.patch.dict(sys.modules, {name: module}),
                    mock.patch.object(
                        Tcl,
                        "toolkit",
                        classmethod(lambda cls, h=None: resolved.append(h)),
                    ),
                    contextlib.redirect_stdout(io.StringIO()),
                ):
                    self.assertIsNone(Tcl.launch())
                self.assertEqual(resolved, [], "a headless launch resolved the toolkit")
                new = {m for m in set(sys.modules) - before if m.split(".")[0] in engines}
                self.assertEqual(new, set(), "a headless launch imported the toolkit")

    def test_each_host_says_whether_it_is_headless(self):
        for host in Tcl.HOSTS:
            for headless in (True, False):
                with self.subTest(host=host, headless=headless):
                    name, module = self._probe_module(host, headless)
                    with mock.patch.dict(sys.modules, {name: module}):
                        self.assertIs(Tcl.headless(host), headless)

    def test_an_unanswerable_probe_assumes_a_gui(self):
        """``cmds.about`` raises in a mayapy before ``standalone.initialize``: unknown is not
        headless (the launch goes on, as the Maya check always did)."""
        module = types.ModuleType("maya.cmds")

        def about(**_kw):
            raise RuntimeError("not initialized")

        module.about = about
        with mock.patch.dict(sys.modules, {"maya.cmds": module}):
            self.assertIs(Tcl.headless("maya"), False)
        self.assertIs(Tcl.headless("other"), False)


class TestMissingToolkitReachesTheUser(unittest.TestCase):
    """A launch in Blender whose toolkit (blendertk) is missing cannot be reported by the
    toolkit's adapter -- it is the missing part -- so the launcher shows it: a popup on a
    one-shot timer (a startup script has no window yet), else the console. Raised instead,
    Blender prints the install line to the SYSTEM console, hidden by default on Windows, and
    the user sees the launcher do nothing. Scoped to the ImportError: anything else keeps its
    traceback."""

    MISSING = (
        "tentacle: the blender engine (blendertk) is not installed. "
        'Install it with:  python -m pip install "tentacletk[blender]"'
    )

    def _launch_without_a_toolkit(self, bpy, error, host="blender"):
        def toolkit(cls, h=None):
            raise error

        with (
            mock.patch.object(Tcl, "host", classmethod(lambda cls: host)),
            mock.patch.dict(sys.modules, {"bpy": bpy}),
            mock.patch.object(Tcl, "toolkit", classmethod(toolkit)),
            contextlib.redirect_stdout(io.StringIO()),
        ):
            return Tcl.launch()

    def test_the_install_line_reaches_a_popup(self):
        bpy, drawn = _fake_bpy(), []

        def _popup(draw, **_kw):
            menu = mock.MagicMock()
            menu.layout.label.side_effect = lambda text: drawn.append(text)
            draw(menu, None)

        bpy.context = mock.MagicMock()
        bpy.context.window_manager.popup_menu.side_effect = _popup
        self.assertIsNone(self._launch_without_a_toolkit(bpy, ImportError(self.MISSING)))
        callback = bpy.app.timers.register.call_args.args[0]
        self.assertIs(bpy.app.timers.register.call_args.kwargs.get("persistent"), True)
        bpy.context.window_manager.popup_menu.assert_not_called()  # waits for a window
        self.assertIsNone(callback())  # one shot
        self.assertEqual(" ".join(drawn), self.MISSING)
        self.assertIn('Install it with:  python -m pip install "tentacletk[blender]"', drawn)

    def test_a_popup_that_cannot_render_falls_back_to_the_console(self):
        bpy = _fake_bpy()
        bpy.context = mock.MagicMock()
        bpy.context.window_manager.popup_menu.side_effect = RuntimeError("no window")
        self._launch_without_a_toolkit(bpy, ImportError(self.MISSING))
        callback = bpy.app.timers.register.call_args.args[0]
        with contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertIsNone(callback())
        self.assertIn("tentacletk[blender]", out.getvalue())

    def test_a_real_bug_keeps_its_traceback(self):
        with self.assertRaises(ValueError):
            self._launch_without_a_toolkit(_fake_bpy(), ValueError("a real bug"))

    def test_maya_raises_into_its_script_editor(self):
        """Maya shows a startup script's traceback where the user looks: no popup needed."""
        with self.assertRaises(ImportError):
            self._launch_without_a_toolkit(_fake_bpy(), ImportError("x"), host="maya")


class _StubToolkit(types.ModuleType):
    """A host toolkit stand-in: its adapter (``Tcl.ADAPTERS``), ``ShotStore`` and ``Macros``,
    each recording what the build asked of it."""

    def __init__(self, host):
        super().__init__(f"stub_{host}tk")
        from uitk import PureMarkingMenuHost

        self.calls = calls = []

        class Adapter(PureMarkingMenuHost):
            def start(self, app=None):
                calls.append("start")
                toolkit.app = app

            def attach(self, menu):
                calls.append(("attach", menu))

            def live_menu(self):
                return toolkit.live

        toolkit = self
        self.live = None

        setattr(self, Tcl.ADAPTERS[host], Adapter)
        self.ShotStore = types.SimpleNamespace(
            running_host=lambda: calls.append("shot store host")
        )
        self.Macros = types.SimpleNamespace(
            apply_saved_macros=lambda: calls.append("macros")
        )


class TestBuildMakesOneMenu(unittest.TestCase):
    """``Tcl.launch`` builds ONE ``uitk.MarkingMenu(host=...)`` per host, from a stub toolkit.

    The real menu, Switchboard and shared roots, offscreen; only the toolkit is a stand-in, so
    no DCC is needed. Everything per host comes from the host name: the toolkit, its adapter
    (``Tcl.ADAPTERS``), the native-menu pages (``ui/<host>_menus``), the both-button
    chord's ``<host>#startmenu`` and the ``{host}`` context tag.
    """

    def setUp(self):
        try:
            from qtpy import QtWidgets
            from uitk import MarkingMenu, PureMarkingMenuHost  # noqa: F401
        except Exception as error:  # noqa: BLE001 - no Qt binding here
            self.skipTest(f"needs Qt + uitk: {error}")
        self.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(["t"])
        self.menus = []
        self.addCleanup(self._retire)

    def _retire(self):
        for menu in self.menus:
            try:
                menu.retire()
                menu.deleteLater()
            except RuntimeError:
                pass

    def _launch(self, host, key_show="F9"):
        toolkit = _StubToolkit(host)
        from uitk import MarkingMenu

        built = []
        real_init = MarkingMenu.__init__

        def counting_init(menu, *args, **kwargs):
            built.append(menu)
            toolkit.calls.append("menu")
            real_init(menu, *args, **kwargs)

        with (
            mock.patch.object(Tcl, "host", classmethod(lambda cls: host)),
            mock.patch.object(
                Tcl, "_import_entry", classmethod(lambda cls, h, module, attr=None: toolkit)
            ),
            mock.patch.object(MarkingMenu, "__init__", counting_init),
            contextlib.redirect_stdout(io.StringIO()),
        ):
            menu = Tcl.launch(key_show=key_show)  # the pure defer builds at once
        self.menus.extend(built)
        return toolkit, built, menu

    def test_each_host_gets_one_menu_hosted_by_its_adapter(self):
        for host in Tcl.HOSTS:
            with self.subTest(host=host):
                toolkit, built, menu = self._launch(host)
                self.assertEqual(len(built), 1, "ONE MarkingMenu per launch")
                self.assertIs(menu, built[0])
                adapter_type = getattr(toolkit, Tcl.ADAPTERS[host])
                self.assertIsInstance(menu.host, adapter_type)
                self.assertEqual(type(menu).__name__, "MarkingMenu", "no per-host subclass")

    def test_the_host_names_everything_per_host(self):
        for host in Tcl.HOSTS:
            with self.subTest(host=host):
                toolkit, _built, menu = self._launch(host)
                self.assertEqual(menu.sb.context_tags, {host})
                key = Tcl.resolve_key("F9", {host})  # a key a user persisted outranks F9
                self.assertEqual(
                    menu.default_bindings.get(f"{key}|LeftButton|RightButton"),
                    f"{host}#startmenu",
                )
                self.assertTrue(
                    menu.sb.is_registered_ui(f"{host}#startmenu"),
                    f"ui/{host}_menus is not registered",
                )
                self.assertTrue(menu.sb.is_registered_ui("hud#startmenu"))

    def test_the_shared_wiring_is_done_once(self):
        toolkit, _built, menu = self._launch("maya")
        self.assertIs(menu.sb.tk, toolkit)
        self.assertEqual(toolkit.calls.count("shot store host"), 1)
        self.assertEqual(toolkit.calls.count("macros"), 1)

    def test_a_host_that_drives_a_live_menu_gets_it_back(self):
        """Blender's keymap bridge drives one menu per process: a second launch hands it
        back instead of stacking a second menu (and a second keymap wiring) over it."""
        toolkit = _StubToolkit("blender")
        from uitk import MarkingMenu

        built = []
        real_init = MarkingMenu.__init__

        def counting_init(menu, *args, **kwargs):
            built.append(menu)
            real_init(menu, *args, **kwargs)

        with (
            mock.patch.object(Tcl, "host", classmethod(lambda cls: "blender")),
            mock.patch.object(
                Tcl, "_import_entry", classmethod(lambda cls, h, module, attr=None: toolkit)
            ),
            mock.patch.object(MarkingMenu, "__init__", counting_init),
            contextlib.redirect_stdout(io.StringIO()),
        ):
            first = Tcl.launch()
            self.menus.extend(built)
            toolkit.live = first
            second = Tcl.launch()
        self.assertIs(second, first)
        self.assertEqual(len(built), 1, "the live menu was built over")

    def test_the_env_names_the_default_key(self):
        """``TENTACLE_KEY`` (``Tcl.KEY_ENV``) is the default a launch names none for, on
        every host; an explicit ``key_show`` names it over the env."""
        for host in Tcl.HOSTS:
            with self.subTest(host=host), mock.patch.dict(
                os.environ, {Tcl.KEY_ENV: "F7"}
            ):
                _toolkit, _built, menu = self._launch(host, key_show=None)
                key = Tcl.resolve_key("F7", {host})
                self.assertIn(key, menu.default_bindings)
                _toolkit, _built, menu = self._launch(host, key_show="F8")
                self.assertIn(Tcl.resolve_key("F8", {host}), menu.default_bindings)

    def test_a_relative_slot_source_is_relative_to_tentacle(self):
        """As the per-host subclasses resolved it (their module's folder), never uitk's."""
        captured = {}
        from uitk import MarkingMenu

        real_init = MarkingMenu.__init__

        def capturing_init(menu, *args, **kwargs):
            captured.update(kwargs)
            real_init(menu, *args, **kwargs)

        toolkit = _StubToolkit("maya")
        with (
            mock.patch.object(Tcl, "host", classmethod(lambda cls: "maya")),
            mock.patch.object(
                Tcl, "_import_entry", classmethod(lambda cls, h, module, attr=None: toolkit)
            ),
            mock.patch.object(MarkingMenu, "__init__", capturing_init),
            contextlib.redirect_stdout(io.StringIO()),
        ):
            menu = Tcl.build("maya", slot_source="slots")
        self.menus.append(menu)
        self.assertEqual(
            os.path.normcase(captured["slot_source"]), os.path.normcase(str(PKG / "slots"))
        )

    def test_the_launcher_names_the_application_it_stands_qt_up_for(self):
        """The host names what it makes for the app after it (Blender's env vars, its
        qt_deps folder, its messages): tentacle says it is tentacle."""
        toolkit, _built, _menu = self._launch("blender")
        self.assertEqual(toolkit.app, Tcl.APP_NAME)
        self.assertEqual(Tcl.APP_NAME, "tentacle")

    def test_qt_is_stood_up_before_the_menu(self):
        toolkit, _built, menu = self._launch("blender")
        self.assertLess(toolkit.calls.index("start"), toolkit.calls.index("menu"))
        self.assertIn(("attach", menu), toolkit.calls)


class TestQtPlatformErrorReachesTheUser(unittest.TestCase):
    """blendertk's ``QtPlatformUnavailable`` (Qt cannot open a window here) carries its fix, so,
    like the missing engine, the launch's timer shows it in a popup rather than the hidden
    system console. Driven through the REAL ``Tcl.launch``, ``btk.BlenderMarkingMenuHost`` and
    ``btk.QtRuntime``: only the probe's ``subprocess.run``, the platform and ``bpy`` are faked.
    The preflight itself is blendertk's ``test_qt_runtime``, the popup its
    ``test_marking_menu_host``."""

    ABORTED = subprocess.CompletedProcess(
        args=[],
        returncode=-6,
        stdout="",
        stderr=(
            'qt.qpa.plugin: Could not load the Qt platform plugin "xcb" in "" even though it '
            "was found.\nThis application failed to start because no Qt platform plugin "
            "could be initialized."
        ),
    )

    def setUp(self):
        try:
            import blendertk
            from qtpy import QtWidgets  # noqa: F401

            blendertk.BlenderMarkingMenuHost  # noqa: B018 - an older install has none
        except Exception as error:  # noqa: BLE001 - any import-time miss = not testable here
            self.skipTest(f"needs Qt + this blendertk: {error}")

    @contextlib.contextmanager
    def _linux_without_a_qapp(self, probe):
        """Linux, no QApplication yet, uitk's platform policy stubbed, the probe child faked:
        *probe* is its ``CompletedProcess``, or the exception launching it raises."""
        import uitk
        from qtpy import QtWidgets

        run = (
            mock.patch("subprocess.run", side_effect=probe)
            if isinstance(probe, BaseException)
            else mock.patch("subprocess.run", return_value=probe)
        )
        with (
            mock.patch.object(sys, "platform", "linux"),
            mock.patch.object(
                QtWidgets.QApplication, "instance", new=staticmethod(lambda: None)
            ),
            mock.patch.object(
                uitk.Bootstrap,
                "configure_platform",
                new=staticmethod(lambda *a, **k: False),
            ),
            run,
        ):
            yield

    def test_a_qt_platform_that_cannot_start_reaches_the_user(self):
        bpy, drawn = _fake_bpy(), []

        def _popup(draw, **_kw):
            """Run the draw callback the way Blender does, capturing its labels."""
            menu = mock.MagicMock()
            menu.layout.label.side_effect = lambda text: drawn.append(text)
            draw(menu, None)

        bpy.context = mock.MagicMock()
        bpy.context.window_manager.popup_menu.side_effect = _popup
        with (
            self._linux_without_a_qapp(self.ABORTED),
            mock.patch.dict(sys.modules, {"bpy": bpy}),
            mock.patch.object(Tcl, "host", classmethod(lambda cls: "blender")),
            contextlib.redirect_stdout(io.StringIO()),
        ):
            self.assertIsNone(Tcl.launch())
            callback = bpy.app.timers.register.call_args.args[0]
            self.assertIsNone(callback())  # must NOT propagate out of the timer

        self.assertTrue(drawn, "the Qt platform error never reached a popup")
        self.assertTrue(any("marking menu is off" in s for s in drawn), drawn)
        self.assertTrue(any("libxcb-cursor0" in s for s in drawn), drawn)
        # One line per label: Blender draws a label unwrapped, a newline included.
        self.assertEqual([s for s in drawn if "\n" in s], [])


class TestDefaultKeyUpgradePath(unittest.TestCase):
    """A shipped default-key change must actually reach a user who already has bindings persisted.

    Bindings live in QSettings and are forward-merged at construction
    (``MarkingMenu._reconcile_bindings``), and the activation key is the FIRST ``Key_*`` the
    resolver meets while walking that merged dict. So "does the new default win?" is decided by
    merge ordering — the difference between a default change taking effect and being a silent
    no-op for every existing install. Pure functions, so this runs without a DCC.
    """

    def test_new_default_wins_over_previously_persisted_bindings(self):
        from uitk import MarkingMenu, MenuResolver

        stored = Tcl.chord_bindings(
            "F12", "maya#startmenu"
        )  # an older default, persisted
        defaults = Tcl.chord_bindings(Tcl.DEFAULT_KEY, "maya#startmenu")

        merged = MarkingMenu._reconcile_bindings(defaults, stored)
        _normalized, activation = MenuResolver.parse_binding_keys(merged)

        self.assertEqual(activation, f"Key_{Tcl.DEFAULT_KEY}")

    def test_chords_resolve_against_the_new_key(self):
        """Not just the bare key — the whole chord set must be reachable post-upgrade."""
        from uitk import MarkingMenu

        merged = MarkingMenu._reconcile_bindings(
            Tcl.chord_bindings(Tcl.DEFAULT_KEY, "maya#startmenu"),
            Tcl.chord_bindings("F12", "maya#startmenu"),
        )
        key = f"Key_{Tcl.DEFAULT_KEY}"
        self.assertEqual(merged[f"{key}|LeftButton"], "cameras#startmenu")
        self.assertEqual(merged[f"{key}|LeftButton|RightButton"], "maya#startmenu")


class TestActivationKeyPrecedence(unittest.TestCase):
    """``user-persisted > named default > DEFAULT_KEY`` — whose activation key wins at launch.

    ``key_show`` in a startup script names that install's DEFAULT: it applies on first run
    and for every user who never rebound — which is also what lets a changed default reach
    exactly those installs. A key the user actively chose (persisted by
    ``MarkingMenu.set_activation_key``, the single rebind path, so presence IS provenance)
    outranks it: a startup script re-asserts its default at every launch, and letting that
    overwrite the persisted choice was the "shortcut editor keeps resetting my key" bug.
    """

    @contextlib.contextmanager
    def _stored(self, key):
        from uitk import MarkingMenu

        with mock.patch.object(
            MarkingMenu, "stored_activation_key", return_value=key
        ) as stub:
            yield stub

    def test_persisted_key_wins_over_the_named_default(self):
        """The startup script re-asserts its default every launch; the user's choice survives."""
        with self._stored("Key_F11"):
            self.assertEqual(Tcl.resolve_key("Z", {"maya"}), "Key_F11")

    def test_named_default_applies_when_nothing_is_stored(self):
        with self._stored(None):
            self.assertEqual(Tcl.resolve_key("F12", {"maya"}), "Key_F12")

    def test_persisted_key_is_used_when_none_is_named(self):
        with self._stored("Key_F11"):
            self.assertEqual(Tcl.resolve_key(None, {"maya"}), "Key_F11")

    def test_default_applies_when_nothing_is_named_or_stored(self):
        with self._stored(None):
            self.assertEqual(Tcl.resolve_key(None, {"maya"}), f"Key_{Tcl.DEFAULT_KEY}")

    def test_named_default_is_normalized(self):
        with self._stored(None):
            self.assertEqual(Tcl.resolve_key("Key_F12", {"maya"}), "Key_F12")

    def test_the_store_is_read_for_the_hosts_own_context(self):
        """A wrong tag set reads another DCC's key — the shared-QSettings hazard."""
        with self._stored("Key_F11") as stub:
            Tcl.resolve_key(None, {"blender"})
            stub.assert_called_once_with({"blender"})

    def test_an_unreadable_store_falls_back_to_the_named_default(self):
        """Startup must never fail on a bad store — the menu has to come up with *some* key."""
        from uitk import MarkingMenu

        with mock.patch.object(
            MarkingMenu, "stored_activation_key", side_effect=RuntimeError("no backend")
        ):
            self.assertEqual(Tcl.resolve_key("F12", {"maya"}), "Key_F12")


class TestOneLauncher(unittest.TestCase):
    """One launcher builds every host's menu: no ``MarkingMenu`` subclass per host, no per-host
    table beyond ``Tcl.HOSTS`` detection, the chord table built in one place.

    Source-level because the forks this replaced were only constructible in their DCC. A literal
    ``hud#startmenu`` or a host's ``<host>#startmenu`` / ``<host>_menus`` outside the convention
    is the signature of a re-grown fork.
    """

    def _launchers(self):
        return sorted(PKG.glob("tcl*.py"))

    def test_the_per_host_forks_are_gone(self):
        for name in ("tcl_maya.py", "tcl_max.py"):
            with self.subTest(module=name):
                self.assertFalse((PKG / name).exists(), f"{name} is back")

    def test_no_module_subclasses_the_marking_menu(self):
        import ast

        for path in sorted(PKG.rglob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            bases = [
                ast.unparse(base)
                for node in ast.walk(tree)
                if isinstance(node, ast.ClassDef)
                for base in node.bases
            ]
            with self.subTest(module=path.name):
                self.assertFalse(
                    [b for b in bases if b.endswith("MarkingMenu")],
                    "host behavior is the adapter's, never a MarkingMenu subclass",
                )

    @staticmethod
    def _code_strings(tree):
        """Every string constant in *tree*'s code -- docstrings, which may name a host
        to explain, left out."""
        import ast

        docstrings = {
            id(node.body[0].value)
            for node in ast.walk(tree)
            if isinstance(
                node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
            )
            and node.body
            and isinstance(node.body[0], ast.Expr)
            and isinstance(node.body[0].value, ast.Constant)
        }
        return [
            node.value
            for node in ast.walk(tree)
            if isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and id(node) not in docstrings
        ]

    def test_nothing_spells_a_host_out(self):
        """The native-menu pages, the both-button target, the context tag and the UI
        handler come from the host name or its adapter; a literal one in code is a
        per-host table growing back."""
        import ast

        for path in self._launchers():
            tree = ast.parse(path.read_text(encoding="utf-8"))
            strings = self._code_strings(tree)
            for literal in (
                "maya#startmenu",
                "blender#startmenu",
                "maya_menus",
                "blender_menus",
                "MayaUiHandler",
                "BlenderUiHandler",
            ):
                with self.subTest(module=path.name, literal=literal):
                    self.assertFalse([s for s in strings if literal in s])
            host_sets = [
                ast.unparse(node)
                for node in ast.walk(tree)
                if isinstance(node, ast.Set)
                and any(
                    isinstance(e, ast.Constant) and e.value in Tcl.HOSTS
                    for e in node.elts
                )
            ]
            with self.subTest(module=path.name, literal="a host's context tag"):
                self.assertEqual(host_sets, [])

    def test_the_chord_table_is_built_in_one_place(self):
        for path in self._launchers():
            with self.subTest(module=path.name):
                src = path.read_text(encoding="utf-8")
                count = src.count('"hud#startmenu"')
                self.assertEqual(count, 1 if path.name == "tcl.py" else 0)

    def test_default_key_is_defined_once(self):
        """A launcher carrying its own bare default re-opens the drift this replaced."""
        for path in self._launchers():
            with self.subTest(module=path.name):
                src = path.read_text(encoding="utf-8")
                self.assertNotIn(f'"key_show", "{Tcl.DEFAULT_KEY}"', src)

    def test_each_hosts_adapter_is_declared_and_its_toolkit_exports_it(self):
        """``Tcl.ADAPTERS`` names each host's adapter class, which its toolkit's root
        publishes (read off the sibling checkout's ``DEFAULT_INCLUDE``, never imported)."""
        import ast

        self.assertEqual(set(Tcl.ADAPTERS), set(Tcl.HOSTS))
        for host, name in Tcl.ADAPTERS.items():
            engine = Tcl.ENGINES[host]
            init = ROOT.parent / engine / engine / "__init__.py"
            if not init.is_file():
                continue  # no sibling checkout here (CI installs one engine)
            with self.subTest(host=host):
                tree = ast.parse(init.read_text(encoding="utf-8"))
                published = {
                    node.value
                    for node in ast.walk(tree)
                    if isinstance(node, ast.Constant) and isinstance(node.value, str)
                }
                self.assertIn(name, published)

    def test_the_launcher_holds_no_host_named_method(self):
        """Host behavior is the adapter's: no ``_reload_<host>`` / ``_report_<host>`` and no
        dispatch by a host-built method name. The one host-named method left is the
        fallback for a MISSING toolkit, whose adapter cannot report its own absence."""
        import ast

        tree = ast.parse((PKG / "tcl.py").read_text(encoding="utf-8"))
        methods = {
            node.name
            for node in ast.walk(tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
        host_named = {
            m for m in methods for host in Tcl.HOSTS if host in m.lower()
        }
        self.assertEqual(host_named, {"_report_blender_startup_error"})
        self.assertNotIn('f"_reload_{host}"', (PKG / "tcl.py").read_text(encoding="utf-8"))

    def test_the_blender_stub_reaches_no_private_console_state(self):
        src = (PKG / "tcl_blender.py").read_text(encoding="utf-8")
        self.assertNotIn("ScriptConsole._instance", src)

    def test_the_blender_stub_builds_through_the_launcher(self):
        src = (PKG / "tcl_blender.py").read_text(encoding="utf-8")
        self.assertIn('Tcl.build("blender"', src)


class TestStyleDefaults(unittest.TestCase):
    """Window blur is uitk's own per-theme default: on in light and dark, off in the
    opaque high-contrast theme. tentacle sets no base value over it.

    The entry classes used to set ``WINDOW_BLUR`` "on" in EVERY theme through
    ``StyleSheet.set_base_variable``: redundant once uitk shipped it on, and it turned
    blur on in high-contrast, whose surfaces are opaque (and a theme without the token
    would have raised out of the entry class, leaving no menu).
    """

    def test_no_tentacle_module_overrides_uitk_s_theme_defaults(self):
        for path in sorted(PKG.rglob("*.py")):
            with self.subTest(module=path.name):
                src = path.read_text(encoding="utf-8")
                self.assertNotIn("set_base_variable", src)
                self.assertNotIn("WINDOW_BLUR", src)


class TestEngineExtras(unittest.TestCase):
    """The DCC engine is an ``[extra]``, resolved from installed metadata.

    The contract: every key in ``[project.optional-dependencies]`` equals a ``Tcl.HOSTS``
    key, so ``host()`` doubles as the extra resolver and no second table exists to drift.

    These read the LIVE metadata, so they must not assume which engine this interpreter
    has — inside Maya ``mayatk`` is genuinely installed and in CI neither may be. What is
    asserted is the mapping (which extra declares which dist), never presence.
    """

    def test_base_requirements_exclude_both_engines(self):
        """The whole point: neither engine may be a base dependency, or both land in
        every install again (~19 MB of never-imported code in the other DCC)."""
        base = Tcl._requires()
        if not base:
            self.skipTest("no installed metadata (source checkout)")
        self.assertIn("pythontk", base)
        self.assertIn("uitk", base)
        self.assertNotIn("mayatk", base)
        self.assertNotIn("blendertk", base)

    def test_each_host_extra_declares_its_own_engine(self):
        if not Tcl._requires():
            self.skipTest("no installed metadata (source checkout)")
        self.assertEqual(Tcl.engine_dists("maya"), ("mayatk",))
        self.assertEqual(Tcl.engine_dists("blender"), ("blendertk",))

    def test_a_host_without_an_extra_is_a_no_op(self):
        """A host that ships no engine must read as "nothing to install", not as an
        error, so the launcher stays uniform across hosts."""
        self.assertEqual(Tcl.engine_dists("no-such-host"), ())

    def test_no_host_is_not_the_base_set(self):
        """``_requires(extra=None)`` means "the BASE set", and ``host()`` answers None
        outside any DCC — so a missing guard made ``engine_dists(None)`` claim this
        host's engine is ``pythontk``/``uitk``."""
        self.assertEqual(Tcl.engine_dists(None), ())
        self.assertEqual(Tcl.engine_dists(""), ())

    def test_declared_dists_names_this_hosts_engine_and_not_the_other(self):
        if not Tcl._requires():
            self.skipTest("no installed metadata (source checkout)")
        maya = Tcl.declared_dists("maya")
        blender = Tcl.declared_dists("blender")
        self.assertIn("mayatk", maya)
        self.assertNotIn("blendertk", maya)
        self.assertIn("blendertk", blender)
        self.assertNotIn("mayatk", blender)

    def test_declared_dists_includes_the_package_itself_last(self):
        if not Tcl._requires():
            self.skipTest("no installed metadata (source checkout)")
        self.assertEqual(Tcl.declared_dists("maya")[-1], Tcl.DIST)
        self.assertNotIn(Tcl.DIST, Tcl.declared_dists("maya", include_self=False))

    def test_unreadable_metadata_reports_empty_not_a_partial_list(self):
        """A source checkout has no metadata. Reporting ``(pythontk, uitk)`` there would
        be a LIE the updater acts on; empty means "unknown" and lets it fall back."""
        with mock.patch.object(
            Tcl, "_requires", classmethod(lambda cls, extra=None: ())
        ):
            self.assertEqual(Tcl.declared_dists("maya"), ())

    def test_install_hint_names_the_extra_and_quotes_it(self):
        """``[maya]`` is a glob character class in POSIX shells — an unquoted hint is a
        line that silently does nothing when pasted into bash."""
        hint = Tcl.engine_install_hint("maya")
        self.assertIn('"tentacletk[maya]"', hint)
        self.assertIn("-m pip install", hint)

    def test_a_hostless_hint_lists_only_hosts_that_declare_an_engine(self):
        """Asked outside any DCC. ``[None]`` would be nonsense, and offering a host with
        no engine sends the reader to a pip line resolving to nothing."""
        if not Tcl._requires():
            self.skipTest("no installed metadata (source checkout)")
        with mock.patch.object(Tcl, "host", classmethod(lambda cls: None)):
            hint = Tcl.engine_install_hint()
        self.assertNotIn("None", hint)
        self.assertIn("[maya]", hint)
        self.assertIn("[blender]", hint)

    def test_a_host_with_no_engine_gets_no_pip_line_for_it(self):
        """A host with no extra (``"tentacletk[other]"`` names one that does not exist —
        pip warns and no-ops) must fall through to the same "here are the hosts that DO
        ship one" answer as the hostless call."""
        if not Tcl._requires():
            self.skipTest("no installed metadata (source checkout)")
        hint = Tcl.engine_install_hint("other")
        self.assertNotIn("[other]", hint)
        self.assertIn("[maya]", hint)

    def test_a_source_checkout_keeps_the_named_hosts_pip_line(self):
        """With no metadata EVERY host reads as engine-less. Demoting a real Maya user
        onto the hostless branch there would cost the interpreter-specific line."""
        with mock.patch.object(
            Tcl, "_requires", classmethod(lambda cls, extra=None: ())
        ):
            hint = Tcl.engine_install_hint("maya")
        self.assertIn('"tentacletk[maya]"', hint)

    def test_requirement_parsing_cannot_raise(self):
        """``_import_entry`` consults ``engine_dists`` from INSIDE an ``except ImportError``
        handler — anything that raises there replaces the user's real error with a
        confusing one raised during exception handling."""
        for label, patch_kwargs in (
            ("metadata raises", {"side_effect": RuntimeError("boom")}),
            ("metadata None", {"return_value": None}),
            ("garbage rows", {"return_value": ["", ";;;", 'x; extra == "']}),
        ):
            with self.subTest(case=label):
                with mock.patch("importlib.metadata.requires", **patch_kwargs):
                    self.assertIsInstance(Tcl._requires(), tuple)
                    self.assertIsInstance(Tcl.engine_dists("maya"), tuple)
                    self.assertIsInstance(Tcl.declared_dists("maya"), tuple)

    @staticmethod
    def _fake_exe(name, *parents):
        """An interpreter path in the RUNNING platform's syntax.

        The allowlist reads ``os.path.basename(sys.executable)``, which is the
        NATIVE one — so a hardcoded ``C:\\...\\python.exe`` has no separator at
        all on a POSIX runner and arrives as one undivided basename. That fails
        ``startswith("python")`` for the wrong reason: the "is it named python?"
        assertions below then pass vacuously, and the one that requires the
        interpreter to BE named fails. Exactly how these tests read green on
        Windows and red on Linux CI (2026-08-19 → 2026-08-20).
        """
        return os.path.join(os.sep, *parents, name)

    def test_the_hint_never_names_a_dcc_host_binary(self):
        """pip driven through ``maya.exe`` routes into its ``-c`` handler and HANGS the
        host (uitk's ``default_install`` refuses for exactly this reason). ``pip_python``
        returns None in that case — falling back to ``sys.executable`` would print a
        command that freezes the user's DCC, which is worse than naming no interpreter."""
        from uitk.managers.optional_package_manager import OptionalPackageManager

        host_exe = self._fake_exe("maya.exe", "Autodesk", "Maya2025", "bin")

        # (a) DCC host with no sibling python — uitk declines to bless one
        with (
            mock.patch.object(
                OptionalPackageManager, "pip_python", staticmethod(lambda: None)
            ),
            mock.patch.object(sys, "executable", host_exe),
        ):
            hint = Tcl.engine_install_hint("maya")
        self.assertNotIn("maya.exe", hint)
        self.assertIn("tentacletk[maya]", hint)

        # (b) uitk unreachable — still must not fall back to sys.executable. Not exotic:
        # pip_python imports ExternalAppHandler, which pulls qtpy, which raises with no
        # Qt binding installed (bare venv / CI).
        with (
            mock.patch.dict(
                sys.modules, {"uitk.managers.optional_package_manager": None}
            ),
            mock.patch.object(sys, "executable", host_exe),
        ):
            hint = Tcl.engine_install_hint("maya")
        self.assertNotIn("maya.exe", hint)
        self.assertIn("tentacletk[maya]", hint)

        # (c) ...but a plain `python*` interpreter IS safe to name, and should be — the
        # fallback is an allowlist, not "anything that isn't a DCC I recognise".
        venv_exe = self._fake_exe("python.exe", "venv", "Scripts")
        with (
            mock.patch.dict(
                sys.modules, {"uitk.managers.optional_package_manager": None}
            ),
            mock.patch.object(sys, "executable", venv_exe),
        ):
            hint = Tcl.engine_install_hint("maya")
        self.assertIn(venv_exe, hint)

    def test_the_hint_fallback_is_an_allowlist_not_a_denylist(self):
        """An unrecognised interpreter name must NOT be named. A denylist ("not one of
        the DCC binaries I know") would print the host binary of any DCC whose probe
        module failed to import — the exact command that hangs the session."""
        with (
            mock.patch.dict(
                sys.modules, {"uitk.managers.optional_package_manager": None}
            ),
            mock.patch.object(
                sys, "executable", self._fake_exe("host-app.exe", "Some", "Unknown")
            ),
        ):
            hint = Tcl.engine_install_hint("maya")
        self.assertNotIn("host-app.exe", hint)
        self.assertIn("tentacletk[maya]", hint)

    def test_a_combined_marker_still_resolves_its_extra(self):
        """setuptools writes a lone ``extra == "maya"`` today, but a combined marker is
        legal. An exact-string compare dropped it silently — no diagnostic for the
        launcher, and the updater blind to that engine."""
        combined = [
            "pythontk>=0.9.24",
            'mayatk>=0.13.53; python_version >= "3.10" and extra == "maya"',
            "blendertk>=0.5.73; extra == 'blender'",  # single-quoted is legal too
        ]
        with mock.patch("importlib.metadata.requires", return_value=combined):
            self.assertEqual(Tcl.engine_dists("maya"), ("mayatk",))
            self.assertEqual(Tcl.engine_dists("blender"), ("blendertk",))
            self.assertEqual(Tcl._requires(), ("pythontk",))


class TestRegisterApps(unittest.TestCase):
    """``Tcl.register_apps``: extapps' apps are opened by name through the
    external-app handler, within the range ``tentacletk[apps]`` declares, so an
    installed extapps never falls out of step with this tentacle (2026-10-31)."""

    def _switchboard(self):
        sb = mock.MagicMock()
        return sb, sb.handlers.external_app

    def test_the_declared_range_rides_the_provider(self):
        sb, handler = self._switchboard()
        requirement = mock.MagicMock()
        requirement.__str__ = lambda _self: "extapps>=0.8.0,<0.9"
        with mock.patch("pythontk.PackageRequirement.declared_by", return_value=requirement) as declared:
            Tcl.register_apps(sb)
        declared.assert_called_once_with(Tcl.DIST, "extapps", extra=Tcl.APPS_EXTRA)
        handler.add_provider.assert_called_once_with(
            "extapps>=0.8.0,<0.9", probe_module="extapps"
        )
        handler.discover.assert_called_once_with()

    def test_a_source_checkout_registers_it_unranged(self):
        """No tentacletk metadata (a checkout on the path): the apps are still
        found by name, the regression the move left (no provider at all)."""
        sb, handler = self._switchboard()
        with mock.patch("pythontk.PackageRequirement.declared_by", return_value=None):
            Tcl.register_apps(sb)
        handler.add_provider.assert_called_once_with("extapps", probe_module="extapps")

    def test_the_extra_states_a_floor_and_a_cap(self):
        pyproject = ROOT / "pyproject.toml"
        if not pyproject.is_file():
            self.skipTest("no pyproject.toml (installed, not a source checkout)")
        text = pyproject.read_text(encoding="utf-8")
        self.assertRegex(text, r'apps = \["extapps>=\d+\.\d+\.\d+,<\d+\.\d+"\]')


class TestEngineExtrasContract(unittest.TestCase):
    """``pyproject.toml``'s extras keys ARE ``Tcl.HOSTS`` keys — the identity the design rests on.

    Reads the source pyproject (not metadata) so a renamed extra fails here, in a fresh
    checkout, rather than at a user's pip line.
    """

    def _pyproject(self):
        toml = ROOT / "pyproject.toml"
        if not toml.is_file():
            self.skipTest("no pyproject.toml (installed, not a source checkout)")
        try:
            import tomllib
        except ModuleNotFoundError:  # < 3.11
            try:
                import tomli as tomllib
            except ModuleNotFoundError:
                self.skipTest("no TOML parser available")
        with open(toml, "rb") as handle:
            return tomllib.load(handle).get("project", {})

    def test_every_extra_is_named_after_a_host(self):
        """The one exception is ``Tcl.APPS_EXTRA``: the standalone-apps product,
        not an engine, whose range ``Tcl.register_apps`` installs within."""
        for extra in self._pyproject().get("optional-dependencies", {}):
            if extra == Tcl.APPS_EXTRA:
                continue
            with self.subTest(extra=extra):
                self.assertIn(
                    extra,
                    Tcl.HOSTS,
                    f"extra '{extra}' matches no Tcl.HOSTS key — Tcl.host() can no "
                    f"longer resolve it, so declared_dists() silently returns nothing",
                )

    def test_the_engines_are_declared_as_extras_not_base_dependencies(self):
        joined = " ".join(self._pyproject().get("dependencies", []))
        self.assertNotIn("mayatk", joined)
        self.assertNotIn("blendertk", joined)

    def test_declared_engines_carry_a_version_floor(self):
        """push.ps1 syncs pins by regexing ``"<dist>>=<ver>"`` over the whole file. A
        floor-less extra silently drops out of the release cascade."""
        for extra, specs in self._pyproject().get("optional-dependencies", {}).items():
            for spec in specs:
                with self.subTest(extra=extra, spec=spec):
                    self.assertIn(">=", spec)


class TestMissingEngineDiagnostic(unittest.TestCase):
    """A missing engine must name itself and the fix; anything else propagates untouched.

    ``engine_dists`` is stubbed throughout: inside Maya the real ``mayatk`` IS installed,
    so testing against the live environment would assert nothing.
    """

    @contextlib.contextmanager
    def _imports_raising(self, error):
        """Patch the launcher's importer so the entry module raises *error*."""
        import tentacle.tcl as tcl_module

        real = tcl_module.importlib.import_module

        def fake(name):
            if name == "mayatk":
                raise error
            return real(name)

        with (
            mock.patch.object(
                Tcl, "engine_dists", classmethod(lambda cls, host: ("mayatk",))
            ),
            mock.patch.object(tcl_module.importlib, "import_module", fake),
        ):
            yield

    def _import_maya_entry(self):
        """Import the Maya toolkit the way a launch does (``Tcl.toolkit``)."""
        return Tcl.toolkit("maya")

    def test_a_missing_engine_names_the_dist_and_the_pip_line(self):
        error = ModuleNotFoundError("No module named 'mayatk'", name="mayatk")
        with self._imports_raising(error):
            with self.assertRaises(ImportError) as ctx:
                self._import_maya_entry()
        message = str(ctx.exception)
        self.assertIn("mayatk", message)
        self.assertIn('"tentacletk[maya]"', message)

    def test_a_missing_engine_submodule_is_still_the_engine(self):
        """``import mayatk.foo`` reports ``mayatk.foo`` — matching only the exact dist
        name would let the real cause fall through as a bare ModuleNotFoundError."""
        error = ModuleNotFoundError("No module named 'mayatk.core'", name="mayatk.core")
        with self._imports_raising(error):
            with self.assertRaises(ImportError) as ctx:
                self._import_maya_entry()
        self.assertIn("tentacletk[maya]", str(ctx.exception))

    def test_an_unrelated_import_error_is_not_rewritten(self):
        """Rewriting every ImportError would disguise a real bug inside the engine as
        "the engine is not installed" and send the user to a pip line that fixes nothing."""
        error = ModuleNotFoundError("No module named 'PIL'", name="PIL")
        with self._imports_raising(error):
            with self.assertRaises(ImportError) as ctx:
                self._import_maya_entry()
        message = str(ctx.exception)
        self.assertIn("PIL", message)
        self.assertNotIn("tentacletk[maya]", message)

    def test_a_from_import_failure_inside_the_engine_is_not_rewritten(self):
        """``from mayatk import Gone`` raises a plain ImportError whose ``.name`` is
        still ``mayatk`` — the engine IS installed and a symbol it exports moved (the
        cascade break). Rewriting that to "not installed" offers a pip line that
        reinstalls what is already there and hides the rename."""
        error = ImportError("cannot import name 'Gone' from 'mayatk'", name="mayatk")
        with self._imports_raising(error):
            with self.assertRaises(ImportError) as ctx:
                self._import_maya_entry()
        message = str(ctx.exception)
        self.assertIn("Gone", message)
        self.assertNotIn("tentacletk[maya]", message)

    def test_the_original_error_is_chained(self):
        error = ModuleNotFoundError("No module named 'mayatk'", name="mayatk")
        with self._imports_raising(error):
            with self.assertRaises(ImportError) as ctx:
                self._import_maya_entry()
        self.assertIs(ctx.exception.__cause__, error)

    def test_a_successful_import_returns_the_named_attribute(self):
        self.assertIs(Tcl._import_entry("maya", "tentacle.tcl", "Tcl"), Tcl)

    def test_no_attribute_returns_the_module(self):
        module = Tcl._import_entry("maya", "tentacle.tcl")
        self.assertEqual(module.__name__, "tentacle.tcl")

    def test_the_launcher_never_installs_anything(self):
        """Driving pip from a DCC's startup tick blocks the host on network I/O, and
        Blender's bundled interpreter keeps user-site off ``sys.path`` so the obvious
        install would not even be importable. The diagnostic is the whole feature."""
        source = (PKG / "tcl.py").read_text(encoding="utf-8")
        for banned in ("PackageManager(", "subprocess"):
            with self.subTest(token=banned):
                offenders = [
                    line
                    for line in source.splitlines()
                    if banned in line and not line.lstrip().startswith("#")
                ]
                self.assertEqual(offenders, [], f"{banned} reached tcl.py")


class TestTheToolkitRoutesThroughTheGuard(unittest.TestCase):
    """The launch imports the host's toolkit through ``_import_entry``.

    By source: a launcher that re-inlines ``import mayatk`` loses the missing-engine diagnostic
    silently — nothing fails, the user just gets a raw ModuleNotFoundError with no fix in it.
    """

    def test_the_toolkit_uses_the_guarded_import(self):
        source = (PKG / "tcl.py").read_text(encoding="utf-8")
        body = source.split("def toolkit(")[1].split("\n    @")[0]
        self.assertIn("_import_entry(", body)
        import ast

        tree = ast.parse(source)
        imported = {
            alias.name.split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        } | {
            (node.module or "").split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom)
        }
        self.assertFalse(
            imported & set(Tcl.ENGINES.values()), "the launcher imports a toolkit by name"
        )


class TestReloadTeardown(unittest.TestCase):
    """``Settings > Reload Scripts`` must release what the reload would ORPHAN.

    ``ptk.ModuleReloader`` rebinds module globals, but the DCC keeps holding what
    the old code registered with it — an armed activation shortcut, a live
    ``scriptJob``, an OpenMaya callback — while the handle that could cancel any
    of them goes out with the old class object. That is both reported symptoms:
    the reload appears to do nothing (the pre-reload menu still owns the key),
    and the host dies later when a scene event fires a callback whose widget is
    gone. ``prepare_reload`` is the teardown that runs while those handles are
    still reachable.

    Host-independent by construction (these must also pass inside a live Maya):
    the engine is named through a patched ``Tcl.ENGINES`` rather than by faking
    a DCC, and the marking-menu module is a stand-in rather than the real one,
    so a run never retires a menu another test is using.
    """

    class _Instance:
        def __init__(self):
            self.retired = False
            self.deleted = False

        def deleteLater(self):
            self.deleted = True

    def _uitk_module(self, instances):
        """A stand-in for the ``uitk`` root, whose PUBLIC ``MarkingMenu`` the
        teardown reaches for (the previous Maya teardown reached for internals
        uitk had dropped, and no-opped in silence for as long as that lasted)."""
        module = types.ModuleType("uitk")

        class _MarkingMenu:
            @staticmethod
            def _live_registry():
                return list(instances)

            @staticmethod
            def retire_all():
                # Mirrors uitk: retires every live instance and hands them back,
                # so the caller can dispose of them without touching the registry.
                for instance in instances:
                    instance.retired = True
                return list(instances)

        module.MarkingMenu = _MarkingMenu
        return module

    def _engine_module(self, reset=None):
        module = types.ModuleType("tentacle_fake_engine")
        if reset is not None:
            module.ScriptJobManager = types.SimpleNamespace(reset=reset)
        return module

    @contextlib.contextmanager
    def _patched(self, instances=(), engine=None):
        modules = {"uitk": self._uitk_module(instances)}
        if engine is not None:
            modules["tentacle_fake_engine"] = engine
        with (
            mock.patch.dict(sys.modules, modules),
            mock.patch.dict(
                Tcl.ENGINES, {"testhost": "tentacle_fake_engine"}, clear=True
            ),
        ):
            yield

    def test_live_marking_menus_are_retired_and_returned(self):
        instances = [self._Instance(), self._Instance()]
        with self._patched(instances):
            retired = Tcl.prepare_reload("testhost")
        self.assertEqual(retired, instances)
        self.assertTrue(all(i.retired for i in instances))

    def test_the_engines_script_jobs_are_reset(self):
        reset = mock.MagicMock()
        with self._patched(engine=self._engine_module(reset)):
            Tcl.prepare_reload("testhost")
        reset.assert_called_once_with()

    def test_a_host_with_no_engine_is_not_an_error(self):
        with self._patched():
            self.assertEqual(Tcl.prepare_reload("other"), [])

    def test_the_retired_instances_come_from_uitks_public_surface(self):
        """Not from a private module path: the Maya fork's previous teardown
        reached for internals uitk had dropped and no-opped in SILENCE."""
        instances = [self._Instance()]
        with self._patched(instances):
            self.assertIs(Tcl.prepare_reload("testhost")[0], instances[0])

    def test_a_failing_teardown_never_blocks_the_reload(self):
        """A skew in the code being REPLACED must not strand the user on it."""
        reset = mock.MagicMock(side_effect=RuntimeError("stale engine"))
        instances = [self._Instance()]
        with self._patched(instances, self._engine_module(reset)):
            with contextlib.redirect_stdout(io.StringIO()):
                retired = Tcl.prepare_reload("testhost")
        self.assertEqual(retired, instances)  # the menu teardown still ran

    def test_a_uitk_that_answers_a_count_does_not_break_the_rebuild(self):
        """Version skew degrades to "retired but not disposed" — a leak — never
        to an int handed to dispose_retired to iterate, which raises from inside
        the caller's finally and takes the rebuild with it."""
        instances = [self._Instance()]
        module = self._uitk_module(instances)
        module.MarkingMenu.retire_all = staticmethod(lambda: len(instances))
        with mock.patch.dict(sys.modules, {"uitk": module}):
            with contextlib.redirect_stdout(io.StringIO()):
                retired = Tcl.prepare_reload("other")
        self.assertEqual(retired, [])
        Tcl.dispose_retired(retired)  # must not raise

    def test_dispose_retired_defers_deletion_of_the_old_menus(self):
        instances = [self._Instance(), self._Instance()]
        Tcl.dispose_retired(instances)
        self.assertTrue(all(i.deleted for i in instances))

    def test_dispose_retired_tolerates_an_already_dead_instance(self):
        dead = mock.MagicMock()
        dead.deleteLater.side_effect = RuntimeError("C++ object already deleted")
        Tcl.dispose_retired([dead, self._Instance()])  # must not raise

    def test_dispose_retired_accepts_nothing_to_dispose(self):
        Tcl.dispose_retired(None)
        Tcl.dispose_retired([])


class TestReloadPackages(unittest.TestCase):
    """The half of the reload both DCCs share: one dependency order, one
    ``import_missing`` policy, one place that names a module which did not
    reload. ``pythontk`` is stood in for so the real ecosystem is never
    re-executed underneath the suite."""

    class _Report(list):
        def __init__(self, modules=(), failed=()):
            super().__init__(modules)
            self.failed = list(failed)

    @contextlib.contextmanager
    def _stub_ptk(self, report):
        calls = []
        module = types.ModuleType("pythontk")

        class ModuleReloader:
            def reload(self, package, **kwargs):
                calls.append((package, kwargs))
                return report

        module.ModuleReloader = ModuleReloader
        with mock.patch.dict(sys.modules, {"pythontk": module}):
            yield calls

    def test_the_engine_reloads_with_its_host_and_never_the_other_ones(self):
        with self._stub_ptk(self._Report(["a"])) as calls:
            Tcl.reload_packages("maya")
            Tcl.reload_packages("blender")
        self.assertEqual(
            calls[0][1]["dependencies_first"], ("pythontk", "mayatk", "uitk")
        )
        self.assertEqual(
            calls[1][1]["dependencies_first"], ("pythontk", "blendertk", "uitk")
        )

    def test_only_what_this_session_loaded_is_refreshed(self):
        """import_missing=True would discovery-import the OTHER DCC's slot
        package, which imports a host that is not running."""
        with self._stub_ptk(self._Report()) as calls:
            Tcl.reload_packages("maya")
        self.assertIs(calls[0][1]["import_missing"], False)
        self.assertEqual(calls[0][0], "tentacle")

    def test_a_host_with_no_engine_drops_it_from_the_order(self):
        with self._stub_ptk(self._Report()) as calls:
            Tcl.reload_packages("other")
        self.assertEqual(calls[0][1]["dependencies_first"], ("pythontk", "uitk"))

    def test_a_module_that_did_not_reload_is_named(self):
        """ModuleReloader.reload records the failure and carries on, so a partial
        reload is the "reload did nothing" report one module at a time."""
        report = self._Report(["a"], [("tentacle.slots.maya.uv", RuntimeError("boom"))])
        out = io.StringIO()
        with self._stub_ptk(report), contextlib.redirect_stdout(out):
            returned = Tcl.reload_packages("maya")
        self.assertIs(returned, report)
        self.assertIn("tentacle.slots.maya.uv", out.getvalue())
        self.assertIn("boom", out.getvalue())

    def test_a_clean_reload_says_nothing(self):
        out = io.StringIO()
        with self._stub_ptk(self._Report(["a", "b"])), contextlib.redirect_stdout(out):
            Tcl.reload_packages("maya")
        self.assertEqual(out.getvalue(), "")


class _ReloadAdapter:
    """A host adapter recording what a reload asks of it."""

    def __init__(self):
        self.calls = []
        self.deferred = []

    def teardown(self):
        self.calls.append("teardown")

    def defer(self, fn):
        self.calls.append("defer")
        self.deferred.append(fn)

    def report(self, message, error=False):
        self.calls.append(("report", message, error))


class _Report(list):
    """``ptk.ReloadReport``: the reloaded modules, and the ones that failed."""

    def __init__(self, items, failed=()):
        super().__init__(items)
        self.failed = list(failed)


class TestReload(unittest.TestCase):
    """``Settings > Reload Scripts`` -- ONE path for every host: retire the menus and the
    engine's callbacks (``prepare_reload``), let the host release what it holds
    (``adapter.teardown``: Blender's keymap bridge and docked console), reload the packages,
    then rebuild on the host's next tick (``adapter.defer``) and tell the user through the
    host (``adapter.report``), never through the retired panel."""

    def _reload(self, host="blender", packages=None, error=None):
        adapter, order = _ReloadAdapter(), []
        retired = [mock.Mock()]

        def prepare(cls, h=None):
            order.append(("prepare", h))
            return retired

        def reload_packages(cls, h=None):
            order.append(("reload", h))
            if error is not None:
                raise error
            return packages if packages is not None else _Report(["a", "b", "c"])

        with (
            mock.patch.object(Tcl, "host", classmethod(lambda cls: host)),
            mock.patch.object(
                Tcl, "host_adapter", classmethod(lambda cls, h=None, toolkit=None: adapter)
            ),
            mock.patch.object(Tcl, "prepare_reload", classmethod(prepare)),
            mock.patch.object(Tcl, "reload_packages", classmethod(reload_packages)),
            contextlib.redirect_stdout(io.StringIO()),
        ):
            count = Tcl.reload()
        return count, adapter, order, retired

    def test_every_host_reloads_the_same_way(self):
        for host in Tcl.HOSTS:
            with self.subTest(host=host):
                count, adapter, order, _retired = self._reload(host)
                self.assertEqual(count, 3)
                self.assertEqual(order, [("prepare", host), ("reload", host)])
                self.assertEqual(adapter.calls[:2], ["teardown", "defer"])
                self.assertEqual(
                    adapter.calls[2], ("report", "Tentacle reloaded (3 modules).", False)
                )

    def test_the_host_lets_go_before_the_packages_reload(self):
        """Its handles (keymap items, the docked console's glue) are reachable only from
        the code the reload is about to replace."""
        adapter, events = _ReloadAdapter(), []
        adapter.teardown = lambda: events.append("teardown")
        with (
            mock.patch.object(Tcl, "host", classmethod(lambda cls: "blender")),
            mock.patch.object(
                Tcl, "host_adapter", classmethod(lambda cls, h=None, toolkit=None: adapter)
            ),
            mock.patch.object(Tcl, "prepare_reload", classmethod(lambda cls, h=None: [])),
            mock.patch.object(
                Tcl,
                "reload_packages",
                classmethod(lambda cls, h=None: events.append("reload") or _Report([])),
            ),
            contextlib.redirect_stdout(io.StringIO()),
        ):
            Tcl.reload()
        self.assertEqual(events, ["teardown", "reload"])

    def test_the_rebuild_waits_for_the_host_and_disposes_the_old_menus(self):
        _count, adapter, _order, retired = self._reload("maya")
        self.assertEqual(len(adapter.deferred), 1, "the rebuild is deferred, never in-frame")
        with mock.patch.object(Tcl, "build", classmethod(lambda cls, h=None, **kw: h)) as _:
            adapter.deferred[0]()
        retired[0].deleteLater.assert_called_once_with()

    def test_a_failed_reload_still_rebuilds_and_says_so(self):
        """The teardown already retired the menu: bailing out would strand the session
        with no marking menu at all (Blender's reload used to)."""
        for host in Tcl.HOSTS:
            with self.subTest(host=host):
                count, adapter, _order, _retired = self._reload(
                    host, error=RuntimeError("a module raised")
                )
                self.assertEqual(count, 0)
                self.assertIn("defer", adapter.calls)
                report = [c for c in adapter.calls if isinstance(c, tuple)]
                self.assertEqual(len(report), 1)
                self.assertTrue(report[0][2], "the failure is reported as an error")
                self.assertIn("FAILED", report[0][1])
                self.assertIn("a module raised", report[0][1])

    def test_a_partial_reload_is_reported(self):
        _count, adapter, _order, _retired = self._reload(
            "maya", packages=_Report(["a", "b"], failed=[("c", "boom")])
        )
        report = [c for c in adapter.calls if isinstance(c, tuple)][0]
        self.assertIn("1 FAILED", report[1])

    def test_no_host_raises(self):
        with mock.patch.object(Tcl, "host", classmethod(lambda cls: None)):
            with self.assertRaises(RuntimeError):
                Tcl.reload()

    def test_the_settings_slot_reloads_through_the_launcher(self):
        source = (PKG / "slots" / "settings.py").read_text(encoding="utf-8")
        body = source[source.index("def tb001") : source.index("def check_for_update")]
        self.assertIn("Tcl.reload()", body)

    def test_the_blender_console_reload_is_the_launchers(self):
        src = (PKG / "tcl_blender.py").read_text(encoding="utf-8")
        body = src[src.index("\ndef reload():") :].split("\ndef ", 2)[1]
        self.assertIn("Tcl.reload()", body)


if __name__ == "__main__":
    unittest.main()
