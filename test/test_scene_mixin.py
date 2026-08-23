#!/usr/bin/python
# coding=utf-8
"""Tests for the shared scene-panel behavior (DCC-agnostic).

``tentacle/slots/_scene.py`` holds ``SceneMixin`` — the ``scene`` slot behavior
shared by both DCC Scene slots: the Fix Non-Orthogonal Axes header entry
(``tb002``), the Export Scene / foreign-bridge hand-off, and the Tools list
(``list003``). The mixin imports nothing DCC-specific (engine access goes
through the ``_diagnostics`` / ``_scene_objects`` / ``_selected_objects`` /
``_tools_items`` hooks), so each flow — scope resolution, dry-run report,
confirm + fix + re-verify; format/path resolution; list construction and
dispatch — is exercised directly here with fakes (no ``maya.cmds`` / ``bpy``
needed; this runs everywhere). AST checks pin that both DCC slots actually mix
the shared class in, supply every hook, and do NOT carry their own copy of a
shared method.
"""
import ast
import os
import sys
import unittest

import pythontk as ptk
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tentacle.slots._scene import SceneMixin  # noqa: E402

MAYA_FILE = ROOT / "tentacle" / "slots" / "maya" / "scene.py"
BLENDER_FILE = ROOT / "tentacle" / "slots" / "blender" / "scene.py"

HOOKS = (
    "_diagnostics",
    "_scene_objects",
    "_selected_objects",
    # Export Scene / the Export list's foreign entry. A fork that skips one of
    # these inherits the mixin's NotImplementedError and dies on click — nothing
    # fails at import, so it has to be pinned here.
    "_current_scene_path",
    "_foreign_scene_bridge",
    "_export_scene_native",
    "_confirm_dense_export",
    # The Tools list's contents — the one part of list003 that is fork-specific.
    "_tools_items",
)
#: Class attributes each fork must supply for the shared behavior above.
REQUIRED_ATTRS = (
    "NON_ORTHOGONAL_FIX_EFFECT",
    "FOREIGN_FORMAT_LABEL",
    "TOOLS_ROOT_TOOLTIP",
)
#: Shared methods that must live ONLY on the mixin — a fork re-defining one is
#: the drift this refactor removed (both forks carried byte-identical copies).
FORK_MUST_NOT_DEFINE = ("list003_init", "_dispatch_tools_item")


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
        self.enable_rules = []
        self.text_rules = []

    def progress(self, **kwargs):
        return _FakeProgress()

    def message_box(self, text, *buttons, **kwargs):
        unknown = set(buttons) - QT_STANDARD_BUTTONS
        assert not unknown, f"non-standard message_box buttons: {unknown}"
        self.messages.append(text)
        return self.click if buttons else None

    def text_view_dialog(self, content, *args, **kwargs):
        self.dialogs.append(content)

    def enable_when(self, ui, targets, trigger, condition=True, **kwargs):
        """Record the rule. The BEHAVIOR is uitk's (``test_switchboard_toggle.py``
        covers late registration, preset refresh and the condition forms); what the
        mixin owns is asking for the right one."""
        self.enable_rules.append((targets, trigger, condition))

    def text_from(self, ui, target, sources, formatter, signal=None, value=None):
        """Record the rule, then apply it the way uitk would.

        A minimal stand-in — enough to prove the MIXIN's half: that it hands over the
        right sources in the right order, a formatter that composes them, and the
        reader override the format combo needs. The rule's own behaviour (wire-time
        apply, late registration, bulk refresh, patterns) is uitk's and is covered by
        ``uitk/test/test_switchboard_toggle.py::TestTextFrom``.
        """
        self.text_rules.append((sources, value))
        readers = value if isinstance(value, dict) else {}

        def apply(*_):
            values = [
                readers[name](w) if name in readers else w.currentData()
                for name, w in ((n, getattr(ui, n)) for n in sources)
            ]
            target.setText(formatter(*values))

        for name in sources:
            getattr(ui, name).currentIndexChanged.connect(apply)
        apply()


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
        for attr in REQUIRED_ATTRS:
            self.assertIn(attr, assigned, f"{path.name} missing {attr}")
        for name in FORK_MUST_NOT_DEFINE:
            self.assertNotIn(
                name,
                defined,
                f"{path.name} re-defines {name} — it belongs to SceneMixin",
            )

    def test_maya_slot(self):
        self._check(MAYA_FILE)

    def test_blender_slot(self):
        self._check(BLENDER_FILE)

    def test_forks_delegate_list003_to_the_mixin(self):
        """``list003`` stays in the forks (its ``@Signals`` decorator is a
        class-body evaluation, and the decorator is re-exposed on the DCC Slots
        base so the slots layer never imports uitk) — but its BODY must be the
        one call into the mixin, not a second copy of the dispatch."""
        for path in (MAYA_FILE, BLENDER_FILE):
            with self.subTest(fork=path.name):
                cls = self._class_def(path)
                fn = next(
                    n
                    for n in cls.body
                    if isinstance(n, ast.FunctionDef) and n.name == "list003"
                )
                # Drop the docstring only — the delegating call is itself an
                # ast.Expr, so filtering the whole node type hides the body.
                body = list(fn.body)
                if ast.get_docstring(fn) is not None:
                    body = body[1:]
                self.assertEqual(
                    [ast.unparse(n) for n in body],
                    ["self._dispatch_tools_item(item)"],
                )


