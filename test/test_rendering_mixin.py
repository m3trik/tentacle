#!/usr/bin/python
# coding=utf-8
"""Tests for the shared rendering-panel behavior (DCC-agnostic).

``tentacle/slots/_rendering.py`` holds ``RenderingMixin`` — the WebXR Preview
option box (``tb002``) and its push flow, shared by both DCC Rendering slots.
The mixin imports nothing DCC-specific (the engine arrives as a parameter), so
the whole flow runs here with fakes: no ``maya.cmds`` / ``bpy``, no Qt.

What is worth pinning is the wiring, because every way it can be wrong is
SILENT. A combo built without item data returns ``None`` from
``currentData()``, which the push reads as ``"selected"`` — so the two widening
scopes would simply never fire, on a panel that still looks correct. A row
whose objectName drifts from the one the push reads raises nothing until a
user clicks. And the scope vocabulary is shared with every other hand-off
bridge (``uitk.bridge.Parameters.scope_spec``); this panel had already forked
its own two-entry copy once.
"""

import ast
import contextlib
import os
import sys
import unittest
from pathlib import Path
from unittest import mock

from uitk.bridge import Parameters

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tentacle.slots._rendering import RenderingMixin  # noqa: E402

MAYA_FILE = ROOT / "tentacle" / "slots" / "maya" / "rendering.py"
BLENDER_FILE = ROOT / "tentacle" / "slots" / "blender" / "rendering.py"
#: Where a test that needs a real file on disk puts it (repo convention).
TEMP_DIR = Path(__file__).resolve().parent / "temp_tests"

#: Shared methods that must live ONLY on the mixin — a fork re-defining one is
#: the drift the shared module exists to remove.
FORK_MUST_NOT_DEFINE = ("webxr_init", "webxr_push")

#: Retired with the Open In Browser row. Never reused for a new control: a new
#: row under this name would silently inherit the old checkbox's stored value.
RETIRED_OBJECT_NAMES = ("chk062",)


class _FakeSignal:
    """A signal that actually delivers, so "nothing is wired to it" is testable.

    The scope combo emits both of Qt's, and the panel connects NEITHER: the
    External GLB browse dialog belongs to the push. A fake that swallowed
    ``connect`` -- or that never emitted -- would let someone re-wire the
    dialog onto the combo and still pass the tests that exist to forbid it.
    """

    def __init__(self):
        self.slots = []

    def connect(self, slot):
        self.slots.append(slot)

    def emit(self, *args):
        for slot in list(self.slots):
            slot(*args)


class _FakeCombo:
    """A ``(label, data)`` combo, populated the way the mixin populates one."""

    def __init__(self, **kwargs):
        self.items = []
        self.index = 0
        self.tooltip = kwargs.get("setToolTip", "")
        # Set as a plain attribute by ``Menu.set_attributes``; the panel asks
        # for it so a restored External index cannot fire the browse dialog.
        self.currentIndexChanged = _FakeSignal()
        # Qt emits this ONLY for a pick from the popup -- never for a
        # programmatic ``setCurrentIndex``, which is what a QSettings restore
        # does. Kept apart here so a test can drive a real user gesture
        # (``pick``) and a restore (``setCurrentIndex``) as the different
        # things they are.
        self.activated = _FakeSignal()

    def addItem(self, label, data):
        self.items.append((label, data))

    def setCurrentIndex(self, index):
        """Programmatic, as a restore or a fallback is -- ``activated`` stays
        silent."""
        self.index = index
        # Emitted like the real widget's: the handler re-enters through this on
        # a cancelled browse, and a fake that stayed silent would hide it.
        self.currentIndexChanged.emit(index)

    def pick(self, index):
        """A person choosing *index* from the popup: both signals, in Qt's
        order.

        Qt emits ``activated`` even when the pick does not change the index,
        so this does too -- a re-pick is a real gesture, and it must not reach
        a dialog either.
        """
        if index != self.index:
            self.setCurrentIndex(index)
        self.activated.emit(index)

    def currentIndex(self):
        return self.index

    def currentText(self):
        return self.items[self.index][0]

    def currentData(self):
        # Deliberately NOT a `.get`-style shrug: the real QComboBox returns None
        # for an item added without data, and that None is the failure this
        # suite exists to catch, so the fake must be able to produce it too.
        return self.items[self.index][1]


