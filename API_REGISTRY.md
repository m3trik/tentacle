# tentacle — API Registry

_Auto-generated. Do not edit by hand. Refresh via `m3trik/scripts/generate_api_registry.py`._

## Index

- [`__init__.py`](#__init__)
- [`slots/_animation.py`](#slots--_animation) — Text the animation panel's Maya and Blender forks say identically.
- [`slots/_slots.py`](#slots--_slots)
- [`slots/_uv.py`](#slots--_uv) — Behavior shared by the Maya and Blender UV panels.
- [`slots/blender/_slots_blender.py`](#slots--blender--_slots_blender)
- [`slots/blender/animation.py`](#slots--blender--animation)
- [`slots/blender/blender.py`](#slots--blender--blender)
- [`slots/blender/uv.py`](#slots--blender--uv)
- [`slots/cameras.py`](#slots--cameras) — Cameras: one Slots class for both hosts.
- [`slots/crease.py`](#slots--crease) — Crease: one Slots class for both hosts.
- [`slots/deformation.py`](#slots--deformation) — Deformation: one Slots class for both hosts.
- [`slots/display.py`](#slots--display) — Display: one Slots class for both hosts.
- [`slots/duplicate.py`](#slots--duplicate) — Duplicate: one Slots class for both hosts.
- [`slots/edit.py`](#slots--edit) — Edit: one Slots class for both hosts.
- [`slots/editors.py`](#slots--editors) — Editors: the editor buttons and the All Editors list, one Slots class for both hosts.
- [`slots/hud.py`](#slots--hud) — HUD: one Slots class for both hosts.
- [`slots/lighting.py`](#slots--lighting) — Lighting: one Slots class for both hosts.
- [`slots/main.py`](#slots--main) — Main: the start menu hub and its Workspace tab, one Slots class for both hosts.
- [`slots/materials.py`](#slots--materials) — Materials: one Slots class for both hosts.
- [`slots/maya/_slots_maya.py`](#slots--maya--_slots_maya)
- [`slots/maya/animation.py`](#slots--maya--animation)
- [`slots/maya/arnold.py`](#slots--maya--arnold)
- [`slots/maya/cache.py`](#slots--maya--cache)
- [`slots/maya/constrain.py`](#slots--maya--constrain)
- [`slots/maya/control.py`](#slots--maya--control)
- [`slots/maya/curves.py`](#slots--maya--curves)
- [`slots/maya/deform.py`](#slots--maya--deform)
- [`slots/maya/edit_mesh.py`](#slots--maya--edit_mesh)
- [`slots/maya/effects.py`](#slots--maya--effects)
- [`slots/maya/fields_solvers.py`](#slots--maya--fields_solvers)
- [`slots/maya/fluids.py`](#slots--maya--fluids)
- [`slots/maya/generate.py`](#slots--maya--generate)
- [`slots/maya/help.py`](#slots--maya--help)
- [`slots/maya/key.py`](#slots--maya--key)
- [`slots/maya/lighting_shading.py`](#slots--maya--lighting_shading)
- [`slots/maya/mash.py`](#slots--maya--mash)
- [`slots/maya/mesh.py`](#slots--maya--mesh)
- [`slots/maya/mesh_display.py`](#slots--maya--mesh_display)
- [`slots/maya/mesh_tools.py`](#slots--maya--mesh_tools)
- [`slots/maya/ncloth.py`](#slots--maya--ncloth)
- [`slots/maya/nconstraint.py`](#slots--maya--nconstraint)
- [`slots/maya/nhair.py`](#slots--maya--nhair)
- [`slots/maya/nparticles.py`](#slots--maya--nparticles)
- [`slots/maya/playback.py`](#slots--maya--playback)
- [`slots/maya/render.py`](#slots--maya--render)
- [`slots/maya/select.py`](#slots--maya--select)
- [`slots/maya/skeleton.py`](#slots--maya--skeleton)
- [`slots/maya/skin.py`](#slots--maya--skin)
- [`slots/maya/stereo.py`](#slots--maya--stereo)
- [`slots/maya/surfaces.py`](#slots--maya--surfaces)
- [`slots/maya/texturing.py`](#slots--maya--texturing)
- [`slots/maya/toon.py`](#slots--maya--toon)
- [`slots/maya/uv.py`](#slots--maya--uv)
- [`slots/maya/visualize.py`](#slots--maya--visualize)
- [`slots/maya/windows.py`](#slots--maya--windows)
- [`slots/normals.py`](#slots--normals) — Normals: one Slots class for both hosts.
- [`slots/nurbs.py`](#slots--nurbs) — NURBS: one Slots class for both hosts.
- [`slots/pivot.py`](#slots--pivot) — Pivot: one Slots class for both hosts.
- [`slots/polygons.py`](#slots--polygons) — Polygons: one Slots class for both hosts.
- [`slots/preferences.py`](#slots--preferences) — Preferences: one Slots class for both hosts.
- [`slots/rendering.py`](#slots--rendering) — Rendering: one Slots class for both hosts.
- [`slots/rigging.py`](#slots--rigging) — Rigging: one Slots class for both hosts.
- [`slots/scene.py`](#slots--scene) — Scene: one Slots class for both hosts.
- [`slots/selection.py`](#slots--selection) — Selection: one Slots class for both hosts.
- [`slots/settings.py`](#slots--settings) — Settings: one Slots class for both hosts.
- [`slots/subdivision.py`](#slots--subdivision) — Subdivision: one Slots class for both hosts.
- [`slots/symmetry.py`](#slots--symmetry) — Symmetry: one Slots class for both hosts.
- [`slots/tools/__init__.py`](#slots--tools--__init__) — Each shared tool's one Slots class, paired by name with its ``ui/tools/<tool>.ui``
- [`slots/tools/_app_bridge/host_bridge.py`](#slots--tools--_app_bridge--host_bridge) — The app-bridge panels' one base, shared by both hosts.
- [`slots/tools/_blendshape_animator/sort_item.py`](#slots--tools--_blendshape_animator--sort_item) — A tween-tree row that sorts its numeric columns by number.
- [`slots/tools/_channels/attribute_form.py`](#slots--tools--_channels--attribute_form) — The Create Attribute popup: a one-shot form over the host's attribute types.
- [`slots/tools/_channels/enum_cell.py`](#slots--tools--_channels--enum_cell) — The value cell of an enum attribute: its labels in a combobox, plus Rename /
- [`slots/tools/_channels/inline_rename.py`](#slots--tools--_channels--inline_rename) — Rename the panel's target in place: the target field, and the footer in
- [`slots/tools/_hierarchy_sync/controller.py`](#slots--tools--_hierarchy_sync--controller) — The Hierarchy Sync panel's state: the reference path, the paths the user
- [`slots/tools/_hierarchy_sync/tree_matcher.py`](#slots--tools--_hierarchy_sync--tree_matcher) — Find the Hierarchy Sync trees' items by the hierarchy paths a diff names.
- [`slots/tools/_hierarchy_sync/tree_renderer.py`](#slots--tools--_hierarchy_sync--tree_renderer) — The Hierarchy Sync trees: filling them, the diff's colours, the ignored
- [`slots/tools/_reference_manager/controller.py`](#slots--tools--_reference_manager--controller) — The Reference Manager panel's controller: the browsed workspace, the table
- [`slots/tools/_reference_manager/listing.py`](#slots--tools--_reference_manager--listing) — The Reference Manager's listing rules: how a scene file reads as a row and
- [`slots/tools/_reference_manager/references.py`](#slots--tools--_reference_manager--references) — The Reference Manager's reference actions: a row's reference and display
- [`slots/tools/_reference_manager/scene_files.py`](#slots--tools--_reference_manager--scene_files) — The Reference Manager's scene files: open / close / save / rename / delete, the
- [`slots/tools/_reference_manager/workspaces.py`](#slots--tools--_reference_manager--workspaces) — The Reference Manager's workspace browser: the Root Directory, the workspace
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
- [`slots/tools/_shot_sequencer/clip_menu.py`](#slots--tools--_shot_sequencer--clip_menu) — Clip context menus and clip-level key operations.
- [`slots/tools/_shot_sequencer/clip_motion.py`](#slots--tools--_shot_sequencer--clip_motion) — Clip and key motion for the Shot Sequencer panel: moving and resizing clips,
- [`slots/tools/_shot_sequencer/controller.py`](#slots--tools--_shot_sequencer--controller) — The Shot Sequencer panel's controller: :class:`ShotSequencerController`.
- [`slots/tools/_shot_sequencer/gap_manager.py`](#slots--tools--_shot_sequencer--gap_manager) — Gap and range-highlight handlers for the Shot Sequencer controller.
- [`slots/tools/_shot_sequencer/key_menu.py`](#slots--tools--_shot_sequencer--key_menu) — Key context menus and the edits run over a key selection, for the Shot
- [`slots/tools/_shot_sequencer/marker_manager.py`](#slots--tools--_shot_sequencer--marker_manager) — Marker persistence for the shot sequencer controller.
- [`slots/tools/_shot_sequencer/scene_callbacks.py`](#slots--tools--_shot_sequencer--scene_callbacks) — Scene events for the shot sequencer: undo/redo, key edits, time changes.
- [`slots/tools/_shot_sequencer/scene_selection.py`](#slots--tools--_shot_sequencer--scene_selection) — Tracks and the scene selection.
- [`slots/tools/_shot_sequencer/shot_edit_dialog.py`](#slots--tools--_shot_sequencer--shot_edit_dialog) — The Shot Sequencer's small shot dialog: :class:`ShotEditDialog`.
- [`slots/tools/_shot_sequencer/shot_lane.py`](#slots--tools--_shot_sequencer--shot_lane) — The shot lane: its context menu and the shot structure edits.
- [`slots/tools/_shot_sequencer/shot_layer.py`](#slots--tools--_shot_sequencer--shot_layer) — The shot layer: the Shot Sequencer's shots on uitk's timeline.
- [`slots/tools/_shot_sequencer/shot_nav.py`](#slots--tools--_shot_sequencer--shot_nav) — Shot navigation and combobox synchronization.
- [`slots/tools/_shot_sequencer/transport.py`](#slots--tools--_shot_sequencer--transport) — Transport: the playhead, audio scrub and the transport row.
- [`slots/tools/_shot_sequencer/undo_ledger.py`](#slots--tools--_shot_sequencer--undo_ledger) — The shot sequencer's undo ledger.
- [`slots/tools/_shot_sequencer/widget_sync.py`](#slots--tools--_shot_sequencer--widget_sync) — Widget sync: rebuilding the sequencer from the scene.
- [`slots/tools/_shots/controller.py`](#slots--tools--_shots--controller) — The Shots panel's controller: the scene's shot settings, the selected shot's
- [`slots/tools/_texture_combine/transfer_mode.py`](#slots--tools--_texture_combine--transfer_mode) — The Texture Combine panel's Transfer mode: UVs or textures, source -> targets.
- [`slots/tools/_unity_bridge/_unity_panel.py`](#slots--tools--_unity_bridge--_unity_panel) — What every Unity panel shares: the 'Unity Project' row, the Editor combo, script management.
- [`slots/tools/arnold_bridge.py`](#slots--tools--arnold_bridge) — Arnold Preview Shader: add or remove the Arnold preview network beside each
- [`slots/tools/articulated_rig.py`](#slots--tools--articulated_rig) — Articulated Rig: rig a prop of rigid parts on hinges, swivels, balls and
- [`slots/tools/audio_clips.py`](#slots--tools--audio_clips) — Audio Clips: the scene's audio files, placed on the timeline.
- [`slots/tools/bevel.py`](#slots--tools--bevel) — Bevel: chamfer the selected polygon edges, with a live preview.
- [`slots/tools/blender_bridge.py`](#slots--tools--blender_bridge) — Blender Bridge: send the selection to a fresh Blender through an import
- [`slots/tools/blendshape_animator.py`](#slots--tools--blendshape_animator) — Blendshape Animator: build a morph between two meshes, add in-between
- [`slots/tools/bridge.py`](#slots--tools--bridge) — Bridge: connect two open edge loops with new polygon faces, with a live preview.
- [`slots/tools/calculator.py`](#slots--tools--calculator) — Calculator: expressions, length units, and the scene's frame-rate helpers.
- [`slots/tools/channels.py`](#slots--tools--channels) — Channels: the selected objects' attributes in one editable table.
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
- [`slots/tools/hierarchy_sync.py`](#slots--tools--hierarchy_sync) — Hierarchy Sync: diff the scene's hierarchy against a reference file, then
- [`slots/tools/image_to_plane.py`](#slots--tools--image_to_plane) — Image to Plane: batch-create textured planes from image files.
- [`slots/tools/image_tracer.py`](#slots--tools--image_tracer) — Image Tracer: trace a raster image's contours into curves, then fill them
- [`slots/tools/key_stash.py`](#slots--tools--key_stash) — Key Stash: park keys out of the working animation as clips, then preview or
- [`slots/tools/light_rig.py`](#slots--tools--light_rig) — Light Rigs: save the scene's lights as named rigs, swap between them and
- [`slots/tools/lightmap_baker.py`](#slots--tools--lightmap_baker) — Lightmap Baker: bake the scene's lighting into lightmaps the engine reads.
- [`slots/tools/marmoset_bridge.py`](#slots--tools--marmoset_bridge) — Marmoset Bridge: send the selection to Marmoset Toolbag through a template.
- [`slots/tools/mat_updater.py`](#slots--tools--mat_updater) — Material Updater: rework scene materials for a target workflow preset,
- [`slots/tools/maya_bridge.py`](#slots--tools--maya_bridge) — Maya Bridge: send the selection to a fresh Maya through an import template.
- [`slots/tools/mirror.py`](#slots--tools--mirror) — Mirror: mirror the selected meshes across an axis, with a live preview.
- [`slots/tools/naming.py`](#slots--tools--naming) — Naming: batch find / rename / convert-case / strip-chars / suffix-by-location /
- [`slots/tools/reference_manager.py`](#slots--tools--reference_manager) — Reference Manager: a workspace scene-file manager -- browse a project's scene
- [`slots/tools/render_effects.py`](#slots--tools--render_effects) — Render Effects: key per-object opacity fades and highlight pulses for export.
- [`slots/tools/rizom_bridge.py`](#slots--tools--rizom_bridge) — RizomUV Bridge: unwrap or pack the selection in RizomUV with a Lua preset and
- [`slots/tools/scene_exporter.py`](#slots--tools--scene_exporter) — Scene Exporter: batch-export the scene through its task/check pipeline.
- [`slots/tools/shader_templates.py`](#slots--tools--shader_templates) — Shader Templates: save a material's shader network as a reusable template
- [`slots/tools/shadow_rig.py`](#slots--tools--shadow_rig) — Shadow Rig: a ground plane carrying the targets' projected shadow, built for
- [`slots/tools/shell_xform.py`](#slots--tools--shell_xform) — Shell Xform: move, flip, rotate, straighten, mirror, distribute, align and
- [`slots/tools/shot_manifest.py`](#slots--tools--shot_manifest) — Shot Manifest: a shot sheet checked against the scene, and the shots built from it.
- [`slots/tools/shot_sequencer.py`](#slots--tools--shot_sequencer) — Shot Sequencer: the scene's shots on a timeline -- objects as tracks, keys as
- [`slots/tools/shots.py`](#slots--tools--shots) — Shots: the scene's shot settings, the selected shot's fields and edits, and
- [`slots/tools/smart_bake.py`](#slots--tools--smart_bake) — Smart Bake: bake what drives the scene's animation to keys, reversibly.
- [`slots/tools/snap.py`](#slots--tools--snap) — Snap: vertices to a target surface, to the closest target vertex, or to the grid.
- [`slots/tools/substance_bridge.py`](#slots--tools--substance_bridge) — Substance Bridge: send the selection to Substance Painter through a template.
- [`slots/tools/telescope_rig.py`](#slots--tools--telescope_rig) — Telescope Rig: nested segments that extend and retract between a base and an
- [`slots/tools/texture_combine.py`](#slots--tools--texture_combine) — Texture Combine: several materials into one atlas and one material, in
- [`slots/tools/texture_path_editor.py`](#slots--tools--texture_path_editor) — Texture Path Editor: inspect and fix the scene's texture paths.
- [`slots/tools/tube_rig.py`](#slots--tools--tube_rig) — Tube Rig: rig a tube-shaped mesh (hose, cable, piston, tail) with joints,
- [`slots/tools/unity_bridge.py`](#slots--tools--unity_bridge) — Unity Bridge: export the selection and copy the FBX into a Unity project's Assets/.
- [`slots/tools/wheel_rig.py`](#slots--tools--wheel_rig) — Wheel Rig: wheels that roll as their driver (control) moves, sized by wheel
- [`slots/tools/workspace_editor.py`](#slots--tools--workspace_editor) — Workspace Editor: the minimal take on Maya's File ▸ Project Window -- one
- [`slots/tools/workspace_map.py`](#slots--tools--workspace_map) — Workspace Map: browse a folder tree of project workspaces and switch the
- [`slots/transform.py`](#slots--transform) — Transform: one Slots class for both hosts.
- [`slots/utilities.py`](#slots--utilities) — Utilities: one Slots class for both hosts.
- [`tcl.py`](#tcl) — The host-agnostic entry point — one launcher snippet for every DCC.
- [`tcl_blender.py`](#tcl_blender) — Blender entry point for tentacle's Qt marking menu — host + keymap bridge + launcher in one.
- [`tcl_max.py`](#tcl_max)
- [`tcl_maya.py`](#tcl_maya)
- [`tentacle_installer.py`](#tentacle_installer) — Install, update or uninstall tentacle in a DCC -- one file, dropped in, no administrator rights.

---

<a id="__init__"></a>
### `__init__.py`

- [`greeting(string, outputToConsole=True)`](tentacle/tentacle/__init__.py#L58) — Format a string using preset variables.
- [`DEFAULT_INCLUDE`](tentacle/tentacle/__init__.py#L11) — constant
- [`MOVED_NAMES`](tentacle/tentacle/__init__.py#L30) — constant

<a id="slots--_animation"></a>
### `slots/_animation.py`

Text the animation panel's Maya and Blender forks say identically.

- **[`class AnimationMixin`](tentacle/tentacle/slots/_animation.py#L46)** — Shared tooltip text and key-edit wrapper for ``slots/{maya,blender}/animation.py``.
  - `AnimationMixin.list000_init(self, widget)` — Tools list: Sequencing / Repair / Bake / Stash / Playback / Info.

<a id="slots--_slots"></a>
### `slots/_slots.py`

- **[`class Slots(QtCore.QObject)`](tentacle/tentacle/slots/_slots.py#L9)** — Provides methods that can be triggered by widgets in the ui.
  - `Slots.tk(self)` *(property)* — The host toolkit (``mtk`` / ``btk``) the entry point set on the
  - `Slots.mirror_app_state(widget, seed=None) -> None` *(static)* — Declare that *widget*'s value mirrors live DCC state, optionally seeding it.
  - `Slots.require_selection(self, message=None)` — The selection, or ``None`` -- after a message box -- when it is empty.
  - `Slots.activate_tool(self, tool) -> bool` — Activate a viewport tool through the host toolkit and confirm it, or say
  - `Slots.run_operation(self, call, *args, empty=None, **kwargs)` — Call a host operation and report it: a refusal (``ValueError`` for a
  - `Slots.add_slot_widget(self, sublist, widget_class=None, **kwargs)` — Add a slot-wired widget as an ExpandableList sublist entry.
  - `Slots.gate_on_app(self, widget, resolve_spec) -> bool` — Gate *widget* on the :class:`pythontk.AppSpec` *resolve_spec* returns.
  - `Slots.recheck_app_gates(self) -> int` — Re-probe every gated app and re-present its widgets.
  - `Slots.toggle_camera_view(self)` — Toggle between the last two viewport-camera views in slot history.
  - `Slots.register_camera_view_toggle(self)` — Wire :meth:`toggle_camera_view` to its triggers.

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

- **[`class SlotsBlender(Slots)`](tentacle/tentacle/slots/blender/_slots_blender.py#L7)** — App specific methods inherited by all other Blender slot classes.
  - `SlotsBlender.selected_objects()` *(static)* — The current object selection: ``btk.CoreUtils.selected_objects`` (the
  - `SlotsBlender.active_object()` *(static)* — The active object (or ``None``): ``btk.CoreUtils.active_object`` (the
  - `SlotsBlender.effective_fps() -> float` *(static)* — The scene frame rate as the user understands it, ``fps / fps_base`` (an
  - `SlotsBlender.ensure_edit_mode(self, obj_type='MESH', select_mode=None)` — Put an object of ``obj_type`` into Edit Mode, optionally setting the mesh
  - `SlotsBlender.ensure_object_mode(self)` — Leave Edit (or any other) Mode before object-level work:
  - `SlotsBlender.set_viewport_tool(self, tool_id, label=None, edit_type=None)` — Activate a builtin viewport tool by idname: ``btk.UiUtils.set_tool``,
  - `SlotsBlender.resolve_op(op_path)` *(static)* — The ``bpy.ops`` callable at a dotted path (``"wm.link"``), or None when the
  - `SlotsBlender.invoke_op(self, op_path, **kwargs)` — Invoke an operator's dialog by dotted path (``INVOKE_DEFAULT``):
  - `SlotsBlender.transfer_from_active(self, data_type, **kwargs)` — Run native Data Transfer from the active mesh to the other selected meshes

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
  - `AnimationSlots.b000(self)` — Open Shot Sequencer — tentacle's shared tool (slots/tools/shot_sequencer.py): shots
  - `AnimationSlots.b004(self)` — Open Shot Manifest — the shared tool: CSV-driven scene assembly over linked
  - `AnimationSlots.b006(self)` — Open Key Stash — the shared tool over ``btk.KeyStash``: park keys out of the working

<a id="slots--blender--blender"></a>
### `slots/blender/blender.py`

- **[`class BlenderSlots(SlotsBlender)`](tentacle/tentacle/slots/blender/blender.py#L6)** — Base-name anchor for the Blender both-button chord menu (``blender#startmenu``).

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
  - `UvSlots.b032(self)` — RizomUV Bridge — the shared tool (round-trip Lua presets + one-way send).
  - `UvSlots.b033(self)` — Open the Shell Xform panel — the ``More..`` button in the Transform group.

<a id="slots--cameras"></a>
### `slots/cameras.py`

Cameras: one Slots class for both hosts.

- **[`class CamerasSlots(Slots)`](tentacle/tentacle/slots/cameras.py#L20)**
  - `CamerasSlots.list000_init(self, widget)` — Initialize the Camera Options list (rebuilt on every show).
  - `CamerasSlots.list000(self, item)` — Camera Options list: run the leaf's operation.
  - `CamerasSlots.b000(self)` — Cameras: Back View
  - `CamerasSlots.b001(self)` — Cameras: Top View
  - `CamerasSlots.b002(self)` — Cameras: Right View (Maya's 'side' camera).
  - `CamerasSlots.b003(self)` — Cameras: Left View
  - `CamerasSlots.b004(self)` — Cameras: Perspective View
  - `CamerasSlots.b005(self)` — Cameras: Front View
  - `CamerasSlots.b006(self)` — Cameras: Bottom View
  - `CamerasSlots.b007(self)` — Cameras: Align View.
  - `CamerasSlots.b010(self)` — Camera: Dolly.
  - `CamerasSlots.b011(self)` — Camera: Roll.
  - `CamerasSlots.b012(self)` — Camera: Truck.
  - `CamerasSlots.b013(self)` — Camera: Orbit.

<a id="slots--crease"></a>
### `slots/crease.py`

Crease: one Slots class for both hosts.

- **[`class CreaseSlots(Slots)`](tentacle/tentacle/slots/crease.py#L16)**
  - `CreaseSlots.tb000_init(self, widget)` — Initialize Crease: the amount and the optional smoothing angle.
  - `CreaseSlots.tb000(self, widget)` — Crease: crease the selected edges (subdivision sharpness), softening or
  - `CreaseSlots.b002(self, widget)` — Transfer Crease Edges: from the first selected (Maya) or active (Blender)

<a id="slots--deformation"></a>
### `slots/deformation.py`

Deformation: one Slots class for both hosts.

- **[`class DeformationSlots(Slots)`](tentacle/tentacle/slots/deformation.py#L14)**
  - `DeformationSlots.tb001_init(self, widget)` — Initialize the Curtain Generator launcher.
  - `DeformationSlots.tb001(self, widget)` — Curtain Generator: open the shared Curtain tool.

<a id="slots--display"></a>
### `slots/display.py`

Display: one Slots class for both hosts.

- **[`class DisplaySlots(Slots)`](tentacle/tentacle/slots/display.py#L15)**
  - `DisplaySlots.header_init(self, widget)` — Header menu: the submenu's Display expandable list -- hover a row to
  - `DisplaySlots.list000_init(self, widget)` — Initialize the Display expandable list (categories -> actions).
  - `DisplaySlots.list000(self, item)` — Run a Display row and report the state it left.
  - `DisplaySlots.b013(self)` — Exploded View: open the Exploded View panel.
  - `DisplaySlots.b014(self)` — Color ID: open the Color ID panel (color-code objects by ID).

<a id="slots--duplicate"></a>
### `slots/duplicate.py`

Duplicate: one Slots class for both hosts.

- **[`class DuplicateSlots(Slots)`](tentacle/tentacle/slots/duplicate.py#L14)**
  - `DuplicateSlots.header_init(self, widget)` — Header menu: the Mirror / Duplicate Linear / Radial / Grid launchers.
  - `DuplicateSlots.tb002_init(self, widget)` — Initialize Auto Instance: configure the option-box menu.
  - `DuplicateSlots.tb002(self, widget)` — Auto Instance: convert geometrically identical meshes into instances
  - `DuplicateSlots.tb000_init(self, widget)`
  - `DuplicateSlots.tb000(self, widget)` — Convert to Instances: the other selected objects become instances of
  - `DuplicateSlots.tb001_init(self, widget)`
  - `DuplicateSlots.tb001(self, widget)` — Select Instanced Objects: the selection and its instances, or every
  - `DuplicateSlots.b005(self)` — Uninstance Selected Objects: each gets its own copy of the shared
  - `DuplicateSlots.b000(self)` — Mirror: open the Mirror tool window.
  - `DuplicateSlots.b006(self)` — Duplicate Linear
  - `DuplicateSlots.b007(self)` — Duplicate Radial
  - `DuplicateSlots.b008(self)` — Duplicate Grid

<a id="slots--edit"></a>
### `slots/edit.py`

Edit: one Slots class for both hosts.

- **[`class EditSlots(Slots)`](tentacle/tentacle/slots/edit.py#L21)**
  - `EditSlots.header_init(self, widget)` — Header menu: the submenu's Create / Convert lists, Channels and Cut On Axis.
  - `EditSlots.b_channels(self)` — Channels: open the Channels panel.
  - `EditSlots.b000(self)` — Cut On Axis: open the Cut On Axis tool (slice objects along an axis plane).
  - `EditSlots.mesh_cleanup_tooltip(self)` — Rich tooltip for the Mesh Cleanup button (``tb000``).
  - `EditSlots.tb000_init(self, widget)` — Initialize Mesh Cleanup.
  - `EditSlots.tb000(self, widget)` — Mesh Cleanup: repair the problem geometry, or (Select) select it.
  - `EditSlots.cleanup_popup_html(header, rows)` *(static)* — Minimal HTML for the Mesh Cleanup popup -- glanceable, one fact per line.
  - `EditSlots.cleanup_console_report(self, title, lines)` — The detailed Mesh Cleanup report, to the host's console (Maya's Script
  - `EditSlots.report_cleanup_failure(self, scope, mode, error)` — Report a failed Mesh Cleanup on both channels: the console and the popup.
  - `EditSlots.tb001_init(self, widget)` — Initialize Delete History: construction history is Maya's (the
  - `EditSlots.tb001(self, widget)` — Delete History: on the scope's objects, plus the option box's scene cleanups.
  - `EditSlots.tb005_init(self, widget)` — Initialize Optimize: Blender's purge of unused data-blocks (the ``.ui``
  - `EditSlots.tb005(self, widget)` — Optimize: purge the data-blocks nothing uses.
  - `EditSlots.tb002(self, widget)` — Delete: the selected components, or the selected objects whole.
  - `EditSlots.tb004_init(self, widget)` — Initialize Lock / Unlock: the combo names both states, and its text is
  - `EditSlots.tb004(self, widget)` — Lock / Unlock: protect objects from accidental edits.
  - `EditSlots.list000_init(self, widget)` — Initialize Create: the host's primitives by category, then its controls.
  - `EditSlots.list000(self, item)` — Create the picked primitive, helper, light or control;
  - `EditSlots.list001_init(self, widget)` — Initialize Convert: the host's conversions.
  - `EditSlots.list001(self, item)` — Convert the selection: the picked conversion.
  - `EditSlots.cmb000_init(self, widget)` — Initialize Transfer: the host's transfers.
  - `EditSlots.cmb000(self, index, widget)` — Transfer: from the source (Maya: the first selected;

<a id="slots--editors"></a>
### `slots/editors.py`

Editors: the editor buttons and the All Editors list, one Slots class for both hosts.

- **[`class EditorsSlots(Slots)`](tentacle/tentacle/slots/editors.py#L22)**
  - `EditorsSlots.list000_init(self, widget)` — Fill the editors list: the host's categories, each a flyout of the
  - `EditorsSlots.list000(self, item)` — Open the picked editor;
  - `EditorsSlots.b000(self)` — Attributes: the Attribute Editor (Blender: the Properties editor).
  - `EditorsSlots.b001(self)` — Outliner.
  - `EditorsSlots.b002(self)` — Tool: the tool settings (Blender: the Properties editor).
  - `EditorsSlots.b003(self)` — Layers: the Layer Editor (Blender: the Outliner, where collections live).
  - `EditorsSlots.b004(self)` — Channels: the Channel Box (Blender: the Properties editor).
  - `EditorsSlots.b005(self)` — Node Editor (Blender: the Shader Editor).
  - `EditorsSlots.b006(self)` — Dependency Graph: the Hypergraph hierarchy (Maya).
  - `EditorsSlots.b014(self)` — Geometry Nodes (Blender).
  - `EditorsSlots.b015(self)` — UV Editor (Blender).
  - `EditorsSlots.b016(self)` — Image Editor (Blender).
  - `EditorsSlots.b017(self)` — Graph Editor (Blender).
  - `EditorsSlots.b018(self)` — Text Editor (Blender).
  - `EditorsSlots.b007(self)` — Status Line (Maya).
  - `EditorsSlots.b008(self)` — Shelf (Maya).
  - `EditorsSlots.b009(self)` — Time & Range: the timeline (Maya: the Time and Range Sliders, hidden
  - `EditorsSlots.b010(self)` — Script Output: the dockable console mirroring the session's output.
  - `EditorsSlots.b011(self)` — Cmd Line: the command line (Blender: a docked Python Console).
  - `EditorsSlots.b012(self)` — Help Line (Maya).
  - `EditorsSlots.b013(self)` — Tool Box (Maya).

<a id="slots--hud"></a>
### `slots/hud.py`

HUD: one Slots class for both hosts.

- **[`class HudSlots(Slots)`](tentacle/tentacle/slots/hud.py#L18)** — Scene and selection information, shown while the marking-menu key is held.
  - `HudSlots.hudTextEdit_init(self, widget) -> None` — The HUD is a display composed afresh on every show -- never persisted.
  - `HudSlots.request_hud_build(self) -> None` — Start a new HUD build;
  - `HudSlots.construct_hud(self) -> None`
  - `HudSlots.insert_scene_status(self, hud, status) -> None` — The scene's state: a newer release, symmetry, the transform
  - `HudSlots.insert_selection_info(self, hud, summary) -> None` — The selected objects: how many, each name and type (up to
  - `HudSlots.insert_component_info(self, hud, summary) -> None` — Selected / total components of the type being edited.
  - `HudSlots.evaluate_warnings(self) -> list` — The :attr:`WARNING_DEFS` that are opted into and fire now, each with
  - `HudSlots.insert_warning_icons(self, hud, warnings) -> None` — One row of coloured badges, one per active warning.
  - `HudSlots.insert_warning_details(self, hud, warnings) -> None` — One detail line per active warning.
  - `HudSlots.insert_prev_command(self, hud, method) -> None` — The last-used command as one length-capped line.

<a id="slots--lighting"></a>
### `slots/lighting.py`

Lighting: one Slots class for both hosts.

- **[`class LightingSlots(Slots)`](tentacle/tentacle/slots/lighting.py#L14)**
  - `LightingSlots.b000(self)` — Launch the HDR Manager (the scene's world / sky-dome HDRI).
  - `LightingSlots.b001(self)` — Launch the Lightmap Baker (bake scene lighting for game engines).
  - `LightingSlots.b002(self)` — Launch Light Rigs: save, swap and restore named light rigs (Maya).
  - `LightingSlots.tb000_init(self, widget)` — Lights From Geometry Init
  - `LightingSlots.tb000(self, widget)` — Create real area lights from the selected fixture geometry.

<a id="slots--main"></a>
### `slots/main.py`

Main: the start menu hub and its Workspace tab, one Slots class for both hosts.

- **[`class MainSlots(Slots)`](tentacle/tentacle/slots/main.py#L29)**
  - `MainSlots.list000_init(self, widget)` — Initialize the Workspace tab.
  - `MainSlots.list000(self, item)` — Workspace tab dispatch: the editing actions, recent-workspace selection,

<a id="slots--materials"></a>
### `slots/materials.py`

Materials: one Slots class for both hosts.

- **[`class MaterialsSlots(Slots)`](tentacle/tentacle/slots/materials.py#L59)** — The material table, the current material, the header menu, the submenu's
  - `MaterialsSlots.tbl000_init(self, widget)` — The material table: built once, re-wired and refilled on every show.
  - `MaterialsSlots.b028(self, widget=None)` — Assign the highlighted material to the selection.
  - `MaterialsSlots.b029(self, widget=None)` — Select what uses the highlighted material, as assigned.
  - `MaterialsSlots.b030(self, widget=None)` — Select every object using the highlighted material.
  - `MaterialsSlots.b031(self, widget=None)` — Narrow the selection to what uses the highlighted material.
  - `MaterialsSlots.b032(self, widget=None)` — Merge the highlighted duplicates into the materials they duplicate.
  - `MaterialsSlots.lbl002(self, widget=None)` — Delete the highlighted materials.
  - `MaterialsSlots.lbl004(self, widget=None)` — Show Attributes: the current material in the host's attribute view
  - `MaterialsSlots.lbl006(self, widget=None)` — Open in Editor: graph the current material in the shader editor.
  - `MaterialsSlots.txt000_init(self, widget)` — The filter field: hides the rows whose name does not hold its text.
  - `MaterialsSlots.b006_init(self, widget)`
  - `MaterialsSlots.b006(self, widget=None)` — New material onto the selection (:meth:`_new_mat`);
  - `MaterialsSlots.b004(self, widget=None)` — Assign Random: a new random-colored material onto the selection;
  - `MaterialsSlots.b033(self, widget=None)` — Select the objects carrying no material.
  - `MaterialsSlots.b014(self, widget=None)` — Remove Duplicate Materials: merge every duplicate in the scene into
  - `MaterialsSlots.b015(self, widget=None)` — Delete All Unused Materials (one Undo;
  - `MaterialsSlots.header_init(self, widget)` — The header: a refresh button, and a menu of the Tools list then
  - `MaterialsSlots.list000_init(self, widget)` — Assign list: the current material at the root, then New, Random and
  - `MaterialsSlots.list000(self, item)` — Dispatch an Assign list release.
  - `MaterialsSlots.select_by_mat(self, shell=False, in_selection=False, get_first=False, add=False, unassigned=False)` — Select the geometry carrying the current material.
  - `MaterialsSlots.b003(self, widget=None)` — Get + Select (submenu): adopt the selection's material, then select its users.
  - `MaterialsSlots.list001_init(self, widget)` — Tools list: Setup / Materials / Texture Maps / External / Utilities.
  - `MaterialsSlots.list001(self, item)` — Dispatch a Tools-list selection to its slot method.
  - `MaterialsSlots.b007(self, widget=None)` — Shader Editor: the host's (Maya: the Hypershade;
  - `MaterialsSlots.b013(self, widget=None)` — Reload Scene Textures, then reset the viewport.
  - `MaterialsSlots.tb001_init(self, widget)` — Get Material Info: its option box.
  - `MaterialsSlots.tb001(self, widget)` — Get Material Info: render a formatted report to the viewer dialog.
  - `MaterialsSlots.tb002_init(self, widget)` — Enable Viewport Opacity (Maya: its Tools row is ``requires="maya"``):
  - `MaterialsSlots.tb002(self, widget)` — Enable Viewport Opacity: wire opacity maps for the chosen scope.
  - `MaterialsSlots.b009(self, widget=None)` — Game Shader.
  - `MaterialsSlots.b010(self, widget=None)` — Texture Path Editor.
  - `MaterialsSlots.b011(self, widget=None)` — Shader Templates.
  - `MaterialsSlots.b018(self, widget=None)` — Mat Updater: reprocess scene materials' textures and re-wire them.
  - `MaterialsSlots.b019(self, widget=None)` — Marmoset Bridge.
  - `MaterialsSlots.b020(self, widget=None)` — Substance Bridge.
  - `MaterialsSlots.b021(self, widget=None)` — Image to Plane.
  - `MaterialsSlots.b026(self, widget=None)` — Arnold Preview Shader (Maya: a parallel aiStandardSurface for in-Maya
  - `MaterialsSlots.b027(self, widget=None)` — Emissive Groups.
  - `MaterialsSlots.b008(self, widget=None)` — Map Packer.
  - `MaterialsSlots.b016(self, widget=None)` — Map Converter.
  - `MaterialsSlots.b022(self, widget=None)` — Map Compositor.
  - `MaterialsSlots.b023(self, widget=None)` — Metashape Workflow.
  - `MaterialsSlots.b024(self, widget=None)` — RealityCapture Workflow.
  - `MaterialsSlots.b025(self, widget=None)` — Brush Splat Workflow.

<a id="slots--maya--_slots_maya"></a>
### `slots/maya/_slots_maya.py`

- **[`class SlotsMaya(Slots)`](tentacle/tentacle/slots/maya/_slots_maya.py#L8)** — App specific methods inherited by all other app specific slot classes.
  - `SlotsMaya.require_selection(self, message=None, **kwargs)` — The current selection, or ``None`` -- after a message box -- when it is empty.

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

<a id="slots--maya--constrain"></a>
### `slots/maya/constrain.py`

- **[`class ConstrainSlots(SlotsMaya)`](tentacle/tentacle/slots/maya/constrain.py#L8)**

<a id="slots--maya--control"></a>
### `slots/maya/control.py`

- **[`class ControlSlots(SlotsMaya)`](tentacle/tentacle/slots/maya/control.py#L8)**

<a id="slots--maya--curves"></a>
### `slots/maya/curves.py`

- **[`class CurvesSlots(SlotsMaya)`](tentacle/tentacle/slots/maya/curves.py#L8)**

<a id="slots--maya--deform"></a>
### `slots/maya/deform.py`

- **[`class DeformSlots(SlotsMaya)`](tentacle/tentacle/slots/maya/deform.py#L8)**

<a id="slots--maya--edit_mesh"></a>
### `slots/maya/edit_mesh.py`

- **[`class EditMeshSlots(SlotsMaya)`](tentacle/tentacle/slots/maya/edit_mesh.py#L8)**

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

<a id="slots--maya--key"></a>
### `slots/maya/key.py`

- **[`class KeySlots(SlotsMaya)`](tentacle/tentacle/slots/maya/key.py#L8)**

<a id="slots--maya--lighting_shading"></a>
### `slots/maya/lighting_shading.py`

- **[`class LightingShadingSlots(SlotsMaya)`](tentacle/tentacle/slots/maya/lighting_shading.py#L8)**

<a id="slots--maya--mash"></a>
### `slots/maya/mash.py`

- **[`class MashSlots(SlotsMaya)`](tentacle/tentacle/slots/maya/mash.py#L8)**

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

<a id="slots--maya--playback"></a>
### `slots/maya/playback.py`

- **[`class PlaybackSlots(SlotsMaya)`](tentacle/tentacle/slots/maya/playback.py#L8)**

<a id="slots--maya--render"></a>
### `slots/maya/render.py`

- **[`class RenderSlots(SlotsMaya)`](tentacle/tentacle/slots/maya/render.py#L8)**

<a id="slots--maya--select"></a>
### `slots/maya/select.py`

- **[`class SelectSlots(SlotsMaya)`](tentacle/tentacle/slots/maya/select.py#L8)**

<a id="slots--maya--skeleton"></a>
### `slots/maya/skeleton.py`

- **[`class SkeletonSlots(SlotsMaya)`](tentacle/tentacle/slots/maya/skeleton.py#L8)**

<a id="slots--maya--skin"></a>
### `slots/maya/skin.py`

- **[`class SkinSlots(SlotsMaya)`](tentacle/tentacle/slots/maya/skin.py#L8)**

<a id="slots--maya--stereo"></a>
### `slots/maya/stereo.py`

- **[`class StereoSlots(SlotsMaya)`](tentacle/tentacle/slots/maya/stereo.py#L8)**

<a id="slots--maya--surfaces"></a>
### `slots/maya/surfaces.py`

- **[`class SurfacesSlots(SlotsMaya)`](tentacle/tentacle/slots/maya/surfaces.py#L8)**

<a id="slots--maya--texturing"></a>
### `slots/maya/texturing.py`

- **[`class TexturingSlots(SlotsMaya)`](tentacle/tentacle/slots/maya/texturing.py#L8)**

<a id="slots--maya--toon"></a>
### `slots/maya/toon.py`

- **[`class ToonSlots(SlotsMaya)`](tentacle/tentacle/slots/maya/toon.py#L8)**

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

<a id="slots--nurbs"></a>
### `slots/nurbs.py`

NURBS: one Slots class for both hosts.

- **[`class NurbsSlots(Slots)`](tentacle/tentacle/slots/nurbs.py#L23)**
  - `NurbsSlots.list000_init(self, widget)` — Initialize the Nurbs expandable list (root -> category -> curve action).
  - `NurbsSlots.list000(self, item)` — Run a Nurbs leaf: its curve action, or its viewport tool.
  - `NurbsSlots.b030(self)` — Extrude: sweep the selected profile curve along a path curve, or
  - `NurbsSlots.b056(self)` — Image Tracer
  - `NurbsSlots.b058(self)` — Curve to Tube
  - `NurbsSlots.tb000_init(self, widget)` — Initialize Revolve.
  - `NurbsSlots.tb000(self, widget)` — Revolve: sweep the selected profile curve around an axis into a surface.
  - `NurbsSlots.tb001_init(self, widget)` — Initialize Loft.
  - `NurbsSlots.tb001(self, widget)` — Loft: build a surface lofted across the selected profile curves.

<a id="slots--pivot"></a>
### `slots/pivot.py`

Pivot: one Slots class for both hosts.

- **[`class PivotSlots(Slots)`](tentacle/tentacle/slots/pivot.py#L17)**
  - `PivotSlots.tb000_init(self, widget)` — Initialize Reset Pivot.
  - `PivotSlots.tb000(self, widget)` — Reset Pivot: the selection's pivot position and/or orientation.
  - `PivotSlots.tb001_init(self, widget)` — Initialize Center Pivot.
  - `PivotSlots.tb001(self, widget)` — Center Pivot
  - `PivotSlots.b000(self)` — Center Pivot: Object
  - `PivotSlots.b001(self)` — Center Pivot: Component
  - `PivotSlots.b002(self, widget)` — Center Pivot: World
  - `PivotSlots.tb002_init(self, widget)` — Initialize Transfer Pivot.
  - `PivotSlots.tb002(self, widget)` — Transfer Pivot: from the source (Maya: the first selected;
  - `PivotSlots.tb003_init(self, widget)` — Initialize World-Aligned Pivot.
  - `PivotSlots.tb003(self, widget)` — World-Aligned Pivot: the manipulator (temporary) or the object pivot
  - `PivotSlots.b004(self)` — Bake Pivot: make the temporary pivot (Maya: the manipulator pivot;

<a id="slots--polygons"></a>
### `slots/polygons.py`

Polygons: one Slots class for both hosts.

- **[`class PolygonsSlots(Slots)`](tentacle/tentacle/slots/polygons.py#L18)**
  - `PolygonsSlots.header_init(self, widget)` — Initialize Header
  - `PolygonsSlots.tb000_init(self, widget)` — Initialize Merge Vertices
  - `PolygonsSlots.tb000(self, widget)` — Merge Vertices: the selected components, else every vertex of the
  - `PolygonsSlots.b005(self)` — Merge Vertices: Set Distance
  - `PolygonsSlots.tb002_init(self, widget)` — Initialize Separate
  - `PolygonsSlots.tb002(self, widget)` — Separate: split each selected mesh into its loose parts (or per material).
  - `PolygonsSlots.tb003_init(self, widget)` — Initialize Extrude
  - `PolygonsSlots.tb003(self, widget)` — Extrude the selected faces, edges or vertices.
  - `PolygonsSlots.tb004_init(self, widget)` — Initialize Combine
  - `PolygonsSlots.tb004(self, widget)` — Combine the selected meshes (optionally one mesh per material).
  - `PolygonsSlots.tb005_init(self, widget)` — Initialize Detach
  - `PolygonsSlots.tb005(self, widget)` — Detach the selected faces (optionally a copy, a new object, per face).
  - `PolygonsSlots.tb006_init(self, widget)` — Initialize Inset Face Region
  - `PolygonsSlots.tb006(self, widget)` — Inset Face Region
  - `PolygonsSlots.chk008(self, state, widget)` — Divide Facet: Split U
  - `PolygonsSlots.chk009(self, state, widget)` — Divide Facet: Split V
  - `PolygonsSlots.chk010(self, state, widget)` — Divide Facet: Tris
  - `PolygonsSlots.tb007_init(self, widget)` — Initialize Divide Facet
  - `PolygonsSlots.tb007(self, widget)` — Divide Facet
  - `PolygonsSlots.tb008_init(self, widget)` — Initialize Boolean Operation
  - `PolygonsSlots.tb008(self, widget)` — Boolean Operation
  - `PolygonsSlots.tb009_init(self, widget)` — Initialize Snap Closest Verts
  - `PolygonsSlots.tb009(self, widget)` — Snap Closest Verts: the first selected mesh's vertices onto the last
  - `PolygonsSlots.b000(self)` — Circularize: reshape the selected vertices, edges or faces into an even circle.
  - `PolygonsSlots.b001(self)` — Fill Hole: cap the open holes bounded by the selection's border edges.
  - `PolygonsSlots.b003(self)` — Symmetrize: mirror the selected components across the symmetry axis.
  - `PolygonsSlots.b006(self)` — Bridge: span two edge selections with new faces.
  - `PolygonsSlots.b007(self)` — Bridge Interactive: open the Bridge tool window.
  - `PolygonsSlots.b008(self)` — Target Weld Center: drag a vertex onto another;
  - `PolygonsSlots.b009(self)` — Collapse: each selected face to its own point;
  - `PolygonsSlots.b011(self)` — Bevel: open the Bevel tool window.
  - `PolygonsSlots.b012(self)` — Multi-Cut Tool
  - `PolygonsSlots.b022(self)` — Attach: connect the selected vertices and edges with new edges.
  - `PolygonsSlots.b032(self)` — Poke: add a center vertex to each selected face, fanning it into triangles.
  - `PolygonsSlots.b034(self)` — Wedge: sweep the selected faces around a selected edge into an arc.
  - `PolygonsSlots.b038(self)` — Assign Hole: toggle the selected faces' hole (invisible) state.
  - `PolygonsSlots.b043(self)` — Target Weld: drag a vertex onto another to weld it there.
  - `PolygonsSlots.b047(self)` — Insert Edgeloop
  - `PolygonsSlots.b049(self)` — Slide: slide the selected edge loops along their neighboring edges.
  - `PolygonsSlots.b051(self)` — Offset Edgeloop: add a loop on each side of the selected edges.
  - `PolygonsSlots.b053(self)` — Edit Edge Flow: adjust the selected edges to follow the surface curvature.

<a id="slots--preferences"></a>
### `slots/preferences.py`

Preferences: one Slots class for both hosts.

- **[`class PreferencesSlots(Slots)`](tentacle/tentacle/slots/preferences.py#L19)**
  - `PreferencesSlots.cmb004_init(self, widget)` — Marking-menu (radial startmenu / submenu) window theme.
  - `PreferencesSlots.cmb004(self, index, widget)` — Apply the marking-menu theme (persists + re-themes live windows).
  - `PreferencesSlots.cmb005_init(self, widget)` — Standalone tool-window theme.
  - `PreferencesSlots.cmb005(self, index, widget)` — Apply the standalone-window theme (persists + re-themes live windows).
  - `PreferencesSlots.cmb006_init(self, widget)` — Presentation for tools whose external app / plugin isn't installed:
  - `PreferencesSlots.cmb006(self, index, widget)` — Persist the chosen presentation policy and re-present the live gates
  - `PreferencesSlots.header_init(self, widget)` — Header menu: the manual re-probe that pairs with ``cmb006``.
  - `PreferencesSlots.tb000(self)` — Re-check installed tools: drop the cached probes, then re-apply the gates.
  - `PreferencesSlots.cmb001_init(self, widget)` — Working units: linear.
  - `PreferencesSlots.cmb001(self, index, widget)` — Set Working Units: Linear.
  - `PreferencesSlots.cmb002_init(self, widget)` — Working units: time (the frame rate).
  - `PreferencesSlots.cmb002(self, index, widget)` — Set Working Units: Time (the frame rate;
  - `PreferencesSlots.s000_init(self, widget)` — Autosave backups: the widget is the source of truth (its restored value
  - `PreferencesSlots.s001_init(self, widget)` — Autosave interval in minutes;
  - `PreferencesSlots.cmb003_init(self, widget)` — App style: the host's style list (Maya: the shipped color styles;
  - `PreferencesSlots.cmb003(self, index, widget)` — Apply the picked style, as the host's own selector would.
  - `PreferencesSlots.b001(self)` — Ui Color: the host's color settings (Blender: Preferences > Themes).
  - `PreferencesSlots.b008(self)` — Hotkeys: the host's hotkey editor (Blender: Preferences > Keymap).
  - `PreferencesSlots.b009(self)` — Plug-ins: the host's plug-in manager (Blender: Preferences > Add-ons).
  - `PreferencesSlots.b010(self)` — Preferences: the host's preferences window (Blender: Interface).
  - `PreferencesSlots.b011(self)` — Macro Manager: the uitk shortcut editor over the host's macros.

<a id="slots--rendering"></a>
### `slots/rendering.py`

Rendering: one Slots class for both hosts.

- **[`class RenderingSlots(Slots)`](tentacle/tentacle/slots/rendering.py#L25)**
  - `RenderingSlots.tb000_init(self, widget)` — Export Playblast: built once, then re-run on every panel show.
  - `RenderingSlots.tb000(self, widget)` — Export Playblast
  - `RenderingSlots.tb001_init(self, widget)` — Render: camera, renderer, IPR, smart redo, key settings and presets.
  - `RenderingSlots.tb001(self, widget)` — Render: render the current frame through the selected camera and renderer.
  - `RenderingSlots.b000(self, widget)` — WebXR Preview: open the live preview panel, wired to this scene.
  - `RenderingSlots.b001(self)` — Global Settings: the render settings (Blender: Properties > Render).
  - `RenderingSlots.b003(self)` — Render Setup: the render-layer manager (Blender: Properties > View Layer).
  - `RenderingSlots.b004(self)` — Rendering Flags: per-object render flags (Blender: Properties > Object,

<a id="slots--rigging"></a>
### `slots/rigging.py`

Rigging: one Slots class for both hosts.

- **[`class RiggingSlots(Slots)`](tentacle/tentacle/slots/rigging.py#L21)**
  - `RiggingSlots.header_init(self, widget)` — Init Rigging Header
  - `RiggingSlots.b020(self)` — Rebind Skin Clusters
  - `RiggingSlots.cmb001_init(self, widget)` — Init Create: the host's rigging utility nodes.
  - `RiggingSlots.cmb001(self, index, widget)` — Create: a rigging utility node the host's way (Maya: joint / IK
  - `RiggingSlots.cmb002_init(self, widget)` — Init Quick Rig: the procedural rig tools, then the host's own
  - `RiggingSlots.cmb002(self, index, widget)` — Quick Rig: open a procedural rig tool, or run the host's auto-rigger.
  - `RiggingSlots.tb000_init(self, widget)` — Init Display Local Rotation Axes
  - `RiggingSlots.tb000(self, widget)` — Toggle Display Local Rotation Axes
  - `RiggingSlots.tb001_init(self, widget)` — Init Constraint Switch
  - `RiggingSlots.tb001(self, widget)` — Constraint Switch: one attribute driving a constraint's targets.
  - `RiggingSlots.tb003_init(self, widget)` — Init Create Locator at Selection
  - `RiggingSlots.tb003(self, widget)` — Create Locator at Selection: each selected object rigged under a
  - `RiggingSlots.tb004_init(self, widget)` — Init Lock/Unlock Attributes
  - `RiggingSlots.tb004(self, widget)` — Lock/Unlock Attributes
  - `RiggingSlots.tb005_init(self, widget)` — Init Add to Skin (Maya: the .ui hides it in Blender).
  - `RiggingSlots.tb005(self, widget)` — Add to Skin: the selected mesh(es) skinned to the LAST selected one.
  - `RiggingSlots.b004(self)` — Render Effects: the shared tool panel.

<a id="slots--scene"></a>
### `slots/scene.py`

Scene: one Slots class for both hosts.

- **[`class SceneSlots(Slots)`](tentacle/tentacle/slots/scene.py#L38)**
  - `SceneSlots.list000_init(self, widget)` — Initialize Recent Files.
  - `SceneSlots.list000(self, item)` — Recent Files: open the picked scene.
  - `SceneSlots.cmb002_init(self, widget)` — Initialize Autosave: the last day's autosaves, newest first.
  - `SceneSlots.cmb002(self, index, widget)` — Autosave: reopen a recent autosaved scene.
  - `SceneSlots.list001_init(self, widget)` — Initialize Import.
  - `SceneSlots.list001(self, item)` — Import: run the picked row.
  - `SceneSlots.list002_init(self, widget)` — Initialize Export.
  - `SceneSlots.list002(self, item)` — Export: run the picked one-shot or open the Scene Exporter.
  - `SceneSlots.tb003_init(self, widget)` — Initialize Export Scene's option box.
  - `SceneSlots.tb003(self, widget)` — Export Scene in the chosen format, using the configured options.
  - `SceneSlots.list003_init(self, widget)` — Tools list: the scene actions grouped into one expandable row.
  - `SceneSlots.list003(self, item)` — Dispatch a Tools leaf to its own slot.
  - `SceneSlots.b013(self)` — Mesh Converter (FBX -> GLB): the DCC-agnostic extapps tool, its file
  - `SceneSlots.b010(self)` — The other DCC's bridge: the shared tool named after its TARGET app
  - `SceneSlots.b016(self)` — Unity Bridge: send the selection to a Unity project's Assets/.
  - `SceneSlots.b001(self)` — Reference Manager (Maya references, Blender linked libraries).
  - `SceneSlots.b004(self)` — Hierarchy Sync: diff / pull / fix the hierarchy against a reference scene.
  - `SceneSlots.b005(self)` — Naming: the shared Naming tool.
  - `SceneSlots.b003(self)` — Audio Clips: the shared tool over the host's ``AudioClips``.
  - `SceneSlots.b015(self)` — Blendshape Animator: the shared tool over the host's ``BlendshapeAnimator``.
  - `SceneSlots.b014_init(self, widget)` — Initialize Save to Original Scene: enabled, labelled and tooltipped from the
  - `SceneSlots.b014(self)` — Save to Original Scene: save the open autosave back to its original, the
  - `SceneSlots.b006(self)` — Cleanup Unknown (Maya): unknown nodes and plugins, legacy XGen expressions.
  - `SceneSlots.b_cleanup(self)` — Scene Cleanup (Blender): purge orphan datablocks (no users, no fake user).
  - `SceneSlots.b009(self)` — Fix OCIO (Maya): repair the Color Management / OCIO config preferences.
  - `SceneSlots.b011(self)` — Fix Color Spaces: each texture's color space by its map type
  - `SceneSlots.b018(self)` — Fix Mangled Names (Maya): the selection, or the whole scene when nothing is
  - `SceneSlots.b012(self)` — Toggle Command Ports (Maya): MEL :7001, Python :7002.
  - `SceneSlots.b017(self)` — Scene Metadata: the tool-authored data-node channels (``DataNodes.dump``)
  - `SceneSlots.b019(self)` — Check GLB / FBX: the Scene Exporter's post-write gates over files on disk.
  - `SceneSlots.tb001_init(self, widget)` — Get Scene Info -- option box: scope, profile, and one toggle per section.
  - `SceneSlots.tb001(self, widget)` — Get Scene Info -- render the sectioned audit report to the viewer dialog.
  - `SceneSlots.tb002_init(self, widget)` — Fix Non-Orthogonal Axes -- option box.
  - `SceneSlots.tb002(self, widget)` — Fix Non-Orthogonal Axes.

<a id="slots--selection"></a>
### `slots/selection.py`

Selection: one Slots class for both hosts.

- **[`class SelectionSlots(Slots)`](tentacle/tentacle/slots/selection.py#L29)** — The ``selection`` panel.
  - `SelectionSlots.list000_init(self, widget)` — Select by Type: hierarchical type list.
  - `SelectionSlots.list000(self, item)` — Select by Type
  - `SelectionSlots.tb004_init(self, widget)` — Select by Type settings menu.
  - `SelectionSlots.tb004(self, widget)` — Select by Type settings: open the scope / mode menu.
  - `SelectionSlots.cmb002_init(self, widget)` — Rig Picking Mode: mirrors the scene, never restored (see
  - `SelectionSlots.cmb002(self, index, widget)` — Rig Picking Mode
  - `SelectionSlots.cmb001_init(self, widget)` — Reorder Selection Init
  - `SelectionSlots.cmb001(self, index, widget)` — Reorder Selection: reselect the selection in the chosen order.
  - `SelectionSlots.list001_init(self, widget)` — Convert To: category rows that convert on click and expand on hover.
  - `SelectionSlots.list001(self, item)` — Convert To: convert the component selection to verts, edges, faces, UVs or shells.
  - `SelectionSlots.b002_init(self, widget)` — Selection constraint: Angle.
  - `SelectionSlots.b002(self, widget)` — Selection constraint: Angle.
  - `SelectionSlots.b003_init(self, widget)` — Selection constraint: Border.
  - `SelectionSlots.b003(self, widget)` — Selection constraint: Border.
  - `SelectionSlots.b004_init(self, widget)` — Selection constraint: Edge Loop.
  - `SelectionSlots.b004(self, widget)` — Selection constraint: Edge Loop.
  - `SelectionSlots.b005_init(self, widget)` — Selection constraint: Edge Ring.
  - `SelectionSlots.b005(self, widget)` — Selection constraint: Edge Ring.
  - `SelectionSlots.b006_init(self, widget)` — Selection constraint: Shell.
  - `SelectionSlots.b006(self, widget)` — Selection constraint: Shell.
  - `SelectionSlots.b007_init(self, widget)` — Selection constraint: UV Edge Loop.
  - `SelectionSlots.b007(self, widget)` — Selection constraint: UV Edge Loop.
  - `SelectionSlots.chk004_init(self, widget)` — Ignore Backfacing mirrors the host's live state (never restored);
  - `SelectionSlots.chk004(self, state, widget)` — Ignore Backfacing: select only what faces the camera (Maya:
  - `SelectionSlots.chk005_init(self, widget)` — Select Style: Marquee (and the three boxes' exclusive group).
  - `SelectionSlots.chk006_init(self, widget)` — Select Style: Lasso
  - `SelectionSlots.chk007_init(self, widget)` — Select Style: Paint (Blender: Circle Select)
  - `SelectionSlots.chk005(self, state, widget)` — Select Style: Marquee
  - `SelectionSlots.chk006(self, state, widget)` — Select Style: Lasso
  - `SelectionSlots.chk007(self, state, widget)` — Select Style: Paint
  - `SelectionSlots.b001(self)` — Toggle Selectability of the selected objects.
  - `SelectionSlots.chk000(self, state, widget)` — Select Nth: uncheck other checkboxes
  - `SelectionSlots.chk001(self, state, widget)` — Select Nth: uncheck other checkboxes
  - `SelectionSlots.chk002(self, state, widget)` — Select Nth: uncheck other checkboxes
  - `SelectionSlots.tb000_init(self, widget)` — Initialize Select Nth
  - `SelectionSlots.tb000(self, widget)` — Select Nth: select edge loops, rings or paths, keeping every Nth component.
  - `SelectionSlots.tb001_init(self, widget)` — Initialize Select Similar
  - `SelectionSlots.tb001(self, widget)` — Select Similar: objects by the checked metrics;
  - `SelectionSlots.tb002_init(self, widget)` — Initialize Select Island
  - `SelectionSlots.tb002(self, widget)` — Select Island: the contiguous faces, around the selected ones, whose
  - `SelectionSlots.tb003_init(self, widget)` — Initialize Select Edges By Angle
  - `SelectionSlots.tb003(self, widget)` — Select Edges By Angle: the selected meshes' edges within the range.

<a id="slots--settings"></a>
### `slots/settings.py`

Settings: one Slots class for both hosts.

- **[`class SettingsSlots(Slots)`](tentacle/tentacle/slots/settings.py#L20)**
  - `SettingsSlots.ecosystem_dists(cls, installed=None)` *(class)* — The distributions to check for updates in THIS host.
  - `SettingsSlots.header_init(self, widget)` — Initialize header
  - `SettingsSlots.tb000(self)` — Update Package
  - `SettingsSlots.tb001(self)` — Reload Scripts: tear tentacle down, reload the ecosystem in place, and
  - `SettingsSlots.check_for_update(self)` — Check the whole ecosystem for updates and upgrade what's outdated.
  - `SettingsSlots.b020(self)` — UI Style Editor
  - `SettingsSlots.b021(self)` — Shortcut Editor
  - `SettingsSlots.b022(self)` — UI Browser: open the tentacle UI browser (search, show/hide registered UIs).
  - `SettingsSlots.b023(self)` — Global Shortcuts: the shortcut editor focused on the global triggers --
  - `SettingsSlots.b024(self)` — Preset Editor: every tool's presets in one window -- lock, group into
  - `SettingsSlots.cmb_bind_default_init(self, widget)` — Default menu (activation key only).
  - `SettingsSlots.cmb_bind_left_init(self, widget)` — Left mouse button.
  - `SettingsSlots.cmb_bind_middle_init(self, widget)` — Middle mouse button.
  - `SettingsSlots.cmb_bind_right_init(self, widget)` — Right mouse button.
  - `SettingsSlots.cmb_bind_left_right_init(self, widget)` — Left + Right mouse buttons.
  - `SettingsSlots.b_reset_bindings(self)` — Reset marking-menu bindings (routes + activation key) to defaults.

<a id="slots--subdivision"></a>
### `slots/subdivision.py`

Subdivision: one Slots class for both hosts.

- **[`class SubdivisionSlots(Slots)`](tentacle/tentacle/slots/subdivision.py#L21)**
  - `SubdivisionSlots.s000_init(self, widget)` — Division Level: reflect the selection's live preview division level.
  - `SubdivisionSlots.s001_init(self, widget)` — Tessellation Level: reflect the selection's live tessellation level.
  - `SubdivisionSlots.s000(self, value: int, widget: object) -> None` — Division Level (Maya: the smooth preview's divisions;
  - `SubdivisionSlots.s001(self, value: int, widget: object) -> None` — Tessellation Level (Maya: OpenSubdiv adaptive tessellation;
  - `SubdivisionSlots.b000(self)` — Quadrangulate: merge triangles into quads.
  - `SubdivisionSlots.b001(self)` — Triangulate: split the selected faces into triangles.
  - `SubdivisionSlots.b005(self)` — Reduce: halve the polygon count -- the one-click form of tb000's Reduce
  - `SubdivisionSlots.b008(self)` — Add Divisions: subdivide the selected mesh.
  - `SubdivisionSlots.b011(self)` — Convert Preview: bake the smooth preview into polygons.
  - `SubdivisionSlots.b028(self)` — Quad Draw: Maya's retopology tool (Blender: Poly Build).
  - `SubdivisionSlots.tb000_init(self, widget)` — Initialize Decimate.
  - `SubdivisionSlots.tb000(self, widget)` — Decimate: reduce the face count by percentage, or dissolve coplanar faces.

<a id="slots--symmetry"></a>
### `slots/symmetry.py`

Symmetry: one Slots class for both hosts.

- **[`class SymmetrySlots(Slots)`](tentacle/tentacle/slots/symmetry.py#L20)**
  - `SymmetrySlots.chk000_init(self, widget)` — Seed the axis group from the host.
  - `SymmetrySlots.chk001_init(self, widget)` — Symmetry Y: mirrors the host;
  - `SymmetrySlots.chk002_init(self, widget)` — Symmetry Z: mirrors the host;
  - `SymmetrySlots.chk000(self, state, widget)` — Symmetry X: toggle modeling symmetry across the X axis.
  - `SymmetrySlots.chk001(self, state, widget)` — Symmetry Y: toggle modeling symmetry across the Y axis.
  - `SymmetrySlots.chk002(self, state, widget)` — Symmetry Z: toggle modeling symmetry across the Z axis.
  - `SymmetrySlots.chk004_init(self, widget)` — Object space: mirrors the host;
  - `SymmetrySlots.chk004(self, state, widget)` — Symmetry: object space.
  - `SymmetrySlots.chk005_init(self, widget)` — Seed the space radio (object vs topology) from the host.
  - `SymmetrySlots.chk005(self, state, widget)` — Symmetry: by topology.

<a id="slots--tools--__init__"></a>
### `slots/tools/__init__.py`

Each shared tool's one Slots class, paired by name with its ``ui/tools/<tool>.ui``

- [`HOSTS`](tentacle/tentacle/slots/tools/__init__.py#L16) — constant

<a id="slots--tools--_app_bridge--host_bridge"></a>
### `slots/tools/_app_bridge/host_bridge.py`

The app-bridge panels' one base, shared by both hosts.

- **[`class HostBridge(Slots.BridgeSlotsBase)`](tentacle/tentacle/slots/tools/_app_bridge/host_bridge.py#L43)** — uitk's ``BridgeSlotsBase`` over the host toolkit (``self.tk``).
  - `HostBridge.bridge_class(self)` *(property)* — The host's engine class for this panel: ``self.tk.<X>Bridge``.
  - `HostBridge.make_bridge(self)` — A fresh engine;
  - `HostBridge.params_module(self)` *(property)* — The engine's parameter registry (a ``uitk.bridge.ParamRegistry``).
  - `HostBridge.template_dir(self)` *(property)* — The engine's template folder.
  - `HostBridge.list_template_modes(self)` — The engine's ``[(template, mode), ...]`` for the template combo.
  - `HostBridge.PRESETS_ROOT(self)` *(property)* — ``<host library>/<UI_NAME>``: each host's presets stay where they were.
  - `HostBridge.resolve_scope_objects(self, scope: str)` — The host's objects for a ``SCOPE`` word;
  - `HostBridge.scoped_objects(self, params, warn: bool = True)` — The Scope's objects closed over what a send of them ships.
  - `HostBridge.live_param_tooltip_blocks(self)` — Append the Bake Source set's CURRENT members to its row's tooltips.
  - `HostBridge.set_bake_source_from_selection(self) -> None` — Store the selection as the scene's bake source.
  - `HostBridge.select_bake_source(self) -> None` — Select the bake-source set's members.
  - `HostBridge.clear_bake_source(self) -> None` — Remove the bake-source set;

<a id="slots--tools--_blendshape_animator--sort_item"></a>
### `slots/tools/_blendshape_animator/sort_item.py`

A tween-tree row that sorts its numeric columns by number.

- **[`class NumericSortItem(QtWidgets.QTreeWidgetItem)`](tentacle/tentacle/slots/tools/_blendshape_animator/sort_item.py#L8)** — A tree row that sorts the Weight and Frame columns by number.

<a id="slots--tools--_channels--attribute_form"></a>
### `slots/tools/_channels/attribute_form.py`

The Create Attribute popup: a one-shot form over the host's attribute types.

- **[`class AttributeForm`](tentacle/tentacle/slots/tools/_channels/attribute_form.py#L6)** — Builds the Create Attribute popup.
  - `AttributeForm.show(cls, sb, parent, types, on_create, keyable=True)` *(class)* — Build and show the form.

<a id="slots--tools--_channels--enum_cell"></a>
### `slots/tools/_channels/enum_cell.py`

The value cell of an enum attribute: its labels in a combobox, plus Rename /

- **[`class EnumCell`](tentacle/tentacle/slots/tools/_channels/enum_cell.py#L7)** — Builds an enum row's value-cell combobox.
  - `EnumCell.build(cls, sb, attr_name, labels, indices, current, on_activated, on_action)` *(class)* — A combobox showing *labels* with *current* (a stored index) chosen.
  - `EnumCell.show_index(combo, index)` *(static)* — Show stored *index* in *combo* without firing its handlers.

<a id="slots--tools--_channels--inline_rename"></a>
### `slots/tools/_channels/inline_rename.py`

Rename the panel's target in place: the target field, and the footer in

- **[`class InlineRename`](tentacle/tentacle/slots/tools/_channels/inline_rename.py#L9)** — Double-click-to-rename on a read-only line edit.
- **[`class FooterRename`](tentacle/tentacle/slots/tools/_channels/inline_rename.py#L78)** — An inline rename page on a uitk ``Footer``.
  - `FooterRename.edit(self)` — Swap the footer's label for the line edit, holding the name.

<a id="slots--tools--_hierarchy_sync--controller"></a>
### `slots/tools/_hierarchy_sync/controller.py`

The Hierarchy Sync panel's state: the reference path, the paths the user

- [`RECENT_LIMIT`](tentacle/tentacle/slots/tools/_hierarchy_sync/controller.py#L24) — constant
- [`LOG_LIMIT`](tentacle/tentacle/slots/tools/_hierarchy_sync/controller.py#L27) — constant
- **[`class HierarchySyncController(pythontk.LoggingMixin)`](tentacle/tentacle/slots/tools/_hierarchy_sync/controller.py#L30)** — The panel's state and the orchestration between it, the host's session
  - `HierarchySyncController.diff_result(self) -> Optional[dict]` *(property)* — The session's last analysis (``None`` before one).
  - `HierarchySyncController.reference_path(self) -> str` *(property)* — The reference scene's path (``""`` when none is set).
  - `HierarchySyncController.update_header_tooltips(self) -> None` — Each tree's header tooltip: its file's full path.
  - `HierarchySyncController.clear_analysis(self) -> None` — Drop the analysis and the held reference (the session's) and the
  - `HierarchySyncController.on_window_hidden(self) -> None` — Release the reference while the panel is hidden.
  - `HierarchySyncController.populate_reference_tree(self, tree_widget, reference_path: str = None) -> None` — Fill the reference tree from *reference_path*, loading it (or
  - `HierarchySyncController.refresh_trees(self, restore_selection: bool = True) -> None` — Rebuild both trees.
  - `HierarchySyncController.refresh_styling(self) -> None` — Diff colours (or none), then the ignored styling, on both trees.
  - `HierarchySyncController.ignored_set(self, tree_widget) -> set` — The ignored paths of *tree_widget* (an empty set for another widget).
  - `HierarchySyncController.is_path_ignored(self, tree_widget, path: str) -> bool` — Whether *path*, or an ancestor of it, is ignored in *tree_widget*.
  - `HierarchySyncController.clear_ignored_paths(self) -> None` — Forget every ignored path, in both trees.
  - `HierarchySyncController.effective_diff(self) -> Dict[str, list]` — The analysis' differences, the ignored paths left out (a reparent or
  - `HierarchySyncController.log_diff_results(self) -> None` — Log the differences (ignored ones left out): the top-level missing
  - `HierarchySyncController.write_diff_report(missing, extra, reparented, fuzzy_matches) -> Optional[str]` *(static)* — Write the full diff to a text file.
  - `HierarchySyncController.coerce_str_list(value) -> List[str]` *(static)* — A settings value as a list: QSettings hands a one-item list back as
  - `HierarchySyncController.get_recent_reference_scenes(self) -> List[str]` — The recent reference scenes that still exist (the last ten).
  - `HierarchySyncController.save_recent_reference_scene(self, scene_path: str) -> None` — Put *scene_path* last in the recent references (the last ten kept).

<a id="slots--tools--_hierarchy_sync--tree_matcher"></a>
### `slots/tools/_hierarchy_sync/tree_matcher.py`

Find the Hierarchy Sync trees' items by the hierarchy paths a diff names.

- [`PLACEHOLDERS`](tentacle/tentacle/slots/tools/_hierarchy_sync/tree_matcher.py#L22) — constant
- **[`class TreePathMatcher(pythontk.LoggingMixin)`](tentacle/tentacle/slots/tools/_hierarchy_sync/tree_matcher.py#L33)** — Index a tree's items by path and find the items a diff path names.
  - `TreePathMatcher.iter_items(widget)` *(static)* — Every item of *widget*, depth first in display order.
  - `TreePathMatcher.item_path(item) -> str` *(static)* — The item's display path: its and its ancestors' names, root first.
  - `TreePathMatcher.raw_item_path(item) -> str` *(static)* — The item's path by its nodes' own names (``_raw_name``: a Maya node's
  - `TreePathMatcher.item_key(self, item) -> str` — The name the host takes *item*'s node by (a pull's target).
  - `TreePathMatcher.build_tree_index(self, widget) -> Tuple[dict, dict, Dict[str, list]]` — Index *widget*'s items three ways for :meth:`find_path_matches`.
  - `TreePathMatcher.find_path_matches(self, target_path: str, by_full: dict, by_clean_full: dict, by_last: dict, prefer_cleaned: bool = False, strict: bool = False) -> Tuple[List[Any], str]` — The items *target_path* names, and the strategy that found them.
  - `TreePathMatcher.log_matching_debug(self, path, candidates, strategy, prefix='') -> None` — Log how *path* matched.

<a id="slots--tools--_hierarchy_sync--tree_renderer"></a>
### `slots/tools/_hierarchy_sync/tree_renderer.py`

The Hierarchy Sync trees: filling them, the diff's colours, the ignored

- [`ORIG_TOOLTIP_ROLE`](tentacle/tentacle/slots/tools/_hierarchy_sync/tree_renderer.py#L26) — constant
- [`BROWSE_PLACEHOLDER`](tentacle/tentacle/slots/tools/_hierarchy_sync/tree_renderer.py#L29) — constant
- [`OPEN_SCENE_PLACEHOLDER`](tentacle/tentacle/slots/tools/_hierarchy_sync/tree_renderer.py#L30) — constant
- **[`class HierarchyTreeRenderer(pythontk.LoggingMixin)`](tentacle/tentacle/slots/tools/_hierarchy_sync/tree_renderer.py#L36)** — Owns the two trees' content and look;
  - `HierarchyTreeRenderer.session(self)` *(property)* — The host's ``HierarchySyncSession``.
  - `HierarchyTreeRenderer.matcher(self) -> TreePathMatcher` — A path matcher over the host's path rules, logging into the panel.
  - `HierarchyTreeRenderer.populate_current_scene_tree(self, tree_widget) -> None` — Fill *tree_widget* with the current scene's hierarchy, or an Open
  - `HierarchyTreeRenderer.populate_reference_tree(self, tree_widget, nodes, reference_name='Reference Scene') -> None` — Fill *tree_widget* with the reference's *nodes* (already loaded).
  - `HierarchyTreeRenderer.show_reference_placeholder(self, tree_widget, reference_name='Reference Scene') -> None` — A 'Browse for Reference Scene' prompt in the reference tree.
  - `HierarchyTreeRenderer.show_reference_error(self, tree_widget, reference_name='Reference Scene', message='File Not Found') -> None` — A status *message* in the reference tree.
  - `HierarchyTreeRenderer.populate_tree_with_hierarchy(self, tree_widget, nodes, tree_type='current')` — Add *nodes* to *tree_widget*, nested as the scene nests them.
  - `HierarchyTreeRenderer.apply_difference_formatting(self, tree001, tree000) -> None` — Colour the diff into both trees (tint selection while it shows).
  - `HierarchyTreeRenderer.clear_tree_colors(self, tree_widget) -> None` — Drop the diff's colours and tooltips from every item;
  - `HierarchyTreeRenderer.format_tree_differences(self, tree_widget, tree_type, matcher, by_full, by_clean, by_last) -> None` — Colour one tree: extras and the current side of a reparent in the
  - `HierarchyTreeRenderer.apply_ignore_styling(self, tree_widget) -> None` — Style the ignored items: a directly ignored one struck through and
  - `HierarchyTreeRenderer.build_item_path(item) -> str` *(static)* — *item*'s display path (what the ignored paths store).
  - `HierarchyTreeRenderer.selected_item_keys(self, tree_widget) -> List[str]` — The names the host takes the selected items' nodes by (a pull's
  - `HierarchyTreeRenderer.get_selected_tree_items(self, tree_widget) -> list` — *tree_widget*'s selected items, in selection order.
  - `HierarchyTreeRenderer.count_tree_items(tree_widget) -> int` *(static)* — How many items *tree_widget* holds.
  - `HierarchyTreeRenderer.store_tree_selection(self, tree_widget) -> List[str]` — The selected items' paths.
  - `HierarchyTreeRenderer.restore_tree_selection(self, tree_widget, selected_paths) -> int` — Select the items at *selected_paths*;
  - `HierarchyTreeRenderer.get_tree_structure(self, tree_widget) -> List[str]` — Every item's path, sorted: equal before and after a refresh when the
  - `HierarchyTreeRenderer.condense_to_roots(paths) -> List[str]` *(static)* — Drop paths whose ancestor is also in *paths* (keep shallow roots).
  - `HierarchyTreeRenderer.filter_to_leaves(paths) -> List[str]` *(static)* — Keep only paths that are not a parent of another path in *paths*.
  - `HierarchyTreeRenderer.apply_diff_options(self, tree001, tree000, auto_select: bool, expand_diff: bool, select_root_only: bool = False, select_leaves_only: bool = False) -> None` — Select and expand the diff in the trees.

<a id="slots--tools--_reference_manager--controller"></a>
### `slots/tools/_reference_manager/controller.py`

The Reference Manager panel's controller: the browsed workspace, the table

- **[`class ReferenceManagerController(pythontk.LoggingMixin)`](tentacle/tentacle/slots/tools/_reference_manager/controller.py#L28)** — State and behavior behind ``reference_manager.ui`` (see the module docstring).
  - `ReferenceManagerController.tk(self)` *(property)* — The host toolkit (``Slots.tk``).
  - `ReferenceManagerController.norm(path) -> str` *(static)* — The panel's comparison key for a path: normalized, case-folded only where
  - `ReferenceManagerController.role(self, offset: int)` — ``Qt.UserRole + offset`` (the row data roles above).
  - `ReferenceManagerController.table_signals_blocked(self)` — Run a table rebuild without its signals: a programmatic change must not
  - `ReferenceManagerController.message(self, text, *buttons)` — The panel's message box (``sb.message_box``).
  - `ReferenceManagerController.report(self, message: str) -> None` — The engine's ``report``: its plain-text outcome, in a message box.
  - `ReferenceManagerController.error_box(self, lead: str, name: str, error) -> None` — Report *error* for the scene file *name*.
  - `ReferenceManagerController.footer_status(self, text, level='warning')` — Leave *text* in the footer's status label (no-op without a footer).
  - `ReferenceManagerController.header_menu(self)` — The header menu -- home of the naming, filter and include options.
  - `ReferenceManagerController.naming_options(self)` — ``(case_style, suffix, structure_pattern)`` from the header menu's Naming
  - `ReferenceManagerController.type_extensions(cls, include_type)` *(class)* — Every extension the Include Types toggle *include_type* lists (``usd`` ->
  - `ReferenceManagerController.include_type_checked_by_default(self, include_type) -> bool` — True for the host's own scene types (the engine's ``INCLUDE_DEFAULTS``).
  - `ReferenceManagerController.include_type_tooltip(self, include_type) -> str` — What the Include Types toggle lists, and how a row of it references.
  - `ReferenceManagerController.included_extensions(self)` — The extensions whose Include Types checkbox is checked;
  - `ReferenceManagerController.is_importable(self, path) -> bool` — True if Unlink and Import can bring *path*'s row in with no reference
  - `ReferenceManagerController.foreign_route(self)` — The conversion route from the header menu: ``"fbx"`` (default) / ``"usd"``.
  - `ReferenceManagerController.filter_menu(self)` — The Filter field's option menu (ignore case, target);
  - `ReferenceManagerController.scene_notes(self) -> 'ptk.SceneNotes'` *(property)* — The Notes column's store (``ptk.SceneNotes``: one file per project, shared
  - `ReferenceManagerController.note(self, path) -> str` — *path*'s note ('' without one;
  - `ReferenceManagerController.migrate_settings_notes(self)` — Move notes a panel kept in its settings (keyed by path, before 2026-10-13)
  - `ReferenceManagerController.set_note(self, path, text) -> None` — Save *text* as *path*'s note;
  - `ReferenceManagerController.refresh_file_list(self, invalidate=False)` — Rebuild the table for the browsed workspace, then re-select its
  - `ReferenceManagerController.update_table(self, file_names, file_list)` — (Re)fill the table with *file_list* labelled *file_names*: items reused
  - `ReferenceManagerController.update_listing_footer(self, listed: int, referenced: int)` — The footer's listing summary -- files shown, rows referenced, files the
  - `ReferenceManagerController.format_table_item(self, item, file_path, is_current)` — The current scene's name cell: enabled (rename / delete / open) but not
  - `ReferenceManagerController.row_references(self, path) -> list` — The references a row stands for -- through the bake standing in for it too.
  - `ReferenceManagerController.sync_reference_icons(self)` — The reference and display-mode icons of every row, from the live references.
  - `ReferenceManagerController.sync_selection_to_references(self)` — Select exactly the rows the scene references (selectable rows only).
  - `ReferenceManagerController.handle_item_selection(self)` — The selection changed: reference the newly selected rows, remove the
  - `ReferenceManagerController.apply_notes_column_visibility(self)` — Show the Notes column only while Show Notes Column is checked (view-only:
  - `ReferenceManagerController.refilter_on_naming_change(self)` — Re-filter when a naming field changes while a filter / display option
  - `ReferenceManagerController.row_path(self, row)` — The path on *row*'s name cell (None for no row).
  - `ReferenceManagerController.capture_context_row(self, pos)` — Store the right-clicked row (the menu acts on it, not the selection) and
  - `ReferenceManagerController.context_row(self)` — The right-clicked row, validated against the row count, or None.
  - `ReferenceManagerController.label_open_action(self)` — Read the context menu's Open as 'Reopen' on the open scene's row: opening
  - `ReferenceManagerController.select_item_silently(self, item, selected: bool) -> None` — Set *item*'s selection without firing the selection -> reference sync.
  - `ReferenceManagerController.prepare_item_for_edit(self, item)` — Show the full file name in the name cell an inline rename edits.
  - `ReferenceManagerController.restore_item_display(self, item)` — Restore the name cell's label after an edit.
  - `ReferenceManagerController.item_double_clicked(self, item)` — Double-click a name to rename it inline (editable rows only: never a
  - `ReferenceManagerController.item_changed(self, item)` — Commit an inline rename (the name column) or a note (the Notes column).
  - `ReferenceManagerController.editor_closed(self, *_args)` — The inline editor closed: the name cell shows its label again.

<a id="slots--tools--_reference_manager--listing"></a>
### `slots/tools/_reference_manager/listing.py`

The Reference Manager's listing rules: how a scene file reads as a row and

- **[`class SceneListing`](tentacle/tentacle/slots/tools/_reference_manager/listing.py#L17)** — Row labels, filter matches and the naming conventions' path rules.
  - `SceneListing.display_name(path: str, hide_extension: bool, hide_suffix: str) -> str` *(static)* — The table label for *path* -- its basename, less the extension and/or a
  - `SceneListing.split_patterns(cls, text: str) -> List[str]` *(class)* — *text* split on every :attr:`DELIMITERS` entry, each part trimmed.
  - `SceneListing.text_matches_filter(text: str, filter_patterns: Sequence[str], ignore_case: bool = True) -> bool` *(static)* — True if *text* (a file name) matches ANY of the already-split glob
  - `SceneListing.matches_notes_filter(cls, notes_text: str, filter_text: str, ignore_case: bool = True) -> bool` *(class)* — True if the note *notes_text* matches the filter.
  - `SceneListing.scenes_folder(workspace: str) -> str` *(static)* — The ``{scenes}`` placeholder for *workspace*: its ``scene`` file rule when
  - `SceneListing.format_name(name: str, case_style: str = 'None', suffix: str = '') -> str` *(static)* — *name* in the *case_style* convention (``ptk.StrUtils.set_case``;
  - `SceneListing.strip_all_suffixes(base: str, suffix: str) -> str` *(static)* — *base* less EVERY trailing *suffix*: a prefill still ending in one (a
  - `SceneListing.filter_by_folder_structure(files: Iterable[str], workspace: str, pattern: str, suffix: str, scenes: str) -> List[str]` *(static)* — The *files* whose folder ends with *pattern* resolved for each
  - `SceneListing.delete_prompt(cls, paths: Sequence[str], permanent: Sequence[str] = ()) -> str` *(class)* — Confirmation text for deleting *paths*.

<a id="slots--tools--_reference_manager--references"></a>
### `slots/tools/_reference_manager/references.py`

The Reference Manager's reference actions: a row's reference and display

- **[`class ReferenceActions`](tentacle/tentacle/slots/tools/_reference_manager/references.py#L15)** — The row and bulk reference actions (see the module docstring).
  - `ReferenceActions.toggle_reference_at_row(self, row, col=None)` — Reference the row's file, or remove the references it stands for.
  - `ReferenceActions.cycle_display_mode_at_row(self, row, col=None)` — Cycle the row's references' display: Normal -> Reference -> Template.
  - `ReferenceActions.add_unlink_namespace_action(self, button)` — Give *button* the cycling namespace-mode action (applies to every unlink);
  - `ReferenceActions.unlink_namespace_mode(self) -> str` — The namespace handling picked beside Unlink and Import All: the engine's
  - `ReferenceActions.ask_scene_data(self, summary, namespace)` — The unlink question for a reference bringing scene data of its own: merge
  - `ReferenceActions.unlink_references(self, namespaces)` — Unlink and import the references named *namespaces* (confirmed).
  - `ReferenceActions.unlink_import_row(self)` — Unlink and Import at the right-clicked row: a referenced row's data made
  - `ReferenceActions.unlink_all(self)` — Unlink and import every reference (confirmed: an unlink is not undoable).
  - `ReferenceActions.unreference_all(self)` — Remove every reference from the scene (confirmed).
  - `ReferenceActions.convert_to_assembly(self)` — Replace every reference with an assembly (confirmed;

<a id="slots--tools--_reference_manager--scene_files"></a>
### `slots/tools/_reference_manager/scene_files.py`

The Reference Manager's scene files: open / close / save / rename / delete, the

- **[`class SceneFiles`](tentacle/tentacle/slots/tools/_reference_manager/scene_files.py#L24)** — The scene-file actions (see the module docstring).
  - `SceneFiles.normalize_structure_pattern(self, pattern: str) -> str` — The folder-structure pattern trimmed, with the common ``{scene}`` typo read
  - `SceneFiles.default_save_name(self, case_style: str, suffix: str) -> str` — The name Save would prepopulate: the open scene's base, less every trailing
  - `SceneFiles.resolve_save_target(self, name, case_style, suffix, pattern) -> str` — The absolute path Save To Workspace writes for *name* under the browsed
  - `SceneFiles.save_scene_preview(self) -> str` — Live tooltip for the footer's Save button: the exact path Save would write.
  - `SceneFiles.folder_structure_preview(self) -> str` — Live tooltip for the Folder Structure field: its placeholders resolved
  - `SceneFiles.wire_structure_tooltip(self, menu) -> None` — Bind the live folder-structure preview once the field's ``.tooltip`` proxy
  - `SceneFiles.open_scene_at_row(self, row, col=None)` — Open the row's scene -- or close it (a new empty scene) when it already is
  - `SceneFiles.confirm_discard_unsaved(self) -> bool` — True if it is OK to replace the open scene: nothing unsaved, the user saved,
  - `SceneFiles.save_current_scene(self) -> bool` — Save the open scene in place -- or, when it cannot be written where it came
  - `SceneFiles.open_path(self, path) -> bool` — Open *path*, offering to save the open scene's changes first -- the single
  - `SceneFiles.close_scene(self) -> bool` — Close the open scene (a new empty one), guarding unsaved changes.
  - `SceneFiles.save_to_workspace(self)` — Save the open scene into the workspace under the Naming conventions,
  - `SceneFiles.rename_path(self, old_path, new_path, folder=None, item=None) -> Optional[str]` — Rename *old_path* to *new_path* through the engine (the open scene saved and
  - `SceneFiles.rename_scene(self)` — Rename the right-clicked row's scene, prompting for the new name under the
  - `SceneFiles.delete_scene(self)` — Delete the right-clicked row's scene: to the trash, or -- a drive with none,
  - `SceneFiles.open_file_location(self)` — Reveal the right-clicked row's file in the file manager.
  - `SceneFiles.copy_path(self)` — Copy the right-clicked row's full path to the clipboard.
  - `SceneFiles.resolve_rig_mode(self, path)` — How a foreign scene's rig logic travels: asked only when it has some.
  - `SceneFiles.resolve_conversion(self, path)` — The route + rig mode ``bake_scene`` / ``import_scene`` take for *path*, or
  - `SceneFiles.conversion_progress(self, text)` — Footer progress for one conversion;
  - `SceneFiles.bake_foreign_path(self, path, project=None)` — Bake *path* to the host's cached native scene and return it, or None.
  - `SceneFiles.import_paths(self, paths)` — Import each row in *paths* as local data with no reference behind it.

<a id="slots--tools--_reference_manager--workspaces"></a>
### `slots/tools/_reference_manager/workspaces.py`

The Reference Manager's workspace browser: the Root Directory, the workspace

- **[`class WorkspaceBrowser`](tentacle/tentacle/slots/tools/_reference_manager/workspaces.py#L19)** — The Root Directory and Workspaces fields (see the module docstring).
  - `WorkspaceBrowser.root_dir(self) -> str` — The Root Directory field's text.
  - `WorkspaceBrowser.workspace_dir(self) -> str` — The workspace being browsed: the combo's selection, else the root.
  - `WorkspaceBrowser.save_workspace_selection(self, root_dir: str, workspace_name: str)` — Remember which workspace was last selected for *root_dir* (capped).
  - `WorkspaceBrowser.restore_workspace_index(self, widget) -> bool` — Select the workspace last used for the current root, if still listed.
  - `WorkspaceBrowser.update_current_dir(self, text: Optional[str] = None)` — The Root Directory changed (or was validated): rescan its workspaces when
  - `WorkspaceBrowser.update_workspace_combo(self, root_dir=None)` — Repopulate the workspace combo from the workspaces under *root_dir* (the
  - `WorkspaceBrowser.set_workspace(self, workspace_path: str, invalidate: bool = True) -> bool` — Browse *workspace_path* and refresh the file list.
  - `WorkspaceBrowser.update_workspace_footer(self)` — Name the browsed workspace in the footer's status.
  - `WorkspaceBrowser.flash_footer(self, text, level='success')` — Show *text* in the footer's status for a moment, then the workspace again.
  - `WorkspaceBrowser.set_project(self)` — Set the host's project (session workspace) to the browsed workspace -- the
  - `WorkspaceBrowser.set_root_to_current(self)` — Set the Root Directory to the host's current workspace.
  - `WorkspaceBrowser.open_root_dir(self)` — Reveal the Root Directory in the file manager.
  - `WorkspaceBrowser.new_workspace(self)` — Create a marked workspace (``workspace.mel``, rules from the active
  - `WorkspaceBrowser.mark_workspace(self)` — Mark the browsed workspace as a shared Maya/Blender project: a
  - `WorkspaceBrowser.select_workspace(self, path)` — Select the combo entry whose data is *path* (after a repopulate).

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

<a id="slots--tools--_shot_sequencer--clip_menu"></a>
### `slots/tools/_shot_sequencer/clip_menu.py`

Clip context menus and clip-level key operations.

- **[`class ClipMenuMixin`](tentacle/tentacle/slots/tools/_shot_sequencer/clip_menu.py#L20)** — Clip and gap context menus, and the clip-level key operations they run.
  - `ClipMenuMixin.on_clip_menu(self, menu, clip_id: int) -> None` — Add domain-specific actions to a clip's context menu.
  - `ClipMenuMixin.on_gap_menu(self, menu, gap_start: float, gap_end: float) -> None` — Add domain-specific actions to a gap overlay's context menu.

<a id="slots--tools--_shot_sequencer--clip_motion"></a>
### `slots/tools/_shot_sequencer/clip_motion.py`

Clip and key motion for the Shot Sequencer panel: moving and resizing clips,

- [`FLOAT_ZERO_EPS`](tentacle/tentacle/slots/tools/_shot_sequencer/clip_motion.py#L19) — constant
- [`KEY_MATCH_EPS`](tentacle/tentacle/slots/tools/_shot_sequencer/clip_motion.py#L21) — constant
- **[`class ClipMotionMixin`](tentacle/tentacle/slots/tools/_shot_sequencer/clip_motion.py#L26)** — Clip move / resize, per-key drag and delete handlers.
  - `ClipMotionMixin.on_clip_resized(self, clip_id: int, new_start: float, new_duration: float) -> None` — Handle one clip's edge drag -- see :meth:`_commit_clip_resizes`.
  - `ClipMotionMixin.on_clips_batch_resized(self, resizes) -> None` — Handle an edge drag that scaled a SELECTION of clips as one unit.
  - `ClipMotionMixin.on_clip_moved(self, clip_id: int, new_start: float) -> None` — Handle clip move -- routes to audio or shot-level logic.
  - `ClipMotionMixin.on_clips_batch_moved(self, moves) -> None` — Handle a batch of clip moves (group drag), syncing once at the end.
  - `ClipMotionMixin.on_keys_moved(self, clip_id: int, changes: list) -> None` — Move individual keyframes on the curves, then refresh.
  - `ClipMotionMixin.on_keys_batch_moved(self, groups) -> None` — Commit one key drag that spanned any number of clips.
  - `ClipMotionMixin.on_keys_deleted(self, clip_id: int, times: list) -> None` — Delete individual keyframes from the curves, then refresh.

<a id="slots--tools--_shot_sequencer--controller"></a>
### `slots/tools/_shot_sequencer/controller.py`

The Shot Sequencer panel's controller: :class:`ShotSequencerController`.

- **[`class ShotSequencerController(SceneCallbacksMixin, UndoLedgerMixin, ShotLaneMixin, ClipMenuMixin, KeyMenuMixin, WidgetSyncMixin, SceneSelectionMixin, TransportMixin, GapManagerMixin, ClipMotionMixin, ShotNavMixin, MarkerManagerMixin, pythontk.LoggingMixin)`](tentacle/tentacle/slots/tools/_shot_sequencer/controller.py#L49)** — Business logic controller bridging SequencerWidget ↔ ShotSequencer.
  - `ShotSequencerController.host(self)` *(property)* — The host library's ``SequencerHost``: every scene call the panel
  - `ShotSequencerController.sequencer(self)` *(property)* — Return the host's ShotSequencer, lazily created over the active store.
  - `ShotSequencerController.active_shot_id(self) -> Optional[int]` *(property)* — Return the shot_id currently selected, or the first shot's id.

<a id="slots--tools--_shot_sequencer--gap_manager"></a>
### `slots/tools/_shot_sequencer/gap_manager.py`

Gap and range-highlight handlers for the Shot Sequencer controller.

- [`TIME_SNAP_EPS`](tentacle/tentacle/slots/tools/_shot_sequencer/gap_manager.py#L16) — constant
- **[`class GapManagerMixin`](tentacle/tentacle/slots/tools/_shot_sequencer/gap_manager.py#L21)** — Mixin supplying gap-overlay and range-highlight handlers.
  - `GapManagerMixin.on_range_highlight_changed(self, start: float, end: float) -> None` — Update the active shot when a range-highlight handle is dragged.
  - `GapManagerMixin.on_gap_resized(self, original_next_start: float, new_next_start: float) -> None` — Handle a right-edge gap drag: the following shot's ``.start``.
  - `GapManagerMixin.on_gap_left_resized(self, original_prev_end: float, new_prev_end: float) -> None` — Handle a left-edge gap drag: the preceding shot's ``.end``.
  - `GapManagerMixin.on_gap_moved(self, old_start: float, old_end: float, new_start: float, new_end: float) -> None` — Handle body gap drag — slide the gap while preserving its width.
  - `GapManagerMixin.on_gap_lock_changed(self, gap_start: float, gap_end: float, locked: bool) -> None` — Handle a single gap's lock state being toggled via context menu.
  - `GapManagerMixin.on_gap_lock_all(self) -> None` — Lock all gaps so they are preserved during respace.
  - `GapManagerMixin.on_gap_unlock_all(self) -> None` — Unlock all gaps so they follow the global gap value.

<a id="slots--tools--_shot_sequencer--key_menu"></a>
### `slots/tools/_shot_sequencer/key_menu.py`

Key context menus and the edits run over a key selection, for the Shot

- **[`class KeyMenuMixin`](tentacle/tentacle/slots/tools/_shot_sequencer/key_menu.py#L20)** — Key context menus, tangent edits and drags, and the key-selection edits.
  - `KeyMenuMixin.on_key_menu(self, menu, key_groups: list) -> None` — Add the key actions to a key's context menu.
  - `KeyMenuMixin.on_keys_tangent_dragged(self, groups: list, side: str, broken: bool) -> None` — Write the tangents a dragged handle asks for on the keys' curves.
  - `KeyMenuMixin.register_key_targets(self, editor_name: str, source) -> None` — Resolve the key shortcuts' targets through *source* while the

<a id="slots--tools--_shot_sequencer--marker_manager"></a>
### `slots/tools/_shot_sequencer/marker_manager.py`

Marker persistence for the shot sequencer controller.

- **[`class MarkerManagerMixin(_MarkerManagerMixinInternal)`](tentacle/tentacle/slots/tools/_shot_sequencer/marker_manager.py#L40)** — Mixin supplying marker CRUD persistence.
  - `MarkerManagerMixin.on_marker_added(self, marker_id: int, time: float) -> None` — Persist a newly added marker.
  - `MarkerManagerMixin.on_marker_moved(self, marker_id: int, new_time: float) -> None` — Update persisted marker time.
  - `MarkerManagerMixin.on_marker_changed(self, marker_id: int) -> None` — Update persisted marker note/color.
  - `MarkerManagerMixin.on_marker_removed(self, marker_id: int) -> None` — Remove marker from persistent store.

<a id="slots--tools--_shot_sequencer--scene_callbacks"></a>
### `slots/tools/_shot_sequencer/scene_callbacks.py`

Scene events for the shot sequencer: undo/redo, key edits, time changes.

- **[`class SceneCallbacksMixin`](tentacle/tentacle/slots/tools/_shot_sequencer/scene_callbacks.py#L18)** — Scene event hooks: undo/redo, key edits and time changes refresh the widget.
  - `SceneCallbacksMixin.remove_callbacks(self) -> None` — Detach every scene hook and store listener (call on teardown).

<a id="slots--tools--_shot_sequencer--scene_selection"></a>
### `slots/tools/_shot_sequencer/scene_selection.py`

Tracks and the scene selection.

- **[`class SceneSelectionMixin`](tentacle/tentacle/slots/tools/_shot_sequencer/scene_selection.py#L22)** — Tracks, and the scene selection that follows the sequencer's.
  - `SceneSelectionMixin.hide_track(self, track_names) -> None` — Hide one or more tracks by name, persist, and rebuild the widget.
  - `SceneSelectionMixin.show_track(self, track_name: str) -> None` — Un-hide a track by object name, persist, and rebuild the widget.
  - `SceneSelectionMixin.delete_track(self, track_names) -> None` — Permanently remove objects from all shots and rebuild the widget.
  - `SceneSelectionMixin.on_selection_changed(self, clip_ids: list) -> None` — Select the clicked clips' objects, and their CHANNEL if they name one.
  - `SceneSelectionMixin.on_track_selected(self, track_names: list) -> None` — Select the objects whose track labels were clicked in the header.
  - `SceneSelectionMixin.on_sub_track_selected(self, rows: list) -> None` — Select a channel when its sub-row label is clicked in the header.
  - `SceneSelectionMixin.on_clip_locked(self, clip_id: int, locked: bool) -> None` — Persist per-object clip lock and propagate to sibling clips.
  - `SceneSelectionMixin.on_track_menu(self, menu, track_names) -> None` — Add the track actions to the track header's context menu.
  - `SceneSelectionMixin.on_header_menu(self, menu) -> None` — Add settings actions to the header background context menu (none).
  - `SceneSelectionMixin.on_key_selection_changed(self, key_groups: list) -> None` — Sync the host's Graph Editor key selection to the sequencer's.
  - `SceneSelectionMixin.on_clip_renamed(self, clip_id: int, new_label: str) -> None` — Inline rename of a clip: display-only (an object's name owns its

<a id="slots--tools--_shot_sequencer--shot_edit_dialog"></a>
### `slots/tools/_shot_sequencer/shot_edit_dialog.py`

The Shot Sequencer's small shot dialog: :class:`ShotEditDialog`.

- **[`class ShotEditDialog`](tentacle/tentacle/slots/tools/_shot_sequencer/shot_edit_dialog.py#L13)** — Lightweight dialog for creating or editing a shot.
  - `ShotEditDialog.show(parent=None, name: str = '', start: float = 1.0, end: float = 100.0, description: str = '', title: str = 'Shot', validate=None)` *(static)* — Show a modal dialog and return the result tuple or ``None``.

<a id="slots--tools--_shot_sequencer--shot_lane"></a>
### `slots/tools/_shot_sequencer/shot_lane.py`

The shot lane: its context menu and the shot structure edits.

- **[`class ShotLaneMixin`](tentacle/tentacle/slots/tools/_shot_sequencer/shot_lane.py#L20)** — The shot lane's menus and the shot structure edits they run.
  - `ShotLaneMixin.on_zone_context_menu(self, zone: str, time: float, global_pos) -> None` — Build a context menu specific to the clicked zone.
  - `ShotLaneMixin.delete_shot(self, shot_id: int) -> None` — Delete *shot_id* with its contents, closing the timeline behind it.
  - `ShotLaneMixin.delete_shots(self, scope: str = 'stale') -> None` — Delete the shots of *scope*, after naming them.
  - `ShotLaneMixin.move_shot_to_position(self, shot_id: int, position: int) -> None` — Re-slot *shot_id* at 1-based *position*, pushing the rest along.
  - `ShotLaneMixin.merge_shot_with(self, shot_id: int, other_id: int) -> None` — Fuse two neighbouring shots into one spanning both.
  - `ShotLaneMixin.split_shot_at(self, shot_id: int, time: float) -> None` — Cut *shot_id* in two at *time*, leaving its content where it is.

<a id="slots--tools--_shot_sequencer--shot_layer"></a>
### `slots/tools/_shot_sequencer/shot_layer.py`

The shot layer: the Shot Sequencer's shots on uitk's timeline.

- **[`class GapOverlay`](tentacle/tentacle/slots/tools/_shot_sequencer/shot_layer.py#L30)** — Diagonal-hatch overlay for a gap between shots (behaviour).
  - `GapOverlay.item_class(cls, sb)` *(class)* — The gap's scene-item class: this behaviour first, then uitk's
  - `GapOverlay.boundingRect(self) -> QtCore.QRectF`
  - `GapOverlay.hoverEnterEvent(self, event)`
  - `GapOverlay.hoverLeaveEvent(self, event)`
  - `GapOverlay.hoverMoveEvent(self, event)`
  - `GapOverlay.mousePressEvent(self, event)`
  - `GapOverlay.mouseMoveEvent(self, event)`
  - `GapOverlay.mouseReleaseEvent(self, event)`
  - `GapOverlay.contextMenuEvent(self, event)`
  - `GapOverlay.paint(self, painter: QtGui.QPainter, option, widget=None)`
- **[`class ShotLayer(QtCore.QObject)`](tentacle/tentacle/slots/tools/_shot_sequencer/shot_layer.py#L478)** — The Shot Sequencer's layer on a ``SequencerWidget`` (module docstring).
  - `ShotLayer.of(cls, sequencer, sb)` *(class)* — The shot layer on *sequencer*, added on first use.
  - `ShotLayer.set_shot_blocks(self, blocks: list) -> None` — Show one band per shot on the lane.
  - `ShotLayer.clear_shot_blocks(self) -> None` — Remove every band from the lane.
  - `ShotLayer.selected_shot(self) -> Optional[dict]` — The block marked ``active``, or ``None``.
  - `ShotLayer.shot_block_at(self, time: float) -> Optional[dict]` — The block containing *time*, or ``None``.
  - `ShotLayer.add_gap_overlay(self, start: float, end: float, color: str = '#555555', alpha: int = 120, locked: bool = False, tail: bool = False, head: bool = False) -> None` — Add a diagonal-hatch overlay for a gap between shots.
  - `ShotLayer.clear_gap_overlays(self) -> None` — Remove every gap overlay (deferred-safe: a release may be on the stack).
  - `ShotLayer.set_all_gap_overlays_locked(self, locked: bool) -> None` — Set the locked state on every gap overlay.
  - `ShotLayer.show_gap_overlays(self) -> bool` *(property)* — Whether the gap overlays show (the timeline menu's Show Gap Overlays).
  - `ShotLayer.paint_lane(self, painter: QtGui.QPainter, rect: QtCore.QRectF) -> None` — Draw one band per shot in the lane's strip.
  - `ShotLayer.mouse_press(self, event) -> bool` — Ctrl+Shift+Click anywhere switches to the shot there;
  - `ShotLayer.mouse_move(self, event) -> bool` — A lane drag's move (Alt: about the centre);
  - `ShotLayer.mouse_release(self, event) -> bool` — End a lane drag: the highlight emits if a bound moved.
  - `ShotLayer.gesture_group_at(self, viewport_pos) -> Optional[str]` — ``"Shot bounds"`` over the lane's grabs, a cap or the highlight's
  - `ShotLayer.claims_press(self, scene_pos) -> bool` — An unlocked gap's PAINTED rect keeps a press from the range
  - `ShotLayer.legend(self, editor: str, rows: Tuple) -> Tuple` — The track editor's legend with the shot grammar: the shot groups
  - `ShotLayer.context_entries(self, time: float, entries: list) -> list` — The timeline menu: the range overlays are the shots', and the gap
  - `ShotLayer.menu_zone(self, zone: str, time: float) -> str` — A right-click at a time some shot covers is the shot lane's,
  - `ShotLayer.time_bounds(self) -> Optional[Tuple[float, float]]` — The shots' and gaps' extent: a shot that no longer encloses any
  - `ShotLayer.relayout(self) -> None` — Re-derive the gaps' geometry: their height follows the rows.
  - `ShotLayer.clear(self) -> None` — The widget was cleared: no gaps, no bands.

<a id="slots--tools--_shot_sequencer--shot_nav"></a>
### `slots/tools/_shot_sequencer/shot_nav.py`

Shot navigation and combobox synchronization.

- **[`class ShotNavMixin`](tentacle/tentacle/slots/tools/_shot_sequencer/shot_nav.py#L19)** — Mixin supplying shot selection and navigation.
  - `ShotNavMixin.select_shot(self, shot_id: int) -> None` — Set the view's playback range to the shot and select its objects.
  - `ShotNavMixin.on_shot_block_clicked(self, shot_name: str) -> None` — Select a shot by name when its block is clicked in the shot lane.

<a id="slots--tools--_shot_sequencer--transport"></a>
### `slots/tools/_shot_sequencer/transport.py`

Transport: the playhead, audio scrub and the transport row.

- **[`class TransportMixin`](tentacle/tentacle/slots/tools/_shot_sequencer/transport.py#L15)** — The playhead, audible scrubbing and the transport button row.
  - `TransportMixin.on_playhead_moved(self, frame: float) -> None` — Move the scene's time to the widget playhead.

<a id="slots--tools--_shot_sequencer--undo_ledger"></a>
### `slots/tools/_shot_sequencer/undo_ledger.py`

The shot sequencer's undo ledger.

- **[`class UndoLedgerMixin`](tentacle/tentacle/slots/tools/_shot_sequencer/undo_ledger.py#L13)** — Shot-boundary restore points, and the panel's Undo / Redo.
  - `UndoLedgerMixin.on_undo(self) -> None` — Handle undo_requested from the widget: one step of the host's undo,
  - `UndoLedgerMixin.on_redo(self) -> None` — Handle redo_requested from the widget (see :meth:`on_undo`).

<a id="slots--tools--_shot_sequencer--widget_sync"></a>
### `slots/tools/_shot_sequencer/widget_sync.py`

Widget sync: rebuilding the sequencer from the scene.

- **[`class WidgetSyncMixin`](tentacle/tentacle/slots/tools/_shot_sequencer/widget_sync.py#L25)** — Rebuilding the widget from the scene: tracks, clips, sub-rows, decoration.
  - `WidgetSyncMixin.refresh(self) -> None` — Clear cached segments and rebuild the sequencer widget.

<a id="slots--tools--_shots--controller"></a>
### `slots/tools/_shots/controller.py`

The Shots panel's controller: the scene's shot settings, the selected shot's

- **[`class ShotsController(pythontk.LoggingMixin)`](tentacle/tentacle/slots/tools/_shots/controller.py#L31)** — Business logic for the Shots settings panel.
  - `ShotsController.remove_callbacks(self) -> None` — Remove store listeners and invalidation subscription (call on teardown).
  - `ShotsController.refresh_state(self) -> None` — Central enable/disable refresh for all Shots UI widgets.
  - `ShotsController.shot_label(shot) -> str` *(static)* — A shot's row in the dropdown: ``"Shot_1  [1–100]"``.
  - `ShotsController.on_navigate_shot(self, delta: int) -> None` — Make the previous (-1) or next (+1) shot the active one.
  - `ShotsController.on_new_shot(self) -> None` — Append a new shot and make it the active one.
  - `ShotsController.on_detection_changed(self, value: float) -> None`
  - `ShotsController.on_detection_mode_changed(self, index: int) -> None`
  - `ShotsController.on_initial_length_changed(self, value: float) -> None`
  - `ShotsController.on_snap_whole_frames_changed(self, checked: bool) -> None`
  - `ShotsController.on_drop_stale_shots_changed(self, checked: bool) -> None` — Whether this file's exports leave its stale shots out
  - `ShotsController.on_fit_mode_changed(self, index: int) -> None`
  - `ShotsController.on_gap_changed(self, value, scope: str = 'all', respect_locks: bool = True) -> None` — Set the store gap and re-space per *scope*.
  - `ShotsController.on_shot_selected(self, index: int) -> None` — User picked a different shot from the combobox.
  - `ShotsController.on_shot_name_changed(self, text: str) -> None` — Push a name the store accepts;
  - `ShotsController.on_shot_start_changed(self, value: float) -> None`
  - `ShotsController.on_shot_end_changed(self, value: float) -> None`
  - `ShotsController.on_shot_desc_changed(self, text: str) -> None`
  - `ShotsController.delete_scope(self) -> str` — The scope Delete Shots takes (``"stale"`` until one is picked).
  - `ShotsController.label_delete_shots(self) -> None` — Name the picked scope on Delete Shots: "Delete Empty Shots".
  - `ShotsController.swap_mode(self) -> str` — Swap With's mode: ``"swap"`` (until one is picked) or ``"copy"``.
  - `ShotsController.swap_target(self)` — The other shot's id -- swapped with, or copied over -- or ``None``.
  - `ShotsController.swap_retain(self) -> list` — The fields Swap With leaves in place: its checked Retain options.
  - `ShotsController.label_swap_shot(self, *_args) -> None` — Name the mode and the picked shot on Swap With: "Swap With: Shot_3",
  - `ShotsController.label_shift_all(self, *_args) -> None` — Name the frame on Shift To: "Shift To: 1".
  - `ShotsController.label_apply_gap(self, *_args) -> None` — Name the amount on Apply Gap: "Apply Gap: 12".
  - `ShotsController.on_delete_shot(self) -> None` — Delete the active shot after confirmation.
  - `ShotsController.confirm_removal(self, shots, scope: str = 'stale') -> bool` — Ask before ``ShotStore.remove_shots_in_scope``, naming *shots*.
  - `ShotsController.on_delete_shots(self, scope: str = 'stale') -> None` — Delete the shots of *scope* after naming them (All Shots group).
  - `ShotsController.on_move_shot(self) -> None` — Move the active shot to the position specified by spn_move_to.
  - `ShotsController.on_swap_shot(self) -> None` — Swap With, in the mode its option box picks: trade the active
  - `ShotsController.on_trim_empty(self, edge: str = 'both') -> None` — Trim empty space from the active shot, at *edge*.
  - `ShotsController.on_trim_all_shots(self, edge: str = 'both') -> None` — Trim empty space from every shot, at *edge*.
  - `ShotsController.on_shift_all_shots(self, start: float) -> None` — Shift every shot so the first one starts on *start*.
  - `ShotsController.on_add_space(self, edge: str = 'leading') -> None` — Pad the active shot with ``spn_space`` frames of room at *edge*.

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

<a id="slots--tools--_unity_bridge--_unity_panel"></a>
### `slots/tools/_unity_bridge/_unity_panel.py`

What every Unity panel shares: the 'Unity Project' row, the Editor combo, script management.

- **[`class UnityPanelMixin`](tentacle/tentacle/slots/tools/_unity_bridge/_unity_panel.py#L33)** — Unity-panel behavior shared by the three Unity Slots classes.
  - `UnityPanelMixin.template_dir(self) -> Path` *(property)*
  - `UnityPanelMixin.list_template_modes(self)`
  - `UnityPanelMixin.default_output_dir(self) -> str`

<a id="slots--tools--arnold_bridge"></a>
### `slots/tools/arnold_bridge.py`

Arnold Preview Shader: add or remove the Arnold preview network beside each

- **[`class ArnoldBridgeSlots(Slots, pythontk.LoggingMixin)`](tentacle/tentacle/slots/tools/arnold_bridge.py#L19)**
  - `ArnoldBridgeSlots.header_init(self, widget) -> None` — The header menu's Select Bridged Materials, and the help text.
  - `ArnoldBridgeSlots.cmb000_init(self, widget) -> None` — The Scope combo (Selected Objects by default).
  - `ArnoldBridgeSlots.b000(self) -> None` — Add Network.
  - `ArnoldBridgeSlots.b001(self) -> None` — Remove Network.
  - `ArnoldBridgeSlots.select_bridged(self) -> None` — Header menu: select every material that has a network (never the

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

<a id="slots--tools--blender_bridge"></a>
### `slots/tools/blender_bridge.py`

Blender Bridge: send the selection to a fresh Blender through an import

- **[`class BlenderBridgeSlots(HostBridge)`](tentacle/tentacle/slots/tools/blender_bridge.py#L34)**
  - `BlenderBridgeSlots.bridge_class(self)` *(property)*
  - `BlenderBridgeSlots.b000(self)` — Send the selected objects to Blender with the chosen template.

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

<a id="slots--tools--channels"></a>
### `slots/tools/channels.py`

Channels: the selected objects' attributes in one editable table.

- **[`class ChannelsSlots(Slots)`](tentacle/tentacle/slots/tools/channels.py#L48)** — Switchboard slots for the ``channels.ui`` panel.
  - `ChannelsSlots.launch(sb, targets=None, filter=None, search=None)` *(static)* — Open the panel, optionally pre-targeted (:meth:`apply_launch_config`).
  - `ChannelsSlots.apply_launch_config(self, targets=None, filter=None, search=None)` — Pin *targets*, pick *filter* and set the *search* pattern, then refresh.
  - `ChannelsSlots.header_init(self, widget)` — Create Attribute, the view toggles and the host's own editors.
  - `ChannelsSlots.show_create_menu(self, *args)` — Show the Create Attribute form.
  - `ChannelsSlots.cmb000_init(self, widget)` — The host's filters, and an invert action on the combo's option box.
  - `ChannelsSlots.cmb000(self, index)` — Filter changed: refresh.
  - `ChannelsSlots.tbl000_init(self, widget)` — Wire the table, build its menu once, start watching the scene, refresh.
  - `ChannelsSlots.cleanup_scene_callbacks(self)` — End every subscription this instance holds (scene, attributes,

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

<a id="slots--tools--hierarchy_sync"></a>
### `slots/tools/hierarchy_sync.py`

Hierarchy Sync: diff the scene's hierarchy against a reference file, then

- **[`class HierarchySyncSlots(Slots, pythontk.LoggingMixin)`](tentacle/tentacle/slots/tools/hierarchy_sync.py#L31)** — Switchboard slots for the ``hierarchy_sync.ui`` panel.
  - `HierarchySyncSlots.session(self)` *(property)* — The host's ``HierarchySyncSession`` (the controller's).
  - `HierarchySyncSlots.header_init(self, widget)` — The header menu (Dry Run, Log Level, Hide Ignored) and the help.
  - `HierarchySyncSlots.tree000_init(self, widget)` — The reference tree: read-only, its menu, and its header's browse,
  - `HierarchySyncSlots.tree001_init(self, widget)` — The current-scene tree: its menu, Delete key, header buttons,
  - `HierarchySyncSlots.cmb_diff_options_init(self, widget)` — The Diff options, rows of the combo under the Diff button (each
  - `HierarchySyncSlots.cmb_pull_options_init(self, widget)` — The Pull options, rows of the combo under the Pull button.
  - `HierarchySyncSlots.tb002_init(self, widget)` — The Pull button's tooltip.
  - `HierarchySyncSlots.tb003_init(self, widget)` — The Fix button's option box: what a repair does.
  - `HierarchySyncSlots.tb001(self, state=None)` — Diff: analyze, colour the trees, log the differences, and select and
  - `HierarchySyncSlots.tb002(self, state=None)` — Pull: bring the reference tree's selected objects into the scene.
  - `HierarchySyncSlots.tb003(self, state=None)` — Fix: repair the scene toward the reference, as the Fix options say.
  - `HierarchySyncSlots.b003(self)` — Browse for the reference scene.
  - `HierarchySyncSlots.b009(self)` — Refresh the reference tree.
  - `HierarchySyncSlots.b011(self)` — Show the differences in the trees.
  - `HierarchySyncSlots.b012(self)` — Analyze (no auto-select or expand: that is Diff's) and refresh the trees.
  - `HierarchySyncSlots.b005(self)` — Refresh the current-scene tree.
  - `HierarchySyncSlots.b006(self)` — Select the selected items' objects in the scene.
  - `HierarchySyncSlots.b007(self)` — Expand every item of the current-scene tree.
  - `HierarchySyncSlots.b008(self)` — Collapse every item of the current-scene tree.
  - `HierarchySyncSlots.b013(self)` — Ignore the reference tree's selected items.
  - `HierarchySyncSlots.b014(self)` — Unignore the reference tree's selected items.
  - `HierarchySyncSlots.b015(self)` — Ignore the current-scene tree's selected items.
  - `HierarchySyncSlots.b016(self)` — Unignore the current-scene tree's selected items.
  - `HierarchySyncSlots.b017(self)` — Rename current-scene items to reference names.
  - `HierarchySyncSlots.b018(self)` — Delete the selected objects from the scene (their subtrees with them).

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

<a id="slots--tools--light_rig"></a>
### `slots/tools/light_rig.py`

Light Rigs: save the scene's lights as named rigs, swap between them and

- **[`class LightRigSlots(Slots, pythontk.LoggingMixin)`](tentacle/tentacle/slots/tools/light_rig.py#L24)**
  - `LightRigSlots.refresh(self) -> None` — Re-read the library, select the scene's rig, and report the scene.
  - `LightRigSlots.header_init(self, widget) -> None`
  - `LightRigSlots.cmb000_init(self, widget) -> None`
  - `LightRigSlots.cmb000(self, index, widget) -> None` — Show the picked rig (picking never changes the scene).
  - `LightRigSlots.b000(self) -> None` — Apply the picked rig: it replaces the scene's rig (Swap Back returns).
  - `LightRigSlots.b001(self) -> None` — Swap Back: return to the rig the last Apply replaced.
  - `LightRigSlots.open_rig_folder(self) -> None` — Header menu: the folder the rig library lives in.
  - `LightRigSlots.prompt_save(self) -> None` — ＋: save the scene's rig under a new (or existing) name.

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

<a id="slots--tools--marmoset_bridge"></a>
### `slots/tools/marmoset_bridge.py`

Marmoset Bridge: send the selection to Marmoset Toolbag through a template.

- **[`class MarmosetBridgeSlots(HostBridge)`](tentacle/tentacle/slots/tools/marmoset_bridge.py#L24)**
  - `MarmosetBridgeSlots.bridge_class(self)` *(property)*
  - `MarmosetBridgeSlots.select_initial_template_index(self, pairs)` — Prefer 'bake (roundtrip)' then 'bake (send_to)', else the first entry.
  - `MarmosetBridgeSlots.b000(self)` — Send the Scope's objects with the chosen template + mode.

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

<a id="slots--tools--maya_bridge"></a>
### `slots/tools/maya_bridge.py`

Maya Bridge: send the selection to a fresh Maya through an import template.

- **[`class MayaBridgeSlots(HostBridge)`](tentacle/tentacle/slots/tools/maya_bridge.py#L21)**
  - `MayaBridgeSlots.bridge_class(self)` *(property)*
  - `MayaBridgeSlots.b000(self)` — Send the selected objects to Maya with the chosen template.

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

<a id="slots--tools--reference_manager"></a>
### `slots/tools/reference_manager.py`

Reference Manager: a workspace scene-file manager -- browse a project's scene

- **[`class ReferenceManagerSlots(Slots)`](tentacle/tentacle/slots/tools/reference_manager.py#L19)** — Switchboard slots for the ``reference_manager.ui`` panel.
  - `ReferenceManagerSlots.header_init(self, widget)` — Header buttons, the Naming / Filter-Display / Foreign Scenes / Include
  - `ReferenceManagerSlots.tbl000_init(self, widget)` — Table setup: the one-time construction, then the signals re-wired to this
  - `ReferenceManagerSlots.btn_open_scene(self)` — Open the right-clicked row's scene (a reopen on the open scene's row).
  - `ReferenceManagerSlots.btn_rename_scene(self)` — Rename the right-clicked row's scene.
  - `ReferenceManagerSlots.btn_delete_scene(self)` — Delete the right-clicked row's scene.
  - `ReferenceManagerSlots.btn_toggle_reference(self)` — Reference / unreference the right-clicked row.
  - `ReferenceManagerSlots.btn_unlink_import(self)` — Unlink and import the right-clicked row (make it local / import it).
  - `ReferenceManagerSlots.btn_open_file_location(self)` — Reveal the right-clicked row's file.
  - `ReferenceManagerSlots.btn_copy_path(self)` — Copy the right-clicked row's full path.
  - `ReferenceManagerSlots.txt000_init(self, widget)` — Root Directory: recent-folder pins, the browse / open / workspace actions
  - `ReferenceManagerSlots.b000(self)` — Browse for a root directory.
  - `ReferenceManagerSlots.b006(self)` — Open the root directory in the file explorer.
  - `ReferenceManagerSlots.b001(self)` — Set the root directory to the session's current workspace.
  - `ReferenceManagerSlots.btn_new_workspace(self)` — Create a workspace under the root.
  - `ReferenceManagerSlots.btn_mark_workspace(self)` — Mark the selected workspace folder as a project.
  - `ReferenceManagerSlots.chk000(self, checked)` — Recursive Search: rescan the root's workspaces.
  - `ReferenceManagerSlots.chk003(self, checked)` — Ignore Empty Workspaces: rescan the root's workspaces.
  - `ReferenceManagerSlots.cmb000_init(self, widget)` — Workspaces: its ▸ action sets the session's project to the selection (on
  - `ReferenceManagerSlots.cmb000(self, index, widget)` — Browse the selected workspace.
  - `ReferenceManagerSlots.txt001_init(self, widget)` — Filter: an on/off toggle (persisted), Ignore Case and what it matches.
  - `ReferenceManagerSlots.txt001(self, text)` — Filter the list by the typed text.
  - `ReferenceManagerSlots.chk_ignore_case(self, checked)` — Re-filter.
  - `ReferenceManagerSlots.cmb_filter_target(self, index, widget=None)` — Re-filter.
  - `ReferenceManagerSlots.chk_filter_suffix(self, checked)` — Re-filter.
  - `ReferenceManagerSlots.chk_filter_folder_structure(self, checked)` — Re-filter.
  - `ReferenceManagerSlots.chk_hide_suffix(self, checked)` — Re-label.
  - `ReferenceManagerSlots.chk_hide_extension(self, checked)` — Re-label.
  - `ReferenceManagerSlots.chk_show_notes_column(self, checked)` — Show / hide the Notes column.
  - `ReferenceManagerSlots.txt_suffix(self, text)` — Re-filter when a filter reads the suffix.
  - `ReferenceManagerSlots.txt_subfolder_structure(self, text)` — Re-filter when a filter reads the folder structure.
  - `ReferenceManagerSlots.btn_convert_assembly(self)` — Convert every reference to an assembly (Maya).
  - `ReferenceManagerSlots.btn_unlink_import_all(self)` — Unlink and import every reference.

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

<a id="slots--tools--rizom_bridge"></a>
### `slots/tools/rizom_bridge.py`

RizomUV Bridge: unwrap or pack the selection in RizomUV with a Lua preset and

- **[`class RizomBridgeSlots(HostBridge)`](tentacle/tentacle/slots/tools/rizom_bridge.py#L44)**
  - `RizomBridgeSlots.bridge_class(self)` *(property)*
  - `RizomBridgeSlots.params_module(self)` *(property)* — The registry, its rows gated by the installed RizomUV's version.
  - `RizomBridgeSlots.template_dir(self)` *(property)* — The Lua presets (``RizomUVBridge.SCRIPT_DIR``): the panel's templates.
  - `RizomBridgeSlots.list_template_modes(self)` — ``[(preset, ""), ...]``: the presets the installed RizomUV can run
  - `RizomBridgeSlots.b000(self)` — Run the chosen preset: a round trip, or the one-way ``send``.
  - `RizomBridgeSlots.open_uv_editor(self)` — Open the host's UV Editor (Blender: in a new window, since it has no

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

<a id="slots--tools--shot_sequencer"></a>
### `slots/tools/shot_sequencer.py`

Shot Sequencer: the scene's shots on a timeline -- objects as tracks, keys as

- **[`class ShotSequencerSlots(Slots, pythontk.LoggingMixin)`](tentacle/tentacle/slots/tools/shot_sequencer.py#L34)** — Switchboard slots for the ``shot_sequencer.ui`` panel.
  - `ShotSequencerSlots.header_init(self, widget)` — Build the header menu.
  - `ShotSequencerSlots.cmb_shot(self, index)` — A shot (or, in Markers mode, a marker) picked in the dropdown.
  - `ShotSequencerSlots.spn_snap(self, value)` — Set the snap interval on the sequencer widget.
  - `ShotSequencerSlots.btn_colors(self)` — Open the attribute color configuration dialog.
  - `ShotSequencerSlots.btn_shortcuts(self)` — Open the sequencer shortcut editor.
  - `ShotSequencerSlots.btn_shot_settings(self)` — Open the shared Shots panel (pinned, as Edit Shot does).

<a id="slots--tools--shots"></a>
### `slots/tools/shots.py`

Shots: the scene's shot settings, the selected shot's fields and edits, and

- **[`class ShotsSlots(Slots)`](tentacle/tentacle/slots/tools/shots.py#L17)** — Switchboard slots for the ``shots.ui`` panel.
  - `ShotsSlots.header_init(self, widget)` — Configure header help text.
  - `ShotsSlots.spn_detection(self, value)` — Detection threshold changed.
  - `ShotsSlots.cmb_detection_mode(self, index)` — Detection mode combobox changed.
  - `ShotsSlots.spn_initial_length(self, value)` — Initial shot length changed.
  - `ShotsSlots.cmb_fit_mode(self, index)` — Fit mode combobox changed.
  - `ShotsSlots.chk_snap_whole_frames(self, checked)` — Snap-to-whole-frames checkbox toggled.
  - `ShotsSlots.cmb_shot_select(self, index)` — Shot selector combobox changed.
  - `ShotsSlots.txt_shot_name(self, text=None)` — Shot name edited (debounced: the field's text, not the signal's).
  - `ShotsSlots.spn_shot_start(self, value)` — Shot start frame changed.
  - `ShotsSlots.spn_shot_end(self, value)` — Shot end frame changed.
  - `ShotsSlots.txt_shot_desc(self, text=None)` — Shot description edited (debounced: the field's text).
  - `ShotsSlots.b000(self)` — Delete the selected shot.
  - `ShotsSlots.btn_delete_shots(self)` — Delete the shots of the scope picked in the option box (All Shots).
  - `ShotsSlots.cmb_delete_scope(self, index)` — A scope was picked: the button says what a click now deletes.
  - `ShotsSlots.chk_drop_stale_shots(self, checked)` — Leave Stale Shots Out of Exports toggled (Delete Shots' option box).
  - `ShotsSlots.btn_move_shot(self)` — Move shot to the position in spn_move_to.
  - `ShotsSlots.btn_swap_shot(self)` — Swap with, or copy over, the shot picked in the option box.
  - `ShotsSlots.cmb_swap_with(self, index)` — A shot was picked: the button names what a click swaps with.
  - `ShotsSlots.cmb_swap_mode(self, index)` — A mode was picked: the button says what a click now does.
  - `ShotsSlots.btn_apply_gap(self)` — Apply the gap in the option box (spn_gap) to the scope it picks.
  - `ShotsSlots.btn_shift_all(self)` — Re-base every shot onto the frame in the option box (spn_shift_all).
  - `ShotsSlots.btn_trim_empty(self)` — Trim both ends of the selected shot.
  - `ShotsSlots.btn_trim_leading(self)` — Trim the selected shot's leading space.
  - `ShotsSlots.btn_trim_trailing(self)` — Trim the selected shot's trailing space.
  - `ShotsSlots.btn_trim_both(self)` — Trim both ends of the selected shot (option box twin of the button).
  - `ShotsSlots.btn_trim_all(self)` — Trim both ends of every shot.
  - `ShotsSlots.btn_trim_all_leading(self)` — Trim every shot's leading space.
  - `ShotsSlots.btn_trim_all_trailing(self)` — Trim every shot's trailing space.
  - `ShotsSlots.btn_trim_all_both(self)` — Trim both ends of every shot (option box twin of the button).
  - `ShotsSlots.btn_add_leading_space(self)` — Add empty room before the selected shot.
  - `ShotsSlots.btn_add_trailing_space(self)` — Add empty room after the selected shot.

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

<a id="slots--tools--substance_bridge"></a>
### `slots/tools/substance_bridge.py`

Substance Bridge: send the selection to Substance Painter through a template.

- **[`class SubstanceBridgeSlots(HostBridge)`](tentacle/tentacle/slots/tools/substance_bridge.py#L23)**
  - `SubstanceBridgeSlots.bridge_class(self)` *(property)*
  - `SubstanceBridgeSlots.select_initial_template_index(self, pairs)` — Default the panel to ``import (send_to)`` when it is available.
  - `SubstanceBridgeSlots.b000(self)` — Send the Scope's objects with the chosen template + mode.

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

<a id="slots--tools--texture_path_editor"></a>
### `slots/tools/texture_path_editor.py`

Texture Path Editor: inspect and fix the scene's texture paths.

- **[`class TexturePathEditorSlots(Slots, pythontk.LoggingMixin)`](tentacle/tentacle/slots/tools/texture_path_editor.py#L27)**
  - `TexturePathEditorSlots.labels(self)` *(property)* — The host's words for the node and shader columns and row actions.
  - `TexturePathEditorSlots.header_init(self, widget)` — The header menu: General / Naming / Path Management / Selection.
  - `TexturePathEditorSlots.tb_set_texture_directory_init(self, widget)` — The Set Directory option box: the relocate mode and Allow Missing Targets.
  - `TexturePathEditorSlots.tb_normalize_paths_init(self, widget)` — The Normalize Paths option box: what becomes of external textures.
  - `TexturePathEditorSlots.tb_resolve_missing_textures_init(self, widget)` — The Resolve Missing option box: one checkbox per strategy.
  - `TexturePathEditorSlots.tbl000_init(self, widget)` — Build the row menu once, then (re)populate the table.
  - `TexturePathEditorSlots.refresh_texture_table(self)` — Re-read the scene into the table (the header's refresh button).
  - `TexturePathEditorSlots.setup_formatting(self, widget)` — Mark the path cell red when its file is missing (amber when over-long
  - `TexturePathEditorSlots.open_source_images(self)` — Open the project's texture folder in the file explorer.
  - `TexturePathEditorSlots.reload_scene_textures(self)` — Re-read every scene texture from disk.
  - `TexturePathEditorSlots.tb_set_texture_directory(self, widget=None)` — Repath the scope's textures under a chosen directory.
  - `TexturePathEditorSlots.tb_find_and_copy_textures(self, widget=None)` — Open the Find & Copy panel over the current scope.
  - `TexturePathEditorSlots.tb_normalize_paths(self, widget=None)` — Rewrite the scope's paths inside the project to relative;
  - `TexturePathEditorSlots.make_paths_absolute(self)` — Rewrite the scope's relative paths to absolute -- inverse of Normalize.
  - `TexturePathEditorSlots.tb_resolve_missing_textures(self, widget=None)` — Rebind the scope's missing textures to files found in the project's
  - `TexturePathEditorSlots.select_textures_for_objects(self)` — Select the rows whose textures the scene selection's materials read.
  - `TexturePathEditorSlots.select_broken_paths(self)` — Select the rows whose texture file is missing.
  - `TexturePathEditorSlots.select_absolute_paths(self)` — Select the rows whose path is stored absolute -- Normalize candidates
  - `TexturePathEditorSlots.row_browse_for_file(self, selection=None)` — Repath the row's texture to a picked file (several rows: a folder).
  - `TexturePathEditorSlots.row_rename_file(self, selection=None)` — Rename one row's texture file, edited in its own cell: the path cell
  - `TexturePathEditorSlots.handle_cell_edit(self, row: int, col: int)` — An edited cell: the shader / node cells rename what they name, the
  - `TexturePathEditorSlots.select_material(self, selection=None)` — Select the scene objects using the selected rows' materials (a
  - `TexturePathEditorSlots.select_file_node(self, selection=None)` — Select the selected rows' texture nodes.
  - `TexturePathEditorSlots.row_show_in_hypershade(self, selection=None)` — Graph the selected rows' textures in the node editor.
  - `TexturePathEditorSlots.delete_file_node(self, selection=None)` — Delete the selected rows' texture nodes, confirmed with what it would
  - `TexturePathEditorSlots.cleanup_scene_callbacks(self)` — Drop the scene-change subscriptions.

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

<a id="slots--tools--unity_bridge"></a>
### `slots/tools/unity_bridge.py`

Unity Bridge: export the selection and copy the FBX into a Unity project's Assets/.

- **[`class UnityBridgeSlots(UnityPanelMixin, HostBridge)`](tentacle/tentacle/slots/tools/unity_bridge.py#L31)**
  - `UnityBridgeSlots.bridge_class(self)` *(property)*
  - `UnityBridgeSlots.make_bridge(self)` — The engine, or ``None`` while the optional unitytk is absent.
  - `UnityBridgeSlots.b000(self)` — Run the selected template: export-and-copy, or script management.

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

<a id="slots--tools--workspace_editor"></a>
### `slots/tools/workspace_editor.py`

Workspace Editor: the minimal take on Maya's File ▸ Project Window -- one

- **[`class WorkspaceEditorSlots(Slots, pythontk.LoggingMixin)`](tentacle/tentacle/slots/tools/workspace_editor.py#L41)**
  - `WorkspaceEditorSlots.header_init(self, widget)` — Rule add, view toggle, reset/clear, template combo, help text.
  - `WorkspaceEditorSlots.txt000_init(self, widget)` — Project Root: one full path (browse + open-folder option-box actions).
  - `WorkspaceEditorSlots.tbl000_init(self, widget)`
  - `WorkspaceEditorSlots.add_rule(self)` — Append an empty, editable rule row (saves once both cells are filled).
  - `WorkspaceEditorSlots.reset_row(self, row)` — Reset *row*'s location to the active template's default for its rule.
  - `WorkspaceEditorSlots.remove_row(self, row)` — Remove *row* and delete its rule from workspace.mel.
  - `WorkspaceEditorSlots.reset_rules(self)` — Restore the default file rules (the active template's) and save.
  - `WorkspaceEditorSlots.clear_rules(self)` — Remove every file rule and save (hand-written marker lines survive).
  - `WorkspaceEditorSlots.create_project(self)` — Build the project at the current root: marker + the active template's rule
  - `WorkspaceEditorSlots.open_folder(self)` — Open the project root in the system file browser.

<a id="slots--tools--workspace_map"></a>
### `slots/tools/workspace_map.py`

Workspace Map: browse a folder tree of project workspaces and switch the

- **[`class WorkspaceMapSlots(Slots, pythontk.LoggingMixin)`](tentacle/tentacle/slots/tools/workspace_map.py#L27)**
  - `WorkspaceMapSlots.header_init(self, widget)` — Project creation actions + help text.
  - `WorkspaceMapSlots.txt000_init(self, widget)` — The root directory field: browse, Set To Workspace, Recursive Search.
  - `WorkspaceMapSlots.txt001_init(self, widget)` — The workspace-name filter.
  - `WorkspaceMapSlots.tree000_init(self, widget)` — The workspace tree, its double-click and its right-click menu.
  - `WorkspaceMapSlots.update_current_dir(self, text: Optional[str] = None) -> None` — Retarget the scan at the root field's directory (rescans only when it
  - `WorkspaceMapSlots.update_tree(self, filter_text: Optional[str] = None) -> None` — Rebuild the tree from the last scan, narrowed to *filter_text*.
  - `WorkspaceMapSlots.populate_tree(self, tree_data: Dict) -> None` — Clear and refill the tree: a row per parent folder, its workspaces
  - `WorkspaceMapSlots.refresh_tree(self, invalidate: bool = False) -> None` — Refill the tree;
  - `WorkspaceMapSlots.selected_workspace(self) -> Optional[Dict]` — The workspace row under the tree cursor, or None (a folder row is none).
  - `WorkspaceMapSlots.filter_workspaces(self, text) -> None`
  - `WorkspaceMapSlots.b000(self) -> None` — Browse for the root directory.
  - `WorkspaceMapSlots.b001(self) -> None` — Set to Workspace.
  - `WorkspaceMapSlots.b002(self) -> None` — Refresh: rescan the root.
  - `WorkspaceMapSlots.set_to_workspace(self) -> None` — Set the root to the current workspace's folder.
  - `WorkspaceMapSlots.chk000(self, checked) -> None` — Recursive Search: rescan when it changes.
  - `WorkspaceMapSlots.btn_open_workspace(self) -> None` — Make the selected workspace the current project.
  - `WorkspaceMapSlots.btn_explore_folder(self) -> None` — Open the selected workspace's folder in the file browser.
  - `WorkspaceMapSlots.new_project(self) -> None` — Create a project under the root from the ACTIVE template.
  - `WorkspaceMapSlots.mark_root(self) -> None` — Mark the ROOT directory as a shared Maya/Blender project.
  - `WorkspaceMapSlots.save_template(self) -> None` — Publish the ACTIVE project's file rules as a named workspace template.

<a id="slots--transform"></a>
### `slots/transform.py`

Transform: one Slots class for both hosts.

- **[`class TransformSlots(Slots)`](tentacle/tentacle/slots/transform.py#L23)**
  - `TransformSlots.header_init(self, widget)` — Header: Fix Non-Orthogonal Axes and the Snap panel.
  - `TransformSlots.fix_non_ortho_axes(self)` — Fix Non-Orthogonal Axes: bake out shear on the selected objects.
  - `TransformSlots.b_snap_ts(self)` — Snap: open the shared Snap panel.
  - `TransformSlots.cmb002_init(self, widget)` — Align To: the modes the host offers.
  - `TransformSlots.cmb002(self, index, widget)` — Align To: run the chosen mode on the selection.
  - `TransformSlots.tb000_init(self, widget)` — Initialize Drop To Grid.
  - `TransformSlots.tb000(self, widget)` — Drop To Grid
  - `TransformSlots.tb001_init(self, widget)` — Initialize Scale Connected Edges (the scale factor option).
  - `TransformSlots.tb001(self, widget)` — Scale Connected Edges: each connected set of selected edges scales about
  - `TransformSlots.tb002_init(self, widget)` — Initialize Freeze Transforms.
  - `TransformSlots.tb002(self, widget)` — Freeze Transformations
  - `TransformSlots.b002_init(self, widget)` — Initialize Un-Freeze Transforms.
  - `TransformSlots.b_restore_axes(self)` — Restore Authored Axes: point the gizmo at the pre-freeze frame.
  - `TransformSlots.b002(self, widget)` — Un-Freeze Transforms: restore the channels Freeze stamped (the object's
  - `TransformSlots.tb005_init(self, widget)` — Initialize Move To.
  - `TransformSlots.tb005(self, widget)` — Move To: move the selected objects onto the target, by a chosen pivot.
  - `TransformSlots.b001(self)` — Match Scale: scale the first selected (Blender: the active) object to the
  - `TransformSlots.tb003_init(self, widget)` — Constraints: Edge / Surface / Make Live, seeded from the host.
  - `TransformSlots.chk024_init(self, widget)`
  - `TransformSlots.chk025_init(self, widget)`
  - `TransformSlots.chk026_init(self, widget)`
  - `TransformSlots.chk024(self, state, widget)` — Transform Constraints: Edge
  - `TransformSlots.chk025(self, state, widget)` — Transform Constraints: Surface
  - `TransformSlots.chk026(self, state, widget)` — Transform Constraints: Make Live (Blender: project onto surfaces)
  - `TransformSlots.tb004_init(self, widget)` — Snap: Move / Scale / Rotate increment snapping, seeded from the host.
  - `TransformSlots.chk021_init(self, widget)`
  - `TransformSlots.chk022_init(self, widget)`
  - `TransformSlots.chk023_init(self, widget)`
  - `TransformSlots.s021_init(self, widget)`
  - `TransformSlots.s022_init(self, widget)`
  - `TransformSlots.s023_init(self, widget)`
  - `TransformSlots.chk021(self, state, widget)` — Transform Snap: Move
  - `TransformSlots.chk022(self, state, widget)` — Transform Snap: Scale
  - `TransformSlots.chk023(self, state, widget)` — Transform Snap: Rotate
  - `TransformSlots.s021(self, value, widget)` — Transform Snap: the move increment.
  - `TransformSlots.s022(self, value, widget)` — Transform Snap: the scale increment.
  - `TransformSlots.s023(self, value, widget)` — Transform Snap: the rotate increment (degrees).

<a id="slots--utilities"></a>
### `slots/utilities.py`

Utilities: one Slots class for both hosts.

- **[`class UtilitiesSlots(Slots)`](tentacle/tentacle/slots/utilities.py#L15)**
  - `UtilitiesSlots.b000(self)` — Measure: activate the distance-measure tool (Maya's Distance Tool,
  - `UtilitiesSlots.b001(self)` — Annotation: the host's own.
  - `UtilitiesSlots.b002(self)` — Calculator: open the calculator panel.
  - `UtilitiesSlots.b003(self)` — Pencil: sketch with the host's pencil, Blue Pencil (Maya) or a new

<a id="tcl"></a>
### `tcl.py`

The host-agnostic entry point — one launcher snippet for every DCC.

- **[`class QtPlatformUnavailable(RuntimeError)`](tentacle/tentacle/tcl.py#L39)** — Qt cannot open a window in this host process, so the marking menu is off.
- **[`class Tcl(_TclInternal)`](tentacle/tentacle/tcl.py#L452)** — Launch tentacle in whichever DCC is hosting this process.
  - `Tcl.host(cls)` *(class)* — The DCC hosting this process (``'maya'``/``'blender'``/``'max'``), or None.
  - `Tcl.declared_dists(cls, host=None, include_self=True)` *(class)* — Every ecosystem distribution THIS install actually uses, for *host*.
  - `Tcl.prepare_reload(cls, host=None)` *(class)* — Release the host resources an in-place reload would ORPHAN.
  - `Tcl.reload_packages(cls, host=None)` *(class)* — Re-execute the ecosystem packages in dependency order, in place.
  - `Tcl.dispose_retired(instances)` *(static)* — Schedule deletion of the pre-reload marking menus in *instances*.
  - `Tcl.qt_key_name(cls, key_show=None)` *(class)* — Normalize an activation key to its Qt name: ``'Z'`` and ``'Key_Z'`` both → ``'Key_Z'``.
  - `Tcl.resolve_key(cls, key_show=None, context_tags=None)` *(class)* — The activation key to launch with: **user-persisted > ``key_show`` > :attr:`DEFAULT_KEY`**.
  - `Tcl.unserved_tools(context_tags=None)` *(static)* — The shared tools no host in *context_tags* serves (``slots.tools.HOSTS``):
  - `Tcl.register_shared(switchboard)` *(static)* — Register on *switchboard* what every host shares (CODE_STANDARD section 3).
  - `Tcl.chord_bindings(cls, key_show=None, chord_target=None)` *(class)* — The default chord→menu table for ``key_show`` (bare or Qt-named).
  - `Tcl.banner(cls, template=None, force=False)` *(class)* — Print the startup banner — the one sanctioned emitter of :func:`tentacle.greeting`.
  - `Tcl.launch(cls, key_show=None, **kwargs)` *(class)* — Start tentacle in the host DCC, deferring startup the way that host requires.
  - `Tcl.reload(cls)` *(class)* — Settings > Reload Scripts: tear tentacle down, reload the ecosystem in
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