class _FakeList:
    """Stand-in for uitk's ExpandableList (the surface list003_init touches)."""

    def __init__(self, submenu=False):
        self.ui = _Attr(has_tags=lambda *tags: submenu)
        self.fixed_item_height = None
        self.preset = None
        self.items = []

    def apply_preset(self, name):
        self.preset = name

    def get_items(self):
        return list(self.items)

    def add(self, text, **kwargs):
        item = _Attr(text=text, sublist=_FakeList(), **kwargs)
        self.items.append(item)
        return item


class _ToolsHost(SceneMixin):
    """A host wiring only the Tools list's hooks."""

    TOOLS_ROOT_TOOLTIP = "Scene bridges and diagnostics."

    def __init__(self, items):
        self._items = items
        self.slot_widgets = []

    def _tools_items(self):
        return self._items

    def add_slot_widget(self, sublist, **kwargs):
        self.slot_widgets.append((sublist, kwargs))
        return sublist.add(kwargs.get("setText", ""), **kwargs)


TOOLS = {
    "Bridges": [("Unity Bridge", "b016", "Send to Unity.")],
    "Fix": [("Fix OCIO", "b009", "Fix color management.")],
}


class TestToolsList(unittest.TestCase):
    """``list003`` — the Tools list, shared by both forks."""

    def test_submenu_flyout_overlays_the_row_and_fans_left(self):
        """The submenu's trigger is a narrow, absolutely-positioned strip near
        the right edge, so its flyout must cover that row (top-right anchored)
        and fan LEFT — uitk's ``expand_overlay_left``. Fanning right (the panel
        preset) ran the categories off the submenu's edge."""
        widget = _FakeList(submenu=True)
        _ToolsHost(TOOLS).list003_init(widget)
        self.assertEqual(widget.preset, "expand_overlay_left")

    def test_panel_row_keeps_the_header_menu_preset(self):
        """The panel's row is layout-managed with room to its right — unchanged."""
        widget = _FakeList(submenu=False)
        _ToolsHost(TOOLS).list003_init(widget)
        self.assertEqual(widget.preset, "hover_menu")

    def test_every_category_and_leaf_is_built(self):
        widget = _FakeList()
        host = _ToolsHost(TOOLS)
        host.list003_init(widget)

        root = widget.items[0]
        self.assertEqual(root.text, "Tools")
        self.assertEqual(root.setToolTip, host.TOOLS_ROOT_TOOLTIP)
        self.assertEqual([i.text for i in root.sublist.items], list(TOOLS))
        # Leaves are slot-wired by objectName, so their slots/settings identity
        # survives the move out of the header menu.
        self.assertEqual(
            [(kw["setObjectName"], kw["setText"]) for _, kw in host.slot_widgets],
            [("b016", "Unity Bridge"), ("b009", "Fix OCIO")],
        )

    def test_dispatch_calls_a_leaf_and_ignores_a_category(self):
        calls = []
        leaf = _Attr(sublist=_FakeList(), call_slot=lambda: calls.append("leaf"))
        category = _Attr(sublist=_FakeList(), call_slot=lambda: calls.append("cat"))
        category.sublist.add("a leaf under it")

        host = _ToolsHost(TOOLS)
        host._dispatch_tools_item(category)  # navigation only
        self.assertEqual(calls, [])
        host._dispatch_tools_item(leaf)
        self.assertEqual(calls, ["leaf"])

    def test_dispatch_tolerates_an_item_with_no_slot(self):
        """A plain ``add(str)`` row carries no ``call_slot`` — must not raise."""
        _ToolsHost(TOOLS)._dispatch_tools_item(_Attr(sublist=_FakeList()))