class _FakeCheckBox:
    def __init__(self, **kwargs):
        self.text = kwargs.get("setText", "")
        self.checked = bool(kwargs.get("setChecked", False))
        self.tooltip = kwargs.get("setToolTip", "")

    def isChecked(self):
        return self.checked

    def setChecked(self, value):
        self.checked = bool(value)


class _FakeMenu:
    """An option-box menu that builds real stand-ins from ``add()``.

    Widgets land as attributes under their objectName, which is how the push
    reads them — so a row the init names one thing and the push reads by
    another fails here as an AttributeError rather than at a user's click.
    """

    FACTORIES = {"QComboBox": _FakeCombo, "QCheckBox": _FakeCheckBox}

    def __init__(self):
        self.title = ""
        self.order = []

    def setTitle(self, title):
        self.title = title

    def add(self, kind, **kwargs):
        widget = self.FACTORIES[kind](**kwargs)
        name = kwargs["setObjectName"]
        setattr(self, name, widget)
        self.order.append(name)
        return widget


#: ``message_box`` drops any button whose name is not a Qt standard one,
#: leaving a Cancel-only box — silently. The consent dialog this panel shows
#: for a missing ``toktx`` reads its answer back BY NAME, so a dropped button
#: is a prompt that can only be declined. Same guard as ``test_scene_mixin``.
QT_STANDARD_BUTTONS = frozenset(
    {
        "Ok",
        "Open",
        "Save",
        "Cancel",
        "Close",
        "Discard",
        "Apply",
        "Reset",
        "RestoreDefaults",
        "Help",
        "SaveAll",
        "Yes",
        "YesToAll",
        "No",
        "NoToAll",
        "Abort",
        "Retry",
        "Ignore",
    }
)


class _FakeSwitchboard:
    def __init__(self, click=None, browse=None):
        self.click = click  # the button the fake user presses
        # What the fake user picks in the browse dialog, one answer per call;
        # a falsy entry (or an exhausted queue) is a cancel.
        self.browse = list(browse or [])
        self.browsed = []  # the kwargs each browse was opened with
        self.messages = []

    def file_dialog(self, **kwargs):
        self.browsed.append(kwargs)
        return self.browse.pop(0) if self.browse else None

    def message_box(self, text, *buttons, **kwargs):
        unknown = set(buttons) - QT_STANDARD_BUTTONS
        assert not unknown, f"non-standard message_box buttons: {unknown}"
        self.messages.append(text)
        return self.click if buttons else None

    def __getattr__(self, name):
        """Resolve unknown names against ``uitk``, as the real Switchboard does.

        The mixin reaches uitk through ``self.sb`` (a slot module may not import
        it -- ``test_dcc_invariants``.TestSlotImportDiscipline), so a fake that
        stopped at ``message_box`` would make every such lookup an
        ``AttributeError`` and test a panel the real one does not resemble.
        Gated on ``uitk.__all__`` for the same reason the real resolver is: a
        typo must fail here, not silently reach some private module attribute.
        """
        if name.startswith("_"):
            raise AttributeError(name)
        import uitk

        if name not in (uitk.__all__ or ()):
            raise AttributeError(f"{name!r} is not a public uitk symbol")
        return getattr(uitk, name)


class _FakeBridge:
    """A ``PreviewBridge`` stand-in recording exactly what the panel asked for."""

    #: What each scope resolves to, so a push can be traced back to its scope.
    RESOLUTIONS = {
        "selected": ["SEL"],
        "all": ["ROOT_A", "ROOT_B"],
        "visible": ["ROOT_A"],
    }

    instances = 0
    #: ``None`` is a MEANINGFUL result here (the bridge's own failure signal),
    #: so "argument not given" needs its own value.
    _UNSET = object()

    def __init__(self, resolutions=None, result=_UNSET, publish_error=None):
        type(self).instances += 1
        self.published = []
        self.publish_error = publish_error
        self.resolutions = (
            dict(self.RESOLUTIONS) if resolutions is None else dict(resolutions)
        )
        self.result = (
            {"version": 3, "url": "http://127.0.0.1:8118/"}
            if result is self._UNSET
            else result
        )
        self.pushes = []

    def scope_objects(self, scope="selected"):
        return list(self.resolutions.get(scope, self.resolutions["selected"]))

    def push(self, **kwargs):
        self.pushes.append(kwargs)
        return self.result

    def publish_file(self, path, **kwargs):
        if self.publish_error is not None:
            raise self.publish_error
        self.published.append((path, kwargs))
        return {"version": 4, "url": "http://127.0.0.1:8118/", "source": path}

    @staticmethod
    def sidecar_summary(result):
        return "Scene sidecar: base_color 2/2."

    @staticmethod
    def lightmap_summary(result):
        return ""


