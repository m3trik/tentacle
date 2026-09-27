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
- [`slots/_normals.py`](#slots--_normals) — Behavior shared by the Maya and Blender ``normals`` panels.
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
- [`tentacle_installer.py`](#tentacle_installer) — Install, update or uninstall tentacle in a DCC -- one file, dropped in, no administrator rights.

---

<a id="__init__"></a>
### `__init__.py`

- [`greeting(string, outputToConsole=True)`](tentacle/tentacle/__init__.py#L61) — Format a string using preset variables.
- [`DEFAULT_INCLUDE`](tentacle/tentacle/__init__.py#L11) — constant

<a id="slots--_animation"></a>
### `slots/_animation.py`

Text the animation panel's Maya and Blender forks say identically.

- **[`class AnimationMixin`](tentacle/tentacle/slots/_animation.py#L37)** — Shared tooltip text for ``slots/{maya,blender}/animation.py``.
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

- **[`class HudWarningsMixin`](tentacle/tentacle/slots/_hud_warnings.py#L27)**
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

- **[`class MaterialsMixin`](tentacle/tentacle/slots/_materials.py#L58)** — DCC-agnostic ``materials`` slot behavior.
  - `MaterialsMixin.b003(self, widget=None)` — Get + Select (submenu): adopt the selection's material, then select its users.
  - `MaterialsMixin.list001_init(self, widget)` — Tools list: Setup / Conversion / External (mirrors prior header sections).

<a id="slots--_normals"></a>
### `slots/_normals.py`

Behavior shared by the Maya and Blender ``normals`` panels.

- **[`class NormalsMixin`](tentacle/tentacle/slots/_normals.py#L9)** — Shared ``normals`` panel behavior.
  - `NormalsMixin.tb010_init(self, widget)` — Initialize Reverse Normals: Maya's five ``polyNormal`` modes, 1:1 in

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

- **[`class RenderingMixin`](tentacle/tentacle/slots/_rendering.py#L20)** — DCC-agnostic ``rendering`` slot behavior (the playblast encoder guard).

<a id="slots--_rigging"></a>
### `slots/_rigging.py`

Behavior shared by the Maya and Blender ``rigging`` panels.

- **[`class RiggingMixin`](tentacle/tentacle/slots/_rigging.py#L6)** — Shared ``rigging`` panel behavior.

<a id="slots--_scene"></a>
### `slots/_scene.py`

Behavior shared by the Maya and Blender ``scene`` panels.

- **[`class SceneMixin`](tentacle/tentacle/slots/_scene.py#L43)** — Shared ``scene`` panel behavior.
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

- **[`class Slots(QtCore.QObject)`](tentacle/tentacle/slots/_slots.py#L7)** — Provides methods that can be triggered by widgets in the ui.
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
  - `UvMixin.b000_init(self, widget)` — Initialize the Transfer option box.
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
  - `LightingSlots.tb000_init(self, widget)` — Lights From Geometry Init
  - `LightingSlots.tb000(self, widget)` — Create real area lights from the selected fixture meshes.

<a id="slots--blender--main"></a>
### `slots/blender/main.py`

- **[`class MainSlots(MainMixin, SlotsBlender)`](tentacle/tentacle/slots/blender/main.py#L9)** — Blender port of the shared ``main`` start menu — a workspace switcher (primary) with
  - `MainSlots.list000_init(self, widget)` — Initialize the Workspace tab.
  - `MainSlots.list000(self, item)` — Workspace tab dispatch — editing actions, recent-workspace selection, and the

<a id="slots--blender--materials"></a>
### `slots/blender/materials.py`

- **[`class MaterialsSlots(MaterialsMixin, SlotsBlender)`](tentacle/tentacle/slots/blender/materials.py#L8)** — Blender port of the shared ``materials`` menu — mirrors the Maya slot's workflow against
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

- **[`class NormalsSlots(NormalsMixin, SlotsBlender)`](tentacle/tentacle/slots/blender/normals.py#L7)** — Blender port of the shared ``normals`` menu.
  - `NormalsSlots.tb001_init(self, widget)`
  - `NormalsSlots.tb001(self, widget)` — Set Normals By Angle
  - `NormalsSlots.tb004_init(self, widget)`
  - `NormalsSlots.tb004(self, widget)` — Average Normals — soften edges so vertex normals are averaged across shared faces;
  - `NormalsSlots.b000(self)` — Soften Edge Normals (smooth shading).
  - `NormalsSlots.b001(self)` — Harden Edge Normals (flat shading).
  - `NormalsSlots.b006(self)` — Set To Face (vertex normals follow faces = flat shading).
  - `NormalsSlots.tb010(self, widget)` — Reverse Normals (Maya polyNormal modes: Reverse / Propagate / Conform /
  - `NormalsSlots.b002(self)` — Transfer Normals (active mesh → other selected, native Data-Transfer
  - `NormalsSlots.b004(self)` — Toggle lock/unlock vertex normals — Maya parity (m_lock_vertex_normals): report the

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

- **[`class RenderingSlots(RenderingMixin, SlotsBlender)`](tentacle/tentacle/slots/blender/rendering.py#L8)** — Blender port of the shared ``rendering`` menu.
  - `RenderingSlots.tb000_init(self, widget)`
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
  - `RiggingSlots.tb003(self, widget)` — Create Locator at Selection — an Empty (locator) at each selected object's origin,
  - `RiggingSlots.tb004_init(self, widget)`
  - `RiggingSlots.tb004(self, widget)` — Lock/Unlock Attributes (transform channel lock flags, per the chosen scope).
  - `RiggingSlots.cmb002_init(self, widget)`
  - `RiggingSlots.cmb002(self, index, widget)` — Quick Rig — a procedural rig opens its panel (mayatk parity);
  - `RiggingSlots.b004(self)` — Render Effects — co-located blendertk panel (per-object ``opacity`` fades driving Principled

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
  - `SceneSlots.b005(self)` — Naming — open the panel (Find / Rename / Convert Case / Strip Chars / Suffix by
  - `SceneSlots.b008(self)` — Export Selection (FBX, selected objects only).
  - `SceneSlots.b013(self)` — Mesh Converter (FBX -> GLB).
  - `SceneSlots.b_cleanup(self)` — Scene Cleanup — purge orphan datablocks (no users / no fake user).
  - `SceneSlots.b004(self)` — Hierarchy Sync — diff/repair the scene hierarchy against a reference .blend
  - `SceneSlots.b003(self)` — Audio Clips — native blendertk panel over the Video Sequence Editor (add/remove/
  - `SceneSlots.b015(self)` — Blendshape Animator — native blendertk panel (base+target mesh -> keyed shape key,
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
  - `UvSlots.b000(self, widget)` — Transfer UVs OR textures -- one pass per run (mirror of Maya's ``b000``).
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

- **[`class ArnoldSlots(SlotsMaya)`](tentacle/tentacle/slots/maya/arnold.py#L9)**

<a id="slots--maya--cache"></a>
### `slots/maya/cache.py`

- **[`class CacheSlots(SlotsMaya)`](tentacle/tentacle/slots/maya/cache.py#L9)**

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

- **[`class ConstrainSlots(SlotsMaya)`](tentacle/tentacle/slots/maya/constrain.py#L9)**

<a id="slots--maya--control"></a>
### `slots/maya/control.py`

- **[`class ControlSlots(SlotsMaya)`](tentacle/tentacle/slots/maya/control.py#L9)**

<a id="slots--maya--crease"></a>
### `slots/maya/crease.py`

- **[`class CreaseSlots(SlotsMaya)`](tentacle/tentacle/slots/maya/crease.py#L8)**
  - `CreaseSlots.tb000_init(self, widget)`
  - `CreaseSlots.tb000(self, widget)` — Crease: crease the selected edges (subdivision sharpness), with an optional smoothing angle.
  - `CreaseSlots.b002(self, widget)` — Transfer Crease Edges

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

- **[`class EditMeshSlots(SlotsMaya)`](tentacle/tentacle/slots/maya/edit_mesh.py#L9)**

<a id="slots--maya--editors"></a>
### `slots/maya/editors.py`

- **[`class EditorsSlots(SlotsMaya)`](tentacle/tentacle/slots/maya/editors.py#L19)**
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

- **[`class KeySlots(SlotsMaya)`](tentacle/tentacle/slots/maya/key.py#L9)**

<a id="slots--maya--lighting"></a>
### `slots/maya/lighting.py`

- **[`class LightingSlots(LightingMixin, SlotsMaya)`](tentacle/tentacle/slots/maya/lighting.py#L9)**
  - `LightingSlots.b000(self)` — Launch the HDR Manager.
  - `LightingSlots.b001(self)` — Launch the Lightmap Baker.
  - `LightingSlots.tb000_init(self, widget)` — Lights From Geometry Init
  - `LightingSlots.tb000(self, widget)` — Create real area lights from the selected fixture geometry.

<a id="slots--maya--lighting_shading"></a>
### `slots/maya/lighting_shading.py`

- **[`class LightingShadingSlots(SlotsMaya)`](tentacle/tentacle/slots/maya/lighting_shading.py#L9)**

<a id="slots--maya--main"></a>
### `slots/maya/main.py`

- **[`class MainSlots(MainMixin, SlotsMaya)`](tentacle/tentacle/slots/maya/main.py#L11)**
  - `MainSlots.list000_init(self, widget)` — Initialize the Workspace tab.
  - `MainSlots.list000(self, item)` — Workspace tab dispatch — editing actions, recent-workspace selection,

<a id="slots--maya--mash"></a>
### `slots/maya/mash.py`

- **[`class MashSlots(SlotsMaya)`](tentacle/tentacle/slots/maya/mash.py#L9)**

<a id="slots--maya--materials"></a>
### `slots/maya/materials.py`

- **[`class MaterialsSlots(MaterialsMixin, SlotsMaya)`](tentacle/tentacle/slots/maya/materials.py#L11)**
  - `MaterialsSlots.b007(self)` — Hypershade Editor
  - `MaterialsSlots.list000_init(self, widget)` — Assign list: scene materials + 'New' + 'Random'.
  - `MaterialsSlots.list000(self, item)` — Dispatch Assign list selection.
  - `MaterialsSlots.list001(self, item)` — Dispatch Tools list selection to the matching slot method.
  - `MaterialsSlots.cmb002_init(self, widget)` — Initialize Materials
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

- **[`class NormalsSlots(NormalsMixin, SlotsMaya)`](tentacle/tentacle/slots/maya/normals.py#L9)**
  - `NormalsSlots.tb001_init(self, widget)` — Initialize Set Normals By Angle
  - `NormalsSlots.tb001(self, widget)` — Set Normals By Angle
  - `NormalsSlots.tb004_init(self, widget)` — Initialize Average Normals
  - `NormalsSlots.tb004(self, widget)` — Average Normals
  - `NormalsSlots.b000(self)` — Soften Edge Normals
  - `NormalsSlots.b001(self)` — Harden all selected edges.
  - `NormalsSlots.b002(self)` — Transfer Normals
  - `NormalsSlots.b004(self)` — Toggle lock/unlock vertex normals.
  - `NormalsSlots.b006(self)` — Set To Face: set vertex normals to match their face normals (faceted shading).
  - `NormalsSlots.tb010(self, widget)` — Reverse Normals

<a id="slots--maya--nparticles"></a>
### `slots/maya/nparticles.py`

- **[`class NParticlesSlots(SlotsMaya)`](tentacle/tentacle/slots/maya/nparticles.py#L9)**

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

- **[`class PlaybackSlots(SlotsMaya)`](tentacle/tentacle/slots/maya/playback.py#L9)**

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

- **[`class RenderSlots(SlotsMaya)`](tentacle/tentacle/slots/maya/render.py#L9)**

<a id="slots--maya--rendering"></a>
### `slots/maya/rendering.py`

- **[`class RenderingSlots(RenderingMixin, SlotsMaya)`](tentacle/tentacle/slots/maya/rendering.py#L14)**
  - `RenderingSlots.tb000_init(self, widget)` — Export Playblast Init
  - `RenderingSlots.tb000(self, widget)` — Export Playblast
  - `RenderingSlots.tb001_init(self, widget)` — Render: camera, renderer, IPR, and smart redo.
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

- **[`class SelectSlots(SlotsMaya)`](tentacle/tentacle/slots/maya/select.py#L9)**

<a id="slots--maya--selection"></a>
### `slots/maya/selection.py`

- **[`class SelectionSlots(SelectionMixin, SlotsMaya)`](tentacle/tentacle/slots/maya/selection.py#L9)**
  - `SelectionSlots.list000_init(self, widget)` — Select by Type: Hierarchical type list.
  - `SelectionSlots.list000(self, item)` — Select by Type
  - `SelectionSlots.tb004_init(self, widget)` — Select by Type settings menu.
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

- **[`class SkeletonSlots(SlotsMaya)`](tentacle/tentacle/slots/maya/skeleton.py#L9)**

<a id="slots--maya--skin"></a>
### `slots/maya/skin.py`

- **[`class SkinSlots(SlotsMaya)`](tentacle/tentacle/slots/maya/skin.py#L9)**

<a id="slots--maya--stereo"></a>
### `slots/maya/stereo.py`

- **[`class StereoSlots(SlotsMaya)`](tentacle/tentacle/slots/maya/stereo.py#L9)**

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

- **[`class SurfacesSlots(SlotsMaya)`](tentacle/tentacle/slots/maya/surfaces.py#L9)**

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

- **[`class TexturingSlots(SlotsMaya)`](tentacle/tentacle/slots/maya/texturing.py#L9)**

<a id="slots--maya--toon"></a>
### `slots/maya/toon.py`

- **[`class ToonSlots(SlotsMaya)`](tentacle/tentacle/slots/maya/toon.py#L9)**

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

- **[`class UtilitiesSlots(SlotsMaya)`](tentacle/tentacle/slots/maya/utilities.py#L8)**
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
  - `UvSlots.b000(self, widget)` — Transfer UVs OR textures -- one pass per run (see ``b000_init``).
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

- **[`class VisualizeSlots(SlotsMaya)`](tentacle/tentacle/slots/maya/visualize.py#L9)**

<a id="slots--maya--windows"></a>
### `slots/maya/windows.py`

- **[`class WindowsSlots(SlotsMaya)`](tentacle/tentacle/slots/maya/windows.py#L9)**

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
  - `Tcl.chord_bindings(cls, key_show=None, chord_target=None)` *(class)* — The default chord→menu table for ``key_show`` (bare or Qt-named).
  - `Tcl.banner(cls, template=None, force=False)` *(class)* — Print the startup banner — the one sanctioned emitter of :func:`tentacle.greeting`.
  - `Tcl.launch(cls, key_show=None, **kwargs)` *(class)* — Start tentacle in the host DCC, deferring startup the way that host requires.
  - `Tcl.engine_dists(cls, host)` *(class)* — Distribution names ``pyproject``'s ``[project.optional-dependencies]`` declares for *host*.
  - `Tcl.engine_install_hint(cls, host=None)` *(class)* — The pip line that installs *host*'s engine, naming the interpreter to use.

<a id="tcl_blender"></a>
### `tcl_blender.py`

Blender entry point for tentacle's Qt marking menu — host + keymap bridge + launcher in one.

- [`ensure_qapp()`](tentacle/tentacle/tcl_blender.py#L2260) — Return the process QApplication, creating one if Blender has none.
- [`ensure_blender_widget(app)`](tentacle/tentacle/tcl_blender.py#L2265) — Establish ``app.blender_widget`` — the parent for the marking menu.
- [`start_event_pump(app, interval=0.01)`](tentacle/tentacle/tcl_blender.py#L2270) — Pump Qt events from Blender's timer loop so the Qt UI stays responsive (idempotent).
- [`blender_native_window()`](tentacle/tentacle/tcl_blender.py#L2275) — Blender's main GHOST window wrapped as a foreign ``QWindow`` (cached on the QApplication).
- [`launch(**kwargs)`](tentacle/tentacle/tcl_blender.py#L2280) — Stand up the Qt host and return a :class:`TclBlender` (idempotent).
- [`register(**kwargs)`](tentacle/tentacle/tcl_blender.py#L2285) — Blender add-on / startup entry.
- [`unregister()`](tentacle/tentacle/tcl_blender.py#L2290) — Blender add-on teardown.
- [`reload()`](tentacle/tentacle/tcl_blender.py#L2295) — Reload the tentacle ecosystem in place and re-register.
- [`diagnose()`](tentacle/tentacle/tcl_blender.py#L2300) — Return (and print) the live activation state.
- [`enable_click_debug()`](tentacle/tentacle/tcl_blender.py#L2305) — Turn on the opt-in click tracer.
- [`disable_click_debug()`](tentacle/tentacle/tcl_blender.py#L2310) — Remove the click tracer.
- **[`class TclBlender(MarkingMenu)`](tentacle/tentacle/tcl_blender.py#L1503)** — Marking Menu class overridden for use with Blender.
  - `TclBlender.get_main_window(cls)` *(class)* — Blender parent widget for the marking menu (set by :meth:`_QtHost.ensure_widget`).
  - `TclBlender.set_activation_key(self, new_key)` — Rebind the activation key — and move Blender's half of the binding with it.
  - `TclBlender.showEvent(self, event)`
  - `TclBlender.keyPressEvent(self, event)`
  - `TclBlender.keyReleaseEvent(self, event)`
- **[`class Diagnostics`](tentacle/tentacle/tcl_blender.py#L2025)** — The live-activation-state report — run in Blender's Python console to see why the key isn't
  - `Diagnostics.report(emit=True)` *(static)* — Return (and, when ``emit``, print) the live activation state — run in Blender's Python
- **[`class BlenderHost`](tentacle/tentacle/tcl_blender.py#L2138)** — Launcher + Blender add-on lifecycle coordinator — ties the Qt host, keymap bridge and menu
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

<a id="tentacle_installer"></a>
### `tentacle_installer.py`

Install, update or uninstall tentacle in a DCC -- one file, dropped in, no administrator rights.

- [`register()`](tentacle/tentacle/tentacle_installer.py#L1961) — Blender add-on entry: preferences UI, then finish any pending verb / install / launch.
- [`unregister()`](tentacle/tentacle/tentacle_installer.py#L1967) — Blender add-on teardown.
- [`onMayaDroppedPythonFile(*_args)`](tentacle/tentacle/tentacle_installer.py#L1973) — Maya drop hook: first drop installs and launches;
- **[`class TentacleInstaller`](tentacle/tentacle/tentacle_installer.py#L83)** — Provision tentacle into the host's per-user import dir, launch it, update or remove it.
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
