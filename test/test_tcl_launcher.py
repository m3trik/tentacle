#!/usr/bin/python
# coding=utf-8
"""Tests for the host-agnostic launcher and the shared activation-key contract (``tentacle.tcl``).

The three ``tcl_<dcc>`` entry classes need their DCC to construct, so what is pinned here is the
contract they all consume — key normalization, the chord table, host detection, and that ``launch``
forwards to the right host — plus (by source, the only way without a DCC) that each fork actually
routes through it rather than re-hardcoding a fourth copy of the table.

**These must pass in a plain interpreter AND inside a live DCC**, since tentacle's canonical run is
``run_tests.py --in-maya``. That rules out the obvious-looking approach of faking the host via
``sys.modules``: under Maya, ``maya.cmds`` genuinely IS present and detection correctly answers
"maya" no matter what a test injects. Tests wanting a specific host therefore narrow ``Tcl.HOSTS``
or stub ``host()``, and module stand-ins are real ``types.ModuleType`` objects (see ``_fake_bpy``).
"""
import contextlib
import os
import sys
import types
import unittest
from pathlib import Path
from unittest import mock

# Ensure the package root is importable
ROOT = Path(__file__).resolve().parent.parent
PKG = ROOT / "tentacle"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tentacle.tcl import Tcl  # noqa: E402


def _user_keymap_row(key_type, value="PRESS"):
    """A stand-in for a merged user-keyconfig keymap item, with every field the
    bridge reads (``_is_bare_press`` checks the modifier flags)."""
    return types.SimpleNamespace(
        type=key_type,
        value=value,
        idname="tentacle.show_marking_menu",
        any=False,
        ctrl=False,
        alt=False,
        shift=False,
        oskey=False,
    )


def _fake_bpy():
    """A stand-in ``bpy`` that survives being imported.

    A bare ``MagicMock`` is NOT usable here: inside Maya, PySide6's ``shibokensupport`` installs an
    import hook that reads ``__name__`` off every imported module, and MagicMock raises
    AttributeError for it — so the mock blew up at ``import bpy`` in the canonical in-Maya run
    while passing everywhere else. A real module object has the dunders any import hook expects.
    """
    module = types.ModuleType("bpy")
    module.app = mock.MagicMock()
    return module


@contextlib.contextmanager
def _as_blender(bpy, entry):
    """Make ``import bpy`` and ``from tentacle import tcl_blender`` resolve to the given stubs.

    The entry module is patched onto the ``tentacle`` package's ``__dict__``, not into
    ``sys.modules``: ``from tentacle import tcl_blender`` resolves the package ATTRIBUTE first and
    only falls back to ``sys.modules``, so a sys.modules-only patch is ignored once anything else
    in the suite has imported the real module — which ran the real Blender registration mid-test
    (a full-suite-only failure). Patching the dict also avoids the lazy package resolver importing
    the whole Blender/Qt stack just to snapshot the original.
    """
    import tentacle

    with mock.patch.dict(sys.modules, {"bpy": bpy}), mock.patch.dict(
        tentacle.__dict__, {"tcl_blender": entry}
    ):
        yield


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
        self.assertEqual(
            Tcl.HOSTS, {"maya": "maya.cmds", "blender": "bpy", "max": "pymxs"}
        )

    def test_host_table_checks_maya_first(self):
        """Order is load-bearing — a mayapy with a pip-installed ``bpy`` must read as Maya."""
        self.assertEqual(list(Tcl.HOSTS), ["maya", "blender", "max"])

    def test_detects_the_host_from_sys_modules(self):
        for name, probe in Tcl.HOSTS.items():
            with self.subTest(host=name):
                with mock.patch.object(Tcl, "HOSTS", {name: probe}), mock.patch.dict(
                    sys.modules, {probe: mock.MagicMock()}
                ):
                    self.assertEqual(Tcl.host(), name)

    def test_reports_the_actual_host_of_this_interpreter(self):
        """Whatever is really running us — None in plain python, the DCC when hosted."""
        expected = next(
            (name for name, probe in Tcl.HOSTS.items() if probe in sys.modules), None
        )
        self.assertEqual(Tcl.host(), expected)


