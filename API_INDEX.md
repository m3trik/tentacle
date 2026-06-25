# tentacle — API Index

_Auto-generated. Do not edit by hand. Compact symbol index — grep this for a name; for full signatures/docs, slice [API_REGISTRY.md](API_REGISTRY.md) (never Read it whole)._

_Generated: 2026-06-25_

### `__init__.py`
- `greeting(string, outputToConsole=True)`

### `slots/_hud_warnings.py` — Shared HUD warning framework (DCC-agnostic).
- `class HudWarningsMixin`
  - methods: evaluate_warnings, insert_warning_icons, insert_warning_details

### `slots/_slots.py`
- `class Slots(QtCore.QObject)`
  - methods: repeat_last_command

### `slots/maya/_slots_maya.py`
- `class SlotsMaya(Slots)`

### `slots/maya/animation.py`
- `class Animation(SlotsMaya)`
  - methods: header_init, tb000_init, tb000, tb001_init, tb001, tb002_init, tb002, tb003_init, tb003, tb004_init, tb004, tb005_init, tb005, tb006_init, tb006, tb007_init, tb007, tb008_init, tb008, tb009_init, tb009, tb010_init, tb010, tb011_init, tb011, tb013_init, tb013, tb014_init, tb014, tb015_init, tb015, tb016_init, tb016, tb017_init, tb017, tb012_init, tb012, tb018_init, tb018, tb019_init, tb019, tb020_init, tb020, b000, b004, b005

### `slots/maya/arnold.py`
- `class ArnoldSlots(SlotsMaya)`

### `slots/maya/cache.py`
- `class CacheSlots(SlotsMaya)`

### `slots/maya/cameras.py`
- `class Cameras(SlotsMaya)`
  - methods: list000_init, list000, b000, b001, b002, b003, b004, b005, b006, b007, b010, b011, b012, b013, toggle_camera_view

### `slots/maya/constrain.py`
- `class Constrain(SlotsMaya)`

### `slots/maya/control.py`
- `class ControlSlots(SlotsMaya)`

### `slots/maya/crease.py`
- `class Crease(SlotsMaya)`
  - methods: tb000_init, tb000, b002

### `slots/maya/curves.py`
- `class CurvesSlots(SlotsMaya)`

### `slots/maya/deform.py`
- `class DeformSlots(SlotsMaya)`

### `slots/maya/deformation.py`
- `class DeformationSlots(SlotsMaya)`
  - methods: tb001_init, tb001

### `slots/maya/display.py`
- `class DisplaySlots(SlotsMaya)`
  - methods: list000_init, list000, b000, b001, b002, b003, b004, b005, b006, b007, b009, b011, b012, b013, b014, b021, b022, b023, b024

### `slots/maya/duplicate.py`
- `class Duplicate(SlotsMaya)`
  - methods: header_init, tb000_init, tb000, tb001_init, tb001, b000, b005, b006, b007, b008

### `slots/maya/edit.py`
- `class Edit(SlotsMaya)`
  - methods: header_init, tb000_init, tb000, tb001_init, tb001, tb002, tb004_init, tb004, b_channels, b000, list000_init, list000, list001_init, list001, b021, b022, b023, b027

### `slots/maya/edit_mesh.py`
- `class EditMeshSlots(SlotsMaya)`

### `slots/maya/editors.py`
- `class Editors(SlotsMaya)`
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
- `class SelectionMixin`
  - methods: insert_selection_info, insert_component_info
- `class WarningsMixin(HudWarningsMixin)`
- `class HudSlots(SlotsMaya, ptk.PackageManager, StatusMixin, SelectionMixin, WarningsMixin)`
  - methods: request_hud_build, construct_hud

### `slots/maya/key.py`
- `class KeySlots(SlotsMaya)`

### `slots/maya/lighting.py`
- `class Lighting(SlotsMaya)`
  - methods: b000, b001

### `slots/maya/lighting_shading.py`
- `class LightingShadingSlots(SlotsMaya)`

### `slots/maya/main.py`
- `class Main(SlotsMaya)`
  - methods: list000_init, list000

### `slots/maya/mash.py`
- `class MashSlots(SlotsMaya)`

### `slots/maya/materials.py`
- `class MaterialsSlots(SlotsMaya)`
  - methods: header_init, list000_init, list000, list001_init, list001, cmb002_init, lbl007, lbl007_global, tb000_init, tb000, lbl002, b015, lbl004, lbl005, lbl006, b002, b004, b005, b006, b008, b009, b026, b010, b011, b013, b014, b016, b018, tb001_init, tb001, b021, b019, b020, b022, b023, b024, b025

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

### `slots/maya/normals.py`
- `class Normals(SlotsMaya)`
  - methods: tb001_init, tb001, tb004_init, tb004, b000, b001, b002, b004, b006, tb010_init, tb010

### `slots/maya/nparticles.py`
- `class NParticlesSlots(SlotsMaya)`

### `slots/maya/nurbs.py`
- `class Nurbs(SlotsMaya)`
  - methods: list000_init, list000, b056, b058, tb000_init, tb000, tb001_init, tb001, b012, b014, b016, b018, b019, b020, b022, b024, b026, b028, b030, b036, b038, b040, b041, b042, b043, b045, b046, b047, b049, b051, b052, b054

### `slots/maya/pivot.py`
- `class Pivot(SlotsMaya)`
  - methods: tb000_init, tb000, tb001_init, tb001, tb002_init, tb002, tb003_init, tb003, b000, b001, b002, b004

### `slots/maya/playback.py`
- `class PlaybackSlots(SlotsMaya)`

