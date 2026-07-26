#!/usr/bin/python
# coding=utf-8
"""Regression tests for the preferences slots.

Mostly ``slots.maya.preferences`` (Maya unit/autosave widget wiring), plus the
per-DCC panel labelling, which spans Maya *and* Blender — see
``TestAppPreferencesLabels``. The units worth pinning at this layer:

- cmb001: sets cmds.currentUnit(linear=...) from widget.currentData(),
  lowercased — case drift would silently break the option.
- cmb002: sets cmds.currentUnit(time=...) — pin the unit name forwarded.

- cmb003: app-style / theme selector. Its slot forwards the picked template
  (widget.currentData()) to mtk.StyleSetter.apply_template — pin that wiring.

(A prior b002 "Autosave Delete All" handler was removed 2026-07-02 as dead code;
b002 was briefly reused 2026-07-04 for a "Match Style" push-button, then that was
replaced the same day by the cmb003 combo — a theme selector mirroring the app's
native theme dropdown. See Preferences.cmb003 here and in slots/blender/preferences.py.)
"""
import ast
import os
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")  # before any widget is built

from qtpy import QtWidgets  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
UI_DIR = ROOT / "tentacle" / "ui"
SLOTS_DIR = ROOT / "tentacle" / "slots"

try:
    import maya.cmds as cmds
    from tentacle.slots.maya import preferences as preferences_module

    _MAYA_AVAILABLE = True
except ImportError:
    cmds = None
    preferences_module = None
    _MAYA_AVAILABLE = False


def _can_create_widgets() -> bool:
    """False under mayapy.standalone / maya -batch: Maya's non-GUI Qt stub hard-crashes
    on QWidget construction (exit 9, no traceback) — the offscreen QPA above does not
    help there. Same discriminator as test_slots_base / test_overlay_safety."""
    try:
        import maya.cmds as _cmds
    except ImportError:
        return True
    try:
        return not bool(_cmds.about(batch=True))
    except Exception:
        return False


class _FakeWidget:
    def __init__(self, current_data):
        self._d = current_data

    def currentData(self):
        return self._d


@unittest.skipUnless(_MAYA_AVAILABLE, "Requires maya.cmds")
class TestCmb001SetLinearUnit(unittest.TestCase):
    """cmb001 forwards widget.currentData().lower() to cmds.currentUnit."""

    def setUp(self):
        cmds.file(new=True, force=True)
        self.instance = preferences_module.Preferences.__new__(
            preferences_module.Preferences
        )
        self._orig = cmds.currentUnit
        self.calls = []
        cmds.currentUnit = lambda **kw: (
            self.calls.append(kw) or None
        )

    def tearDown(self):
        cmds.currentUnit = self._orig
        cmds.file(new=True, force=True)

    def test_lowercases_unit_value(self):
        """The unit name is lowercased before forwarding (cmds expects lc)."""
        self.instance.cmb001(0, _FakeWidget("Meter"))
        self.assertEqual(self.calls, [{"linear": "meter"}])

    def test_known_unit_name_forwarded(self):
        for unit in ("millimeter", "centimeter", "meter", "kilometer", "inch"):
            self.calls.clear()
            self.instance.cmb001(0, _FakeWidget(unit))
            self.assertEqual(self.calls, [{"linear": unit}])


@unittest.skipUnless(_MAYA_AVAILABLE, "Requires maya.cmds")
class TestCmb002SetTimeUnit(unittest.TestCase):
    """cmb002 sets cmds.currentUnit(time=...) from widget.currentData()."""

    def setUp(self):
        cmds.file(new=True, force=True)
        self.instance = preferences_module.Preferences.__new__(
            preferences_module.Preferences
        )
        self._orig = cmds.currentUnit
        self.calls = []
        cmds.currentUnit = lambda **kw: self.calls.append(kw)

    def tearDown(self):
        cmds.currentUnit = self._orig
        cmds.file(new=True, force=True)

    def test_film_fps_forwarded(self):
        """Time mode names (game/film/pal/ntsc/show/palf/ntscf) flow through."""
        self.instance.cmb002(0, _FakeWidget("film"))
        self.assertEqual(self.calls, [{"time": "film"}])

    def test_ntsc_fps_forwarded(self):
        self.instance.cmb002(0, _FakeWidget("ntsc"))
        self.assertEqual(self.calls, [{"time": "ntsc"}])