class TestLaunchDispatch(unittest.TestCase):
    """``launch`` — routes to the host's entry point and forwards the caller's arguments."""

    def _launch_in(self, host, **kwargs):
        """Run launch() as if hosted by ``host``, returning the kwargs its branch received.

        Detection is stubbed rather than simulated — inside a live Maya (the canonical suite's
        interpreter) the real ``host()`` always and correctly answers "maya", and what these
        tests are about is the dispatch, not the detection (covered by TestHostDetection).
        """
        with mock.patch.object(Tcl, "host", classmethod(lambda cls: host)):
            with mock.patch.object(Tcl, f"_launch_{host}") as launcher:
                Tcl.launch(**kwargs)
        self.assertTrue(launcher.called, f"_launch_{host} was not called")
        return launcher.call_args.kwargs

    def test_each_host_routes_to_its_own_entry(self):
        for host in Tcl.HOSTS:
            with self.subTest(host=host):
                self._launch_in(host)  # asserts the matching launcher fired

    def test_key_show_is_forwarded(self):
        self.assertEqual(self._launch_in("blender", key_show="F11")["key_show"], "F11")

    def test_unset_key_show_is_not_forwarded(self):
        """Omitting it must let each entry class apply its own default (Blender reads
        TENTACLE_KEY) — forwarding None would look identical but bypasses that chain."""
        self.assertNotIn("key_show", self._launch_in("blender"))

    def test_extra_kwargs_are_forwarded(self):
        kwargs = self._launch_in("maya", key_show="Z", log_level="DEBUG")
        self.assertEqual(kwargs["log_level"], "DEBUG")

    def test_no_host_raises_with_a_usable_message(self):
        with mock.patch.object(Tcl, "host", classmethod(lambda cls: None)):
            with self.assertRaises(RuntimeError) as ctx:
                Tcl.launch()
        self.assertIn("no supported DCC host", str(ctx.exception))

    def test_blender_timer_callback_returns_none(self):
        """bpy.app.timers unregisters a one-shot only when its callback returns None; returning
        the menu instance would re-run the whole registration every 0.5s."""
        bpy, entry = _fake_bpy(), mock.MagicMock()
        with _as_blender(bpy, entry):
            Tcl._launch_blender(key_show="Z")
            callback = bpy.app.timers.register.call_args.args[0]
            self.assertIsNone(callback())

        entry.register.assert_called_once_with(key_show="Z")

    def test_blender_startup_is_deferred_not_immediate(self):
        """Blender startup scripts run before the UI settles — the entry must be called from the
        timer callback, never during launch()."""
        bpy, entry = _fake_bpy(), mock.MagicMock()
        with _as_blender(bpy, entry):
            Tcl._launch_blender()
            entry.register.assert_not_called()  # scheduled, not run
            bpy.app.timers.register.call_args.args[0]()
            entry.register.assert_called_once()


class TestDefaultKeyUpgradePath(unittest.TestCase):
    """A shipped default-key change must actually reach a user who already has bindings persisted.

    Bindings live in QSettings and are forward-merged at construction
    (``MarkingMenu._reconcile_bindings``), and the activation key is the FIRST ``Key_*`` the
    resolver meets while walking that merged dict. So "does the new default win?" is decided by
    merge ordering — the difference between a default change taking effect and being a silent
    no-op for every existing install. Pure functions, so this runs without a DCC.
    """

    def test_new_default_wins_over_previously_persisted_bindings(self):
        from uitk.widgets.marking_menu._marking_menu import MarkingMenu
        from uitk.widgets.marking_menu._resolver import MenuResolver

        stored = Tcl.chord_bindings("F12", "maya#startmenu")  # an older default, persisted
        defaults = Tcl.chord_bindings(Tcl.DEFAULT_KEY, "maya#startmenu")

        merged = MarkingMenu._reconcile_bindings(defaults, stored)
        _normalized, activation = MenuResolver.parse_binding_keys(merged)

        self.assertEqual(activation, f"Key_{Tcl.DEFAULT_KEY}")

    def test_chords_resolve_against_the_new_key(self):
        """Not just the bare key — the whole chord set must be reachable post-upgrade."""
        from uitk.widgets.marking_menu._marking_menu import MarkingMenu

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


