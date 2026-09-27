#!/usr/bin/python
# coding=utf-8
"""Regression tests for tentacle.slots.maya.editors.

editors.py's list000 opens every Maya editor through the
mtk.UiUtils.get_editor_types registry. The unit with real conditional logic worth pinning
is b009 (Time & Range) — its 4-way visibility-state matrix decides
which sliders to toggle.
"""
import unittest

from _host import MAYA_AVAILABLE as _MAYA_AVAILABLE, maya_module

cmds = maya_module("maya.cmds")
mel = maya_module("maya.mel")
editors_module = maya_module("tentacle.slots.maya.editors")


@unittest.skipUnless(_MAYA_AVAILABLE, "Requires maya.cmds")
class TestB009TimeAndRange(unittest.TestCase):
    """b009 toggles Time Slider and Range Slider based on current visibility.

    - Both visible: toggle both off (each its own ToggleX).
    - Only TS visible: toggle TS off (only).
    - Only RS visible: toggle RS off (only).
    - Neither visible: toggle both on.
    """

    def setUp(self):
        cmds.file(new=True, force=True)
        self.instance = editors_module.EditorsSlots.__new__(editors_module.EditorsSlots)

        # Mock mel.eval to drive the isUIComponentVisible queries and
        # capture toggle invocations.
        self._orig = mel.eval
        # Per-test, set ts_visible / rs_visible on self before invoking.
        self.ts_visible = False
        self.rs_visible = False
        self.eval_log = []

        def fake_eval(s):
            self.eval_log.append(s)
            if s == 'isUIComponentVisible "Time Slider"':
                return self.ts_visible
            if s == 'isUIComponentVisible "Range Slider"':
                return self.rs_visible
            return None

        mel.eval = fake_eval

    def tearDown(self):
        mel.eval = self._orig
        cmds.file(new=True, force=True)

    def _toggle_calls(self):
        """Return only the toggle commands (not the visibility queries)."""
        return [s for s in self.eval_log if s in ("ToggleTimeSlider", "ToggleRangeSlider")]

    def test_both_visible_toggles_both_off(self):
        self.ts_visible = True
        self.rs_visible = True
        self.instance.b009()
        self.assertEqual(
            self._toggle_calls(), ["ToggleTimeSlider", "ToggleRangeSlider"]
        )

    def test_only_ts_visible_toggles_ts_only(self):
        self.ts_visible = True
        self.rs_visible = False
        self.instance.b009()
        self.assertEqual(self._toggle_calls(), ["ToggleTimeSlider"])

    def test_only_rs_visible_toggles_rs_only(self):
        self.ts_visible = False
        self.rs_visible = True
        self.instance.b009()
        self.assertEqual(self._toggle_calls(), ["ToggleRangeSlider"])

    def test_neither_visible_toggles_both_on(self):
        """The else-branch fires both toggles unconditionally."""
        self.ts_visible = False
        self.rs_visible = False
        self.instance.b009()
        self.assertEqual(
            self._toggle_calls(), ["ToggleTimeSlider", "ToggleRangeSlider"]
        )


class TestList000EditorsResolve(unittest.TestCase):
    """Every row of the editors list opens through mtk.UiUtils's registry.

    list000 was a 132-line ``if text == ...: mel.eval(...)`` chain that had to
    be kept in step with the init's item list by hand; both halves now read
    ``mtk.UiUtils.get_editor_types()``. The init filters against it, so a name
    missing from the registry would not dead-end -- it would silently vanish
    from the list. Read by AST so this runs without Maya.
    """

    def test_every_listed_editor_is_registered(self):
        import ast
        import pathlib

        import mayatk as mtk

        path = pathlib.Path(__file__).parents[1] / "tentacle/slots/maya/editors.py"
        tree = ast.parse(path.read_text(encoding="utf-8"))
        editors = next(
            n for n in ast.walk(tree) if isinstance(n, ast.ClassDef) and n.name == "EditorsSlots"
        )
        table = next(
            ast.literal_eval(n.value)
            for n in editors.body
            if isinstance(n, ast.Assign)
            and any(getattr(t, "id", None) == "_EDITORS" for t in n.targets)
        )
        listed = {name for names in table.values() for name in names}
        self.assertEqual(len(listed), 59)
        self.assertEqual(listed - set(mtk.UiUtils.get_editor_types()), set())


@unittest.skipUnless(_MAYA_AVAILABLE, "Requires maya.cmds")
class TestList000Dispatch(unittest.TestCase):
    """list000 opens the picked editor, and says so when it could not."""

    class _Item:
        def __init__(self, text):
            self._text = text

        def item_text(self):
            return self._text

    def setUp(self):
        from unittest import mock

        self.instance = editors_module.EditorsSlots.__new__(editors_module.EditorsSlots)
        self.messages = []
        self.instance.sb = mock.Mock()
        self.instance.sb.message_box.side_effect = self.messages.append
        patcher = mock.patch.object(editors_module.mtk.UiUtils, "open_editor")
        self.open_editor = patcher.start()
        self.addCleanup(patcher.stop)

    def test_an_editor_row_opens_its_editor(self):
        self.open_editor.return_value = "TextureViewWindow"
        self.instance.list000(self._Item("UV Editor"))
        self.open_editor.assert_called_once_with("UV Editor")
        self.assertEqual(self.messages, [])

    def test_a_category_header_opens_nothing(self):
        self.instance.list000(self._Item("Modeling Editors"))
        self.open_editor.assert_not_called()

    def test_a_failed_open_is_reported(self):
        self.open_editor.return_value = None
        self.instance.list000(self._Item("XGen Editor"))
        self.assertTrue(self.messages)



@unittest.skipUnless(_MAYA_AVAILABLE, "Requires maya.cmds")
class TestPreRenameAlias(unittest.TestCase):
    """``Editors`` became ``EditorsSlots``; mayatk's tests import the class by
    module path, so the old name resolves to the same class, with a warning, for
    one release (``ptk.Deprecation.attributes``)."""

    def test_old_name_resolves_to_the_renamed_class_with_a_warning(self):
        with self.assertWarns(DeprecationWarning):
            old = editors_module.Editors
        self.assertIs(old, editors_module.EditorsSlots)


if __name__ == "__main__":
    unittest.main()
