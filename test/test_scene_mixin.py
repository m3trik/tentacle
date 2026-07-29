#!/usr/bin/python
# coding=utf-8
"""Tests for the shared scene-panel behavior (DCC-agnostic).

``tentacle/slots/_scene.py`` holds ``SceneMixin`` — the shared ``scene`` slot
behavior, currently the Fix Non-Orthogonal Axes header entry (``tb002``)
mixed into both DCC Scene slots. The mixin imports nothing DCC-specific
(engine access goes through the ``_diagnostics`` / ``_scene_objects`` /
``_selected_objects`` hooks), so the whole flow — scope resolution, dry-run
report, confirm + fix + re-verify — is exercised directly here with fakes
(no ``maya.cmds`` / ``bpy`` needed; this runs everywhere). Two AST checks pin
that both DCC slots actually mix the shared class in and supply every hook.
"""
import ast
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tentacle.slots._scene import SceneMixin  # noqa: E402

MAYA_FILE = ROOT / "tentacle" / "slots" / "maya" / "scene.py"
BLENDER_FILE = ROOT / "tentacle" / "slots" / "blender" / "scene.py"

HOOKS = ("_diagnostics", "_scene_objects", "_selected_objects")


class _FakeDiagnostics:
    """Engine stand-in honoring the shared diagnosis contract."""

    def __init__(self, diagnosis, fixed=None):
        # {name: {"skew": float, "cause": str, "driven": [...]}} — what
        # get_non_orthogonal(detailed=True) returns; the flat form is its
        # key list.
        self.diagnosis = dict(diagnosis)
        self.fixed = list(fixed if fixed is not None else diagnosis)
        self.calls = []

    def get_non_orthogonal(self, objects, detailed=False):
        self.calls.append(("detect", list(objects)))
        return dict(self.diagnosis) if detailed else list(self.diagnosis)

    def fix_non_orthogonal_axes(self, objects, quiet=False, break_connections=False):
        self.calls.append(("fix", list(objects), break_connections))
        self.diagnosis = {}  # fixed — later detects come back clean
        return list(self.fixed)


class _Attr:
    """Generic attribute bag (menu / widget / combo stand-in)."""

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class _FakeProgress:
    def __enter__(self):
        return lambda *args, **kwargs: None

    def __exit__(self, *exc):
        return False


# uitk's MessageBox accepts ONLY Qt standard-button names; anything else is
# silently dropped from the dialog (live-caught: a "Fix" button produced a
# Cancel-only box). The fake enforces the same contract so a bad name fails
# here instead of in a live DCC.
QT_STANDARD_BUTTONS = frozenset(
    {
        "Ok", "Open", "Save", "Cancel", "Close", "Discard", "Apply", "Reset",
        "RestoreDefaults", "Help", "SaveAll", "Yes", "YesToAll", "No",
        "NoToAll", "Abort", "Retry", "Ignore",
    }
)


class _FakeSwitchboard:
    def __init__(self, click="Yes"):
        self.click = click  # the button the fake user presses
        self.messages = []
        self.dialogs = []

    def progress(self, **kwargs):
        return _FakeProgress()

    def message_box(self, text, *buttons, **kwargs):
        unknown = set(buttons) - QT_STANDARD_BUTTONS
        assert not unknown, f"non-standard message_box buttons: {unknown}"
        self.messages.append(text)
        return self.click if buttons else None

    def text_view_dialog(self, content, *args, **kwargs):
        self.dialogs.append(content)


class _Host(SceneMixin):
    """Minimal host wiring the mixin's hooks without any DCC."""

    NON_ORTHOGONAL_FIX_EFFECT = "Freezes the transform."

    def __init__(self, diagnostics, scene=(), selection=(), click="Yes"):
        self.sb = _FakeSwitchboard(click=click)
        self._diag = diagnostics
        self._scene = list(scene)
        self._selection = list(selection)
        self.scene_resolutions = 0

    def _diagnostics(self):
        return self._diag

    def _scene_objects(self):
        self.scene_resolutions += 1
        return list(self._scene)

    def _selected_objects(self):
        return list(self._selection)


