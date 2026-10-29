#!/usr/bin/python
# coding=utf-8
"""The Scene panel's flows, driven offline over a fake toolkit.

``tentacle/slots/scene.py`` holds ``SceneSlots``, one class both hosts share (this file
kept its name from the ``SceneMixin`` it replaced). Every host call goes through
``self.tk``, so a fake toolkit stands in for mayatk / blendertk here and each flow --
Fix Non-Orthogonal Axes' scope, dry-run report, confirm + fix + re-verify; Export
Scene's formats, path resolution, label wiring and guards; the foreign hand-off; the
Import list's pull body; Check GLB / FBX; the Tools list -- runs without ``maya.cmds``
or ``bpy``. The host operations themselves are tested in mayatk and blendertk.
"""

import contextlib
import os
import sys
import unittest
from unittest.mock import patch

import pythontk as ptk
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tentacle.slots._slots import Slots  # noqa: E402
from tentacle.slots.scene import SceneSlots  # noqa: E402


class _Attr:
    """Generic attribute bag (menu / widget / combo stand-in)."""

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class _FakeProgress:
    def __enter__(self):
        return lambda *args, **kwargs: None

    def __exit__(self, *exc):
        return False


# uitk's MessageBox accepts ONLY Qt standard-button names; anything else is silently
# dropped from the dialog (live-caught: a "Fix" button produced a Cancel-only box). The
# fake enforces the same contract so a bad name fails here instead of in a live DCC.
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


def _bridge(app="Blender", extensions=(".blend", ".json"), result=None, raises=None):
    """A bridge CLASS as ``EnvUtils.foreign_scene_bridge`` answers: the target on the
    class, each instance's ``save_as`` recorded on it."""

    class Bridge:
        spec = _Attr(app=_Attr(name=app))
        save_extensions = tuple(extensions)
        calls = []
        params = []  # the per-call params (the carrier rides here)

        def save_as(self, out_path, objects=None, params=None):
            Bridge.calls.append((out_path, objects))
            Bridge.params.append(dict(params or {}))
            if raises:
                raise raises
            return result

    return Bridge


def _engine(imported=("a", "b"), raises=None, scene_extensions=(".blend",)):
    """An import engine CLASS as ``EnvUtils.foreign_scene_import`` answers."""

    class Engine:
        SCENE_EXTENSIONS = tuple(scene_extensions)
        calls = []

        def import_scene(self, src, via="fbx"):
            Engine.calls.append((src, via))
            if raises:
                raise raises
            return list(imported)

    return Engine


class _FakeDiagnostics:
    """``Diagnostics`` stand-in honoring the shared diagnosis contract."""

    def __init__(self, diagnosis, scene=(), selection=(), fixed=None):
        # {name: {"skew": float, "cause": str, "driven": [...]}} -- what
        # get_non_orthogonal(detailed=True) returns; the flat form is its key list.
        self.diagnosis = dict(diagnosis)
        self.fixed = list(fixed if fixed is not None else diagnosis)
        self.scopes = {"all": list(scene), "selection": list(selection)}
        self.calls = []
        self.scene_resolutions = 0

    def transforms_in_scope(self, scope="selection"):
        if scope == "all":
            self.scene_resolutions += 1
        return list(self.scopes[scope])

    def get_non_orthogonal(self, objects, detailed=False):
        self.calls.append(("detect", list(objects)))
        return dict(self.diagnosis) if detailed else list(self.diagnosis)

    def fix_non_orthogonal_axes(self, objects, quiet=False, break_connections=False):
        self.calls.append(("fix", list(objects), break_connections))
        self.diagnosis = {}  # fixed -- later detects come back clean
        return list(self.fixed)


class _FakeEnvUtils:
    """``EnvUtils`` stand-in: the scene, the workspace, the bridges and the writer."""

    def __init__(self, scene_path="", bridge=None, engine=None, tris=0, writer_error=None):
        self.scene_path = scene_path
        self.bridge = bridge or _bridge()
        self.engine = engine or _engine()
        self.tris = tris
        self.tri_calls = []
        self.writes = []
        self.writer_error = writer_error

    def saved_scene_path(self):
        return self.scene_path

    def workspace_root(self, path=None):
        return "W:/proj"

    def foreign_scene_bridge(self):
        return self.bridge

    def foreign_scene_import(self):
        return self.engine

    def scene_triangle_count(self, selection_only=False):
        self.tri_calls.append(selection_only)
        return self.tris

    def export_scene(self, file_path, file_format="fbx", progress=None, **options):
        self.writes.append((file_format, file_path, dict(options)))
        if self.writer_error:
            raise self.writer_error
        return file_path


class _FakeSwitchboard:
    def __init__(self, tk, click="Yes", picked=None, opened=None):
        self.tk = tk
        self.click = click  # the button the fake user presses
        self.picked = picked  # what a save dialog returns
        self.opened = opened  # what an open dialog returns
        self.messages = []
        self.dialogs = []
        self.enable_rules = []
        self.text_rules = []
        self.policy = []
        self.save_kwargs = None
        self.open_kwargs = None
        self.cursors = []

    @contextlib.contextmanager
    def busy_cursor(self):
        self.cursors.append("set")
        try:
            yield
        finally:
            self.cursors.append("restore")

    def progress(self, **kwargs):
        return _FakeProgress()

    def message_box(self, text, *buttons, **kwargs):
        unknown = set(buttons) - QT_STANDARD_BUTTONS
        assert not unknown, f"non-standard message_box buttons: {unknown}"
        self.messages.append(text)
        return self.click if buttons else None

    def text_view_dialog(self, content, *args, **kwargs):
        self.dialogs.append(content)

    def save_file_dialog(self, **kwargs):
        self.save_kwargs = kwargs
        return self.picked

    def file_dialog(self, **kwargs):
        self.open_kwargs = kwargs
        return self.opened

    def apply_visibility_policy(self, widget):
        self.policy.append(widget)
        return False

    def enable_when(self, ui, targets, trigger, condition=True, **kwargs):
        """Record the rule. The BEHAVIOR is uitk's (``test_switchboard_toggle.py``);
        what the panel owns is asking for the right one."""
        self.enable_rules.append((targets, trigger, condition))

    def text_from(self, ui, target, sources, formatter, signal=None, value=None):
        """Record the rule, then apply it the way uitk would -- enough to prove the
        panel's half: the sources in order, a formatter that composes them, and the
        reader override the format combo needs."""
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


