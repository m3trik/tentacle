# tentacle — API Index

_Auto-generated. Do not edit by hand. Compact symbol index — grep this for a name; for full signatures/docs, slice [API_REGISTRY.md](API_REGISTRY.md) (never Read it whole)._

### `__init__.py`
- `greeting(string, outputToConsole=True)`
- constants: DEFAULT_INCLUDE, MOVED_NAMES

### `slots/_animation.py` — Text the animation panel's Maya and Blender forks say identically.
- `class AnimationMixin`
  - methods: list000_init

### `slots/_display.py` — Behavior shared by the Maya and Blender ``display`` panels.
- `class DisplayMixin`
  - methods: header_init, list000_init

### `slots/_duplicate.py` — Behavior shared by the Maya and Blender ``duplicate`` panels.
- `class DuplicateMixin`
  - methods: header_init

### `slots/_edit.py` — Shared, DCC-agnostic behavior for the ``edit`` panel.
- `class EditMixin`
  - methods: mesh_cleanup_tooltip, cleanup_popup_html, cleanup_console_report, report_cleanup_failure, cmb000_init

### `slots/_hud_warnings.py` — Shared HUD framework (DCC-agnostic): warnings + the prev-command line.
- `class HudWarningsMixin`
  - methods: hudTextEdit_init, evaluate_warnings, insert_warning_icons, insert_warning_details, insert_prev_command

### `slots/_lighting.py` — Shared surface for the ``lighting`` panel's Maya and Blender forks.
- `class LightingMixin`
  - methods: kelvin_tooltip

### `slots/_main.py` — Behavior shared by the Maya and Blender ``main`` start menus' Workspace tab.
- `class MainMixin`

### `slots/_materials.py` — Shared, DCC-agnostic behavior for the ``materials`` panel.
- `class MaterialsMixin`
  - methods: tbl000_init, b028, b029, b030, b031, b032, lbl002, txt000_init, b006_init, b006, b033, b014, header_init, b003, list001_init

### `slots/_nurbs.py` — Behavior shared by the Maya and Blender ``nurbs`` panels.
- `class NurbsMixin`
  - methods: list000_init

### `slots/_pivot.py` — Behavior shared by the Maya and Blender ``pivot`` panels.
- `class PivotMixin`
  - methods: b000, b001, b002

### `slots/_preferences.py` — Shared, DCC-agnostic behavior for the ``preferences`` panel.
- `class PreferencesMixin`
  - methods: cmb004_init, cmb004, cmb005_init, cmb005, cmb006_init, cmb006, header_init, tb000, b011

### `slots/_rendering.py` — Shared, DCC-agnostic behavior for the ``rendering`` panel.
- `class RenderingMixin`

### `slots/_rigging.py` — Behavior shared by the Maya and Blender ``rigging`` panels.
- `class RiggingMixin`

### `slots/_scene.py` — Behavior shared by the Maya and Blender ``scene`` panels.
- `class SceneMixin`
  - methods: tb003, list003_init, b019, tb001_init, tb001, tb002_init, tb002

### `slots/_selection.py` — Behavior shared by the Maya and Blender ``selection`` panels.
- `class SelectionMixin`
  - methods: list001_init, tb004

### `slots/_settings.py` — Shared, DCC-agnostic behavior for the ``settings`` panel.
- `class SettingsMixin`
  - methods: ecosystem_dists, header_init, tb000, check_for_update, b020, b021, b022, b023, b024, cmb_bind_default_init, cmb_bind_left_init, cmb_bind_middle_init, cmb_bind_right_init, cmb_bind_left_right_init, b_reset_bindings

### `slots/_slots.py`
- `class Slots(QtCore.QObject)`
  - methods: tk, mirror_app_state, require_selection, activate_tool, add_slot_widget, gate_on_app, recheck_app_gates, toggle_camera_view, register_camera_view_toggle

### `slots/_transform.py` — Behavior shared by the Maya and Blender ``transform`` panels.
- `class TransformMixin`
  - methods: tb001_init

### `slots/_uv.py` — Behavior shared by the Maya and Blender UV panels.
- `class UvMixin`
  - methods: b000_init, b000, b030_init, get_map_size, cmb003, s003, b029_init

### `slots/blender/_slots_blender.py`
- `class SlotsBlender(Slots)`
  - methods: selected_objects, active_object, effective_fps, ensure_edit_mode, ensure_object_mode, set_viewport_tool, resolve_op, invoke_op, transfer_from_active

### `slots/blender/animation.py`
- `class AnimationSlots(AnimationMixin, SlotsBlender)`
  - methods: list000, tb000_init, tb000, tb001_init, tb001, tb003_init, tb003, tb009_init, tb009, tb010_init, tb010, tb002_init, tb002, tb004_init, tb004, tb005_init, tb005, tb013_init, tb013, tb007_init, tb007, tb008_init, tb008, tb006_init, tb006, tb012_init, tb012, tb018_init, tb018, tb014_init, tb014, tb017_init, tb017, b005, tb011_init, tb011, tb016_init, tb016, tb019_init, tb019, tb015_init, tb015, tb021_init, tb021, tb020, b000, b004, b006

### `slots/blender/blender.py`
- `class BlenderSlots(SlotsBlender)`

### `slots/blender/cameras.py`
- `class CamerasSlots(SlotsBlender)`
  - methods: list000_init, list000, b000, b001, b002, b003, b004, b005, b006, b007, b010, b011, b012, b013

### `slots/blender/crease.py`
- `class CreaseSlots(SlotsBlender)`
  - methods: tb000_init, tb000, b002

### `slots/blender/deformation.py`
- `class DeformationSlots(SlotsBlender)`
  - methods: tb001_init, tb001

### `slots/blender/display.py`
- `class DisplaySlots(DisplayMixin, SlotsBlender)`
  - methods: list000, b013, b014

### `slots/blender/duplicate.py`
- `class DuplicateSlots(DuplicateMixin, SlotsBlender)`
  - methods: tb000_init, tb000, tb001_init, tb001, tb002_init, tb002, b005, b000, b006, b007, b008

### `slots/blender/edit.py`
- `class EditSlots(EditMixin, SlotsBlender)`
  - methods: header_init, b_channels, tb000_init, tb000, tb002, list000_init, list000, list001_init, list001, b000, cmb000, tb001_init, tb001, tb004_init, tb004

### `slots/blender/editors.py`
- `class EditorsSlots(SlotsBlender)`
  - methods: list000_init, list000, b000, b001, b002, b003, b004, b005, b006_init, b006, b007_init, b007, b008_init, b008, b009, b010, b011, b012_init, b012, b013_init, b013

### `slots/blender/hud.py`
- `class StatusMixin`
  - methods: insert_scene_status
- `class HudSelectionMixin`
  - methods: insert_selection_info, insert_component_info
- `class WarningsMixin(HudWarningsMixin)`
- `class HudSlots(SlotsBlender, StatusMixin, HudSelectionMixin, WarningsMixin)`
  - methods: request_hud_build, construct_hud

### `slots/blender/lighting.py`
- `class LightingSlots(LightingMixin, SlotsBlender)`
  - methods: b000, b001, b002_init, b002, tb000_init, tb000

### `slots/blender/main.py`
- `class MainSlots(MainMixin, SlotsBlender)`
  - methods: list000_init, list000