def _widget(scope="all", dry_run=False, break_connections=False):
    menu = _Attr(
        cmb_scope2=_Attr(currentData=lambda: scope),
        chk_dry_run=_Attr(isChecked=lambda: dry_run),
        chk_break_connections=_Attr(isChecked=lambda: break_connections),
    )
    return _Attr(option_box=_Attr(menu=menu))


DIAGNOSIS = {
    "|grp|bad": {"skew": 0.78, "cause": "inherited", "driven": []},
    "own": {"skew": 0.37, "cause": "shear", "driven": []},
}


class TestTb002Flow(unittest.TestCase):
    def test_empty_scene_and_empty_selection_guards(self):
        host = _Host(_FakeDiagnostics({}), scene=[], selection=[])
        host.tb002(_widget(scope="all"))
        self.assertIn("Empty scene", host.sb.messages[-1])
        host.tb002(_widget(scope="selection"))
        self.assertIn("Nothing selected", host.sb.messages[-1])
        self.assertEqual(host._diag.calls, [])  # never scanned

    def test_clean_scan_reports_nothing_to_fix(self):
        host = _Host(_FakeDiagnostics({}), scene=["clean"])
        host.tb002(_widget(scope="all"))
        self.assertIn("nothing to fix", host.sb.messages[-1])
        self.assertEqual([c[0] for c in host._diag.calls], ["detect"])

    def test_dry_run_renders_report_without_fixing(self):
        host = _Host(_FakeDiagnostics(DIAGNOSIS), scene=["|grp|bad", "own"])
        host.tb002(_widget(scope="all", dry_run=True))
        self.assertEqual([c[0] for c in host._diag.calls], ["detect"])
        report = host.sb.dialogs[-1]
        # Skew-sorted, leaf-named rows with both causes; legend present.
        self.assertIn("0.78000", report)
        self.assertIn("inherited", report)
        self.assertIn("shear", report)
        self.assertLess(report.index("bad"), report.index("own"))
        self.assertNotIn("|grp|", report)  # leaf names only

    def test_fix_flow_confirms_fixes_and_reverifies_fresh(self):
        host = _Host(_FakeDiagnostics(DIAGNOSIS), scene=["|grp|bad", "own"])
        host.tb002(_widget(scope="all"))
        self.assertEqual(
            [c[0] for c in host._diag.calls], ["detect", "fix", "detect"]
        )
        # Confirmation states the count, the inherited breakdown, and the
        # DCC-specific effect before anything is touched.
        confirm = host.sb.messages[0]
        self.assertIn("2</hl> object(s)", confirm)
        self.assertIn("1 inheriting it from a parent", confirm)
        self.assertIn(host.NON_ORTHOGONAL_FIX_EFFECT, confirm)
        self.assertIn("Fixed <hl>2</hl> of <hl>2</hl>", host.sb.messages[-1])
        # The verify re-resolves scene objects (a fix can rename via
        # uninstance) instead of reusing the stale pre-fix list.
        self.assertEqual(host.scene_resolutions, 2)

    def test_cancel_leaves_scene_untouched(self):
        host = _Host(_FakeDiagnostics(DIAGNOSIS), scene=["|grp|bad"], click="Cancel")
        host.tb002(_widget(scope="all"))
        self.assertNotIn("fix", [c[0] for c in host._diag.calls])

    def test_partial_fix_reports_remaining(self):
        class StubbornDiag(_FakeDiagnostics):
            def fix_non_orthogonal_axes(
                self, objects, quiet=False, break_connections=False
            ):
                self.calls.append(("fix", list(objects), break_connections))
                self.diagnosis = {"own": self.diagnosis["own"]}  # one survives
                return ["|grp|bad"]

        host = _Host(StubbornDiag(DIAGNOSIS), scene=["|grp|bad", "own"])
        host.tb002(_widget(scope="all"))
        result = host.sb.messages[-1]
        self.assertIn("Fixed <hl>1</hl> of <hl>2</hl>", result)
        self.assertIn("could not be fixed", result)

    def test_report_truncation_is_stated(self):
        many = {
            f"n{i:03d}": {"skew": 0.5, "cause": "shear", "driven": []}
            for i in range(250)
        }
        host = _Host(_FakeDiagnostics(many), scene=list(many))
        host.tb002(_widget(scope="all", dry_run=True))
        self.assertIn("and 50 more", host.sb.dialogs[-1])

    def test_report_handles_objects_with_name_attribute(self):
        """Blender hands bpy objects (``.name``), Maya hands strings."""
        obj = _Attr(name="BpyObject")
        html = SceneMixin._format_non_orthogonal(
            _Host(_FakeDiagnostics({})),
            {obj: {"skew": 0.5, "cause": "inherited", "driven": []}},
        )
        self.assertIn("BpyObject", html)

    def test_driven_offenders_surface_in_confirm_and_report(self):
        diagnosis = {
            "clean": {"skew": 0.5, "cause": "shear", "driven": []},
            "rigged": {
                "skew": 0.7,
                "cause": "inherited",
                "driven": ["ctrl.rotateZ"],
            },
        }
        # Dry-run report carries the driver column.
        host = _Host(_FakeDiagnostics(diagnosis), scene=list(diagnosis))
        host.tb002(_widget(scope="all", dry_run=True))
        self.assertIn("ctrl.rotateZ", host.sb.dialogs[-1])

        # Confirmation states the skip and the opt-in, and the engine is
        # called with break_connections=False.
        host = _Host(_FakeDiagnostics(diagnosis), scene=list(diagnosis))
        host.tb002(_widget(scope="all"))
        confirm = host.sb.messages[0]
        self.assertIn("DRIVEN", confirm)
        self.assertIn("skipped", confirm)
        fix_call = next(c for c in host._diag.calls if c[0] == "fix")
        self.assertFalse(fix_call[2])

        # With the checkbox on, the confirm flips and the flag passes through.
        host = _Host(_FakeDiagnostics(diagnosis), scene=list(diagnosis))
        host.tb002(_widget(scope="all", break_connections=True))
        self.assertIn("removing their drivers", host.sb.messages[0])
        fix_call = next(c for c in host._diag.calls if c[0] == "fix")
        self.assertTrue(fix_call[2])


class TestDccSlotsWireTheMixin(unittest.TestCase):
    """AST checks: both DCC scene slots mix SceneMixin in and supply the hooks."""

    def _class_def(self, path):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == "SceneSlots":
                return node
        self.fail(f"no SceneSlots class in {path}")

    def _check(self, path):
        cls = self._class_def(path)
        bases = [ast.unparse(b) for b in cls.bases]
        self.assertIn("SceneMixin", bases, f"{path.name} bases: {bases}")
        # The mixin must win the MRO over the DCC base for shared methods.
        self.assertEqual(bases[0], "SceneMixin", bases)
        defined = {n.name for n in cls.body if isinstance(n, ast.FunctionDef)}
        for hook in HOOKS:
            self.assertIn(hook, defined, f"{path.name} missing hook {hook}")
        assigned = {
            t.id
            for n in cls.body
            if isinstance(n, ast.Assign)
            for t in n.targets
            if isinstance(t, ast.Name)
        }
        self.assertIn("NON_ORTHOGONAL_FIX_EFFECT", assigned, path.name)

    def test_maya_slot(self):
        self._check(MAYA_FILE)

    def test_blender_slot(self):
        self._check(BLENDER_FILE)


if __name__ == "__main__":
    unittest.main()