def _slot(
    diagnostics=None,
    scene_path="",
    workspace=None,
    selection=(),
    bridge=None,
    engine=None,
    tris=0,
    writer_error=None,
    **sb_kwargs,
):
    """A ``SceneSlots`` over a fake toolkit (its window has no footer)."""
    env = _FakeEnvUtils(scene_path, bridge, engine, tris, writer_error)
    tk = _Attr(
        EnvUtils=env,
        Diagnostics=diagnostics,
        DataNodes=_Attr(scene_workspace=lambda: workspace),
        CoreUtils=_Attr(selected_objects=lambda: list(selection)),
    )
    sb = _FakeSwitchboard(tk, **sb_kwargs)
    sb.loaded_ui = _Attr(scene=_Attr(), scene_submenu=_Attr())  # no footer
    migrated = Slots._legacy_repeat_last_migrated
    Slots._legacy_repeat_last_migrated = True  # no legacy-shortcut migration
    try:
        return SceneSlots(sb)
    finally:
        Slots._legacy_repeat_last_migrated = migrated


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
    """Fix Non-Orthogonal Axes: the scope comes off ``transforms_in_scope``."""

    def _host(self, diagnosis, scene=(), selection=(), click="Yes"):
        return _slot(
            _FakeDiagnostics(diagnosis, scene=scene, selection=selection), click=click
        )

    def test_empty_scene_and_empty_selection_guards(self):
        host = self._host({})
        host.tb002(_widget(scope="all"))
        self.assertIn("Empty scene", host.sb.messages[-1])
        host.tb002(_widget(scope="selection"))
        self.assertIn("Nothing selected", host.sb.messages[-1])
        self.assertEqual(host.tk.Diagnostics.calls, [])  # never scanned

    def test_clean_scan_reports_nothing_to_fix(self):
        host = self._host({}, scene=["clean"])
        host.tb002(_widget(scope="all"))
        self.assertIn("nothing to fix", host.sb.messages[-1])
        self.assertEqual([c[0] for c in host.tk.Diagnostics.calls], ["detect"])

    def test_dry_run_renders_report_without_fixing(self):
        host = self._host(DIAGNOSIS, scene=["|grp|bad", "own"])
        host.tb002(_widget(scope="all", dry_run=True))
        self.assertEqual([c[0] for c in host.tk.Diagnostics.calls], ["detect"])
        report = host.sb.dialogs[-1]
        # Skew-sorted, leaf-named rows with both causes; legend present.
        self.assertIn("0.78000", report)
        self.assertIn("inherited", report)
        self.assertIn("shear", report)
        self.assertLess(report.index("bad"), report.index("own"))
        self.assertNotIn("|grp|", report)  # leaf names only

    def test_fix_flow_confirms_fixes_and_reverifies_fresh(self):
        host = self._host(DIAGNOSIS, scene=["|grp|bad", "own"])
        host.tb002(_widget(scope="all"))
        diagnostics = host.tk.Diagnostics
        self.assertEqual([c[0] for c in diagnostics.calls], ["detect", "fix", "detect"])
        # The confirmation states the count, the inherited breakdown, and what the
        # fix does in each host before anything is touched.
        confirm = host.sb.messages[0]
        self.assertIn("2</hl> object(s)", confirm)
        self.assertIn("1 inheriting it from a parent", confirm)
        self.assertIn(host.NON_ORTHOGONAL_FIX_EFFECT, confirm)
        self.assertIn("Maya", host.NON_ORTHOGONAL_FIX_EFFECT)
        self.assertIn("Blender", host.NON_ORTHOGONAL_FIX_EFFECT)
        self.assertIn("Fixed <hl>2</hl> of <hl>2</hl>", host.sb.messages[-1])
        # The verify re-resolves the scene (a fix can rename via uninstance) instead
        # of reusing the stale pre-fix list.
        self.assertEqual(diagnostics.scene_resolutions, 2)

    def test_selection_scope_keeps_its_list_for_the_verify(self):
        host = self._host(DIAGNOSIS, selection=["own"])
        host.tb002(_widget(scope="selection"))
        diagnostics = host.tk.Diagnostics
        self.assertEqual(diagnostics.calls[-1], ("detect", ["own"]))
        self.assertEqual(diagnostics.scene_resolutions, 0)

    def test_cancel_leaves_scene_untouched(self):
        host = self._host(DIAGNOSIS, scene=["|grp|bad"], click="Cancel")
        host.tb002(_widget(scope="all"))
        self.assertNotIn("fix", [c[0] for c in host.tk.Diagnostics.calls])

    def test_partial_fix_reports_remaining(self):
        class StubbornDiag(_FakeDiagnostics):
            def fix_non_orthogonal_axes(
                self, objects, quiet=False, break_connections=False
            ):
                self.calls.append(("fix", list(objects), break_connections))
                self.diagnosis = {"own": self.diagnosis["own"]}  # one survives
                return ["|grp|bad"]

        host = _slot(StubbornDiag(DIAGNOSIS, scene=["|grp|bad", "own"]))
        host.tb002(_widget(scope="all"))
        result = host.sb.messages[-1]
        self.assertIn("Fixed <hl>1</hl> of <hl>2</hl>", result)
        self.assertIn("could not be fixed", result)

    def test_report_truncation_is_stated(self):
        many = {
            f"n{i:03d}": {"skew": 0.5, "cause": "shear", "driven": []}
            for i in range(250)
        }
        host = self._host(many, scene=list(many))
        host.tb002(_widget(scope="all", dry_run=True))
        self.assertIn("and 50 more", host.sb.dialogs[-1])

    def test_report_handles_objects_with_name_attribute(self):
        """Blender hands bpy objects (``.name``), Maya hands strings."""
        obj = _Attr(name="BpyObject")
        html = SceneSlots._format_non_orthogonal(
            _slot(), {obj: {"skew": 0.5, "cause": "inherited", "driven": []}}
        )
        self.assertIn("BpyObject", html)

    def test_driven_offenders_surface_in_confirm_and_report(self):
        diagnosis = {
            "clean": {"skew": 0.5, "cause": "shear", "driven": []},
            "rigged": {"skew": 0.7, "cause": "inherited", "driven": ["ctrl.rotateZ"]},
        }
        # Dry-run report carries the driver column.
        host = self._host(diagnosis, scene=list(diagnosis))
        host.tb002(_widget(scope="all", dry_run=True))
        self.assertIn("ctrl.rotateZ", host.sb.dialogs[-1])

        # Confirmation states the skip and the opt-in; the fix gets
        # break_connections=False.
        host = self._host(diagnosis, scene=list(diagnosis))
        host.tb002(_widget(scope="all"))
        confirm = host.sb.messages[0]
        self.assertIn("DRIVEN", confirm)
        self.assertIn("skipped", confirm)
        fix_call = next(c for c in host.tk.Diagnostics.calls if c[0] == "fix")
        self.assertFalse(fix_call[2])

        # With the checkbox on, the confirm flips and the flag passes through.
        host = self._host(diagnosis, scene=list(diagnosis))
        host.tb002(_widget(scope="all", break_connections=True))
        self.assertIn("removing their drivers", host.sb.messages[0])
        fix_call = next(c for c in host.tk.Diagnostics.calls if c[0] == "fix")
        self.assertTrue(fix_call[2])