### `slots/blender/materials.py`
- `class MaterialsSlots(MaterialsMixin, SlotsBlender)`
  - methods: b_shader_editor, select_by_mat, tb001_init, tb001, list000_init, list000, list001, b004, b013, b015, lbl004, lbl006, b021, b010, b009, b027, b011, b018, b008, b016, b022, b023, b024, b025, b019, b020

### `slots/blender/nurbs.py`
- `class NurbsSlots(NurbsMixin, SlotsBlender)`
  - methods: b058, tb000_init, tb000, tb001_init, tb001, list000, b030, b056

### `slots/blender/pivot.py`
- `class PivotSlots(PivotMixin, SlotsBlender)`
  - methods: tb000_init, tb000, tb001_init, tb001, tb002_init, tb002, tb003_init, tb003, b004

### `slots/blender/polygons.py`
- `class PolygonsSlots(SlotsBlender)`
  - methods: header_init, tb000_init, tb000, b005, tb002_init, tb002, tb003_init, tb003, tb004_init, tb004, tb005_init, tb005, tb006_init, tb006, tb007_init, tb007, tb008_init, tb008, tb009_init, tb009, b001, b003, b006, b007, b008, b009, b011, b012, b022, b032, b047, b051, b043, b000, b053, b034, b038_init, b038, b049

### `slots/blender/preferences.py`
- `class PreferencesSlots(PreferencesMixin, SlotsBlender)`
  - methods: cmb001_init, cmb001, cmb002_init, cmb002, s000_init, s001_init, b001, cmb003_init, cmb003, b008, b009, b010

### `slots/blender/rendering.py`
- `class RenderingSlots(RenderingMixin, SlotsBlender)`
  - methods: tb000_init, tb000, tb001_init, tb001, b000, b001, b003, b004

### `slots/blender/rigging.py`
- `class RiggingSlots(RiggingMixin, SlotsBlender)`
  - methods: header_init, b020, cmb001_init, cmb001, tb000_init, tb000, tb001_init, tb001, tb003_init, tb003, tb004_init, tb004, tb005_init, tb005, cmb002_init, cmb002, b004

### `slots/blender/scene.py`
- `class SceneSlots(SceneMixin, SlotsBlender)`
  - methods: list003, list000_init, list000, cmb002_init, cmb002, list001_init, list001, list002_init, list002, tb003_init, b011, b001, b010, b016, b005, b008, b013, b_cleanup, b004, b003, b015, b017

### `slots/blender/selection.py`
- `class SelectionSlots(SelectionMixin, SlotsBlender)`
  - methods: tb000_init, tb000, tb001_init, tb001, tb002_init, tb002, tb003_init, tb003, list001, chk004_init, chk004, chk005_init, chk006_init, chk007_init, chk005, chk006, chk007, b001, b002_init, b002, b003_init, b003, b004_init, b004, b005_init, b005, b006_init, b006, b007_init, b007, cmb002_init, cmb002, cmb001_init, cmb001, list000_init, tb004_init, list000

### `slots/blender/settings.py`
- `class SettingsSlots(SettingsMixin, SlotsBlender)`
  - methods: tb001

### `slots/blender/subdivision.py`
- `class SubdivisionSlots(SlotsBlender)`
  - methods: tb000_init, tb000, s000_init, s001_init, s000, s001, b000, b001, b005, b008, b011, b028

### `slots/blender/symmetry.py`
- `class SymmetrySlots(SlotsBlender)`
  - methods: chk000_init, chk001_init, chk002_init, chk000, chk001, chk002, chk004, chk004_init, chk005_init, chk005

### `slots/blender/transform.py`
- `class TransformSlots(TransformMixin, SlotsBlender)`
  - methods: header_init, b_snap_ts, fix_non_ortho_axes, tb000_init, tb000, tb002_init, tb002, tb005_init, tb005, b001, cmb002_init, cmb002, tb004_init, tb004, s023, chk023_init, chk023, tb001, b002_init, b_restore_axes, b002, tb003_init, chk024, chk025, chk026

### `slots/blender/utilities.py`
- `class UtilitiesSlots(SlotsBlender)`
  - methods: b000, b001, b002, b003

### `slots/blender/uv.py`
- `class UvSlots(UvMixin, SlotsBlender)`
  - methods: tb000_init, tb000, tb001_init, tb001, tb004_init, tb004, tb009_init, tb009, b005, b011, b021, tb007_init, tb007, header_init, uv_snapshot, b031, b003, b004, b029, tb022_init, tb022, b030, b032, b033

### `slots/maya/_slots_maya.py`
- `class SlotsMaya(Slots)`
  - methods: require_selection

### `slots/maya/animation.py`
- `class AnimationSlots(AnimationMixin, SlotsMaya)`
  - methods: list000, b001, tb000_init, tb000, tb001_init, tb001, tb002_init, tb002, tb003_init, tb003, tb004_init, tb004, tb005_init, tb005, tb006_init, tb006, tb007_init, tb007, tb008_init, tb008, tb009_init, tb009, tb010_init, tb010, tb011_init, tb011, tb013_init, tb013, tb014_init, tb014, tb015_init, tb015, tb021_init, tb021, tb016_init, tb016, tb017_init, tb017, tb012_init, tb012, tb018_init, tb018, tb019_init, tb019, tb020, b000, b004, b005, b006

### `slots/maya/arnold.py`
- `class ArnoldSlots(SlotsMaya)`

### `slots/maya/cache.py`
- `class CacheSlots(SlotsMaya)`

### `slots/maya/cameras.py`
- `class CamerasSlots(SlotsMaya)`
  - methods: list000_init, list000, b000, b001, b002, b003, b004, b005, b006, b007, b010, b011, b012, b013

### `slots/maya/constrain.py`
- `class ConstrainSlots(SlotsMaya)`

### `slots/maya/control.py`
- `class ControlSlots(SlotsMaya)`

### `slots/maya/crease.py`
- `class CreaseSlots(SlotsMaya)`
  - methods: tb000_init, tb000, b002

### `slots/maya/curves.py`
- `class CurvesSlots(SlotsMaya)`

### `slots/maya/deform.py`
- `class DeformSlots(SlotsMaya)`

### `slots/maya/deformation.py`
- `class DeformationSlots(SlotsMaya)`
  - methods: tb001_init, tb001

### `slots/maya/display.py`
- `class DisplaySlots(DisplayMixin, SlotsMaya)`
  - methods: list000, b000, b001, b002, b003, b004, b005, b006, b007, b009, b011, b012, b013, b014, b021, b022, b023, b024

### `slots/maya/duplicate.py`
- `class DuplicateSlots(DuplicateMixin, SlotsMaya)`
  - methods: tb002_init, tb002, tb000_init, tb000, tb001_init, tb001, b000, b005, b006, b007, b008

### `slots/maya/edit.py`
- `class EditSlots(EditMixin, SlotsMaya)`
  - methods: header_init, tb000_init, tb000, tb001_init, tb001, tb002, tb004_init, tb004, b_channels, b000, list000_init, list000, list001_init, list001, cmb000

### `slots/maya/edit_mesh.py`
- `class EditMeshSlots(SlotsMaya)`

### `slots/maya/editors.py`
- `class EditorsSlots(SlotsMaya)`
  - methods: list000_init, list000, b000, b001, b002, b003, b004, b005, b006, b007, b008, b009, b010, b011, b012, b013, getEditorWidget

