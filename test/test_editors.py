#!/usr/bin/python
# coding=utf-8
"""Regression tests for tentacle.slots.maya.editors.

editors.py is dominated by a mel.eval dispatch table (list000) for every
Maya editor window. The unit with real conditional logic worth pinning
is b009 (Time & Range) — its 4-way visibility-state matrix decides
which sliders to toggle.
"""
import unittest

try:
    import maya.cmds as cmds
    import maya.mel as mel
    from tentacle.slots.maya import editors as editors_module

    _MAYA_AVAILABLE = True
except ImportError:
    cmds = None
    mel = None
    editors_module = None
    _MAYA_AVAILABLE = False


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
        self.instance = editors_module.Editors.__new__(editors_module.Editors)

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


@unittest.skipUnless(_MAYA_AVAILABLE, "Requires maya.cmds")
class TestList000DispatchCompleteness(unittest.TestCase):
    """The list000 dispatcher is a 5-category × N-item dispatch table. The
    init builds an editors_dict from string literals; list000 has a
    matching `if text == "Foo": mel.eval(...)` chain.

    Drift between the two (adding an item to the dict but forgetting the
    branch) produces a click-does-nothing bug. We don't probe every entry
    (would mean stubbing both halves) but we do verify the source-code
    text references match — a static check.
    """

    def test_every_editors_dict_item_has_dispatch_branch(self):
        """Probe by AST: every quoted item in editors_dict appears in list000
        as a `text == "..."` comparison."""
        import ast
        import pathlib

        src = (
            pathlib.Path(editors_module.__file__).read_text(encoding="utf-8")
        )
        tree = ast.parse(src)

        # Find Editors class
        editors_class = next(
            n for n in ast.walk(tree)
            if isinstance(n, ast.ClassDef) and n.name == "Editors"
        )

        # Collect editors_dict literal items from list000_init.
        list000_init = next(
            n for n in editors_class.body
            if isinstance(n, ast.FunctionDef) and n.name == "list000_init"
        )
        dict_items: set[str] = set()
        for node in ast.walk(list000_init):
            if isinstance(node, ast.Dict):
                for val in node.values:
                    if isinstance(val, ast.List):
                        for elt in val.elts:
                            if isinstance(elt, ast.Constant) and isinstance(
                                elt.value, str
                            ):
                                dict_items.add(elt.value)

        # Collect dispatched strings from list000 (text == "...").
        list000 = next(
            n for n in editors_class.body
            if isinstance(n, ast.FunctionDef) and n.name == "list000"
        )
        dispatched: set[str] = set()
        for node in ast.walk(list000):
            if (
                isinstance(node, ast.Compare)
                and isinstance(node.left, ast.Name)
                and node.left.id == "text"
                and len(node.comparators) == 1
                and isinstance(node.comparators[0], ast.Constant)
                and isinstance(node.comparators[0].value, str)
            ):
                dispatched.add(node.comparators[0].value)

        # Every item declared in the init should appear in the dispatcher.
        missing = dict_items - dispatched
        self.assertEqual(
            missing,
            set(),
            f"editors_dict declares items with no dispatch branch: {sorted(missing)}",
        )


if __name__ == "__main__":
    unittest.main()