class _FakeList:
    """Stand-in for uitk's ExpandableList (the surface the list inits touch)."""

    def __init__(self, submenu=False):
        self.ui = _Attr(has_tags=lambda *tags: submenu)
        self.fixed_item_height = None
        self.preset = None
        self.items = []

    def apply_preset(self, name):
        self.preset = name

    def get_items(self):
        return list(self.items)

    def add(self, text, data=None, **kwargs):
        item = _Attr(text=text, data=data, sublist=_FakeList(), properties={}, **kwargs)
        item.setProperty = item.properties.__setitem__
        self.items.append(item)
        return item


TOOLS = {
    "Bridges": [("{app} Bridge", "b010", "Send to {app}.", None)],
    "Recover": [("Save to Original Scene", "b014", "Recover.", "maya")],
    "Fix": [
        ("Fix OCIO", "b009", "Fix color management.", "maya"),
        ("Fix Color Spaces", "b011", "By map type.", None),
    ],
}


def _tools_host(items=TOOLS):
    """A slot whose Tools table is *items*, recording the leaves it registers."""
    host = _slot()
    host._tools_items = lambda: items
    host.slot_widgets = []

    def add_slot_widget(sublist, widget_class=None, **kwargs):
        host.slot_widgets.append((widget_class, kwargs))
        return sublist.add(kwargs.get("setText", ""), **kwargs)

    host.add_slot_widget = add_slot_widget
    return host


class TestToolsList(unittest.TestCase):
    """``list003`` -- the Tools list."""

    def test_submenu_flyout_overlays_the_row_and_fans_left(self):
        """The submenu's trigger is a narrow strip near the right edge, so its flyout
        must cover that row and fan LEFT -- uitk's ``expand_overlay_left``."""
        widget = _FakeList(submenu=True)
        _tools_host().list003_init(widget)
        self.assertEqual(widget.preset, "expand_overlay_left")

    def test_panel_row_keeps_the_header_menu_preset(self):
        widget = _FakeList(submenu=False)
        _tools_host().list003_init(widget)
        self.assertEqual(widget.preset, "hover_menu")

    def test_every_category_and_leaf_is_built_naming_the_other_dcc(self):
        widget = _FakeList()
        host = _tools_host()
        host.list003_init(widget)
        root = widget.items[0]
        self.assertEqual(root.text, "Tools")
        self.assertEqual(root.setToolTip, host.TOOLS_ROOT_TOOLTIP)
        self.assertEqual([i.text for i in root.sublist.items], list(TOOLS))
        # Leaves are slot-wired by objectName, so their slots / settings identity
        # survive; "{app}" is the other DCC, off the host's bridge.
        self.assertEqual(
            [(kw["setObjectName"], kw["setText"]) for _, kw in host.slot_widgets],
            [
                ("b010", "Blender Bridge"),
                ("b014", "Save to Original Scene"),
                ("b009", "Fix OCIO"),
                ("b011", "Fix Color Spaces"),
            ],
        )
        self.assertEqual(host.slot_widgets[0][1]["setToolTip"], "Send to Blender.")

    def test_a_one_host_leaf_is_tagged_before_it_registers(self):
        """The tag must be on the widget BEFORE ``register_widget`` runs its
        ``*_init``: the visibility policy hides it first, and b014_init then never
        reaches a library call the other host lacks."""
        host = _tools_host()
        host.sb.registered_widgets = _Attr(PushButton=_FakeButton)
        host.list003_init(_FakeList())
        built = {kw["setObjectName"]: factory() for factory, kw in host.slot_widgets}
        self.assertEqual(built["b014"].properties, {"requires": "maya"})
        self.assertEqual(built["b009"].properties, {"requires": "maya"})
        self.assertEqual(built["b011"].properties, {})

    def test_a_category_every_leaf_of_which_one_host_serves_is_tagged_too(self):
        widget = _FakeList()
        host = _tools_host()
        host.list003_init(widget)
        categories = {i.text: i for i in widget.items[0].sublist.items}
        self.assertEqual(categories["Recover"].properties, {"requires": "maya"})
        self.assertEqual(categories["Fix"].properties, {})  # a mixed category stays
        self.assertIn(categories["Recover"], host.sb.policy)

    def test_the_real_table_tags_only_one_host_rows(self):
        host = _slot()
        host.sb.tooltip = _Attr(fmt=lambda **kw: "formatted")
        rows = [row for entries in host._tools_items().values() for row in entries]
        tagged = {name: requires for _, name, _, requires in rows if requires}
        self.assertEqual(
            tagged,
            {
                "b014": "maya",
                "b006": "maya",
                "b_cleanup": "blender",
                "b009": "maya",
                "b018": "maya",
                "b012": "maya",
            },
        )
        names = [name for _, name, _, _ in rows]
        self.assertEqual(len(names), len(set(names)), "one objectName per leaf")
        self.assertIn("b019", names)

    def test_dispatch_calls_a_leaf_and_ignores_a_category(self):
        calls = []
        leaf = _Attr(sublist=_FakeList(), call_slot=lambda: calls.append("leaf"))
        category = _Attr(sublist=_FakeList(), call_slot=lambda: calls.append("cat"))
        category.sublist.add("a leaf under it")
        host = _tools_host()
        host.list003(category)  # navigation only
        self.assertEqual(calls, [])
        host.list003(leaf)
        self.assertEqual(calls, ["leaf"])

    def test_dispatch_tolerates_an_item_with_no_slot(self):
        """A plain ``add(str)`` row carries no ``call_slot`` -- must not raise."""
        _tools_host().list003(_Attr(sublist=_FakeList()))