### `slots/maya/effects.py`
- `class EffectsSlots(SlotsMaya)`

### `slots/maya/fields_solvers.py`
- `class FieldsSolversSlots(SlotsMaya)`

### `slots/maya/fluids.py`
- `class FluidsSlots(SlotsMaya)`

### `slots/maya/generate.py`
- `class GenerateSlots(SlotsMaya)`

### `slots/maya/help.py`
- `class HelpSlots(SlotsMaya)`

### `slots/maya/hud.py`
- `class StatusMixin`
  - methods: insert_scene_status
- `class HudSelectionMixin`
  - methods: insert_selection_info, insert_component_info
- `class WarningsMixin(HudWarningsMixin)`
- `class HudSlots(SlotsMaya, pythontk.PackageManager, StatusMixin, HudSelectionMixin, WarningsMixin)`
  - methods: request_hud_build, construct_hud

### `slots/maya/key.py`
- `class KeySlots(SlotsMaya)`

### `slots/maya/lighting.py`
- `class LightingSlots(LightingMixin, SlotsMaya)`
  - methods: b000, b001, b002, tb000_init, tb000

### `slots/maya/lighting_shading.py`
- `class LightingShadingSlots(SlotsMaya)`

### `slots/maya/main.py`
- `class MainSlots(MainMixin, SlotsMaya)`
  - methods: list000_init, list000

### `slots/maya/mash.py`
- `class MashSlots(SlotsMaya)`

### `slots/maya/materials.py`
- `class MaterialsSlots(MaterialsMixin, SlotsMaya)`
  - methods: b007, list000_init, list000, list001, select_by_mat, b015, lbl004, lbl006, b004, b008, b009, b026, b027, b010, b011, b013, b016, b018, tb001_init, tb001, tb002_init, tb002, b021, b019, b020, b022, b023, b024, b025

### `slots/maya/mesh.py`
- `class MeshSlots(SlotsMaya)`

### `slots/maya/mesh_display.py`
- `class MeshDisplaySlots(SlotsMaya)`

### `slots/maya/mesh_tools.py`
- `class MeshToolsSlots(SlotsMaya)`

### `slots/maya/ncloth.py`
- `class NClothSlots(SlotsMaya)`

### `slots/maya/nconstraint.py`
- `class NConstraintSlots(SlotsMaya)`

### `slots/maya/nhair.py`
- `class NHairSlots(SlotsMaya)`

### `slots/maya/nparticles.py`
- `class NParticlesSlots(SlotsMaya)`

### `slots/maya/nurbs.py`
- `class NurbsSlots(NurbsMixin, SlotsMaya)`
  - methods: list000, b056, b058, tb000_init, tb000, tb001_init, tb001, b016, b030

### `slots/maya/pivot.py`
- `class PivotSlots(PivotMixin, SlotsMaya)`
  - methods: tb000_init, tb000, tb001_init, tb001, tb002_init, tb002, tb003_init, tb003, b004

### `slots/maya/playback.py`
- `class PlaybackSlots(SlotsMaya)`

### `slots/maya/polygons.py`
- `class PolygonsSlots(SlotsMaya)`
  - methods: header_init, chk008, chk009, chk010, tb000_init, tb000, tb002_init, tb002, tb003_init, tb003, tb004_init, tb004, tb005_init, tb005, tb006_init, tb006, tb007_init, tb007, tb008_init, tb008, tb009_init, tb009, b000, b001, b003, b005, b006, b007, b008, b009, b011, b012, b022, b032, b034, b038, b043, b047, b049, b051, b053

### `slots/maya/preferences.py`
- `class PreferencesSlots(PreferencesMixin, SlotsMaya)`
  - methods: cmb001_init, cmb001, cmb002_init, cmb002, s000_init, s001_init, b001, cmb003_init, cmb003, b008, b009, b010

### `slots/maya/render.py`
- `class RenderSlots(SlotsMaya)`

### `slots/maya/rendering.py`
- `class RenderingSlots(RenderingMixin, SlotsMaya)`
  - methods: tb000_init, tb000, tb001_init, tb001, b000, b001, b003, b004

### `slots/maya/rigging.py`
- `class RiggingSlots(RiggingMixin, SlotsMaya)`
  - methods: header_init, b020, cmb001_init, cmb001, cmb002_init, cmb002, chk000, chk001, chk002, s000, tb000_init, tb000, tb001_init, tb001, tb003_init, tb003, tb004_init, tb004, tb005_init, tb005, b004

### `slots/maya/scene.py`
- `class SceneSlots(SceneMixin, SlotsMaya)`
  - methods: list003, cmb002_init, cmb002, list001_init, list001, list002_init, list002, list000_init, list000, b001, b010, b016, tb003_init, b004, b005, b006, b009, b011, b018, b012, b017, b013, b014_init, b014

### `slots/maya/select.py`
- `class SelectSlots(SlotsMaya)`

### `slots/maya/selection.py`
- `class SelectionSlots(SelectionMixin, SlotsMaya)`
  - methods: list000_init, list000, tb004_init, cmb002_init, cmb002, cmb001_init, cmb001, list001, b002_init, b002, b003_init, b003, b004_init, b004, b005_init, b005, b006_init, b006, b007_init, b007, chk000, chk001, chk002, chk005_init, chk005, chk006, chk007, chk004, chkxxx, tb000_init, tb000, tb001_init, tb001, tb002_init, tb002, tb003_init, tb003, b001, get_selection_tool, set_selection_tool

### `slots/maya/settings.py`
- `class SettingsSlots(SettingsMixin, SlotsMaya)`
  - methods: tb001

### `slots/maya/skeleton.py`
- `class SkeletonSlots(SlotsMaya)`

### `slots/maya/skin.py`
- `class SkinSlots(SlotsMaya)`

### `slots/maya/stereo.py`
- `class StereoSlots(SlotsMaya)`

### `slots/maya/subdivision.py`
- `class SubdivisionSlots(SlotsMaya)`
  - methods: s000_init, s001_init, s000, s001, b000, b001, b005, tb000_init, tb000, b008, b011, b028, smoothProxy

### `slots/maya/surfaces.py`
- `class SurfacesSlots(SlotsMaya)`

### `slots/maya/symmetry.py`
- `class SymmetrySlots(SlotsMaya)`
  - methods: chk000_init, chk000, chk001, chk002, chk004, chk005_init, chk005

### `slots/maya/texturing.py`
- `class TexturingSlots(SlotsMaya)`

### `slots/maya/toon.py`
- `class ToonSlots(SlotsMaya)`

### `slots/maya/transform.py`
- `class TransformSlots(TransformMixin, SlotsMaya)`
  - methods: header_init, cmb002_init, cmb002, tb000_init, tb000, tb001, tb002_init, tb002, tb003_init, tb004_init, tb005_init, tb005, chk021, chk022, chk023, chk024, chk025, chk026, s021, s022, s023, b_snap_ts, b001, b002_init, b_restore_axes, b002, setTransformSnap

### `slots/maya/utilities.py`
- `class UtilitiesSlots(SlotsMaya)`
  - methods: b000, b001, b002, b003

### `slots/maya/uv.py`
- `class UvSlots(UvMixin, SlotsMaya)`
  - methods: header_init, tb000_init, tb000, tb001_init, tb001, tb004_init, tb004, tb007_init, tb007, tb009_init, tb009, b003, b004, b005, b011, b021, tb022_init, tb022, b029, b030, b031, b032, b033