class _FakeCombo:
    """Minimal stand-in for the uitk ComboBox: records add()/setCurrentIndex and returns a
    chosen currentData(), so cmb003_init/cmb003 can be exercised without a real widget.

    Faithful to the real ComboBox contract that tripped up the first draft: ``.items`` returns the
    item DATA values (``itemData`` when set), NOT the display labels — so the slot must index by a
    template's token, not its display name."""

    def __init__(self, current_data=None):
        self.is_initialized = False
        self.items = []
        self._current_data = current_data
        self.current_index = None

    def add(self, mapping):
        self.items = list(mapping.values())  # data values, matching the real ComboBox.items

    def setCurrentIndex(self, i):
        self.current_index = i

    def currentData(self):
        return self._current_data


@unittest.skipUnless(_MAYA_AVAILABLE, "Requires maya.cmds")
class TestCmb003StyleSelector(unittest.TestCase):
    """cmb003 is the app-style selector. Its init just populates from
    mtk.StyleSetter.list_templates() (no backup/auto-select — removed 2026-07-05, see the mayatk
    CHANGELOG); picking an entry forwards its token to apply_template. Both are mocked here so the
    wiring is pinned without touching real Maya color prefs."""

    def setUp(self):
        cmds.file(new=True, force=True)
        self.instance = preferences_module.Preferences.__new__(
            preferences_module.Preferences
        )

    def tearDown(self):
        cmds.file(new=True, force=True)

    def test_init_populates_from_list_templates(self):
        import mayatk as mtk

        # Tokens deliberately DIFFER from display names (as Blender's real filepath tokens do) so
        # this pins that .items holds tokens, not labels, even though nothing gets auto-selected.
        orig_list = mtk.StyleSetter.list_templates
        mtk.StyleSetter.list_templates = staticmethod(lambda: {"Maya": "tok_maya", "Blender": "tok_blender"})
        try:
            widget = _FakeCombo()
            self.instance.cmb003_init(widget)
        finally:
            mtk.StyleSetter.list_templates = orig_list
        self.assertEqual(widget.items, ["tok_maya", "tok_blender"])  # .items are DATA tokens
        self.assertIsNone(widget.current_index)  # no auto-select — mirrors the native dropdown

    def test_select_forwards_token_to_apply_template(self):
        import mayatk as mtk

        calls = []
        orig = mtk.StyleSetter.apply_template
        mtk.StyleSetter.apply_template = staticmethod(lambda token, **kw: calls.append(token))
        try:
            self.instance.cmb003(1, _FakeCombo(current_data="Blender"))
        finally:
            mtk.StyleSetter.apply_template = orig
        self.assertEqual(calls, ["Blender"])


class _StubMarkingMenu:
    """The two hosted-theme properties ``PreferencesThemeMixin`` drives."""

    def __init__(self):
        self.menu_theme = "dark"
        self.window_theme = "dark"