class _FakeButton:
    def __init__(self):
        self.properties = {}

    def setProperty(self, name, value):
        self.properties[name] = value


class TestExportFormats(unittest.TestCase):
    """The format table + path resolution the Export Scene combo drives."""

    def test_the_combo_offers_the_portable_four_plus_the_other_dcc(self):
        items = _slot()._export_format_items()
        self.assertEqual([d for _, d in items], ["fbx", "obj", "glb", "usd", "foreign"])
        # Only the LAST label is the host's: its bridge's own extension.
        self.assertEqual(items[-1], ("BLEND", "foreign"))
        maya = _slot(bridge=_bridge("Maya", (".ma", ".mb")))
        self.assertEqual(maya._export_format_items()[-1], ("MA", "foreign"))

    def test_inserting_usd_renamed_the_combo_so_stored_indices_cannot_lie(self):
        """uitk persists a combo by INDEX: the foreign twin moved from 3 to 4, so the
        objectName moved too (a stored "Blend" must not become "USD")."""
        self.assertEqual(SceneSlots.EXPORT_FORMAT_COMBO, "cmb_export_format")
        self.assertNotEqual(SceneSlots.EXPORT_FORMAT_COMBO, "cmb_format")

    def test_transfer_items_are_pythontk_s_carrier_vocabulary(self):
        self.assertEqual(
            [d for _, d in SceneSlots.EXPORT_TRANSFER_ITEMS],
            list(ptk.CARRIER_EXTENSIONS),
        )
        self.assertEqual(SceneSlots.EXPORT_TRANSFER_ITEMS[0], ("FBX", "fbx"))

    def test_extensions_resolve_and_the_foreign_one_comes_off_the_bridge(self):
        host = _slot(bridge=_bridge("Maya", (".ma", ".mb")))
        self.assertEqual(host._export_extension("fbx"), ".fbx")
        self.assertEqual(host._export_extension("obj"), ".obj")
        self.assertEqual(host._export_extension("glb"), ".glb")
        self.assertEqual(host._export_extension("usd"), ".usd")
        # Not a second table here -- the bridge already declares it.
        self.assertEqual(host._export_extension("foreign"), ".ma")

    def test_a_loose_scene_exports_into_its_own_folders_data_dir(self):
        """A saved scene outside any project is its own (unmarked) workspace
        (``ptk.Workspace.for_scene``), so the quick route writes to
        ``<scene folder>/data/`` -- the one layout, never beside the scene."""
        tmp = ptk.TempArtifacts.scoped("tentacle_scene_export_loose")
        self.addCleanup(tmp.cleanup)
        folder = tmp.dir_path()
        scene = os.path.join(folder, "asset.ma")
        ws = ptk.Workspace.for_scene(scene)  # the real rule, no session project
        self.assertIsNotNone(ws)
        host = _slot(scene_path=scene, workspace=ws)
        out = host._resolve_export_path("export_dir", ".fbx")
        self.assertEqual(
            os.path.normcase(out),
            os.path.normcase(os.path.join(folder, "data", "asset.fbx")),
        )
        self.assertTrue(os.path.isdir(os.path.dirname(out)))

    def _project(self, rules=None):
        tmp = ptk.TempArtifacts.scoped("tentacle_scene_export")
        self.addCleanup(tmp.cleanup)
        root = tmp.dir_path()
        os.makedirs(os.path.join(root, "scenes"))
        return root, ptk.Workspace(root, rules or {})

    def test_export_dir_mode_writes_into_the_scene_project_export_folder(self):
        """The quick route follows the scene project's export rule (``FBX export``,
        else ``data/``), never the scene folder -- and makes it."""
        root, ws = self._project()
        scene = os.path.join(root, "scenes", "asset.ma")
        host = _slot(scene_path=scene, workspace=ws)
        out = host._resolve_export_path("export_dir", ".fbx")
        self.assertEqual(out, os.path.join(root, "data", "asset.fbx"))
        self.assertTrue(os.path.isdir(os.path.dirname(out)))

    def test_export_dir_mode_honors_the_project_export_rule(self):
        root, ws = self._project({"FBX export": "deliver/fbx"})
        scene = os.path.join(root, "scenes", "asset.ma")
        host = _slot(scene_path=scene, workspace=ws)
        self.assertEqual(
            host._resolve_export_path("export_dir", ".glb"),
            os.path.join(root, "deliver", "fbx", "asset.glb"),
        )

    def test_prompt_mode_prefills_the_project_export_folder(self):
        root, ws = self._project()
        os.makedirs(os.path.join(root, "data"))
        scene = os.path.join(root, "scenes", "asset.ma")
        host = _slot(scene_path=scene, workspace=ws, picked="X:/a.fbx")
        host._resolve_export_path("prompt", ".fbx")
        self.assertEqual(
            host.sb.save_kwargs["start_dir"], os.path.join(root, "data", "asset.fbx")
        )

    def test_export_dir_mode_reports_an_unsaved_scene_instead_of_guessing(self):
        host = _slot(scene_path="")
        self.assertIsNone(host._resolve_export_path("export_dir", ".fbx"))
        self.assertIn("has not been saved", host.sb.messages[-1])

    def test_prompt_mode_without_a_project_prefills_the_scene_dir(self):
        host = _slot(scene_path="P:/proj/asset.ma", picked="P:/out/thing.glb")
        self.assertEqual(
            host._resolve_export_path("prompt", ".glb"), "P:/out/thing.glb"
        )
        self.assertEqual(
            host.sb.save_kwargs["start_dir"], os.path.join("P:/proj", "asset.glb")
        )
        self.assertEqual(host.sb.save_kwargs["file_types"], ["*.glb"])

    def test_prompt_mode_falls_back_to_the_workspace_root_when_unsaved(self):
        """The workspace ROOT, absolute -- the forks passed its folder NAME, a path
        relative to wherever the host's process happened to sit."""
        host = _slot(scene_path="", picked="X:/a.fbx")
        host._resolve_export_path("prompt", ".fbx")
        self.assertEqual(
            host.sb.save_kwargs["start_dir"], os.path.join("W:/proj", "untitled.fbx")
        )

    def test_prompt_mode_appends_a_missing_extension(self):
        """Qt does not reliably add the filter's suffix, and the writer picks its
        translator off the extension."""
        host = _slot(picked="X:/bare_name")
        self.assertEqual(
            host._resolve_export_path("prompt", ".obj"), "X:/bare_name.obj"
        )

    def test_prompt_mode_cancels_cleanly(self):
        host = _slot(picked=None)
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
    """A tb003 whose combos carry the panel's OWN item tables (so this can't drift)."""
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
        self.host = _slot()

    def test_the_defaults_are_a_quick_export_of_the_selection_as_fbx(self):
        """Each combo's LEADING item -- what an unconfigured option box shows."""
        self.assertEqual(
            self.host._default_export_button_text(), "Quick Export Sel FBX"
        )

    def test_quick_marks_the_no_prompt_route_only(self):
        self.assertEqual(
            self.host._export_button_text("selected", "export_dir", "GLB"),
            "Quick Export Sel GLB",
        )
        self.assertEqual(
            self.host._export_button_text("selected", "prompt", "GLB"),
            "Export Sel GLB",
        )

    def test_the_scope_word_follows_the_scope(self):
        self.assertEqual(
            self.host._export_button_text("all", "export_dir", "FBX"),
            "Quick Export Scene FBX",
        )
        self.assertEqual(
            self.host._export_button_text("all", "prompt", "FBX"), "Export Scene FBX"
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
        "fbx" where the button wants to say "FBX"; reading the combo's own label is
        also what makes the other DCC's format read as the host names it."""
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
        menu.cmb_export_format.setCurrentIndex(4)  # the other DCC's
        self.assertEqual(widget.text, "Export Scene BLEND")

    def test_cameras_and_lights_gate_on_the_scope_through_enable_when(self):
        widget = _export_option_box(self.host)
        self.host._wire_export_options(widget)
        self.assertEqual(
            self.host.sb.enable_rules,
            [("chk_cameras,chk_lights", "cmb_scope", "all")],
        )

    def test_the_transfer_combo_is_not_gated_on_the_export_format(self):
        """The carrier is read by the Import list's pull rows too, so gating it on
        the foreign format left the USD pull route unreachable."""
        widget = _export_option_box(self.host)
        self.host._wire_export_options(widget)
        self.assertNotIn("cmb_transfer", [rule[0] for rule in self.host.sb.enable_rules])


class TestForeignExport(unittest.TestCase):
    """The blocking bridge hand-off shared by the list row and the format combo."""

    def test_success_returns_the_result_and_balances_the_cursor(self):
        bridge = _bridge(result={"output": "X:/a.blend", "duration": 1.5})
        host = _slot(bridge=bridge)
        result = host._run_foreign_export("X:/a.blend", ["cube"])
        self.assertEqual(result["output"], "X:/a.blend")
        self.assertEqual(bridge.calls, [("X:/a.blend", ["cube"])])
        self.assertEqual(host.sb.cursors, ["set", "restore"])
        self.assertEqual(host.sb.messages, [])

    def test_a_handled_failure_is_reported_not_silent(self):
        """The bridge returns None having logged the reason; a silent no-op after a
        ten-second wait is the worst outcome."""
        host = _slot(bridge=_bridge(result=None))
        self.assertIsNone(host._run_foreign_export("X:/a.blend"))
        self.assertIn("failed", host.sb.messages[-1])
        self.assertIn("Blender", host.sb.messages[-1])
        self.assertEqual(host.sb.cursors, ["set", "restore"])

    def test_a_raised_error_is_reported_as_text_and_the_cursor_restores(self):
        host = _slot(bridge=_bridge(raises=RuntimeError("bad prim </root>")))
        self.assertIsNone(host._run_foreign_export("X:/a.blend"))
        self.assertIn("bad prim &lt;/root&gt;", host.sb.messages[-1])
        self.assertEqual(host.sb.cursors, ["set", "restore"])

    def test_the_list_row_prompts_then_delegates(self):
        bridge = _bridge(result={"output": "X:/a.blend", "duration": 2.0})
        host = _slot(bridge=bridge, scene_path="P:/proj/asset.ma", picked="X:/a.blend")
        host._export_foreign_scene()
        self.assertEqual(bridge.calls, [("X:/a.blend", None)])  # the whole scene
        self.assertIn("Exported", host.sb.messages[-1])
        self.assertEqual(host.sb.save_kwargs["title"], "Export Blender Scene")
        self.assertEqual(
            host.sb.save_kwargs["start_dir"], os.path.join("P:/proj", "asset.blend")
        )

    def test_the_list_row_cancels_without_running_anything(self):
        bridge = _bridge()
        host = _slot(bridge=bridge, picked=None)
        host._export_foreign_scene()
        self.assertEqual(bridge.calls, [])
        self.assertEqual(host.sb.cursors, [])


def _export_widget(fmt="fbx", scope="all", save="export_dir", transfer="fbx", **checks):
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
        **{name: _Attr(isChecked=lambda v=value: v) for name, value in state.items()},
    )
    return _Attr(option_box=_Attr(menu=menu))