### `slots/maya/visualize.py`
- `class VisualizeSlots(SlotsMaya)`

### `slots/maya/windows.py`
- `class WindowsSlots(SlotsMaya)`

### `slots/normals.py` — Normals: one Slots class for both hosts.
- `class NormalsSlots(Slots)`
  - methods: tb001_init, tb001, tb004_init, tb004, b000, b001, b002, b004, b006, tb010_init, tb010

### `slots/tools/__init__.py` — Each shared tool's one Slots class, paired by name with its ``ui/tools/<tool>.ui``
- constants: HOSTS

### `slots/tools/_app_bridge/host_bridge.py` — The app-bridge panels' one base, shared by both hosts.
- `class HostBridge(Slots.BridgeSlotsBase)`
  - methods: bridge_class, make_bridge, params_module, template_dir, list_template_modes, PRESETS_ROOT, resolve_scope_objects, scoped_objects, live_param_tooltip_blocks, set_bake_source_from_selection, select_bake_source, clear_bake_source

### `slots/tools/_blendshape_animator/sort_item.py` — A tween-tree row that sorts its numeric columns by number.
- `class NumericSortItem(QtWidgets.QTreeWidgetItem)`

### `slots/tools/_channels/attribute_form.py` — The Create Attribute popup: a one-shot form over the host's attribute types.
- `class AttributeForm`
  - methods: show

### `slots/tools/_channels/enum_cell.py` — The value cell of an enum attribute: its labels in a combobox, plus Rename /
- `class EnumCell`
  - methods: build, show_index

### `slots/tools/_channels/inline_rename.py` — Rename the panel's target in place: the target field, and the footer in
- `class InlineRename`
- `class FooterRename`
  - methods: edit

### `slots/tools/_hierarchy_sync/controller.py` — The Hierarchy Sync panel's state: the reference path, the paths the user
- constants: RECENT_LIMIT, LOG_LIMIT
- `class HierarchySyncController(pythontk.LoggingMixin)`
  - methods: diff_result, reference_path, update_header_tooltips, clear_analysis, on_window_hidden, populate_reference_tree, refresh_trees, refresh_styling, ignored_set, is_path_ignored, clear_ignored_paths, effective_diff, log_diff_results, write_diff_report, coerce_str_list, get_recent_reference_scenes, save_recent_reference_scene

### `slots/tools/_hierarchy_sync/tree_matcher.py` — Find the Hierarchy Sync trees' items by the hierarchy paths a diff names.
- constants: PLACEHOLDERS
- `class TreePathMatcher(pythontk.LoggingMixin)`
  - methods: iter_items, item_path, raw_item_path, item_key, build_tree_index, find_path_matches, log_matching_debug

### `slots/tools/_hierarchy_sync/tree_renderer.py` — The Hierarchy Sync trees: filling them, the diff's colours, the ignored
- constants: ORIG_TOOLTIP_ROLE, BROWSE_PLACEHOLDER, OPEN_SCENE_PLACEHOLDER
- `class HierarchyTreeRenderer(pythontk.LoggingMixin)`
  - methods: session, matcher, populate_current_scene_tree, populate_reference_tree, show_reference_placeholder, show_reference_error, populate_tree_with_hierarchy, apply_difference_formatting, clear_tree_colors, format_tree_differences, apply_ignore_styling, build_item_path, selected_item_keys, get_selected_tree_items, count_tree_items, store_tree_selection, restore_tree_selection, get_tree_structure, condense_to_roots, filter_to_leaves, apply_diff_options

### `slots/tools/_reference_manager/controller.py` — The Reference Manager panel's controller: the browsed workspace, the table
- `class ReferenceManagerController(pythontk.LoggingMixin)`
  - methods: tk, norm, role, table_signals_blocked, message, report, error_box, footer_status, header_menu, naming_options, type_extensions, include_type_checked_by_default, include_type_tooltip, included_extensions, is_importable, foreign_route, filter_menu, scene_notes, note, migrate_settings_notes, set_note, refresh_file_list, update_table, update_listing_footer, format_table_item, row_references, sync_reference_icons, sync_selection_to_references, handle_item_selection, apply_notes_column_visibility, refilter_on_naming_change, row_path, capture_context_row, context_row, label_open_action, select_item_silently, prepare_item_for_edit, restore_item_display, item_double_clicked, item_changed, editor_closed

### `slots/tools/_reference_manager/listing.py` — The Reference Manager's listing rules: how a scene file reads as a row and
- `class SceneListing`
  - methods: display_name, split_patterns, text_matches_filter, matches_notes_filter, scenes_folder, format_name, strip_all_suffixes, filter_by_folder_structure, delete_prompt

### `slots/tools/_reference_manager/references.py` — The Reference Manager's reference actions: a row's reference and display
- `class ReferenceActions`
  - methods: toggle_reference_at_row, cycle_display_mode_at_row, add_unlink_namespace_action, unlink_namespace_mode, ask_scene_data, unlink_references, unlink_import_row, unlink_all, unreference_all, convert_to_assembly

### `slots/tools/_reference_manager/scene_files.py` — The Reference Manager's scene files: open / close / save / rename / delete, the
- `class SceneFiles`
  - methods: normalize_structure_pattern, default_save_name, resolve_save_target, save_scene_preview, folder_structure_preview, wire_structure_tooltip, open_scene_at_row, confirm_discard_unsaved, save_current_scene, open_path, close_scene, save_to_workspace, rename_path, rename_scene, delete_scene, open_file_location, copy_path, resolve_rig_mode, resolve_conversion, conversion_progress, bake_foreign_path, import_paths

### `slots/tools/_reference_manager/workspaces.py` — The Reference Manager's workspace browser: the Root Directory, the workspace
- `class WorkspaceBrowser`
  - methods: root_dir, workspace_dir, save_workspace_selection, restore_workspace_index, update_current_dir, update_workspace_combo, set_workspace, update_workspace_footer, flash_footer, set_project, set_root_to_current, open_root_dir, new_workspace, mark_workspace, select_workspace

### `slots/tools/_shot_manifest/controller.py` — The Shot Manifest panel's controller: its state, the steps the table shows,
- `class ShotManifestController(ManifestTableMixin, RangeColumnMixin, StoreFollowMixin, ManifestSourceMixin, MappingPickerMixin, RowMenusMixin, HeaderMenuMixin, ViewCombosMixin, ExportPreviewMixin, pythontk.LoggingMixin)`
  - methods: build, assess

### `slots/tools/_shot_manifest/export_preview.py` — The Shot Manifest's Export button (beside Assess): a live preview of the
- `class ExportPreviewMixin`
  - methods: export

### `slots/tools/_shot_manifest/header_menu.py` — The Shot Manifest's header menu: Long Names, Local Edits' Edits mode and
- `class HeaderMenuMixin`

### `slots/tools/_shot_manifest/manifest_data.py` — Constants, column layout, and pure helper functions for the Shot Manifest UI.
- constants: SETTINGS_NS, HEADERS, COL_STEP, COL_SECTION, COL_DESC, COL_BEHAVIORS, COL_START, COL_END, STEP_ICON_COLOR, PASTEL_STATUS, ERROR_COLOR
- `class ManifestData`
  - methods: level, status_color, worst, glyph_html, issues_html, fmt_behavior, format_behavior_html