class _FakeBridge:
    """Stand-in for mtk.BlenderBridge / btk.MayaBridge (the attrs the mixin reads)."""

    def __init__(self, name="Blender", extensions=(".blend",), result=None, raises=None):
        self.spec = _Attr(app=_Attr(name=name))
        self.save_extensions = tuple(extensions)
        self.calls = []
        self.params = []  # the per-call params (the carrier rides here)
        self._result = result
        self._raises = raises

    def save_as(self, out_path, objects=None, params=None):
        self.calls.append((out_path, objects))
        self.params.append(dict(params or {}))
        if self._raises:
            raise self._raises
        return self._result


class _ExportHost(_Host):
    """A ``_Host`` that also wires the export hooks."""

    FOREIGN_FORMAT_LABEL = "Blend"

    def __init__(self, bridge, scene_path="", picked=None, **kwargs):
        super().__init__(diagnostics=None, **kwargs)
        self._bridge = bridge
        self._scene_path = scene_path
        self._picked = picked
        self.sb.save_file_dialog = self._save_file_dialog
        self.sb.QtWidgets = _Attr(QApplication=_Attr(
            setOverrideCursor=lambda *a: self.cursors.append("set"),
            restoreOverrideCursor=lambda *a: self.cursors.append("restore"),
        ))
        self.sb.QtCore = _Attr(Qt=_Attr(WaitCursor=object()))
        self.cursors = []
        self.dialog_kwargs = None

    def _save_file_dialog(self, **kwargs):
        self.dialog_kwargs = kwargs
        return self._picked

    def _current_scene_path(self):
        return self._scene_path

    def _foreign_scene_bridge(self):
        return self._bridge

    def _resolve_workspace_text(self):
        return "W:/proj"


class TestExportFormats(unittest.TestCase):
    """The format table + path resolution the Export Scene combo drives."""

    def setUp(self):
        self.bridge = _FakeBridge()

    def test_the_combo_offers_the_portable_four_plus_the_foreign_twin(self):
        items = _ExportHost(self.bridge)._export_format_items()
        self.assertEqual([d for _, d in items], ["fbx", "obj", "glb", "usd", "foreign"])
        # Only the LAST label is per-fork; the data values are shared, which is
        # what lets the dispatch be shared.
        self.assertEqual(items[-1], ("Blend", "foreign"))

    def test_inserting_usd_renamed_the_combo_so_stored_indices_cannot_lie(self):
        """uitk persists a combo by INDEX: the foreign twin moved from 3 to 4, so the
        objectName moved too (a stored "Blend" must not become "USD")."""
        self.assertEqual(_ExportHost.EXPORT_FORMAT_COMBO, "cmb_export_format")
        self.assertNotEqual(_ExportHost.EXPORT_FORMAT_COMBO, "cmb_format")

    def test_transfer_items_are_pythontk_s_carrier_vocabulary(self):
        self.assertEqual(
            [d for _, d in _ExportHost.EXPORT_TRANSFER_ITEMS], list(ptk.CARRIER_EXTENSIONS)
        )
        self.assertEqual(_ExportHost.EXPORT_TRANSFER_ITEMS[0], ("FBX", "fbx"))

    def test_extensions_resolve_and_the_foreign_one_comes_off_the_bridge(self):
        host = _ExportHost(_FakeBridge(extensions=(".ma", ".mb")))
        self.assertEqual(host._export_extension("fbx"), ".fbx")
        self.assertEqual(host._export_extension("obj"), ".obj")
        self.assertEqual(host._export_extension("glb"), ".glb")
        self.assertEqual(host._export_extension("usd"), ".usd")
        # Not a second table here -- the bridge already declares it.
        self.assertEqual(host._export_extension("foreign"), ".ma")

    def test_scene_dir_mode_writes_beside_the_open_scene(self):
        host = _ExportHost(self.bridge, scene_path="P:/proj/scenes/asset.ma")
        self.assertEqual(
            host._resolve_export_path("scene_dir", ".fbx"), "P:/proj/scenes/asset.fbx"
        )

    def test_scene_dir_mode_reports_an_unsaved_scene_instead_of_guessing(self):
        host = _ExportHost(self.bridge, scene_path="")
        self.assertIsNone(host._resolve_export_path("scene_dir", ".fbx"))
        self.assertIn("has not been saved", host.sb.messages[-1])

    def test_prompt_mode_prefills_the_scene_dir_default(self):
        host = _ExportHost(
            self.bridge, scene_path="P:/proj/asset.ma", picked="P:/out/thing.glb"
        )
        self.assertEqual(host._resolve_export_path("prompt", ".glb"), "P:/out/thing.glb")
        self.assertEqual(
            host.dialog_kwargs["start_dir"], os.path.join("P:/proj", "asset.glb")
        )
        self.assertEqual(host.dialog_kwargs["file_types"], ["*.glb"])

    def test_prompt_mode_falls_back_to_the_workspace_when_unsaved(self):
        host = _ExportHost(self.bridge, scene_path="", picked="X:/a.fbx")
        host._resolve_export_path("prompt", ".fbx")
        self.assertEqual(
            host.dialog_kwargs["start_dir"], os.path.join("W:/proj", "untitled.fbx")
        )

    def test_prompt_mode_appends_a_missing_extension(self):
        """Qt does not reliably add the filter's suffix, and the writer picks its
        translator off the extension."""
        host = _ExportHost(self.bridge, picked="X:/bare_name")
        self.assertEqual(host._resolve_export_path("prompt", ".obj"), "X:/bare_name.obj")

    def test_prompt_mode_cancels_cleanly(self):
        host = _ExportHost(self.bridge, picked=None)
        self.assertIsNone(host._resolve_export_path("prompt", ".fbx"))
        self.assertEqual(host.sb.messages, [])