class TestTb003ExportFlow(unittest.TestCase):
    """Export Scene: the option reads, guards, path and reporting, then ONE
    ``EnvUtils.export_scene`` write (or the foreign bridge)."""

    def _host(self, **kwargs):
        kwargs.setdefault("scene_path", "P:/proj/asset.ma")
        return _slot(**kwargs)

    def test_fbx_writes_beside_the_scene_and_reports(self):
        host = self._host()
        host.tb003(_export_widget(fmt="fbx"))
        fmt, path, _options = host.tk.EnvUtils.writes[0]
        self.assertEqual((fmt, path), ("fbx", "P:/proj/asset.fbx"))
        self.assertIn("Exported", host.sb.messages[-1])

    def test_each_format_picks_up_its_own_extension(self):
        for fmt, ext in (("fbx", ".fbx"), ("obj", ".obj"), ("glb", ".glb")):
            host = self._host()
            host.tb003(_export_widget(fmt=fmt))
            with self.subTest(fmt=fmt):
                self.assertTrue(host.tk.EnvUtils.writes[0][1].endswith(ext))

    def test_selected_only_coerces_the_scene_level_toggles_off(self):
        """Cameras/lights only export if selected, so a stale checked-but-disabled box
        must not leak through; skins ride the selected mesh."""
        host = self._host(selection=["cube"])
        host.tb003(_export_widget(scope="selected"))
        options = host.tk.EnvUtils.writes[0][2]
        self.assertTrue(options["selection_only"])
        self.assertFalse(options["include_cameras"])
        self.assertFalse(options["include_lights"])
        self.assertTrue(options["include_skins"])

    def test_selected_only_with_nothing_selected_stops_before_writing(self):
        host = self._host(selection=[])
        host.tb003(_export_widget(scope="selected"))
        self.assertEqual(host.tk.EnvUtils.writes, [])
        self.assertIn("No objects selected", host.sb.messages[-1])

    def test_obj_skips_the_tangent_cost_warning(self):
        """OBJ carries no tangent channel, so the cost it warns about isn't paid."""
        host = self._host()
        host.tb003(_export_widget(fmt="obj"))
        self.assertEqual(host.tk.EnvUtils.tri_calls, [])
        host = self._host()
        host.tb003(_export_widget(fmt="fbx"))
        self.assertEqual(host.tk.EnvUtils.tri_calls, [False])

    def test_a_dense_scene_asks_first_and_no_writes_nothing(self):
        host = self._host(tris=SceneSlots._DENSE_TRI_THRESHOLD, click="No")
        host.tb003(_export_widget())
        self.assertEqual(host.tk.EnvUtils.writes, [])
        self.assertIn("5,000,000", host.sb.messages[0])
        host = self._host(tris=SceneSlots._DENSE_TRI_THRESHOLD, click="Yes")
        host.tb003(_export_widget())
        self.assertEqual(len(host.tk.EnvUtils.writes), 1)

    def test_an_unsaved_scene_stops_before_writing(self):
        host = self._host(scene_path="")
        host.tb003(_export_widget(save="export_dir"))
        self.assertEqual(host.tk.EnvUtils.writes, [])
        self.assertIn("has not been saved", host.sb.messages[-1])

    def test_a_cancelled_prompt_writes_nothing(self):
        host = self._host(picked=None)
        host.tb003(_export_widget(save="prompt"))
        self.assertEqual(host.tk.EnvUtils.writes, [])
        self.assertEqual(host.sb.messages, [])

    def test_a_writer_error_is_reported_as_text_not_markup(self):
        """pxr's errors quote prim paths like ``</>``, which the box reads as markup."""
        host = self._host(writer_error=RuntimeError("syntax error in </>"))
        host.tb003(_export_widget(fmt="usd"))
        self.assertIn("syntax error in &lt;/&gt;", host.sb.messages[-1])

    def test_the_foreign_format_routes_through_the_bridge_not_the_writer(self):
        bridge = _bridge(result={"output": "P:/proj/asset.blend", "duration": 3.0})
        host = self._host(bridge=bridge)
        host.tb003(_export_widget(fmt="foreign"))
        self.assertEqual(host.tk.EnvUtils.writes, [])
        self.assertEqual(bridge.calls, [("P:/proj/asset.blend", None)])
        self.assertEqual(bridge.params, [{ptk.CARRIER_PARAM: "fbx"}])
        self.assertIn("Exported", host.sb.messages[-1])

    def test_the_transfer_combo_picks_the_foreign_hand_off_s_carrier(self):
        bridge = _bridge(result={"output": "P:/proj/asset.blend", "duration": 3.0})
        host = self._host(bridge=bridge)
        host.tb003(_export_widget(fmt="foreign", transfer="usd"))
        self.assertEqual(bridge.params, [{ptk.CARRIER_PARAM: "usd"}])

    def test_a_host_without_a_panel_transfers_via_fbx(self):
        """Headless callers (and the Import list before the option box exists)."""
        self.assertEqual(_slot()._transfer_carrier(), "fbx")

    def test_the_foreign_format_honors_the_scope_combo(self):
        bridge = _bridge(result={"output": "X:/a.blend", "duration": 1.0})
        host = self._host(bridge=bridge, selection=["cube"])
        host.tb003(_export_widget(fmt="foreign", scope="selected"))
        self.assertEqual(bridge.calls[0][1], ["cube"])