### `slots/tools/_shot_manifest/manifest_editor.py` — Local Edits for the Shot Manifest panel: change the table, never the sheet.
- `class ManifestEditor`
  - methods: enabled, add_header_options, edits_mode, view_original, refuse_viewing, reset, source_key, load, save, apply, stale, refresh, refuse_locked, begin_edit, commit_edit, set_behaviors, add_menu_actions, add_step, add_shot, remove_step, hide_steps, unlocked_hidden_objects, show_hidden_objects, hide_object, move_object, rename_all, revert_step, revert_object, decorate

### `slots/tools/_shot_manifest/manifest_source.py` — Where the Shot Manifest's steps come from: a build sheet (a CSV path or link,
- `class ManifestSourceMixin`
  - methods: detect

### `slots/tools/_shot_manifest/mapping_picker.py` — The Shot Manifest's mapping template: its own popup on the build sheet
- `class MappingPickerMixin`

### `slots/tools/_shot_manifest/range_column.py` — The Shot Manifest table's Start / End column: what a step's range is
- `class RangeColumnMixin`

### `slots/tools/_shot_manifest/row_menus.py` — The Shot Manifest rows' context menus and what they do: a step row's (colour
- `class RowMenusMixin`

### `slots/tools/_shot_manifest/store_follow.py` — The Shot Manifest panel following the scene's store: its events (a shot
- `class StoreFollowMixin`
  - methods: remove_callbacks

### `slots/tools/_shot_manifest/table_presenter.py` — The Shot Manifest tree's rows: populating them (``ShotPairing.rows``: steps,
- `class ManifestTableMixin`
  - methods: expand_missing, expand_extra

### `slots/tools/_shot_manifest/view_combos.py` — The Shot Manifest's view row, above the table: Select, Expand, Collapse,
- `class ViewCombosMixin`

### `slots/tools/_shot_sequencer/clip_menu.py` — Clip context menus and clip-level key operations.
- `class ClipMenuMixin`
  - methods: on_clip_menu, on_gap_menu

### `slots/tools/_shot_sequencer/clip_motion.py` — Clip and key motion for the Shot Sequencer panel: moving and resizing clips,
- constants: FLOAT_ZERO_EPS, KEY_MATCH_EPS
- `class ClipMotionMixin`
  - methods: on_clip_resized, on_clips_batch_resized, on_clip_moved, on_clips_batch_moved, on_keys_moved, on_keys_batch_moved, on_keys_deleted

### `slots/tools/_shot_sequencer/controller.py` — The Shot Sequencer panel's controller: :class:`ShotSequencerController`.
- `class ShotSequencerController(SceneCallbacksMixin, UndoLedgerMixin, ShotLaneMixin, ClipMenuMixin, KeyMenuMixin, WidgetSyncMixin, SceneSelectionMixin, TransportMixin, GapManagerMixin, ClipMotionMixin, ShotNavMixin, MarkerManagerMixin, pythontk.LoggingMixin)`
  - methods: host, sequencer, active_shot_id

### `slots/tools/_shot_sequencer/gap_manager.py` — Gap and range-highlight handlers for the Shot Sequencer controller.
- constants: TIME_SNAP_EPS
- `class GapManagerMixin`
  - methods: on_range_highlight_changed, on_gap_resized, on_gap_left_resized, on_gap_moved, on_gap_lock_changed, on_gap_lock_all, on_gap_unlock_all

### `slots/tools/_shot_sequencer/key_menu.py` — Key context menus and the edits run over a key selection, for the Shot
- `class KeyMenuMixin`
  - methods: on_key_menu, on_keys_tangent_dragged, register_key_targets

### `slots/tools/_shot_sequencer/marker_manager.py` — Marker persistence for the shot sequencer controller.
- `class MarkerManagerMixin(_MarkerManagerMixinInternal)`
  - methods: on_marker_added, on_marker_moved, on_marker_changed, on_marker_removed

### `slots/tools/_shot_sequencer/scene_callbacks.py` — Scene events for the shot sequencer: undo/redo, key edits, time changes.
- `class SceneCallbacksMixin`
  - methods: remove_callbacks

### `slots/tools/_shot_sequencer/scene_selection.py` — Tracks and the scene selection.
- `class SceneSelectionMixin`
  - methods: hide_track, show_track, delete_track, on_selection_changed, on_track_selected, on_sub_track_selected, on_clip_locked, on_track_menu, on_header_menu, on_key_selection_changed, on_clip_renamed

### `slots/tools/_shot_sequencer/shot_edit_dialog.py` — The Shot Sequencer's small shot dialog: :class:`ShotEditDialog`.
- `class ShotEditDialog`
  - methods: show

### `slots/tools/_shot_sequencer/shot_lane.py` — The shot lane: its context menu and the shot structure edits.
- `class ShotLaneMixin`
  - methods: on_zone_context_menu, delete_shot, delete_shots, move_shot_to_position, merge_shot_with, split_shot_at

### `slots/tools/_shot_sequencer/shot_layer.py` — The shot layer: the Shot Sequencer's shots on uitk's timeline.
- `class GapOverlay`
  - methods: item_class, boundingRect, hoverEnterEvent, hoverLeaveEvent, hoverMoveEvent, mousePressEvent, mouseMoveEvent, mouseReleaseEvent, contextMenuEvent, paint
- `class ShotLayer(QtCore.QObject)`
  - methods: of, set_shot_blocks, clear_shot_blocks, selected_shot, shot_block_at, add_gap_overlay, clear_gap_overlays, set_all_gap_overlays_locked, show_gap_overlays, paint_lane, mouse_press, mouse_move, mouse_release, gesture_group_at, claims_press, legend, context_entries, menu_zone, time_bounds, relayout, clear

### `slots/tools/_shot_sequencer/shot_nav.py` — Shot navigation and combobox synchronization.
- `class ShotNavMixin`
  - methods: select_shot, on_shot_block_clicked

### `slots/tools/_shot_sequencer/transport.py` — Transport: the playhead, audio scrub and the transport row.
- `class TransportMixin`
  - methods: on_playhead_moved

### `slots/tools/_shot_sequencer/undo_ledger.py` — The shot sequencer's undo ledger.
- `class UndoLedgerMixin`
  - methods: on_undo, on_redo

### `slots/tools/_shot_sequencer/widget_sync.py` — Widget sync: rebuilding the sequencer from the scene.
- `class WidgetSyncMixin`
  - methods: refresh

### `slots/tools/_shots/controller.py` — The Shots panel's controller: the scene's shot settings, the selected shot's
- `class ShotsController(pythontk.LoggingMixin)`
  - methods: remove_callbacks, refresh_state, shot_label, on_navigate_shot, on_new_shot, on_detection_changed, on_detection_mode_changed, on_initial_length_changed, on_snap_whole_frames_changed, on_drop_stale_shots_changed, on_fit_mode_changed, on_gap_changed, on_shot_selected, on_shot_name_changed, on_shot_start_changed, on_shot_end_changed, on_shot_desc_changed, delete_scope, label_delete_shots, swap_mode, swap_target, swap_retain, label_swap_shot, label_shift_all, label_apply_gap, on_delete_shot, confirm_removal, on_delete_shots, on_move_shot, on_swap_shot, on_trim_empty, on_trim_all_shots, on_shift_all_shots, on_add_space