class TestBlenderKeyTranslation(unittest.TestCase):
    """The Qt ↔ Blender keymap-``type`` translation — the Blender fork's half of the key contract.

    It has to work in BOTH directions: forward to install the keymap item, and backward to name
    the Qt key for a rebind a user made in Preferences ▸ Keymap (measured as a working rebind
    route in ``test/blender/gui_keymap_editor_check.py``). A backward translation that produces a
    name ``QtCore.Qt`` doesn't have would make the adoption a silent no-op.
    """

    @classmethod
    def setUpClass(cls):
        try:
            from tentacle.tcl_blender import _KeymapBridge
        except Exception as error:  # no Qt binding available in this interpreter
            raise unittest.SkipTest(f"tcl_blender unimportable: {error}")
        cls.bridge = _KeymapBridge

    def test_forward_translation(self):
        for qt_key, expected in (
            ("Key_F12", "F12"),
            ("Key_Z", "Z"),
            ("Key_Meta", "OSKEY"),
            ("Key_1", "ONE"),
            ("Key_BracketLeft", "LEFT_BRACKET"),
        ):
            with self.subTest(qt_key=qt_key):
                self.assertEqual(self.bridge.qt_key_to_blender_type(qt_key), expected)

    def test_forward_translation_accepts_any_casing(self):
        """Callers pass bare or Qt-named keys in whatever case the user typed."""
        for form in ("Key_META", "meta", "Meta", "Key_Meta"):
            with self.subTest(form=form):
                self.assertEqual(self.bridge.qt_key_to_blender_type(form), "OSKEY")

    def test_backward_translation_names_a_real_qt_key(self):
        from qtpy import QtCore

        for key_type in ("F12", "Z", "OSKEY", "ONE", "SPACE", "LEFT_ARROW", "ESC"):
            with self.subTest(key_type=key_type):
                name = self.bridge.blender_type_to_qt_key(key_type)
                self.assertIsNotNone(name, f"{key_type} produced no Qt name")
                self.assertTrue(hasattr(QtCore.Qt, name), f"{name} is not a Qt key")

    def test_shared_blender_types_name_the_canonical_qt_spelling(self):
        """Meta/Super_L/Super_R all map to OSKEY; coming back it must be the first — ``Meta``."""
        self.assertEqual(self.bridge.blender_type_to_qt_key("OSKEY"), "Key_Meta")
        self.assertEqual(self.bridge.blender_type_to_qt_key("RET"), "Key_Return")

    def test_round_trip_is_stable_for_every_alias(self):
        """Qt name → Blender type → Qt name → the SAME Blender type (aliases may collapse)."""
        for qt_name, key_type in self.bridge._BLENDER_KEY_ALIASES.items():
            with self.subTest(qt_name=qt_name):
                back = self.bridge.blender_type_to_qt_key(key_type)
                self.assertIsNotNone(back, f"{key_type} has no Qt name")
                self.assertEqual(self.bridge.qt_key_to_blender_type(back), key_type)

    def test_types_with_no_qt_counterpart_return_none(self):
        """Blender binds things Qt has no key for; adopting one must be declined, not faked."""
        for key_type in ("LEFTMOUSE", "NDOF_BUTTON_1", "WHEELUPMOUSE", "", None):
            with self.subTest(key_type=key_type):
                self.assertIsNone(self.bridge.blender_type_to_qt_key(key_type))

    def test_rebind_moves_existing_items_in_place(self):
        """A rebind is a MOVE: retype the installed items, never tear them down and rebuild.

        Recreating would briefly unbind the very item the user just edited in the keymap editor."""
        bridge = self.bridge
        before = (bridge.keymaps, bridge.active_vk, bridge.key_down)
        item = types.SimpleNamespace(type="Z")
        try:
            bridge.keymaps = [(None, item)]
            with mock.patch.object(bridge, "install_keymap") as reinstall:
                bridge.rebind(None, "Key_F12")
            self.assertEqual(item.type, "F12")
            reinstall.assert_not_called()
        finally:
            bridge.keymaps, bridge.active_vk, bridge.key_down = before

    def test_rebind_installs_when_nothing_is_bound_yet(self):
        bridge = self.bridge
        before = (bridge.keymaps, bridge.active_vk, bridge.key_down)
        try:
            bridge.keymaps = []
            with mock.patch.object(bridge, "install_keymap") as install:
                bridge.rebind("tcl-sentinel", "Key_F12")
            install.assert_called_once_with("tcl-sentinel", "F12")
        finally:
            bridge.keymaps, bridge.active_vk, bridge.key_down = before

    def test_rebind_survives_a_platform_without_virtual_keys(self):
        """``rebind`` runs on every platform; only the poller's key is Windows-specific.

        A single-character key used to reach ``ctypes.windll`` from here and take the whole
        rebind — keymap item included — down with it off Windows."""
        bridge = self.bridge
        before = (bridge.keymaps, bridge.active_vk, bridge.key_down)
        item = types.SimpleNamespace(type="F12")
        try:
            bridge.keymaps = [(None, item)]
            with mock.patch("tentacle.tcl_blender.sys.platform", "linux"):
                bridge.rebind(None, "Key_Z")
            self.assertEqual(item.type, "Z")  # the keymap half still moved
            self.assertIsNone(bridge.active_vk)  # the Windows-only half declined cleanly
        finally:
            bridge.keymaps, bridge.active_vk, bridge.key_down = before

    def test_rebind_moves_the_user_keyconfig_rows_too(self):
        """A Qt-side rebind must retype the merged user-keyconfig rows, not just our addon items.

        Blender's keymap editor edits a MERGED copy of our item (see ``user_keymap_items``), and
        that copy — including any customization saved in userpref.blend — does not follow an
        addon-item retype. Left behind on the old key, ``sync_keymap_rebind`` reads it as a fresh
        Preferences ▸ Keymap edit and adopts the OLD key right back: the shortcut-editor rebind
        reverts within a second, and the store resets to the stale key across sessions."""
        bridge = self.bridge
        before = (bridge.keymaps, bridge.active_vk, bridge.key_down)
        addon_item = types.SimpleNamespace(type="Z")
        user_row = _user_keymap_row("Z")
        try:
            bridge.keymaps = [(None, addon_item)]
            with mock.patch.object(
                bridge, "user_keymap_items", return_value=[user_row]
            ):
                bridge.rebind(None, "Key_F12")
            self.assertEqual(addon_item.type, "F12")
            self.assertEqual(user_row.type, "F12")
        finally:
            bridge.keymaps, bridge.active_vk, bridge.key_down = before

    def test_editor_rebind_survives_the_keymap_scan(self):
        """The scan must not re-adopt the key a Qt-side rebind just moved away from.

        The end-to-end regression: rebind to F12 through the shortcut-editor route, then run the
        throttled ``sync_keymap_rebind`` scan against a user-keyconfig row that carried the old
        key. Pre-fix the scan saw live=Z ≠ installed=F12 and called ``set_activation_key(Key_Z)``
        — silently reverting the user's choice."""
        bridge = self.bridge
        before = (
            bridge.keymaps,
            bridge.active_vk,
            bridge.key_down,
            bridge.tcl,
            bridge.gesture_active,
            bridge._last_key_scan,
            bridge._declined,
        )
        addon_item = types.SimpleNamespace(type="Z")
        user_row = _user_keymap_row("Z")
        tcl = types.SimpleNamespace(
            _activation_key_held=False, set_activation_key=mock.Mock()
        )
        try:
            bridge.keymaps = [(None, addon_item)]
            bridge.tcl = tcl
            bridge.gesture_active = False
            bridge._declined = None
            with mock.patch.object(
                bridge, "user_keymap_items", return_value=[user_row]
            ):
                bridge.rebind(tcl, "Key_F12")
                bridge._last_key_scan = 0.0  # defeat the once-a-second throttle
                bridge.sync_keymap_rebind(tcl)
            tcl.set_activation_key.assert_not_called()
        finally:
            (
                bridge.keymaps,
                bridge.active_vk,
                bridge.key_down,
                bridge.tcl,
                bridge.gesture_active,
                bridge._last_key_scan,
                bridge._declined,
            ) = before

    @unittest.skipUnless(sys.platform == "win32", "virtual-keys are a Windows concept")
    def test_rebind_moves_the_pollers_virtual_key(self):
        """The poller watches by virtual-key; left on the old one it ends the gesture instantly."""
        bridge = self.bridge
        before = (bridge.active_vk, bridge.key_down)
        try:
            bridge.key_down = True
            # No keymap items installed (no Blender here) → rebind only moves the poller.
            with mock.patch.object(bridge, "addon_key_type", return_value="F12"):
                bridge.rebind(None, "Key_F12")
            self.assertEqual(bridge.active_vk, 0x7B)  # VK_F12
            self.assertFalse(bridge.key_down)  # edge state reset for the new key
        finally:
            bridge.active_vk, bridge.key_down = before