class _FakeSignal:
    """The one Qt signal the option-box wiring uses."""

    def __init__(self):
        self.slots = []

    def connect(self, slot):
        self.slots.append(slot)

    def emit(self, index):
        for slot in list(self.slots):
            slot(index)


class _FakeCombo:
    """A ``(label, data)`` combo that fires ``currentIndexChanged`` like the real one."""

    def __init__(self, items, index=0):
        self.items = list(items)
        self.index = index
        self.currentIndexChanged = _FakeSignal()

    def setCurrentIndex(self, index):
        self.index = index
        self.currentIndexChanged.emit(index)

    def currentText(self):
        return self.items[self.index][0]

    def currentData(self):
        return self.items[self.index][1]


class _FakeExportButton:
    """The tb003 stand-in the wiring relabels."""

    def __init__(self, menu):
        self.text = ""
        self.option_box = _Attr(menu=menu)

    def setText(self, text):
        self.text = text


def _export_option_box(host):
    """A tb003 whose combos carry the mixin's OWN item tables (so this can't drift).

    No checkbox stand-ins: the cameras/lights gating is an ``sb.enable_when`` rule
    now, recorded by the fake switchboard rather than applied to widgets here.
    """
    menu = _Attr(
        cmb_scope=_FakeCombo(host.EXPORT_SCOPE_ITEMS),
        cmb_save=_FakeCombo(host.EXPORT_SAVE_ITEMS),
        cmb_export_format=_FakeCombo(host._export_format_items()),
        cmb_transfer=_FakeCombo(host.EXPORT_TRANSFER_ITEMS),
    )
    return _FakeExportButton(menu)