### `slots/tools/_texture_combine/transfer_mode.py` — The Texture Combine panel's Transfer mode: UVs or textures, source -> targets.
- `class TransferMode`
  - methods: ui, tk, terms, init_transfer, init_source, init_targets, init_resolution, init_uv_sets, init_lightmaps, source_tooltip, capture_source, select_source, clear_source, passes, resolve_auto, source_note, auto_note, pair, gate, lightmap_probe, sync, run, derived_name, texture_pass, read_files, overwrite_note, lightmap_pass

### `slots/tools/_unity_bridge/_unity_panel.py` — What every Unity panel shares: the 'Unity Project' row, the Editor combo, script management.
- `class UnityPanelMixin`
  - methods: template_dir, list_template_modes, default_output_dir

### `slots/tools/arnold_bridge.py` — Arnold Preview Shader: add or remove the Arnold preview network beside each
- `class ArnoldBridgeSlots(Slots, pythontk.LoggingMixin)`
  - methods: header_init, cmb000_init, b000, b001, select_bridged

### `slots/tools/articulated_rig.py` — Articulated Rig: rig a prop of rigid parts on hinges, swivels, balls and
- `class ArticulatedRigSlots(Slots, pythontk.LoggingMixin)`
  - methods: header_init, btn_ik_fk_init, parse_limits, refresh_table, btn_analyze, btn_build, btn_grab, btn_ik_fk, match_end_control, btn_rest, btn_insert, btn_fold, btn_limits_from_pose, btn_clear_limits, btn_rebuild, btn_remove

### `slots/tools/audio_clips.py` — Audio Clips: the scene's audio files, placed on the timeline.
- `class AudioClipsSlots(Slots)`
  - methods: noun, header_init, btn_export, btn_channels, cmb000_init, cmb000, select_track, btn_add_tracks, btn_rename_track, btn_replace_track, btn_remove_selected, btn_cleanup_unused, btn_remove_audio, tb001_init, tb001, btn_select_carrier, btn_sync_audio, s000_init, s001_init, b003_init, b003, b004_init, b004

### `slots/tools/bevel.py` — Bevel: chamfer the selected polygon edges, with a live preview.
- `class BevelSlots(Slots)`
  - methods: header_init, perform_operation

### `slots/tools/blender_bridge.py` — Blender Bridge: send the selection to a fresh Blender through an import
- `class BlenderBridgeSlots(HostBridge)`
  - methods: bridge_class, b000

### `slots/tools/blendshape_animator.py` — Blendshape Animator: build a morph between two meshes, add in-between
- constants: COL_NAME, COL_WEIGHT, COL_FRAME, COL_TOPOLOGY, COL_STATUS, MODE_WEIGHT, MODE_FRAME, STATUS_KEYS
- `class BlendshapeAnimatorSlots(Slots)`
  - methods: header_init, b000_init, b000, cmb000_init, le000_init, le001_init, b001_init, b001, b003, b004_init, b004, b005, b006_init, b006, b007, b008_init, b008

### `slots/tools/bridge.py` — Bridge: connect two open edge loops with new polygon faces, with a live preview.
- `class BridgeSlots(Slots)`
  - methods: header_init, perform_operation

### `slots/tools/calculator.py` — Calculator: expressions, length units, and the scene's frame-rate helpers.
- `class CalculatorSlots(Slots)`
  - methods: header_init, on_input, on_clear, on_backspace, on_equal, on_convert_units, get_fps, get_current_time, frames_to_sec, sec_to_frames

### `slots/tools/channels.py` — Channels: the selected objects' attributes in one editable table.
- `class ChannelsSlots(Slots)`
  - methods: launch, apply_launch_config, header_init, show_create_menu, cmb000_init, cmb000, tbl000_init, cleanup_scene_callbacks

### `slots/tools/color_id.py` — Color ID: color-code objects across channels from a swatch palette.
- `class ColorIdSlots(Slots)`
  - methods: header_init, selected_button, target_color, b000, b001, b002, b003

### `slots/tools/curtain.py` — Curtain: drape a pleated, gravity-sagged cloth curtain from a rail, with a
- `class CurtainSlots(Slots)`
  - methods: header_init, cmb000_init, b001_init, b002, perform_operation

### `slots/tools/curve_to_tube.py` — Curve to Tube: sweep a circular profile along the selected curves into a
- `class CurveToTubeSlots(Slots)`
  - methods: header_init, b001_init, perform_operation

### `slots/tools/cut_on_axis.py` — Cut On Axis: slice the selected meshes along an axis, then optionally delete
- `class CutOnAxisSlots(Slots)`
  - methods: header_init, toggle_weight_ui, perform_operation

### `slots/tools/duplicate_grid.py` — Duplicate Grid: copies of the selection in a 3D grid.
- `class DuplicateGridSlots(Slots)`
  - methods: header_init, b001_init, perform_operation

### `slots/tools/duplicate_linear.py` — Duplicate Linear: copies of the selection along a line, each interpolating
- constants: INTERPOLATION_MODES
- `class DuplicateLinearSlots(Slots)`
  - methods: header_init, toggle_weight_ui, b001_init, perform_operation

### `slots/tools/duplicate_radial.py` — Duplicate Radial: copies of the selection in a radial pattern about a pivot.
- `class DuplicateRadialSlots(Slots)`
  - methods: header_init, s015_init, s016_init, b001_init, perform_operation, regroup_copies

### `slots/tools/dynamic_pipe.py` — Dynamic Pipe: a pipe mesh that follows a chain of handles live.
- `class DynamicPipeSlots(Slots)`
  - methods: header_init, b000

### `slots/tools/emissive_groups.py` — Emissive Groups: named face groups whose emissive regions a game engine gates.
- `class EmissiveGroupsSlots(Slots)`
  - methods: header_init, txt000_init, tbl000_init, b000, b001, b002, b003, tb000_init, tb000, select_members, remove_group, weights_all_on, weights_all_off, make_weights_keyable, key_weights, remove_keyable_weights, compact_slots, republish_export

### `slots/tools/exploded_view.py` — Exploded View: spread the selected objects apart to inspect interior parts.
- `class ExplodedViewSlots(Slots)`
  - methods: header_init, b000, b001, b002, b003

### `slots/tools/game_shader.py` — Game Shader: build a PBR material from a set of texture maps, packed for a
- `class GameShaderSlots(Slots, pythontk.LoggingMixin)`
  - methods: header_init, lbl_graph_material, mat_name, mat_prefix, mat_suffix, normal_map_type, output_extension, shader_type, opacity_mode, cmb002_init, cmb003_init, cmb004_init, txt000_init, txt002_init, b000

### `slots/tools/hdr_manager.py` — HDR Manager: light the scene from an HDR environment map, spin it and adjust
- `class HdrManagerSlots(Slots, pythontk.LoggingMixin)`
  - methods: header_init, cmb000_init, hdr_map, hdr_map_visibility, hdr_map_preview, cmb000, slider000, spn_intensity, spn_exposure, spn_resolution, spn_samples, spn_diffuse, spn_specular, add_hdr, open_sourceimages, clear_network, ctx_select_skydome, ctx_select_transform, ctx_select_file_node, ctx_reveal_in_explorer

