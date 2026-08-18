# tentacle — API Registry

_Auto-generated. Do not edit by hand. Refresh via `m3trik/scripts/generate_api_registry.py`._

_Generated: 2026-08-18_

## Index

- [`__init__.py`](#__init__)
- [`slots/_edit.py`](#slots--_edit) — Shared, DCC-agnostic behavior for the ``edit`` panel.
- [`slots/_hud_warnings.py`](#slots--_hud_warnings) — Shared HUD warning framework (DCC-agnostic).
- [`slots/_lighting.py`](#slots--_lighting) — Shared surface for the ``lighting`` panel's Maya and Blender forks.
- [`slots/_main.py`](#slots--_main) — Behavior shared by the Maya and Blender ``main`` start menus' Workspace tab.
- [`slots/_materials.py`](#slots--_materials) — Shared, DCC-agnostic behavior for the ``materials`` panel.
- [`slots/_preferences.py`](#slots--_preferences) — Shared, DCC-agnostic behavior for the ``preferences`` panel.
- [`slots/_rendering.py`](#slots--_rendering) — Shared, DCC-agnostic behavior for the ``rendering`` panel.
- [`slots/_scene.py`](#slots--_scene) — Behavior shared by the Maya and Blender ``scene`` panels.
- [`slots/_selection.py`](#slots--_selection) — Behavior shared by the Maya and Blender ``selection`` panels.
- [`slots/_settings.py`](#slots--_settings) — Shared, DCC-agnostic behavior for the ``settings`` panel.
- [`slots/_slots.py`](#slots--_slots)
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
- [`slots/blender/normals.py`](#slots--blender--normals)
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
- [`slots/maya/normals.py`](#slots--maya--normals)
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
- [`tcl.py`](#tcl) — The host-agnostic entry point — one launcher snippet for every DCC.
- [`tcl_blender.py`](#tcl_blender) — Blender entry point for tentacle's Qt marking menu — host + keymap bridge + launcher in one.
- [`tcl_max.py`](#tcl_max)
- [`tcl_maya.py`](#tcl_maya)

---

<a id="__init__"></a>
### `__init__.py`

- [`greeting(string, outputToConsole=True)`](tentacle/tentacle/__init__.py#L49) — Format a string using preset variables.

<a id="slots--_edit"></a>
### `slots/_edit.py`

Shared, DCC-agnostic behavior for the ``edit`` panel.

- **[`class EditMixin`](tentacle/tentacle/slots/_edit.py#L17)** — DCC-agnostic ``edit`` slot behavior (Mesh Cleanup user-feedback formatting).
  - `EditMixin.mesh_cleanup_tooltip(self)` — Rich tooltip for the Mesh Cleanup button (``edit.tb000``).
  - `EditMixin.cleanup_popup_html(header, rows)` *(static)* — Minimal HTML for the Mesh Cleanup popup (``sb.message_box``) — glanceable, one fact per line.
  - `EditMixin.cleanup_console_report(title, lines)` *(static)* — Detailed Mesh Cleanup report to stdout (Maya Script Editor / Blender system console).
  - `EditMixin.report_cleanup_failure(self, scope, mode_label, exc)` — Report a Mesh Cleanup failure through both channels — a detailed console line and a

<a id="slots--_hud_warnings"></a>
### `slots/_hud_warnings.py`

Shared HUD warning framework (DCC-agnostic).

- **[`class HudWarningsMixin`](tentacle/tentacle/slots/_hud_warnings.py#L22)**
  - `HudWarningsMixin.evaluate_warnings(self) -> list` — Return the subset of WARNING_DEFS whose check fires and is enabled.
  - `HudWarningsMixin.insert_warning_icons(self, hud, warnings) -> None` — Insert a single-line row of colored badges;
  - `HudWarningsMixin.insert_warning_details(self, hud, warnings) -> None` — Insert a formatted detail line per active warning.

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

- **[`class MaterialsMixin`](tentacle/tentacle/slots/_materials.py#L66)** — DCC-agnostic ``materials`` slot behavior.
  - `MaterialsMixin.lbl005(self)` — Rename the current material.
  - `MaterialsMixin.b003(self, widget=None)` — Get + Select (submenu): adopt the selection's material, then select its users.

<a id="slots--_preferences"></a>
### `slots/_preferences.py`

Shared, DCC-agnostic behavior for the ``preferences`` panel.

- **[`class PreferencesMixin`](tentacle/tentacle/slots/_preferences.py#L17)** — DCC-agnostic ``preferences`` slot behavior.
  - `PreferencesMixin.cmb004_init(self, widget)` — Marking-menu (radial startmenu / submenu) window theme.
  - `PreferencesMixin.cmb004(self, index, widget)` — Apply the marking-menu theme (persists + re-themes live windows).
  - `PreferencesMixin.cmb005_init(self, widget)` — Standalone tool-window theme.
  - `PreferencesMixin.cmb005(self, index, widget)` — Apply the standalone-window theme (persists + re-themes live windows).

<a id="slots--_rendering"></a>
### `slots/_rendering.py`

Shared, DCC-agnostic behavior for the ``rendering`` panel.

- **[`class RenderingMixin`](tentacle/tentacle/slots/_rendering.py#L22)** — DCC-agnostic ``rendering`` slot behavior (WebXR Preview option box + push).
  - `RenderingMixin.webxr_init(self, widget, sidecar_tooltip)` — Build the WebXR Preview option box (``rendering.tb002``).
  - `RenderingMixin.webxr_push(self, widget, engine, has_selection, log_hint)` — Read the option box and push to the live preview (``rendering.tb002``).

<a id="slots--_scene"></a>
### `slots/_scene.py`

Behavior shared by the Maya and Blender ``scene`` panels.

- **[`class SceneMixin`](tentacle/tentacle/slots/_scene.py#L34)** — Shared ``scene`` panel behavior.
  - `SceneMixin.tb003(self, widget)` — Export Scene in the chosen format, using the configured options.
  - `SceneMixin.list003_init(self, widget)` — Tools list: the scene actions that used to sit loose in the header
  - `SceneMixin.tb002_init(self, widget)` — Fix Non-Orthogonal Axes — option box.
  - `SceneMixin.tb002(self, widget)` — Fix Non-Orthogonal Axes.

<a id="slots--_selection"></a>
### `slots/_selection.py`

Behavior shared by the Maya and Blender ``selection`` panels.

- **[`class SelectionMixin`](tentacle/tentacle/slots/_selection.py#L22)** — Shared ``selection`` panel behavior.
  - `SelectionMixin.list001_init(self, widget)` — Convert To: one flat list of the fork's conversions.

<a id="slots--_settings"></a>
### `slots/_settings.py`

Shared, DCC-agnostic behavior for the ``settings`` panel.

- **[`class SettingsMixin`](tentacle/tentacle/slots/_settings.py#L18)** — DCC-agnostic ``settings`` slot behavior.
  - `SettingsMixin.header_init(self, widget)` — Initialize header
  - `SettingsMixin.tb000(self)` — Update Package
  - `SettingsMixin.check_for_update(self)` — Check the whole ecosystem for updates and upgrade what's outdated.
  - `SettingsMixin.b020(self)` — UI Style Editor
  - `SettingsMixin.b021(self)` — Shortcut Editor
  - `SettingsMixin.b022(self)` — UI Browser: open the tentacle UI browser (search, show/hide registered UIs).
  - `SettingsMixin.b023(self)` — Global Shortcuts: open the shortcut editor focused on the global
  - `SettingsMixin.cmb_bind_default_init(self, widget)` — Default menu (activation key only).
  - `SettingsMixin.cmb_bind_left_init(self, widget)` — Left mouse button.
  - `SettingsMixin.cmb_bind_middle_init(self, widget)` — Middle mouse button.
  - `SettingsMixin.cmb_bind_right_init(self, widget)` — Right mouse button.
  - `SettingsMixin.cmb_bind_left_right_init(self, widget)` — Left + Right mouse buttons.
  - `SettingsMixin.b_reset_bindings(self)` — Reset marking-menu bindings (routes + activation key) to defaults.

<a id="slots--_slots"></a>
### `slots/_slots.py`

- **[`class Slots(QtCore.QObject)`](tentacle/tentacle/slots/_slots.py#L7)** — Provides methods that can be triggered by widgets in the ui.
  - `Slots.mirror_app_state(widget, seed=None) -> None` *(static)* — Declare that *widget*'s value mirrors live DCC state, optionally seeding it.
  - `Slots.add_slot_widget(self, sublist, widget_class=None, **kwargs)` — Add a slot-wired widget as an ExpandableList sublist entry.
  - `Slots.toggle_camera_view(self)` — Toggle between the last two viewport-camera views in slot history.
  - `Slots.register_camera_view_toggle(self)` — Wire :meth:`toggle_camera_view` to its triggers.

<a id="slots--_uv"></a>
### `slots/_uv.py`

Behavior shared by the Maya and Blender UV panels.

- **[`class UvMixin`](tentacle/tentacle/slots/_uv.py#L6)** — Shared UV-panel behavior (see ``slots/maya/uv.py``, ``slots/blender/uv.py``).
  - `UvMixin.b030_init(self, widget)` — Stack button — non-checkable text button with the stack option box.

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

- **[`class Animation(SlotsBlender)`](tentacle/tentacle/slots/blender/animation.py#L8)** — Blender port of the shared ``animation`` menu.
  - `Animation.list000_init(self, widget)` — Tools list: Sequencing / Repair / Bake / Playback / Info.
  - `Animation.list000(self, item)` — Dispatch a Tools leaf to its slot method.
  - `Animation.tb000_init(self, widget)`
  - `Animation.tb000(self, widget)` — Go To Frame (absolute, or relative offset from the current frame);
  - `Animation.tb001_init(self, widget)`
  - `Animation.tb001(self, widget)` — Invert Keys (mirror key times and/or values — reverses timing / flips motion).
  - `Animation.tb003_init(self, widget)`
  - `Animation.tb003(self, widget)` — Stagger Keys (re-time selected objects sequentially).
  - `Animation.tb009_init(self, widget)`
  - `Animation.tb009(self, widget)` — Snap Keys to Frames
  - `Animation.tb010_init(self, widget)`
  - `Animation.tb010(self, widget)` — Delete Keys (clear all animation on the selection, or only a time-scoped subset).
  - `Animation.tb002_init(self, widget)`
  - `Animation.tb002(self, widget)` — Adjust Key Spacing (shift every key at/after the frame by the amount).
  - `Animation.tb004_init(self, widget)`
  - `Animation.tb004(self, widget)` — Transfer Keys (active object → other selected, independent copies).
  - `Animation.tb005_init(self, widget)`
  - `Animation.tb005(self, widget)` — Add/Remove Intermediate Keys
  - `Animation.tb013_init(self, widget)`
  - `Animation.tb013(self, widget)` — Select Keys (``select_control_point`` — shows in the Dope Sheet / Graph Editor).
  - `Animation.tb007_init(self, widget)`
  - `Animation.tb007(self, widget)` — Align Selected Keyframes (keys picked in the Dope Sheet / Graph Editor).
  - `Animation.tb008_init(self, widget)`
  - `Animation.tb008(self, widget)` — Set Visibility Keys (key viewport + render visibility).
  - `Animation.tb006_init(self, widget)`
  - `Animation.tb006(self, widget)` — Move Keys (align the selection's keys to the current frame).
  - `Animation.tb012_init(self, widget)`
  - `Animation.tb012(self, widget)` — Copy Keys (from the active object;
  - `Animation.tb018_init(self, widget)`
  - `Animation.tb018(self, widget)` — Paste Keys (independent copies onto the selection).
  - `Animation.tb014_init(self, widget)`
  - `Animation.tb014(self, widget)` — Scale Keys
  - `Animation.tb017_init(self, widget)`
  - `Animation.tb017(self, widget)` — Set Tangents (key interpolation type — stepped / linear / smooth).
  - `Animation.b005(self)` — Fit Playback Range (to the keyed extent of the selection, or the whole scene).
  - `Animation.tb011_init(self, widget)`
  - `Animation.tb011(self, widget)` — Tie/Untie Keyframes
  - `Animation.tb016_init(self, widget)`
  - `Animation.tb016(self, widget)` — Get Animation Info — render a per-object keyframe summary to the viewer dialog.
  - `Animation.tb019_init(self, widget)`
  - `Animation.tb019(self, widget)` — Optimize Keys — remove redundant animation data.
  - `Animation.tb015_init(self, widget)`
  - `Animation.tb015(self, widget)` — Repair Corrupted Curves — strip NaN/infinite or out-of-range keys;
  - `Animation.tb020(self, widget)` — Smart Bake
  - `Animation.b000(self)` — Open Shot Sequencer — native blendertk panel (anim_utils/shots/shot_sequencer), 1:1
  - `Animation.b004(self)` — Open Shot Manifest — native blendertk panel (anim_utils/shots/shot_manifest), 1:1 with

<a id="slots--blender--blender"></a>
### `slots/blender/blender.py`

- **[`class Blender(SlotsBlender)`](tentacle/tentacle/slots/blender/blender.py#L6)** — Base-name anchor for the Blender both-button chord menu (``blender#startmenu``).

<a id="slots--blender--cameras"></a>
### `slots/blender/cameras.py`

- **[`class Cameras(SlotsBlender)`](tentacle/tentacle/slots/blender/cameras.py#L8)** — Blender port of the shared ``cameras`` menu.
  - `Cameras.list000_init(self, widget)` — Initialize Camera Options List
  - `Cameras.list000(self, item)` — Camera Options List
  - `Cameras.b000(self)` — Cameras: Back View
  - `Cameras.b001(self)` — Cameras: Top View
  - `Cameras.b002(self)` — Cameras: Right View
  - `Cameras.b003(self)` — Cameras: Left View
  - `Cameras.b004(self)` — Cameras: Perspective View
  - `Cameras.b005(self)` — Cameras: Front View
  - `Cameras.b006(self)` — Cameras: Bottom View
  - `Cameras.b007(self)` — Cameras: Align View (align the viewport to the active element's normal and frame
  - `Cameras.b010(self)` — Camera: Dolly — arm the interactive dolly tool (LMB-drag to move the eye in/out).
  - `Cameras.b011(self)` — Camera: Roll — arm the interactive roll tool (LMB-drag to roll the view about its axis).
  - `Cameras.b012(self)` — Camera: Truck — arm the interactive track/pan tool (LMB-drag to pan the view).
  - `Cameras.b013(self)` — Camera: Orbit — arm the interactive tumble tool (LMB-drag to orbit the view).

<a id="slots--blender--crease"></a>
### `slots/blender/crease.py`

- **[`class Crease(SlotsBlender)`](tentacle/tentacle/slots/blender/crease.py#L7)** — Blender port of the shared ``crease`` menu.
  - `Crease.tb000_init(self, widget)`
  - `Crease.tb000(self, widget)` — Crease
  - `Crease.b002(self, widget)` — Transfer Crease Edges (active mesh → other selected, native Data-Transfer).

<a id="slots--blender--deformation"></a>
### `slots/blender/deformation.py`

- **[`class Deformation(SlotsBlender)`](tentacle/tentacle/slots/blender/deformation.py#L6)** — Blender port of the shared ``deformation`` menu.
  - `Deformation.tb001_init(self, widget)` — Init Curtain Generator launcher.
  - `Deformation.tb001(self, widget)` — Curtain Generator — open the curtain panel.

<a id="slots--blender--display"></a>
### `slots/blender/display.py`

- **[`class DisplaySlots(SlotsBlender)`](tentacle/tentacle/slots/blender/display.py#L8)** — Blender port of the shared ``display`` menu.
  - `DisplaySlots.header_init(self, widget)` — Header menu: the submenu's Display expandable list — hover a row to
  - `DisplaySlots.list000_init(self, widget)` — Initialize Display expandable list (categories → actions).
  - `DisplaySlots.list000(self, item)` — Dispatch a Display action and report state via message_box.
  - `DisplaySlots.b013(self)` — Explode View — open the Exploded View panel (Explode / Un-Explode / Un-Explode All /
  - `DisplaySlots.b014(self)` — Color ID — swatch palette to color-code objects (material / object color / vertex).

<a id="slots--blender--duplicate"></a>
### `slots/blender/duplicate.py`

- **[`class Duplicate(SlotsBlender)`](tentacle/tentacle/slots/blender/duplicate.py#L8)** — Blender port of the shared ``duplicate`` menu.
  - `Duplicate.header_init(self, widget)`
  - `Duplicate.tb000_init(self, widget)`
  - `Duplicate.tb000(self, widget)` — Convert to Instances (selected objects share the active object's data).
  - `Duplicate.tb001_init(self, widget)`
  - `Duplicate.tb001(self, widget)` — Select Instanced Objects
  - `Duplicate.tb002_init(self, widget)` — Initialize Auto Instance — configure option-box menu.
  - `Duplicate.tb002(self, widget)` — Auto Instance: find and convert geometrically identical meshes
  - `Duplicate.b005(self)` — Uninstance Selected Objects (make their data single-user).
  - `Duplicate.b000(self)` — Mirror
  - `Duplicate.b006(self)` — Duplicate Linear
  - `Duplicate.b007(self)` — Duplicate Radial
  - `Duplicate.b008(self)` — Duplicate Grid

<a id="slots--blender--edit"></a>
### `slots/blender/edit.py`

- **[`class Edit(EditMixin, SlotsBlender)`](tentacle/tentacle/slots/blender/edit.py#L8)** — Blender port of the shared ``edit`` menu.
  - `Edit.header_init(self, widget)`
  - `Edit.b_channels(self)` — Channels — open the spreadsheet-style channel editor (btk.Channels panel).
  - `Edit.tb000_init(self, widget)`
  - `Edit.tb000(self, widget)` — Mesh Cleanup — Repair (fix) or, in Select mode, select the matched problem geometry.
  - `Edit.tb002(self, widget)` — Delete Selected (objects in object mode, components by select mode in edit mode).
  - `Edit.list000_init(self, widget)` — Initialize Create Primitives list — 6 categories, mirroring Maya's Polygon/NURBS/
  - `Edit.list000(self, item)` — Create Primitive — branch per category the way Maya's list000 does (Control/Curve/
  - `Edit.list001_init(self, widget)` — Initialize Convert list.
  - `Edit.list001(self, item)` — Convert the selected object(s) to another type (or run a Convert-list action that
  - `Edit.b000(self)` — Cut On Axis
  - `Edit.cmb000_init(self, widget)` — Initialize the Transfer operations menu.
  - `Edit.cmb000(self, index, widget)` — Transfer — dispatch the selected transfer operation.
  - `Edit.tb001_init(self, widget)` — Optimize — relabel the shared "Delete History" button (its text lives in the shared
  - `Edit.tb001(self, widget)` — Optimize — purge orphaned (zero-user) datablocks;
  - `Edit.tb004_init(self, widget)` — Object Locking — Lock/Unlock selector (mirror of Maya's cmb_lock).
  - `Edit.tb004(self, widget)` — Object Locking — Blender's analogue of Maya's node lock: toggle ``hide_select`` (make

<a id="slots--blender--editors"></a>
### `slots/blender/editors.py`

- **[`class Editors(SlotsBlender)`](tentacle/tentacle/slots/blender/editors.py#L7)** — Blender port of the shared ``editors`` menu.
  - `Editors.list000_init(self, widget)` — Initialize the editors list (categories → Blender editors).
  - `Editors.list000(self, item)` — Open the picked editor in a new window (category headers are nav-only).
  - `Editors.b000(self)` — Attributes (Properties editor)
  - `Editors.b001(self)` — Outliner
  - `Editors.b002(self)` — Tool (active-tool settings live in the Properties editor's Tool tab)
  - `Editors.b003(self)` — Layers (Blender's collections live in the Outliner)
  - `Editors.b004(self)` — Channels (object data lives in the Properties editor)
  - `Editors.b005(self)` — Node Editor (Shader Editor)
  - `Editors.b006_init(self, widget)` — Relabel: Dependency Graph → Geometry Nodes.
  - `Editors.b006(self)` — Geometry Nodes (substitute for Maya's Dependency Graph)
  - `Editors.b007_init(self, widget)` — Relabel: Status Line → UV Editor.
  - `Editors.b007(self)` — UV Editor (substitute for Maya's Status Line toggle)
  - `Editors.b008_init(self, widget)` — Relabel: Shelf → Image Editor.
  - `Editors.b008(self)` — Image Editor (substitute for Maya's Shelf toggle)
  - `Editors.b009(self)` — Time & Range — toggle the Timeline docked along the bottom of the viewport, in place.
  - `Editors.b010(self)` — Script Output — the shared ``uitk.ScriptOutput`` console (syntax-highlighted
  - `Editors.b011(self)` — Command Line (Python Console)
  - `Editors.b012_init(self, widget)` — Relabel: Help Line → Graph Editor.
  - `Editors.b012(self)` — Graph Editor (substitute for Maya's Help Line toggle)
  - `Editors.b013_init(self, widget)` — Relabel: Tool Box → Text Editor.
  - `Editors.b013(self)` — Text Editor (substitute for Maya's Tool Box toggle)

<a id="slots--blender--hud"></a>
### `slots/blender/hud.py`

- **[`class StatusMixin`](tentacle/tentacle/slots/blender/hud.py#L10)**
  - `StatusMixin.insert_scene_status(self, hud) -> None`
- **[`class SelectionMixin`](tentacle/tentacle/slots/blender/hud.py#L40)**
  - `SelectionMixin.insert_selection_info(self, hud, selection) -> None`
  - `SelectionMixin.insert_component_info(self, hud, active) -> None` — Selected/total component counts for the mesh being edited (cheap:
- **[`class WarningsMixin(HudWarningsMixin)`](tentacle/tentacle/slots/blender/hud.py#L107)** — Blender HUD warnings — the framework lives in the shared
- **[`class HudSlots(SlotsBlender, StatusMixin, SelectionMixin, WarningsMixin)`](tentacle/tentacle/slots/blender/hud.py#L168)** — HUD Slots for Blender, providing scene and selection information.
  - `HudSlots.request_hud_build(self) -> None` — Start a new HUD build request, only the latest token will be used.
  - `HudSlots.construct_hud(self) -> None`

<a id="slots--blender--lighting"></a>
### `slots/blender/lighting.py`

- **[`class Lighting(LightingMixin, SlotsBlender)`](tentacle/tentacle/slots/blender/lighting.py#L8)** — Blender port of the shared ``lighting`` menu.
  - `Lighting.b000(self)` — Launch the HDR Manager (world-environment HDRI panel).
  - `Lighting.b001(self)` — Launch the Lightmap Baker (Cycles-bake → game-engine lightmaps).
  - `Lighting.tb000_init(self, widget)` — Lights From Geometry Init
  - `Lighting.tb000(self, widget)` — Create real area lights from the selected fixture meshes.

<a id="slots--blender--main"></a>
### `slots/blender/main.py`

- **[`class Main(MainMixin, SlotsBlender)`](tentacle/tentacle/slots/blender/main.py#L9)** — Blender port of the shared ``main`` start menu — a workspace switcher (primary) with
  - `Main.list000_init(self, widget)` — Initialize the Workspace tab.
  - `Main.list000(self, item)` — Workspace tab dispatch — editing actions, recent-workspace selection, and the

<a id="slots--blender--materials"></a>
### `slots/blender/materials.py`

- **[`class MaterialsSlots(MaterialsMixin, SlotsBlender)`](tentacle/tentacle/slots/blender/materials.py#L9)** — Blender port of the shared ``materials`` menu — mirrors the Maya slot's workflow against
  - `MaterialsSlots.b_shader_editor(self)` — Shader Editor — Blender's analogue of Maya's Hypershade.
  - `MaterialsSlots.cmb002_init(self, widget)` — Materials combo: scene materials with color swatches + option box (Cleanup) + a
  - `MaterialsSlots.cmb002(self, index, widget)` — Current Material (selection only — assignment is on the b-buttons).
  - `MaterialsSlots.tb000_init(self, widget)`
  - `MaterialsSlots.tb000(self, widget)` — Select By Material — the option box supplies the parameters.
  - `MaterialsSlots.select_by_mat(self, shell=False, in_selection=False, get_first=False, add=False, unassigned=False)` — Select the geometry carrying the current material.
  - `MaterialsSlots.tb001_init(self, widget)` — Get Material Info — option box.
  - `MaterialsSlots.tb001(self, widget)` — Get Material Info — render a formatted report to the text-view dialog.
  - `MaterialsSlots.list000_init(self, widget)` — Assign list: assign-current root + New / Random + scene materials.
  - `MaterialsSlots.list000(self, item)` — Assign list: root assigns the current material;
  - `MaterialsSlots.list001_init(self, widget)` — Tools list (Setup tools with a native Blender op).
  - `MaterialsSlots.list001(self, item)` — Dispatch a Tools-list selection to its slot method.
  - `MaterialsSlots.b002(self, widget=None)` — Get Material: set the combo to the selection's material.
  - `MaterialsSlots.b004(self, widget=None)` — Assign Random
  - `MaterialsSlots.b006(self, widget=None)` — Assign New Material
  - `MaterialsSlots.b013(self)` — Reload Scene Textures
  - `MaterialsSlots.b014(self)` — Remove Duplicate Materials
  - `MaterialsSlots.b015(self, widget=None)` — Delete All Unused Materials
  - `MaterialsSlots.lbl002(self)` — Delete the current material.
  - `MaterialsSlots.lbl004(self)` — Select Node — select the object(s) using the current material.
  - `MaterialsSlots.lbl006(self)` — Open in Editor — graph the current material in the Shader Editor.
  - `MaterialsSlots.lbl007(self)` — Rename the current material by stripping trailing integers/underscores.
  - `MaterialsSlots.lbl007_global(self)` — Strip trailing ints/underscores from ALL scene materials (skips on-collision).
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

<a id="slots--blender--normals"></a>
### `slots/blender/normals.py`

- **[`class Normals(SlotsBlender)`](tentacle/tentacle/slots/blender/normals.py#L7)** — Blender port of the shared ``normals`` menu.
  - `Normals.tb001_init(self, widget)`
  - `Normals.tb001(self, widget)` — Set Normals By Angle
  - `Normals.tb004_init(self, widget)`
  - `Normals.tb004(self, widget)` — Average Normals — soften edges so vertex normals are averaged across shared faces;
  - `Normals.b000(self)` — Soften Edge Normals (smooth shading).
  - `Normals.b001(self)` — Harden Edge Normals (flat shading).
  - `Normals.b006(self)` — Set To Face (vertex normals follow faces = flat shading).
  - `Normals.tb010_init(self, widget)` — Maya's five ``polyNormal`` modes, 1:1 (same items, same default index) — the
  - `Normals.tb010(self, widget)` — Reverse Normals (Maya polyNormal modes: Reverse / Propagate / Conform /
  - `Normals.b002(self)` — Transfer Normals (active mesh → other selected, native Data-Transfer
  - `Normals.b004(self)` — Toggle lock/unlock vertex normals — Maya parity (m_lock_vertex_normals): report the

<a id="slots--blender--nurbs"></a>
### `slots/blender/nurbs.py`

- **[`class Nurbs(SlotsBlender)`](tentacle/tentacle/slots/blender/nurbs.py#L10)** — Blender port of the shared ``nurbs`` menu.
  - `Nurbs.b058(self)` — Curve to Tube (curve bevel).
  - `Nurbs.tb000_init(self, widget)`
  - `Nurbs.tb000(self, widget)` — Revolve (Screw modifier;
  - `Nurbs.tb001_init(self, widget)`
  - `Nurbs.tb001(self, widget)` — Loft — bridge the selected profile curves / mesh loops into a surface (btk.loft).
  - `Nurbs.list000_init(self, widget)` — Initialize the Nurbs expandable list (categories -> curve actions) — same
  - `Nurbs.list000(self, item)` — Dispatch a Nurbs leaf action (mirrors Maya's list000: no-op on a node that still
  - `Nurbs.b030(self)` — Extrude Curve Profile — build a surface from the selected curve(s), the Blender
  - `Nurbs.b056(self)` — Image Tracer (native wrap: trace the active image-empty to Grease Pencil,

<a id="slots--blender--pivot"></a>
### `slots/blender/pivot.py`

- **[`class Pivot(SlotsBlender)`](tentacle/tentacle/slots/blender/pivot.py#L8)** — Blender port of the shared ``pivot`` menu.
  - `Pivot.tb000_init(self, widget)`
  - `Pivot.tb000(self, widget)` — Reset Pivot
  - `Pivot.tb001_init(self, widget)`
  - `Pivot.tb001(self, widget)` — Center Pivot
  - `Pivot.b000(self)` — Center Pivot: Object
  - `Pivot.b001(self)` — Center Pivot: Component
  - `Pivot.b002(self, widget)` — Center Pivot: World
  - `Pivot.tb002_init(self, widget)` — Transfer Pivot options — the Mirror combo only.
  - `Pivot.tb002(self, widget)` — Transfer Pivot — move the selected objects' origins onto the **active** object's origin.
  - `Pivot.tb003_init(self, widget)`
  - `Pivot.tb003(self, widget)` — World-Aligned Pivot — a faithful mirror of Maya's ``tb003`` *including its
  - `Pivot.b004(self)` — Bake Pivot — bake Blender's *temporary* pivot, the 3D cursor, into the selected

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
  - `PolygonsSlots.b009(self)` — Collapse Component (Maya-twin split: a face mask collapses per-region
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

- **[`class Preferences(PreferencesMixin, SlotsBlender)`](tentacle/tentacle/slots/blender/preferences.py#L11)** — Blender port of the shared ``preferences`` menu.
  - `Preferences.cmb001_init(self, widget)`
  - `Preferences.cmb001(self, index, widget)` — Set Working Units: Linear
  - `Preferences.cmb002_init(self, widget)`
  - `Preferences.cmb002(self, index, widget)` — Set Working Units: Time (frame rate)
  - `Preferences.s000_init(self, widget)`
  - `Preferences.s001_init(self, widget)`
  - `Preferences.b001(self)` — Color Settings → Blender Preferences (Themes).
  - `Preferences.cmb003_init(self, widget)` — App-style / theme selector — mirrors Blender's Preferences > Themes dropdown.
  - `Preferences.cmb003(self, index, widget)` — Apply the selected native theme preset (Blender's built-in, the user's own, or our
  - `Preferences.b008(self)` — Hotkeys → Blender Preferences (Keymap).
  - `Preferences.b009(self)` — Plug-In Manager → Blender Preferences (Add-ons).
  - `Preferences.b010(self)` — Settings/Preferences → Blender Preferences (Interface).
  - `Preferences.b011(self)` — Macro Manager — the unified shortcut editor over the blendertk macros

<a id="slots--blender--rendering"></a>
### `slots/blender/rendering.py`

- **[`class Rendering(RenderingMixin, SlotsBlender)`](tentacle/tentacle/slots/blender/rendering.py#L8)** — Blender port of the shared ``rendering`` menu.
  - `Rendering.tb000_init(self, widget)`
  - `Rendering.tb000(self, widget)` — Export Playblast (OpenGL viewport render of the chosen frame range / format).
  - `Rendering.tb001_init(self, widget)` — Render: pick the camera and renderer, then render the current frame.
  - `Rendering.tb001(self, widget)` — Render Current Frame
  - `Rendering.tb002_init(self, widget)` — WebXR Preview: scope and export options for the live browser preview.
  - `Rendering.tb002(self, widget)` — Push the selection to the live WebXR preview.
  - `Rendering.b001(self)` — Render Settings (Properties editor, Render tab)
  - `Rendering.b003(self)` — Render Setup — Maya's render-layer manager maps onto Blender's **View Layers**
  - `Rendering.b004(self)` — Rendering Flags — Maya's per-object render flags map onto Blender's per-object ray

<a id="slots--blender--rigging"></a>
### `slots/blender/rigging.py`

- **[`class Rigging(SlotsBlender)`](tentacle/tentacle/slots/blender/rigging.py#L9)** — Blender port of the shared ``rigging`` menu.
  - `Rigging.header_init(self, widget)`
  - `Rigging.b020(self)` — Rebind Skin Clusters — refresh each selected mesh's Armature modifier (re-point it at its
  - `Rigging.cmb001_init(self, widget)`
  - `Rigging.cmb001(self, index, widget)` — Create rigging primitives.
  - `Rigging.tb000_init(self, widget)`
  - `Rigging.tb000(self, widget)` — Toggle Display Local Rotation Axes — object axes (show_axis), or armature bone axes
  - `Rigging.tb001_init(self, widget)`
  - `Rigging.tb001(self, widget)` — Constraint Switch — drive the active object's constraints' influence from a single custom
  - `Rigging.tb003_init(self, widget)`
  - `Rigging.tb003(self, widget)` — Create Locator at Selection — an Empty (locator) at each selected object's origin,
  - `Rigging.b003(self)` — Remove Locator — dissolve each selected locator (Empty) the way mayatk's
  - `Rigging.tb004_init(self, widget)`
  - `Rigging.tb004(self, widget)` — Lock/Unlock Attributes (transform channel lock flags, per the chosen scope).
  - `Rigging.cmb002_init(self, widget)`
  - `Rigging.cmb002(self, index, widget)` — Quick Rig — a procedural rig opens its panel (mayatk parity);
  - `Rigging.b004(self)` — Render Opacity — co-located blendertk panel (keyable per-object ``opacity`` prop driving

<a id="slots--blender--scene"></a>
### `slots/blender/scene.py`

- **[`class SceneSlots(SceneMixin, SlotsBlender)`](tentacle/tentacle/slots/blender/scene.py#L12)** — Blender port of the shared ``scene`` menu.
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
  - `SceneSlots.b005(self)` — Naming — open the panel (Find / Rename / Convert Case / Strip Chars / Suffix by
  - `SceneSlots.b008(self)` — Export Selection (FBX, selected objects only).
  - `SceneSlots.b013(self)` — Mesh Converter (FBX -> GLB).
  - `SceneSlots.b_cleanup(self)` — Scene Cleanup — purge orphan datablocks (no users / no fake user).
  - `SceneSlots.tb001_init(self, widget)`
  - `SceneSlots.tb001(self, widget)` — Get Scene Info — render the budgeted, sectioned audit (btk.analyze_scene) to the viewer.
  - `SceneSlots.b004(self)` — Hierarchy Sync — diff/repair the scene hierarchy against a reference .blend
  - `SceneSlots.b003(self)` — Audio Clips — native blendertk panel over the Video Sequence Editor (add/remove/
  - `SceneSlots.b015(self)` — Blendshape Animator — native blendertk panel (base+target mesh -> keyed shape key,
  - `SceneSlots.b017(self)` — Scene Metadata — dump the tool-authored data-node channels to the viewer (mirror of

<a id="slots--blender--selection"></a>
### `slots/blender/selection.py`

- **[`class Selection(SelectionMixin, SlotsBlender)`](tentacle/tentacle/slots/blender/selection.py#L8)** — Blender port of the shared ``selection`` menu.
  - `Selection.tb000_init(self, widget)`
  - `Selection.tb000(self, widget)` — Select Nth
  - `Selection.tb001_init(self, widget)`
  - `Selection.tb001(self, widget)` — Select Similar — object-level similarity by topology / area / bounding-box metrics
  - `Selection.tb002_init(self, widget)`
  - `Selection.tb002(self, widget)` — Select Island (connected region;
  - `Selection.tb003_init(self, widget)`
  - `Selection.tb003(self, widget)` — Select Edges By Angle (within the Low–High range, via ``btk.select_edges_by_angle``).
  - `Selection.list001(self, item)` — Convert the current selection to another component type (Maya Convert-To parity).
  - `Selection.chk004_init(self, widget)` — Reflect the live viewport X-ray state (the DCC owns it — see ``mirror_app_state``).
  - `Selection.chk004(self, state, widget)` — Ignore Backfacing — toggle viewport X-ray (occlude) so only front faces select.
  - `Selection.chk005_init(self, widget)`
  - `Selection.chk006_init(self, widget)` — Select Style: Lasso — mirrors the active tool;
  - `Selection.chk007_init(self, widget)` — Select Style: Circle — mirrors the active tool;
  - `Selection.chk005(self, state, widget)` — Select Style: Box (Marquee)
  - `Selection.chk006(self, state, widget)` — Select Style: Lasso
  - `Selection.chk007(self, state, widget)` — Select Style: Circle (Paint)
  - `Selection.b001(self)` — Toggle Selectability of the selected object(s).
  - `Selection.b002_init(self, widget)` — Selection constraint: Angle.
  - `Selection.b002(self, widget)` — Selection constraint: Angle (one-shot expand).
  - `Selection.b003_init(self, widget)` — Selection constraint: Border.
  - `Selection.b003(self, widget)` — Selection constraint: Border (one-shot expand).
  - `Selection.b004_init(self, widget)` — Selection constraint: Edge Loop.
  - `Selection.b004(self, widget)` — Selection constraint: Edge Loop (one-shot expand).
  - `Selection.b005_init(self, widget)` — Selection constraint: Edge Ring.
  - `Selection.b005(self, widget)` — Selection constraint: Edge Ring (one-shot expand).
  - `Selection.b006_init(self, widget)` — Selection constraint: Shell.
  - `Selection.b006(self, widget)` — Selection constraint: Shell (one-shot expand).
  - `Selection.b007_init(self, widget)` — Selection constraint: UV Edge Loop.
  - `Selection.b007(self, widget)` — Selection constraint: UV Edge Loop (one-shot expand).
  - `Selection.cmb001_init(self, widget)` — Reorder Selection — backed by the rolled ``btk.SelectionOrder`` tracker (Blender
  - `Selection.cmb001(self, index, widget)` — Reorder Selection (sort via ``btk.reorder_objects``, record the order on
  - `Selection.list000_init(self, widget)` — Select by Type: hierarchical type list.
  - `Selection.tb004_init(self, widget)` — Select by Type settings menu (mirror of the Maya slot's tb004).
  - `Selection.tb004(self, widget)` — Select by Type settings: open the scope/mode menu.
  - `Selection.list000(self, item)` — Select by Type (native bpy predicates via ``btk.Selection``).

<a id="slots--blender--settings"></a>
### `slots/blender/settings.py`

- **[`class Settings(SettingsMixin, SlotsBlender)`](tentacle/tentacle/slots/blender/settings.py#L9)** — Blender fork of the shared ``settings`` menu.
  - `Settings.tb001(self)` — Reload Scripts (tear down, reload the tentacle ecosystem in place, re-register).

<a id="slots--blender--subdivision"></a>
### `slots/blender/subdivision.py`

- **[`class Subdivision(SlotsBlender)`](tentacle/tentacle/slots/blender/subdivision.py#L7)** — Blender port of the shared ``subdivision`` menu.
  - `Subdivision.tb000_init(self, widget)`
  - `Subdivision.tb000(self, widget)` — Decimate: reduce face count by collapse percentage or coplanar-face dissolve.
  - `Subdivision.s000_init(self, widget)` — Division Level — reflect the active object's live viewport subdivision level.
  - `Subdivision.s001_init(self, widget)` — Tesselation Level — reflect the active object's live render subdivision level.
  - `Subdivision.s000(self, value, widget)` — Division Level (live Subdivision-Surface viewport level).
  - `Subdivision.s001(self, value, widget)` — Tesselation Level (Subdivision-Surface render level).
  - `Subdivision.b000(self)` — Quadrangulate (tris -> quads).
  - `Subdivision.b001(self)` — Triangulate
  - `Subdivision.b005(self)` — Reduce (decimate to 50%) — whole meshes, or the selected components in Edit Mode.
  - `Subdivision.b008(self)` — Add Divisions - Subdivide Mesh
  - `Subdivision.b011(self)` — Apply Smooth Preview — bake the live Subdivision-Surface modifier to polygons
  - `Subdivision.b028(self)` — Quad Draw (Blender's retopo equivalent: the Poly Build tool) — EDIT_MESH-only, so

<a id="slots--blender--symmetry"></a>
### `slots/blender/symmetry.py`

- **[`class Symmetry(SlotsBlender)`](tentacle/tentacle/slots/blender/symmetry.py#L6)** — Blender port of the shared ``symmetry`` menu.
  - `Symmetry.chk000_init(self, widget)` — Set initial symmetry state from the active mesh.
  - `Symmetry.chk001_init(self, widget)` — Symmetry Y — mirrors the active mesh;
  - `Symmetry.chk002_init(self, widget)` — Symmetry Z — mirrors the active mesh;
  - `Symmetry.chk000(self, state, widget)` — Symmetry X
  - `Symmetry.chk001(self, state, widget)` — Symmetry Y
  - `Symmetry.chk002(self, state, widget)` — Symmetry Z
  - `Symmetry.chk004(self, state, widget)` — Symmetry: match by position (Blender mirror flags are always object-space;
  - `Symmetry.chk004_init(self, widget)` — Match-by-position — mirrors the active mesh;
  - `Symmetry.chk005_init(self, widget)` — Set symmetry reference space (position vs topology), mirrored from the active mesh.
  - `Symmetry.chk005(self, state, widget)` — Symmetry: Topo (match mirrored verts by topology instead of position).

<a id="slots--blender--transform"></a>
### `slots/blender/transform.py`

- **[`class TransformSlots(SlotsBlender)`](tentacle/tentacle/slots/blender/transform.py#L10)** — Blender port of the shared ``transform`` menu.
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
  - `TransformSlots.tb001_init(self, widget)`
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

- **[`class Utilities(SlotsBlender)`](tentacle/tentacle/slots/blender/utilities.py#L7)** — Blender port of the shared ``utilities`` menu.
  - `Utilities.b000(self)` — Measure
  - `Utilities.b001(self)` — Annotation
  - `Utilities.b002(self)` — Calculator
  - `Utilities.b003(self)` — Grease Pencil (add an empty stroke object to draw into)

<a id="slots--blender--uv"></a>
### `slots/blender/uv.py`

- **[`class Uv(UvMixin, SlotsBlender)`](tentacle/tentacle/slots/blender/uv.py#L10)** — Blender port of the shared ``uv`` menu.
  - `Uv.get_map_size(self)` — Get the map size from the combobox as an int.
  - `Uv.tb000_init(self, widget)`
  - `Uv.tb000(self, widget)` — Pack UVs (optionally equal-texel-density pre-scaled), then moved into the target
  - `Uv.tb001_init(self, widget)`
  - `Uv.tb001(self, widget)` — Auto Unwrap (Smart UV Project, or an external unwrapping engine).
  - `Uv.tb004_init(self, widget)`
  - `Uv.tb004(self, widget)` — Unfold (unwrap, then optionally relax, axis-align, and stack similar shells).
  - `Uv.tb009_init(self, widget)`
  - `Uv.tb009(self, widget)` — Cut Cylinder — seam by crease angle, then unfold.
  - `Uv.b005(self)` — Cut UVs (mark seam on selected edges)
  - `Uv.b011(self)` — Sew UVs (clear seam on selected edges)
  - `Uv.b021(self, widget)` — Unfold and Pack UVs
  - `Uv.tb007_init(self, widget)` — Cleanup UV Sets option box (reuses the Maya objectNames + labels — same options,
  - `Uv.tb007(self, widget)` — Cleanup UV Sets (standardize/clean the UV layers — mirror of Maya's cleanup_uv_sets).
  - `Uv.header_init(self, widget)` — Header menu — Create UV Snapshot + RizomUV Bridge (reuse the Maya objectNames + labels,
  - `Uv.uv_snapshot(self)` — Create UV Snapshot — export the active mesh's UV layout to an image.
  - `Uv.b031(self)` — Open UV Editor
  - `Uv.b000_init(self, widget)` — Transfer UVs option box — scope + similarity tolerance (mirror of Maya's;
  - `Uv.b000(self, widget)` — Transfer UVs — from the active mesh, to the other selected meshes (Selection
  - `Uv.b003(self)` — Get Texel Density (into the s003 readout, against the cmb003 map size).
  - `Uv.b004(self)` — Set Texel Density (from the s003 value, against the cmb003 map size).
  - `Uv.b029_init(self, widget)` — Initialize Pin/Unpin button — non-checkable text button.
  - `Uv.b029(self, widget)` — Pin / Unpin UVs (dual-state toggle, Maya parity: first click on a fresh selection
  - `Uv.tb022_init(self, widget)`
  - `Uv.tb022(self, widget)` — Cut UV Hard Edges (mark seams on edges whose dihedral angle is in the [low, high]
  - `Uv.b030(self, widget)` — Stack / Unstack shells (dual-state toggle: first click stacks the targeted
  - `Uv.b032(self)` — RizomUV Bridge — co-located blendertk panel (round-trip Lua presets + one-way send).
  - `Uv.b033(self)` — Open the Shell Xform panel — the ``More..`` button in the Transform group.
  - `Uv.cmb003(self, index, widget)` — UV Map Size — passive input;
  - `Uv.s003(self, value, widget)` — Texel Density — passive input;

<a id="slots--maya--_slots_maya"></a>
### `slots/maya/_slots_maya.py`

- **[`class SlotsMaya(Slots)`](tentacle/tentacle/slots/maya/_slots_maya.py#L8)** — App specific methods inherited by all other app specific slot classes.
  - `SlotsMaya.require_selection(self, message=None, **kwargs)` — The current selection, or ``None`` — after a message box — when it is empty.

<a id="slots--maya--animation"></a>
### `slots/maya/animation.py`

- **[`class Animation(SlotsMaya)`](tentacle/tentacle/slots/maya/animation.py#L8)**
  - `Animation.list000_init(self, widget)` — Tools list: Sequencing / Repair / Bake / Playback / Info.
  - `Animation.list000(self, item)` — Dispatch a Tools leaf to its slot method.
  - `Animation.b006(self)` — Repair Visibility Tangents
  - `Animation.tb000_init(self, widget)` — Go To Frame Init
  - `Animation.tb000(self, widget)` — Go To Frame: jump the time slider to the next/previous key or a snap target.
  - `Animation.tb001_init(self, widget)` — Invert Keyframes Init
  - `Animation.tb001(self, widget)` — Invert keyframes (selected keys preferred, fallback to all keys).
  - `Animation.tb002_init(self, widget)` — Adjust Spacing Init
  - `Animation.tb002(self, widget)` — Adjust spacing
  - `Animation.tb003_init(self, widget)` — Stagger Keys Init
  - `Animation.tb003(self, widget)` — Stagger Keys
  - `Animation.tb004_init(self, widget)` — Transfer Keys Init
  - `Animation.tb004(self, widget)` — Transfer Keys
  - `Animation.tb005_init(self, widget)` — Add/Remove Intermediate Keys Init
  - `Animation.tb005(self, widget)` — Add/Remove Intermediate Keys
  - `Animation.tb006_init(self, widget)` — Move Keys Init
  - `Animation.tb006(self, widget)` — Move Keys: move the selected keys in time, with optional spacing/alignment.
  - `Animation.tb007_init(self, widget)` — Align Selected Keyframes Init
  - `Animation.tb007(self, widget)` — Align Selected Keyframes
  - `Animation.tb008_init(self, widget)` — Set Visibility Keys Init
  - `Animation.tb008(self, widget)` — Set Visibility Keys
  - `Animation.tb009_init(self, widget)` — Snap Keys to Frames Init
  - `Animation.tb009(self, widget)` — Snap Keys to Frames
  - `Animation.tb010_init(self, widget)` — Delete Keys Init
  - `Animation.tb010(self, widget)` — Delete Keys: delete keys on the selection over a chosen time range.
  - `Animation.tb011_init(self, widget)` — Tie/Untie Keyframes Init
  - `Animation.tb011(self, widget)` — Tie/Untie Keyframes
  - `Animation.tb013_init(self, widget)` — Select Keys Init
  - `Animation.tb013(self, widget)` — Select Keys: select keys on the selection within a frame range.
  - `Animation.tb014_init(self, widget)` — Scale Keys Init
  - `Animation.tb014(self, widget)` — Scale Keys: scale the selected keys in time about a pivot.
  - `Animation.tb015_init(self, widget)` — Repair Corrupted Curves - Initialize option box
  - `Animation.tb015(self, widget)` — Repair Corrupted Curves
  - `Animation.tb016_init(self, widget)` — Get Animation Info — option box.
  - `Animation.tb016(self, widget)` — Get Animation Info — render the report to the viewer dialog.
  - `Animation.tb017_init(self, widget)` — Step Tangents Init
  - `Animation.tb017(self, widget)` — Step Tangents — set stepped tangents on keys.
  - `Animation.tb012_init(self, widget)` — Copy Keys Init
  - `Animation.tb012(self, widget)` — Copy Keys: copy the selected objects' keys for later paste.
  - `Animation.tb018_init(self, widget)` — Paste Keys Init
  - `Animation.tb018(self, widget)` — Paste Keys: paste previously copied keys onto the selection.
  - `Animation.tb019_init(self, widget)` — Optimize Keys Init
  - `Animation.tb019(self, widget)` — Optimize Keys — remove redundant animation data.
  - `Animation.tb020(self, widget)` — Smart Bake
  - `Animation.b000(self)` — Open Shot Sequencer
  - `Animation.b004(self)` — Open Shot Manifest
  - `Animation.b005(self)` — Fit Playback Range

<a id="slots--maya--arnold"></a>
### `slots/maya/arnold.py`

- **[`class ArnoldSlots(SlotsMaya)`](tentacle/tentacle/slots/maya/arnold.py#L9)**

<a id="slots--maya--cache"></a>
### `slots/maya/cache.py`

- **[`class CacheSlots(SlotsMaya)`](tentacle/tentacle/slots/maya/cache.py#L9)**

<a id="slots--maya--cameras"></a>
### `slots/maya/cameras.py`

- **[`class Cameras(SlotsMaya)`](tentacle/tentacle/slots/maya/cameras.py#L9)**
  - `Cameras.list000_init(self, widget)` — Initialize Camera Options List
  - `Cameras.list000(self, item)` — Camera Options List
  - `Cameras.b000(self)` — Cameras: Back View
  - `Cameras.b001(self)` — Cameras: Top View
  - `Cameras.b002(self)` — Cameras: Right View
  - `Cameras.b003(self)` — Cameras: Left View
  - `Cameras.b004(self)` — Cameras: Perspective View
  - `Cameras.b005(self)` — Cameras: Front View
  - `Cameras.b006(self)` — Cameras: Bottom View
  - `Cameras.b007(self)` — Cameras: Align View
  - `Cameras.b010(self)` — Camera: Dolly
  - `Cameras.b011(self)` — Camera: Roll
  - `Cameras.b012(self)` — Camera: Truck
  - `Cameras.b013(self)` — Camera: Orbit

<a id="slots--maya--constrain"></a>
### `slots/maya/constrain.py`

- **[`class Constrain(SlotsMaya)`](tentacle/tentacle/slots/maya/constrain.py#L9)**

<a id="slots--maya--control"></a>
### `slots/maya/control.py`

- **[`class ControlSlots(SlotsMaya)`](tentacle/tentacle/slots/maya/control.py#L9)**

<a id="slots--maya--crease"></a>
### `slots/maya/crease.py`

- **[`class Crease(SlotsMaya)`](tentacle/tentacle/slots/maya/crease.py#L8)**
  - `Crease.tb000_init(self, widget)`
  - `Crease.tb000(self, widget)` — Crease: crease the selected edges (subdivision sharpness), with an optional smoothing angle.
  - `Crease.b002(self, widget)` — Transfer Crease Edges

<a id="slots--maya--curves"></a>
### `slots/maya/curves.py`

- **[`class CurvesSlots(SlotsMaya)`](tentacle/tentacle/slots/maya/curves.py#L9)**

<a id="slots--maya--deform"></a>
### `slots/maya/deform.py`

- **[`class DeformSlots(SlotsMaya)`](tentacle/tentacle/slots/maya/deform.py#L9)**

<a id="slots--maya--deformation"></a>
### `slots/maya/deformation.py`

- **[`class DeformationSlots(SlotsMaya)`](tentacle/tentacle/slots/maya/deformation.py#L6)** — Slots for the Deformation panel (``deformation.ui``).
  - `DeformationSlots.tb001_init(self, widget)` — Init Curtain Generator launcher.
  - `DeformationSlots.tb001(self, widget)` — Curtain Generator — open the mayatk Curtain tool.

<a id="slots--maya--display"></a>
### `slots/maya/display.py`

- **[`class DisplaySlots(SlotsMaya)`](tentacle/tentacle/slots/maya/display.py#L9)**
  - `DisplaySlots.header_init(self, widget)` — Header menu: the submenu's Display expandable list — hover a row to
  - `DisplaySlots.list000_init(self, widget)` — Initialize Display expandable list (categories → actions).
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

- **[`class Duplicate(SlotsMaya)`](tentacle/tentacle/slots/maya/duplicate.py#L9)**
  - `Duplicate.header_init(self, widget)`
  - `Duplicate.tb002_init(self, widget)` — Initialize Auto Instance — configure option-box menu.
  - `Duplicate.tb002(self, widget)` — Auto Instance: find and convert geometrically identical meshes
  - `Duplicate.tb000_init(self, widget)`
  - `Duplicate.tb000(self, widget)` — Convert to Instances
  - `Duplicate.tb001_init(self, widget)`
  - `Duplicate.tb001(self, widget)` — Select Instanced Objects
  - `Duplicate.b000(self)` — Mirror: open the Mirror tool window.
  - `Duplicate.b005(self)` — Uninstance Selected Objects
  - `Duplicate.b006(self)` — Duplicate Linear
  - `Duplicate.b007(self)` — Duplicate Radial
  - `Duplicate.b008(self)` — Duplicate Grid

<a id="slots--maya--edit"></a>
### `slots/maya/edit.py`

- **[`class Edit(EditMixin, SlotsMaya)`](tentacle/tentacle/slots/maya/edit.py#L9)**
  - `Edit.header_init(self, widget)` — Initialize header menu
  - `Edit.tb000_init(self, widget)` — Initialize Mesh Cleanup
  - `Edit.tb000(self, widget)` — Mesh Cleanup — Repair (fix) or, in Select mode, select the matched problem geometry.
  - `Edit.tb001_init(self, widget)` — Initialize Delete History
  - `Edit.tb001(self, widget)` — Delete History
  - `Edit.tb002(self, widget)` — Delete Selected
  - `Edit.tb004_init(self, widget)` — Init Lock/Unlock Nodes
  - `Edit.tb004(self, widget)` — Node Locking
  - `Edit.b_channels(self)` — Channels: open the Channels panel.
  - `Edit.b000(self)` — Cut On Axis: open the Cut On Axis tool (slice objects along an axis plane).
  - `Edit.list000_init(self, widget)` — Initialize Create Primitives list.
  - `Edit.list000(self, item)` — Create Primitive
  - `Edit.list001_init(self, widget)` — Initialize Convert list.
  - `Edit.list001(self, item)` — Convert: convert the selected geometry between types (NURBS / polygon / subdiv / curve, etc.).
  - `Edit.cmb000_init(self, widget)` — Initialize the Transfer operations menu.
  - `Edit.cmb000(self, index, widget)` — Transfer — dispatch the selected transfer operation.

<a id="slots--maya--edit_mesh"></a>
### `slots/maya/edit_mesh.py`

- **[`class EditMeshSlots(SlotsMaya)`](tentacle/tentacle/slots/maya/edit_mesh.py#L9)**

<a id="slots--maya--editors"></a>
### `slots/maya/editors.py`

- **[`class Editors(SlotsMaya)`](tentacle/tentacle/slots/maya/editors.py#L9)**
  - `Editors.list000_init(self, widget)` — Initialize the widget with structured data for easier maintenance.
  - `Editors.list000(self, item)` — Open the chosen Maya editor (general, modeling, animation, rendering, or relationship).
  - `Editors.b000(self)` — Attributes: open the Attribute Editor.
  - `Editors.b001(self)` — Outliner: open the Outliner window.
  - `Editors.b002(self)` — Tool: open the Tool Settings window.
  - `Editors.b003(self)` — Layers: open the Channels / Layers panel.
  - `Editors.b004(self)` — Channels: open the Channels / Layers panel.
  - `Editors.b005(self)` — Node Editor: open the Node Editor window.
  - `Editors.b006(self)` — Dependancy Graph
  - `Editors.b007(self)` — Status Line: toggle the Status Line UI.
  - `Editors.b008(self)` — Shelf: toggle the Shelf UI.
  - `Editors.b009(self)` — Time & Range
  - `Editors.b010(self)` — Script Output
  - `Editors.b011(self)` — Command Line
  - `Editors.b012(self)` — Help Line: toggle the Help Line UI.
  - `Editors.b013(self)` — Tool Box: toggle the Toolbox UI.
  - `Editors.getEditorWidget(self, name)` — Get a maya widget from a given name.

<a id="slots--maya--effects"></a>
### `slots/maya/effects.py`

- **[`class EffectsSlots(SlotsMaya)`](tentacle/tentacle/slots/maya/effects.py#L9)**

<a id="slots--maya--fields_solvers"></a>
### `slots/maya/fields_solvers.py`

- **[`class FieldsSolversSlots(SlotsMaya)`](tentacle/tentacle/slots/maya/fields_solvers.py#L9)**

<a id="slots--maya--fluids"></a>
### `slots/maya/fluids.py`

- **[`class FluidsSlots(SlotsMaya)`](tentacle/tentacle/slots/maya/fluids.py#L9)**

<a id="slots--maya--generate"></a>
### `slots/maya/generate.py`

- **[`class GenerateSlots(SlotsMaya)`](tentacle/tentacle/slots/maya/generate.py#L9)**

<a id="slots--maya--help"></a>
### `slots/maya/help.py`

- **[`class HelpSlots(SlotsMaya)`](tentacle/tentacle/slots/maya/help.py#L9)**

<a id="slots--maya--hud"></a>
### `slots/maya/hud.py`

- **[`class StatusMixin`](tentacle/tentacle/slots/maya/hud.py#L12)**
  - `StatusMixin.insert_scene_status(self, hud) -> None`
- **[`class SelectionMixin`](tentacle/tentacle/slots/maya/hud.py#L55)**
  - `SelectionMixin.insert_selection_info(self, hud, selection) -> None`
  - `SelectionMixin.insert_component_info(self, hud, selection) -> None`
- **[`class WarningsMixin(HudWarningsMixin)`](tentacle/tentacle/slots/maya/hud.py#L128)** — Maya HUD warnings — the framework lives in the shared
- **[`class HudSlots(SlotsMaya, ptk.PackageManager, StatusMixin, SelectionMixin, WarningsMixin)`](tentacle/tentacle/slots/maya/hud.py#L208)** — HUD Slots for Maya, providing scene and selection information.
  - `HudSlots.request_hud_build(self) -> None` — Start a new HUD build request, only the latest token will be used.
  - `HudSlots.construct_hud(self) -> None`

<a id="slots--maya--key"></a>
### `slots/maya/key.py`

- **[`class KeySlots(SlotsMaya)`](tentacle/tentacle/slots/maya/key.py#L9)**

<a id="slots--maya--lighting"></a>
### `slots/maya/lighting.py`

- **[`class Lighting(LightingMixin, SlotsMaya)`](tentacle/tentacle/slots/maya/lighting.py#L9)**
  - `Lighting.b000(self)` — Launch the HDR Manager.
  - `Lighting.b001(self)` — Launch the Lightmap Baker.
  - `Lighting.tb000_init(self, widget)` — Lights From Geometry Init
  - `Lighting.tb000(self, widget)` — Create real area lights from the selected fixture geometry.

<a id="slots--maya--lighting_shading"></a>
### `slots/maya/lighting_shading.py`

- **[`class LightingShadingSlots(SlotsMaya)`](tentacle/tentacle/slots/maya/lighting_shading.py#L9)**

<a id="slots--maya--main"></a>
### `slots/maya/main.py`

- **[`class Main(MainMixin, SlotsMaya)`](tentacle/tentacle/slots/maya/main.py#L11)**
  - `Main.list000_init(self, widget)` — Initialize the Workspace tab.
  - `Main.list000(self, item)` — Workspace tab dispatch — editing actions, recent-workspace selection,

<a id="slots--maya--mash"></a>
### `slots/maya/mash.py`

- **[`class MashSlots(SlotsMaya)`](tentacle/tentacle/slots/maya/mash.py#L9)**

<a id="slots--maya--materials"></a>
### `slots/maya/materials.py`

- **[`class MaterialsSlots(MaterialsMixin, SlotsMaya)`](tentacle/tentacle/slots/maya/materials.py#L12)**
  - `MaterialsSlots.b007(self)` — Hypershade Editor
  - `MaterialsSlots.list000_init(self, widget)` — Assign list: scene materials + 'New' + 'Random'.
  - `MaterialsSlots.list000(self, item)` — Dispatch Assign list selection.
  - `MaterialsSlots.list001_init(self, widget)` — Tools list: Setup / Conversion / External (mirrors prior header sections).
  - `MaterialsSlots.list001(self, item)` — Dispatch Tools list selection to the matching slot method.
  - `MaterialsSlots.cmb002_init(self, widget)` — Initialize Materials
  - `MaterialsSlots.lbl007(self)` — Rename the current material by stripping trailing integers and underscores.
  - `MaterialsSlots.lbl007_global(self)` — Rename ALL scene materials by stripping trailing integers and underscores.
  - `MaterialsSlots.tb000_init(self, widget)`
  - `MaterialsSlots.tb000(self, widget)` — Select By Material — the option box supplies the parameters.
  - `MaterialsSlots.select_by_mat(self, shell=False, in_selection=False, get_first=False, add=False, unassigned=False)` — Select the geometry carrying the current material.
  - `MaterialsSlots.lbl002(self)` — Delete Material
  - `MaterialsSlots.b015(self, widget)` — Delete Unused Materials
  - `MaterialsSlots.lbl004(self)` — Select and Show Attributes: Show Material Attributes in the Attribute Editor.
  - `MaterialsSlots.lbl006(self)` — Open material in editor
  - `MaterialsSlots.b002(self, widget)` — Get Material: Change the index to match the current material selection.
  - `MaterialsSlots.b004(self, widget)` — Assign Random
  - `MaterialsSlots.b006(self, widget)` — Assign: New Material
  - `MaterialsSlots.b008(self, widget)` — Map Packer
  - `MaterialsSlots.b009(self, widget)` — Create Game Shader
  - `MaterialsSlots.b026(self, widget)` — Arnold Preview Shader (parallel aiStandardSurface for in-Maya Arnold preview;
  - `MaterialsSlots.b027(self, widget)` — Emissive Groups
  - `MaterialsSlots.b010(self, widget)` — Texture Path Editor
  - `MaterialsSlots.b011(self, widget)` — Shader Templates
  - `MaterialsSlots.b013(self)` — Reload Textures and Reset Viewport
  - `MaterialsSlots.b014(self)` — Remove and Reassign Duplicates
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

- **[`class MeshSlots(SlotsMaya)`](tentacle/tentacle/slots/maya/mesh.py#L9)**

<a id="slots--maya--mesh_display"></a>
### `slots/maya/mesh_display.py`

- **[`class MeshDisplaySlots(SlotsMaya)`](tentacle/tentacle/slots/maya/mesh_display.py#L9)**

<a id="slots--maya--mesh_tools"></a>
### `slots/maya/mesh_tools.py`

- **[`class MeshToolsSlots(SlotsMaya)`](tentacle/tentacle/slots/maya/mesh_tools.py#L9)**

<a id="slots--maya--ncloth"></a>
### `slots/maya/ncloth.py`

- **[`class NClothSlots(SlotsMaya)`](tentacle/tentacle/slots/maya/ncloth.py#L9)**

<a id="slots--maya--nconstraint"></a>
### `slots/maya/nconstraint.py`

- **[`class NConstraintSlots(SlotsMaya)`](tentacle/tentacle/slots/maya/nconstraint.py#L9)**

<a id="slots--maya--nhair"></a>
### `slots/maya/nhair.py`

- **[`class NHairSlots(SlotsMaya)`](tentacle/tentacle/slots/maya/nhair.py#L9)**

<a id="slots--maya--normals"></a>
### `slots/maya/normals.py`

- **[`class Normals(SlotsMaya)`](tentacle/tentacle/slots/maya/normals.py#L9)**
  - `Normals.tb001_init(self, widget)` — Initialize Set Normals By Angle
  - `Normals.tb001(self, widget)` — Set Normals By Angle
  - `Normals.tb004_init(self, widget)` — Initialize Average Normals
  - `Normals.tb004(self, widget)` — Average Normals
  - `Normals.b000(self)` — Soften Edge Normals
  - `Normals.b001(self)` — Harden all selected edges.
  - `Normals.b002(self)` — Transfer Normals
  - `Normals.b004(self)` — Toggle lock/unlock vertex normals.
  - `Normals.b006(self)` — Set To Face: set vertex normals to match their face normals (faceted shading).
  - `Normals.tb010_init(self, widget)` — Initialize Reverse Normals
  - `Normals.tb010(self, widget)` — Reverse Normals

<a id="slots--maya--nparticles"></a>
### `slots/maya/nparticles.py`

- **[`class NParticlesSlots(SlotsMaya)`](tentacle/tentacle/slots/maya/nparticles.py#L9)**

<a id="slots--maya--nurbs"></a>
### `slots/maya/nurbs.py`

- **[`class Nurbs(SlotsMaya)`](tentacle/tentacle/slots/maya/nurbs.py#L9)**
  - `Nurbs.list000_init(self, widget)` — Initialize Nurbs expandable list (categories → curve actions).
  - `Nurbs.list000(self, item)` — Dispatch a Nurbs leaf action via mel.eval (uses Maya's stored settings).
  - `Nurbs.b056(self)` — Image Tracer
  - `Nurbs.b058(self)` — Curve to Tube
  - `Nurbs.tb000_init(self, widget)`
  - `Nurbs.tb000(self, widget)` — Revolve: sweep the selected profile curve around an axis into a surface.
  - `Nurbs.tb001_init(self, widget)`
  - `Nurbs.tb001(self, widget)` — Loft: build a surface lofted across the selected profile curves.
  - `Nurbs.b016(self)` — Extract Curve
  - `Nurbs.b030(self)` — Extrude: extrude the selected NURBS curve(s) into a surface.

<a id="slots--maya--pivot"></a>
### `slots/maya/pivot.py`

- **[`class Pivot(SlotsMaya)`](tentacle/tentacle/slots/maya/pivot.py#L9)**
  - `Pivot.tb000_init(self, widget)`
  - `Pivot.tb000(self, widget)` — Reset Pivot: reset the selected objects' pivot position and/or orientation.
  - `Pivot.tb001_init(self, widget)`
  - `Pivot.tb001(self, widget)` — Center Pivot
  - `Pivot.tb002_init(self, widget)`
  - `Pivot.tb002(self, widget)` — Transfer Pivot
  - `Pivot.tb003_init(self, widget)` — Initialize World-Aligned Pivot options
  - `Pivot.tb003(self, widget)` — World-Aligned Pivot: world-align the pivot of the selected objects or components.
  - `Pivot.b000(self)` — Center Pivot: Object
  - `Pivot.b001(self)` — Center Pivot: Component
  - `Pivot.b002(self, widget)` — Center Pivot: World
  - `Pivot.b004(self)` — Bake Pivot: bake the manipulator pivot's position and orientation into the transform.

<a id="slots--maya--playback"></a>
### `slots/maya/playback.py`

- **[`class PlaybackSlots(SlotsMaya)`](tentacle/tentacle/slots/maya/playback.py#L9)**

<a id="slots--maya--polygons"></a>
### `slots/maya/polygons.py`

- **[`class PolygonsSlots(SlotsMaya)`](tentacle/tentacle/slots/maya/polygons.py#L10)**
  - `PolygonsSlots.header_init(self, widget)` — Initialize Header
  - `PolygonsSlots.chk008(self, state, widget)` — Divide Facet: Split U
  - `PolygonsSlots.chk009(self, state, widget)` — Divide Facet: Split V
  - `PolygonsSlots.chk010(self, state, widget)` — Divide Facet: Tris
  - `PolygonsSlots.tb000_init(self, widget)` — Initialize Merge Vertices
  - `PolygonsSlots.tb000(self, widget)` — Merge Vertices
  - `PolygonsSlots.tb002_init(self, widget)` — Initialize Separate
  - `PolygonsSlots.tb002(self, widget)` — Separate: split a combined mesh into its disconnected shells (optionally per material).
  - `PolygonsSlots.tb003_init(self, widget)` — Initialize Extrude
  - `PolygonsSlots.tb003(self, widget)` — Extrude: push out the selected faces, edges, or vertices.
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
  - `PolygonsSlots.b009(self)` — Collapse Component
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

- **[`class Preferences(PreferencesMixin, SlotsMaya)`](tentacle/tentacle/slots/maya/preferences.py#L12)**
  - `Preferences.cmb001_init(self, widget)` — Initializes the combo box with unit options.
  - `Preferences.cmb001(self, index, widget)` — Set Working Units: Linear
  - `Preferences.cmb002_init(self, widget)` — Initializes the combo box with frame rate options.
  - `Preferences.cmb002(self, index, widget)` — Set Working Units: Time
  - `Preferences.s000_init(self, widget)` — Initialize autosave max backups spinbox (widget is source of truth).
  - `Preferences.s001_init(self, widget)` — Initialize autosave interval spinbox (widget is source of truth).
  - `Preferences.b001(self)` — Color Settings
  - `Preferences.cmb003_init(self, widget)` — App-style / color selector — the Maya-side counterpart to the Blender slot's ``cmb003``.
  - `Preferences.cmb003(self, index, widget)` — Apply the selected shipped style (e.g.
  - `Preferences.b008(self)` — Hotkeys: open Maya's native Hotkey Preferences window.
  - `Preferences.b011(self)` — Macro Manager — the unified shortcut editor over the mayatk macros
  - `Preferences.b009(self)` — Plug-In Manager
  - `Preferences.b010(self)` — Settings/Preferences

<a id="slots--maya--render"></a>
### `slots/maya/render.py`

- **[`class Render(SlotsMaya)`](tentacle/tentacle/slots/maya/render.py#L9)**

<a id="slots--maya--rendering"></a>
### `slots/maya/rendering.py`

- **[`class Rendering(RenderingMixin, SlotsMaya)`](tentacle/tentacle/slots/maya/rendering.py#L13)**
  - `Rendering.tb000_init(self, widget)` — Export Playblast Init
  - `Rendering.tb000(self, widget)` — Export Playblast
  - `Rendering.tb001_init(self, widget)` — Render: camera, renderer, Arnold network, IPR, and smart redo.
  - `Rendering.tb001(self, widget)` — Render: render the current frame through the selected camera and renderer.
  - `Rendering.tb002_init(self, widget)` — WebXR Preview: scope and export options for the live browser preview.
  - `Rendering.tb002(self, widget)` — Push the selection to the live WebXR preview.
  - `Rendering.b001(self)` — Open Render Settings Window
  - `Rendering.b003(self)` — Editor: Render Setup
  - `Rendering.b004(self)` — Editor: Rendering Flags

<a id="slots--maya--rigging"></a>
### `slots/maya/rigging.py`

- **[`class Rigging(SlotsMaya)`](tentacle/tentacle/slots/maya/rigging.py#L11)**
  - `Rigging.header_init(self, widget)` — Init Rigging Header
  - `Rigging.b020(self)` — Rebind Skin Clusters
  - `Rigging.cmb001_init(self, widget)` — Init Create
  - `Rigging.cmb001(self, index, widget)` — Create: create a rigging utility node — joints, IK handle, lattice, or cluster.
  - `Rigging.cmb002_init(self, widget)` — Init Quick Rig — our procedural rig tools plus Maya's built-in character auto-riggers.
  - `Rigging.cmb002(self, index, widget)` — Quick Rig: open a procedural rig tool, or Maya's built-in Quick Rig / HumanIK.
  - `Rigging.chk000(self, state, widget)` — Scale Joint
  - `Rigging.chk001(self, state, widget)` — Scale IK
  - `Rigging.chk002(self, state, widget)` — Scale IK/FK
  - `Rigging.s000(self, value, widget)` — Scale Joint/IK/FK
  - `Rigging.tb000_init(self, widget)` — Init Display Local Rotation Axes
  - `Rigging.tb000(self, widget)` — Toggle Display Local Rotation Axes
  - `Rigging.tb001_init(self, widget)` — Init Constraint Switch
  - `Rigging.tb001(self, widget)` — Constraint Switch
  - `Rigging.tb003_init(self, widget)` — Init Create Locator at Selection
  - `Rigging.tb003(self, widget)` — Create Locator at Selection
  - `Rigging.b003(self)` — Remove Locator
  - `Rigging.tb004_init(self, widget)` — Init Lock/Unlock Attributes
  - `Rigging.tb004(self, widget)` — Lock/Unlock Attributes
  - `Rigging.b004(self)` — Render Opacity

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
  - `SceneSlots.tb001_init(self, widget)` — Get Scene Info — option box.
  - `SceneSlots.tb001(self, widget)` — Get Scene Info — render the audit report to the viewer dialog.
  - `SceneSlots.b011(self)` — Fix Color Spaces
  - `SceneSlots.b018(self)` — Fix Mangled Names
  - `SceneSlots.b012(self)` — Toggle Command Ports
  - `SceneSlots.b017(self)` — Scene Metadata — dump the tool-authored data-node channels to the viewer.
  - `SceneSlots.b013(self)` — Mesh Converter (FBX -> GLB)
  - `SceneSlots.b014_init(self, widget)` — Initialize Save to Original Scene.
  - `SceneSlots.b014(self)` — Save to Original Scene.

<a id="slots--maya--select"></a>
### `slots/maya/select.py`

- **[`class SelectSlots(SlotsMaya)`](tentacle/tentacle/slots/maya/select.py#L9)**

<a id="slots--maya--selection"></a>
### `slots/maya/selection.py`

- **[`class Selection(SelectionMixin, SlotsMaya)`](tentacle/tentacle/slots/maya/selection.py#L9)**
  - `Selection.list000_init(self, widget)` — Select by Type: Hierarchical type list.
  - `Selection.list000(self, item)` — Select by Type
  - `Selection.tb004_init(self, widget)` — Select by Type settings menu.
  - `Selection.tb004(self, widget)` — Select by Type settings: open the scope/mode menu.
  - `Selection.cmb001_init(self, widget)` — Reorder Selection Init
  - `Selection.cmb001(self, index, widget)` — Reorder Selection
  - `Selection.list001(self, item)` — Convert To: convert the component selection to verts, edges, faces, UVs, or shells.
  - `Selection.b002_init(self, widget)` — Selection constraint: Angle.
  - `Selection.b002(self, widget)` — Selection constraint: Angle (toggle).
  - `Selection.b003_init(self, widget)` — Selection constraint: Border.
  - `Selection.b003(self, widget)` — Selection constraint: Border (toggle).
  - `Selection.b004_init(self, widget)` — Selection constraint: Edge Loop.
  - `Selection.b004(self, widget)` — Selection constraint: Edge Loop (toggle).
  - `Selection.b005_init(self, widget)` — Selection constraint: Edge Ring.
  - `Selection.b005(self, widget)` — Selection constraint: Edge Ring (toggle).
  - `Selection.b006_init(self, widget)` — Selection constraint: Shell.
  - `Selection.b006(self, widget)` — Selection constraint: Shell (toggle).
  - `Selection.b007_init(self, widget)` — Selection constraint: UV Edge Loop.
  - `Selection.b007(self, widget)` — Selection constraint: UV Edge Loop (toggle).
  - `Selection.chk000(self, state, widget)` — Select Nth: uncheck other checkboxes
  - `Selection.chk001(self, state, widget)` — Select Nth: uncheck other checkboxes
  - `Selection.chk002(self, state, widget)` — Select Nth: uncheck other checkboxes
  - `Selection.chk005_init(self, widget)` — Create button group for radioboxes chk005, chk006, chk007
  - `Selection.chk005(self, state, widget)` — Select Style: Marquee
  - `Selection.chk006(self, state, widget)` — Select Style: Lasso
  - `Selection.chk007(self, state, widget)` — Select Style: Paint
  - `Selection.chk004(self, state, widget)` — Ignore Backfacing (Camera Based Selection)
  - `Selection.chkxxx(self, **kwargs)` — Transform Constraints: Constraint CheckBoxes
  - `Selection.tb000_init(self, widget)`
  - `Selection.tb000(self, widget)` — Select Nth: select edge loops/rings or shortest paths, stepping every Nth component.
  - `Selection.tb001_init(self, widget)`
  - `Selection.tb001(self, widget)` — Select Similar.
  - `Selection.tb002_init(self, widget)`
  - `Selection.tb002(self, widget)` — Select Island: Select Polygon Face Island
  - `Selection.tb003_init(self, widget)`
  - `Selection.tb003(self, widget)` — Select Edges By Angle
  - `Selection.b001(self)` — Toggle Selectability
  - `Selection.get_selection_tool()` *(static)* — Queries the current selection tool in Maya.
  - `Selection.set_selection_tool(tool)` *(static)* — Sets the selection tool in Maya.

<a id="slots--maya--settings"></a>
### `slots/maya/settings.py`

- **[`class Settings(SettingsMixin, SlotsMaya)`](tentacle/tentacle/slots/maya/settings.py#L13)** — Maya fork of the shared ``settings`` menu.
  - `Settings.tb001(self)` — Reload Tentacle package with its dependencies.

<a id="slots--maya--skeleton"></a>
### `slots/maya/skeleton.py`

- **[`class SkeletonSlots(SlotsMaya)`](tentacle/tentacle/slots/maya/skeleton.py#L9)**

<a id="slots--maya--skin"></a>
### `slots/maya/skin.py`

- **[`class Skin(SlotsMaya)`](tentacle/tentacle/slots/maya/skin.py#L9)**

<a id="slots--maya--stereo"></a>
### `slots/maya/stereo.py`

- **[`class StereoSlots(SlotsMaya)`](tentacle/tentacle/slots/maya/stereo.py#L9)**

<a id="slots--maya--subdivision"></a>
### `slots/maya/subdivision.py`

- **[`class Subdivision(SlotsMaya)`](tentacle/tentacle/slots/maya/subdivision.py#L9)**
  - `Subdivision.s000_init(self, widget)` — Division Level — reflect the selection's live preview division level.
  - `Subdivision.s001_init(self, widget)` — Adaptive Level — reflect the selection's live adaptive tessellation level.
  - `Subdivision.s000(self, value: int, widget: object) -> None` — Division Level (smooth mesh preview divisions).
  - `Subdivision.s001(self, value: int, widget: object) -> None` — Adaptive Level (OpenSubdiv adaptive tessellation).
  - `Subdivision.b000(self)` — Quadrangulate
  - `Subdivision.b001(self)` — Triangulate: split the selected faces into triangles.
  - `Subdivision.b005(self)` — Reduce: halve the polygon count while preserving border, hard, crease, and UV edges.
  - `Subdivision.tb000_init(self, widget)` — Initialize Decimate
  - `Subdivision.tb000(self, widget)` — Decimate: reduce face count by quadric-error percentage or coplanar-face dissolve.
  - `Subdivision.b008(self)` — Add Divisions - Subdivide Mesh
  - `Subdivision.b011(self)` — Apply Smooth Preview
  - `Subdivision.b028(self)` — Quad Draw: enter Maya's Quad Draw retopology tool.
  - `Subdivision.smoothProxy()` *(static)* — Subdiv Proxy

<a id="slots--maya--surfaces"></a>
### `slots/maya/surfaces.py`

- **[`class SurfacesSlots(SlotsMaya)`](tentacle/tentacle/slots/maya/surfaces.py#L9)**

<a id="slots--maya--symmetry"></a>
### `slots/maya/symmetry.py`

- **[`class Symmetry(SlotsMaya)`](tentacle/tentacle/slots/maya/symmetry.py#L7)**
  - `Symmetry.chk000_init(self, widget)` — Set initial symmetry state
  - `Symmetry.chk000(self, state, widget)` — Symmetry X: toggle modeling symmetry across the X axis.
  - `Symmetry.chk001(self, state, widget)` — Symmetry Y: toggle modeling symmetry across the Y axis.
  - `Symmetry.chk002(self, state, widget)` — Symmetry Z: toggle modeling symmetry across the Z axis.
  - `Symmetry.chk004(self, state, widget)` — Symmetry: Object space (radio partner of Topo;
  - `Symmetry.chk005_init(self, widget)` — Set symmetry reference space
  - `Symmetry.chk005(self, state, widget)` — Symmetry: Topo

<a id="slots--maya--texturing"></a>
### `slots/maya/texturing.py`

- **[`class TexturingSlots(SlotsMaya)`](tentacle/tentacle/slots/maya/texturing.py#L9)**

<a id="slots--maya--toon"></a>
### `slots/maya/toon.py`

- **[`class ToonSlots(SlotsMaya)`](tentacle/tentacle/slots/maya/toon.py#L9)**

<a id="slots--maya--transform"></a>
### `slots/maya/transform.py`

- **[`class TransformSlots(SlotsMaya)`](tentacle/tentacle/slots/maya/transform.py#L9)**
  - `TransformSlots.header_init(self, widget)` — Header Init
  - `TransformSlots.cmb002_init(self, widget)` — Align To Init
  - `TransformSlots.cmb002(self, index, widget)` — Align To: snap/align objects point-to-point, multi-point, or along a curve.
  - `TransformSlots.tb000_init(self, widget)` — Drop To Grid Init
  - `TransformSlots.tb000(self, widget)` — Drop To Grid
  - `TransformSlots.tb001_init(self, widget)` — Scale Connected Edges Init
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

- **[`class Utilities(SlotsMaya)`](tentacle/tentacle/slots/maya/utilities.py#L8)**
  - `Utilities.b000(self)` — Measure: create a distance-measure tool between two points.
  - `Utilities.b001(self)` — Annotation: create an annotation (text label) node.
  - `Utilities.b002(self)` — Calculator: open the calculator tool.
  - `Utilities.b003(self)` — Grease Pencil

<a id="slots--maya--uv"></a>
### `slots/maya/uv.py`

- **[`class UvSlots(UvMixin, SlotsMaya)`](tentacle/tentacle/slots/maya/uv.py#L11)**
  - `UvSlots.get_map_size(self)` — Get the map size from the combobox as an int.
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
  - `UvSlots.cmb003(self, index, widget)` — UV Map Size — passive input;
  - `UvSlots.s003(self, value, widget)` — Texel Density — passive input;
  - `UvSlots.b000_init(self, widget)` — Initialize Transfer UVs option box — scope + similarity tolerance.
  - `UvSlots.b000(self, widget)` — Transfer UV's
  - `UvSlots.b003(self)` — Get texel density.
  - `UvSlots.b004(self)` — Set Texel Density
  - `UvSlots.b005(self)` — Cut UVs: split the UV shell along the selected edges.
  - `UvSlots.b011(self)` — Sew UVs: stitch the selected UV edges back together.
  - `UvSlots.b021(self, widget)` — Unfold and Pack UVs
  - `UvSlots.tb022_init(self, widget)` — Initialize Cut Hard Edges option menu.
  - `UvSlots.tb022(self, widget)` — Cut UV hard edges (always), optionally also UV borders and auto-detected seams.
  - `UvSlots.b029_init(self, widget)` — Initialize Pin/Unpin button — non-checkable text button.
  - `UvSlots.b029(self, widget)` — Pin / Unpin selected UVs (dual-state toggle).
  - `UvSlots.b030(self, widget)` — Stack / Unstack shells (dual-state toggle).
  - `UvSlots.b031(self)` — Open UV Editor
  - `UvSlots.b032(self)` — RizomUV Bridge
  - `UvSlots.b033(self)` — Open the Shell Xform panel (move / flip / rotate / align / orient / distribute).

<a id="slots--maya--visualize"></a>
### `slots/maya/visualize.py`

- **[`class VisualizeSlots(SlotsMaya)`](tentacle/tentacle/slots/maya/visualize.py#L9)**

<a id="slots--maya--windows"></a>
### `slots/maya/windows.py`

- **[`class WindowsSlots(SlotsMaya)`](tentacle/tentacle/slots/maya/windows.py#L9)**

<a id="tcl"></a>
### `tcl.py`

The host-agnostic entry point — one launcher snippet for every DCC.

- **[`class Tcl(_TclInternal)`](tentacle/tentacle/tcl.py#L106)** — Launch tentacle in whichever DCC is hosting this process.
  - `Tcl.host(cls)` *(class)* — The DCC hosting this process (``'maya'``/``'blender'``/``'max'``), or None.
  - `Tcl.qt_key_name(cls, key_show=None)` *(class)* — Normalize an activation key to its Qt name: ``'Z'`` and ``'Key_Z'`` both → ``'Key_Z'``.
  - `Tcl.resolve_key(cls, key_show=None, context_tags=None)` *(class)* — The activation key to launch with: **user-persisted > ``key_show`` > :attr:`DEFAULT_KEY`**.
  - `Tcl.chord_bindings(cls, key_show=None, chord_target=None)` *(class)* — The default chord→menu table for ``key_show`` (bare or Qt-named).
  - `Tcl.launch(cls, key_show=None, **kwargs)` *(class)* — Start tentacle in the host DCC, deferring startup the way that host requires.

<a id="tcl_blender"></a>
### `tcl_blender.py`

Blender entry point for tentacle's Qt marking menu — host + keymap bridge + launcher in one.

- [`ensure_qapp()`](tentacle/tentacle/tcl_blender.py#L2088) — Return the process QApplication, creating one if Blender has none.
- [`ensure_blender_widget(app)`](tentacle/tentacle/tcl_blender.py#L2093) — Establish ``app.blender_widget`` — the parent for the marking menu.
- [`start_event_pump(app, interval=0.01)`](tentacle/tentacle/tcl_blender.py#L2098) — Pump Qt events from Blender's timer loop so the Qt UI stays responsive (idempotent).
- [`blender_native_window()`](tentacle/tentacle/tcl_blender.py#L2103) — Blender's main GHOST window wrapped as a foreign ``QWindow`` (cached on the QApplication).
- [`launch(**kwargs)`](tentacle/tentacle/tcl_blender.py#L2108) — Stand up the Qt host and return a :class:`TclBlender` (idempotent).
- [`register(**kwargs)`](tentacle/tentacle/tcl_blender.py#L2113) — Blender add-on / startup entry.
- [`unregister()`](tentacle/tentacle/tcl_blender.py#L2118) — Blender add-on teardown.
- [`reload()`](tentacle/tentacle/tcl_blender.py#L2123) — Reload the tentacle ecosystem in place and re-register.
- [`diagnose()`](tentacle/tentacle/tcl_blender.py#L2128) — Return (and print) the live activation state.
- [`enable_click_debug()`](tentacle/tentacle/tcl_blender.py#L2133) — Turn on the opt-in click tracer.
- [`disable_click_debug()`](tentacle/tentacle/tcl_blender.py#L2138) — Remove the click tracer.
- **[`class TclBlender(MarkingMenu)`](tentacle/tentacle/tcl_blender.py#L1369)** — Marking Menu class overridden for use with Blender.
  - `TclBlender.get_main_window(cls)` *(class)* — Blender parent widget for the marking menu (set by :meth:`_QtHost.ensure_widget`).
  - `TclBlender.set_activation_key(self, new_key)` — Rebind the activation key — and move Blender's half of the binding with it.
  - `TclBlender.showEvent(self, event)`
  - `TclBlender.keyPressEvent(self, event)`
  - `TclBlender.keyReleaseEvent(self, event)`
- **[`class Diagnostics`](tentacle/tentacle/tcl_blender.py#L1852)** — The live-activation-state report — run in Blender's Python console to see why the key isn't
  - `Diagnostics.report(emit=True)` *(static)* — Return (and, when ``emit``, print) the live activation state — run in Blender's Python
- **[`class BlenderHost`](tentacle/tentacle/tcl_blender.py#L1967)** — Launcher + Blender add-on lifecycle coordinator — ties the Qt host, keymap bridge and menu
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

- **[`class TclMaya(MarkingMenu)`](tentacle/tentacle/tcl_maya.py#L9)** — Marking Menu class overridden for use with Autodesk Maya.