### `slots/maya/polygons.py`
- `class PolygonsSlots(SlotsMaya)`
  - methods: header_init, chk008, chk009, chk010, tb000_init, tb000, tb002_init, tb002, tb003_init, tb003, tb004_init, tb004, tb005_init, tb005, tb006_init, tb006, tb007_init, tb007, tb008_init, tb008, tb009_init, tb009, b000, b001, b003, b005, b006, b007, b008, b009, b011, b012, b022, b032, b034, b038, b043, b047, b049, b051, b053

### `slots/maya/preferences.py`
- `class Preferences(SlotsMaya)`
  - methods: cmb001_init, cmb001, cmb002_init, cmb002, s000_init, s001_init, b001, b002, b008, b009, b010

### `slots/maya/render.py`
- `class Render(SlotsMaya)`

### `slots/maya/rendering.py`
- `class Rendering(SlotsMaya)`
  - methods: tb000_init, tb000, tb001_init, tb001, b001, b003, b004

### `slots/maya/rigging.py`
- `class Rigging(SlotsMaya)`
  - methods: header_init, cmb001_init, cmb001, cmb002_init, cmb002, chk000, chk001, chk002, s000, tb000_init, tb000, tb001_init, tb001, tb003_init, tb003, b003, tb004_init, tb004, b004

### `slots/maya/scene.py`
- `class SceneSlots(SlotsMaya)`
  - methods: header_init, txt000, cmb000_init, cmb000, cmb002_init, cmb002, cmb003_init, cmb003, cmb004_init, cmb004, cmb005_init, cmb005, list000_init, list000, b000, b001, b002, b010, b016, tb003_init, tb003, b004, b005, b006, b009, tb001_init, tb001, b011, b012, b007, b008, b013, b014_init, b014, b015

### `slots/maya/select.py`
- `class SelectSlots(SlotsMaya)`

### `slots/maya/selection.py`
- `class Selection(SlotsMaya)`
  - methods: list000_init, list000, cmb001_init, cmb001, cmb003_init, cmb003, cmb005_init, cmb005, chk000, chk001, chk002, chk005_init, chk005, chk006, chk007, lbl003, lbl004, chk004, chk008, chkxxx, tb000_init, tb000, tb001_init, tb001, tb002_init, tb002, tb003_init, tb003, b001, b016, b017, b018, b019, get_selection_tool, set_selection_tool

### `slots/maya/settings.py`
- `class Settings(SlotsMaya)`
  - methods: header_init, tb000, tb001, check_for_update, b020, b021, b022, cmb_bind_default_init, cmb_bind_left_init, cmb_bind_middle_init, cmb_bind_right_init, cmb_bind_left_right_init, kse_activation_key_init, kse_repeat_last_init, b_reset_bindings

### `slots/maya/skeleton.py`
- `class SkeletonSlots(SlotsMaya)`

### `slots/maya/skin.py`
- `class Skin(SlotsMaya)`

### `slots/maya/stereo.py`
- `class StereoSlots(SlotsMaya)`

### `slots/maya/subdivision.py`
- `class Subdivision(SlotsMaya)`
  - methods: cmb001, cmb002, s000, s001, b000, b001, b005, tb000_init, tb000, b008, b009, b011, b028, smoothProxy

### `slots/maya/surfaces.py`
- `class SurfacesSlots(SlotsMaya)`

### `slots/maya/symmetry.py`
- `class Symmetry(SlotsMaya)`
  - methods: chk000_init, chk000, chk001, chk002, chk004, chk005_init, chk005

### `slots/maya/texturing.py`
- `class TexturingSlots(SlotsMaya)`

### `slots/maya/toon.py`
- `class ToonSlots(SlotsMaya)`

### `slots/maya/transform.py`
- `class TransformSlots(SlotsMaya)`
  - methods: header_init, cmb002_init, cmb002, tb000_init, tb000, tb001_init, tb001, tb002_init, tb002, tb003_init, tb004_init, tb005_init, tb005, chk021, chk022, chk023, chk024, chk025, chk026, s021, s022, s023, b_snap_ts, b001, b002, setTransformSnap

### `slots/maya/utilities.py`
- `class Utilities(SlotsMaya)`
  - methods: b000, b001, b002, b003

### `slots/maya/uv.py`
- `class UvSlots(SlotsMaya)`
  - methods: get_map_size, header_init, cmb002_init, tb000_init, tb000, tb001_init, tb001, tb004_init, tb004, tb005_init, tb005, tb006_init, tb006, tb007_init, tb007, tb008_init, tb008, tb009_init, tb009, cmb002, cmb003, s003, b000, b003, b004, b005, b011, b021, tb022_init, tb022, b023, b024, b025, b026, b029_init, b029, b030_init, b030, b031, b032

### `slots/maya/visualize.py`
- `class VisualizeSlots(SlotsMaya)`

### `slots/maya/windows.py`
- `class WindowsSlots(SlotsMaya)`

### `tcl_blender.py` — Blender entry point for tentacle's Qt marking menu — host + keymap bridge + launcher in one.
- `ensure_qapp()`
- `ensure_blender_widget(app)`
- `start_event_pump(app, interval=0.01)`
- `blender_native_window()`
- `launch(**kwargs)`
- `register()`
- `unregister()`
- `reload()`
- `diagnose()`
- `enable_click_debug()`
- `disable_click_debug()`
- `class TclBlender(MarkingMenu)`
  - methods: get_main_window, showEvent, keyPressEvent, keyReleaseEvent
- `class Diagnostics`
  - methods: report
- `class BlenderHost`
  - methods: launch, register, unregister, reload

### `tcl_max.py`
- `class TclMax(MarkingMenu)`
  - methods: get_main_window, showEvent, hideEvent

### `tcl_maya.py`
- `class TclMaya(MarkingMenu)`