### `slots/tools/hierarchy_sync.py` — Hierarchy Sync: diff the scene's hierarchy against a reference file, then
- `class HierarchySyncSlots(Slots, pythontk.LoggingMixin)`
  - methods: session, header_init, tree000_init, tree001_init, cmb_diff_options_init, cmb_pull_options_init, tb002_init, tb003_init, tb001, tb002, tb003, b003, b009, b011, b012, b005, b006, b007, b008, b013, b014, b015, b016, b017, b018

### `slots/tools/image_to_plane.py` — Image to Plane: batch-create textured planes from image files.
- `class ImageToPlaneSlots(Slots)`
  - methods: header_init, txt_suffix_init, b000, b004, b001, b002

### `slots/tools/image_tracer.py` — Image Tracer: trace a raster image's contours into curves, then fill them
- `class ImageTracerSlots(Slots)`
  - methods: header_init, txt000_init, chk000, blue_pencil_button, b002, b003, b004, b005

### `slots/tools/key_stash.py` — Key Stash: park keys out of the working animation as clips, then preview or
- `class KeyStashSlots(Slots, pythontk.LoggingMixin)`
  - methods: header_init, store, refresh, refresh_from_scene, b000, b001, chk001, b003

### `slots/tools/light_rig.py` — Light Rigs: save the scene's lights as named rigs, swap between them and
- `class LightRigSlots(Slots, pythontk.LoggingMixin)`
  - methods: refresh, header_init, cmb000_init, cmb000, b000, b001, open_rig_folder, prompt_save

### `slots/tools/lightmap_baker.py` — Lightmap Baker: bake the scene's lighting into lightmaps the engine reads.
- `class LightmapBakerSlots(Slots, pythontk.LoggingMixin)`
  - methods: header_init, cmb000_init, btn_reset_defaults_init, cmb002_init, cmb_scope_init, set_exclusions_init, set_exclusions, select_exclusions, clear_exclusions, set_isolation_init, set_isolation, select_isolation, clear_isolation, cmb_resolution_init, spn_samples_init, spn_gi_samples_init, spn_bounces_init, cmb_device_init, txt_output_dir_init, txt000_init, b000, cmb_page_init, cmb_page, tbl_maps_init, select_by_state, open_map_folder, combine_selected, fix_all, track_selected, revert_selected, rebake_selected, show_bake_state, open_output

### `slots/tools/marmoset_bridge.py` — Marmoset Bridge: send the selection to Marmoset Toolbag through a template.
- `class MarmosetBridgeSlots(HostBridge)`
  - methods: bridge_class, select_initial_template_index, b000

### `slots/tools/mat_updater.py` — Material Updater: rework scene materials for a target workflow preset,
- `class MatUpdaterSlots(Slots)`
  - methods: logger, header_init, selection_mode, move_to_folder, shader_type, cmb001_init, b001

### `slots/tools/maya_bridge.py` — Maya Bridge: send the selection to a fresh Maya through an import template.
- `class MayaBridgeSlots(HostBridge)`
  - methods: bridge_class, b000

### `slots/tools/mirror.py` — Mirror: mirror the selected meshes across an axis, with a live preview.
- `class MirrorSlots(Slots)`
  - methods: header_init, prepare_operation, perform_operation

### `slots/tools/naming.py` — Naming: batch find / rename / convert-case / strip-chars / suffix-by-location /
- `class NamingSlots(Slots)`
  - methods: logger, header_init, scope, dry_run, file_scope, base_names, valid_suffixes, txt000_init, txt000, txt001_init, txt001, tb000_init, tb000, tb001_init, tb001, tb002_init, tb002, tb003_init, tb003

### `slots/tools/reference_manager.py` — Reference Manager: a workspace scene-file manager -- browse a project's scene
- `class ReferenceManagerSlots(Slots)`
  - methods: header_init, tbl000_init, btn_open_scene, btn_rename_scene, btn_delete_scene, btn_toggle_reference, btn_unlink_import, btn_open_file_location, btn_copy_path, txt000_init, b000, b006, b001, btn_new_workspace, btn_mark_workspace, chk000, chk003, cmb000_init, cmb000, txt001_init, txt001, chk_ignore_case, cmb_filter_target, chk_filter_suffix, chk_filter_folder_structure, chk_hide_suffix, chk_hide_extension, chk_show_notes_column, txt_suffix, txt_subfolder_structure, btn_convert_assembly, btn_unlink_import_all

### `slots/tools/render_effects.py` — Render Effects: key per-object opacity fades and highlight pulses for export.
- `class RenderEffectsSlots(Slots)`
  - methods: header_init, cmb_effect_init, cmb_effect, stk_effects_init, ui_field, focus, unfocus, b000, btn_remove, btn_webxr_init, btn_webxr

### `slots/tools/rizom_bridge.py` — RizomUV Bridge: unwrap or pack the selection in RizomUV with a Lua preset and
- `class RizomBridgeSlots(HostBridge)`
  - methods: bridge_class, params_module, template_dir, list_template_modes, b000, open_uv_editor

### `slots/tools/scene_exporter.py` — Scene Exporter: batch-export the scene through its task/check pipeline.
- `class SceneExporterSlots(Slots, pythontk.LoggingMixin)`
  - methods: confirm, decide_check_failure, workspace, header_init, cmb000_init, txt000_init, output_name_preview, txt001_init, cmb001_init, cmb002_init, cmb007_init, cmb008_init, ignore_groups_init, export_data_node_init, cmb004_init, cmb005_init, b000, b010, b012, b006, b007, b008, save_output_dir, save_output_name

### `slots/tools/shader_templates.py` — Shader Templates: save a material's shader network as a reusable template
- `class ShaderTemplatesSlots(Slots, pythontk.LoggingMixin)`
  - methods: source_images_dir, header_init, lbl_graph_material, lbl_open_templates_dir, cmb002_init, refresh_templates, rename_template_safe, lbl000, lbl001, lbl002, b000, b001, b002

### `slots/tools/shadow_rig.py` — Shadow Rig: a ground plane carrying the targets' projected shadow, built for
- `class ShadowRigSlots(Slots, pythontk.LoggingMixin)`
  - methods: header_init, cmb_type_init, txt_source_init, b003_init, b002_init, b009_init, b001_init, prepare_operation, source_from_selection, reproject_sources, perform_operation, chk_follow_init, chk_follow, s001_init, s001, s002, s003, chk_horizon_preview_init, chk_horizon_preview, b002, b003, apply_source, rebuild_rig, restore_expression, b009, detach_to_plane, b010

### `slots/tools/shell_xform.py` — Shell Xform: move, flip, rotate, straighten, mirror, distribute, align and
- `class ShellXformSlots(Slots)`
  - methods: header_init, cmb_move_scope_init, b023, b024, b025, b026, gather_to_udim, b034, b035, b036, b037, s041, tb005_init, tb005, tb006_init, tb006, tb008_init, tb008, align_u_min, align_u_avg, align_u_max, align_v_min, align_v_avg, align_v_max, linear_align, orient_shells, orient_edges, gather_shells, randomize_shells, open_uv_editor

### `slots/tools/shot_manifest.py` — Shot Manifest: a shot sheet checked against the scene, and the shots built from it.
- `class ShotManifestSlots(Slots)`
  - methods: header_init, btn_settings, b002, b003, b004