class TestPullScene(unittest.TestCase):
    """``_pull_scene`` -- the browse / import / report body every Import-list pull
    row runs (the other DCC's scene, glTF, USD)."""

    def test_a_pick_is_imported_with_the_transfer_carrier_and_reported(self):
        engine = _engine()
        host = _slot(engine=engine, opened="X:/in/set.blend")
        host._pull_scene(["*.blend"], "Import Blender Scene", "Blender Scenes", "k")
        self.assertEqual(engine.calls, [("X:/in/set.blend", "fbx")])
        self.assertIn("Imported <hl>2</hl> object(s)", host.sb.messages[-1])
        self.assertIn("set.blend", host.sb.messages[-1])
        self.assertEqual(host.sb.cursors, ["set", "restore"])

    def test_the_browser_opens_beside_the_scene_then_the_workspace(self):
        host = _slot(scene_path="P:/proj/scenes/asset.ma")
        host._pull_scene(["*.blend"], "t", "d", "k")
        self.assertEqual(host.sb.open_kwargs["start_dir"], "P:/proj/scenes")
        self.assertFalse(host.sb.open_kwargs["allow_multiple"])
        host = _slot()  # unsaved scene
        host._pull_scene(["*.blend"], "t", "d", "k")
        self.assertEqual(host.sb.open_kwargs["start_dir"], "W:/proj")

    def test_cancelling_the_browser_imports_nothing(self):
        engine = _engine()
        host = _slot(engine=engine, opened=None)
        host._pull_scene(["*.blend"], "t", "d", "k")
        self.assertEqual(engine.calls, [])
        self.assertEqual(host.sb.cursors, [])
        self.assertEqual(host.sb.messages, [])

    def test_an_engine_failure_is_reported_escaped_and_the_cursor_restores(self):
        host = _slot(
            engine=_engine(raises=RuntimeError("syntax error in </>")),
            opened="X:/in/damaged.usda",
        )
        host._pull_scene(["*.usda"], "Import USD", "USD Files", "USD")
        self.assertIn("USD import failed", host.sb.messages[-1])
        self.assertIn("&lt;/&gt;", host.sb.messages[-1])
        self.assertEqual(host.sb.cursors, ["set", "restore"])

    def test_an_importer_given_runs_in_place_of_the_engine(self):
        """A file the host imports natively (Blender's FBX) shares the browse / cursor
        / report body, not the engine or its carrier."""
        seen = []
        engine = _engine()
        host = _slot(engine=engine, opened="X:/in/shots.fbx")
        host._pull_scene(
            ["*.fbx"],
            "Import FBX",
            "FBX Files",
            "FBX",
            importer=lambda src: seen.append(src) or ["a", "b", "c"],
        )
        self.assertEqual(seen, ["X:/in/shots.fbx"])
        self.assertEqual(engine.calls, [])
        self.assertIn("Imported <hl>3</hl> object(s)", host.sb.messages[-1])

    def test_the_other_dcc_s_scene_browses_its_engine_s_extensions(self):
        engine = _engine(scene_extensions=(".ma", ".mb"))
        host = _slot(engine=engine, bridge=_bridge("Maya", (".ma", ".mb")))
        host._import_foreign_scene()
        self.assertEqual(host.sb.open_kwargs["file_types"], ["*.ma", "*.mb"])
        self.assertEqual(host.sb.open_kwargs["title"], "Import Maya Scene")