class _Host(RenderingMixin):
    """Minimal host: the mixin needs only ``self.sb`` and its own state."""

    def __init__(self, browse=None):
        self.sb = _FakeSwitchboard(browse=browse)


class _Widget:
    def __init__(self, menu):
        self.option_box = type("_OptionBox", (), {"menu": menu})()


def _built(host=None):
    """Run the real ``webxr_init`` and hand back ``(host, widget, menu)``."""
    host = host or _Host()
    menu = _FakeMenu()
    widget = _Widget(menu)
    host.webxr_init(widget, sidecar_tooltip="per-DCC text")
    return host, widget, menu


class TestOptionBox(unittest.TestCase):
    """What ``webxr_init`` builds."""

    def test_scope_is_the_shared_spec_not_a_local_copy(self):
        """The whole point of reading the spec: this panel cannot fork it again.

        The spec's entries lead, in the spec's own order; only External GLB --
        a source no other hand-off could honour -- follows them.
        """
        _, _, menu = _built()
        shared = list(Parameters.scope_spec().choices)
        self.assertEqual(menu.cmb061.items[: len(shared)], shared)
        # And the third entry is the one the rewrite was for.
        self.assertIn(("Visible Only", "visible"), menu.cmb061.items)

    def test_external_is_the_only_entry_the_panel_adds(self):
        """It stays out of ``scope_spec``: every other bridge would inherit a
        choice it has no way to honour."""
        _, _, menu = _built()
        shared = {data for _, data in Parameters.scope_spec().choices}
        extra = [data for _, data in menu.cmb061.items if data not in shared]
        self.assertEqual(extra, [RenderingMixin.WEBXR_EXTERNAL_SCOPE])

    def test_scope_order_keeps_a_stored_index_meaning_what_it_meant(self):
        """These combos persist by INDEX, so every addition has to be
        append-only.

        Someone with 'Entire Scene' stored has index 1; if Visible Only (or
        External GLB after it) had been inserted anywhere but last, their next
        session would silently push a different scope.
        """
        _, _, menu = _built()
        self.assertEqual(
            [data for _, data in menu.cmb061.items[:2]], ["selected", "all"]
        )
        self.assertEqual(menu.cmb061.items[2][1], "visible")
        self.assertEqual(menu.cmb061.items[-1][1], RenderingMixin.WEBXR_EXTERNAL_SCOPE)

    def test_every_combo_item_carries_data(self):
        """An item added without data reads back None, which the push floors to
        'selected' / the deliverer's default — a silent loss of the control."""
        _, _, menu = _built()
        for name in ("cmb061", "cmb062"):
            items = getattr(menu, name).items
            # An empty combo would pass the loop below vacuously, which is the
            # same silent shape the test is about.
            self.assertTrue(items, f"{name} was built with no items at all")
            for label, data in items:
                self.assertIsNotNone(data, f"{name}: {label!r} has no item data")

    def test_defaults_are_the_prior_behavior(self):
        _, _, menu = _built()
        self.assertEqual(menu.cmb061.currentData(), "selected")
        self.assertEqual(menu.cmb062.currentData(), "WEBP")
        self.assertTrue(menu.chk061.isChecked())  # Include Textures
        self.assertTrue(menu.chk063.isChecked())  # Scene Sidecar
        self.assertFalse(menu.chk064.isChecked())  # Include Animation

    def test_the_retired_open_in_browser_row_is_gone(self):
        _, _, menu = _built()
        for name in RETIRED_OBJECT_NAMES:
            self.assertNotIn(name, menu.order)

    def test_every_script_row_names_a_packaged_script(self):
        """A checkbox naming a script pythontk does not serve makes the page's
        import 404 — and the only trace is a console warning nobody is watching
        inside a headset."""
        from pythontk import PreviewServer

        for _name, script, _label, _tip in RenderingMixin.WEBXR_SCRIPTS:
            self.assertIn(script, PreviewServer.SCRIPTS)

    def test_every_row_carries_a_tooltip(self):
        _, _, menu = _built()
        for name in menu.order:
            self.assertTrue(getattr(menu, name).tooltip, f"{name} has no tooltip")