### `slots/tools/shot_sequencer.py` — Shot Sequencer: the scene's shots on a timeline -- objects as tracks, keys as
- `class ShotSequencerSlots(Slots, pythontk.LoggingMixin)`
  - methods: header_init, cmb_shot, spn_snap, btn_colors, btn_shortcuts, btn_shot_settings

### `slots/tools/shots.py` — Shots: the scene's shot settings, the selected shot's fields and edits, and
- `class ShotsSlots(Slots)`
  - methods: header_init, spn_detection, cmb_detection_mode, spn_initial_length, cmb_fit_mode, chk_snap_whole_frames, cmb_shot_select, txt_shot_name, spn_shot_start, spn_shot_end, txt_shot_desc, b000, btn_delete_shots, cmb_delete_scope, chk_drop_stale_shots, btn_move_shot, btn_swap_shot, cmb_swap_with, cmb_swap_mode, btn_apply_gap, btn_shift_all, btn_trim_empty, btn_trim_leading, btn_trim_trailing, btn_trim_both, btn_trim_all, btn_trim_all_leading, btn_trim_all_trailing, btn_trim_all_both, btn_add_leading_space, btn_add_trailing_space

### `slots/tools/smart_bake.py` — Smart Bake: bake what drives the scene's animation to keys, reversibly.
- `class SmartBakeSlots(Slots, pythontk.LoggingMixin)`
  - methods: cmb_scope_init, cmb_backup_init, header_init, b000, b001

### `slots/tools/snap.py` — Snap: vertices to a target surface, to the closest target vertex, or to the grid.
- `class SnapSlots(Slots)`
  - methods: header_init, b000_init, b000, b001_init, b001, b002_init, b002

### `slots/tools/substance_bridge.py` — Substance Bridge: send the selection to Substance Painter through a template.
- `class SubstanceBridgeSlots(HostBridge)`
  - methods: bridge_class, select_initial_template_index, b000

### `slots/tools/telescope_rig.py` — Telescope Rig: nested segments that extend and retract between a base and an
- `class TelescopeRigSlots(Slots, pythontk.LoggingMixin)`
  - methods: header_init, build_rig, remove_rig

### `slots/tools/texture_combine.py` — Texture Combine: several materials into one atlas and one material, in
- `class TextureCombineSlots(Slots, pythontk.LoggingMixin)`
  - methods: header_init, cmb_mode_init, open_output_folder, cmb_set_init, select_set, recombine_set, restore_set, forget_set, tbl_sources_init, parse_scale, select_row_members, remove_override, reset_scales, b001, b002, cmb_sizing_init, cmb_normalize_init, cmb_atlas_init, s_spacing_init, chk_rotate_init, chk_lightmaps_init, cmb_tt_transfer_init, cmb_tt_source_init, cmb_tt_targets_init, cmb_tt_resolution_init, t_tt_dst_uvset_init, chk_tt_lightmaps_init, t_name_init, record_name, t_output_init, cmb_quality_init, s_padding_init, chk_assign_init, t_affix_init, material_affix, cmb_shader_init, overwrites_target, assign_options, sync_shared, status, b000, combine

### `slots/tools/texture_path_editor.py` — Texture Path Editor: inspect and fix the scene's texture paths.
- `class TexturePathEditorSlots(Slots, pythontk.LoggingMixin)`
  - methods: labels, header_init, tb_set_texture_directory_init, tb_normalize_paths_init, tb_resolve_missing_textures_init, tbl000_init, refresh_texture_table, setup_formatting, open_source_images, reload_scene_textures, tb_set_texture_directory, tb_find_and_copy_textures, tb_normalize_paths, make_paths_absolute, tb_resolve_missing_textures, select_textures_for_objects, select_broken_paths, select_absolute_paths, row_browse_for_file, row_rename_file, handle_cell_edit, select_material, select_file_node, row_show_in_hypershade, delete_file_node, cleanup_scene_callbacks

### `slots/tools/tube_rig.py` — Tube Rig: rig a tube-shaped mesh (hose, cable, piston, tail) with joints,
- `class TubeRigSlots(Slots)`
  - methods: txt000_init, header_init, apply_mode, get_mode, get_strategy, b000, b001, b002, b003, b004, b005, b006, b007

### `slots/tools/unity_bridge.py` — Unity Bridge: export the selection and copy the FBX into a Unity project's Assets/.
- `class UnityBridgeSlots(UnityPanelMixin, HostBridge)`
  - methods: bridge_class, make_bridge, b000

### `slots/tools/wheel_rig.py` — Wheel Rig: wheels that roll as their driver (control) moves, sized by wheel
- `class WheelRigSlots(Slots)`
  - methods: header_init, rig_name, movement_axis, rotation_axis, set_wheel_height, txt000_init, s000_init, update_rig_name_placeholder, b000

### `slots/tools/workspace_editor.py` — Workspace Editor: the minimal take on Maya's File ▸ Project Window -- one
- `class WorkspaceEditorSlots(Slots, pythontk.LoggingMixin)`
  - methods: header_init, txt000_init, tbl000_init, add_rule, reset_row, remove_row, reset_rules, clear_rules, create_project, open_folder

### `slots/tools/workspace_map.py` — Workspace Map: browse a folder tree of project workspaces and switch the
- `class WorkspaceMapSlots(Slots, pythontk.LoggingMixin)`
  - methods: header_init, txt000_init, txt001_init, tree000_init, update_current_dir, update_tree, populate_tree, refresh_tree, selected_workspace, filter_workspaces, b000, b001, b002, set_to_workspace, chk000, btn_open_workspace, btn_explore_folder, new_project, mark_root, save_template

### `tcl.py` — The host-agnostic entry point — one launcher snippet for every DCC.
- `class QtPlatformUnavailable(RuntimeError)`
- `class Tcl(_TclInternal)`
  - methods: host, declared_dists, prepare_reload, reload_packages, dispose_retired, qt_key_name, resolve_key, unserved_tools, register_shared, chord_bindings, banner, launch, engine_dists, engine_install_hint

### `tcl_blender.py` — Blender entry point for tentacle's Qt marking menu — host + keymap bridge + launcher in one.
- `ensure_qapp()`
- `ensure_blender_widget(app)`
- `start_event_pump(app, interval=0.01)`
- `blender_native_window()`
- `launch(**kwargs)`
- `register(**kwargs)`
- `unregister()`
- `reload()`
- `diagnose()`
- `enable_click_debug()`
- `disable_click_debug()`
- `class TclBlender(MarkingMenu)`
  - methods: get_main_window, set_activation_key, showEvent, keyPressEvent, keyReleaseEvent
- `class Diagnostics`
  - methods: report
- `class BlenderHost`
  - methods: launch, register, unregister, reload

### `tcl_max.py`
- `class TclMax(MarkingMenu)`
  - methods: get_main_window, showEvent, hideEvent

### `tcl_maya.py`
- `class TclMaya(MarkingMenu)`

### `tentacle_installer.py` — Install, update or uninstall tentacle in a DCC -- one file, dropped in, no administrator rights.
- `register()`
- `unregister()`
- `onMayaDroppedPythonFile(*_args)`
- `class TentacleInstaller`
  - methods: host, headless, loaded, specs, python_exe, maya_paths, target_dir, is_installed, lock_path, manifest_path, read_manifest, write_manifest, installed_version, install, update, uninstall, request, provision, launch, shutdown, ensure_and_launch, write_maya_module, dropped, register_blender_ui, unregister_blender_ui, main