class TestPreferencesThemeMixin(unittest.TestCase):
    """cmb004 / cmb005 expose uitk's two previously hard-pinned window themes.

    DCC-agnostic by construction — the mixin only touches
    ``sb.handlers.marking_menu`` and ``uitk.StyleSheet`` — so this runs without
    Maya or Blender, and covers the slots both DCCs inherit.

    Uses the REAL uitk ComboBox: the mixin's contract is a label→token map
    written with ``add()`` and read back with ``currentData()``/
    ``setCurrentText()``, and only the real widget pins that round-trip
    (``items`` hold data tokens, not the display labels).
    """

    @classmethod
    def setUpClass(cls):
        try:
            from uitk.widgets.comboBox import ComboBox  # noqa: F401
        except ImportError as error:
            raise unittest.SkipTest(f"uitk unavailable: {error}")
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def setUp(self):
        import types

        from tentacle.slots.preferences_theme_mixin import PreferencesThemeMixin

        self.menu = _StubMarkingMenu()
        self.slots = PreferencesThemeMixin()
        self.slots.sb = types.SimpleNamespace(
            handlers=types.SimpleNamespace(marking_menu=self.menu)
        )

    def _combo(self):
        from uitk.widgets.comboBox import ComboBox

        widget = ComboBox()
        widget.is_initialized = False
        return widget

    def test_labels_are_titled_tokens(self):
        """Hyphenated tokens get a readable label but keep their token data."""
        self.assertEqual(
            self.slots._theme_items().get("High Contrast"), "high-contrast"
        )

    def test_items_cover_every_registered_theme(self):
        from uitk.themes.style_sheet import StyleSheet

        self.assertEqual(
            sorted(self.slots._theme_items().values()), sorted(StyleSheet.themes)
        )

    def test_cmb004_init_selects_the_live_menu_theme(self):
        self.menu.menu_theme = "high-contrast"
        widget = self._combo()
        self.slots.cmb004_init(widget)
        self.assertEqual(widget.currentData(), "high-contrast")

    def test_cmb005_init_selects_the_live_window_theme(self):
        self.menu.window_theme = "light"
        widget = self._combo()
        self.slots.cmb005_init(widget)
        self.assertEqual(widget.currentData(), "light")

    def test_cmb004_writes_menu_theme_only(self):
        widget = self._combo()
        self.slots.cmb004_init(widget)
        widget.setCurrentText("Light")
        self.slots.cmb004(widget.currentIndex(), widget)
        self.assertEqual(self.menu.menu_theme, "light")
        self.assertEqual(self.menu.window_theme, "dark")

    def test_cmb005_writes_window_theme_only(self):
        widget = self._combo()
        self.slots.cmb005_init(widget)
        widget.setCurrentText("High Contrast")
        self.slots.cmb005(widget.currentIndex(), widget)
        self.assertEqual(self.menu.window_theme, "high-contrast")
        self.assertEqual(self.menu.menu_theme, "dark")

    def test_cmb004_ignores_header_row_selection(self):
        """A change fired while the header row is current (currentData()==None)
        must be a no-op, not a crash. The combos carry a header, so the live
        menu's change signal can fire with no real item selected."""
        widget = self._combo()
        self.slots.cmb004_init(widget)
        widget.setCurrentIndex(-1)
        self.assertIsNone(widget.currentData())
        self.slots.cmb004(widget.currentIndex(), widget)  # must not raise
        self.assertEqual(self.menu.menu_theme, "dark")

    def test_cmb005_ignores_header_row_selection(self):
        widget = self._combo()
        self.slots.cmb005_init(widget)
        widget.setCurrentIndex(-1)
        self.assertIsNone(widget.currentData())
        self.slots.cmb005(widget.currentIndex(), widget)  # must not raise
        self.assertEqual(self.menu.window_theme, "dark")

    def test_init_repopulates_only_once(self):
        """``*_init`` runs on every panel show; only the first fills the list."""
        widget = self._combo()
        self.slots.cmb004_init(widget)
        count = widget.count()
        widget.is_initialized = True
        self.menu.menu_theme = "light"
        self.slots.cmb004_init(widget)
        self.assertEqual(widget.count(), count)
        self.assertEqual(widget.currentData(), "light")


class TestPreferencesSlotsInheritThemeMixin(unittest.TestCase):
    """Both DCCs' ``Preferences`` must list ``PreferencesThemeMixin`` as a base.

    Read via AST so neither DCC needs to be importable — dropping the mixin from
    one host silently removes its two theme combos from that panel.
    """

    def _bases(self, dcc):
        tree = ast.parse((SLOTS_DIR / dcc / "preferences.py").read_text(encoding="utf-8"))
        cls = next(
            c
            for c in ast.walk(tree)
            if isinstance(c, ast.ClassDef) and c.name == "Preferences"
        )
        return [b.id for b in cls.bases if isinstance(b, ast.Name)]

    def test_mixin_is_first_base_in_every_dcc(self):
        for dcc in ("maya", "blender"):
            with self.subTest(dcc=dcc):
                bases = self._bases(dcc)
                self.assertIn("PreferencesThemeMixin", bases)
                # Ahead of the SlotsX base so its slots aren't shadowed, and so
                # super().__init__ still reaches the DCC base unchanged.
                self.assertEqual(bases[0], "PreferencesThemeMixin")