@contextlib.contextmanager
def _ktx2_encoder(installed=None, error=None, calls=None):
    """Stand in for ``ImgUtils.ensure_ktx2_encoder``, whatever this machine has.

    The install branch only runs where ``toktx`` is absent, so a developer with
    KTX-Software installed would otherwise never execute it — the environment
    has to be stated rather than inherited. *installed* is the primitive's own
    return contract: the path it installed, or None when one was already there.
    """
    import pythontk as ptk

    def fake(**kwargs):
        if calls is not None:
            calls.append(kwargs)
        if error is not None:
            raise error
        return installed

    with mock.patch.object(ptk.ImgUtils, "ensure_ktx2_encoder", fake):
        yield


class TestTextureToolGate(unittest.TestCase):
    """The KTX2 row must not be able to dead-end in an install URL.

    Its sibling control on the Scene Exporter offers the managed KTX-Software
    install; a preview push that merely raised would be the same environment
    answered two different ways by two panels.
    """

    def setUp(self):
        self.host = _Host()

    def test_webp_asks_nothing(self):
        """WebP needs no external tool, so probing for one would ask a question
        about a control the user never touched."""
        calls = []
        with _ktx2_encoder(calls=calls):
            self.assertTrue(self.host._webxr_texture_tool_ready("WEBP"))
        self.assertEqual(calls, [])
        self.assertEqual(self.host.sb.messages, [])

    def test_ktx2_hands_the_primitive_the_panel_s_own_consent(self):
        """The dialog is what makes this an OFFER rather than an abort."""
        calls = []
        with _ktx2_encoder(calls=calls):
            self.assertTrue(self.host._webxr_texture_tool_ready("KTX2"))
        self.assertEqual(len(calls), 1)
        self.assertTrue(callable(calls[0].get("prompt")), "consent must be the panel's")

    def test_the_consent_callable_reads_the_modal_back_correctly(self):
        """Drives the prompt the primitive would call. ``message_box`` silently
        DROPS a non-standard button name, so a typo there yields a dialog whose
        answer can never equal the accept value — a prompt only ever declined,
        with nothing raised to say so. The fake asserts the names; this asserts
        both answers map through."""
        calls = []
        for click, expected in (("Yes", True), ("No", False)):
            with self.subTest(click=click):
                host = _Host()
                host.sb.click = click
                del calls[:]
                with _ktx2_encoder(calls=calls):
                    host._webxr_texture_tool_ready("KTX2")
                self.assertIs(calls[0]["prompt"]("Download KTX-Software?"), expected)

    def test_an_accepted_install_reports_the_binary_it_landed(self):
        """Not just 'installed' — the path, so the user can see WHAT answered."""
        with _ktx2_encoder(installed="C:/ktx/bin/toktx.exe"):
            self.assertTrue(self.host._webxr_texture_tool_ready("KTX2"))
        self.assertIn("C:/ktx/bin/toktx.exe", self.host.sb.messages[0])

    def test_an_already_installed_toktx_says_nothing(self):
        """``None`` is the primitive's 'nothing to install' — no notice, no
        dialog, the push just runs."""
        with _ktx2_encoder(installed=None):
            self.assertTrue(self.host._webxr_texture_tool_ready("KTX2"))
        self.assertEqual(self.host.sb.messages, [])

    def test_a_declined_or_failed_install_stops_the_push_with_the_fix(self):
        """``FileNotFoundError`` from the primitive is the fix-shaped message
        naming the manual install, so it IS what the user is shown."""
        error = FileNotFoundError("KTX2 encoding requires 'toktx'. Install it from …")
        with _ktx2_encoder(error=error):
            self.assertFalse(self.host._webxr_texture_tool_ready("KTX2"))
        self.assertIn("toktx", self.host.sb.messages[0])