class TestForksUseTheSharedContract(unittest.TestCase):
    """The forks must consume ``Tcl``, not re-hardcode the table — the drift this module prevents.

    Source-level because constructing any fork needs its DCC. A literal ``hud#startmenu`` outside
    ``tcl.py`` is the signature of a re-inlined copy.
    """

    FORKS = ("tcl_maya.py", "tcl_blender.py", "tcl_max.py")

    def _source(self, name):
        return (PKG / name).read_text(encoding="utf-8")

    def test_forks_call_the_shared_helpers(self):
        for name in self.FORKS:
            with self.subTest(fork=name):
                src = self._source(name)
                self.assertIn("Tcl.resolve_key(", src)
                self.assertIn("Tcl.chord_bindings(", src)

    def test_forks_do_not_rebuild_the_chord_table(self):
        for name in self.FORKS:
            with self.subTest(fork=name):
                self.assertNotIn("hud#startmenu", self._source(name))

    def test_default_key_is_defined_once(self):
        """Any fork carrying its own bare default re-opens the drift this replaced."""
        for name in self.FORKS:
            with self.subTest(fork=name):
                src = self._source(name)
                self.assertNotIn(f'"key_show", "{Tcl.DEFAULT_KEY}"', src)


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
        """``max`` ships no engine (there is no ``maxtk``) — that must read as "nothing
        to install", not as an error, so the launcher stays uniform across hosts."""
        self.assertEqual(Tcl.engine_dists("max"), ())
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
        """Asked outside any DCC. ``[None]`` would be nonsense, and offering ``[max]``
        — a host with no engine — sends the reader to a pip line resolving to nothing."""
        if not Tcl._requires():
            self.skipTest("no installed metadata (source checkout)")
        with mock.patch.object(Tcl, "host", classmethod(lambda cls: None)):
            hint = Tcl.engine_install_hint()
        self.assertNotIn("None", hint)
        self.assertIn("[maya]", hint)
        self.assertIn("[blender]", hint)
        self.assertNotIn("[max]", hint)

    def test_a_host_with_no_engine_gets_no_pip_line_for_it(self):
        """``max`` ships no engine, so ``"tentacletk[max]"`` names an extra that does
        not exist — pip warns and no-ops. The named host must fall through to the same
        "here are the hosts that DO ship one" answer as the hostless call."""
        if not Tcl._requires():
            self.skipTest("no installed metadata (source checkout)")
        hint = Tcl.engine_install_hint("max")
        self.assertNotIn("[max]", hint)
        self.assertIn("[maya]", hint)

    def test_a_source_checkout_keeps_the_named_hosts_pip_line(self):
        """With no metadata EVERY host reads as engine-less. Demoting a real Maya user
        onto the hostless branch there would cost the interpreter-specific line and
        still print ``[max]`` via its ``or list(HOSTS)`` fallback."""
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
        with mock.patch.object(
            OptionalPackageManager, "pip_python", staticmethod(lambda: None)
        ), mock.patch.object(sys, "executable", host_exe):
            hint = Tcl.engine_install_hint("maya")
        self.assertNotIn("maya.exe", hint)
        self.assertIn("tentacletk[maya]", hint)

        # (b) uitk unreachable — still must not fall back to sys.executable. Not exotic:
        # pip_python imports ExternalAppHandler, which pulls qtpy, which raises with no
        # Qt binding installed (bare venv / CI).
        with mock.patch.dict(
            sys.modules, {"uitk.managers.optional_package_manager": None}
        ), mock.patch.object(sys, "executable", host_exe):
            hint = Tcl.engine_install_hint("maya")
        self.assertNotIn("maya.exe", hint)
        self.assertIn("tentacletk[maya]", hint)

        # (c) ...but a plain `python*` interpreter IS safe to name, and should be — the
        # fallback is an allowlist, not "anything that isn't a DCC I recognise".
        venv_exe = self._fake_exe("python.exe", "venv", "Scripts")
        with mock.patch.dict(
            sys.modules, {"uitk.managers.optional_package_manager": None}
        ), mock.patch.object(sys, "executable", venv_exe):
            hint = Tcl.engine_install_hint("maya")
        self.assertIn(venv_exe, hint)

    def test_the_hint_fallback_is_an_allowlist_not_a_denylist(self):
        """An unrecognised interpreter name must NOT be named. A denylist ("not one of
        the DCC binaries I know") would print the host binary of any DCC whose probe
        module failed to import — the exact command that hangs the session."""
        with mock.patch.dict(
            sys.modules, {"uitk.managers.optional_package_manager": None}
        ), mock.patch.object(
            sys, "executable", self._fake_exe("host-app.exe", "Some", "Unknown")
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
        for extra in self._pyproject().get("optional-dependencies", {}):
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
            if name == "tentacle.tcl_maya":
                raise error
            return real(name)

        with mock.patch.object(
            Tcl, "engine_dists", classmethod(lambda cls, host: ("mayatk",))
        ), mock.patch.object(tcl_module.importlib, "import_module", fake):
            yield

    def _import_maya_entry(self):
        """Import the Maya entry the way ``_launch_maya`` does, bypassing the package
        attribute so the patched importer is the thing that answers."""
        import tentacle

        with mock.patch.dict(tentacle.__dict__, {}, clear=False):
            tentacle.__dict__.pop("tcl_maya", None)
            return Tcl._import_entry("maya", "tentacle.tcl_maya", "TclMaya")

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


class TestEntryForksRouteThroughTheGuard(unittest.TestCase):
    """Each ``_launch_*`` imports its entry through ``_import_entry``.

    By source: a fork that re-inlines ``from tentacle.tcl_maya import ...`` loses the
    missing-engine diagnostic silently — nothing fails, the user just gets a raw
    ModuleNotFoundError with no fix in it.
    """

    def test_every_launcher_uses_the_guarded_import(self):
        source = (PKG / "tcl.py").read_text(encoding="utf-8")
        for host in ("maya", "blender", "max"):
            with self.subTest(host=host):
                body = source.split(f"def _launch_{host}")[1].split("\n    @")[0]
                self.assertIn("_import_entry(", body)
                self.assertNotIn("from tentacle.tcl_", body)
                self.assertNotIn("from tentacle import tcl_", body)


if __name__ == "__main__":
    unittest.main()