class TestUsdListEntries(unittest.TestCase):
    """Import USD / Export USD -- the Import and Export lists' USD one-shots."""

    USD_GLOBS = [f"*{ext}" for ext in ptk.USD_EXTENSIONS]

    def test_import_usd_browses_every_usd_spelling(self):
        engine = _engine()
        host = _slot(engine=engine, opened="X:/in/set.usdz")
        host._import_usd()
        self.assertEqual(host.sb.open_kwargs["file_types"], self.USD_GLOBS)
        self.assertEqual(host.sb.open_kwargs["title"], "Import USD")
        self.assertEqual([src for src, _ in engine.calls], ["X:/in/set.usdz"])

    def test_export_usd_writes_the_whole_scene_through_the_writer(self):
        host = _slot(scene_path="P:/proj/asset.ma", picked="X:/out/asset.usd")
        host._export_usd()
        ((fmt, path, options),) = host.tk.EnvUtils.writes
        self.assertEqual((fmt, path), ("usd", "X:/out/asset.usd"))
        self.assertEqual(options, SceneSlots.ONE_SHOT_EXPORT_OPTIONS)
        self.assertIn("Exported", host.sb.messages[-1])
        self.assertEqual(host.sb.save_kwargs["file_types"], self.USD_GLOBS)
        self.assertEqual(
            host.sb.save_kwargs["start_dir"], os.path.join("P:/proj", "asset.usd")
        )

    def test_export_usd_keeps_a_typed_spelling_and_completes_a_bare_name(self):
        for picked, written in (
            ("X:/out/hero.usdz", "X:/out/hero.usdz"),
            ("X:/out/hero.usda", "X:/out/hero.usda"),
            ("X:/out/hero", "X:/out/hero.usd"),
        ):
            with self.subTest(picked=picked):
                host = _slot(picked=picked)
                host._export_one_shot("usd")
                self.assertEqual(host.tk.EnvUtils.writes[0][1], written)

    def test_export_usd_cancel_writes_nothing(self):
        host = _slot(picked=None)
        host._export_one_shot("usd")
        self.assertEqual(host.tk.EnvUtils.writes, [])
        self.assertEqual(host.sb.messages, [])

    def test_maya_s_export_gltf_row_is_the_glb_one_shot(self):
        host = _slot(scene_path="P:/proj/asset.ma", picked="X:/out/hero")
        host._export_gltf()
        self.assertEqual(
            host.tk.EnvUtils.writes,
            [("glb", "X:/out/hero.glb", SceneSlots.ONE_SHOT_EXPORT_OPTIONS)],
        )
        self.assertEqual(host.sb.save_kwargs["file_types"], ["*.glb"])

    def test_one_shot_passes_export_scene_s_dense_gate(self):
        """A whole-scene GLB rides FBX with tangents on -- the cost Export Scene warns
        about -- so a dense scene asks first, and a No writes nothing."""
        host = _slot(picked="X:/out/hero.glb", tris=10_000_000, click="No")
        host._export_one_shot("glb")
        self.assertEqual(host.tk.EnvUtils.tri_calls, [False])
        self.assertEqual(host.tk.EnvUtils.writes, [])
        self.assertIsNone(host.sb.save_kwargs)  # cancelled before the prompt

    def test_export_scene_s_usd_prompt_takes_the_same_spellings(self):
        host = _slot(picked="X:/out/hero.usdz")
        host.tb003(_export_widget(fmt="usd", save="prompt"))
        self.assertEqual(host.tk.EnvUtils.writes[0][:2], ("usd", "X:/out/hero.usdz"))

    def test_only_usd_has_alternate_spellings(self):
        host = _slot(picked="X:/out/hero.usdz")
        host.tb003(_export_widget(fmt="fbx", save="prompt"))
        self.assertEqual(host.tk.EnvUtils.writes[0][1], "X:/out/hero.usdz.fbx")

    def test_the_foreign_format_takes_every_extension_its_bridge_writes(self):
        """A Maya scene is ``.ma`` or ``.mb``: a typed ``shot.mb`` stays one."""
        host = _slot(bridge=_bridge("Maya", (".ma", ".mb")), picked="X:/out/shot.mb")
        spellings = host._export_spellings("foreign")
        self.assertEqual(spellings, (".ma", ".mb"))
        self.assertEqual(
            host._resolve_export_path("prompt", ".ma", spellings), "X:/out/shot.mb"
        )