class TestPush(unittest.TestCase):
    """What ``webxr_push`` sends."""

    def _push(self, menu_setup=None, **kwargs):
        host, widget, menu = _built()
        if menu_setup:
            menu_setup(menu)
        # Under the encoder stub, always: selecting KTX2 sends the push through
        # the tool gate, which without this asks the MACHINE whether toktx is
        # installed. That passed on a workstation that has it and failed on CI
        # that does not -- the gate returned False, the push never happened,
        # and the assertion died on an empty list two frames away from the
        # cause. These tests are about what `push` is SENT; which encoder the
        # host owns is TestTextureToolGate's subject, and it states it too.
        with _ktx2_encoder():
            host.webxr_push(
                widget, engine=_FakeBridge, log_hint="script editor", **kwargs
            )
        return host, menu

    def test_scope_reaches_the_bridge_as_objects_and_as_a_param(self):
        """Both halves matter: the objects are what is exported, and SCOPE is
        what tells ``BlenderExportMixin`` not to descend into hidden children."""
        for index, scope in enumerate(("selected", "all", "visible")):
            with self.subTest(scope=scope):
                host, _ = self._push(lambda m, i=index: m.cmb061.setCurrentIndex(i))
                sent = host._webxr.pushes[0]
                self.assertEqual(sent["scope"], scope)
                self.assertEqual(sent["objects"], _FakeBridge.RESOLUTIONS[scope])

    def test_texture_format_reaches_the_deliverer(self):
        host, _ = self._push(lambda m: m.cmb062.setCurrentIndex(1))
        self.assertEqual(host._webxr.pushes[0]["texture_format"], "KTX2")

    def test_scripts_are_an_explicit_list_even_when_none_are_ticked(self):
        """``None`` means 'leave the server's set alone', so an unticked box
        could never turn a script back off."""
        host, _ = self._push()
        self.assertEqual(host._webxr.pushes[0]["scripts"], [])

    def test_ticked_scripts_are_sent_by_their_registered_name(self):
        def tick_all(menu):
            for name, _script, _label, _tip in RenderingMixin.WEBXR_SCRIPTS:
                getattr(menu, name).setChecked(True)

        host, _ = self._push(tick_all)
        self.assertEqual(
            host._webxr.pushes[0]["scripts"],
            [script for _n, script, _l, _t in RenderingMixin.WEBXR_SCRIPTS],
        )

    def test_open_browser_is_always_auto(self):
        """The removed checkbox's behavior, now fixed: a page that can pick the
        version up is reused rather than having focus stolen from the DCC."""
        host, _ = self._push()
        self.assertEqual(host._webxr.pushes[0]["open_browser"], "auto")

    def test_export_params_travel_with_their_checkbox(self):
        def flip(menu):
            menu.chk061.setChecked(False)
            menu.chk063.setChecked(False)
            menu.chk064.setChecked(True)

        host, _ = self._push(flip)
        sent = host._webxr.pushes[0]
        self.assertIs(sent["EMBED_TEXTURES"], False)
        self.assertIs(sent["SCENE_SIDECAR"], False)
        self.assertIs(sent["INCLUDE_ANIMATION"], True)

    def test_an_empty_scope_is_reported_as_that_scope(self):
        """The reason the panel resolves rather than pushing blind: 'nothing
        selected', 'the scene is empty' and 'the export failed' are three
        different next actions for the user."""
        host, widget, menu = _built()
        menu.cmb061.setCurrentIndex(1)  # Entire Scene
        engine = lambda: _FakeBridge(resolutions={"selected": [], "all": []})  # noqa: E731
        host.webxr_push(widget, engine=engine, log_hint="script editor")

        self.assertEqual(host._webxr.pushes, [], "an empty scope must not push")
        self.assertEqual(len(host.sb.messages), 1)
        message = host.sb.messages[0]
        self.assertIn("scene", message.lower())
        self.assertNotIn("nothing selected", message.lower())

    def test_the_bridge_is_built_once_and_kept(self):
        """The deliverer's server, port and open tab hang off it."""
        host, widget, _ = _built()
        _FakeBridge.instances = 0
        host.webxr_push(widget, engine=_FakeBridge, log_hint="script editor")
        first = host._webxr
        host.webxr_push(widget, engine=_FakeBridge, log_hint="script editor")
        self.assertIs(host._webxr, first)
        self.assertEqual(_FakeBridge.instances, 1)

    def test_a_failed_push_names_where_the_log_is(self):
        host, widget, _ = _built()
        host.webxr_push(
            widget,
            engine=lambda: _FakeBridge(result=None),
            log_hint="script output",
        )
        self.assertIn("script output", host.sb.messages[0])

    def test_a_successful_push_reports_the_url_and_the_summaries(self):
        host, _ = self._push()
        message = host.sb.messages[0]
        self.assertIn("http://127.0.0.1:8118/", message)
        self.assertIn("Scene sidecar", message)