class TestExportButtonLabel(unittest.TestCase):
    """The Export entry spells out what a click will do, from its own options."""

    def setUp(self):
        self.host = _ExportHost(_FakeBridge())

    def test_the_defaults_are_a_quick_export_of_the_selection_as_fbx(self):
        """Each combo's LEADING item — what an unconfigured option box shows."""
        self.assertEqual(
            self.host._default_export_button_text(), "Quick Export Sel FBX"
        )

    def test_quick_marks_the_no_prompt_route_only(self):
        self.assertEqual(
            self.host._export_button_text("selected", "scene_dir", "GLB"),
            "Quick Export Sel GLB",
        )
        # Prompt for File stops to ask, so it is not quick.
        self.assertEqual(
            self.host._export_button_text("selected", "prompt", "GLB"),
            "Export Sel GLB",
        )

    def test_the_scope_word_follows_the_scope(self):
        self.assertEqual(
            self.host._export_button_text("all", "scene_dir", "FBX"),
            "Quick Export Scene FBX",
        )
        self.assertEqual(
            self.host._export_button_text("all", "prompt", "FBX"), "Export Scene FBX"
        )

    def test_the_suffix_is_the_combo_label_so_the_foreign_twin_follows_the_fork(self):
        """Not the data value: "foreign" would read as itself on both sides."""
        self.assertEqual(
            self.host._export_button_text("all", "prompt", "Blend"),
            "Export Scene Blend",
        )

    def test_an_unknown_scope_falls_back_to_the_selection_word(self):
        self.assertEqual(
            self.host._export_button_text(None, "prompt", "OBJ"), "Export Sel OBJ"
        )

    def test_wiring_labels_the_button_from_the_options_on_init(self):
        widget = _export_option_box(self.host)
        self.host._wire_export_options(widget)
        self.assertEqual(widget.text, "Quick Export Sel FBX")

    def test_the_format_combo_is_the_one_source_read_by_LABEL(self):
        """Its items carry data, and the default reader would hand the formatter
        "fbx" where the button wants to say "FBX". Reading the combo's own label is
        also what lets the foreign twin read "Blend" / "MA" with no table here."""
        widget = _export_option_box(self.host)
        self.host._wire_export_options(widget)
        sources, value = self.host.sb.text_rules[0]
        self.assertEqual(
            list(sources), ["cmb_scope", "cmb_save", self.host.EXPORT_FORMAT_COMBO]
        )
        self.assertEqual(list(value), [self.host.EXPORT_FORMAT_COMBO])

    def test_every_combo_relabels_the_button_not_just_the_scope(self):
        widget = _export_option_box(self.host)
        self.host._wire_export_options(widget)
        menu = widget.option_box.menu

        menu.cmb_scope.setCurrentIndex(1)  # Entire Scene
        self.assertEqual(widget.text, "Quick Export Scene FBX")
        menu.cmb_save.setCurrentIndex(1)  # Prompt for File
        self.assertEqual(widget.text, "Export Scene FBX")
        menu.cmb_export_format.setCurrentIndex(2)  # GLB
        self.assertEqual(widget.text, "Export Scene GLB")
        menu.cmb_export_format.setCurrentIndex(3)  # USD
        self.assertEqual(widget.text, "Export Scene USD")
        menu.cmb_export_format.setCurrentIndex(4)  # the fork's foreign twin
        self.assertEqual(widget.text, "Export Scene Blend")

    def test_cameras_and_lights_gate_on_the_scope_through_enable_when(self):
        """Scene-level categories are inert in Selected Only mode (the default).

        Wired as uitk's declarative rule, not a closure here: it also re-applies on
        late registration and on a preset load made with signals blocked, which a
        plain signal connection would miss.
        """
        widget = _export_option_box(self.host)
        self.host._wire_export_options(widget)
        self.assertEqual(
            self.host.sb.enable_rules,
            [("chk_cameras,chk_lights", "cmb_scope", "all")],
        )

    def test_the_transfer_combo_is_not_gated_on_the_export_format(self):
        """The carrier lives on the Export option box but is NOT the export's alone.

        Three of its four readers ignore the format combo entirely: the Export
        list's foreign one-shot and both Import <other DCC> Scene entries, which
        share the setting through ``_transfer_carrier()``'s panel-read fallback --
        exactly what the combo's own tooltip promises. Gating it on "foreign" left
        it disabled at the default format, so the USD pull route was unreachable
        without first switching the EXPORT format to Blend / MA.
        """
        widget = _export_option_box(self.host)
        self.host._wire_export_options(widget)
        self.assertNotIn(
            "cmb_transfer",
            [rule[0] for rule in self.host.sb.enable_rules],
        )

    def test_both_forks_delegate_the_wiring_and_persist_the_scope_by_data(self):
        """The scope combo's items were REORDERED (Selected Only leads), so an
        index persisted against the old order would silently select the other
        scope on restore — ``restore_by = "data"`` is what makes that safe."""
        for path in (MAYA_FILE, BLENDER_FILE):
            with self.subTest(fork=path.name):
                src = path.read_text(encoding="utf-8")
                self.assertIn("self._wire_export_options(widget)", src)
                self.assertIn('cmb_scope.restore_by = "data"', src)
                self.assertIn("for text, data in self.EXPORT_SCOPE_ITEMS:", src)
                self.assertIn("for text, data in self.EXPORT_SAVE_ITEMS:", src)