def _fake_verifier(rows_by_file=None, raises_for=()):
    """An ``ExportVerifier`` stand-in recording its inputs. Each file's report carries
    ``rows_by_file[basename]`` (a single PASS by default); a basename in *raises_for*
    fails to open, as a corrupt file does."""
    from pythontk.file_utils.mesh_convert.export_verify import (
        Finding,
        VerificationReport,
    )

    calls = []

    class FakeVerifier:
        def __init__(self, glb=None, fbx=None, **kwargs):
            calls.append({"glb": glb, "fbx": fbx})
            name = os.path.basename(glb or fbx)
            if name in raises_for:
                raise ValueError("not a GLB container")
            self.sidecar_path = None
            self._rows = (rows_by_file or {}).get(
                name, [Finding("PASS", "glb_container", "ok")]
            )

        def run(self, checks=None):
            return VerificationReport(rows=list(self._rows))

    return FakeVerifier, calls


class TestCheckDeliverables(unittest.TestCase):
    """``b019`` -- the Scene Exporter's post-write gates, over files on disk."""

    def _run(self, host, verifier):
        with patch.object(ptk, "ExportVerifier", verifier):
            host.b019()

    def test_a_glb_and_its_fbx_are_checked_as_one_deliverable(self):
        fake, calls = _fake_verifier()
        host = _slot(
            opened=["X:/out/hero_v004.glb", "X:/out/hero_v004.FBX", "X:/out/prop.glb"]
        )
        self._run(host, fake)
        self.assertEqual(
            calls,
            [
                {"glb": "X:/out/hero_v004.glb", "fbx": "X:/out/hero_v004.FBX"},
                {"glb": "X:/out/prop.glb", "fbx": None},
            ],
        )
        report = host.sb.dialogs[-1]
        self.assertIn("hero_v004", report)
        self.assertIn("2 deliverable(s) checked: 2 passed, 0 failed", report)

    def test_cancelling_the_browser_checks_nothing(self):
        for picked in (None, []):
            with self.subTest(picked=picked):
                fake, calls = _fake_verifier()
                host = _slot(opened=picked)
                self._run(host, fake)
                self.assertEqual(calls, [])
                self.assertEqual(host.sb.dialogs, [])
                self.assertEqual(host.sb.messages, [])

    def test_a_pick_holding_no_deliverable_says_so(self):
        fake, calls = _fake_verifier()
        host = _slot(opened=["X:/notes.txt"])
        self._run(host, fake)
        self.assertEqual(calls, [])
        self.assertIn(".glb", host.sb.messages[-1])

    def test_the_report_names_every_failing_gate_and_counts_it(self):
        from pythontk.file_utils.mesh_convert.export_verify import Finding

        fake, _ = _fake_verifier(
            rows_by_file={
                "hero.glb": [
                    Finding("FAIL", "glb_container", "truncated <chunk>"),
                    Finding("WARN", "glb_skins", "stub skins"),
                ]
            }
        )
        host = _slot(opened=["X:/hero.glb"])
        self._run(host, fake)
        report = host.sb.dialogs[-1]
        self.assertIn("[FAIL] glb_container: truncated &lt;chunk&gt;", report)
        self.assertIn("1 deliverable(s) checked: 0 passed, 1 failed", report)

    def test_a_file_that_cannot_be_opened_is_reported_and_the_rest_still_run(self):
        fake, calls = _fake_verifier(raises_for=("broken.glb",))
        host = _slot(opened=["X:/broken.glb", "X:/good.glb"])
        self._run(host, fake)
        self.assertEqual(len(calls), 2)
        report = host.sb.dialogs[-1]
        self.assertIn("not a GLB container", report)
        self.assertIn("1 could not be checked", report)

    def test_the_browser_opens_beside_the_scene_then_the_workspace(self):
        fake, _ = _fake_verifier()
        host = _slot(scene_path="P:/proj/scenes/asset.ma")
        self._run(host, fake)
        self.assertEqual(host.sb.open_kwargs["start_dir"], "P:/proj/scenes")
        self.assertEqual(host.sb.open_kwargs["file_types"], ["*.glb", "*.fbx"])
        self.assertTrue(host.sb.open_kwargs["allow_multiple"])
        host = _slot()  # unsaved scene
        self._run(host, fake)
        self.assertEqual(host.sb.open_kwargs["start_dir"], "W:/proj")

    def test_the_check_is_listed_under_diagnostics_for_both_hosts(self):
        host = _slot()
        host.sb.tooltip = _Attr(fmt=lambda **kw: "formatted")
        diagnostics = host._tools_items()["Diagnostics"]
        self.assertIn(("b019", None), [(name, req) for _, name, _, req in diagnostics])


if __name__ == "__main__":
    unittest.main()