class TestExternalGlb(unittest.TestCase):
    """The External GLB source: asked for at push time, published unconverted.

    Every failure here is silent in the same way the rest of this panel's are.
    A dialog wired to the COMBO fires while the option box is still being
    configured -- and, since a restore replays the stored index as the panel
    draws, greets the next panel open with a file browser nobody asked for. An
    external push that fell through to the export path would quietly re-export
    the scene instead of publishing the file that was picked. And a browse the
    user cancels must read as "no", not as a tool failure.
    """

    EXTERNAL_INDEX = len(Parameters.scope_spec().choices)

    def setUp(self):
        TEMP_DIR.mkdir(parents=True, exist_ok=True)
        self.written = []
        self.GLB = self._write("vendor_chair.glb")
        self.glb = Path(self.GLB)

    def _write(self, name):
        """A GLB-shaped file in the suite's temp dir, cleaned up in teardown."""
        path = TEMP_DIR / name
        path.write_bytes(b"glTF\x02\x00\x00\x00")
        self.written.append(path)
        return str(path)

    def tearDown(self):
        for path in self.written:
            path.unlink(missing_ok=True)

    def _armed(self, browse=None):
        """A panel sitting on External, with *browse* queued for the dialog."""
        host, widget, menu = _built(_Host(browse=browse))
        menu.cmb061.pick(self.EXTERNAL_INDEX)
        return host, widget, menu

    def _push(self, host, widget, engine=None):
        host.webxr_push(widget, engine=engine or _FakeBridge, log_hint="script editor")

    # -- when the dialog appears -------------------------------------------
    def test_choosing_external_asks_nothing(self):
        """The option box is where a run is CONFIGURED. A modal that interrupts
        that is a dialog nobody asked for yet -- the push is what needs the
        file."""
        host, _, _ = self._armed(browse=[self.GLB])
        self.assertEqual(host.sb.browsed, [])

    def test_no_scope_choice_asks_anything(self):
        host, _, menu = _built(_Host(browse=[self.GLB]))
        for index in range(len(menu.cmb061.items)):
            menu.cmb061.pick(index)
        self.assertEqual(host.sb.browsed, [])

    def test_a_restored_external_index_asks_nothing(self):
        """The restore replays the stored index as the panel draws. Nothing is
        wired to the combo, so it cannot reach a dialog by any path."""
        host, _, menu = _built(_Host(browse=[self.GLB]))
        menu.cmb061.setCurrentIndex(self.EXTERNAL_INDEX)
        self.assertEqual(host.sb.browsed, [])

    def test_the_push_is_what_asks(self):
        host, widget, _ = self._armed(browse=[self.GLB])
        self._push(host, widget)
        self.assertEqual(len(host.sb.browsed), 1)
        self.assertEqual(host.sb.browsed[0]["file_types"], ["*.glb"])
        self.assertIs(host.sb.browsed[0]["allow_multiple"], False)

    def test_every_push_asks_again(self):
        """Remembering would save a click and cost the ability to ever choose a
        different file: the combo is already on External, so re-picking it says
        nothing new."""
        second = self._write("other.glb")
        host, widget, _ = self._armed(browse=[self.GLB, second])
        self._push(host, widget)
        self._push(host, widget)
        self.assertEqual(len(host.sb.browsed), 2)
        self.assertEqual(
            [path for path, _kwargs in host._webxr.published], [self.GLB, second]
        )

    def test_the_second_ask_opens_where_the_first_one_landed(self):
        """The folder is the one thing worth carrying over -- re-opening at the
        user's home folder would make them navigate back every push."""
        host, widget, _ = self._armed(browse=[self.GLB, self._write("other.glb")])
        self._push(host, widget)
        self._push(host, widget)
        self.assertEqual(host.sb.browsed[0]["start_dir"], "")
        self.assertEqual(host.sb.browsed[1]["start_dir"], os.path.dirname(self.GLB))

    # -- what the push does with the answer ---------------------------------
    def test_it_publishes_the_chosen_file_unconverted(self):
        host, widget, _ = self._armed(browse=[self.GLB])
        self._push(host, widget)

        self.assertEqual(host._webxr.pushes, [], "an external source must not export")
        self.assertEqual(len(host._webxr.published), 1)
        path, kwargs = host._webxr.published[0]
        self.assertEqual(path, self.GLB)
        self.assertEqual(kwargs["open_browser"], "auto")

    def test_the_viewer_scripts_still_apply(self):
        """They are a property of the PAGE, which is the same page either
        source publishes to."""
        host, widget, menu = self._armed(browse=[self.GLB])
        for name, _script, _label, _tip in RenderingMixin.WEBXR_SCRIPTS:
            getattr(menu, name).setChecked(True)
        self._push(host, widget)
        self.assertEqual(
            host._webxr.published[0][1]["scripts"],
            [script for _n, script, _l, _t in RenderingMixin.WEBXR_SCRIPTS],
        )

    def test_a_cancelled_browse_reports_nothing(self):
        """The user just said no; a failure message would blame the tool."""
        host, widget, _ = self._armed(browse=[])
        self._push(host, widget)
        self.assertEqual(host._webxr.published, [])
        self.assertEqual(host.sb.messages, [])

    def test_a_cancelled_browse_leaves_the_scope_alone(self):
        """Nothing is published and nothing is reset -- the next press of the
        button simply asks again."""
        host, widget, menu = self._armed(browse=[])
        self._push(host, widget)
        self.assertEqual(menu.cmb061.currentData(), RenderingMixin.WEBXR_EXTERNAL_SCOPE)

    def test_a_refused_file_is_reported_with_the_bridge_s_own_reason(self):
        """The bridge's refusals name the fix (the file moved, it is not a
        .glb), so they must not be replaced by 'see the log'."""
        host, widget, _ = self._armed(browse=[self.GLB])
        error = ValueError("the preview needs a binary .glb rather than .gltf")
        self._push(host, widget, engine=lambda: _FakeBridge(publish_error=error))
        self.assertEqual(len(host.sb.messages), 1)
        self.assertIn(".glb", host.sb.messages[0])
        self.assertNotIn("script editor", host.sb.messages[0])

    def test_the_report_names_the_file_not_the_export_summaries(self):
        """'Scene sidecar off' would imply an export skipped something; there
        was no export."""
        host, widget, _ = self._armed(browse=[self.GLB])
        self._push(host, widget)
        message = host.sb.messages[0]
        self.assertIn("http://127.0.0.1:8118/", message)
        self.assertIn("vendor_chair.glb", message)
        self.assertNotIn("Scene sidecar", message)


class TestForksStayThin(unittest.TestCase):
    """AST checks: the forks must not grow their own copy of the shared flow."""

    @staticmethod
    def _methods(path):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        return {
            node.name
            for cls in ast.walk(tree)
            if isinstance(cls, ast.ClassDef)
            for node in cls.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }

    def test_neither_fork_redefines_a_shared_method(self):
        for path in (MAYA_FILE, BLENDER_FILE):
            methods = self._methods(path)
            for name in FORK_MUST_NOT_DEFINE:
                self.assertNotIn(name, methods, f"{path.name} redefines {name}")

    def test_neither_fork_passes_a_selection_hook(self):
        """Scope resolution is the engine's (``PreviewBridge.scope_objects``).
        A fork still passing ``has_selection=`` is a TypeError at click time."""
        for path in (MAYA_FILE, BLENDER_FILE):
            self.assertNotIn("has_selection", path.read_text(encoding="utf-8"))

    def test_both_forks_call_the_shared_flow(self):
        for path in (MAYA_FILE, BLENDER_FILE):
            source = path.read_text(encoding="utf-8")
            self.assertIn("self.webxr_init(", source)
            self.assertIn("self.webxr_push(", source)


if __name__ == "__main__":
    unittest.main()