class TestForeignExport(unittest.TestCase):
    """The blocking bridge hand-off shared by the list entry and the format combo."""

    def test_success_returns_the_result_and_balances_the_cursor(self):
        bridge = _FakeBridge(result={"output": "X:/a.blend", "duration": 1.5})
        host = _ExportHost(bridge)
        result = host._run_foreign_export("X:/a.blend", ["cube"])
        self.assertEqual(result["output"], "X:/a.blend")
        self.assertEqual(bridge.calls, [("X:/a.blend", ["cube"])])
        self.assertEqual(host.cursors, ["set", "restore"])
        self.assertEqual(host.sb.messages, [])

    def test_a_handled_failure_is_reported_not_silent(self):
        """The bridge returns None having logged the reason; a silent no-op after a
        ten-second wait is the worst outcome."""
        host = _ExportHost(_FakeBridge(result=None))
        self.assertIsNone(host._run_foreign_export("X:/a.blend"))
        self.assertIn("failed", host.sb.messages[-1])
        self.assertEqual(host.cursors, ["set", "restore"])

    def test_a_raised_error_is_reported_and_the_cursor_still_restores(self):
        host = _ExportHost(_FakeBridge(raises=RuntimeError("boom")))
        self.assertIsNone(host._run_foreign_export("X:/a.blend"))
        self.assertIn("boom", host.sb.messages[-1])
        self.assertEqual(host.cursors, ["set", "restore"])

    def test_the_list_entry_prompts_then_delegates(self):
        bridge = _FakeBridge(result={"output": "X:/a.blend", "duration": 2.0})
        host = _ExportHost(
            bridge, scene_path="P:/proj/asset.ma", picked="X:/a.blend"
        )
        host._export_foreign_scene()
        # Whole scene: no object list is passed.
        self.assertEqual(bridge.calls, [("X:/a.blend", None)])
        self.assertIn("Exported", host.sb.messages[-1])
        self.assertEqual(host.dialog_kwargs["title"], "Export Blender Scene")

    def test_the_list_entry_cancels_without_running_anything(self):
        bridge = _FakeBridge()
        host = _ExportHost(bridge, picked=None)
        host._export_foreign_scene()
        self.assertEqual(bridge.calls, [])
        self.assertEqual(host.cursors, [])


def _export_widget(fmt="fbx", scope="all", save="scene_dir", transfer="fbx", **checks):
    """A tb003 stand-in: the option box tb003_init builds, with all boxes ticked."""
    state = dict(
        chk_cameras=True,
        chk_lights=True,
        chk_skins=True,
        chk_tangents=True,
        chk_embed=True,
    )
    state.update(checks)
    menu = _Attr(
        cmb_export_format=_Attr(currentData=lambda: fmt),
        cmb_transfer=_Attr(currentData=lambda: transfer),
        cmb_scope=_Attr(currentData=lambda: scope),
        cmb_save=_Attr(currentData=lambda: save),
        **{
            name: _Attr(isChecked=lambda v=value: v)
            for name, value in state.items()
        },
    )
    return _Attr(option_box=_Attr(menu=menu))