def _init_label_writes(dcc):
    """{target: label} for the ``setTitle``/``setText`` string-literal calls in this
    DCC's ``Preferences.__init__`` — e.g. ``{"ui.parent_app.setTitle": "Maya Preferences"}``.

    Read via AST rather than substring-matching the source, so reformatting the call
    (black wrapping it, a different quote style) can't fake a pass or a failure.
    """
    tree = ast.parse((SLOTS_DIR / dcc / "preferences.py").read_text(encoding="utf-8"))
    init = next(
        (
            fn
            for cls in ast.walk(tree)
            if isinstance(cls, ast.ClassDef) and cls.name == "Preferences"
            for fn in cls.body
            if isinstance(fn, ast.FunctionDef) and fn.name == "__init__"
        ),
        None,
    )
    writes = {}
    for node in ast.walk(init) if init else ():
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr in ("setTitle", "setText")
            and len(node.args) == 1
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
        ):
            # ``self.ui.parent_app.setTitle`` -> "ui.parent_app.setTitle"
            target = ast.unparse(node.func).removeprefix("self.")
            writes[target] = node.args[0].value
    return writes


class TestAppPreferencesLabels(unittest.TestCase):
    """Each DCC names the shared preferences panel after itself.

    The .ui pair is shared by every host, so it ships a literal ``<app> Preferences``
    token that each DCC's slot ``__init__`` overwrites with its own name. That makes
    the two target objectNames **load-bearing**: rename ``parent_app`` or ``b010`` in
    Designer and ``__init__`` raises AttributeError, taking down the whole preferences
    panel rather than just mislabelling it. Both halves are pinned here — that the
    widgets resolve from the real .ui, and that every DCC writes to them.
    """

    EXPECTED = {
        "maya": "Maya Preferences",
        "blender": "Blender Preferences",
    }
    TARGETS = ("ui.parent_app.setTitle", "submenu.b010.setText")

    def test_each_dcc_slot_names_itself_on_both_targets(self):
        """Every DCC shipping a preferences slot labels the group and the submenu button."""
        for dcc, label in self.EXPECTED.items():
            with self.subTest(dcc=dcc):
                self.assertEqual(
                    _init_label_writes(dcc), {t: label for t in self.TARGETS}
                )

    def test_every_dcc_with_a_preferences_slot_is_covered(self):
        """A DCC added later must name itself too — this list is the whole set."""
        shipped = {p.parent.name for p in SLOTS_DIR.glob("*/preferences.py")}
        self.assertEqual(
            shipped,
            set(self.EXPECTED),
            "slots/<dcc>/preferences.py loads the shared .ui, whose '<app>' token only "
            "gets filled in by the slot — add the new DCC to EXPECTED and to its slot.",
        )


@unittest.skipUnless(
    _can_create_widgets(),
    "Needs real-widget Qt (skipped under mayapy.standalone's non-GUI stub).",
)
class TestAppPreferencesLabelTargetsResolve(unittest.TestCase):
    """The widgets ``Preferences.__init__`` labels resolve from the real .ui.

    Loads the shipped .ui pair through a real Switchboard — no Maya/Blender needed —
    and reproduces the access exactly as ``__init__`` makes it: **before any show**.
    That timing is the point. ``MainWindow.register_children`` only binds child widgets
    as attributes on ``showEvent``, so these lookups land on the ``__getattr__``
    findChild fallback; a test that showed the window first would pass while the real
    slot raised AttributeError.
    """

    @classmethod
    def setUpClass(cls):
        try:
            from uitk import Switchboard
        except ImportError as error:
            raise unittest.SkipTest(f"uitk unavailable: {error}")
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        cls.sb = Switchboard(ui_source=str(UI_DIR))

    def test_labels_reach_the_widgets_unshown(self):
        """Each target resolves unshown and takes the DCC's label."""
        for dcc, label in TestAppPreferencesLabels.EXPECTED.items():
            with self.subTest(dcc=dcc):
                ui = self.sb.loaded_ui.preferences
                submenu = self.sb.loaded_ui.preferences_submenu
                self.assertFalse(ui.isVisible(), "must exercise the pre-show path")

                ui.parent_app.setTitle(label)
                submenu.b010.setText(label)

                self.assertEqual(ui.parent_app.title(), label)
                self.assertEqual(submenu.b010.text(), label)

    def test_in_panel_button_keeps_its_own_label(self):
        """Only the group is app-named in-panel — its b010 stays plain, so the panel
        doesn't read 'Maya Preferences > Maya Preferences'."""
        self.assertEqual(self.sb.loaded_ui.preferences.b010.text(), "Preferences")


if __name__ == "__main__":
    unittest.main()
