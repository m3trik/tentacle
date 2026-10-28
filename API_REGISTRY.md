# tentacle — API Registry

_Auto-generated. Do not edit by hand. Refresh via `m3trik/scripts/generate_api_registry.py`._

## Index

- [`__init__.py`](#__init__)
- [`slots/_animation.py`](#slots--_animation) — Text the animation panel's Maya and Blender forks say identically.
- [`slots/_display.py`](#slots--_display) — Behavior shared by the Maya and Blender ``display`` panels.
- [`slots/_duplicate.py`](#slots--_duplicate) — Behavior shared by the Maya and Blender ``duplicate`` panels.
- [`slots/_edit.py`](#slots--_edit) — Shared, DCC-agnostic behavior for the ``edit`` panel.
- [`slots/_hud_warnings.py`](#slots--_hud_warnings) — Shared HUD framework (DCC-agnostic): warnings + the prev-command line.
- [`slots/_lighting.py`](#slots--_lighting) — Shared surface for the ``lighting`` panel's Maya and Blender forks.
- [`slots/_main.py`](#slots--_main) — Behavior shared by the Maya and Blender ``main`` start menus' Workspace tab.
- [`slots/_materials.py`](#slots--_materials) — Shared, DCC-agnostic behavior for the ``materials`` panel.
- [`slots/_nurbs.py`](#slots--_nurbs) — Behavior shared by the Maya and Blender ``nurbs`` panels.
- [`slots/_pivot.py`](#slots--_pivot) — Behavior shared by the Maya and Blender ``pivot`` panels.
- [`slots/_preferences.py`](#slots--_preferences) — Shared, DCC-agnostic behavior for the ``preferences`` panel.
- [`slots/_rendering.py`](#slots--_rendering) — Shared, DCC-agnostic behavior for the ``rendering`` panel.
- [`slots/_rigging.py`](#slots--_rigging) — Behavior shared by the Maya and Blender ``rigging`` panels.
- [`slots/_scene.py`](#slots--_scene) — Behavior shared by the Maya and Blender ``scene`` panels.
- [`slots/_selection.py`](#slots--_selection) — Behavior shared by the Maya and Blender ``selection`` panels.
- [`slots/_settings.py`](#slots--_settings) — Shared, DCC-agnostic behavior for the ``settings`` panel.
- [`slots/_slots.py`](#slots--_slots)
- [`slots/_transform.py`](#slots--_transform) — Behavior shared by the Maya and Blender ``transform`` panels.
- [`slots/_uv.py`](#slots--_uv) — Behavior shared by the Maya and Blender UV panels.
- [`slots/blender/_slots_blender.py`](#slots--blender--_slots_blender)
- [`slots/blender/animation.py`](#slots--blender--animation)
- [`slots/blender/blender.py`](#slots--blender--blender)
- [`slots/blender/cameras.py`](#slots--blender--cameras)
- [`slots/blender/crease.py`](#slots--blender--crease)
- [`slots/blender/deformation.py`](#slots--blender--deformation)
- [`slots/blender/display.py`](#slots--blender--display)
- [`slots/blender/duplicate.py`](#slots--blender--duplicate)
- [`slots/blender/edit.py`](#slots--blender--edit)
- [`slots/blender/editors.py`](#slots--blender--editors)
- [`slots/blender/hud.py`](#slots--blender--hud)
- [`slots/blender/lighting.py`](#slots--blender--lighting)
- [`slots/blender/main.py`](#slots--blender--main)
- [`slots/blender/materials.py`](#slots--blender--materials)
- [`slots/blender/nurbs.py`](#slots--blender--nurbs)
- [`slots/blender/pivot.py`](#slots--blender--pivot)
- [`slots/blender/polygons.py`](#slots--blender--polygons)
- [`slots/blender/preferences.py`](#slots--blender--preferences)
- [`slots/blender/rendering.py`](#slots--blender--rendering)
- [`slots/blender/rigging.py`](#slots--blender--rigging)
- [`slots/blender/scene.py`](#slots--blender--scene)
- [`slots/blender/selection.py`](#slots--blender--selection)
- [`slots/blender/settings.py`](#slots--blender--settings)
- [`slots/blender/subdivision.py`](#slots--blender--subdivision)
- [`slots/blender/symmetry.py`](#slots--blender--symmetry)
- [`slots/blender/transform.py`](#slots--blender--transform)
- [`slots/blender/utilities.py`](#slots--blender--utilities)
- [`slots/blender/uv.py`](#slots--blender--uv)
- [`slots/maya/_slots_maya.py`](#slots--maya--_slots_maya)
- [`slots/maya/animation.py`](#slots--maya--animation)
- [`slots/maya/arnold.py`](#slots--maya--arnold)
- [`slots/maya/cache.py`](#slots--maya--cache)
- [`slots/maya/cameras.py`](#slots--maya--cameras)
- [`slots/maya/constrain.py`](#slots--maya--constrain)
- [`slots/maya/control.py`](#slots--maya--control)
- [`slots/maya/crease.py`](#slots--maya--crease)
- [`slots/maya/curves.py`](#slots--maya--curves)
- [`slots/maya/deform.py`](#slots--maya--deform)
- [`slots/maya/deformation.py`](#slots--maya--deformation)
- [`slots/maya/display.py`](#slots--maya--display)
- [`slots/maya/duplicate.py`](#slots--maya--duplicate)
- [`slots/maya/edit.py`](#slots--maya--edit)
- [`slots/maya/edit_mesh.py`](#slots--maya--edit_mesh)
- [`slots/maya/editors.py`](#slots--maya--editors)
- [`slots/maya/effects.py`](#slots--maya--effects)
- [`slots/maya/fields_solvers.py`](#slots--maya--fields_solvers)
- [`slots/maya/fluids.py`](#slots--maya--fluids)
- [`slots/maya/generate.py`](#slots--maya--generate)
- [`slots/maya/help.py`](#slots--maya--help)
- [`slots/maya/hud.py`](#slots--maya--hud)
- [`slots/maya/key.py`](#slots--maya--key)
- [`slots/maya/lighting.py`](#slots--maya--lighting)
- [`slots/maya/lighting_shading.py`](#slots--maya--lighting_shading)
- [`slots/maya/main.py`](#slots--maya--main)
- [`slots/maya/mash.py`](#slots--maya--mash)
- [`slots/maya/materials.py`](#slots--maya--materials)
- [`slots/maya/mesh.py`](#slots--maya--mesh)
- [`slots/maya/mesh_display.py`](#slots--maya--mesh_display)
- [`slots/maya/mesh_tools.py`](#slots--maya--mesh_tools)
- [`slots/maya/ncloth.py`](#slots--maya--ncloth)
- [`slots/maya/nconstraint.py`](#slots--maya--nconstraint)
- [`slots/maya/nhair.py`](#slots--maya--nhair)
- [`slots/maya/nparticles.py`](#slots--maya--nparticles)
- [`slots/maya/nurbs.py`](#slots--maya--nurbs)
- [`slots/maya/pivot.py`](#slots--maya--pivot)
- [`slots/maya/playback.py`](#slots--maya--playback)
- [`slots/maya/polygons.py`](#slots--maya--polygons)
- [`slots/maya/preferences.py`](#slots--maya--preferences)
- [`slots/maya/render.py`](#slots--maya--render)
- [`slots/maya/rendering.py`](#slots--maya--rendering)
- [`slots/maya/rigging.py`](#slots--maya--rigging)
- [`slots/maya/scene.py`](#slots--maya--scene)
- [`slots/maya/select.py`](#slots--maya--select)
- [`slots/maya/selection.py`](#slots--maya--selection)
- [`slots/maya/settings.py`](#slots--maya--settings)
- [`slots/maya/skeleton.py`](#slots--maya--skeleton)
- [`slots/maya/skin.py`](#slots--maya--skin)
- [`slots/maya/stereo.py`](#slots--maya--stereo)
- [`slots/maya/subdivision.py`](#slots--maya--subdivision)
- [`slots/maya/surfaces.py`](#slots--maya--surfaces)
- [`slots/maya/symmetry.py`](#slots--maya--symmetry)
- [`slots/maya/texturing.py`](#slots--maya--texturing)
- [`slots/maya/toon.py`](#slots--maya--toon)
- [`slots/maya/transform.py`](#slots--maya--transform)
- [`slots/maya/utilities.py`](#slots--maya--utilities)
- [`slots/maya/uv.py`](#slots--maya--uv)
- [`slots/maya/visualize.py`](#slots--maya--visualize)
- [`slots/maya/windows.py`](#slots--maya--windows)
- [`slots/normals.py`](#slots--normals) — Normals: one Slots class for both hosts.
- [`slots/tools/_blendshape_animator/sort_item.py`](#slots--tools--_blendshape_animator--sort_item) — A tween-tree row that sorts its numeric columns by number.
- [`slots/tools/_shot_manifest/controller.py`](#slots--tools--_shot_manifest--controller) — The Shot Manifest panel's controller: its state, the steps the table shows,
- [`slots/tools/_shot_manifest/export_preview.py`](#slots--tools--_shot_manifest--export_preview) — The Shot Manifest's Export button (beside Assess): a live preview of the
- [`slots/tools/_shot_manifest/header_menu.py`](#slots--tools--_shot_manifest--header_menu) — The Shot Manifest's header menu: Long Names, Local Edits' Edits mode and
- [`slots/tools/_shot_manifest/manifest_data.py`](#slots--tools--_shot_manifest--manifest_data) — Constants, column layout, and pure helper functions for the Shot Manifest UI.
- [`slots/tools/_shot_manifest/manifest_editor.py`](#slots--tools--_shot_manifest--manifest_editor) — Local Edits for the Shot Manifest panel: change the table, never the sheet.
- [`slots/tools/_shot_manifest/manifest_source.py`](#slots--tools--_shot_manifest--manifest_source) — Where the Shot Manifest's steps come from: a build sheet (a CSV path or link,
- [`slots/tools/_shot_manifest/mapping_picker.py`](#slots--tools--_shot_manifest--mapping_picker) — The Shot Manifest's mapping template: its own popup on the build sheet
- [`slots/tools/_shot_manifest/range_column.py`](#slots--tools--_shot_manifest--range_column) — The Shot Manifest table's Start / End column: what a step's range is
- [`slots/tools/_shot_manifest/row_menus.py`](#slots--tools--_shot_manifest--row_menus) — The Shot Manifest rows' context menus and what they do: a step row's (colour
- [`slots/tools/_shot_manifest/store_follow.py`](#slots--tools--_shot_manifest--store_follow) — The Shot Manifest panel following the scene's store: its events (a shot
- [`slots/tools/_shot_manifest/table_presenter.py`](#slots--tools--_shot_manifest--table_presenter) — The Shot Manifest tree's rows: populating them (``ShotPairing.rows``: steps,
- [`slots/tools/_shot_manifest/view_combos.py`](#slots--tools--_shot_manifest--view_combos) — The Shot Manifest's view row, above the table: Select, Expand, Collapse,
- [`slots/tools/_texture_combine/transfer_mode.py`](#slots--tools--_texture_combine--transfer_mode) — The Texture Combine panel's Transfer mode: UVs or textures, source -> targets.
- [`slots/tools/articulated_rig.py`](#slots--tools--articulated_rig) — Articulated Rig: rig a prop of rigid parts on hinges, swivels, balls and
- [`slots/tools/audio_clips.py`](#slots--tools--audio_clips) — Audio Clips: the scene's audio files, placed on the timeline.
- [`slots/tools/bevel.py`](#slots--tools--bevel) — Bevel: chamfer the selected polygon edges, with a live preview.
- [`slots/tools/blendshape_animator.py`](#slots--tools--blendshape_animator) — Blendshape Animator: build a morph between two meshes, add in-between
- [`slots/tools/bridge.py`](#slots--tools--bridge) — Bridge: connect two open edge loops with new polygon faces, with a live preview.
- [`slots/tools/calculator.py`](#slots--tools--calculator) — Calculator: expressions, length units, and the scene's frame-rate helpers.
- [`slots/tools/color_id.py`](#slots--tools--color_id) — Color ID: color-code objects across channels from a swatch palette.
- [`slots/tools/curtain.py`](#slots--tools--curtain) — Curtain: drape a pleated, gravity-sagged cloth curtain from a rail, with a
- [`slots/tools/curve_to_tube.py`](#slots--tools--curve_to_tube) — Curve to Tube: sweep a circular profile along the selected curves into a
- [`slots/tools/cut_on_axis.py`](#slots--tools--cut_on_axis) — Cut On Axis: slice the selected meshes along an axis, then optionally delete
- [`slots/tools/duplicate_grid.py`](#slots--tools--duplicate_grid) — Duplicate Grid: copies of the selection in a 3D grid.
- [`slots/tools/duplicate_linear.py`](#slots--tools--duplicate_linear) — Duplicate Linear: copies of the selection along a line, each interpolating
- [`slots/tools/duplicate_radial.py`](#slots--tools--duplicate_radial) — Duplicate Radial: copies of the selection in a radial pattern about a pivot.
- [`slots/tools/dynamic_pipe.py`](#slots--tools--dynamic_pipe) — Dynamic Pipe: a pipe mesh that follows a chain of handles live.
- [`slots/tools/emissive_groups.py`](#slots--tools--emissive_groups) — Emissive Groups: named face groups whose emissive regions a game engine gates.
- [`slots/tools/exploded_view.py`](#slots--tools--exploded_view) — Exploded View: spread the selected objects apart to inspect interior parts.
- [`slots/tools/game_shader.py`](#slots--tools--game_shader) — Game Shader: build a PBR material from a set of texture maps, packed for a
- [`slots/tools/hdr_manager.py`](#slots--tools--hdr_manager) — HDR Manager: light the scene from an HDR environment map, spin it and adjust
- [`slots/tools/image_to_plane.py`](#slots--tools--image_to_plane) — Image to Plane: batch-create textured planes from image files.
- [`slots/tools/image_tracer.py`](#slots--tools--image_tracer) — Image Tracer: trace a raster image's contours into curves, then fill them
- [`slots/tools/key_stash.py`](#slots--tools--key_stash) — Key Stash: park keys out of the working animation as clips, then preview or
- [`slots/tools/lightmap_baker.py`](#slots--tools--lightmap_baker) — Lightmap Baker: bake the scene's lighting into lightmaps the engine reads.
- [`slots/tools/mat_updater.py`](#slots--tools--mat_updater) — Material Updater: rework scene materials for a target workflow preset,
- [`slots/tools/mirror.py`](#slots--tools--mirror) — Mirror: mirror the selected meshes across an axis, with a live preview.
- [`slots/tools/naming.py`](#slots--tools--naming) — Naming: batch find / rename / convert-case / strip-chars / suffix-by-location /
- [`slots/tools/render_effects.py`](#slots--tools--render_effects) — Render Effects: key per-object opacity fades and highlight pulses for export.
- [`slots/tools/scene_exporter.py`](#slots--tools--scene_exporter) — Scene Exporter: batch-export the scene through its task/check pipeline.
- [`slots/tools/shader_templates.py`](#slots--tools--shader_templates) — Shader Templates: save a material's shader network as a reusable template
- [`slots/tools/shadow_rig.py`](#slots--tools--shadow_rig) — Shadow Rig: a ground plane carrying the targets' projected shadow, built for
- [`slots/tools/shell_xform.py`](#slots--tools--shell_xform) — Shell Xform: move, flip, rotate, straighten, mirror, distribute, align and
- [`slots/tools/shot_manifest.py`](#slots--tools--shot_manifest) — Shot Manifest: a shot sheet checked against the scene, and the shots built from it.
- [`slots/tools/smart_bake.py`](#slots--tools--smart_bake) — Smart Bake: bake what drives the scene's animation to keys, reversibly.
- [`slots/tools/snap.py`](#slots--tools--snap) — Snap: vertices to a target surface, to the closest target vertex, or to the grid.
- [`slots/tools/telescope_rig.py`](#slots--tools--telescope_rig) — Telescope Rig: nested segments that extend and retract between a base and an
- [`slots/tools/texture_combine.py`](#slots--tools--texture_combine) — Texture Combine: several materials into one atlas and one material, in
- [`slots/tools/tube_rig.py`](#slots--tools--tube_rig) — Tube Rig: rig a tube-shaped mesh (hose, cable, piston, tail) with joints,
- [`slots/tools/wheel_rig.py`](#slots--tools--wheel_rig) — Wheel Rig: wheels that roll as their driver (control) moves, sized by wheel
- [`tcl.py`](#tcl) — The host-agnostic entry point — one launcher snippet for every DCC.
- [`tcl_blender.py`](#tcl_blender) — Blender entry point for tentacle's Qt marking menu — host + keymap bridge + launcher in one.
- [`tcl_max.py`](#tcl_max)
- [`tcl_maya.py`](#tcl_maya)
- [`tentacle_installer.py`](#tentacle_installer) — Install, update or uninstall tentacle in a DCC -- one file, dropped in, no administrator rights.

---

<a id="__init__"></a>
### `__init__.py`

- [`greeting(string, outputToConsole=True)`](tentacle/tentacle/__init__.py#L68) — Format a string using preset variables.
- [`DEFAULT_INCLUDE`](tentacle/tentacle/__init__.py#L11) — constant
- [`MOVED_NAMES`](tentacle/tentacle/__init__.py#L56) — constant

<a id="slots--_animation"></a>
### `slots/_animation.py`

Text the animation panel's Maya and Blender forks say identically.

- **[`class AnimationMixin`](tentacle/tentacle/slots/_animation.py#L46)** — Shared tooltip text and key-edit wrapper for ``slots/{maya,blender}/animation.py``.
  - `AnimationMixin.list000_init(self, widget)` — Tools list: Sequencing / Repair / Bake / Stash / Playback / Info.

<a id="slots--_display"></a>
### `slots/_display.py`

Behavior shared by the Maya and Blender ``display`` panels.

- **[`class DisplayMixin`](tentacle/tentacle/slots/_display.py#L9)** — Shared ``display`` panel behavior.
  - `DisplayMixin.header_init(self, widget)` — Header menu: the submenu's Display expandable list — hover a row to
  - `DisplayMixin.list000_init(self, widget)` — Initialize Display expandable list (categories → actions).

<a id="slots--_duplicate"></a>
### `slots/_duplicate.py`

Behavior shared by the Maya and Blender ``duplicate`` panels.

- **[`class DuplicateMixin`](tentacle/tentacle/slots/_duplicate.py#L9)** — Shared ``duplicate`` panel behavior.
  - `DuplicateMixin.header_init(self, widget)` — Header menu: the Mirror / Duplicate Linear / Radial / Grid launchers

<a id="slots--_edit"></a>
### `slots/_edit.py`

Shared, DCC-agnostic behavior for the ``edit`` panel.

- **[`class EditMixin`](tentacle/tentacle/slots/_edit.py#L17)** — DCC-agnostic ``edit`` slot behavior (Mesh Cleanup user-feedback formatting).
  - `EditMixin.mesh_cleanup_tooltip(self)` — Rich tooltip for the Mesh Cleanup button (``edit.tb000``).
  - `EditMixin.cleanup_popup_html(header, rows)` *(static)* — Minimal HTML for the Mesh Cleanup popup (``sb.message_box``) — glanceable, one fact per line.
  - `EditMixin.cleanup_console_report(title, lines)` *(static)* — Detailed Mesh Cleanup report to stdout (Maya Script Editor / Blender system console).
  - `EditMixin.report_cleanup_failure(self, scope, mode_label, exc)` — Report a Mesh Cleanup failure through both channels — a detailed console line and a
  - `EditMixin.cmb000_init(self, widget)` — Initialize the Transfer operations menu.

<a id="slots--_hud_warnings"></a>
### `slots/_hud_warnings.py`

Shared HUD framework (DCC-agnostic): warnings + the prev-command line.

- **[`class HudWarningsMixin`](tentacle/tentacle/slots/_hud_warnings.py#L28)**
  - `HudWarningsMixin.hudTextEdit_init(self, widget) -> None` — The HUD is a display composed afresh on every show — never persisted.
  - `HudWarningsMixin.evaluate_warnings(self) -> list` — Return the subset of WARNING_DEFS whose check fires and is enabled.
  - `HudWarningsMixin.insert_warning_icons(self, hud, warnings) -> None` — Insert a single-line row of colored badges;
  - `HudWarningsMixin.insert_warning_details(self, hud, warnings) -> None` — Insert a formatted detail line per active warning.
  - `HudWarningsMixin.insert_prev_command(self, hud, method) -> None` — Insert the last-used command as a single, length-capped line.

<a id="slots--_lighting"></a>
### `slots/_lighting.py`

Shared surface for the ``lighting`` panel's Maya and Blender forks.

- **[`class LightingMixin`](tentacle/tentacle/slots/_lighting.py#L12)** — Behaviour and reference data shared by both ``lighting`` forks.
  - `LightingMixin.kelvin_tooltip(cls, lead: str, tail: str) -> str` *(class)* — *lead*, then the reference table, then *tail*.

<a id="slots--_main"></a>
### `slots/_main.py`

Behavior shared by the Maya and Blender ``main`` start menus' Workspace tab.

- **[`class MainMixin`](tentacle/tentacle/slots/_main.py#L25)** — Shared ``main`` Workspace-tab behavior.

<a id="slots--_materials"></a>
### `slots/_materials.py`

Shared, DCC-agnostic behavior for the ``materials`` panel.

- **[`class MaterialsMixin`](tentacle/tentacle/slots/_materials.py#L72)** — DCC-agnostic ``materials`` slot behavior: the material table, the current
  - `MaterialsMixin.tbl000_init(self, widget)` — The material table: built once, re-wired and refilled on every show.
  - `MaterialsMixin.b028(self, widget=None)` — Assign the highlighted material to the selection.
  - `MaterialsMixin.b029(self, widget=None)` — Select what uses the highlighted material, as assigned.
  - `MaterialsMixin.b030(self, widget=None)` — Select every object using the highlighted material.
  - `MaterialsMixin.b031(self, widget=None)` — Narrow the selection to what uses the highlighted material.
  - `MaterialsMixin.b032(self, widget=None)` — Merge the highlighted duplicates into the materials they duplicate.
  - `MaterialsMixin.lbl002(self, widget=None)` — Delete the highlighted materials.
  - `MaterialsMixin.txt000_init(self, widget)` — The filter field: hides the rows whose name does not hold its text.
  - `MaterialsMixin.b006_init(self, widget)`
  - `MaterialsMixin.b006(self, widget=None)` — New material onto the selection (:meth:`_new_mat`);
  - `MaterialsMixin.b033(self, widget=None)` — Select the objects carrying no material.
  - `MaterialsMixin.b014(self, widget=None)` — Remove Duplicate Materials: merge every duplicate in the scene into
  - `MaterialsMixin.header_init(self, widget)` — The header: a refresh button, and a menu of the Tools list then
  - `MaterialsMixin.b003(self, widget=None)` — Get + Select (submenu): adopt the selection's material, then select its users.
  - `MaterialsMixin.list001_init(self, widget)` — Tools list: Setup / Materials / Texture Maps / External / Utilities.

<a id="slots--_nurbs"></a>
### `slots/_nurbs.py`

Behavior shared by the Maya and Blender ``nurbs`` panels.

- **[`class NurbsMixin`](tentacle/tentacle/slots/_nurbs.py#L9)** — Shared ``nurbs`` panel behavior.
  - `NurbsMixin.list000_init(self, widget)` — Initialize the Nurbs expandable list (root -> category -> curve action),

<a id="slots--_pivot"></a>
### `slots/_pivot.py`

Behavior shared by the Maya and Blender ``pivot`` panels.

- **[`class PivotMixin`](tentacle/tentacle/slots/_pivot.py#L10)** — Shared ``pivot`` panel behavior.
  - `PivotMixin.b000(self)` — Center Pivot: Object
  - `PivotMixin.b001(self)` — Center Pivot: Component
  - `PivotMixin.b002(self, widget)` — Center Pivot: World

<a id="slots--_preferences"></a>
### `slots/_preferences.py`

Shared, DCC-agnostic behavior for the ``preferences`` panel.

- **[`class PreferencesMixin`](tentacle/tentacle/slots/_preferences.py#L22)** — DCC-agnostic ``preferences`` slot behavior.
  - `PreferencesMixin.cmb004_init(self, widget)` — Marking-menu (radial startmenu / submenu) window theme.
  - `PreferencesMixin.cmb004(self, index, widget)` — Apply the marking-menu theme (persists + re-themes live windows).
  - `PreferencesMixin.cmb005_init(self, widget)` — Standalone tool-window theme.
  - `PreferencesMixin.cmb005(self, index, widget)` — Apply the standalone-window theme (persists + re-themes live windows).
  - `PreferencesMixin.cmb006_init(self, widget)` — Presentation for tools whose external app / plugin isn't installed.
  - `PreferencesMixin.cmb006(self, index, widget)` — Persist the chosen presentation policy and re-present the live gates.
  - `PreferencesMixin.header_init(self, widget)` — Header menu — the manual re-probe that pairs with ``cmb006``.
  - `PreferencesMixin.tb000(self)` — Re-check installed tools: drop the cached probes, then re-apply the gates.
  - `PreferencesMixin.b011(self)` — Macro Manager — the unified uitk shortcut editor over the engine's

<a id="slots--_rendering"></a>
### `slots/_rendering.py`

Shared, DCC-agnostic behavior for the ``rendering`` panel.

- **[`class RenderingMixin`](tentacle/tentacle/slots/_rendering.py#L23)** — DCC-agnostic ``rendering`` slot behavior (the playblast encoder guard and

<a id="slots--_rigging"></a>
### `slots/_rigging.py`

Behavior shared by the Maya and Blender ``rigging`` panels.

- **[`class RiggingMixin`](tentacle/tentacle/slots/_rigging.py#L6)** — Shared ``rigging`` panel behavior.

<a id="slots--_scene"></a>
### `slots/_scene.py`

Behavior shared by the Maya and Blender ``scene`` panels.

- **[`class SceneMixin`](tentacle/tentacle/slots/_scene.py#L44)** — Shared ``scene`` panel behavior.
  - `SceneMixin.tb003(self, widget)` — Export Scene in the chosen format, using the configured options.
  - `SceneMixin.list003_init(self, widget)` — Tools list: the scene actions that used to sit loose in the header
  - `SceneMixin.b019(self)` — Check GLB / FBX -- the Scene Exporter's post-write gates, over files on disk.
  - `SceneMixin.tb001_init(self, widget)` — Get Scene Info — option box: scope, profile, and one toggle per section.
  - `SceneMixin.tb001(self, widget)` — Get Scene Info — render the sectioned audit report to the viewer dialog.
  - `SceneMixin.tb002_init(self, widget)` — Fix Non-Orthogonal Axes — option box.
  - `SceneMixin.tb002(self, widget)` — Fix Non-Orthogonal Axes.

<a id="slots--_selection"></a>
### `slots/_selection.py`

Behavior shared by the Maya and Blender ``selection`` panels.

- **[`class SelectionMixin`](tentacle/tentacle/slots/_selection.py#L26)** — Shared ``selection`` panel behavior.
  - `SelectionMixin.list001_init(self, widget)` — Convert To: category rows that convert on click and expand on hover.
  - `SelectionMixin.tb004(self, widget)` — Select by Type settings: open the scope/mode menu.

<a id="slots--_settings"></a>
### `slots/_settings.py`

Shared, DCC-agnostic behavior for the ``settings`` panel.

- **[`class SettingsMixin`](tentacle/tentacle/slots/_settings.py#L18)** — DCC-agnostic ``settings`` slot behavior.
  - `SettingsMixin.ecosystem_dists(cls, installed=None)` *(class)* — The distributions to check for updates in THIS host.
  - `SettingsMixin.header_init(self, widget)` — Initialize header
  - `SettingsMixin.tb000(self)` — Update Package
  - `SettingsMixin.check_for_update(self)` — Check the whole ecosystem for updates and upgrade what's outdated.
  - `SettingsMixin.b020(self)` — UI Style Editor
  - `SettingsMixin.b021(self)` — Shortcut Editor
  - `SettingsMixin.b022(self)` — UI Browser: open the tentacle UI browser (search, show/hide registered UIs).
  - `SettingsMixin.b023(self)` — Global Shortcuts: open the shortcut editor focused on the global
  - `SettingsMixin.b024(self)` — Preset Editor: every tool's presets in one window — lock, group into
  - `SettingsMixin.cmb_bind_default_init(self, widget)` — Default menu (activation key only).
  - `SettingsMixin.cmb_bind_left_init(self, widget)` — Left mouse button.
  - `SettingsMixin.cmb_bind_middle_init(self, widget)` — Middle mouse button.
  - `SettingsMixin.cmb_bind_right_init(self, widget)` — Right mouse button.
  - `SettingsMixin.cmb_bind_left_right_init(self, widget)` — Left + Right mouse buttons.
  - `SettingsMixin.b_reset_bindings(self)` — Reset marking-menu bindings (routes + activation key) to defaults.

<a id="slots--_slots"></a>
### `slots/_slots.py`

- **[`class Slots(QtCore.QObject)`](tentacle/tentacle/slots/_slots.py#L9)** — Provides methods that can be triggered by widgets in the ui.
  - `Slots.tk(self)` *(property)* — The host toolkit (``mtk`` / ``btk``) the entry point set on the
  - `Slots.mirror_app_state(widget, seed=None) -> None` *(static)* — Declare that *widget*'s value mirrors live DCC state, optionally seeding it.
  - `Slots.add_slot_widget(self, sublist, widget_class=None, **kwargs)` — Add a slot-wired widget as an ExpandableList sublist entry.
  - `Slots.gate_on_app(self, widget, resolve_spec) -> bool` — Gate *widget* on the :class:`pythontk.AppSpec` *resolve_spec* returns.
  - `Slots.recheck_app_gates(self) -> int` — Re-probe every gated app and re-present its widgets.
  - `Slots.toggle_camera_view(self)` — Toggle between the last two viewport-camera views in slot history.
  - `Slots.register_camera_view_toggle(self)` — Wire :meth:`toggle_camera_view` to its triggers.

<a id="slots--_transform"></a>
### `slots/_transform.py`

Behavior shared by the Maya and Blender ``transform`` panels.

- **[`class TransformMixin`](tentacle/tentacle/slots/_transform.py#L9)** — Shared ``transform`` panel behavior.
  - `TransformMixin.tb001_init(self, widget)` — Initialize Scale Connected Edges (the scale factor option).

<a id="slots--_uv"></a>
### `slots/_uv.py`

Behavior shared by the Maya and Blender UV panels.

- **[`class UvMixin`](tentacle/tentacle/slots/_uv.py#L6)** — Shared UV-panel behavior (see ``slots/maya/uv.py``, ``slots/blender/uv.py``).
  - `UvMixin.b000_init(self, widget)` — The Texture Combine launcher: a plain button, the panel is the UI.
  - `UvMixin.b000(self)` — Open the Texture Combine panel (Combine / Transfer modes).
  - `UvMixin.b030_init(self, widget)` — Stack button — non-checkable text button with the stack option box.
  - `UvMixin.get_map_size(self)` — Get the map size from the combobox as an int.
  - `UvMixin.cmb003(self, index, widget)` — UV Map Size — passive input;
  - `UvMixin.s003(self, value, widget)` — Texel Density — passive input;
  - `UvMixin.b029_init(self, widget)` — Initialize Pin/Unpin button — non-checkable text button.

<a id="slots--blender--_slots_blender"></a>
### `slots/blender/_slots_blender.py`

- **[`class SlotsBlender(Slots)`](tentacle/tentacle/slots/blender/_slots_blender.py#L8)** — App specific methods inherited by all other Blender slot classes.
  - `SlotsBlender.selected_objects()` *(static)* — The current object selection (filtered of ``None``) — shared by all Blender slots.
  - `SlotsBlender.active_object()` *(static)* — The active object (or ``None``) — shared by all Blender slots.
  - `SlotsBlender.effective_fps() -> float` *(static)* — The scene frame rate as the user understands it — ``fps / fps_base`` — shared by all
  - `SlotsBlender.ensure_edit_mode(self, obj_type='MESH', select_mode=None)` — Put an object of ``obj_type`` into Edit Mode (Maya's *component* mode), optionally
  - `SlotsBlender.ensure_object_mode(self)` — Leave Edit (or any other) Mode before object-level surgery — data-block reassignment,
  - `SlotsBlender.set_viewport_tool(self, tool_id, label=None, edit_type=None)` — Activate a builtin viewport workspace tool (knife / loop-cut / poly-build /
  - `SlotsBlender.resolve_op(op_path)` *(static)* — The ``bpy.ops`` callable at a dotted path (``"wm.link"``), or None when the
  - `SlotsBlender.invoke_op(self, op_path, **kwargs)` — Invoke an operator's dialog by dotted path (``INVOKE_DEFAULT``), degrading to a
  - `SlotsBlender.transfer_from_active(self, data_type, **kwargs)` — Run native Data-Transfer from the active mesh to the other selected meshes

<a id="slots--blender--animation"></a>
### `slots/blender/animation.py`

- **[`class AnimationSlots(AnimationMixin, SlotsBlender)`](tentacle/tentacle/slots/blender/animation.py#L8)** — Blender port of the shared ``animation`` menu.
  - `AnimationSlots.list000(self, item)` — Dispatch a Tools leaf to its slot method.
  - `AnimationSlots.tb000_init(self, widget)`
  - `AnimationSlots.tb000(self, widget)` — Go To Frame (absolute, or relative offset from the current frame);
  - `AnimationSlots.tb001_init(self, widget)`
  - `AnimationSlots.tb001(self, widget)` — Invert Keys (mirror key times and/or values — reverses timing / flips motion).
  - `AnimationSlots.tb003_init(self, widget)`
  - `AnimationSlots.tb003(self, widget)` — Stagger Keys (re-time selected objects sequentially).
  - `AnimationSlots.tb009_init(self, widget)`
  - `AnimationSlots.tb009(self, widget)` — Snap Keys to Frames
  - `AnimationSlots.tb010_init(self, widget)`
  - `AnimationSlots.tb010(self, widget)` — Delete Keys (clear all animation on the selection, or only a time-scoped subset).
  - `AnimationSlots.tb002_init(self, widget)`
  - `AnimationSlots.tb002(self, widget)` — Adjust Key Spacing (shift every key at/after the frame by the amount).
  - `AnimationSlots.tb004_init(self, widget)`
  - `AnimationSlots.tb004(self, widget)` — Transfer Keys (active object → other selected, independent copies).
  - `AnimationSlots.tb005_init(self, widget)`
  - `AnimationSlots.tb005(self, widget)` — Add/Remove Intermediate Keys
  - `AnimationSlots.tb013_init(self, widget)`
  - `AnimationSlots.tb013(self, widget)` — Select Keys (``select_control_point`` — shows in the Dope Sheet / Graph Editor).
  - `AnimationSlots.tb007_init(self, widget)`
  - `AnimationSlots.tb007(self, widget)` — Align Selected Keyframes (keys picked in the Dope Sheet / Graph Editor).
  - `AnimationSlots.tb008_init(self, widget)`
  - `AnimationSlots.tb008(self, widget)` — Set Visibility Keys (key viewport + render visibility).
  - `AnimationSlots.tb006_init(self, widget)`
  - `AnimationSlots.tb006(self, widget)` — Move Keys (align the selection's keys to the current frame).
  - `AnimationSlots.tb012_init(self, widget)`
  - `AnimationSlots.tb012(self, widget)` — Copy Keys (from the active object;
  - `AnimationSlots.tb018_init(self, widget)`
  - `AnimationSlots.tb018(self, widget)` — Paste Keys (independent copies onto the selection).
  - `AnimationSlots.tb014_init(self, widget)`
  - `AnimationSlots.tb014(self, widget)` — Scale Keys
  - `AnimationSlots.tb017_init(self, widget)`
  - `AnimationSlots.tb017(self, widget)` — Set Tangents (key interpolation type — stepped / linear / smooth).
  - `AnimationSlots.b005(self)` — Fit Playback Range (to the keyed extent of the selection, or the whole scene).
  - `AnimationSlots.tb011_init(self, widget)`
  - `AnimationSlots.tb011(self, widget)` — Tie/Untie Keyframes
  - `AnimationSlots.tb016_init(self, widget)`
  - `AnimationSlots.tb016(self, widget)` — Get Animation Info — render a per-object keyframe summary to the viewer dialog.
  - `AnimationSlots.tb019_init(self, widget)`
  - `AnimationSlots.tb019(self, widget)` — Optimize Keys — remove redundant animation data.
  - `AnimationSlots.tb015_init(self, widget)`
  - `AnimationSlots.tb015(self, widget)` — Repair Corrupted Curves — strip NaN/infinite or out-of-range keys;
  - `AnimationSlots.tb021_init(self, widget)`
  - `AnimationSlots.tb021(self, widget)` — Snap Fractional Key Times — the repair-scoped twin of Snap Keys.
  - `AnimationSlots.tb020(self, widget)` — Smart Bake
  - `AnimationSlots.b000(self)` — Open Shot Sequencer — native blendertk panel (anim_utils/shots/shot_sequencer), 1:1
  - `AnimationSlots.b004(self)` — Open Shot Manifest — native blendertk panel (anim_utils/shots/shot_manifest), 1:1 with
  - `AnimationSlots.b006(self)` — Open Key Stash — native blendertk panel (anim_utils/key_stash), 1:1 with mayatk's:

<a id="slots--blender--blender"></a>
### `slots/blender/blender.py`

- **[`class BlenderSlots(SlotsBlender)`](tentacle/tentacle/slots/blender/blender.py#L6)** — Base-name anchor for the Blender both-button chord menu (``blender#startmenu``).

<a id="slots--blender--cameras"></a>
### `slots/blender/cameras.py`

- **[`class CamerasSlots(SlotsBlender)`](tentacle/tentacle/slots/blender/cameras.py#L8)** — Blender port of the shared ``cameras`` menu.
  - `CamerasSlots.list000_init(self, widget)` — Initialize Camera Options List
  - `CamerasSlots.list000(self, item)` — Camera Options List
  - `CamerasSlots.b000(self)` — Cameras: Back View
  - `CamerasSlots.b001(self)` — Cameras: Top View
  - `CamerasSlots.b002(self)` — Cameras: Right View
  - `CamerasSlots.b003(self)` — Cameras: Left View
  - `CamerasSlots.b004(self)` — Cameras: Perspective View
  - `CamerasSlots.b005(self)` — Cameras: Front View
  - `CamerasSlots.b006(self)` — Cameras: Bottom View
  - `CamerasSlots.b007(self)` — Cameras: Align View (align the viewport to the active element's normal and frame
  - `CamerasSlots.b010(self)` — Camera: Dolly — arm the interactive dolly tool (LMB-drag to move the eye in/out).
  - `CamerasSlots.b011(self)` — Camera: Roll — arm the interactive roll tool (LMB-drag to roll the view about its axis).
  - `CamerasSlots.b012(self)` — Camera: Truck — arm the interactive track/pan tool (LMB-drag to pan the view).
  - `CamerasSlots.b013(self)` — Camera: Orbit — arm the interactive tumble tool (LMB-drag to orbit the view).

<a id="slots--blender--crease"></a>
### `slots/blender/crease.py`

- **[`class CreaseSlots(SlotsBlender)`](tentacle/tentacle/slots/blender/crease.py#L7)** — Blender port of the shared ``crease`` menu.
  - `CreaseSlots.tb000_init(self, widget)`
  - `CreaseSlots.tb000(self, widget)` — Crease
  - `CreaseSlots.b002(self, widget)` — Transfer Crease Edges (active mesh → other selected, native Data-Transfer).

<a id="slots--blender--deformation"></a>
### `slots/blender/deformation.py`

- **[`class DeformationSlots(SlotsBlender)`](tentacle/tentacle/slots/blender/deformation.py#L6)** — Blender port of the shared ``deformation`` menu.
  - `DeformationSlots.tb001_init(self, widget)` — Init Curtain Generator launcher.
  - `DeformationSlots.tb001(self, widget)` — Curtain Generator — open the curtain panel.

<a id="slots--blender--display"></a>
### `slots/blender/display.py`

- **[`class DisplaySlots(DisplayMixin, SlotsBlender)`](tentacle/tentacle/slots/blender/display.py#L8)** — Blender port of the shared ``display`` menu.
  - `DisplaySlots.list000(self, item)` — Dispatch a Display action and report state via message_box.
  - `DisplaySlots.b013(self)` — Explode View — open the Exploded View panel (Explode / Un-Explode / Un-Explode All /
  - `DisplaySlots.b014(self)` — Color ID — swatch palette to color-code objects (material / object color / vertex).

<a id="slots--blender--duplicate"></a>
### `slots/blender/duplicate.py`

- **[`class DuplicateSlots(DuplicateMixin, SlotsBlender)`](tentacle/tentacle/slots/blender/duplicate.py#L8)** — Blender port of the shared ``duplicate`` menu.
  - `DuplicateSlots.tb000_init(self, widget)`
  - `DuplicateSlots.tb000(self, widget)` — Convert to Instances (selected objects share the active object's data).
  - `DuplicateSlots.tb001_init(self, widget)`
  - `DuplicateSlots.tb001(self, widget)` — Select Instanced Objects
  - `DuplicateSlots.tb002_init(self, widget)` — Initialize Auto Instance — configure option-box menu.
  - `DuplicateSlots.tb002(self, widget)` — Auto Instance: find and convert geometrically identical meshes
  - `DuplicateSlots.b005(self)` — Uninstance Selected Objects (make their data single-user).
  - `DuplicateSlots.b000(self)` — Mirror
  - `DuplicateSlots.b006(self)` — Duplicate Linear
  - `DuplicateSlots.b007(self)` — Duplicate Radial
  - `DuplicateSlots.b008(self)` — Duplicate Grid

<a id="slots--blender--edit"></a>
### `slots/blender/edit.py`

- **[`class EditSlots(EditMixin, SlotsBlender)`](tentacle/tentacle/slots/blender/edit.py#L8)** — Blender port of the shared ``edit`` menu.
  - `EditSlots.header_init(self, widget)`
  - `EditSlots.b_channels(self)` — Channels — open the spreadsheet-style channel editor (btk.Channels panel).
  - `EditSlots.tb000_init(self, widget)`
  - `EditSlots.tb000(self, widget)` — Mesh Cleanup — Repair (fix) or, in Select mode, select the matched problem geometry.
  - `EditSlots.tb002(self, widget)` — Delete Selected (objects in object mode, components by select mode in edit mode).
  - `EditSlots.list000_init(self, widget)` — Initialize Create Primitives list — 6 categories, mirroring Maya's Polygon/NURBS/
  - `EditSlots.list000(self, item)` — Create Primitive — branch per category the way Maya's list000 does (Control/Curve/
  - `EditSlots.list001_init(self, widget)` — Initialize Convert list.
  - `EditSlots.list001(self, item)` — Convert the selected object(s) to another type (or run a Convert-list action that
  - `EditSlots.b000(self)` — Cut On Axis
  - `EditSlots.cmb000(self, index, widget)` — Transfer — dispatch the selected transfer operation.
  - `EditSlots.tb001_init(self, widget)` — Optimize — relabel the shared "Delete History" button (its text lives in the shared
  - `EditSlots.tb001(self, widget)` — Optimize — purge orphaned (zero-user) datablocks;
  - `EditSlots.tb004_init(self, widget)` — Object Locking — Lock/Unlock selector (mirror of Maya's cmb_lock).
  - `EditSlots.tb004(self, widget)` — Object Locking — Blender's analogue of Maya's node lock: toggle ``hide_select`` (make

<a id="slots--blender--editors"></a>
### `slots/blender/editors.py`

- **[`class EditorsSlots(SlotsBlender)`](tentacle/tentacle/slots/blender/editors.py#L7)** — Blender port of the shared ``editors`` menu.
  - `EditorsSlots.list000_init(self, widget)` — Initialize the editors list (categories → Blender editors).
  - `EditorsSlots.list000(self, item)` — Open the picked editor in a new window (category headers are nav-only).
  - `EditorsSlots.b000(self)` — Attributes (Properties editor)
  - `EditorsSlots.b001(self)` — Outliner
  - `EditorsSlots.b002(self)` — Tool (active-tool settings live in the Properties editor's Tool tab)
  - `EditorsSlots.b003(self)` — Layers (Blender's collections live in the Outliner)
  - `EditorsSlots.b004(self)` — Channels (object data lives in the Properties editor)
  - `EditorsSlots.b005(self)` — Node Editor (Shader Editor)
  - `EditorsSlots.b006_init(self, widget)` — Relabel: Dependency Graph → Geometry Nodes.
  - `EditorsSlots.b006(self)` — Geometry Nodes (substitute for Maya's Dependency Graph)
  - `EditorsSlots.b007_init(self, widget)` — Relabel: Status Line → UV Editor.
  - `EditorsSlots.b007(self)` — UV Editor (substitute for Maya's Status Line toggle)
  - `EditorsSlots.b008_init(self, widget)` — Relabel: Shelf → Image Editor.
  - `EditorsSlots.b008(self)` — Image Editor (substitute for Maya's Shelf toggle)
  - `EditorsSlots.b009(self)` — Time & Range — toggle the Timeline docked along the bottom of the viewport, in place.
  - `EditorsSlots.b010(self)` — Script Output — the shared ``uitk.ScriptOutput`` console (syntax-highlighted
  - `EditorsSlots.b011(self)` — Command Line (Python Console)
  - `EditorsSlots.b012_init(self, widget)` — Relabel: Help Line → Graph Editor.
  - `EditorsSlots.b012(self)` — Graph Editor (substitute for Maya's Help Line toggle)
  - `EditorsSlots.b013_init(self, widget)` — Relabel: Tool Box → Text Editor.
  - `EditorsSlots.b013(self)` — Text Editor (substitute for Maya's Tool Box toggle)

<a id="slots--blender--hud"></a>
### `slots/blender/hud.py`

- **[`class StatusMixin`](tentacle/tentacle/slots/blender/hud.py#L11)**
  - `StatusMixin.insert_scene_status(self, hud) -> None`
- **[`class HudSelectionMixin`](tentacle/tentacle/slots/blender/hud.py#L41)** — HUD readout of what is selected — unrelated to the package-level
  - `HudSelectionMixin.insert_selection_info(self, hud, selection) -> None`
  - `HudSelectionMixin.insert_component_info(self, hud, active) -> None` — Selected/total component counts for the mesh being edited (cheap:
- **[`class WarningsMixin(HudWarningsMixin)`](tentacle/tentacle/slots/blender/hud.py#L113)** — Blender HUD warnings — the framework lives in the shared
- **[`class HudSlots(SlotsBlender, StatusMixin, HudSelectionMixin, WarningsMixin)`](tentacle/tentacle/slots/blender/hud.py#L172)** — HUD Slots for Blender, providing scene and selection information.
  - `HudSlots.request_hud_build(self) -> None` — Start a new HUD build request, only the latest token will be used.
  - `HudSlots.construct_hud(self) -> None`

<a id="slots--blender--lighting"></a>
### `slots/blender/lighting.py`

- **[`class LightingSlots(LightingMixin, SlotsBlender)`](tentacle/tentacle/slots/blender/lighting.py#L8)** — Blender port of the shared ``lighting`` menu.
  - `LightingSlots.b000(self)` — Launch the HDR Manager (world-environment HDRI panel).
  - `LightingSlots.b001(self)` — Launch the Lightmap Baker (Cycles-bake → game-engine lightmaps).
  - `LightingSlots.b002_init(self, widget)` — Light Rigs -- hidden until ported: blendertk has no LightRig twin yet, so the
  - `LightingSlots.b002(self)` — Light Rigs -- unreachable (b002_init hides the button);
  - `LightingSlots.tb000_init(self, widget)` — Lights From Geometry Init
  - `LightingSlots.tb000(self, widget)` — Create real area lights from the selected fixture meshes.

<a id="slots--blender--main"></a>
### `slots/blender/main.py`

- **[`class MainSlots(MainMixin, SlotsBlender)`](tentacle/tentacle/slots/blender/main.py#L9)** — Blender port of the shared ``main`` start menu — a workspace switcher (primary) with
  - `MainSlots.list000_init(self, widget)` — Initialize the Workspace tab.
  - `MainSlots.list000(self, item)` — Workspace tab dispatch — editing actions, recent-workspace selection, and the

<a id="slots--blender--materials"></a>
### `slots/blender/materials.py`

- **[`class MaterialsSlots(MaterialsMixin, SlotsBlender)`](tentacle/tentacle/slots/blender/materials.py#L10)** — Blender port of the shared ``materials`` menu — mirrors the Maya slot's workflow against
  - `MaterialsSlots.b_shader_editor(self)` — Shader Editor — Blender's analogue of Maya's Hypershade.
  - `MaterialsSlots.select_by_mat(self, shell=False, in_selection=False, get_first=False, add=False, unassigned=False)` — Select the geometry carrying the current material.
  - `MaterialsSlots.tb001_init(self, widget)` — Get Material Info — option box.
  - `MaterialsSlots.tb001(self, widget)` — Get Material Info — render a formatted report to the text-view dialog.
  - `MaterialsSlots.list000_init(self, widget)` — The submenu's Assign list: assign-current root + New / Random + the
  - `MaterialsSlots.list000(self, item)` — Assign list: root assigns the current material;
  - `MaterialsSlots.list001(self, item)` — Dispatch a Tools-list selection to its slot method.
  - `MaterialsSlots.b004(self, widget=None)` — Assign Random
  - `MaterialsSlots.b013(self)` — Reload Scene Textures
  - `MaterialsSlots.b015(self, widget=None)` — Delete All Unused Materials
  - `MaterialsSlots.lbl004(self)` — Select Node — select the object(s) using the current material.
  - `MaterialsSlots.lbl006(self)` — Open in Editor — graph the current material in the Shader Editor.
  - `MaterialsSlots.b021(self)` — Image to Plane — open the panel (batch image→plane with aspect sizing, material affix
  - `MaterialsSlots.b010(self)` — Texture Path Editor — co-located blendertk panel (list / repath / resolve-missing /
  - `MaterialsSlots.b009(self)` — Game Shader — co-located blendertk panel (auto-build a Principled material from a PBR
  - `MaterialsSlots.b027(self)` — Emissive Groups — co-located blendertk panel (named face groups a game engine gates at
  - `MaterialsSlots.b011(self)` — Shader Templates — co-located blendertk panel (Principled-BSDF presets: create new /
  - `MaterialsSlots.b018(self)` — Update Materials (Material Updater) — co-located blendertk panel (batch-reprocess material
  - `MaterialsSlots.b008(self)` — Map Packer
  - `MaterialsSlots.b016(self)` — Map Converter
  - `MaterialsSlots.b022(self)` — Map Compositor
  - `MaterialsSlots.b023(self)` — Metashape Workflow
  - `MaterialsSlots.b024(self)` — RealityCapture Workflow
  - `MaterialsSlots.b025(self)` — Brush Splat Workflow
  - `MaterialsSlots.b019(self)` — Marmoset Bridge
  - `MaterialsSlots.b020(self)` — Substance Bridge

<a id="slots--blender--nurbs"></a>
### `slots/blender/nurbs.py`

- **[`class NurbsSlots(NurbsMixin, SlotsBlender)`](tentacle/tentacle/slots/blender/nurbs.py#L10)** — Blender port of the shared ``nurbs`` menu.
  - `NurbsSlots.b058(self)` — Curve to Tube (curve bevel).
  - `NurbsSlots.tb000_init(self, widget)`
  - `NurbsSlots.tb000(self, widget)` — Revolve (Screw modifier;
  - `NurbsSlots.tb001_init(self, widget)`
  - `NurbsSlots.tb001(self, widget)` — Loft — bridge the selected profile curves / mesh loops into a surface (btk.loft).
  - `NurbsSlots.list000(self, item)` — Dispatch a Nurbs leaf action (mirrors Maya's list000: no-op on a node that still
  - `NurbsSlots.b030(self)` — Extrude Curve Profile — build a surface from the selected curve(s), the Blender
  - `NurbsSlots.b056(self)` — Image Tracer (native wrap: trace the active image-empty to Grease Pencil,

<a id="slots--blender--pivot"></a>
### `slots/blender/pivot.py`

- **[`class PivotSlots(PivotMixin, SlotsBlender)`](tentacle/tentacle/slots/blender/pivot.py#L8)** — Blender port of the shared ``pivot`` menu.
  - `PivotSlots.tb000_init(self, widget)`
  - `PivotSlots.tb000(self, widget)` — Reset Pivot
  - `PivotSlots.tb001_init(self, widget)`
  - `PivotSlots.tb001(self, widget)` — Center Pivot
  - `PivotSlots.tb002_init(self, widget)` — Transfer Pivot options — the Mirror combo only.
  - `PivotSlots.tb002(self, widget)` — Transfer Pivot — move the selected objects' origins onto the **active** object's origin.
  - `PivotSlots.tb003_init(self, widget)`
  - `PivotSlots.tb003(self, widget)` — World-Aligned Pivot — a faithful mirror of Maya's ``tb003`` *including its
  - `PivotSlots.b004(self)` — Bake Pivot — bake Blender's *temporary* pivot, the 3D cursor, into the selected

<a id="slots--blender--polygons"></a>
### `slots/blender/polygons.py`

- **[`class PolygonsSlots(SlotsBlender)`](tentacle/tentacle/slots/blender/polygons.py#L9)** — Blender port of the shared ``polygons`` menu.
  - `PolygonsSlots.header_init(self, widget)`
  - `PolygonsSlots.tb000_init(self, widget)`
  - `PolygonsSlots.tb000(self, widget)` — Merge Vertices
  - `PolygonsSlots.b005(self)` — Merge Vertices: Set Distance — set the merge threshold from two selected verts
  - `PolygonsSlots.tb002_init(self, widget)`
  - `PolygonsSlots.tb002(self, widget)` — Separate (split the mesh into loose parts, or by material).
  - `PolygonsSlots.tb003_init(self, widget)`
  - `PolygonsSlots.tb003(self, widget)` — Extrude (region together or per-face), then offset along normals.
  - `PolygonsSlots.tb004_init(self, widget)`
  - `PolygonsSlots.tb004(self, widget)` — Combine Selected Meshes (optionally one mesh per material / clustered by distance).
  - `PolygonsSlots.tb005_init(self, widget)`
  - `PolygonsSlots.tb005(self, widget)` — Detach (separate selected components into a new object;
  - `PolygonsSlots.tb006_init(self, widget)`
  - `PolygonsSlots.tb006(self, widget)` — Inset Face Region
  - `PolygonsSlots.tb007_init(self, widget)`
  - `PolygonsSlots.tb007(self, widget)` — Divide Facet (subdivide the selected components).
  - `PolygonsSlots.tb008_init(self, widget)`
  - `PolygonsSlots.tb008(self, widget)` — Boolean Operation (active mesh = base, other selected = operands).
  - `PolygonsSlots.tb009_init(self, widget)`
  - `PolygonsSlots.tb009(self, widget)` — Snap Closest Verts (the other selected mesh's verts snap onto the ACTIVE mesh).
  - `PolygonsSlots.b001(self)` — Fill Holes
  - `PolygonsSlots.b003(self)` — Symmetrize
  - `PolygonsSlots.b006(self)` — Bridge (selected edge loops).
  - `PolygonsSlots.b007(self)` — Bridge Interactive — open the Bridge panel (Divisions / Offset + live Preview),
  - `PolygonsSlots.b008(self)` — Weld Center: interactive target weld merging at the midpoint (mirror of Maya's
  - `PolygonsSlots.b009(self)` — Collapse Component: faces per region, verts/edges at one center.
  - `PolygonsSlots.b011(self)` — Bevel — open the bevel panel (Width / Segments / Profile + live Preview),
  - `PolygonsSlots.b012(self)` — Multi-Cut Tool (Knife) — EDIT_MESH-only, so the mesh is put into component mode.
  - `PolygonsSlots.b022(self)` — Attach — Maya's Connect-components tool (dR_connectTool;
  - `PolygonsSlots.b032(self)` — Poke
  - `PolygonsSlots.b047(self)` — Insert Edgeloop (Loop Cut tool) — EDIT_MESH-only, so the mesh is put into
  - `PolygonsSlots.b051(self)` — Offset Edgeloop
  - `PolygonsSlots.b043(self)` — Target Weld: interactively merge one vertex onto another by dragging.
  - `PolygonsSlots.b000(self)` — Circularize (LoopTools Circle on the selected edge loop).
  - `PolygonsSlots.b053(self)` — Edit Edge Flow (Set Flow on the selected edge loops).
  - `PolygonsSlots.b034(self)` — Wedge (sweep the selected faces 90° around a selected hinge edge).
  - `PolygonsSlots.b038_init(self, widget)` — Assign Invisible — hidden: Maya ``polyHole`` invisible/hole faces have no Blender
  - `PolygonsSlots.b038(self)` — Assign Invisible — unreachable (b038_init hides the button);
  - `PolygonsSlots.b049(self)` — Slide Edge — interactively slide the selected edge loop along the surface, the

<a id="slots--blender--preferences"></a>
### `slots/blender/preferences.py`

- **[`class PreferencesSlots(PreferencesMixin, SlotsBlender)`](tentacle/tentacle/slots/blender/preferences.py#L11)** — Blender port of the shared ``preferences`` menu.
  - `PreferencesSlots.cmb001_init(self, widget)`
  - `PreferencesSlots.cmb001(self, index, widget)` — Set Working Units: Linear
  - `PreferencesSlots.cmb002_init(self, widget)`
  - `PreferencesSlots.cmb002(self, index, widget)` — Set Working Units: Time (frame rate)
  - `PreferencesSlots.s000_init(self, widget)`
  - `PreferencesSlots.s001_init(self, widget)`
  - `PreferencesSlots.b001(self)` — Color Settings → Blender Preferences (Themes).
  - `PreferencesSlots.cmb003_init(self, widget)` — App-style / theme selector — mirrors Blender's Preferences > Themes dropdown.
  - `PreferencesSlots.cmb003(self, index, widget)` — Apply the selected native theme preset (Blender's built-in, the user's own, or our
  - `PreferencesSlots.b008(self)` — Hotkeys → Blender Preferences (Keymap).
  - `PreferencesSlots.b009(self)` — Plug-In Manager → Blender Preferences (Add-ons).
  - `PreferencesSlots.b010(self)` — Settings/Preferences → Blender Preferences (Interface).

<a id="slots--blender--rendering"></a>
### `slots/blender/rendering.py`

- **[`class RenderingSlots(RenderingMixin, SlotsBlender)`](tentacle/tentacle/slots/blender/rendering.py#L10)** — Blender port of the shared ``rendering`` menu.
  - `RenderingSlots.tb000_init(self, widget)` — Playblast: built once, then re-run on every panel show.
  - `RenderingSlots.tb000(self, widget)` — Export Playblast (OpenGL viewport render of the chosen frame range / format).
  - `RenderingSlots.tb001_init(self, widget)` — Render: pick the camera and renderer, then render the current frame.
  - `RenderingSlots.tb001(self, widget)` — Render Current Frame
  - `RenderingSlots.b000(self, widget)` — WebXR Preview — open the live preview panel, wired to this scene.
  - `RenderingSlots.b001(self)` — Render Settings (Properties editor, Render tab)
  - `RenderingSlots.b003(self)` — Render Setup — Maya's render-layer manager maps onto Blender's **View Layers**
  - `RenderingSlots.b004(self)` — Rendering Flags — Maya's per-object render flags map onto Blender's per-object ray

<a id="slots--blender--rigging"></a>
### `slots/blender/rigging.py`

- **[`class RiggingSlots(RiggingMixin, SlotsBlender)`](tentacle/tentacle/slots/blender/rigging.py#L9)** — Blender port of the shared ``rigging`` menu.
  - `RiggingSlots.header_init(self, widget)`
  - `RiggingSlots.b020(self)` — Rebind Skin Clusters — refresh each selected mesh's Armature modifier (re-point it at its
  - `RiggingSlots.cmb001_init(self, widget)`
  - `RiggingSlots.cmb001(self, index, widget)` — Create rigging primitives.
  - `RiggingSlots.tb000_init(self, widget)`
  - `RiggingSlots.tb000(self, widget)` — Toggle Display Local Rotation Axes — object axes (show_axis), or armature bone axes
  - `RiggingSlots.tb001_init(self, widget)`
  - `RiggingSlots.tb001(self, widget)` — Constraint Switch — drive the active object's constraints' influence from a single custom
  - `RiggingSlots.tb003_init(self, widget)`
  - `RiggingSlots.tb003(self, widget)` — Create Locator at Selection — a zeroed locator Empty at each selected object's
  - `RiggingSlots.tb004_init(self, widget)`
  - `RiggingSlots.tb004(self, widget)` — Lock/Unlock Attributes (transform channel lock flags, per the chosen scope).
  - `RiggingSlots.tb005_init(self, widget)` — Add to Skin — hidden until ported: the Maya tool (``mtk.SkinUtils.add_to_skin``)
  - `RiggingSlots.tb005(self, widget)` — Add to Skin — unreachable (tb005_init hides the button);
  - `RiggingSlots.cmb002_init(self, widget)`
  - `RiggingSlots.cmb002(self, index, widget)` — Quick Rig — a procedural rig opens its panel (mayatk parity);
  - `RiggingSlots.b004(self)` — Render Effects — the shared tool over ``btk.RenderEffects`` (per-object ``opacity``

<a id="slots--blender--scene"></a>
### `slots/blender/scene.py`

- **[`class SceneSlots(SceneMixin, SlotsBlender)`](tentacle/tentacle/slots/blender/scene.py#L11)** — Blender port of the shared ``scene`` menu.
  - `SceneSlots.list003(self, item)` — Dispatch a Tools leaf to its own slot (shared: ``SceneMixin``).
  - `SceneSlots.list000_init(self, widget)` — Initialize Recent Files
  - `SceneSlots.list000(self, item)` — Recent Files
  - `SceneSlots.cmb002_init(self, widget)` — Initialize Autosave (recent temp-dir .blend autosaves, newest first).
  - `SceneSlots.cmb002(self, index, widget)` — Autosave
  - `SceneSlots.list001_init(self, widget)` — Initialize Import
  - `SceneSlots.list001(self, item)` — Import
  - `SceneSlots.list002_init(self, widget)` — Initialize Export.
  - `SceneSlots.list002(self, item)` — Export.
  - `SceneSlots.tb003_init(self, widget)` — Initialize the Scene Exporter option box — the Blender counterpart of Maya's tb003.
  - `SceneSlots.b011(self)` — Fix Color Spaces — set data textures to 'Non-Color' / color maps to 'sRGB' by map type
  - `SceneSlots.b001(self)` — Reference Manager (library links — File ▸ Link manager panel).
  - `SceneSlots.b010(self)` — Maya Bridge — send the selection to a fresh Maya (btk.MayaBridge).
  - `SceneSlots.b016(self)` — Unity Bridge — send the selection to a Unity project's Assets/ (btk.UnityBridge).
  - `SceneSlots.b005(self)` — Naming — open the shared Naming tool (Find / Rename / Convert Case / Strip Chars /
  - `SceneSlots.b008(self)` — Export Selection (FBX, selected objects only).
  - `SceneSlots.b013(self)` — Mesh Converter (FBX -> GLB).
  - `SceneSlots.b_cleanup(self)` — Scene Cleanup — purge orphan datablocks (no users / no fake user).
  - `SceneSlots.b004(self)` — Hierarchy Sync — diff/repair the scene hierarchy against a reference .blend
  - `SceneSlots.b003(self)` — Audio Clips — the shared tool over ``btk.AudioClips`` (Video Sequence Editor clips:
  - `SceneSlots.b015(self)` — Blendshape Animator — the shared tool (base+target mesh -> keyed shape key,
  - `SceneSlots.b017(self)` — Scene Metadata — the tool-authored data-node channels in the shared data

<a id="slots--blender--selection"></a>
### `slots/blender/selection.py`

- **[`class SelectionSlots(SelectionMixin, SlotsBlender)`](tentacle/tentacle/slots/blender/selection.py#L8)** — Blender port of the shared ``selection`` menu.
  - `SelectionSlots.tb000_init(self, widget)`
  - `SelectionSlots.tb000(self, widget)` — Select Nth
  - `SelectionSlots.tb001_init(self, widget)`
  - `SelectionSlots.tb001(self, widget)` — Select Similar — object-level similarity by topology / area / bounding-box metrics
  - `SelectionSlots.tb002_init(self, widget)`
  - `SelectionSlots.tb002(self, widget)` — Select Island (connected region;
  - `SelectionSlots.tb003_init(self, widget)`
  - `SelectionSlots.tb003(self, widget)` — Select Edges By Angle (within the Low–High range, via ``btk.select_edges_by_angle``).
  - `SelectionSlots.list001(self, item)` — Convert the current selection to another component type (Maya Convert-To parity).
  - `SelectionSlots.chk004_init(self, widget)` — Reflect the live viewport X-ray state (the DCC owns it — see ``mirror_app_state``).
  - `SelectionSlots.chk004(self, state, widget)` — Ignore Backfacing — toggle viewport X-ray (occlude) so only front faces select.
  - `SelectionSlots.chk005_init(self, widget)`
  - `SelectionSlots.chk006_init(self, widget)` — Select Style: Lasso — mirrors the active tool;
  - `SelectionSlots.chk007_init(self, widget)` — Select Style: Circle — mirrors the active tool;
  - `SelectionSlots.chk005(self, state, widget)` — Select Style: Box (Marquee)
  - `SelectionSlots.chk006(self, state, widget)` — Select Style: Lasso
  - `SelectionSlots.chk007(self, state, widget)` — Select Style: Circle (Paint)
  - `SelectionSlots.b001(self)` — Toggle Selectability of the selected object(s).
  - `SelectionSlots.b002_init(self, widget)` — Selection constraint: Angle.
  - `SelectionSlots.b002(self, widget)` — Selection constraint: Angle (one-shot expand).
  - `SelectionSlots.b003_init(self, widget)` — Selection constraint: Border.
  - `SelectionSlots.b003(self, widget)` — Selection constraint: Border (one-shot expand).
  - `SelectionSlots.b004_init(self, widget)` — Selection constraint: Edge Loop.
  - `SelectionSlots.b004(self, widget)` — Selection constraint: Edge Loop (one-shot expand).
  - `SelectionSlots.b005_init(self, widget)` — Selection constraint: Edge Ring.
  - `SelectionSlots.b005(self, widget)` — Selection constraint: Edge Ring (one-shot expand).
  - `SelectionSlots.b006_init(self, widget)` — Selection constraint: Shell.
  - `SelectionSlots.b006(self, widget)` — Selection constraint: Shell (one-shot expand).
  - `SelectionSlots.b007_init(self, widget)` — Selection constraint: UV Edge Loop.
  - `SelectionSlots.b007(self, widget)` — Selection constraint: UV Edge Loop (one-shot expand).
  - `SelectionSlots.cmb002_init(self, widget)` — Rig Picking Mode — hidden: the Maya modes (``mtk.Selection.set_rig_selection_mode``)
  - `SelectionSlots.cmb002(self, index, widget)` — Rig Picking Mode — unreachable (cmb002_init hides the combo).
  - `SelectionSlots.cmb001_init(self, widget)` — Reorder Selection — backed by the rolled ``btk.SelectionOrder`` tracker (Blender
  - `SelectionSlots.cmb001(self, index, widget)` — Reorder Selection (sort via ``btk.reorder_objects``, record the order on
  - `SelectionSlots.list000_init(self, widget)` — Select by Type: hierarchical type list.
  - `SelectionSlots.tb004_init(self, widget)` — Select by Type settings menu (mirror of the Maya slot's tb004).
  - `SelectionSlots.list000(self, item)` — Select by Type (native bpy predicates via ``btk.Selection``).

<a id="slots--blender--settings"></a>
### `slots/blender/settings.py`

- **[`class SettingsSlots(SettingsMixin, SlotsBlender)`](tentacle/tentacle/slots/blender/settings.py#L9)** — Blender fork of the shared ``settings`` menu.
  - `SettingsSlots.tb001(self)` — Reload Scripts (tear down, reload the tentacle ecosystem in place, re-register).

<a id="slots--blender--subdivision"></a>
### `slots/blender/subdivision.py`

- **[`class SubdivisionSlots(SlotsBlender)`](tentacle/tentacle/slots/blender/subdivision.py#L7)** — Blender port of the shared ``subdivision`` menu.
  - `SubdivisionSlots.tb000_init(self, widget)`
  - `SubdivisionSlots.tb000(self, widget)` — Decimate: reduce face count by collapse percentage or coplanar-face dissolve.
  - `SubdivisionSlots.s000_init(self, widget)` — Division Level — reflect the active object's live viewport subdivision level.
  - `SubdivisionSlots.s001_init(self, widget)` — Tesselation Level — reflect the active object's live render subdivision level.
  - `SubdivisionSlots.s000(self, value, widget)` — Division Level (live Subdivision-Surface viewport level).
  - `SubdivisionSlots.s001(self, value, widget)` — Tesselation Level (Subdivision-Surface render level).
  - `SubdivisionSlots.b000(self)` — Quadrangulate (tris -> quads).
  - `SubdivisionSlots.b001(self)` — Triangulate
  - `SubdivisionSlots.b005(self)` — Reduce (decimate to 50%) — whole meshes, or the selected components in Edit Mode.
  - `SubdivisionSlots.b008(self)` — Add Divisions - Subdivide Mesh
  - `SubdivisionSlots.b011(self)` — Apply Smooth Preview — bake the live Subdivision-Surface modifier to polygons
  - `SubdivisionSlots.b028(self)` — Quad Draw (Blender's retopo equivalent: the Poly Build tool) — EDIT_MESH-only, so

<a id="slots--blender--symmetry"></a>
### `slots/blender/symmetry.py`

- **[`class SymmetrySlots(SlotsBlender)`](tentacle/tentacle/slots/blender/symmetry.py#L6)** — Blender port of the shared ``symmetry`` menu.
  - `SymmetrySlots.chk000_init(self, widget)` — Set initial symmetry state from the active mesh.
  - `SymmetrySlots.chk001_init(self, widget)` — Symmetry Y — mirrors the active mesh;
  - `SymmetrySlots.chk002_init(self, widget)` — Symmetry Z — mirrors the active mesh;
  - `SymmetrySlots.chk000(self, state, widget)` — Symmetry X
  - `SymmetrySlots.chk001(self, state, widget)` — Symmetry Y
  - `SymmetrySlots.chk002(self, state, widget)` — Symmetry Z
  - `SymmetrySlots.chk004(self, state, widget)` — Symmetry: match by position (Blender mirror flags are always object-space;
  - `SymmetrySlots.chk004_init(self, widget)` — Match-by-position — mirrors the active mesh;
  - `SymmetrySlots.chk005_init(self, widget)` — Set symmetry reference space (position vs topology), mirrored from the active mesh.
  - `SymmetrySlots.chk005(self, state, widget)` — Symmetry: Topo (match mirrored verts by topology instead of position).

<a id="slots--blender--transform"></a>
### `slots/blender/transform.py`

- **[`class TransformSlots(TransformMixin, SlotsBlender)`](tentacle/tentacle/slots/blender/transform.py#L10)** — Blender port of the shared ``transform`` menu.
  - `TransformSlots.header_init(self, widget)` — Header — Fix Non-Orthogonal Axes + the Snap Toolset button.
  - `TransformSlots.b_snap_ts(self)` — Snap Toolset — open the Snap panel (mirror of Maya's b_snap_ts).
  - `TransformSlots.fix_non_ortho_axes(self)` — Fix Non-Orthogonal Axes (bake out shear on the selected objects).
  - `TransformSlots.tb000_init(self, widget)`
  - `TransformSlots.tb000(self, widget)` — Drop To Grid
  - `TransformSlots.tb002_init(self, widget)`
  - `TransformSlots.tb002(self, widget)` — Freeze Transformations
  - `TransformSlots.tb005_init(self, widget)`
  - `TransformSlots.tb005(self, widget)` — Move To (align source object(s) to the active/target object).
  - `TransformSlots.b001(self)` — Match Scale (rescale the active object to the other selected objects' combined
  - `TransformSlots.cmb002_init(self, widget)`
  - `TransformSlots.cmb002(self, index, widget)` — Align To (object centers onto the active object's, native ``object.align``).
  - `TransformSlots.tb004_init(self, widget)`
  - `TransformSlots.tb004(self, widget)` — Transform Snap (per-transform increment snapping via the scene tool settings).
  - `TransformSlots.s023(self, value, widget)` — Transform Tool Snap Settings: rotate increment (degrees → the scene's
  - `TransformSlots.chk023_init(self, widget)` — Snap Rotate toggle — reflect the live tool-settings state.
  - `TransformSlots.chk023(self, state, widget)` — Snap: Rotate (increment rotation snapping).
  - `TransformSlots.tb001(self, widget)` — Scale Connected Edges (each connected set of selected edges scales about its
  - `TransformSlots.b002_init(self, widget)` — Un-Freeze Transforms Init (mirror of the Maya panel's b002 option box).
  - `TransformSlots.b_restore_axes(self)` — Restore Authored Axes - point the gizmo at the pre-freeze frame.
  - `TransformSlots.b002(self, widget)` — Un-Freeze Transforms (restore the channels stamped by Freeze;
  - `TransformSlots.tb003_init(self, widget)` — Constraints Init (mirrors the Maya option box;
  - `TransformSlots.chk024(self, state, widget)` — Transform Constraints: Edge (snap-to-edge during move).
  - `TransformSlots.chk025(self, state, widget)` — Transform Constraints: Surface (snap-to-face during move).
  - `TransformSlots.chk026(self, state, widget)` — Transform Constraints: Make Live (project transformed geometry onto surfaces —

<a id="slots--blender--utilities"></a>
### `slots/blender/utilities.py`

- **[`class UtilitiesSlots(SlotsBlender)`](tentacle/tentacle/slots/blender/utilities.py#L7)** — Blender port of the shared ``utilities`` menu.
  - `UtilitiesSlots.b000(self)` — Measure
  - `UtilitiesSlots.b001(self)` — Annotation
  - `UtilitiesSlots.b002(self)` — Calculator
  - `UtilitiesSlots.b003(self)` — Grease Pencil (add an empty stroke object to draw into)

<a id="slots--blender--uv"></a>
### `slots/blender/uv.py`

- **[`class UvSlots(UvMixin, SlotsBlender)`](tentacle/tentacle/slots/blender/uv.py#L10)** — Blender port of the shared ``uv`` menu.
  - `UvSlots.tb000_init(self, widget)`
  - `UvSlots.tb000(self, widget)` — Pack UVs (optionally equal-texel-density pre-scaled), then moved into the target
  - `UvSlots.tb001_init(self, widget)`
  - `UvSlots.tb001(self, widget)` — Auto Unwrap (Smart UV Project, or an external unwrapping engine).
  - `UvSlots.tb004_init(self, widget)`
  - `UvSlots.tb004(self, widget)` — Unfold (unwrap, then optionally relax, axis-align, and stack similar shells).
  - `UvSlots.tb009_init(self, widget)`
  - `UvSlots.tb009(self, widget)` — Cut Cylinder — seam by crease angle, then unfold.
  - `UvSlots.b005(self)` — Cut UVs (mark seam on selected edges)
  - `UvSlots.b011(self)` — Sew UVs (clear seam on selected edges)
  - `UvSlots.b021(self, widget)` — Unfold and Pack UVs
  - `UvSlots.tb007_init(self, widget)` — Cleanup UV Sets option box (reuses the Maya objectNames + labels — same options,
  - `UvSlots.tb007(self, widget)` — Cleanup UV Sets (standardize/clean the UV layers — mirror of Maya's cleanup_uv_sets).
  - `UvSlots.header_init(self, widget)` — Header menu — Create UV Snapshot + RizomUV Bridge (reuse the Maya objectNames + labels,
  - `UvSlots.uv_snapshot(self)` — Create UV Snapshot — export the active mesh's UV layout to an image.
  - `UvSlots.b031(self)` — Open UV Editor
  - `UvSlots.b003(self)` — Get Texel Density (into the s003 readout, against the cmb003 map size).
  - `UvSlots.b004(self)` — Set Texel Density (from the s003 value, against the cmb003 map size).
  - `UvSlots.b029(self, widget)` — Pin / Unpin UVs (dual-state toggle, Maya parity: first click on a fresh selection
  - `UvSlots.tb022_init(self, widget)`
  - `UvSlots.tb022(self, widget)` — Cut UV Hard Edges (mark seams on edges whose dihedral angle is in the [low, high]
  - `UvSlots.b030(self, widget)` — Stack / Unstack shells (dual-state toggle: first click stacks the targeted
  - `UvSlots.b032(self)` — RizomUV Bridge — co-located blendertk panel (round-trip Lua presets + one-way send).
  - `UvSlots.b033(self)` — Open the Shell Xform panel — the ``More..`` button in the Transform group.

<a id="slots--maya--_slots_maya"></a>
### `slots/maya/_slots_maya.py`

- **[`class SlotsMaya(Slots)`](tentacle/tentacle/slots/maya/_slots_maya.py#L8)** — App specific methods inherited by all other app specific slot classes.
  - `SlotsMaya.require_selection(self, message=None, **kwargs)` — The current selection, or ``None`` — after a message box — when it is empty.

<a id="slots--maya--animation"></a>
### `slots/maya/animation.py`

- **[`class AnimationSlots(AnimationMixin, SlotsMaya)`](tentacle/tentacle/slots/maya/animation.py#L8)**
  - `AnimationSlots.list000(self, item)` — Dispatch a Tools leaf to its slot method.
  - `AnimationSlots.b001(self)` — Repair Visibility Tangents
  - `AnimationSlots.tb000_init(self, widget)` — Go To Frame Init
  - `AnimationSlots.tb000(self, widget)` — Go To Frame: jump the time slider to the next/previous key or a snap target.
  - `AnimationSlots.tb001_init(self, widget)` — Invert Keyframes Init
  - `AnimationSlots.tb001(self, widget)` — Invert keyframes (selected keys preferred, fallback to all keys).
  - `AnimationSlots.tb002_init(self, widget)` — Adjust Spacing Init
  - `AnimationSlots.tb002(self, widget)` — Adjust spacing
  - `AnimationSlots.tb003_init(self, widget)` — Stagger Keys Init
  - `AnimationSlots.tb003(self, widget)` — Stagger Keys
  - `AnimationSlots.tb004_init(self, widget)` — Transfer Keys Init
  - `AnimationSlots.tb004(self, widget)` — Transfer Keys
  - `AnimationSlots.tb005_init(self, widget)` — Add/Remove Intermediate Keys Init
  - `AnimationSlots.tb005(self, widget)` — Add/Remove Intermediate Keys.
  - `AnimationSlots.tb006_init(self, widget)` — Move Keys Init
  - `AnimationSlots.tb006(self, widget)` — Move Keys: move the selected keys in time, with optional spacing/alignment.
  - `AnimationSlots.tb007_init(self, widget)` — Align Selected Keyframes Init
  - `AnimationSlots.tb007(self, widget)` — Align Selected Keyframes
  - `AnimationSlots.tb008_init(self, widget)` — Set Visibility Keys Init
  - `AnimationSlots.tb008(self, widget)` — Set Visibility Keys
  - `AnimationSlots.tb009_init(self, widget)` — Snap Keys to Frames Init
  - `AnimationSlots.tb009(self, widget)` — Snap Keys to Frames
  - `AnimationSlots.tb010_init(self, widget)` — Delete Keys Init
  - `AnimationSlots.tb010(self, widget)` — Delete Keys: delete keys on the selection over a chosen time range.
  - `AnimationSlots.tb011_init(self, widget)` — Tie/Untie Keyframes Init
  - `AnimationSlots.tb011(self, widget)` — Tie/Untie Keyframes
  - `AnimationSlots.tb013_init(self, widget)` — Select Keys Init
  - `AnimationSlots.tb013(self, widget)` — Select Keys: select keys on the selection within a frame range.
  - `AnimationSlots.tb014_init(self, widget)` — Scale Keys Init
  - `AnimationSlots.tb014(self, widget)` — Scale Keys: scale the selected keys in time about a pivot.
  - `AnimationSlots.tb015_init(self, widget)` — Repair Corrupted Curves - Initialize option box
  - `AnimationSlots.tb015(self, widget)` — Repair Corrupted Curves
  - `AnimationSlots.tb021_init(self, widget)` — Snap Fractional Key Times — initialize the option box.
  - `AnimationSlots.tb021(self, widget)` — Snap Fractional Key Times — the repair-scoped twin of Snap Keys.
  - `AnimationSlots.tb016_init(self, widget)` — Get Animation Info — option box.
  - `AnimationSlots.tb016(self, widget)` — Get Animation Info — render the report to the viewer dialog.
  - `AnimationSlots.tb017_init(self, widget)` — Step Tangents Init
  - `AnimationSlots.tb017(self, widget)` — Step Tangents — set stepped tangents on keys.
  - `AnimationSlots.tb012_init(self, widget)` — Copy Keys Init
  - `AnimationSlots.tb012(self, widget)` — Copy Keys: copy the selected objects' keys for later paste.
  - `AnimationSlots.tb018_init(self, widget)` — Paste Keys Init
  - `AnimationSlots.tb018(self, widget)` — Paste Keys: paste previously copied keys onto the selection.
  - `AnimationSlots.tb019_init(self, widget)` — Optimize Keys Init
  - `AnimationSlots.tb019(self, widget)` — Optimize Keys — remove redundant animation data.
  - `AnimationSlots.tb020(self, widget)` — Smart Bake
  - `AnimationSlots.b000(self)` — Open Shot Sequencer
  - `AnimationSlots.b004(self)` — Open Shot Manifest
  - `AnimationSlots.b005(self)` — Fit Playback Range
  - `AnimationSlots.b006(self)` — Open Key Stash

<a id="slots--maya--arnold"></a>
### `slots/maya/arnold.py`

- **[`class ArnoldSlots(SlotsMaya)`](tentacle/tentacle/slots/maya/arnold.py#L8)**

<a id="slots--maya--cache"></a>
### `slots/maya/cache.py`

- **[`class CacheSlots(SlotsMaya)`](tentacle/tentacle/slots/maya/cache.py#L8)**

<a id="slots--maya--cameras"></a>
### `slots/maya/cameras.py`

- **[`class CamerasSlots(SlotsMaya)`](tentacle/tentacle/slots/maya/cameras.py#L9)**
  - `CamerasSlots.list000_init(self, widget)` — Initialize Camera Options List
  - `CamerasSlots.list000(self, item)` — Camera Options List
  - `CamerasSlots.b000(self)` — Cameras: Back View
  - `CamerasSlots.b001(self)` — Cameras: Top View
  - `CamerasSlots.b002(self)` — Cameras: Right View
  - `CamerasSlots.b003(self)` — Cameras: Left View
  - `CamerasSlots.b004(self)` — Cameras: Perspective View
  - `CamerasSlots.b005(self)` — Cameras: Front View
  - `CamerasSlots.b006(self)` — Cameras: Bottom View
  - `CamerasSlots.b007(self)` — Cameras: Align View
  - `CamerasSlots.b010(self)` — Camera: Dolly
  - `CamerasSlots.b011(self)` — Camera: Roll
  - `CamerasSlots.b012(self)` — Camera: Truck
  - `CamerasSlots.b013(self)` — Camera: Orbit

<a id="slots--maya--constrain"></a>
### `slots/maya/constrain.py`

- **[`class ConstrainSlots(SlotsMaya)`](tentacle/tentacle/slots/maya/constrain.py#L8)**

<a id="slots--maya--control"></a>
### `slots/maya/control.py`

- **[`class ControlSlots(SlotsMaya)`](tentacle/tentacle/slots/maya/control.py#L8)**

<a id="slots--maya--crease"></a>
### `slots/maya/crease.py`

- **[`class CreaseSlots(SlotsMaya)`](tentacle/tentacle/slots/maya/crease.py#L8)**
  - `CreaseSlots.tb000_init(self, widget)`
  - `CreaseSlots.tb000(self, widget)` — Crease: crease the selected edges (subdivision sharpness), with an optional smoothing angle.
  - `CreaseSlots.b002(self, widget)` — Transfer Crease Edges

<a id="slots--maya--curves"></a>
### `slots/maya/curves.py`

- **[`class CurvesSlots(SlotsMaya)`](tentacle/tentacle/slots/maya/curves.py#L8)**

<a id="slots--maya--deform"></a>
### `slots/maya/deform.py`

- **[`class DeformSlots(SlotsMaya)`](tentacle/tentacle/slots/maya/deform.py#L8)**

<a id="slots--maya--deformation"></a>
### `slots/maya/deformation.py`

- **[`class DeformationSlots(SlotsMaya)`](tentacle/tentacle/slots/maya/deformation.py#L6)** — Slots for the Deformation panel (``deformation.ui``).
  - `DeformationSlots.tb001_init(self, widget)` — Init Curtain Generator launcher.
  - `DeformationSlots.tb001(self, widget)` — Curtain Generator — open the shared Curtain tool.

<a id="slots--maya--display"></a>
### `slots/maya/display.py`

- **[`class DisplaySlots(DisplayMixin, SlotsMaya)`](tentacle/tentacle/slots/maya/display.py#L9)**
  - `DisplaySlots.list000(self, item)` — Dispatch a Display action and report state via message_box.
  - `DisplaySlots.b000(self)` — Set Wireframe color
  - `DisplaySlots.b001(self)` — Wireframe Selected
  - `DisplaySlots.b002(self)` — Hide Selected
  - `DisplaySlots.b003(self)` — Show Selected
  - `DisplaySlots.b004(self)` — Show Geometry
  - `DisplaySlots.b005(self)` — Xray Selected.
  - `DisplaySlots.b006(self)` — Un-Xray All
  - `DisplaySlots.b007(self)` — Xray Other (uniform toggle across all non-selected shapes)
  - `DisplaySlots.b009(self)` — Toggle Material Override
  - `DisplaySlots.b011(self)` — Toggle Component ID Display
  - `DisplaySlots.b012(self)` — Wireframe Non Active (Wireframe All But The Selected Item)
  - `DisplaySlots.b013(self)` — Explode View GUI
  - `DisplaySlots.b014(self)` — Color ID GUI
  - `DisplaySlots.b021(self)` — Template Selected
  - `DisplaySlots.b022(self)` — Display UV Borders
  - `DisplaySlots.b023(self)` — Soft Edge Display
  - `DisplaySlots.b024(self)` — Display Face Normals

<a id="slots--maya--duplicate"></a>
### `slots/maya/duplicate.py`

- **[`class DuplicateSlots(DuplicateMixin, SlotsMaya)`](tentacle/tentacle/slots/maya/duplicate.py#L9)**
  - `DuplicateSlots.tb002_init(self, widget)` — Initialize Auto Instance — configure option-box menu.
  - `DuplicateSlots.tb002(self, widget)` — Auto Instance: find and convert geometrically identical meshes
  - `DuplicateSlots.tb000_init(self, widget)`
  - `DuplicateSlots.tb000(self, widget)` — Convert to Instances
  - `DuplicateSlots.tb001_init(self, widget)`
  - `DuplicateSlots.tb001(self, widget)` — Select Instanced Objects
  - `DuplicateSlots.b000(self)` — Mirror: open the Mirror tool window.
  - `DuplicateSlots.b005(self)` — Uninstance Selected Objects
  - `DuplicateSlots.b006(self)` — Duplicate Linear
  - `DuplicateSlots.b007(self)` — Duplicate Radial
  - `DuplicateSlots.b008(self)` — Duplicate Grid

<a id="slots--maya--edit"></a>
### `slots/maya/edit.py`

- **[`class EditSlots(EditMixin, SlotsMaya)`](tentacle/tentacle/slots/maya/edit.py#L9)**
  - `EditSlots.header_init(self, widget)` — Initialize header menu
  - `EditSlots.tb000_init(self, widget)` — Initialize Mesh Cleanup
  - `EditSlots.tb000(self, widget)` — Mesh Cleanup — Repair (fix) or, in Select mode, select the matched problem geometry.
  - `EditSlots.tb001_init(self, widget)` — Initialize Delete History
  - `EditSlots.tb001(self, widget)` — Delete History
  - `EditSlots.tb002(self, widget)` — Delete Selected
  - `EditSlots.tb004_init(self, widget)` — Init Lock/Unlock Nodes
  - `EditSlots.tb004(self, widget)` — Node Locking
  - `EditSlots.b_channels(self)` — Channels: open the Channels panel.
  - `EditSlots.b000(self)` — Cut On Axis: open the Cut On Axis tool (slice objects along an axis plane).
  - `EditSlots.list000_init(self, widget)` — Initialize Create Primitives list.
  - `EditSlots.list000(self, item)` — Create Primitive
  - `EditSlots.list001_init(self, widget)` — Initialize Convert list.
  - `EditSlots.list001(self, item)` — Convert: convert the selected geometry between types (NURBS / polygon / subdiv / curve, etc.).
  - `EditSlots.cmb000(self, index, widget)` — Transfer — dispatch the selected transfer operation.

<a id="slots--maya--edit_mesh"></a>
### `slots/maya/edit_mesh.py`

- **[`class EditMeshSlots(SlotsMaya)`](tentacle/tentacle/slots/maya/edit_mesh.py#L8)**

<a id="slots--maya--editors"></a>
### `slots/maya/editors.py`

- **[`class EditorsSlots(SlotsMaya)`](tentacle/tentacle/slots/maya/editors.py#L9)**
  - `EditorsSlots.list000_init(self, widget)` — Initialize the editors list (categories -> Maya editors), filtered
  - `EditorsSlots.list000(self, item)` — Open the chosen Maya editor (category headers are nav-only).
  - `EditorsSlots.b000(self)` — Attributes: open the Attribute Editor.
  - `EditorsSlots.b001(self)` — Outliner: open the Outliner window.
  - `EditorsSlots.b002(self)` — Tool: open the Tool Settings window.
  - `EditorsSlots.b003(self)` — Layers: open the Channels / Layers panel.
  - `EditorsSlots.b004(self)` — Channels: open the Channels / Layers panel.
  - `EditorsSlots.b005(self)` — Node Editor: open the Node Editor window.
  - `EditorsSlots.b006(self)` — Dependancy Graph
  - `EditorsSlots.b007(self)` — Status Line: toggle the Status Line UI.
  - `EditorsSlots.b008(self)` — Shelf: toggle the Shelf UI.
  - `EditorsSlots.b009(self)` — Time & Range
  - `EditorsSlots.b010(self)` — Script Output
  - `EditorsSlots.b011(self)` — Command Line
  - `EditorsSlots.b012(self)` — Help Line: toggle the Help Line UI.
  - `EditorsSlots.b013(self)` — Tool Box: toggle the Toolbox UI.
  - `EditorsSlots.getEditorWidget(self, name)` — Get a maya widget from a given name.

<a id="slots--maya--effects"></a>
### `slots/maya/effects.py`

- **[`class EffectsSlots(SlotsMaya)`](tentacle/tentacle/slots/maya/effects.py#L8)**

<a id="slots--maya--fields_solvers"></a>
### `slots/maya/fields_solvers.py`

- **[`class FieldsSolversSlots(SlotsMaya)`](tentacle/tentacle/slots/maya/fields_solvers.py#L8)**

<a id="slots--maya--fluids"></a>
### `slots/maya/fluids.py`

- **[`class FluidsSlots(SlotsMaya)`](tentacle/tentacle/slots/maya/fluids.py#L8)**

<a id="slots--maya--generate"></a>
### `slots/maya/generate.py`

- **[`class GenerateSlots(SlotsMaya)`](tentacle/tentacle/slots/maya/generate.py#L8)**

<a id="slots--maya--help"></a>
### `slots/maya/help.py`

- **[`class HelpSlots(SlotsMaya)`](tentacle/tentacle/slots/maya/help.py#L8)**

<a id="slots--maya--hud"></a>
### `slots/maya/hud.py`

- **[`class StatusMixin`](tentacle/tentacle/slots/maya/hud.py#L11)**
  - `StatusMixin.insert_scene_status(self, hud) -> None`
- **[`class HudSelectionMixin`](tentacle/tentacle/slots/maya/hud.py#L54)** — HUD readout of what is selected — unrelated to the package-level
  - `HudSelectionMixin.insert_selection_info(self, hud, selection) -> None`
  - `HudSelectionMixin.insert_component_info(self, hud, selection) -> None`
- **[`class WarningsMixin(HudWarningsMixin)`](tentacle/tentacle/slots/maya/hud.py#L132)** — Maya HUD warnings — the framework lives in the shared
- **[`class HudSlots(SlotsMaya, pythontk.PackageManager, StatusMixin, HudSelectionMixin, WarningsMixin)`](tentacle/tentacle/slots/maya/hud.py#L207)** — HUD Slots for Maya, providing scene and selection information.
  - `HudSlots.request_hud_build(self) -> None` — Start a new HUD build request, only the latest token will be used.
  - `HudSlots.construct_hud(self) -> None`

<a id="slots--maya--key"></a>
### `slots/maya/key.py`

- **[`class KeySlots(SlotsMaya)`](tentacle/tentacle/slots/maya/key.py#L8)**

<a id="slots--maya--lighting"></a>
### `slots/maya/lighting.py`

- **[`class LightingSlots(LightingMixin, SlotsMaya)`](tentacle/tentacle/slots/maya/lighting.py#L9)**
  - `LightingSlots.b000(self)` — Launch the HDR Manager.
  - `LightingSlots.b001(self)` — Launch the Lightmap Baker.
  - `LightingSlots.b002(self)` — Launch Light Rigs: save, swap and restore named light rigs.
  - `LightingSlots.tb000_init(self, widget)` — Lights From Geometry Init
  - `LightingSlots.tb000(self, widget)` — Create real area lights from the selected fixture geometry.

<a id="slots--maya--lighting_shading"></a>
### `slots/maya/lighting_shading.py`

- **[`class LightingShadingSlots(SlotsMaya)`](tentacle/tentacle/slots/maya/lighting_shading.py#L8)**

<a id="slots--maya--main"></a>
### `slots/maya/main.py`

- **[`class MainSlots(MainMixin, SlotsMaya)`](tentacle/tentacle/slots/maya/main.py#L11)**
  - `MainSlots.list000_init(self, widget)` — Initialize the Workspace tab.
  - `MainSlots.list000(self, item)` — Workspace tab dispatch — editing actions, recent-workspace selection,

<a id="slots--maya--mash"></a>
### `slots/maya/mash.py`

- **[`class MashSlots(SlotsMaya)`](tentacle/tentacle/slots/maya/mash.py#L8)**

<a id="slots--maya--materials"></a>
### `slots/maya/materials.py`

- **[`class MaterialsSlots(MaterialsMixin, SlotsMaya)`](tentacle/tentacle/slots/maya/materials.py#L13)**
  - `MaterialsSlots.b007(self)` — Hypershade Editor
  - `MaterialsSlots.list000_init(self, widget)` — Assign list: scene materials + 'New' + 'Random'.
  - `MaterialsSlots.list000(self, item)` — Dispatch Assign list selection.
  - `MaterialsSlots.list001(self, item)` — Dispatch Tools list selection to the matching slot method.
  - `MaterialsSlots.select_by_mat(self, shell=False, in_selection=False, get_first=False, add=False, unassigned=False)` — Select the geometry carrying the current material.
  - `MaterialsSlots.b015(self, widget)` — Delete Unused Materials
  - `MaterialsSlots.lbl004(self)` — Select and Show Attributes: Show Material Attributes in the Attribute Editor.
  - `MaterialsSlots.lbl006(self)` — Open material in editor
  - `MaterialsSlots.b004(self, widget)` — Assign Random
  - `MaterialsSlots.b008(self, widget)` — Map Packer
  - `MaterialsSlots.b009(self, widget)` — Create Game Shader
  - `MaterialsSlots.b026(self, widget)` — Arnold Preview Shader (parallel aiStandardSurface for in-Maya Arnold preview;
  - `MaterialsSlots.b027(self, widget)` — Emissive Groups
  - `MaterialsSlots.b010(self, widget)` — Texture Path Editor
  - `MaterialsSlots.b011(self, widget)` — Shader Templates
  - `MaterialsSlots.b013(self)` — Reload Textures and Reset Viewport
  - `MaterialsSlots.b016(self)` — Map Converter
  - `MaterialsSlots.b018(self, widget)` — Update Materials (Material Updater) — reprocess scene materials' textures and re-wire them.
  - `MaterialsSlots.tb001_init(self, widget)` — Get Material Info — option box.
  - `MaterialsSlots.tb001(self, widget)` — Get Material Info — render a formatted report to the viewer dialog.
  - `MaterialsSlots.tb002_init(self, widget)` — Enable Viewport Opacity — option box.
  - `MaterialsSlots.tb002(self, widget)` — Enable Viewport Opacity — wire opacity maps for the chosen scope.
  - `MaterialsSlots.b021(self, widget)` — Image to Plane
  - `MaterialsSlots.b019(self, widget)` — Marmoset Bridge
  - `MaterialsSlots.b020(self, widget)` — Substance Bridge
  - `MaterialsSlots.b022(self, widget)` — Map Compositor
  - `MaterialsSlots.b023(self, widget)` — Metashape Workflow
  - `MaterialsSlots.b024(self, widget)` — RealityCapture Workflow
  - `MaterialsSlots.b025(self, widget)` — Brush Splat Workflow

<a id="slots--maya--mesh"></a>
### `slots/maya/mesh.py`

- **[`class MeshSlots(SlotsMaya)`](tentacle/tentacle/slots/maya/mesh.py#L8)**

<a id="slots--maya--mesh_display"></a>
### `slots/maya/mesh_display.py`

- **[`class MeshDisplaySlots(SlotsMaya)`](tentacle/tentacle/slots/maya/mesh_display.py#L8)**

<a id="slots--maya--mesh_tools"></a>
### `slots/maya/mesh_tools.py`

- **[`class MeshToolsSlots(SlotsMaya)`](tentacle/tentacle/slots/maya/mesh_tools.py#L8)**

<a id="slots--maya--ncloth"></a>
### `slots/maya/ncloth.py`

- **[`class NClothSlots(SlotsMaya)`](tentacle/tentacle/slots/maya/ncloth.py#L8)**

<a id="slots--maya--nconstraint"></a>
### `slots/maya/nconstraint.py`

- **[`class NConstraintSlots(SlotsMaya)`](tentacle/tentacle/slots/maya/nconstraint.py#L8)**

<a id="slots--maya--nhair"></a>
### `slots/maya/nhair.py`

- **[`class NHairSlots(SlotsMaya)`](tentacle/tentacle/slots/maya/nhair.py#L8)**

<a id="slots--maya--nparticles"></a>
### `slots/maya/nparticles.py`

- **[`class NParticlesSlots(SlotsMaya)`](tentacle/tentacle/slots/maya/nparticles.py#L8)**

<a id="slots--maya--nurbs"></a>
### `slots/maya/nurbs.py`

- **[`class NurbsSlots(NurbsMixin, SlotsMaya)`](tentacle/tentacle/slots/maya/nurbs.py#L9)**
  - `NurbsSlots.list000(self, item)` — Dispatch a Nurbs leaf action via mel.eval (uses Maya's stored settings).
  - `NurbsSlots.b056(self)` — Image Tracer
  - `NurbsSlots.b058(self)` — Curve to Tube
  - `NurbsSlots.tb000_init(self, widget)`
  - `NurbsSlots.tb000(self, widget)` — Revolve: sweep the selected profile curve around an axis into a surface.
  - `NurbsSlots.tb001_init(self, widget)`
  - `NurbsSlots.tb001(self, widget)` — Loft: build a surface lofted across the selected profile curves.
  - `NurbsSlots.b016(self)` — Extract Curve
  - `NurbsSlots.b030(self)` — Extrude: extrude the selected NURBS curve(s) into a surface.

<a id="slots--maya--pivot"></a>
### `slots/maya/pivot.py`

- **[`class PivotSlots(PivotMixin, SlotsMaya)`](tentacle/tentacle/slots/maya/pivot.py#L9)**
  - `PivotSlots.tb000_init(self, widget)`
  - `PivotSlots.tb000(self, widget)` — Reset Pivot: reset the selected objects' pivot position and/or orientation.
  - `PivotSlots.tb001_init(self, widget)`
  - `PivotSlots.tb001(self, widget)` — Center Pivot
  - `PivotSlots.tb002_init(self, widget)`
  - `PivotSlots.tb002(self, widget)` — Transfer Pivot
  - `PivotSlots.tb003_init(self, widget)` — Initialize World-Aligned Pivot options
  - `PivotSlots.tb003(self, widget)` — World-Aligned Pivot: world-align the pivot of the selected objects or components.
  - `PivotSlots.b004(self)` — Bake Pivot: bake the manipulator pivot's position and orientation into the transform.

<a id="slots--maya--playback"></a>
### `slots/maya/playback.py`

- **[`class PlaybackSlots(SlotsMaya)`](tentacle/tentacle/slots/maya/playback.py#L8)**

<a id="slots--maya--polygons"></a>
### `slots/maya/polygons.py`

- **[`class PolygonsSlots(SlotsMaya)`](tentacle/tentacle/slots/maya/polygons.py#L9)**
  - `PolygonsSlots.header_init(self, widget)` — Initialize Header
  - `PolygonsSlots.chk008(self, state, widget)` — Divide Facet: Split U
  - `PolygonsSlots.chk009(self, state, widget)` — Divide Facet: Split V
  - `PolygonsSlots.chk010(self, state, widget)` — Divide Facet: Tris
  - `PolygonsSlots.tb000_init(self, widget)` — Initialize Merge Vertices
  - `PolygonsSlots.tb000(self, widget)` — Merge Vertices
  - `PolygonsSlots.tb002_init(self, widget)` — Initialize Separate
  - `PolygonsSlots.tb002(self, widget)` — Separate: split a combined mesh into its disconnected shells (optionally per material).
  - `PolygonsSlots.tb003_init(self, widget)` — Initialize Extrude
  - `PolygonsSlots.tb003(self, widget)` — Extrude the selected faces, edges or vertices (an object extrudes its faces).
  - `PolygonsSlots.tb004_init(self, widget)` — Initialize Combine
  - `PolygonsSlots.tb004(self, widget)` — Combine Selected Meshes.
  - `PolygonsSlots.tb005_init(self, widget)` — Initialize Detach
  - `PolygonsSlots.tb005(self, widget)` — Detach: extract the selected faces into a new object (optionally duplicated/separated).
  - `PolygonsSlots.tb006_init(self, widget)` — Initialize Inset Face Region
  - `PolygonsSlots.tb006(self, widget)` — Inset Face Region
  - `PolygonsSlots.tb007_init(self, widget)` — Initialize Divide Facet
  - `PolygonsSlots.tb007(self, widget)` — Divide Facet
  - `PolygonsSlots.tb008_init(self, widget)` — Initialize Boolean Operation
  - `PolygonsSlots.tb008(self, widget)` — Boolean Operation
  - `PolygonsSlots.tb009_init(self, widget)` — Initialize Snap Closest Verts
  - `PolygonsSlots.tb009(self, widget)` — Snap Closest Verts
  - `PolygonsSlots.b000(self)` — Circularize: reshape the selected vertices, edges, or faces into an even circle.
  - `PolygonsSlots.b001(self)` — Fill Holes: cap open holes bounded by the mesh's border edges.
  - `PolygonsSlots.b003(self)` — Symmetrize: mirror topology and edits across the active symmetry axis.
  - `PolygonsSlots.b005(self)` — Merge Vertices: Set Distance
  - `PolygonsSlots.b006(self, widget)` — Bridge: span two edge selections with new connecting faces (closes border edges).
  - `PolygonsSlots.b007(self)` — Interactive Bridge
  - `PolygonsSlots.b008(self)` — Weld Center: merge the selected vertices to their shared center point.
  - `PolygonsSlots.b009(self)` — Collapse Component: faces each to their own point, edges/verts to one center.
  - `PolygonsSlots.b011(self)` — Bevel: open the Bevel tool window.
  - `PolygonsSlots.b012(self)` — Multi-Cut Tool
  - `PolygonsSlots.b022(self)` — Attach: connect components interactively with Maya's Connect tool.
  - `PolygonsSlots.b032(self)` — Poke: add a center vertex to each selected face, fanning it into triangles.
  - `PolygonsSlots.b034(self)` — Wedge: sweep the selected faces around a chosen edge into an arc.
  - `PolygonsSlots.b038(self)` — Assign Invisible
  - `PolygonsSlots.b043(self)` — Target Weld: interactively merge one vertex onto another by dragging.
  - `PolygonsSlots.b047(self)` — Insert Edgeloop
  - `PolygonsSlots.b049(self)` — Slide Edge Tool
  - `PolygonsSlots.b051(self)` — Offset Edgeloop
  - `PolygonsSlots.b053(self)` — Edit Edge Flow

<a id="slots--maya--preferences"></a>
### `slots/maya/preferences.py`

- **[`class PreferencesSlots(PreferencesMixin, SlotsMaya)`](tentacle/tentacle/slots/maya/preferences.py#L12)**
  - `PreferencesSlots.cmb001_init(self, widget)` — Initializes the combo box with unit options.
  - `PreferencesSlots.cmb001(self, index, widget)` — Set Working Units: Linear
  - `PreferencesSlots.cmb002_init(self, widget)` — Initializes the combo box with frame rate options.
  - `PreferencesSlots.cmb002(self, index, widget)` — Set Working Units: Time
  - `PreferencesSlots.s000_init(self, widget)` — Initialize autosave max backups spinbox (widget is source of truth).
  - `PreferencesSlots.s001_init(self, widget)` — Initialize autosave interval spinbox (widget is source of truth).
  - `PreferencesSlots.b001(self)` — Color Settings
  - `PreferencesSlots.cmb003_init(self, widget)` — App-style / color selector — the Maya-side counterpart to the Blender slot's ``cmb003``.
  - `PreferencesSlots.cmb003(self, index, widget)` — Apply the selected shipped style (e.g.
  - `PreferencesSlots.b008(self)` — Hotkeys: open Maya's native Hotkey Preferences window.
  - `PreferencesSlots.b009(self)` — Plug-In Manager
  - `PreferencesSlots.b010(self)` — Settings/Preferences

<a id="slots--maya--render"></a>
### `slots/maya/render.py`

- **[`class RenderSlots(SlotsMaya)`](tentacle/tentacle/slots/maya/render.py#L8)**

<a id="slots--maya--rendering"></a>
### `slots/maya/rendering.py`

- **[`class RenderingSlots(RenderingMixin, SlotsMaya)`](tentacle/tentacle/slots/maya/rendering.py#L14)**
  - `RenderingSlots.tb000_init(self, widget)` — Export Playblast: built once, then re-run on every panel show.
  - `RenderingSlots.tb000(self, widget)` — Export Playblast
  - `RenderingSlots.tb001_init(self, widget)` — Render: camera, renderer, IPR, smart redo, key settings and presets.
  - `RenderingSlots.tb001(self, widget)` — Render: render the current frame through the selected camera and renderer.
  - `RenderingSlots.b000(self, widget)` — WebXR Preview — open the live preview panel, wired to this scene.
  - `RenderingSlots.b001(self)` — Open Render Settings Window
  - `RenderingSlots.b003(self)` — Editor: Render Setup
  - `RenderingSlots.b004(self)` — Editor: Rendering Flags

<a id="slots--maya--rigging"></a>
### `slots/maya/rigging.py`

- **[`class RiggingSlots(RiggingMixin, SlotsMaya)`](tentacle/tentacle/slots/maya/rigging.py#L12)**
  - `RiggingSlots.header_init(self, widget)` — Init Rigging Header
  - `RiggingSlots.b020(self)` — Rebind Skin Clusters
  - `RiggingSlots.cmb001_init(self, widget)` — Init Create
  - `RiggingSlots.cmb001(self, index, widget)` — Create: create a rigging utility node — joints, IK handle, lattice, or cluster.
  - `RiggingSlots.cmb002_init(self, widget)` — Init Quick Rig — our procedural rig tools plus Maya's built-in character auto-riggers.
  - `RiggingSlots.cmb002(self, index, widget)` — Quick Rig: open a procedural rig tool, or Maya's built-in Quick Rig / HumanIK.
  - `RiggingSlots.chk000(self, state, widget)` — Scale Joint
  - `RiggingSlots.chk001(self, state, widget)` — Scale IK
  - `RiggingSlots.chk002(self, state, widget)` — Scale IK/FK
  - `RiggingSlots.s000(self, value, widget)` — Scale Joint/IK/FK
  - `RiggingSlots.tb000_init(self, widget)` — Init Display Local Rotation Axes
  - `RiggingSlots.tb000(self, widget)` — Toggle Display Local Rotation Axes
  - `RiggingSlots.tb001_init(self, widget)` — Init Constraint Switch
  - `RiggingSlots.tb001(self, widget)` — Constraint Switch
  - `RiggingSlots.tb003_init(self, widget)` — Init Create Locator at Selection
  - `RiggingSlots.tb003(self, widget)` — Create Locator at Selection
  - `RiggingSlots.tb004_init(self, widget)` — Init Lock/Unlock Attributes
  - `RiggingSlots.tb004(self, widget)` — Lock/Unlock Attributes
  - `RiggingSlots.tb005_init(self, widget)` — Init Add to Skin
  - `RiggingSlots.tb005(self, widget)` — Add to Skin
  - `RiggingSlots.b004(self)` — Render Effects

<a id="slots--maya--scene"></a>
### `slots/maya/scene.py`

- **[`class SceneSlots(SceneMixin, SlotsMaya)`](tentacle/tentacle/slots/maya/scene.py#L14)**
  - `SceneSlots.list003(self, item)` — Dispatch a Tools leaf to its own slot (shared: ``SceneMixin``).
  - `SceneSlots.cmb002_init(self, widget)` — Initialize Autosave
  - `SceneSlots.cmb002(self, index, widget)` — Autosave: reopen a recent autosaved scene file.
  - `SceneSlots.list001_init(self, widget)` — Initialize Import
  - `SceneSlots.list001(self, item)` — Import: import a file, or open import / FBX / OBJ preset options.
  - `SceneSlots.list002_init(self, widget)` — Initialize Export.
  - `SceneSlots.list002(self, item)` — Export: the one-shot export actions and the Scene Exporter launcher.
  - `SceneSlots.list000_init(self, widget)` — Initialize Recent Files
  - `SceneSlots.list000(self, item)` — Recent Files
  - `SceneSlots.b001(self)` — Open Reference Manager
  - `SceneSlots.b010(self)` — Blender Bridge — send the selection to a fresh Blender (mtk.BlenderBridge).
  - `SceneSlots.b016(self)` — Unity Bridge — send the selection to a Unity project's Assets/ (mtk.UnityBridge).
  - `SceneSlots.tb003_init(self, widget)` — Initialize Export.
  - `SceneSlots.b004(self)` — Open Hierarchy Sync
  - `SceneSlots.b005(self)` — Open Naming Tool
  - `SceneSlots.b006(self)` — Scene Cleanup
  - `SceneSlots.b009(self)` — Fix OCIO
  - `SceneSlots.b011(self)` — Fix Color Spaces
  - `SceneSlots.b018(self)` — Fix Mangled Names
  - `SceneSlots.b012(self)` — Toggle Command Ports
  - `SceneSlots.b017(self)` — Scene Metadata — the tool-authored data-node channels in the shared data
  - `SceneSlots.b013(self)` — Mesh Converter (FBX -> GLB)
  - `SceneSlots.b014_init(self, widget)` — Initialize Save to Original Scene.
  - `SceneSlots.b014(self)` — Save to Original Scene.

<a id="slots--maya--select"></a>
### `slots/maya/select.py`

- **[`class SelectSlots(SlotsMaya)`](tentacle/tentacle/slots/maya/select.py#L8)**

<a id="slots--maya--selection"></a>
### `slots/maya/selection.py`

- **[`class SelectionSlots(SelectionMixin, SlotsMaya)`](tentacle/tentacle/slots/maya/selection.py#L9)**
  - `SelectionSlots.list000_init(self, widget)` — Select by Type: Hierarchical type list.
  - `SelectionSlots.list000(self, item)` — Select by Type
  - `SelectionSlots.tb004_init(self, widget)` — Select by Type settings menu.
  - `SelectionSlots.cmb002_init(self, widget)` — Rig Picking Mode: mirrors the scene, never restored (see mirror_app_state).
  - `SelectionSlots.cmb002(self, index, widget)` — Rig Picking Mode
  - `SelectionSlots.cmb001_init(self, widget)` — Reorder Selection Init
  - `SelectionSlots.cmb001(self, index, widget)` — Reorder Selection
  - `SelectionSlots.list001(self, item)` — Convert To: convert the component selection to verts, edges, faces, UVs, or shells.
  - `SelectionSlots.b002_init(self, widget)` — Selection constraint: Angle.
  - `SelectionSlots.b002(self, widget)` — Selection constraint: Angle (toggle).
  - `SelectionSlots.b003_init(self, widget)` — Selection constraint: Border.
  - `SelectionSlots.b003(self, widget)` — Selection constraint: Border (toggle).
  - `SelectionSlots.b004_init(self, widget)` — Selection constraint: Edge Loop.
  - `SelectionSlots.b004(self, widget)` — Selection constraint: Edge Loop (toggle).
  - `SelectionSlots.b005_init(self, widget)` — Selection constraint: Edge Ring.
  - `SelectionSlots.b005(self, widget)` — Selection constraint: Edge Ring (toggle).
  - `SelectionSlots.b006_init(self, widget)` — Selection constraint: Shell.
  - `SelectionSlots.b006(self, widget)` — Selection constraint: Shell (toggle).
  - `SelectionSlots.b007_init(self, widget)` — Selection constraint: UV Edge Loop.
  - `SelectionSlots.b007(self, widget)` — Selection constraint: UV Edge Loop (toggle).
  - `SelectionSlots.chk000(self, state, widget)` — Select Nth: uncheck other checkboxes
  - `SelectionSlots.chk001(self, state, widget)` — Select Nth: uncheck other checkboxes
  - `SelectionSlots.chk002(self, state, widget)` — Select Nth: uncheck other checkboxes
  - `SelectionSlots.chk005_init(self, widget)` — Create button group for radioboxes chk005, chk006, chk007
  - `SelectionSlots.chk005(self, state, widget)` — Select Style: Marquee
  - `SelectionSlots.chk006(self, state, widget)` — Select Style: Lasso
  - `SelectionSlots.chk007(self, state, widget)` — Select Style: Paint
  - `SelectionSlots.chk004(self, state, widget)` — Ignore Backfacing (Camera Based Selection)
  - `SelectionSlots.chkxxx(self, **kwargs)` — Transform Constraints: Constraint CheckBoxes
  - `SelectionSlots.tb000_init(self, widget)`
  - `SelectionSlots.tb000(self, widget)` — Select Nth: select edge loops/rings or shortest paths, stepping every Nth component.
  - `SelectionSlots.tb001_init(self, widget)`
  - `SelectionSlots.tb001(self, widget)` — Select Similar.
  - `SelectionSlots.tb002_init(self, widget)`
  - `SelectionSlots.tb002(self, widget)` — Select Island: Select Polygon Face Island
  - `SelectionSlots.tb003_init(self, widget)`
  - `SelectionSlots.tb003(self, widget)` — Select Edges By Angle
  - `SelectionSlots.b001(self)` — Toggle Selectability
  - `SelectionSlots.get_selection_tool()` *(static)* — Queries the current selection tool in Maya.
  - `SelectionSlots.set_selection_tool(tool)` *(static)* — Sets the selection tool in Maya.

<a id="slots--maya--settings"></a>
### `slots/maya/settings.py`

- **[`class SettingsSlots(SettingsMixin, SlotsMaya)`](tentacle/tentacle/slots/maya/settings.py#L13)** — Maya fork of the shared ``settings`` menu.
  - `SettingsSlots.tb001(self)` — Reload Scripts (tear down, reload the ecosystem in place, rebuild deferred).

<a id="slots--maya--skeleton"></a>
### `slots/maya/skeleton.py`

- **[`class SkeletonSlots(SlotsMaya)`](tentacle/tentacle/slots/maya/skeleton.py#L8)**

<a id="slots--maya--skin"></a>
### `slots/maya/skin.py`

- **[`class SkinSlots(SlotsMaya)`](tentacle/tentacle/slots/maya/skin.py#L8)**

<a id="slots--maya--stereo"></a>
### `slots/maya/stereo.py`

- **[`class StereoSlots(SlotsMaya)`](tentacle/tentacle/slots/maya/stereo.py#L8)**

<a id="slots--maya--subdivision"></a>
### `slots/maya/subdivision.py`

- **[`class SubdivisionSlots(SlotsMaya)`](tentacle/tentacle/slots/maya/subdivision.py#L9)**
  - `SubdivisionSlots.s000_init(self, widget)` — Division Level — reflect the selection's live preview division level.
  - `SubdivisionSlots.s001_init(self, widget)` — Adaptive Level — reflect the selection's live adaptive tessellation level.
  - `SubdivisionSlots.s000(self, value: int, widget: object) -> None` — Division Level (smooth mesh preview divisions).
  - `SubdivisionSlots.s001(self, value: int, widget: object) -> None` — Adaptive Level (OpenSubdiv adaptive tessellation).
  - `SubdivisionSlots.b000(self)` — Quadrangulate
  - `SubdivisionSlots.b001(self)` — Triangulate: split the selected faces into triangles.
  - `SubdivisionSlots.b005(self)` — Reduce: halve the polygon count while preserving border, hard, crease, and UV edges.
  - `SubdivisionSlots.tb000_init(self, widget)` — Initialize Decimate
  - `SubdivisionSlots.tb000(self, widget)` — Decimate: reduce face count by quadric-error percentage or coplanar-face dissolve.
  - `SubdivisionSlots.b008(self)` — Add Divisions - Subdivide Mesh
  - `SubdivisionSlots.b011(self)` — Apply Smooth Preview
  - `SubdivisionSlots.b028(self)` — Quad Draw: enter Maya's Quad Draw retopology tool.
  - `SubdivisionSlots.smoothProxy()` *(static)* — Subdiv Proxy

<a id="slots--maya--surfaces"></a>
### `slots/maya/surfaces.py`

- **[`class SurfacesSlots(SlotsMaya)`](tentacle/tentacle/slots/maya/surfaces.py#L8)**

<a id="slots--maya--symmetry"></a>
### `slots/maya/symmetry.py`

- **[`class SymmetrySlots(SlotsMaya)`](tentacle/tentacle/slots/maya/symmetry.py#L7)**
  - `SymmetrySlots.chk000_init(self, widget)` — Set initial symmetry state
  - `SymmetrySlots.chk000(self, state, widget)` — Symmetry X: toggle modeling symmetry across the X axis.
  - `SymmetrySlots.chk001(self, state, widget)` — Symmetry Y: toggle modeling symmetry across the Y axis.
  - `SymmetrySlots.chk002(self, state, widget)` — Symmetry Z: toggle modeling symmetry across the Z axis.
  - `SymmetrySlots.chk004(self, state, widget)` — Symmetry: Object space (radio partner of Topo;
  - `SymmetrySlots.chk005_init(self, widget)` — Set symmetry reference space
  - `SymmetrySlots.chk005(self, state, widget)` — Symmetry: Topo

<a id="slots--maya--texturing"></a>
### `slots/maya/texturing.py`

- **[`class TexturingSlots(SlotsMaya)`](tentacle/tentacle/slots/maya/texturing.py#L8)**

<a id="slots--maya--toon"></a>
### `slots/maya/toon.py`

- **[`class ToonSlots(SlotsMaya)`](tentacle/tentacle/slots/maya/toon.py#L8)**

<a id="slots--maya--transform"></a>
### `slots/maya/transform.py`

- **[`class TransformSlots(TransformMixin, SlotsMaya)`](tentacle/tentacle/slots/maya/transform.py#L9)**
  - `TransformSlots.header_init(self, widget)` — Header Init
  - `TransformSlots.cmb002_init(self, widget)` — Align To Init
  - `TransformSlots.cmb002(self, index, widget)` — Align To: snap/align objects point-to-point, multi-point, or along a curve.
  - `TransformSlots.tb000_init(self, widget)` — Drop To Grid Init
  - `TransformSlots.tb000(self, widget)` — Drop To Grid
  - `TransformSlots.tb001(self, widget)` — Scale Connected Edges
  - `TransformSlots.tb002_init(self, widget)` — Freeze Transformations Init
  - `TransformSlots.tb002(self, widget)` — Freeze Transformations
  - `TransformSlots.tb003_init(self, widget)` — Constraints Init
  - `TransformSlots.tb004_init(self, widget)` — Snap Init
  - `TransformSlots.tb005_init(self, widget)` — Move To Init
  - `TransformSlots.tb005(self, widget)` — Move To: move the selected objects onto the last-selected object (by a chosen pivot).
  - `TransformSlots.chk021(self, state, widget)` — Transform Tool Snap Settings: Move
  - `TransformSlots.chk022(self, state, widget)` — Transform Tool Snap Settings: Scale
  - `TransformSlots.chk023(self, state, widget)` — Transform Tool Snap Settings: Rotate
  - `TransformSlots.chk024(self, state, widget)` — Transform Constraints: Edge
  - `TransformSlots.chk025(self, state, widget)` — Transform Contraints: Surface
  - `TransformSlots.chk026(self, state, widget)` — Transform Constraints: Make Live
  - `TransformSlots.s021(self, value, widget)` — Transform Tool Snap Settings: Spinboxes
  - `TransformSlots.s022(self, value, widget)` — Transform Tool Snap Settings: Spinboxes
  - `TransformSlots.s023(self, value, widget)` — Transform Tool Snap Settings: Spinboxes
  - `TransformSlots.b_snap_ts(self)` — Snap Toolset
  - `TransformSlots.b001(self)` — Match Scale: scale the selected object(s) to match the first-selected object's size.
  - `TransformSlots.b002_init(self, widget)` — Un-Freeze Transforms Init
  - `TransformSlots.b_restore_axes(self)` — Restore Authored Axes - point the manipulator at the pre-freeze frame.
  - `TransformSlots.b002(self, widget)` — Un-Freeze Transforms
  - `TransformSlots.setTransformSnap(self, ctx, state)` — Set the transform tool's move, rotate, and scale snap states.

<a id="slots--maya--utilities"></a>
### `slots/maya/utilities.py`

- **[`class UtilitiesSlots(SlotsMaya)`](tentacle/tentacle/slots/maya/utilities.py#L7)**
  - `UtilitiesSlots.b000(self)` — Measure: create a distance-measure tool between two points.
  - `UtilitiesSlots.b001(self)` — Annotation: create an annotation (text label) node.
  - `UtilitiesSlots.b002(self)` — Calculator: open the calculator tool.
  - `UtilitiesSlots.b003(self)` — Grease Pencil

<a id="slots--maya--uv"></a>
### `slots/maya/uv.py`

- **[`class UvSlots(UvMixin, SlotsMaya)`](tentacle/tentacle/slots/maya/uv.py#L12)**
  - `UvSlots.header_init(self, widget)` — Initialize UV Menu Header
  - `UvSlots.tb000_init(self, widget)` — Initialize UV packing tool interface.
  - `UvSlots.tb000(self, widget)` — Pack UVs with specified settings.
  - `UvSlots.tb001_init(self, widget)` — Initialize Auto Unwrap.
  - `UvSlots.tb001(self, widget)` — Auto Unwrap: automatically unwrap UVs for the selected objects.
  - `UvSlots.tb004_init(self, widget)` — Initialize Unfold UV
  - `UvSlots.tb004(self, widget)` — Unfold: relax/unfold the selected UVs to reduce stretch and distortion.
  - `UvSlots.tb007_init(self, widget)` — Initialize Cleanup UV Sets
  - `UvSlots.tb007(self, widget)` — Cleanup UV Sets
  - `UvSlots.tb009_init(self, widget)` — Initialize Cut Cylinder.
  - `UvSlots.tb009(self, widget)` — Cut Cylinder
  - `UvSlots.b003(self)` — Get texel density.
  - `UvSlots.b004(self)` — Set Texel Density
  - `UvSlots.b005(self)` — Cut UVs: split the UV shell along the selected edges.
  - `UvSlots.b011(self)` — Sew UVs: stitch the selected UV edges back together.
  - `UvSlots.b021(self, widget)` — Unfold and Pack UVs
  - `UvSlots.tb022_init(self, widget)` — Initialize Cut Hard Edges option menu.
  - `UvSlots.tb022(self, widget)` — Cut UV hard edges (always), optionally also UV borders and auto-detected seams.
  - `UvSlots.b029(self, widget)` — Pin / Unpin selected UVs (dual-state toggle).
  - `UvSlots.b030(self, widget)` — Stack / Unstack shells (dual-state toggle).
  - `UvSlots.b031(self)` — Open UV Editor
  - `UvSlots.b032(self)` — RizomUV Bridge
  - `UvSlots.b033(self)` — Open the Shell Xform panel (move / flip / rotate / align / orient / distribute).

<a id="slots--maya--visualize"></a>
### `slots/maya/visualize.py`

- **[`class VisualizeSlots(SlotsMaya)`](tentacle/tentacle/slots/maya/visualize.py#L8)**

<a id="slots--maya--windows"></a>
### `slots/maya/windows.py`

- **[`class WindowsSlots(SlotsMaya)`](tentacle/tentacle/slots/maya/windows.py#L8)**

<a id="slots--normals"></a>
### `slots/normals.py`

Normals: one Slots class for both hosts.

- **[`class NormalsSlots(Slots)`](tentacle/tentacle/slots/normals.py#L13)**
  - `NormalsSlots.tb001_init(self, widget)` — Initialize Set Normals By Angle
  - `NormalsSlots.tb001(self, widget)` — Set Normals By Angle
  - `NormalsSlots.tb004_init(self, widget)` — Initialize Average Normals
  - `NormalsSlots.tb004(self, widget)` — Average Normals
  - `NormalsSlots.b000(self)` — Soften Edge Normals
  - `NormalsSlots.b001(self)` — Harden Edge Normals
  - `NormalsSlots.b002(self)` — Transfer Normals: from the first selected (Maya) or active (Blender)
  - `NormalsSlots.b004(self)` — Toggle lock/unlock normals.
  - `NormalsSlots.b006(self)` — Set To Face: vertex normals follow their faces (faceted shading).
  - `NormalsSlots.tb010_init(self, widget)` — Initialize Reverse Normals: Maya's five ``polyNormal`` modes, in both
  - `NormalsSlots.tb010(self, widget)` — Reverse Normals

<a id="slots--tools--_blendshape_animator--sort_item"></a>
### `slots/tools/_blendshape_animator/sort_item.py`

A tween-tree row that sorts its numeric columns by number.

- **[`class NumericSortItem(QtWidgets.QTreeWidgetItem)`](tentacle/tentacle/slots/tools/_blendshape_animator/sort_item.py#L8)** — A tree row that sorts the Weight and Frame columns by number.

<a id="slots--tools--_shot_manifest--controller"></a>
### `slots/tools/_shot_manifest/controller.py`

The Shot Manifest panel's controller: its state, the steps the table shows,

- **[`class ShotManifestController(ManifestTableMixin, RangeColumnMixin, StoreFollowMixin, ManifestSourceMixin, MappingPickerMixin, RowMenusMixin, HeaderMenuMixin, ViewCombosMixin, ExportPreviewMixin, pythontk.LoggingMixin)`](tentacle/tentacle/slots/tools/_shot_manifest/controller.py#L40)** — Business logic for the Shot Manifest UI (see the module docstring).
  - `ShotManifestController.build(self) -> None` — Build or update shots in the store from loaded steps.
  - `ShotManifestController.assess(self, skip_key_check: bool = False, note: str = '') -> None` — Compare the steps against the scene's shots and colour the tree.

<a id="slots--tools--_shot_manifest--export_preview"></a>
### `slots/tools/_shot_manifest/export_preview.py`

The Shot Manifest's Export button (beside Assess): a live preview of the

- **[`class ExportPreviewMixin`](tentacle/tentacle/slots/tools/_shot_manifest/export_preview.py#L23)** — The Export button's preview, mixed into ``ShotManifestController``.
  - `ExportPreviewMixin.export(self) -> None` — Open the preview of the export (or bring the open one up): its

<a id="slots--tools--_shot_manifest--header_menu"></a>
### `slots/tools/_shot_manifest/header_menu.py`

The Shot Manifest's header menu: Long Names, Local Edits' Edits mode and

- **[`class HeaderMenuMixin`](tentacle/tentacle/slots/tools/_shot_manifest/header_menu.py#L16)** — The header menu, mixed into ``ShotManifestController``.

<a id="slots--tools--_shot_manifest--manifest_data"></a>
### `slots/tools/_shot_manifest/manifest_data.py`

Constants, column layout, and pure helper functions for the Shot Manifest UI.

- [`SETTINGS_NS`](tentacle/tentacle/slots/tools/_shot_manifest/manifest_data.py#L18) — constant
- [`HEADERS`](tentacle/tentacle/slots/tools/_shot_manifest/manifest_data.py#L21) — constant
- [`COL_STEP`](tentacle/tentacle/slots/tools/_shot_manifest/manifest_data.py#L24) — constant
- [`COL_SECTION`](tentacle/tentacle/slots/tools/_shot_manifest/manifest_data.py#L25) — constant
- [`COL_DESC`](tentacle/tentacle/slots/tools/_shot_manifest/manifest_data.py#L26) — constant
- [`COL_BEHAVIORS`](tentacle/tentacle/slots/tools/_shot_manifest/manifest_data.py#L27) — constant
- [`COL_START`](tentacle/tentacle/slots/tools/_shot_manifest/manifest_data.py#L28) — constant
- [`COL_END`](tentacle/tentacle/slots/tools/_shot_manifest/manifest_data.py#L29) — constant
- [`STEP_ICON_COLOR`](tentacle/tentacle/slots/tools/_shot_manifest/manifest_data.py#L31) — constant
- [`PASTEL_STATUS`](tentacle/tentacle/slots/tools/_shot_manifest/manifest_data.py#L35) — constant
- [`ERROR_COLOR`](tentacle/tentacle/slots/tools/_shot_manifest/manifest_data.py#L38) — constant
- **[`class ManifestData`](tentacle/tentacle/slots/tools/_shot_manifest/manifest_data.py#L41)** — ManifestData — module namespace.
  - `ManifestData.level(status: str) -> str` *(static)* — *status*'s severity (``SHOT_STATUS_LEVELS``);
  - `ManifestData.status_color(status: str) -> Optional[str]` *(static)* — *status*'s colour in this panel's palette, or ``None`` for none.
  - `ManifestData.worst(statuses: Iterable[str]) -> Optional[str]` *(static)* — The status of *statuses* at the worst severity (the first of
  - `ManifestData.glyph_html(status: str) -> str` *(static)* — *status*'s glyph in its colour, as rich text (``""``: no severity).
  - `ManifestData.issues_html(issues: Iterable[Tuple[str, str]]) -> str` *(static)* — ``(status, text)`` *issues* as rich text, a line each: its glyph,
  - `ManifestData.fmt_behavior(name: str) -> str` *(static)* — ``'fade_in'`` → ``'Fade In'`` (``Behaviors.label``: the marker
  - `ManifestData.format_behavior_html(behaviors, broken=(), status_color=None, stale=(), disabled=(), marked=()) -> str` *(static)* — Return rich-text HTML for a list of behavior names.

<a id="slots--tools--_shot_manifest--manifest_editor"></a>
### `slots/tools/_shot_manifest/manifest_editor.py`

Local Edits for the Shot Manifest panel: change the table, never the sheet.

- **[`class ManifestEditor`](tentacle/tentacle/slots/tools/_shot_manifest/manifest_editor.py#L45)** — One panel's Local Edits: its edit layer, its cell editors, and the
  - `ManifestEditor.enabled(self) -> bool` *(property)* — Whether the edits are in force -- applied and editable: always,
  - `ManifestEditor.add_header_options(self, menu) -> None` — Add the Local Edits row to *menu*: the Edits combo
  - `ManifestEditor.edits_mode(self) -> str` *(property)* — The Edits mode in force: ``"keep"``, ``"rebuild"`` or ``"compare"``.
  - `ManifestEditor.view_original(self, on: bool = True) -> None` — Show the sheet as delivered (*on*), or the manifest with its edits.
  - `ManifestEditor.refuse_viewing(self, to: str = 'edit') -> bool` — Say so and return ``True`` while the original sheet is viewed:
  - `ManifestEditor.reset(self, confirm: bool = True) -> None` — Drop every edit of the current source, after asking.
  - `ManifestEditor.source_key(self) -> str` *(property)* — The source the edits belong to: the sheet's path, or ``""`` for
  - `ManifestEditor.load(self) -> None` — Read the current source's edits from the scene -- a sheet moved
  - `ManifestEditor.save(self) -> None` — Write the current source's edits to the scene, under the sheet's
  - `ManifestEditor.apply(self, steps: List[ptk.BuilderStep]) -> List[ptk.BuilderStep]` — *steps* with the edits applied -- as delivered while the original
  - `ManifestEditor.stale(self) -> List[str]` — The edits the loaded sheet gives no place to (``ManifestEdits.stale``).
  - `ManifestEditor.refresh(self) -> None` — Re-apply the edits to the loaded steps and redraw the table.
  - `ManifestEditor.refuse_locked(self, step) -> bool` — Say so and return ``True`` when *step* is locked (:meth:`_locked`).
  - `ManifestEditor.begin_edit(self, item, column: int) -> bool` — Open an editor on a step's name or description, or an object's
  - `ManifestEditor.commit_edit(self, item, column: int) -> bool` — Record the edit a cell editor committed;
  - `ManifestEditor.set_behaviors(self, step_id: str, obj, behaviors: List[str]) -> bool` — Record *obj*'s ticked *behaviors* in step *step_id*;
  - `ManifestEditor.add_menu_actions(self, menu, item, selected: List[str] = ()) -> None` — Add Local Edits' actions for the row at *item* (``None``: empty
  - `ManifestEditor.add_step(self, after: str) -> str` — Add a step after step *after* (``""``: at the top) and open its
  - `ManifestEditor.add_shot(self, shot, after: str) -> Optional[str]` — Take a shot no step pairs with into the manifest: a step of its own
  - `ManifestEditor.remove_step(self, step) -> None` — Remove an added step;
  - `ManifestEditor.hide_steps(self, step_ids: List[str], hidden: bool = True) -> None` — Hide (or show) steps.
  - `ManifestEditor.unlocked_hidden_objects(self) -> List[Tuple[str, str]]` — The hidden objects :meth:`show_hidden_objects` shows, as
  - `ManifestEditor.show_hidden_objects(self) -> None` — Show every object the edits hide, wherever it sits -- but in a
  - `ManifestEditor.hide_object(self, home: str, sheet_name: str, hidden: bool = True) -> None` — Hide (or show) an object: a hidden one leaves its step, and Build
  - `ManifestEditor.move_object(self, step, obj, target) -> None` — Move *obj* from *step* to *target* (to the end of its objects).
  - `ManifestEditor.rename_all(self, name: str, new: Optional[str] = None) -> int` — Point every step listing *name* at *new* (asked for when
  - `ManifestEditor.revert_step(self, step) -> None` — Drop *step*'s own edits (name, description);
  - `ManifestEditor.revert_object(self, home: str, sheet_name: str, name: str = '') -> None` — Drop an object's edits: the sheet's name, step and behaviors.
  - `ManifestEditor.decorate(self) -> None` — Mark the edited cells -- italic, the sheet's value in the tooltip --

<a id="slots--tools--_shot_manifest--manifest_source"></a>
### `slots/tools/_shot_manifest/manifest_source.py`

Where the Shot Manifest's steps come from: a build sheet (a CSV path or link,

- **[`class ManifestSourceMixin`](tentacle/tentacle/slots/tools/_shot_manifest/manifest_source.py#L21)** — The panel's sources, mixed into ``ShotManifestController``.
  - `ManifestSourceMixin.detect(self, gap: Optional[float] = None) -> None` — Detect animation regions in the scene and populate the table.

<a id="slots--tools--_shot_manifest--mapping_picker"></a>
### `slots/tools/_shot_manifest/mapping_picker.py`

The Shot Manifest's mapping template: its own popup on the build sheet

- **[`class MappingPickerMixin`](tentacle/tentacle/slots/tools/_shot_manifest/mapping_picker.py#L19)** — The mapping template, mixed into ``ShotManifestController``.

<a id="slots--tools--_shot_manifest--range_column"></a>
### `slots/tools/_shot_manifest/range_column.py`

The Shot Manifest table's Start / End column: what a step's range is

- **[`class RangeColumnMixin`](tentacle/tentacle/slots/tools/_shot_manifest/range_column.py#L22)** — The Start / End column, mixed into ``ShotManifestController``.

<a id="slots--tools--_shot_manifest--row_menus"></a>
### `slots/tools/_shot_manifest/row_menus.py`

The Shot Manifest rows' context menus and what they do: a step row's (colour

- **[`class RowMenusMixin`](tentacle/tentacle/slots/tools/_shot_manifest/row_menus.py#L21)** — The rows' context menus, mixed into ``ShotManifestController``.

<a id="slots--tools--_shot_manifest--store_follow"></a>
### `slots/tools/_shot_manifest/store_follow.py`

The Shot Manifest panel following the scene's store: its events (a shot

- **[`class StoreFollowMixin`](tentacle/tentacle/slots/tools/_shot_manifest/store_follow.py#L27)** — Store events and scene swaps, mixed into ``ShotManifestController``.
  - `StoreFollowMixin.remove_callbacks(self) -> None` — Remove the ShotStore listener and the invalidation subscription,

<a id="slots--tools--_shot_manifest--table_presenter"></a>
### `slots/tools/_shot_manifest/table_presenter.py`

The Shot Manifest tree's rows: populating them (``ShotPairing.rows``: steps,

- **[`class ManifestTableMixin`](tentacle/tentacle/slots/tools/_shot_manifest/table_presenter.py#L49)** — Presentation methods for the manifest tree widget.
  - `ManifestTableMixin.expand_missing(self) -> None` — Expand the step rows the shown assessment found something in
  - `ManifestTableMixin.expand_extra(self) -> None` — Expand the step rows holding an object the step does not list

<a id="slots--tools--_shot_manifest--view_combos"></a>
### `slots/tools/_shot_manifest/view_combos.py`

The Shot Manifest's view row, above the table: Select, Expand, Collapse,

- **[`class ViewCombosMixin`](tentacle/tentacle/slots/tools/_shot_manifest/view_combos.py#L25)** — The view row, mixed into ``ShotManifestController``.

<a id="slots--tools--_texture_combine--transfer_mode"></a>
### `slots/tools/_texture_combine/transfer_mode.py`

The Texture Combine panel's Transfer mode: UVs or textures, source -> targets.

- **[`class TransferMode`](tentacle/tentacle/slots/tools/_texture_combine/transfer_mode.py#L30)** — Transfer mode's decisions and its run, over the panel's widgets.
  - `TransferMode.ui(self)` *(property)*
  - `TransferMode.tk(self)` *(property)* — The host toolkit (the panel's ``Slots.tk``).
  - `TransferMode.terms(self)` *(property)* — The host's words for its selection convention and UV channels.
  - `TransferMode.init_transfer(self, widget) -> None`
  - `TransferMode.init_source(self, widget) -> None`
  - `TransferMode.init_targets(self, widget) -> None`
  - `TransferMode.init_resolution(self, widget) -> None`
  - `TransferMode.init_uv_sets(self, src, dst) -> None`
  - `TransferMode.init_lightmaps(self, widget) -> None`
  - `TransferMode.source_tooltip(self) -> str` — Live tooltip for the Store Source Meshes icon -- what is stored NOW.
  - `TransferMode.capture_source(self) -> None`
  - `TransferMode.select_source(self) -> None` — Select the stored source meshes -- the capture, made visible.
  - `TransferMode.clear_source(self) -> None`
  - `TransferMode.passes(cls, source_mode, transfer_mode) -> Tuple[bool, bool]` *(class)* — ``(do_uvs, do_textures)`` for a Source / Transfer pair (Auto unresolved
  - `TransferMode.resolve_auto(self, source_meshes, has_lightmap=None) -> str` — Auto's run-time pick: Textures once any source material carries a map
  - `TransferMode.source_note(self, mode) -> str`
  - `TransferMode.auto_note(self, auto, do_textures, source_mode=None, lightmaps=False) -> str`
  - `TransferMode.pair(self, targets, sources, do_uvs)` — ``(pairs, error)`` for mesh sources (Stored / Last).
  - `TransferMode.gate(self, mode, scope, source, targets, do_uvs, do_textures, notes=('', ''))` — ``(pairs, targets, others, refusal)`` -- the run's refusals and pairs.
  - `TransferMode.lightmap_probe(self)`
  - `TransferMode.sync(self) -> None` — Grey every row the current Source / Transfer pair makes meaningless.
  - `TransferMode.run(self) -> None` — Transfer UVs OR textures -- one pass per run, one undo step.
  - `TransferMode.derived_name(self, source, targets) -> str` — A blank Output Name: the source's common name (else the targets').
  - `TransferMode.texture_pass(self, targets, source) -> str` — The texture pass (and, with Include Lightmaps, the lightmap pass).
  - `TransferMode.read_files(self, targets) -> set` — Path keys of the maps the materials *targets* wear read now.
  - `TransferMode.overwrite_note(cls, before, results, warnings) -> str` *(class)* — Overwrite target's report: the files rewritten where they are (the
  - `TransferMode.lightmap_pass(self, targets, source, out_name) -> Tuple[str, bool]`

<a id="slots--tools--articulated_rig"></a>
### `slots/tools/articulated_rig.py`

Articulated Rig: rig a prop of rigid parts on hinges, swivels, balls and

- **[`class ArticulatedRigSlots(Slots, pythontk.LoggingMixin)`](tentacle/tentacle/slots/tools/articulated_rig.py#L38)** — Slots for the Articulated Rig panel.
  - `ArticulatedRigSlots.header_init(self, widget)`
  - `ArticulatedRigSlots.btn_ik_fk_init(self, widget)` — Switch IK / FK's option box: put the end control back on the end
  - `ArticulatedRigSlots.parse_limits(text: str, channels: Sequence[str]) -> Dict[str, Tuple[Optional[float], Optional[float]]]` *(static)* — The limits typed into a Limits cell (``ptk.ArticulationPlan.
  - `ArticulatedRigSlots.refresh_table(self)`
  - `ArticulatedRigSlots.btn_analyze(self)`
  - `ArticulatedRigSlots.btn_build(self)`
  - `ArticulatedRigSlots.btn_grab(self)`
  - `ArticulatedRigSlots.btn_ik_fk(self)`
  - `ArticulatedRigSlots.match_end_control(self)`
  - `ArticulatedRigSlots.btn_rest(self)`
  - `ArticulatedRigSlots.btn_insert(self)`
  - `ArticulatedRigSlots.btn_fold(self)`
  - `ArticulatedRigSlots.btn_limits_from_pose(self)`
  - `ArticulatedRigSlots.btn_clear_limits(self)`
  - `ArticulatedRigSlots.btn_rebuild(self)`
  - `ArticulatedRigSlots.btn_remove(self)`

<a id="slots--tools--audio_clips"></a>
### `slots/tools/audio_clips.py`

Audio Clips: the scene's audio files, placed on the timeline.

- **[`class AudioClipsSlots(Slots)`](tentacle/tentacle/slots/tools/audio_clips.py#L28)** — Switchboard slots for the ``audio_clips.ui`` panel.
  - `AudioClipsSlots.noun(self) -> str` *(property)* — One entry, capitalized: ``"Track"`` (Maya) or ``"Clip"`` (Blender).
  - `AudioClipsSlots.header_init(self, widget) -> None` — The header menu: import, export and inspect options;
  - `AudioClipsSlots.btn_export(self) -> None` — Export the audio in the header's Export mode (Maya).
  - `AudioClipsSlots.btn_channels(self) -> None` — Open the Channels panel on the tracks' carrier (Maya).
  - `AudioClipsSlots.cmb000_init(self, widget) -> None` — The list's option box: add, rename, replace and remove.
  - `AudioClipsSlots.cmb000(self, index, widget=None) -> None` — A pick: Maya puts the track's sound on the Time Slider.
  - `AudioClipsSlots.select_track(self, name: str) -> bool` — Show the track or clip answering to *name* -- the Shot Manifest's
  - `AudioClipsSlots.btn_add_tracks(self) -> None` — Browse for audio files and add them.
  - `AudioClipsSlots.btn_rename_track(self) -> None` — Rename the selected track or clip.
  - `AudioClipsSlots.btn_replace_track(self) -> None` — Point the selected track or clip at another audio file.
  - `AudioClipsSlots.btn_remove_selected(self) -> None` — Delete the selected track or clip.
  - `AudioClipsSlots.btn_cleanup_unused(self) -> None` — Delete every track that holds no key (Maya).
  - `AudioClipsSlots.btn_remove_audio(self) -> None` — Delete every track or clip in the scene.
  - `AudioClipsSlots.tb001_init(self, widget) -> None` — The place action's label, and its option box.
  - `AudioClipsSlots.tb001(self, widget=None) -> None` — Place the selected track or clip at the playhead (Maya: key an audio
  - `AudioClipsSlots.btn_select_carrier(self) -> None` — Show where the audio lives (Maya: the carrier node;
  - `AudioClipsSlots.btn_sync_audio(self) -> None` — Rebuild the sound nodes and the composite from the keys (Maya).
  - `AudioClipsSlots.s000_init(self, widget) -> None`
  - `AudioClipsSlots.s001_init(self, widget) -> None`
  - `AudioClipsSlots.b003_init(self, widget) -> None`
  - `AudioClipsSlots.b003(self) -> None` — Apply Trim: the Start/End frames off the selected clip's ends.
  - `AudioClipsSlots.b004_init(self, widget) -> None` — Sync Scene Range: its fit mode in the option box.
  - `AudioClipsSlots.b004(self, widget=None) -> None` — Fit the scene frame range to the clips.

<a id="slots--tools--bevel"></a>
### `slots/tools/bevel.py`

Bevel: chamfer the selected polygon edges, with a live preview.

- **[`class BevelSlots(Slots)`](tentacle/tentacle/slots/tools/bevel.py#L12)**
  - `BevelSlots.header_init(self, widget)` — Configure header help text.
  - `BevelSlots.perform_operation(self, objects, contract=None)` — Bevel *objects* (Maya's Preview passes its cleanup *contract*).

<a id="slots--tools--blendshape_animator"></a>
### `slots/tools/blendshape_animator.py`

Blendshape Animator: build a morph between two meshes, add in-between

- [`COL_NAME`](tentacle/tentacle/slots/tools/blendshape_animator.py#L21) — constant
- [`COL_WEIGHT`](tentacle/tentacle/slots/tools/blendshape_animator.py#L22) — constant
- [`COL_FRAME`](tentacle/tentacle/slots/tools/blendshape_animator.py#L23) — constant
- [`COL_TOPOLOGY`](tentacle/tentacle/slots/tools/blendshape_animator.py#L24) — constant
- [`COL_STATUS`](tentacle/tentacle/slots/tools/blendshape_animator.py#L25) — constant
- [`MODE_WEIGHT`](tentacle/tentacle/slots/tools/blendshape_animator.py#L28) — constant
- [`MODE_FRAME`](tentacle/tentacle/slots/tools/blendshape_animator.py#L29) — constant
- [`STATUS_KEYS`](tentacle/tentacle/slots/tools/blendshape_animator.py#L32) — constant
- **[`class BlendshapeAnimatorSlots(Slots)`](tentacle/tentacle/slots/tools/blendshape_animator.py#L39)**
  - `BlendshapeAnimatorSlots.header_init(self, widget) -> None` — Configure header buttons and help.
  - `BlendshapeAnimatorSlots.b000_init(self, widget) -> None` — Create Setup — the option box offers the other ways in.
  - `BlendshapeAnimatorSlots.b000(self, widget) -> None` — Create Setup from the two selected meshes.
  - `BlendshapeAnimatorSlots.cmb000_init(self, widget) -> None` — Populate the edit-mode combo, and say which input each mode uses.
  - `BlendshapeAnimatorSlots.le000_init(self, widget) -> None` — Name field — optional, so an empty name is a real choice.
  - `BlendshapeAnimatorSlots.le001_init(self, widget) -> None` — CSV weights field — the option box offers preset lists.
  - `BlendshapeAnimatorSlots.b001_init(self, widget) -> None` — Add Tweens — the option box holds the count and the group / prefix.
  - `BlendshapeAnimatorSlots.b001(self, widget) -> None` — Add Tweens — by weight or by frame, as the edit-mode combo says (one
  - `BlendshapeAnimatorSlots.b003(self, widget) -> None` — Diagnose Topology.
  - `BlendshapeAnimatorSlots.b004_init(self, widget) -> None` — Cleanup Topology Mismatches — the option box holds its two flags.
  - `BlendshapeAnimatorSlots.b004(self, widget) -> None` — Clean up tweens whose topology doesn't match the base mesh.
  - `BlendshapeAnimatorSlots.b005(self, widget) -> None` — Recover Animation.
  - `BlendshapeAnimatorSlots.b006_init(self, widget) -> None` — Apply All Edits — the option box holds its two flags.
  - `BlendshapeAnimatorSlots.b006(self, widget) -> None` — Apply All Edits — every tween of the setup, with the option box's flags.
  - `BlendshapeAnimatorSlots.b007(self, widget) -> None` — Remove Target Mesh.
  - `BlendshapeAnimatorSlots.b008_init(self, widget) -> None` — Finalize for Export — the option box holds its four flags.
  - `BlendshapeAnimatorSlots.b008(self, widget) -> None` — Finalize the setup for export: apply, clean up, hide the source.

<a id="slots--tools--bridge"></a>
### `slots/tools/bridge.py`

Bridge: connect two open edge loops with new polygon faces, with a live preview.

- **[`class BridgeSlots(Slots)`](tentacle/tentacle/slots/tools/bridge.py#L14)**
  - `BridgeSlots.header_init(self, widget)` — Configure header help text.
  - `BridgeSlots.perform_operation(self, objects, contract=None)` — Bridge *objects* (Maya's Preview passes its cleanup *contract*).

<a id="slots--tools--calculator"></a>
### `slots/tools/calculator.py`

Calculator: expressions, length units, and the scene's frame-rate helpers.

- **[`class CalculatorSlots(Slots)`](tentacle/tentacle/slots/tools/calculator.py#L13)**
  - `CalculatorSlots.header_init(self, widget)` — Configure header help text.
  - `CalculatorSlots.on_input(self, text)`
  - `CalculatorSlots.on_clear(self)`
  - `CalculatorSlots.on_backspace(self)`
  - `CalculatorSlots.on_equal(self)`
  - `CalculatorSlots.on_convert_units(self)`
  - `CalculatorSlots.get_fps(self)`
  - `CalculatorSlots.get_current_time(self)`
  - `CalculatorSlots.frames_to_sec(self)`
  - `CalculatorSlots.sec_to_frames(self)`

<a id="slots--tools--color_id"></a>
### `slots/tools/color_id.py`

Color ID: color-code objects across channels from a swatch palette.

- **[`class ColorIdSlots(Slots)`](tentacle/tentacle/slots/tools/color_id.py#L15)**
  - `ColorIdSlots.header_init(self, widget)` — Configure header help text and preset combobox.
  - `ColorIdSlots.selected_button(self)` *(property)* — The checked swatch in the palette group, or None.
  - `ColorIdSlots.target_color(self)` *(property)* — The active swatch's color as 0-1 ``(r, g, b)``, or None without one.
  - `ColorIdSlots.b000(self) -> None` — Reset: clear the ENABLED channels on the selection (Ctrl+click: every
  - `ColorIdSlots.b001(self) -> None` — Set Color: apply the active color to the selection on the enabled channels.
  - `ColorIdSlots.b002(self) -> None` — Select By Color: select the objects carrying the active color on the
  - `ColorIdSlots.b003(self) -> None` — Get Color: read the selected object's color on the enabled channels into

<a id="slots--tools--curtain"></a>
### `slots/tools/curtain.py`

Curtain: drape a pleated, gravity-sagged cloth curtain from a rail, with a

- **[`class CurtainSlots(Slots)`](tentacle/tentacle/slots/tools/curtain.py#L19)**
  - `CurtainSlots.header_init(self, widget)` — Configure header help text (the preset combo lives in the panel).
  - `CurtainSlots.cmb000_init(self, widget)` — Wire the in-panel preset selector: the host's shipped presets under
  - `CurtainSlots.b001_init(self, widget)` — Reset to Defaults, on uitk's shared reset grammar (Shift+Click saves the
  - `CurtainSlots.b002(self)` — Get: set Position to the bounding-box center of the selection.
  - `CurtainSlots.perform_operation(self, objects, contract=None)` — Build the curtain from the resolved rail (the Preview's entry point;

<a id="slots--tools--curve_to_tube"></a>
### `slots/tools/curve_to_tube.py`

Curve to Tube: sweep a circular profile along the selected curves into a

- **[`class CurveToTubeSlots(Slots)`](tentacle/tentacle/slots/tools/curve_to_tube.py#L15)**
  - `CurveToTubeSlots.header_init(self, widget)` — Configure header help text.
  - `CurveToTubeSlots.b001_init(self, widget)` — Reset to Defaults, on uitk's shared reset grammar (Shift+Click saves the
  - `CurveToTubeSlots.perform_operation(self, objects, contract=None)` — Build the tube(s) along *objects* (Maya's Preview passes its cleanup

<a id="slots--tools--cut_on_axis"></a>
### `slots/tools/cut_on_axis.py`

Cut On Axis: slice the selected meshes along an axis, then optionally delete

- **[`class CutOnAxisSlots(Slots)`](tentacle/tentacle/slots/tools/cut_on_axis.py#L14)**
  - `CutOnAxisSlots.header_init(self, widget)` — Configure header help text.
  - `CutOnAxisSlots.toggle_weight_ui(self)` — Enable the weight fields only for the modes that consume them:
  - `CutOnAxisSlots.perform_operation(self, objects, contract=None)` — Cut *objects* (Maya's Preview passes its cleanup *contract*).

<a id="slots--tools--duplicate_grid"></a>
### `slots/tools/duplicate_grid.py`

Duplicate Grid: copies of the selection in a 3D grid.

- **[`class DuplicateGridSlots(Slots)`](tentacle/tentacle/slots/tools/duplicate_grid.py#L13)**
  - `DuplicateGridSlots.header_init(self, widget)` — Configure header help text.
  - `DuplicateGridSlots.b001_init(self, widget)` — Reset to Defaults, on uitk's shared reset grammar (Shift+Click saves the
  - `DuplicateGridSlots.perform_operation(self, objects, contract=None)` — Lay *objects* out in the grid (Maya's Preview passes its cleanup

<a id="slots--tools--duplicate_linear"></a>
### `slots/tools/duplicate_linear.py`

Duplicate Linear: copies of the selection along a line, each interpolating

- [`INTERPOLATION_MODES`](tentacle/tentacle/slots/tools/duplicate_linear.py#L16) — constant
- **[`class DuplicateLinearSlots(Slots)`](tentacle/tentacle/slots/tools/duplicate_linear.py#L27)**
  - `DuplicateLinearSlots.header_init(self, widget)` — Configure header help text.
  - `DuplicateLinearSlots.toggle_weight_ui(self)` — Disable the weight spinners the current interpolation mode ignores:
  - `DuplicateLinearSlots.b001_init(self, widget)` — Reset to Defaults, on uitk's shared reset grammar (Shift+Click saves the
  - `DuplicateLinearSlots.perform_operation(self, objects, contract=None)` — Duplicate *objects* along the line (Maya's Preview passes its cleanup

<a id="slots--tools--duplicate_radial"></a>
### `slots/tools/duplicate_radial.py`

Duplicate Radial: copies of the selection in a radial pattern about a pivot.

- **[`class DuplicateRadialSlots(Slots)`](tentacle/tentacle/slots/tools/duplicate_radial.py#L13)**
  - `DuplicateRadialSlots.header_init(self, widget)` — Configure header help text.
  - `DuplicateRadialSlots.s015_init(self, widget)` — Initialize Weight Bias.
  - `DuplicateRadialSlots.s016_init(self, widget)` — Initialize Weight Curve.
  - `DuplicateRadialSlots.b001_init(self, widget)` — Reset to Defaults, on uitk's shared reset grammar (Shift+Click saves the
  - `DuplicateRadialSlots.perform_operation(self, objects, contract=None)` — Duplicate *objects* radially from the panel's values.
  - `DuplicateRadialSlots.regroup_copies(self)` — The commit's finalize step: the host groups the committed copies.

<a id="slots--tools--dynamic_pipe"></a>
### `slots/tools/dynamic_pipe.py`

Dynamic Pipe: a pipe mesh that follows a chain of handles live.

- **[`class DynamicPipeSlots(Slots)`](tentacle/tentacle/slots/tools/dynamic_pipe.py#L13)**
  - `DynamicPipeSlots.header_init(self, widget)` — Configure header help text.
  - `DynamicPipeSlots.b000(self)` — Initialize Pipe: build the pipe through the selected handles.

<a id="slots--tools--emissive_groups"></a>
### `slots/tools/emissive_groups.py`

Emissive Groups: named face groups whose emissive regions a game engine gates.

- **[`class EmissiveGroupsSlots(Slots)`](tentacle/tentacle/slots/tools/emissive_groups.py#L15)** — Switchboard slots for the ``emissive_groups.ui`` panel.
  - `EmissiveGroupsSlots.header_init(self, widget) -> None`
  - `EmissiveGroupsSlots.txt000_init(self, widget) -> None` — Group-name field — clearable back to the auto-derived name.
  - `EmissiveGroupsSlots.tbl000_init(self, widget) -> None` — Table setup: one-time construction, then (re)wire signals and populate.
  - `EmissiveGroupsSlots.b000(self) -> None` — Add (or extend) a group from the selection.
  - `EmissiveGroupsSlots.b001(self) -> None` — Remove the selected group (retires its slot).
  - `EmissiveGroupsSlots.b002(self) -> None` — Select the group's member faces.
  - `EmissiveGroupsSlots.b003(self) -> None` — Validate authoring state.
  - `EmissiveGroupsSlots.tb000_init(self, widget) -> None` — Initialize Bake.
  - `EmissiveGroupsSlots.tb000(self, widget) -> None` — Bake membership and publish the export manifest.
  - `EmissiveGroupsSlots.select_members(self) -> None`
  - `EmissiveGroupsSlots.remove_group(self) -> None`
  - `EmissiveGroupsSlots.weights_all_on(self) -> None`
  - `EmissiveGroupsSlots.weights_all_off(self) -> None`
  - `EmissiveGroupsSlots.make_weights_keyable(self) -> None`
  - `EmissiveGroupsSlots.key_weights(self) -> None`
  - `EmissiveGroupsSlots.remove_keyable_weights(self) -> None`
  - `EmissiveGroupsSlots.compact_slots(self) -> None`
  - `EmissiveGroupsSlots.republish_export(self) -> None`

<a id="slots--tools--exploded_view"></a>
### `slots/tools/exploded_view.py`

Exploded View: spread the selected objects apart to inspect interior parts.

- **[`class ExplodedViewSlots(Slots)`](tentacle/tentacle/slots/tools/exploded_view.py#L12)**
  - `ExplodedViewSlots.header_init(self, widget)` — Configure header help text.
  - `ExplodedViewSlots.b000(self)` — Explode.
  - `ExplodedViewSlots.b001(self)` — Un-Explode (selected).
  - `ExplodedViewSlots.b002(self)` — Un-Explode All.
  - `ExplodedViewSlots.b003(self)` — Toggle Explode.

<a id="slots--tools--game_shader"></a>
### `slots/tools/game_shader.py`

Game Shader: build a PBR material from a set of texture maps, packed for a

- **[`class GameShaderSlots(Slots, pythontk.LoggingMixin)`](tentacle/tentacle/slots/tools/game_shader.py#L20)**
  - `GameShaderSlots.header_init(self, widget)` — Initialize the header widget.
  - `GameShaderSlots.lbl_graph_material(self)` — Open in Editor: graph the material last built here, else the one the
  - `GameShaderSlots.mat_name(self) -> str` *(property)* — The Material Name field's text ('' derives the name from the textures).
  - `GameShaderSlots.mat_prefix(self) -> str` *(property)* — Return the affix text when it resolves as a prefix, else empty string.
  - `GameShaderSlots.mat_suffix(self) -> str` *(property)* — Return the affix text when it resolves as a suffix, else empty string.
  - `GameShaderSlots.normal_map_type(self) -> str` *(property)* — The Normal Map combo's convention: 'OpenGL' or 'DirectX'.
  - `GameShaderSlots.output_extension(self) -> str` *(property)* — Selected output extension, or '' when 'Profile default' is chosen.
  - `GameShaderSlots.shader_type(self) -> Optional[str]` *(property)* — The Shader Type combo's ``shader_type`` (Maya: 'stingray',
  - `GameShaderSlots.opacity_mode(self) -> Optional[str]` *(property)* — The opacity graph the panel asks for.
  - `GameShaderSlots.cmb002_init(self, widget)` — Initialize Presets
  - `GameShaderSlots.cmb003_init(self, widget)` — Initialize Output Format.
  - `GameShaderSlots.cmb004_init(self, widget)` — Initialize Shader Type from the host's surface shaders.
  - `GameShaderSlots.txt000_init(self, widget)` — Material-name field — clearable back to the auto-derived name.
  - `GameShaderSlots.txt002_init(self, widget)` — Add a prefix/suffix/auto-mode picker to the affix field.
  - `GameShaderSlots.b000(self)` — Create Network: pick texture files and build their material(s).

<a id="slots--tools--hdr_manager"></a>
### `slots/tools/hdr_manager.py`

HDR Manager: light the scene from an HDR environment map, spin it and adjust

- **[`class HdrManagerSlots(Slots, pythontk.LoggingMixin)`](tentacle/tentacle/slots/tools/hdr_manager.py#L25)**
  - `HdrManagerSlots.header_init(self, widget) -> None` — Configure the header menu, the refresh button and the help text.
  - `HdrManagerSlots.cmb000_init(self, widget) -> None` — Wire the HDR dropdown: option-box plugins, context menu, auto-refresh.
  - `HdrManagerSlots.hdr_map(self) -> Optional[str]` *(property)* — The dropdown's picked HDR path (or the None token).
  - `HdrManagerSlots.hdr_map_visibility(self) -> bool` *(property)* — The render-visibility toggle;
  - `HdrManagerSlots.hdr_map_preview(self) -> bool` *(property)* — The viewport-visibility toggle;
  - `HdrManagerSlots.cmb000(self, index, widget) -> None` — HDR map pick: the panel's apply, handed to the manager's
  - `HdrManagerSlots.slider000(self, value, widget) -> None` — Rotate the environment around the up axis.
  - `HdrManagerSlots.spn_intensity(self, value) -> None` — The environment's linear intensity.
  - `HdrManagerSlots.spn_exposure(self, value) -> None` — The environment's exposure, in stops.
  - `HdrManagerSlots.spn_resolution(self, value) -> None` — The HDR's importance-sampling resolution.
  - `HdrManagerSlots.spn_samples(self, value) -> None` — The environment's light samples.
  - `HdrManagerSlots.spn_diffuse(self, value) -> None` — The environment's diffuse contribution.
  - `HdrManagerSlots.spn_specular(self, value) -> None` — The environment's specular contribution.
  - `HdrManagerSlots.add_hdr(self) -> None` — Add HDR(s): one dialog picks loose files and/or folders (expanded
  - `HdrManagerSlots.open_sourceimages(self) -> None` — Open the project's texture folder in the file manager.
  - `HdrManagerSlots.clear_network(self) -> None` — Remove the HDR environment and reset the controls to defaults.
  - `HdrManagerSlots.ctx_select_skydome(self) -> None` — Select the skydome light.
  - `HdrManagerSlots.ctx_select_transform(self) -> None` — Select the skydome's transform.
  - `HdrManagerSlots.ctx_select_file_node(self) -> None` — Select the file node feeding the skydome's HDR texture.
  - `HdrManagerSlots.ctx_reveal_in_explorer(self) -> None` — Reveal the environment's HDR file in the file manager;

<a id="slots--tools--image_to_plane"></a>
### `slots/tools/image_to_plane.py`

Image to Plane: batch-create textured planes from image files.

- **[`class ImageToPlaneSlots(Slots)`](tentacle/tentacle/slots/tools/image_to_plane.py#L17)**
  - `ImageToPlaneSlots.header_init(self, widget)` — Configure header menu.
  - `ImageToPlaneSlots.txt_suffix_init(self, widget)` — Add a prefix/suffix/auto-mode picker to the affix field.
  - `ImageToPlaneSlots.b000(self)` — Browse…: queue image files from a file dialog (no duplicates).
  - `ImageToPlaneSlots.b004(self)` — Clear: empty the queue.
  - `ImageToPlaneSlots.b001(self)` — Create Planes: one textured plane per queued image.
  - `ImageToPlaneSlots.b002(self)` — Remove Selected: delete the selected planes and their materials.

<a id="slots--tools--image_tracer"></a>
### `slots/tools/image_tracer.py`

Image Tracer: trace a raster image's contours into curves, then fill them

- **[`class ImageTracerSlots(Slots)`](tentacle/tentacle/slots/tools/image_tracer.py#L14)**
  - `ImageTracerSlots.header_init(self, widget)` — Initialize the header widget.
  - `ImageTracerSlots.txt000_init(self, widget)` — Configure the path field's option box (▸) as an image file browser.
  - `ImageTracerSlots.chk000(self, state)` — Use Blue Pencil: no image path while it is on.
  - `ImageTracerSlots.blue_pencil_button(self)` — Open Blue Pencil: the host's Blue Pencil tool (disabled where none).
  - `ImageTracerSlots.b002(self)` — Trace the source image into curves.
  - `ImageTracerSlots.b003(self)` — Build a mesh from the traced curves.
  - `ImageTracerSlots.b004(self)` — Build a mesh from the traced negative space.
  - `ImageTracerSlots.b005(self)` — Project the traced result onto a plane.

<a id="slots--tools--key_stash"></a>
### `slots/tools/key_stash.py`

Key Stash: park keys out of the working animation as clips, then preview or

- **[`class KeyStashSlots(Slots, pythontk.LoggingMixin)`](tentacle/tentacle/slots/tools/key_stash.py#L23)**
  - `KeyStashSlots.header_init(self, widget) -> None` — Configure header buttons, the refresh action and the help text.
  - `KeyStashSlots.store(self)` *(property)* — The host's active store, (re)bound to this panel's change listener.
  - `KeyStashSlots.refresh(self) -> None` — Repaint the clip list from the store.
  - `KeyStashSlots.refresh_from_scene(self) -> None` — Header refresh: prune clips whose stored keys are gone, then repaint.
  - `KeyStashSlots.b000(self) -> None` — Store Keys
  - `KeyStashSlots.b001(self) -> None` — Retrieve
  - `KeyStashSlots.chk001(self, checked: bool) -> None` — Preview (toggle)
  - `KeyStashSlots.b003(self) -> None` — Drop

<a id="slots--tools--lightmap_baker"></a>
### `slots/tools/lightmap_baker.py`

Lightmap Baker: bake the scene's lighting into lightmaps the engine reads.

- **[`class LightmapBakerSlots(Slots, pythontk.LoggingMixin)`](tentacle/tentacle/slots/tools/lightmap_baker.py#L23)** — The Lightmap Baker panel.
  - `LightmapBakerSlots.header_init(self, widget) -> None` — Configure the header and its help text.
  - `LightmapBakerSlots.cmb000_init(self, widget) -> None` — Wire the Preset combo: uitk's preset template over the shared store.
  - `LightmapBakerSlots.btn_reset_defaults_init(self, widget) -> None` — Wire Reset to Defaults to uitk's shared reset grammar.
  - `LightmapBakerSlots.cmb002_init(self, widget) -> None` — Populate the Packing combobox (Atlas by Material is the default) and
  - `LightmapBakerSlots.cmb_scope_init(self, widget) -> None` — Populate the Scope combobox (Selected is the default) and hang the
  - `LightmapBakerSlots.set_exclusions_init(self, widget) -> None` — Hang Select / Clear off the Exclude row (:meth:`_init_set_row`).
  - `LightmapBakerSlots.set_exclusions(self) -> None` — Make the selection the Exclude set;
  - `LightmapBakerSlots.select_exclusions(self) -> None` — Select the Exclude set's members (:meth:`_select_set_row`).
  - `LightmapBakerSlots.clear_exclusions(self) -> None` — Remove the Exclude set;
  - `LightmapBakerSlots.set_isolation_init(self, widget) -> None` — Hang Select / Clear off the Isolate row (:meth:`_init_set_row`).
  - `LightmapBakerSlots.set_isolation(self) -> None` — Make the selection the Isolate set;
  - `LightmapBakerSlots.select_isolation(self) -> None` — Select the Isolate set's members (:meth:`_select_set_row`).
  - `LightmapBakerSlots.clear_isolation(self) -> None` — Remove the Isolate set;
  - `LightmapBakerSlots.cmb_resolution_init(self, widget) -> None` — Populate the Resolution combobox (value carried as item data,
  - `LightmapBakerSlots.spn_samples_init(self, widget) -> None` — Range and seed the Samples field in the host's units, and hang the
  - `LightmapBakerSlots.spn_gi_samples_init(self, widget) -> None` — Seed GI Samples from the default tier, or hide it where the host's
  - `LightmapBakerSlots.spn_bounces_init(self, widget) -> None` — Seed Bounces from the default tier, under the host engine's key for
  - `LightmapBakerSlots.cmb_device_init(self, widget) -> None` — Populate the Processor combobox (value carried as item data);
  - `LightmapBakerSlots.txt_output_dir_init(self, widget) -> None` — Add the folder browser and the Beside Material Textures toggle.
  - `LightmapBakerSlots.txt000_init(self, widget) -> None` — Add the Prefix / Suffix / Auto picker to the name-affix field.
  - `LightmapBakerSlots.b000(self) -> None` — The Bake page's run button: bake the Scope minus the Exclude set
  - `LightmapBakerSlots.cmb_page_init(self, widget) -> None` — Populate the page picker (Bake first);
  - `LightmapBakerSlots.cmb_page(self, index) -> None` — Show the picked page (:meth:`_refresh_page`).
  - `LightmapBakerSlots.tbl_maps_init(self, widget) -> None` — The Manage table: one row per map the scene reads
  - `LightmapBakerSlots.select_by_state(self, kind: str) -> None` — The footer's **Select**: highlight the maps in *kind*'s state on
  - `LightmapBakerSlots.open_map_folder(self) -> None` — Open the highlighted map's folder in the file manager: its home,
  - `LightmapBakerSlots.combine_selected(self) -> None` — Pack the highlighted split maps' groups into one atlas each, no
  - `LightmapBakerSlots.fix_all(self) -> None` — The footer's **Fix All**: every map that needs it, once confirmed
  - `LightmapBakerSlots.track_selected(self) -> None` — Start tracking the selected untracked objects as they stand
  - `LightmapBakerSlots.revert_selected(self) -> None` — Take the lightmaps off the selected objects, once confirmed.
  - `LightmapBakerSlots.rebake_selected(self) -> None` — Re-bake the selected baked objects the way each was baked, changed
  - `LightmapBakerSlots.show_bake_state(self) -> None` — Show the scene's bake state, map by map, in a viewer
  - `LightmapBakerSlots.open_output(self) -> None` — Open the bake's output folder in the file manager.

<a id="slots--tools--mat_updater"></a>
### `slots/tools/mat_updater.py`

Material Updater: rework scene materials for a target workflow preset,

- **[`class MatUpdaterSlots(Slots)`](tentacle/tentacle/slots/tools/mat_updater.py#L22)**
  - `MatUpdaterSlots.logger(self)` *(property)* — The engine's logger: the run report and this panel's notes share it.
  - `MatUpdaterSlots.header_init(self, widget)` — Format global options in the header menu.
  - `MatUpdaterSlots.selection_mode(self)` *(property)*
  - `MatUpdaterSlots.move_to_folder(self)` *(property)*
  - `MatUpdaterSlots.shader_type(self)` *(property)* — The selected retype target, or None for "keep the current type"
  - `MatUpdaterSlots.cmb001_init(self, widget)` — Initialize Presets.
  - `MatUpdaterSlots.b001(self)` — Update Materials

<a id="slots--tools--mirror"></a>
### `slots/tools/mirror.py`

Mirror: mirror the selected meshes across an axis, with a live preview.

- **[`class MirrorSlots(Slots)`](tentacle/tentacle/slots/tools/mirror.py#L13)**
  - `MirrorSlots.header_init(self, widget)` — Configure header help text.
  - `MirrorSlots.prepare_operation(self, objects)` — Break instance links once, before the preview contract exists.
  - `MirrorSlots.perform_operation(self, objects, contract=None)` — Mirror *objects* (Maya's Preview passes its cleanup *contract*).

<a id="slots--tools--naming"></a>
### `slots/tools/naming.py`

Naming: batch find / rename / convert-case / strip-chars / suffix-by-location /

- **[`class NamingSlots(Slots)`](tentacle/tentacle/slots/tools/naming.py#L32)**
  - `NamingSlots.logger(self)` *(property)* — The host engine's logger (``Naming.logger``): what the operations
  - `NamingSlots.header_init(self, widget)` — Configure header menu with tool description and workflow instructions.
  - `NamingSlots.scope(self) -> str` *(property)*
  - `NamingSlots.dry_run(self) -> bool` *(property)*
  - `NamingSlots.file_scope(self) -> bool` *(property)*
  - `NamingSlots.base_names(self) -> bool` *(property)* — Operate on map-suffix-free base names — file scopes only.
  - `NamingSlots.valid_suffixes(self)` *(property)* — The current Suffix By Type strings (non-empty), from the tb003 option box.
  - `NamingSlots.txt000_init(self, widget)` — Initialize Find
  - `NamingSlots.txt000(self, widget)` — Find: select scene objects (or browse for files) whose name matches the pattern.
  - `NamingSlots.txt001_init(self, widget)` — Initialize Rename
  - `NamingSlots.txt001(self, widget)` — Rename: rename matched objects or files (find → replace, with regex / suffix options).
  - `NamingSlots.tb000_init(self, widget)` — Initialize Convert Case
  - `NamingSlots.tb000(self, widget)` — Convert Case
  - `NamingSlots.tb001_init(self, widget)` — Initialize Suffix By Location
  - `NamingSlots.tb001(self, widget)` — Suffix By Location: number the objects in scope by their distance from
  - `NamingSlots.tb002_init(self, widget)` — Initialize Strip Chars
  - `NamingSlots.tb002(self, widget)` — Strip Chars: remove a number of leading/trailing characters from the names in scope.
  - `NamingSlots.tb003_init(self, widget)` — Initialize Suffix By Type — the editor for the shared naming convention.
  - `NamingSlots.tb003(self, widget)` — Suffix By Type

<a id="slots--tools--render_effects"></a>
### `slots/tools/render_effects.py`

Render Effects: key per-object opacity fades and highlight pulses for export.

- **[`class RenderEffectsSlots(Slots)`](tentacle/tentacle/slots/tools/render_effects.py#L50)** — Switchboard slots for the Render Effects UI.
  - `RenderEffectsSlots.header_init(self, widget)` — Configure header menu.
  - `RenderEffectsSlots.cmb_effect_init(self, widget)` — The effect picker: one entry per page.
  - `RenderEffectsSlots.cmb_effect(self, index, widget=None)` — Show the picked effect's page.
  - `RenderEffectsSlots.stk_effects_init(self, widget)` — Build every page into the stack, bind the recipe, register the rows.
  - `RenderEffectsSlots.ui_field(self, name)` — A page field by objectName, from whichever page holds it.
  - `RenderEffectsSlots.focus(self, channel, objects, title='', apply=None, apply_text='')` — Open on one effect for *objects*, as the manifest's row actions do.
  - `RenderEffectsSlots.unfocus(self, *_args) -> None` — Back to the standalone panel: the picker, its title, the Key texts
  - `RenderEffectsSlots.b000(self, widget=None)` — Key: the shown page's keyer (``PAGES``).
  - `RenderEffectsSlots.btn_remove(self, widget=None)` — Strip the shown page's channel from the selection.
  - `RenderEffectsSlots.btn_webxr_init(self, widget)`
  - `RenderEffectsSlots.btn_webxr(self, widget=None)` — Preview the shown page's effect in WebXR.

<a id="slots--tools--scene_exporter"></a>
### `slots/tools/scene_exporter.py`

Scene Exporter: batch-export the scene through its task/check pipeline.

- **[`class SceneExporterSlots(Slots, pythontk.LoggingMixin)`](tentacle/tentacle/slots/tools/scene_exporter.py#L28)**
  - `SceneExporterSlots.confirm(self, question: str) -> bool` — The engine's consent seam as the panel's modal Yes/No.
  - `SceneExporterSlots.decide_check_failure(self, check: str, messages: List[str], remaining: List[str]) -> str` — The engine's check-failure seam as the panel's three-button dialog.
  - `SceneExporterSlots.workspace(self) -> str` *(property)* — The current workspace's root (the dialogs' start folder);
  - `SceneExporterSlots.header_init(self, widget)` — Initialize the header widget (its help;
  - `SceneExporterSlots.cmb000_init(self, widget) -> None` — Init FBX Preset — a Settings row (``cmb008``), created by
  - `SceneExporterSlots.txt000_init(self, widget) -> None` — Init Output Directory
  - `SceneExporterSlots.output_name_preview(self) -> str` — Live tooltip for the Output Filename field.
  - `SceneExporterSlots.txt001_init(self, widget) -> None` — Init Output Name
  - `SceneExporterSlots.cmb001_init(self, widget) -> None` — Tasks — scene-prep steps the engine dispatches (``TASK_ORDER``),
  - `SceneExporterSlots.cmb002_init(self, widget) -> None` — Validation Checks — the gates that abort the write, grouped by tag.
  - `SceneExporterSlots.cmb007_init(self, widget) -> None` — Export Preset — the whole panel's run configuration under a name.
  - `SceneExporterSlots.cmb008_init(self, widget) -> None` — Settings — what is written and from what (the scene-prep steps are
  - `SceneExporterSlots.ignore_groups_init(self, widget) -> None` — Init Ignore Groups — a Settings row (``cmb008``), created by
  - `SceneExporterSlots.export_data_node_init(self, widget) -> None` — Init Export Scene Data Node — a Settings row (``cmb008``).
  - `SceneExporterSlots.cmb004_init(self, widget) -> None` — Init Output Format — FBX (default), GLB, FBX + GLB, or USD.
  - `SceneExporterSlots.cmb005_init(self, widget) -> None` — Init Texture Template — optionally convert textures to a registry workflow.
  - `SceneExporterSlots.b000(self) -> None` — Export: run the scene export with the configured tasks and settings.
  - `SceneExporterSlots.b010(self) -> None` — Set Output Directory
  - `SceneExporterSlots.b012(self) -> None` — Browse for Output File -- name the export after an existing file.
  - `SceneExporterSlots.b006(self) -> None` — Open Output Directory
  - `SceneExporterSlots.b007(self) -> None` — Open FBX Preset Directory -- the host's own FBX preset folder, where
  - `SceneExporterSlots.b008(self) -> None` — Edit FBX Preset -- the host's edit surface for the selected preset
  - `SceneExporterSlots.save_output_dir(self, output_dir: str) -> None` — Record the output directory into the recent values plugin.
  - `SceneExporterSlots.save_output_name(self, output_name: str) -> None` — Record the output filename into the recent values plugin.

<a id="slots--tools--shader_templates"></a>
### `slots/tools/shader_templates.py`

Shader Templates: save a material's shader network as a reusable template

- **[`class ShaderTemplatesSlots(Slots, pythontk.LoggingMixin)`](tentacle/tentacle/slots/tools/shader_templates.py#L22)**
  - `ShaderTemplatesSlots.source_images_dir(self) -> str` *(property)* — Where Load Texture Maps opens: the scene project's texture folder,
  - `ShaderTemplatesSlots.header_init(self, widget)` — Initialize the header widget.
  - `ShaderTemplatesSlots.lbl_graph_material(self)` — Graph the last restored material in the host's shader editor.
  - `ShaderTemplatesSlots.lbl_open_templates_dir(self)` — Open the user's shader templates directory in the file manager.
  - `ShaderTemplatesSlots.cmb002_init(self, widget)` — Initialize the ComboBox for shader templates.
  - `ShaderTemplatesSlots.refresh_templates(self, widget)` — List the templates, each carrying its file: shipped and the user's
  - `ShaderTemplatesSlots.rename_template_safe(self, widget, new_name)` — Rename the selected (user) template to *new_name*, through the
  - `ShaderTemplatesSlots.lbl000(self)` — Make the ComboBox editable, to rename the template.
  - `ShaderTemplatesSlots.lbl001(self)` — Delete the selected (user) template.
  - `ShaderTemplatesSlots.lbl002(self)` — Open the selected template in the default editor.
  - `ShaderTemplatesSlots.b000(self)` — Create Network: rebuild the selected template, rebinding the loaded
  - `ShaderTemplatesSlots.b001(self)` — Load Texture Maps: pick the maps Create Network rebinds by type.
  - `ShaderTemplatesSlots.b002(self)` — Save Template: capture the selection's material network under a

<a id="slots--tools--shadow_rig"></a>
### `slots/tools/shadow_rig.py`

Shadow Rig: a ground plane carrying the targets' projected shadow, built for

- **[`class ShadowRigSlots(Slots, pythontk.LoggingMixin)`](tentacle/tentacle/slots/tools/shadow_rig.py#L25)**
  - `ShadowRigSlots.header_init(self, widget)` — Configure header help text.
  - `ShadowRigSlots.cmb_type_init(self, widget)` — A rig type the panel only plans for is listed but not selectable.
  - `ShadowRigSlots.txt_source_init(self, widget)` — Source Name's option box: the two actions about the source --
  - `ShadowRigSlots.b003_init(self, widget)` — Recalculate Silhouette's option box: the deeper updates of an
  - `ShadowRigSlots.b002_init(self, widget)` — Bake to Keyframes' option box: Restore Expression, its inverse.
  - `ShadowRigSlots.b009_init(self, widget)` — Delete Rig's option box: Detach to Plane, the teardown that keeps
  - `ShadowRigSlots.b001_init(self, widget)` — Reset to Defaults, on uitk's shared reset grammar (Shift+Click saves the
  - `ShadowRigSlots.prepare_operation(self, objects)` — Preview's one-shot precondition, run at enable outside any
  - `ShadowRigSlots.source_from_selection(self)` — Source From Selection (Source Name's option box): the selected
  - `ShadowRigSlots.reproject_sources(self)` — Reproject (Source Name's option box): re-render the silhouette of
  - `ShadowRigSlots.perform_operation(self, objects, contract=None)` — Build one shadow rig per source for the selected target(s).
  - `ShadowRigSlots.chk_follow_init(self, widget)` — Follow Source arms the engine's watcher from the box's (saved)
  - `ShadowRigSlots.chk_follow(self, checked)` — Follow Source: re-render a silhouette as soon as its source -- or
  - `ShadowRigSlots.s001_init(self, widget)` — Softness shows the scene's value for the first Source Name -- its
  - `ShadowRigSlots.s001(self, value)` — Softness: the diameter the shadow gives the source(s) named in
  - `ShadowRigSlots.s002(self, value)` — Intensity: the overall darkness a new rig builds with, applied at
  - `ShadowRigSlots.s003(self, value)` — Ground Y: the floor's world height (Blender's Z) a new rig builds
  - `ShadowRigSlots.chk_horizon_preview_init(self, widget)` — The box mirrors the SCENE, never a saved setting: checked while a
  - `ShadowRigSlots.chk_horizon_preview(self, checked)` — Live Horizon Preview: the horizon plane(s) the selection touches
  - `ShadowRigSlots.b002(self)` — Bake to Keyframes: bake the rig(s) the selection touches (or all)
  - `ShadowRigSlots.b003(self)` — Recalculate Silhouette: re-render the rig(s) the selection touches
  - `ShadowRigSlots.apply_source(self)` — Apply Source (Recalculate's option box): re-point the rig(s) the
  - `ShadowRigSlots.rebuild_rig(self)` — Rebuild Rig (Recalculate's option box): re-create the rig(s) the
  - `ShadowRigSlots.restore_expression(self)` — Restore Expression (Bake's option box): un-bake the rig(s) the
  - `ShadowRigSlots.b009(self)` — Delete Rig: tear down the rig(s) the selection touches.
  - `ShadowRigSlots.detach_to_plane(self)` — Detach to Plane (Delete Rig's option box): the rig(s) the selection
  - `ShadowRigSlots.b010(self)` — Pack Atlas: pack or repack every shadow rig's tiles into the

<a id="slots--tools--shell_xform"></a>
### `slots/tools/shell_xform.py`

Shell Xform: move, flip, rotate, straighten, mirror, distribute, align and

- **[`class ShellXformSlots(Slots)`](tentacle/tentacle/slots/tools/shell_xform.py#L17)**
  - `ShellXformSlots.header_init(self, widget)` — Header menu — Open UV Editor + panel help.
  - `ShellXformSlots.cmb_move_scope_init(self, widget)` — Move scope — how far one arrow press travels, plus the snap button.
  - `ShellXformSlots.b023(self)` — Move To UV Space: Left
  - `ShellXformSlots.b024(self)` — Move To UV Space: Down
  - `ShellXformSlots.b025(self)` — Move To UV Space: Up
  - `ShellXformSlots.b026(self)` — Move To UV Space: Right
  - `ShellXformSlots.gather_to_udim(self)` — Move shells sitting outside the selection's UDIM tile into it.
  - `ShellXformSlots.b034(self)` — Flip U: mirror the selected UVs horizontally about each shell's center.
  - `ShellXformSlots.b035(self)` — Flip V: mirror the selected UVs vertically about each shell's center.
  - `ShellXformSlots.b036(self)` — Rotate the selected UVs counter-clockwise by the s041 angle.
  - `ShellXformSlots.b037(self)` — Rotate the selected UVs clockwise by the s041 angle.
  - `ShellXformSlots.s041(self, value, widget)` — Rotate Angle — passive input; read by the Rotate buttons (b036/b037).
  - `ShellXformSlots.tb005_init(self, widget)` — Initialize Straighten UV
  - `ShellXformSlots.tb005(self, widget)` — Straighten UV: selected UV edges within the angle snap flat;
  - `ShellXformSlots.tb006_init(self, widget)` — Initialize Distribute
  - `ShellXformSlots.tb006(self, widget)` — Distribute: lay the selected UV shells out in a row along U or V.
  - `ShellXformSlots.tb008_init(self, widget)` — Initialize Mirror UVs.
  - `ShellXformSlots.tb008(self, widget)` — Mirror UVs (footprint-preserving by default).
  - `ShellXformSlots.align_u_min(self)` — Align the selected UVs to their minimum U (left).
  - `ShellXformSlots.align_u_avg(self)` — Align the selected UVs to their average U (center).
  - `ShellXformSlots.align_u_max(self)` — Align the selected UVs to their maximum U (right).
  - `ShellXformSlots.align_v_min(self)` — Align the selected UVs to their minimum V (bottom).
  - `ShellXformSlots.align_v_avg(self)` — Align the selected UVs to their average V (center).
  - `ShellXformSlots.align_v_max(self)` — Align the selected UVs to their maximum V (top).
  - `ShellXformSlots.linear_align(self)` — Linearly align the selected UVs between their two end points.
  - `ShellXformSlots.orient_shells(self)` — Orient each shell to run parallel with its nearest U/V axis.
  - `ShellXformSlots.orient_edges(self)` — Orient the shell so its selected edge runs along U or V.
  - `ShellXformSlots.gather_shells(self)` — Gather the selected shells together toward the 0-1 UV space.
  - `ShellXformSlots.randomize_shells(self)` — Randomly offset the selected shells;
  - `ShellXformSlots.open_uv_editor(self)` — Open the host's UV Editor.

<a id="slots--tools--shot_manifest"></a>
### `slots/tools/shot_manifest.py`

Shot Manifest: a shot sheet checked against the scene, and the shots built from it.

- **[`class ShotManifestSlots(Slots)`](tentacle/tentacle/slots/tools/shot_manifest.py#L15)** — Switchboard slots for the ``shot_manifest.ui`` panel.
  - `ShotManifestSlots.header_init(self, widget)` — Header menu is configured once in the controller's ``__init__``.
  - `ShotManifestSlots.btn_settings(self)` — Open the shared shots settings panel.
  - `ShotManifestSlots.b002(self)` — Assess the steps against the scene.
  - `ShotManifestSlots.b003(self)` — Build shots from loaded steps (or auto-detect from scene).
  - `ShotManifestSlots.b004(self)` — Export the manifest's rows (the option menu says how).

<a id="slots--tools--smart_bake"></a>
### `slots/tools/smart_bake.py`

Smart Bake: bake what drives the scene's animation to keys, reversibly.

- **[`class SmartBakeSlots(Slots, pythontk.LoggingMixin)`](tentacle/tentacle/slots/tools/smart_bake.py#L19)**
  - `SmartBakeSlots.cmb_scope_init(self, widget) -> None`
  - `SmartBakeSlots.cmb_backup_init(self, widget) -> None`
  - `SmartBakeSlots.header_init(self, widget) -> None` — Configure header menu, refresh button, and help text.
  - `SmartBakeSlots.b000(self, widget) -> None` — Bake.
  - `SmartBakeSlots.b001(self, widget) -> None` — Unbake.

<a id="slots--tools--snap"></a>
### `slots/tools/snap.py`

Snap: vertices to a target surface, to the closest target vertex, or to the grid.

- **[`class SnapSlots(Slots)`](tentacle/tentacle/slots/tools/snap.py#L13)**
  - `SnapSlots.header_init(self, widget)` — Configure header help text.
  - `SnapSlots.b000_init(self, widget)` — Initialize Snap to Surface button option box.
  - `SnapSlots.b000(self)` — Snap to Surface button.
  - `SnapSlots.b001_init(self, widget)` — Initialize Snap to Closest Vertex button option box.
  - `SnapSlots.b001(self)` — Snap to Closest Vertex button.
  - `SnapSlots.b002_init(self, widget)` — Initialize Snap to Grid button option box.
  - `SnapSlots.b002(self)` — Snap to Grid button.

<a id="slots--tools--telescope_rig"></a>
### `slots/tools/telescope_rig.py`

Telescope Rig: nested segments that extend and retract between a base and an

- **[`class TelescopeRigSlots(Slots, pythontk.LoggingMixin)`](tentacle/tentacle/slots/tools/telescope_rig.py#L19)**
  - `TelescopeRigSlots.header_init(self, widget)` — Configure header help text.
  - `TelescopeRigSlots.build_rig(self)` — Build Telescope Rig: rig the selected segments between their handles.
  - `TelescopeRigSlots.remove_rig(self)` — Remove Telescope Rig: tear down the rigs on the selection, or the

<a id="slots--tools--texture_combine"></a>
### `slots/tools/texture_combine.py`

Texture Combine: several materials into one atlas and one material, in

- **[`class TextureCombineSlots(Slots, pythontk.LoggingMixin)`](tentacle/tentacle/slots/tools/texture_combine.py#L36)** — Switchboard slots for the ``texture_combine.ui`` panel.
  - `TextureCombineSlots.header_init(self, widget) -> None`
  - `TextureCombineSlots.cmb_mode_init(self, widget) -> None`
  - `TextureCombineSlots.open_output_folder(self) -> None`
  - `TextureCombineSlots.cmb_set_init(self, widget) -> None`
  - `TextureCombineSlots.select_set(self) -> None`
  - `TextureCombineSlots.recombine_set(self) -> None`
  - `TextureCombineSlots.restore_set(self) -> None`
  - `TextureCombineSlots.forget_set(self) -> None`
  - `TextureCombineSlots.tbl_sources_init(self, widget) -> None`
  - `TextureCombineSlots.parse_scale(text: str) -> Optional[float]` *(static)* — ``0.33``, ``1/3`` or ``33%`` as a float, ``None`` when unreadable.
  - `TextureCombineSlots.select_row_members(self) -> None`
  - `TextureCombineSlots.remove_override(self) -> None`
  - `TextureCombineSlots.reset_scales(self) -> None`
  - `TextureCombineSlots.b001(self) -> None` — Add the selected meshes as one mesh override row each.
  - `TextureCombineSlots.b002(self) -> None` — Add the islands under the selected faces as an override row.
  - `TextureCombineSlots.cmb_sizing_init(self, widget) -> None`
  - `TextureCombineSlots.cmb_normalize_init(self, widget) -> None`
  - `TextureCombineSlots.cmb_atlas_init(self, widget) -> None`
  - `TextureCombineSlots.s_spacing_init(self, widget) -> None`
  - `TextureCombineSlots.chk_rotate_init(self, widget) -> None`
  - `TextureCombineSlots.chk_lightmaps_init(self, widget) -> None`
  - `TextureCombineSlots.cmb_tt_transfer_init(self, widget) -> None`
  - `TextureCombineSlots.cmb_tt_source_init(self, widget) -> None`
  - `TextureCombineSlots.cmb_tt_targets_init(self, widget) -> None`
  - `TextureCombineSlots.cmb_tt_resolution_init(self, widget) -> None`
  - `TextureCombineSlots.t_tt_dst_uvset_init(self, widget) -> None`
  - `TextureCombineSlots.chk_tt_lightmaps_init(self, widget) -> None`
  - `TextureCombineSlots.t_name_init(self, widget) -> None`
  - `TextureCombineSlots.record_name(self, name: str) -> None`
  - `TextureCombineSlots.t_output_init(self, widget) -> None`
  - `TextureCombineSlots.cmb_quality_init(self, widget) -> None`
  - `TextureCombineSlots.s_padding_init(self, widget) -> None`
  - `TextureCombineSlots.chk_assign_init(self, widget) -> None`
  - `TextureCombineSlots.t_affix_init(self, widget) -> None`
  - `TextureCombineSlots.material_affix(self)` — ``(assign_prefix, assign_suffix)`` from the affix row (blank: Auto).
  - `TextureCombineSlots.cmb_shader_init(self, widget) -> None`
  - `TextureCombineSlots.overwrites_target(self) -> bool` — Whether the Material row re-uses the target's material in place --
  - `TextureCombineSlots.assign_options(self) -> Dict[str, Any]`
  - `TextureCombineSlots.sync_shared(self, textures: bool = True) -> None` — Transfer mode: the Output / Material rows follow the texture pass.
  - `TextureCombineSlots.status(self, text: str) -> None`
  - `TextureCombineSlots.b000(self) -> None` — Run the current mode.
  - `TextureCombineSlots.combine(self) -> None`

<a id="slots--tools--tube_rig"></a>
### `slots/tools/tube_rig.py`

Tube Rig: rig a tube-shaped mesh (hose, cable, piston, tail) with joints,

- **[`class TubeRigSlots(Slots)`](tentacle/tentacle/slots/tools/tube_rig.py#L16)**
  - `TubeRigSlots.txt000_init(self, widget)` — Rig-name field — optional, so clearing back to auto-naming is a state.
  - `TubeRigSlots.header_init(self, widget)` — Configure header help text.
  - `TubeRigSlots.apply_mode(self, index: int)` — Apply a mode's values and constraints to the option widgets.
  - `TubeRigSlots.get_mode(self)` — The current rig mode (a ``TubeRig.MODES`` entry).
  - `TubeRigSlots.get_strategy(self) -> str` — The current mode's strategy name (``spline`` / ``anchor`` / ``fk``).
  - `TubeRigSlots.b000(self)` — One-Click Rig — runs Steps 1 → 2 → 3 with the step parameters,
  - `TubeRigSlots.b001(self)` — Step 1: Create Joints from Tube — once per selected tube.
  - `TubeRigSlots.b002(self)` — Step 2: Create IK / Controls (mode dependent) on the selected chain.
  - `TubeRigSlots.b003(self)` — Step 3: Bind the joint chain to the tube.
  - `TubeRigSlots.b004(self)` — Utility: Constrain Ends to Anchors — one anchor or both, each to its
  - `TubeRigSlots.b005(self)` — Utility: Remove Rig — tear down every rig the selection touches.
  - `TubeRigSlots.b006(self)` — Utility: Rename Rig — to the Rig Name field, every node included.
  - `TubeRigSlots.b007(self)` — Utility: Rebind Skin — re-solve the bind for every rig the selection

<a id="slots--tools--wheel_rig"></a>
### `slots/tools/wheel_rig.py`

Wheel Rig: wheels that roll as their driver (control) moves, sized by wheel

- **[`class WheelRigSlots(Slots)`](tentacle/tentacle/slots/tools/wheel_rig.py#L15)**
  - `WheelRigSlots.header_init(self, widget)` — Configure header menu with mode toggle and instructions.
  - `WheelRigSlots.rig_name(self) -> str` *(property)* — The Rig Name field's text ("" when left to the default).
  - `WheelRigSlots.movement_axis(self) -> str` *(property)* — The driver's travel channel the Axis combo names (``translateZ``).
  - `WheelRigSlots.rotation_axis(self) -> str` *(property)* — The wheel rotation channel the Axis combo pairs with it (``rotateX``).
  - `WheelRigSlots.set_wheel_height(self)` — Get Wheel Size: Wheel Height from the selected wheel's bounding box,
  - `WheelRigSlots.txt000_init(self, widget)` — Rig-name field — optional, so clearing back to auto-naming is a state.
  - `WheelRigSlots.s000_init(self, widget)` — Initialize the wheel height field's option-box menu.
  - `WheelRigSlots.update_rig_name_placeholder(self)` — Show, as the Rig Name placeholder, the name a rig on the selection's
  - `WheelRigSlots.b000(self)` — Rig Rotation: rig the selected wheels to the selected driver, or

<a id="tcl"></a>
### `tcl.py`

The host-agnostic entry point — one launcher snippet for every DCC.

- **[`class QtPlatformUnavailable(RuntimeError)`](tentacle/tentacle/tcl.py#L39)** — Qt cannot open a window in this host process, so the marking menu is off.
- **[`class Tcl(_TclInternal)`](tentacle/tentacle/tcl.py#L377)** — Launch tentacle in whichever DCC is hosting this process.
  - `Tcl.host(cls)` *(class)* — The DCC hosting this process (``'maya'``/``'blender'``/``'max'``), or None.
  - `Tcl.declared_dists(cls, host=None, include_self=True)` *(class)* — Every ecosystem distribution THIS install actually uses, for *host*.
  - `Tcl.prepare_reload(cls, host=None)` *(class)* — Release the host resources an in-place reload would ORPHAN.
  - `Tcl.reload_packages(cls, host=None)` *(class)* — Re-execute the ecosystem packages in dependency order, in place.
  - `Tcl.dispose_retired(instances)` *(static)* — Schedule deletion of the pre-reload marking menus in *instances*.
  - `Tcl.qt_key_name(cls, key_show=None)` *(class)* — Normalize an activation key to its Qt name: ``'Z'`` and ``'Key_Z'`` both → ``'Key_Z'``.
  - `Tcl.resolve_key(cls, key_show=None, context_tags=None)` *(class)* — The activation key to launch with: **user-persisted > ``key_show`` > :attr:`DEFAULT_KEY`**.
  - `Tcl.register_shared(switchboard)` *(static)* — Register on *switchboard* what every host shares (CODE_STANDARD section 3).
  - `Tcl.chord_bindings(cls, key_show=None, chord_target=None)` *(class)* — The default chord→menu table for ``key_show`` (bare or Qt-named).
  - `Tcl.banner(cls, template=None, force=False)` *(class)* — Print the startup banner — the one sanctioned emitter of :func:`tentacle.greeting`.
  - `Tcl.launch(cls, key_show=None, **kwargs)` *(class)* — Start tentacle in the host DCC, deferring startup the way that host requires.
  - `Tcl.engine_dists(cls, host)` *(class)* — Distribution names ``pyproject``'s ``[project.optional-dependencies]`` declares for *host*.
  - `Tcl.engine_install_hint(cls, host=None)` *(class)* — The pip line that installs *host*'s engine, naming the interpreter to use.

<a id="tcl_blender"></a>
### `tcl_blender.py`

Blender entry point for tentacle's Qt marking menu — host + keymap bridge + launcher in one.

- [`ensure_qapp()`](tentacle/tentacle/tcl_blender.py#L2262) — Return the process QApplication, creating one if Blender has none.
- [`ensure_blender_widget(app)`](tentacle/tentacle/tcl_blender.py#L2267) — Establish ``app.blender_widget`` — the parent for the marking menu.
- [`start_event_pump(app, interval=0.01)`](tentacle/tentacle/tcl_blender.py#L2272) — Pump Qt events from Blender's timer loop so the Qt UI stays responsive (idempotent).
- [`blender_native_window()`](tentacle/tentacle/tcl_blender.py#L2277) — Blender's main GHOST window wrapped as a foreign ``QWindow`` (cached on the QApplication).
- [`launch(**kwargs)`](tentacle/tentacle/tcl_blender.py#L2282) — Stand up the Qt host and return a :class:`TclBlender` (idempotent).
- [`register(**kwargs)`](tentacle/tentacle/tcl_blender.py#L2287) — Blender add-on / startup entry.
- [`unregister()`](tentacle/tentacle/tcl_blender.py#L2292) — Blender add-on teardown.
- [`reload()`](tentacle/tentacle/tcl_blender.py#L2297) — Reload the tentacle ecosystem in place and re-register.
- [`diagnose()`](tentacle/tentacle/tcl_blender.py#L2302) — Return (and print) the live activation state.
- [`enable_click_debug()`](tentacle/tentacle/tcl_blender.py#L2307) — Turn on the opt-in click tracer.
- [`disable_click_debug()`](tentacle/tentacle/tcl_blender.py#L2312) — Remove the click tracer.
- **[`class TclBlender(MarkingMenu)`](tentacle/tentacle/tcl_blender.py#L1503)** — Marking Menu class overridden for use with Blender.
  - `TclBlender.get_main_window(cls)` *(class)* — Blender parent widget for the marking menu (set by :meth:`_QtHost.ensure_widget`).
  - `TclBlender.set_activation_key(self, new_key)` — Rebind the activation key — and move Blender's half of the binding with it.
  - `TclBlender.showEvent(self, event)`
  - `TclBlender.keyPressEvent(self, event)`
  - `TclBlender.keyReleaseEvent(self, event)`
- **[`class Diagnostics`](tentacle/tentacle/tcl_blender.py#L2027)** — The live-activation-state report — run in Blender's Python console to see why the key isn't
  - `Diagnostics.report(emit=True)` *(static)* — Return (and, when ``emit``, print) the live activation state — run in Blender's Python
- **[`class BlenderHost`](tentacle/tentacle/tcl_blender.py#L2140)** — Launcher + Blender add-on lifecycle coordinator — ties the Qt host, keymap bridge and menu
  - `BlenderHost.launch(**kwargs)` *(static)* — Stand up the Qt host (QApplication + ``blender_widget`` + event pump) and return a
  - `BlenderHost.register(**kwargs)` *(static)* — Blender add-on / startup entry: stand up the host.
  - `BlenderHost.unregister()` *(static)* — Blender add-on teardown: remove the keymap items + bridge operator.
  - `BlenderHost.reload()` *(static)* — Reload the tentacle ecosystem in place and re-register — the Blender "Reload Scripts".

<a id="tcl_max"></a>
### `tcl_max.py`

- **[`class TclMax(MarkingMenu)`](tentacle/tentacle/tcl_max.py#L12)** — Marking Menu class overridden for use with Autodesk 3ds Max.
  - `TclMax.get_main_window(cls)` *(class)* — Get the 3DS MAX main window.
  - `TclMax.showEvent(self, event)`
  - `TclMax.hideEvent(self, event)`

<a id="tcl_maya"></a>
### `tcl_maya.py`

- **[`class TclMaya(MarkingMenu)`](tentacle/tentacle/tcl_maya.py#L11)** — Marking Menu class overridden for use with Autodesk Maya.

<a id="tentacle_installer"></a>
### `tentacle_installer.py`

Install, update or uninstall tentacle in a DCC -- one file, dropped in, no administrator rights.

- [`register()`](tentacle/tentacle/tentacle_installer.py#L2279) — Blender add-on entry: preferences UI, then finish any pending verb / install / launch.
- [`unregister()`](tentacle/tentacle/tentacle_installer.py#L2285) — Blender add-on teardown.
- [`onMayaDroppedPythonFile(*_args)`](tentacle/tentacle/tentacle_installer.py#L2291) — Maya drop hook: first drop installs and launches;
- **[`class TentacleInstaller`](tentacle/tentacle/tentacle_installer.py#L94)** — Provision tentacle into the host's per-user import dir, launch it, update or remove it.
  - `TentacleInstaller.host()` *(static)* — ``"blender"`` / ``"maya"`` for the DCC this interpreter is embedded in, else None.
  - `TentacleInstaller.headless(host)` *(static)* — True with no UI to report into (``blender --background``, ``mayapy`` / ``maya -batch``).
  - `TentacleInstaller.loaded()` *(static)* — True once our code is imported in this process -- its extension modules are then
  - `TentacleInstaller.specs(cls, host, fresh=True)` *(class)* — pip requirements for *host*: the package with its engine extra (+ Qt on a fresh Blender install).
  - `TentacleInstaller.python_exe(host)` *(static)* — The host's own interpreter (``sys.executable`` is the DCC binary in a GUI session).
  - `TentacleInstaller.maya_paths(cls, app_dir=None, version=None)` *(class)* — ``(module_root, mod_file)`` for this Maya -- both under the per-version prefs dir.
  - `TentacleInstaller.target_dir(cls, host)` *(class)* — Where the packages go: a per-user dir the host imports from at tail precedence.
  - `TentacleInstaller.is_installed(cls, host)` *(class)* — True when ``tentacle`` and the host's engine both resolve on ``sys.path``.
  - `TentacleInstaller.lock_path(cls, target)` *(class)*
  - `TentacleInstaller.manifest_path(cls, target)` *(class)*
  - `TentacleInstaller.read_manifest(cls, target)` *(class)* — The manifest dict (``{}`` when absent or unreadable).
  - `TentacleInstaller.write_manifest(cls, target, **updates)` *(class)* — Merge *updates* into the manifest.
  - `TentacleInstaller.installed_version(cls, target, name=None)` *(class)* — A dist's version as recorded in *target*'s dist-info (default: tentacletk), else None -- no import.
  - `TentacleInstaller.install(cls, host, target=None, python=None, upgrade=False)` *(class)* — Provision (or upgrade) the host's spec set and record it;
  - `TentacleInstaller.update(cls, host, target=None, python=None)` *(class)* — Upgrade the package (and whatever its floors now require);
  - `TentacleInstaller.uninstall(cls, host, target=None, python=None)` *(class)* — Remove what this installer put there;
  - `TentacleInstaller.request(cls, host, verb)` *(class)* — The one entry every surface calls with a verb;
  - `TentacleInstaller.provision(cls, host, upgrade=False, target=None, python=None, specs=None)` *(class)* — Install *specs* into *target*;
  - `TentacleInstaller.launch(cls, host)` *(class)* — Start the menu through tentacle's own host-aware entry (deferred as the host needs).
  - `TentacleInstaller.shutdown(cls)` *(class)* — Blender add-on teardown: tear down the keymap bridge if tentacle ever came up.
  - `TentacleInstaller.ensure_and_launch(cls, host=None)` *(class)* — The startup entry both hosts call: finish a pending verb, install if needed, launch.
  - `TentacleInstaller.write_maya_module(cls, source, app_dir=None, version=None)` *(class)* — Register the user-owned Maya module that re-runs this file at every start.
  - `TentacleInstaller.dropped(cls, source)` *(class)* — Maya drop hook body: first drop installs;
  - `TentacleInstaller.register_blender_ui(cls, addon_name)` *(class)* — Build and register the add-on preferences (version, Update, Uninstall) lazily --
  - `TentacleInstaller.unregister_blender_ui(cls)` *(class)*
  - `TentacleInstaller.main(cls, argv=None)` *(class)* — ``[install|update|uninstall]`` from a plain ``mayapy`` / ``blender --background`` run.