class _Tb003Host(_ExportHost):
    """An export host that records the native writes instead of performing them."""

    def __init__(self, *args, dense_ok=True, native_error=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.native = []
        self.dense_calls = []
        self._dense_ok = dense_ok
        self._native_error = native_error

    def _selected_objects(self):
        return list(self._selection)

    def _confirm_dense_export(self, selection_only, include_tangents):
        self.dense_calls.append((selection_only, include_tangents))
        return self._dense_ok

    def _export_scene_native(self, export_format, out_path, options, tick):
        self.native.append((export_format, out_path, dict(options)))
        if self._native_error:
            raise self._native_error


class TestTb003ExportFlow(unittest.TestCase):
    """The shared Export Scene skeleton — one flow, both DCCs.

    Only ``_export_scene_native`` differs per fork; everything here (option reads,
    guards, path resolution, the foreign route, reporting) used to be duplicated in
    the two ``tb003`` bodies and is now exercised once, offline, for both.
    """

    def _host(self, **kwargs):
        kwargs.setdefault("scene_path", "P:/proj/asset.ma")
        return _Tb003Host(_FakeBridge(), **kwargs)

    def test_fbx_writes_beside_the_scene_and_reports(self):
        host = self._host()
        host.tb003(_export_widget(fmt="fbx"))
        self.assertEqual(host.native[0][0], "fbx")
        self.assertEqual(host.native[0][1], "P:/proj/asset.fbx")
        self.assertIn("Exported", host.sb.messages[-1])

    def test_each_format_picks_up_its_own_extension(self):
        for fmt, ext in (("fbx", ".fbx"), ("obj", ".obj"), ("glb", ".glb")):
            host = self._host()
            host.tb003(_export_widget(fmt=fmt))
            with self.subTest(fmt=fmt):
                self.assertTrue(host.native[0][1].endswith(ext), host.native)

    def test_selected_only_coerces_the_scene_level_toggles_off(self):
        """Cameras/lights only export if selected, so the "include all" intent does
        not apply — a stale checked-but-disabled box must not leak through."""
        host = self._host(selection=["cube"])
        host.tb003(_export_widget(scope="selected"))
        options = host.native[0][2]
        self.assertTrue(options["selection_only"])
        self.assertFalse(options["include_cameras"])
        self.assertFalse(options["include_lights"])
        # Skins are intrinsic to the selected mesh, so they survive.
        self.assertTrue(options["include_skins"])

    def test_selected_only_with_nothing_selected_stops_before_writing(self):
        host = self._host(selection=[])
        host.tb003(_export_widget(scope="selected"))
        self.assertEqual(host.native, [])
        self.assertIn("No objects selected", host.sb.messages[-1])

    def test_obj_skips_the_tangent_cost_warning(self):
        """OBJ carries no tangent channel, so the cost it warns about isn't paid."""
        host = self._host()
        host.tb003(_export_widget(fmt="obj"))
        self.assertEqual(host.dense_calls, [(False, False)])
        host = self._host()
        host.tb003(_export_widget(fmt="fbx"))
        self.assertEqual(host.dense_calls, [(False, True)])

    def test_declining_the_dense_warning_writes_nothing(self):
        host = self._host(dense_ok=False)
        host.tb003(_export_widget())
        self.assertEqual(host.native, [])

    def test_an_unsaved_scene_stops_before_writing(self):
        host = self._host(scene_path="")
        host.tb003(_export_widget(save="scene_dir"))
        self.assertEqual(host.native, [])
        self.assertIn("has not been saved", host.sb.messages[-1])

    def test_a_cancelled_prompt_writes_nothing(self):
        host = self._host(picked=None)
        host.tb003(_export_widget(save="prompt"))
        self.assertEqual(host.native, [])
        self.assertEqual(host.sb.messages, [])

    def test_a_failing_writer_is_reported_not_raised(self):
        host = self._host(native_error=RuntimeError("plugin missing"))
        host.tb003(_export_widget())
        self.assertIn("plugin missing", host.sb.messages[-1])

    def test_the_foreign_format_routes_through_the_bridge_not_the_writer(self):
        bridge = _FakeBridge(result={"output": "P:/proj/asset.blend", "duration": 3.0})
        host = _Tb003Host(bridge, scene_path="P:/proj/asset.ma")
        host.tb003(_export_widget(fmt="foreign"))
        self.assertEqual(host.native, [])  # never touches the native writer
        self.assertEqual(bridge.calls, [("P:/proj/asset.blend", None)])
        self.assertEqual(bridge.params, [{"CARRIER": "fbx"}])  # the default carrier
        self.assertIn("Exported", host.sb.messages[-1])

    def test_the_transfer_combo_picks_the_foreign_hand_off_s_carrier(self):
        bridge = _FakeBridge(result={"output": "P:/proj/asset.blend", "duration": 3.0})
        host = _Tb003Host(bridge, scene_path="P:/proj/asset.ma")
        host.tb003(_export_widget(fmt="foreign", transfer="usd"))
        self.assertEqual(bridge.params, [{"CARRIER": "usd"}])

    def test_a_host_without_a_panel_transfers_via_fbx(self):
        """Headless callers (and the Import list before the option box exists)."""
        self.assertEqual(_ExportHost(_FakeBridge())._transfer_carrier(), "fbx")

    def test_the_foreign_format_honors_the_scope_combo(self):
        bridge = _FakeBridge(result={"output": "X:/a.blend", "duration": 1.0})
        host = _Tb003Host(bridge, scene_path="P:/proj/asset.ma", selection=["cube"])
        host.tb003(_export_widget(fmt="foreign", scope="selected"))
        # Selected Only passes the selection; whole-scene passes None.
        self.assertEqual(bridge.calls[0][1], ["cube"])


if __name__ == "__main__":
    unittest.main()
