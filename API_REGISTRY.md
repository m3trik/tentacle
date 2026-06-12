# tentacle — API Registry

_Auto-generated. Do not edit by hand. Refresh via `m3trik/scripts/generate_api_registry.py`._

_Generated: 2026-06-12_

## Index

- [`__init__.py`](#__init__)
- [`slots/_hud_warnings.py`](#slots--_hud_warnings) — Shared HUD warning framework (DCC-agnostic).
- [`slots/_slots.py`](#slots--_slots)
- [`slots/blender/_slots_blender.py`](#slots--blender--_slots_blender)
- [`slots/blender/animation.py`](#slots--blender--animation)
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
- [`tcl_blender.py`](#tcl_blender) — Blender entry point for tentacle's Qt marking menu — host + keymap bridge + launcher in one.
- [`tcl_max.py`](#tcl_max)
- [`tcl_maya.py`](#tcl_maya)

---

<a id="__init__"></a>
### `__init__.py`

- [`greeting(string, outputToConsole=True)`](tentacle/tentacle/__init__.py#L26) — Format a string using preset variables.

<a id="slots--_hud_warnings"></a>
### `slots/_hud_warnings.py`

Shared HUD warning framework (DCC-agnostic).

- **[`class HudWarningsMixin`](tentacle/tentacle/slots/_hud_warnings.py#L22)**
  - `HudWarningsMixin.evaluate_warnings(self) -> list` — Return the subset of WARNING_DEFS whose check fires and is enabled.
  - `HudWarningsMixin.insert_warning_icons(self, hud, warnings) -> None` — Insert a single-line row of colored badges;
  - `HudWarningsMixin.insert_warning_details(self, hud, warnings) -> None` — Insert a formatted detail line per active warning.

<a id="slots--_slots"></a>
### `slots/_slots.py`

- **[`class Slots(QtCore.QObject)`](tentacle/tentacle/slots/_slots.py#L6)** — Provides methods that can be triggered by widgets in the ui.
  - `Slots.repeat_last_command(self)` — Repeat the last stored command.

<a id="slots--blender--_slots_blender"></a>
### `slots/blender/_slots_blender.py`

- **[`class SlotsBlender(Slots)`](tentacle/tentacle/slots/blender/_slots_blender.py#L7)** — App specific methods inherited by all other Blender slot classes.
  - `SlotsBlender.selected_objects()` *(static)* — The current object selection (filtered of ``None``) — shared by all Blender slots.

<a id="slots--blender--animation"></a>
### `slots/blender/animation.py`

- **[`class Animation(SlotsBlender)`](tentacle/tentacle/slots/blender/animation.py#L8)** — Blender port of the shared ``animation`` menu.
  - `Animation.tb000_init(self, widget)`
  - `Animation.tb000(self, widget)` — Go To Frame
  - `Animation.tb001(self, widget)` — Invert Keys (mirror key times about the range center — reverses the motion).
  - `Animation.tb003_init(self, widget)`
  - `Animation.tb003(self, widget)` — Stagger Keys (re-time selected objects sequentially).
  - `Animation.tb009(self, widget)` — Snap Keys to Frames
  - `Animation.tb010(self, widget)` — Delete Keys (clear all animation on the selection).
  - `Animation.tb012(self, widget)` — Copy Keys (from the active object).
  - `Animation.tb018(self, widget)` — Paste Keys (independent copies onto the selection).
  - `Animation.tb014_init(self, widget)`
  - `Animation.tb014(self, widget)` — Scale Keys
  - `Animation.tb017(self, widget)` — Step Tangents (constant interpolation on every key).
  - `Animation.b005(self)` — Fit Playback Range (to the keyed extent of the selection, or the whole scene).
  - `Animation.b000(self)` — Shot Sequencer — mayatk window;
  - `Animation.b004(self)` — Shot Manifest — mayatk window;
  - `Animation.tb002(self, widget)` — Adjust Key Spacing — not yet ported.
  - `Animation.tb004(self, widget)` — Transfer Keys — not yet ported.
  - `Animation.tb005(self, widget)` — Add/Remove Intermediate Keys — not yet ported.
  - `Animation.tb006(self, widget)` — Move Keys — use the Dope Sheet (G to grab keys).
  - `Animation.tb007(self, widget)` — Align Keys — not yet ported.
  - `Animation.tb008(self, widget)` — Set Visibility Keys — not yet ported.
  - `Animation.tb013(self, widget)` — Select Keys — use the Dope Sheet / Graph Editor.

<a id="slots--blender--cameras"></a>
### `slots/blender/cameras.py`

- **[`class Cameras(SlotsBlender)`](tentacle/tentacle/slots/blender/cameras.py#L24)** — Blender port of the shared ``cameras`` menu.
  - `Cameras.list000_init(self, widget)` — Initialize Camera Options List
  - `Cameras.list000(self, item)` — Camera Options List
  - `Cameras.b000(self)` — Cameras: Back View
  - `Cameras.b001(self)` — Cameras: Top View
  - `Cameras.b002(self)` — Cameras: Right View
  - `Cameras.b003(self)` — Cameras: Left View
  - `Cameras.b004(self)` — Cameras: Perspective View
  - `Cameras.b005(self)` — Cameras: Front View
  - `Cameras.b006(self)` — Cameras: Bottom View
  - `Cameras.b007(self)` — Cameras: Align View — Maya align-camera-to-polygon has no direct Blender analogue.
  - `Cameras.b010(self)` — Camera: Dolly — Blender viewport navigation is modal, not a persistent tool.
  - `Cameras.b011(self)` — Camera: Roll
  - `Cameras.b012(self)` — Camera: Truck
  - `Cameras.b013(self)` — Camera: Orbit
  - `Cameras.toggle_camera_view(self)` — Toggle between the last two camera views in history (DCC-agnostic switchboard logic).

<a id="slots--blender--crease"></a>
### `slots/blender/crease.py`

- **[`class Crease(SlotsBlender)`](tentacle/tentacle/slots/blender/crease.py#L7)** — Blender port of the shared ``crease`` menu.
  - `Crease.tb000_init(self, widget)`
  - `Crease.tb000(self, widget)` — Crease
  - `Crease.b002(self, widget)` — Transfer Crease Edges — needs a Data-Transfer edge-data setup;

<a id="slots--blender--deformation"></a>
### `slots/blender/deformation.py`

- **[`class Deformation(SlotsBlender)`](tentacle/tentacle/slots/blender/deformation.py#L6)** — Blender port of the shared ``deformation`` menu.
  - `Deformation.tb001(self, widget)` — Curtain Generator — mayatk tool;

<a id="slots--blender--display"></a>
### `slots/blender/display.py`

- **[`class DisplaySlots(SlotsBlender)`](tentacle/tentacle/slots/blender/display.py#L8)** — Blender port of the shared ``display`` menu.
  - `DisplaySlots.list000_init(self, widget)` — Initialize Display expandable list (categories → actions).
  - `DisplaySlots.list000(self, item)` — Dispatch a Display action and report state via message_box.
  - `DisplaySlots.b013(self)` — Explode View — separate window not ported to Blender yet.
  - `DisplaySlots.b014(self)` — Color Manager — separate window not ported to Blender yet.

<a id="slots--blender--duplicate"></a>
### `slots/blender/duplicate.py`

- **[`class Duplicate(SlotsBlender)`](tentacle/tentacle/slots/blender/duplicate.py#L8)** — Blender port of the shared ``duplicate`` menu.
  - `Duplicate.header_init(self, widget)`
  - `Duplicate.tb000_init(self, widget)`
  - `Duplicate.tb000(self, widget)` — Convert to Instances (selected objects share the active object's data).
  - `Duplicate.tb001_init(self, widget)`
  - `Duplicate.tb001(self, widget)` — Select Instanced Objects
  - `Duplicate.b005(self)` — Uninstance Selected Objects (make their data single-user).
  - `Duplicate.b000(self)` — Mirror — separate menu not ported to Blender yet.
  - `Duplicate.b006(self)` — Duplicate Linear — separate menu not ported to Blender yet.
  - `Duplicate.b007(self)` — Duplicate Radial — separate menu not ported to Blender yet.
  - `Duplicate.b008(self)` — Duplicate Grid — separate menu not ported to Blender yet.

<a id="slots--blender--edit"></a>
### `slots/blender/edit.py`

- **[`class Edit(SlotsBlender)`](tentacle/tentacle/slots/blender/edit.py#L9)** — Blender port of the shared ``edit`` menu.
  - `Edit.header_init(self, widget)`
  - `Edit.tb000_init(self, widget)`
  - `Edit.tb000(self, widget)` — Mesh Cleanup
  - `Edit.tb002(self, widget)` — Delete Selected (objects in object mode, components by select mode in edit mode).
  - `Edit.list000_init(self, widget)` — Initialize Create Primitives list.
  - `Edit.list000(self, item)` — Create Primitive
  - `Edit.list001_init(self, widget)` — Initialize Convert list.
  - `Edit.list001(self, item)` — Convert the selected object(s) to another type.
  - `Edit.tb001(self, widget)` — Delete History — Blender has no construction history (modifier stack is non-destructive).
  - `Edit.tb004(self, widget)` — Node Locking — Maya node locking has no Blender analogue.
  - `Edit.b000(self)` — Cut On Axis — mesh bisect;
  - `Edit.b021(self, widget)` — Transfer Maps — needs a bake/Data-Transfer setup;
  - `Edit.b022(self, widget)` — Transfer Vertex Order — Maya-specific;
  - `Edit.b023(self, widget)` — Transfer Attribute Values — needs a Data-Transfer setup;
  - `Edit.b027(self, widget)` — Shading Sets — Maya shading groups;

<a id="slots--blender--editors"></a>
### `slots/blender/editors.py`

- **[`class Editors(SlotsBlender)`](tentacle/tentacle/slots/blender/editors.py#L8)** — Blender port of the shared ``editors`` menu.
  - `Editors.list000_init(self, widget)` — Initialize the editors list (categories → Blender editors).
  - `Editors.list000(self, item)` — Open the picked editor in a new window.
  - `Editors.b000(self)` — Attributes (Properties editor)
  - `Editors.b001(self)` — Outliner
  - `Editors.b002(self)` — Tool (active-tool settings live in the Properties editor's Tool tab)
  - `Editors.b003(self)` — Layers (Blender's collections live in the Outliner)
  - `Editors.b004(self)` — Channels (object data lives in the Properties editor)
  - `Editors.b005(self)` — Node Editor (Shader Editor)
  - `Editors.b009(self)` — Time & Range (Timeline editor)
  - `Editors.b010(self)` — Script Output (Info log)
  - `Editors.b011(self)` — Command Line (Python Console)
  - `Editors.b006(self)` — Dependency Graph — Blender has no user-facing dependency-graph editor.
  - `Editors.b007(self)` — Status Line — Maya UI chrome;
  - `Editors.b008(self)` — Shelf — Maya UI chrome;
  - `Editors.b012(self)` — Help Line — Maya UI chrome;
  - `Editors.b013(self)` — Tool Box — Blender's toolbar is the T-panel inside each editor.

<a id="slots--blender--hud"></a>
### `slots/blender/hud.py`

- **[`class StatusMixin`](tentacle/tentacle/slots/blender/hud.py#L11)**
  - `StatusMixin.insert_scene_status(self, hud) -> None`
- **[`class SelectionMixin`](tentacle/tentacle/slots/blender/hud.py#L41)**
  - `SelectionMixin.insert_selection_info(self, hud, selection) -> None`
  - `SelectionMixin.insert_component_info(self, hud, active) -> None` — Selected/total component counts for the mesh being edited (cheap:
- **[`class WarningsMixin(HudWarningsMixin)`](tentacle/tentacle/slots/blender/hud.py#L108)** — Blender HUD warnings — the framework lives in the shared
- **[`class HudSlots(SlotsBlender, StatusMixin, SelectionMixin, WarningsMixin)`](tentacle/tentacle/slots/blender/hud.py#L167)** — HUD Slots for Blender, providing scene and selection information.
  - `HudSlots.request_hud_build(self) -> None` — Start a new HUD build request, only the latest token will be used.
  - `HudSlots.construct_hud(self) -> None`

<a id="slots--blender--lighting"></a>
### `slots/blender/lighting.py`

- **[`class Lighting(SlotsBlender)`](tentacle/tentacle/slots/blender/lighting.py#L6)** — Blender port of the shared ``lighting`` menu.
  - `Lighting.b000(self)` — HDR Manager — mayatk panel;
  - `Lighting.b001(self)` — Lightmap Baker — mayatk panel;

<a id="slots--blender--main"></a>
### `slots/blender/main.py`

- **[`class Main(SlotsBlender)`](tentacle/tentacle/slots/blender/main.py#L10)** — Blender port of the shared ``main`` start menu — a workspace directory browser.
  - `Main.list000_init(self, widget)` — Initialize Workspace Browser
  - `Main.list000(self, item)` — Workspace Browser

<a id="slots--blender--materials"></a>
### `slots/blender/materials.py`

- **[`class MaterialsSlots(SlotsBlender)`](tentacle/tentacle/slots/blender/materials.py#L9)** — Blender port of the shared ``materials`` menu.
  - `MaterialsSlots.cmb002_init(self, widget)` — Initialize the scene-materials combo (label -> material datablock).
  - `MaterialsSlots.cmb002(self, index, widget)` — Current Material (selection only — assignment is on the b-buttons).
  - `MaterialsSlots.tb000_init(self, widget)`
  - `MaterialsSlots.tb000(self, widget)` — Select By Material
  - `MaterialsSlots.b002(self, widget)` — Get Material: set the combo to the selection's material.
  - `MaterialsSlots.b004(self, widget)` — Assign Random
  - `MaterialsSlots.b005(self, widget)` — Assign Current
  - `MaterialsSlots.b006(self, widget)` — Assign New Material
  - `MaterialsSlots.b013(self)` — Reload Textures
  - `MaterialsSlots.list000_init(self, widget)` — Assign list: scene materials + New + Random.
  - `MaterialsSlots.list000(self, item)` — Assign the picked material (or a New/Random one) to the selection.
  - `MaterialsSlots.list001_init(self, widget)` — Tools list — Maya-only windows (Stingray/game shader/Arnold bridge);

<a id="slots--blender--normals"></a>
### `slots/blender/normals.py`

- **[`class Normals(SlotsBlender)`](tentacle/tentacle/slots/blender/normals.py#L8)** — Blender port of the shared ``normals`` menu.
  - `Normals.tb001_init(self, widget)`
  - `Normals.tb001(self, widget)` — Set Normals By Angle
  - `Normals.tb004_init(self, widget)`
  - `Normals.tb004(self, widget)` — Average Normals (smooth shading averages vertex normals).
  - `Normals.b000(self)` — Soften Edge Normals (smooth shading).
  - `Normals.b001(self)` — Harden Edge Normals (flat shading).
  - `Normals.b006(self)` — Set To Face (vertex normals follow faces = flat shading).
  - `Normals.tb010_init(self, widget)`
  - `Normals.tb010(self, widget)` — Reverse Normals
  - `Normals.b002(self)` — Transfer Normals — needs a Data-Transfer custom-normal setup;
  - `Normals.b004(self)` — Lock/Unlock Vertex Normals — Maya normal locking has no direct Blender analogue.

<a id="slots--blender--nurbs"></a>
### `slots/blender/nurbs.py`

- **[`class Nurbs(SlotsBlender)`](tentacle/tentacle/slots/blender/nurbs.py#L8)** — Blender port of the shared ``nurbs`` menu — largely HIDE per the plan (Blender has no
  - `Nurbs.b058(self)` — Curve to Tube (curve bevel).
  - `Nurbs.tb000(self, widget)` — Revolve (Screw modifier about Z).
  - `Nurbs.list000_init(self, widget)` — Maya NURBS action list (mel dispatcher) — hidden;
  - `Nurbs.tb001(self, widget)` — Loft — Blender has no Maya-grade loft;
  - `Nurbs.b030(self)` — Extrude — use mesh/curve extrude in Edit Mode (E).
  - `Nurbs.b056(self)` — Image Tracer — not yet ported (Blender: import SVG / trace image add-on).

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
  - `Pivot.tb002(self, widget)` — Transfer Pivot — Maya's per-channel (translate/rotate/scale) pivot transfer has no
  - `Pivot.tb003(self, widget)` — World-Aligned Pivot — Maya manipulator-pivot orientation;
  - `Pivot.b004(self)` — Bake Pivot — Blender object origins are always baked into the transform (no-op).

<a id="slots--blender--polygons"></a>
### `slots/blender/polygons.py`

- **[`class PolygonsSlots(SlotsBlender)`](tentacle/tentacle/slots/blender/polygons.py#L8)** — Blender port of the shared ``polygons`` menu.
  - `PolygonsSlots.tb000_init(self, widget)`
  - `PolygonsSlots.tb000(self, widget)` — Merge Vertices
  - `PolygonsSlots.tb002(self, widget)` — Separate (split the mesh into loose parts).
  - `PolygonsSlots.tb003(self, widget)` — Extrude (in place — move with G after).
  - `PolygonsSlots.tb004(self, widget)` — Combine Selected Meshes
  - `PolygonsSlots.tb005(self, widget)` — Detach (separate the selected components into a new object).
  - `PolygonsSlots.tb006_init(self, widget)`
  - `PolygonsSlots.tb006(self, widget)` — Inset Face Region
  - `PolygonsSlots.tb007_init(self, widget)`
  - `PolygonsSlots.tb007(self, widget)` — Divide Facet (subdivide the selected components).
  - `PolygonsSlots.tb008_init(self, widget)`
  - `PolygonsSlots.tb008(self, widget)` — Boolean Operation (active mesh = base, other selected = operands).
  - `PolygonsSlots.tb009(self, widget)` — Snap Closest Verts — not yet ported (use snap + Auto Merge).
  - `PolygonsSlots.b001(self)` — Fill Holes
  - `PolygonsSlots.b003(self)` — Symmetrize
  - `PolygonsSlots.b006(self)` — Bridge (selected edge loops).
  - `PolygonsSlots.b008(self)` — Weld Center (merge selected at center).
  - `PolygonsSlots.b009(self)` — Collapse Component
  - `PolygonsSlots.b011(self)` — Bevel
  - `PolygonsSlots.b012(self)` — Multi-Cut Tool (Knife).
  - `PolygonsSlots.b022(self)` — Attach (join the selected meshes).
  - `PolygonsSlots.b032(self)` — Poke
  - `PolygonsSlots.b047(self)` — Insert Edgeloop (Loop Cut tool).
  - `PolygonsSlots.b051(self)` — Offset Edgeloop
  - `PolygonsSlots.b000(self)` — Circularize — needs the LoopTools add-on (Circle);
  - `PolygonsSlots.b007(self)` — Interactive Bridge — modal Maya tool;
  - `PolygonsSlots.b034(self)` — Wedge — no non-modal Blender analogue (use Spin).
  - `PolygonsSlots.b038(self)` — Assign Invisible — Maya invisible faces have no Blender analogue.
  - `PolygonsSlots.b043(self)` — Target Weld — enable snap (Vertex) + Auto Merge for the same workflow.
  - `PolygonsSlots.b049(self)` — Slide Edge — modal in Blender (GG);
  - `PolygonsSlots.b053(self)` — Edit Edge Flow — needs the Edit-Flow add-on;

<a id="slots--blender--preferences"></a>
### `slots/blender/preferences.py`

- **[`class Preferences(SlotsBlender)`](tentacle/tentacle/slots/blender/preferences.py#L7)** — Blender port of the shared ``preferences`` menu.
  - `Preferences.cmb001_init(self, widget)`
  - `Preferences.cmb001(self, index, widget)` — Set Working Units: Linear
  - `Preferences.cmb002_init(self, widget)`
  - `Preferences.cmb002(self, index, widget)` — Set Working Units: Time (frame rate)
  - `Preferences.s000_init(self, widget)`
  - `Preferences.s001_init(self, widget)`
  - `Preferences.b001(self)` — Color Settings → Blender Preferences (Themes).
  - `Preferences.b008(self)` — Hotkeys → Blender Preferences (Keymap).
  - `Preferences.b009(self)` — Plug-In Manager → Blender Preferences (Add-ons).
  - `Preferences.b010(self)` — Settings/Preferences → Blender Preferences (Interface).

<a id="slots--blender--rendering"></a>
### `slots/blender/rendering.py`

- **[`class Rendering(SlotsBlender)`](tentacle/tentacle/slots/blender/rendering.py#L8)** — Blender port of the shared ``rendering`` menu.
  - `Rendering.cmb001_init(self, widget)` — Initialize the render-camera combo (label -> camera object).
  - `Rendering.cmb001(self, index, widget)` — Set the scene's active (render) camera.
  - `Rendering.tb000_init(self, widget)`
  - `Rendering.tb000(self, widget)` — Export Playblast (OpenGL viewport render of the frame range).
  - `Rendering.b000(self)` — Render Current Frame
  - `Rendering.b001(self)` — Render Settings (Properties editor, Render tab)
  - `Rendering.b002(self)` — Show Last Render
  - `Rendering.b003(self)` — Render Setup — Maya editor;
  - `Rendering.b004(self)` — Rendering Flags — Maya editor with no Blender analogue.

<a id="slots--blender--rigging"></a>
### `slots/blender/rigging.py`

- **[`class Rigging(SlotsBlender)`](tentacle/tentacle/slots/blender/rigging.py#L8)** — Blender port of the shared ``rigging`` menu.
  - `Rigging.cmb001_init(self, widget)`
  - `Rigging.cmb001(self, index, widget)` — Create rigging primitives.
  - `Rigging.tb000(self, widget)` — Toggle Display Local Rotation Axes (``show_axis``).
  - `Rigging.tb003(self, widget)` — Create Locator at Selection (an Empty at each selected object's origin;
  - `Rigging.b003(self)` — Remove Locator (delete selected Empties).
  - `Rigging.tb004_init(self, widget)`
  - `Rigging.tb004(self, widget)` — Lock/Unlock Attributes (toggles based on the first object's current state).
  - `Rigging.cmb002(self, index, widget)` — Quick Rig — Maya HumanIK workflow;
  - `Rigging.tb001(self, widget)` — Constraint Switch — not yet ported (Blender bone constraints differ structurally).
  - `Rigging.b004(self)` — Render Opacity — mayatk tool;

<a id="slots--blender--scene"></a>
### `slots/blender/scene.py`

- **[`class SceneSlots(SlotsBlender)`](tentacle/tentacle/slots/blender/scene.py#L10)** — Blender port of the shared ``scene`` menu.
  - `SceneSlots.list000_init(self, widget)` — Initialize Recent Files
  - `SceneSlots.list000(self, item)` — Recent Files
  - `SceneSlots.cmb002_init(self, widget)` — Initialize Autosave (recent temp-dir .blend autosaves, newest first).
  - `SceneSlots.cmb002(self, index, widget)` — Autosave
  - `SceneSlots.cmb003_init(self, widget)`
  - `SceneSlots.cmb003(self, index, widget)` — Import
  - `SceneSlots.cmb004_init(self, widget)`
  - `SceneSlots.cmb004(self, index, widget)` — Export
  - `SceneSlots.tb003(self, widget)` — Export Scene (FBX file dialog)
  - `SceneSlots.b007(self)` — Import file
  - `SceneSlots.tb000(self, widget)` — Set Workspace — Blender derives the workspace from the saved .blend's directory.
  - `SceneSlots.b001(self)` — Reference Manager — Blender uses library linking (File ▸ Link);
  - `SceneSlots.b002(self)` — Scene Exporter — mayatk window;
  - `SceneSlots.b004(self)` — Hierarchy Manager — mayatk window;
  - `SceneSlots.b005(self)` — Naming — mayatk window;

<a id="slots--blender--selection"></a>
### `slots/blender/selection.py`

- **[`class Selection(SlotsBlender)`](tentacle/tentacle/slots/blender/selection.py#L10)** — Blender port of the shared ``selection`` menu.
  - `Selection.tb000_init(self, widget)`
  - `Selection.tb000(self, widget)` — Select Nth
  - `Selection.tb001_init(self, widget)`
  - `Selection.tb001(self, widget)` — Select Similar
  - `Selection.tb002_init(self, widget)`
  - `Selection.tb002(self, widget)` — Select Island (connected region)
  - `Selection.tb003_init(self, widget)`
  - `Selection.tb003(self, widget)` — Select Edges By Angle
  - `Selection.cmb003_init(self, widget)`
  - `Selection.cmb003(self, index, widget)` — Convert the current selection to another component type.
  - `Selection.chk004(self, state, widget)` — Ignore Backfacing — toggle viewport X-ray (occlude) so only front faces select.
  - `Selection.chk005_init(self, widget)`
  - `Selection.chk005(self, state, widget)` — Select Style: Box (Marquee)
  - `Selection.chk006(self, state, widget)` — Select Style: Lasso
  - `Selection.chk007(self, state, widget)` — Select Style: Circle (Paint)
  - `Selection.b001(self)` — Toggle Selectability of the selected object(s).
  - `Selection.cmb001_init(self, widget)`
  - `Selection.cmb001(self, index, widget)` — Reorder Selection — not yet ported to Blender.
  - `Selection.cmb005_init(self, widget)`
  - `Selection.cmb005(self, index, widget)` — Selection Constraints — Maya draggable-constraint tool has no direct Blender analogue.
  - `Selection.list000(self, *args)` — Select by Type — deferred (needs blendertk type categories + the list widget).

<a id="slots--blender--settings"></a>
### `slots/blender/settings.py`

- **[`class Settings(SlotsBlender)`](tentacle/tentacle/slots/blender/settings.py#L6)** — Blender port of the shared ``settings`` menu.
  - `Settings.header_init(self, widget)`
  - `Settings.tb000(self)` — Update Package — Maya's updater shells out to mayapy;
  - `Settings.tb001(self)` — Reload Scripts — live reload uses a Maya-specific mechanism;
  - `Settings.b020(self)` — UI Style Editor
  - `Settings.b021(self)` — Hotkey Editor
  - `Settings.b022(self)` — UI Browser
  - `Settings.b_reset_bindings(self)` — Reset marking-menu bindings to defaults.

<a id="slots--blender--subdivision"></a>
### `slots/blender/subdivision.py`

- **[`class Subdivision(SlotsBlender)`](tentacle/tentacle/slots/blender/subdivision.py#L7)** — Blender port of the shared ``subdivision`` menu.
  - `Subdivision.tb000_init(self, widget)`
  - `Subdivision.tb000(self, widget)` — Decimate
  - `Subdivision.s000(self, value, widget)` — Division Level (live Subdivision-Surface viewport level).
  - `Subdivision.s001(self, value, widget)` — Tesselation Level (Subdivision-Surface render level).
  - `Subdivision.b000(self)` — Quadrangulate (tris -> quads).
  - `Subdivision.b001(self)` — Triangulate
  - `Subdivision.b005(self)` — Reduce (decimate to 50%).
  - `Subdivision.b008(self)` — Add Divisions - Subdivide Mesh
  - `Subdivision.b011(self)` — Apply Smooth Preview (live Subdivision-Surface modifier).
  - `Subdivision.b028(self)` — Quad Draw — Maya retopo tool;

<a id="slots--blender--symmetry"></a>
### `slots/blender/symmetry.py`

- **[`class Symmetry(SlotsBlender)`](tentacle/tentacle/slots/blender/symmetry.py#L7)** — Blender port of the shared ``symmetry`` menu.
  - `Symmetry.chk000_init(self, widget)` — Set initial symmetry state from the active mesh.
  - `Symmetry.chk000(self, state, widget)` — Symmetry X
  - `Symmetry.chk001(self, state, widget)` — Symmetry Y
  - `Symmetry.chk002(self, state, widget)` — Symmetry Z
  - `Symmetry.chk005_init(self, widget)` — Set symmetry reference space (position vs topology).
  - `Symmetry.chk005(self, state, widget)` — Symmetry: Topo (match mirrored verts by topology instead of position).

<a id="slots--blender--transform"></a>
### `slots/blender/transform.py`

- **[`class TransformSlots(SlotsBlender)`](tentacle/tentacle/slots/blender/transform.py#L8)** — Blender port of the shared ``transform`` menu.
  - `TransformSlots.tb000_init(self, widget)`
  - `TransformSlots.tb000(self, widget)` — Drop To Grid
  - `TransformSlots.tb002_init(self, widget)`
  - `TransformSlots.tb002(self, widget)` — Freeze Transformations
  - `TransformSlots.tb005_init(self, widget)`
  - `TransformSlots.tb005(self, widget)` — Move To (align source object(s) to the active/target object).
  - `TransformSlots.b001(self)` — Match Scale (rescale source object(s) to the active/target object).
  - `TransformSlots.cmb002_init(self, widget)`
  - `TransformSlots.cmb002(self, index, widget)` — Align To — Maya snap/align tools have no direct Blender analogue yet.
  - `TransformSlots.tb001(self, widget)` — Scale Connected Edges — component op, not yet ported.
  - `TransformSlots.b002(self)` — Un-Freeze Transforms — needs stored original transforms;
  - `TransformSlots.tb003(self, widget)` — Transform Constraints — Maya edge/surface/make-live constraints have no Blender analogue.
  - `TransformSlots.tb004(self, widget)` — Transform Snap — Maya manipulator snap;
  - `TransformSlots.chk023_init(self, widget)` — Snap Rotate toggle (Maya manipulator snap) — hidden until tb004 is ported.
  - `TransformSlots.chk024_init(self, widget)` — Constraint: Edge toggle — hidden until tb003 is ported.
  - `TransformSlots.chk025_init(self, widget)` — Constraint: Surface toggle — hidden until tb003 is ported.

<a id="slots--blender--utilities"></a>
### `slots/blender/utilities.py`

- **[`class Utilities(SlotsBlender)`](tentacle/tentacle/slots/blender/utilities.py#L7)** — Blender port of the shared ``utilities`` menu.
  - `Utilities.b000(self)` — Measure
  - `Utilities.b001(self)` — Annotation
  - `Utilities.b002(self)` — Calculator
  - `Utilities.b003(self)` — Grease Pencil (add an empty stroke object to draw into)

<a id="slots--blender--uv"></a>
### `slots/blender/uv.py`

- **[`class Uv(SlotsBlender)`](tentacle/tentacle/slots/blender/uv.py#L8)** — Blender port of the shared ``uv`` menu.
  - `Uv.tb000(self, widget)` — Pack UVs
  - `Uv.tb001(self, widget)` — Auto Unwrap (Smart UV Project)
  - `Uv.tb004(self, widget)` — Unfold (angle-based unwrap)
  - `Uv.tb009(self, widget)` — Cut Cylinder (cylinder project)
  - `Uv.b005(self)` — Cut UVs (mark seam on selected edges)
  - `Uv.b011(self)` — Sew UVs (clear seam on selected edges)
  - `Uv.b021(self, widget)` — Unfold and Pack UVs
  - `Uv.b023(self)` — Move To UV Space: Left
  - `Uv.b024(self)` — Move To UV Space: Down
  - `Uv.b025(self)` — Move To UV Space: Up
  - `Uv.b026(self)` — Move To UV Space: Right
  - `Uv.tb007(self, widget)` — Cleanup UV Sets (keep only the first UV map).
  - `Uv.tb005(self, widget)` — Straighten UV — UV-editor align op;
  - `Uv.tb006(self, widget)` — Distribute — UV-editor align/distribute op;
  - `Uv.tb008(self, widget)` — Mirror UVs — UV-editor mirror op;
  - `Uv.tb022(self, widget)` — Cut UV hard edges — seam-from-sharp;
  - `Uv.b000(self, widget)` — Transfer UVs — needs a Data-Transfer UV setup;
  - `Uv.b003(self)` — Get Texel Density — needs a texel-density helper;
  - `Uv.b004(self)` — Set Texel Density — needs a texel-density helper;
  - `Uv.b029(self, widget)` — Pin / Unpin UVs — UV-editor pin;
  - `Uv.b030(self, widget)` — Stack / Unstack shells — not yet ported.
  - `Uv.b031(self)` — Open UV Editor — switch an area to the UV editor;
  - `Uv.b032(self)` — RizomUV Bridge — external tool;
  - `Uv.cmb002(self, index, widget)` — Transform — UV transform options;
  - `Uv.cmb003(self, index, widget)` — UV set options — not yet ported.
  - `Uv.s003(self, value, widget)` — UV spin option — not yet wired.

<a id="slots--maya--_slots_maya"></a>
### `slots/maya/_slots_maya.py`

- **[`class SlotsMaya(Slots)`](tentacle/tentacle/slots/maya/_slots_maya.py#L6)** — App specific methods inherited by all other app specific slot classes.

<a id="slots--maya--animation"></a>
### `slots/maya/animation.py`

- **[`class Animation(SlotsMaya)`](tentacle/tentacle/slots/maya/animation.py#L11)**
  - `Animation.header_init(self, widget)` — Header Init
  - `Animation.tb000_init(self, widget)` — Go To Frame Init
  - `Animation.tb000(self, widget)` — Go To Frame
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
  - `Animation.tb006(self, widget)` — Move Keys
  - `Animation.tb007_init(self, widget)` — Align Selected Keyframes Init
  - `Animation.tb007(self, widget)` — Align Selected Keyframes
  - `Animation.tb008_init(self, widget)` — Set Visibility Keys Init
  - `Animation.tb008(self, widget)` — Set Visibility Keys
  - `Animation.tb009_init(self, widget)` — Snap Keys to Frames Init
  - `Animation.tb009(self, widget)` — Snap Keys to Frames
  - `Animation.tb010_init(self, widget)` — Delete Keys Init
  - `Animation.tb010(self, widget)` — Delete Keys
  - `Animation.tb011_init(self, widget)` — Tie/Untie Keyframes Init
  - `Animation.tb011(self, widget)` — Tie/Untie Keyframes
  - `Animation.tb013_init(self, widget)` — Select Keys Init
  - `Animation.tb013(self, widget)` — Select Keys
  - `Animation.tb014_init(self, widget)` — Scale Keys Init
  - `Animation.tb014(self, widget)` — Scale Keys
  - `Animation.tb015_init(self, widget)` — Repair Corrupted Curves - Initialize option box
  - `Animation.tb015(self, widget)` — Repair Corrupted Curves
  - `Animation.tb016_init(self, widget)` — Get Animation Info — option box.
  - `Animation.tb016(self, widget)` — Get Animation Info — render the report to the viewer dialog.
  - `Animation.tb017_init(self, widget)` — Step Tangents Init
  - `Animation.tb017(self, widget)` — Step Tangents — set stepped tangents on keys.
  - `Animation.tb012_init(self, widget)` — Copy Keys Init
  - `Animation.tb012(self, widget)` — Copy Keys
  - `Animation.tb018_init(self, widget)` — Paste Keys Init
  - `Animation.tb018(self, widget)` — Paste Keys
  - `Animation.tb019_init(self, widget)` — Optimize Keys Init
  - `Animation.tb019(self, widget)` — Optimize Keys — remove redundant animation data.
  - `Animation.tb020_init(self, widget)` — Smart Bake Init
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

- **[`class Cameras(SlotsMaya)`](tentacle/tentacle/slots/maya/cameras.py#L10)**
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
  - `Cameras.toggle_camera_view(self)` — Toggle between the last two camera views in history.

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
  - `Crease.tb000(self, widget)` — Crease
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

- **[`class DisplaySlots(SlotsMaya)`](tentacle/tentacle/slots/maya/display.py#L10)**
  - `DisplaySlots.list000_init(self, widget)` — Initialize Display expandable list (categories → actions).
  - `DisplaySlots.list000(self, item)` — Dispatch a Display action and report state via message_box.
  - `DisplaySlots.b000(self)` — Set Wireframe color
  - `DisplaySlots.b001(self)` — Wireframe Selected
  - `DisplaySlots.b002(self)` — Hide Selected
  - `DisplaySlots.b003(self)` — Show Selected
  - `DisplaySlots.b004(self)` — Show Geometry
  - `DisplaySlots.b005(self)` — Xray Selected
  - `DisplaySlots.b006(self)` — Un-Xray All
  - `DisplaySlots.b007(self)` — Xray Other
  - `DisplaySlots.b009(self)` — Toggle Material Override
  - `DisplaySlots.b011(self)` — Toggle Component ID Display
  - `DisplaySlots.b012(self)` — Wireframe Non Active (Wireframe All But The Selected Item)
  - `DisplaySlots.b013(self)` — Explode View GUI
  - `DisplaySlots.b014(self)` — Color Manager GUI
  - `DisplaySlots.b021(self)` — Template Selected
  - `DisplaySlots.b022(self)` — Display UV Borders
  - `DisplaySlots.b023(self)` — Soft Edge Display
  - `DisplaySlots.b024(self)` — Display Face Normals

<a id="slots--maya--duplicate"></a>
### `slots/maya/duplicate.py`

- **[`class Duplicate(SlotsMaya)`](tentacle/tentacle/slots/maya/duplicate.py#L8)**
  - `Duplicate.header_init(self, widget)`
  - `Duplicate.tb000_init(self, widget)`
  - `Duplicate.tb000(self, widget)` — Convert to Instances
  - `Duplicate.tb001_init(self, widget)`
  - `Duplicate.tb001(self, widget)` — Select Instanced Objects
  - `Duplicate.b000(self)` — Mirror
  - `Duplicate.b005(self)` — Uninstance Selected Objects
  - `Duplicate.b006(self)` — Duplicate Linear
  - `Duplicate.b007(self)` — Duplicate Radial
  - `Duplicate.b008(self)` — Duplicate Grid

<a id="slots--maya--edit"></a>
### `slots/maya/edit.py`

- **[`class Edit(SlotsMaya)`](tentacle/tentacle/slots/maya/edit.py#L11)**
  - `Edit.header_init(self, widget)` — Initialize header menu
  - `Edit.tb000_init(self, widget)` — Initialize Mesh Cleanup
  - `Edit.tb000(self, widget)` — Mesh Cleanup
  - `Edit.tb001_init(self, widget)` — Initialize Delete History
  - `Edit.tb001(self, widget)` — Delete History
  - `Edit.tb002(self, widget)` — Delete Selected
  - `Edit.tb004_init(self, widget)`
  - `Edit.tb004(self, widget)` — Node Locking
  - `Edit.b_channels(self)` — Channels
  - `Edit.b000(self)` — Cut On Axis
  - `Edit.list000_init(self, widget)` — Initialize Create Primitives list.
  - `Edit.list000(self, item)` — Create Primitive
  - `Edit.list001_init(self, widget)` — Initialize Convert list.
  - `Edit.list001(self, item)` — Convert
  - `Edit.b021(self)` — Tranfer Maps
  - `Edit.b022(self)` — Transfer Vertex Order
  - `Edit.b023(self)` — Transfer Attribute Values
  - `Edit.b027(self)` — Shading Sets

<a id="slots--maya--edit_mesh"></a>
### `slots/maya/edit_mesh.py`

- **[`class EditMeshSlots(SlotsMaya)`](tentacle/tentacle/slots/maya/edit_mesh.py#L9)**

<a id="slots--maya--editors"></a>
### `slots/maya/editors.py`

- **[`class Editors(SlotsMaya)`](tentacle/tentacle/slots/maya/editors.py#L9)**
  - `Editors.list000_init(self, widget)` — Initialize the widget with structured data for easier maintenance.
  - `Editors.list000(self, item)`
  - `Editors.b000(self)` — Attributes
  - `Editors.b001(self)` — Outliner
  - `Editors.b002(self)` — Tool
  - `Editors.b003(self)` — Layers
  - `Editors.b004(self)` — Channels
  - `Editors.b005(self)` — Node Editor
  - `Editors.b006(self)` — Dependancy Graph
  - `Editors.b007(self)` — Status Line
  - `Editors.b008(self)` — Shelf
  - `Editors.b009(self)` — Time & Range
  - `Editors.b010(self)` — Script Output
  - `Editors.b011(self)` — Command Line
  - `Editors.b012(self)` — Help Line
  - `Editors.b013(self)` — Tool Box
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

- **[`class StatusMixin`](tentacle/tentacle/slots/maya/hud.py#L13)**
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

- **[`class Lighting(SlotsMaya)`](tentacle/tentacle/slots/maya/lighting.py#L9)**
  - `Lighting.b000(self)` — Launch the HDR Manager.
  - `Lighting.b001(self)` — Launch the Lightmap Baker.

<a id="slots--maya--lighting_shading"></a>
### `slots/maya/lighting_shading.py`

- **[`class LightingShadingSlots(SlotsMaya)`](tentacle/tentacle/slots/maya/lighting_shading.py#L9)**

<a id="slots--maya--main"></a>
### `slots/maya/main.py`

- **[`class Main(SlotsMaya)`](tentacle/tentacle/slots/maya/main.py#L10)**
  - `Main.list000_init(self, widget)` — Initialize Workspace Browser
  - `Main.list000(self, item)` — Workspace Browser

<a id="slots--maya--mash"></a>
### `slots/maya/mash.py`

- **[`class MashSlots(SlotsMaya)`](tentacle/tentacle/slots/maya/mash.py#L9)**

<a id="slots--maya--materials"></a>
### `slots/maya/materials.py`

- **[`class MaterialsSlots(SlotsMaya)`](tentacle/tentacle/slots/maya/materials.py#L12)**
  - `MaterialsSlots.header_init(self, widget)` — Initialize the header menu (Utilities only — Setup/Conversion/External live in the submenu Tools li…
  - `MaterialsSlots.list000_init(self, widget)` — Assign list: scene materials + 'New' + 'Random'.
  - `MaterialsSlots.list000(self, item)` — Dispatch Assign list selection.
  - `MaterialsSlots.list001_init(self, widget)` — Tools list: Setup / Conversion / External (mirrors prior header sections).
  - `MaterialsSlots.list001(self, item)` — Dispatch Tools list selection to the matching slot method.
  - `MaterialsSlots.cmb002_init(self, widget)` — Initialize Materials
  - `MaterialsSlots.lbl007(self)` — Rename the current material by stripping trailing integers and underscores.
  - `MaterialsSlots.lbl007_global(self)` — Rename ALL scene materials by stripping trailing integers and underscores.
  - `MaterialsSlots.tb000_init(self, widget)`
  - `MaterialsSlots.tb000(self, widget)` — Select By Material
  - `MaterialsSlots.lbl002(self)` — Delete Material
  - `MaterialsSlots.b015(self, widget)` — Delete Unused Materials
  - `MaterialsSlots.lbl004(self)` — Select and Show Attributes: Show Material Attributes in the Attribute Editor.
  - `MaterialsSlots.lbl005(self)` — Set the current combo box text as editable.
  - `MaterialsSlots.lbl006(self)` — Open material in editor
  - `MaterialsSlots.b002(self, widget)` — Get Material: Change the index to match the current material selection.
  - `MaterialsSlots.b004(self, widget)` — Assign Random
  - `MaterialsSlots.b005(self, widget)` — Assign Current (main UI button)
  - `MaterialsSlots.b006(self, widget)` — Assign: New Material
  - `MaterialsSlots.b008(self, widget)` — Map Packer
  - `MaterialsSlots.b009(self, widget)` — Create Game Shader
  - `MaterialsSlots.b026(self, widget)` — Arnold Bridge
  - `MaterialsSlots.b010(self, widget)` — Texture Path Editor
  - `MaterialsSlots.b011(self, widget)` — Shader Templates
  - `MaterialsSlots.b013(self)` — Reload Textures and Reset Viewport
  - `MaterialsSlots.b014(self)` — Remove and Reassign Duplicates
  - `MaterialsSlots.b016(self)` — Map Converter
  - `MaterialsSlots.b018(self, widget)` — Material Updater
  - `MaterialsSlots.tb001_init(self, widget)` — Get Material Info — option box.
  - `MaterialsSlots.tb001(self, widget)` — Get Material Info — render a formatted report to the viewer dialog.
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
  - `Normals.b006(self)` — Set To Face
  - `Normals.tb010_init(self, widget)` — Initialize Reverse Normals
  - `Normals.tb010(self, widget)` — Reverse Normals

<a id="slots--maya--nparticles"></a>
### `slots/maya/nparticles.py`

- **[`class NParticlesSlots(SlotsMaya)`](tentacle/tentacle/slots/maya/nparticles.py#L9)**

<a id="slots--maya--nurbs"></a>
### `slots/maya/nurbs.py`

- **[`class Nurbs(SlotsMaya)`](tentacle/tentacle/slots/maya/nurbs.py#L11)**
  - `Nurbs.list000_init(self, widget)` — Initialize Nurbs expandable list (categories → curve actions).
  - `Nurbs.list000(self, item)` — Dispatch a Nurbs leaf action via mel.eval (uses Maya's stored settings).
  - `Nurbs.b056(self)` — Image Tracer
  - `Nurbs.b058(self)` — Curve to Tube
  - `Nurbs.tb000_init(self, widget)`
  - `Nurbs.tb000(self, widget)` — Revolve
  - `Nurbs.tb001_init(self, widget)`
  - `Nurbs.tb001(self, widget)` — Loft
  - `Nurbs.b012(self)` — Project Curve
  - `Nurbs.b014(self)` — Duplicate Curve
  - `Nurbs.b016(self)` — Extract Curve
  - `Nurbs.b018(self)` — Lock Curve
  - `Nurbs.b019(self)` — Unlock Curve
  - `Nurbs.b020(self)` — Bend Curve
  - `Nurbs.b022(self)` — Curl Curve
  - `Nurbs.b024(self)` — Modify Curve Curvature
  - `Nurbs.b026(self)` — Smooth Curve
  - `Nurbs.b028(self)` — Straighten Curve
  - `Nurbs.b030(self)` — Extrude
  - `Nurbs.b036(self)` — Planar
  - `Nurbs.b038(self)` — Insert Isoparm
  - `Nurbs.b040(self)` — Edit Curve Tool
  - `Nurbs.b041(self)` — Attach Curve
  - `Nurbs.b042(self)` — Detach Curve
  - `Nurbs.b043(self)` — Extend Curve
  - `Nurbs.b045(self)` — Cut Curve
  - `Nurbs.b046(self)` — Open/Close Curve
  - `Nurbs.b047(self)` — Insert Knot
  - `Nurbs.b049(self)` — Add Points Tool
  - `Nurbs.b051(self)` — Reverse Curve
  - `Nurbs.b052(self)` — Extend Curve
  - `Nurbs.b054(self)` — Extend On Surface

<a id="slots--maya--pivot"></a>
### `slots/maya/pivot.py`

- **[`class Pivot(SlotsMaya)`](tentacle/tentacle/slots/maya/pivot.py#L9)**
  - `Pivot.tb000_init(self, widget)`
  - `Pivot.tb000(self, widget)` — Reset Pivot
  - `Pivot.tb001_init(self, widget)`
  - `Pivot.tb001(self, widget)` — Center Pivot
  - `Pivot.tb002_init(self, widget)`
  - `Pivot.tb002(self, widget)` — Transfer Pivot
  - `Pivot.tb003_init(self, widget)` — Initialize World-Aligned Pivot options
  - `Pivot.tb003(self, widget)` — World-Aligned Pivot
  - `Pivot.b000(self)` — Center Pivot: Object
  - `Pivot.b001(self)` — Center Pivot: Component
  - `Pivot.b002(self, widget)` — Center Pivot: World
  - `Pivot.b004(self)` — Bake Pivot

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
  - `PolygonsSlots.tb002(self, widget)` — Separate
  - `PolygonsSlots.tb003_init(self, widget)` — Initialize Extrude
  - `PolygonsSlots.tb003(self, widget)` — Extrude
  - `PolygonsSlots.tb004_init(self, widget)` — Initialize Combine
  - `PolygonsSlots.tb004(self, widget)` — Combine Selected Meshes.
  - `PolygonsSlots.tb005_init(self, widget)` — Initialize Detach
  - `PolygonsSlots.tb005(self, widget)` — Detach.
  - `PolygonsSlots.tb006_init(self, widget)` — Initialize Inset Face Region
  - `PolygonsSlots.tb006(self, widget)` — Inset Face Region
  - `PolygonsSlots.tb007_init(self, widget)` — Initialize Divide Facet
  - `PolygonsSlots.tb007(self, widget)` — Divide Facet
  - `PolygonsSlots.tb008_init(self, widget)` — Initialize Boolean Operation
  - `PolygonsSlots.tb008(self, widget)` — Boolean Operation
  - `PolygonsSlots.tb009_init(self, widget)` — Initialize Snap Closest Verts
  - `PolygonsSlots.tb009(self, widget)` — Snap Closest Verts
  - `PolygonsSlots.b000(self)` — Circularize
  - `PolygonsSlots.b001(self)` — Fill Holes
  - `PolygonsSlots.b003(self)` — Symmetrize
  - `PolygonsSlots.b005(self)` — Merge Vertices: Set Distance
  - `PolygonsSlots.b006(self, widget)` — Bridge
  - `PolygonsSlots.b007(self)` — Interactive Bridge
  - `PolygonsSlots.b008(self)` — Weld Center
  - `PolygonsSlots.b009(self)` — Collapse Component
  - `PolygonsSlots.b011(self)` — Bevel
  - `PolygonsSlots.b012(self)` — Multi-Cut Tool
  - `PolygonsSlots.b022(self)` — Attach
  - `PolygonsSlots.b032(self)` — Poke
  - `PolygonsSlots.b034(self)` — Wedge
  - `PolygonsSlots.b038(self)` — Assign Invisible
  - `PolygonsSlots.b043(self)` — Target Weld
  - `PolygonsSlots.b047(self)` — Insert Edgeloop
  - `PolygonsSlots.b049(self)` — Slide Edge Tool
  - `PolygonsSlots.b051(self)` — Offset Edgeloop
  - `PolygonsSlots.b053(self)` — Edit Edge Flow

<a id="slots--maya--preferences"></a>
### `slots/maya/preferences.py`

- **[`class Preferences(SlotsMaya)`](tentacle/tentacle/slots/maya/preferences.py#L15)**
  - `Preferences.cmb001_init(self, widget)` — Initializes the combo box with unit options.
  - `Preferences.cmb001(self, index, widget)` — Set Working Units: Linear
  - `Preferences.cmb002_init(self, widget)` — Initializes the combo box with frame rate options.
  - `Preferences.cmb002(self, index, widget)` — Set Working Units: Time
  - `Preferences.s000_init(self, widget)` — Initialize autosave max backups spinbox (widget is source of truth).
  - `Preferences.s001_init(self, widget)` — Initialize autosave interval spinbox (widget is source of truth).
  - `Preferences.b001(self)` — Color Settings
  - `Preferences.b002(self)` — Autosave: Delete All
  - `Preferences.b008(self)` — Hotkeys
  - `Preferences.b009(self)` — Plug-In Manager
  - `Preferences.b010(self)` — Settings/Preferences

<a id="slots--maya--render"></a>
### `slots/maya/render.py`

- **[`class Render(SlotsMaya)`](tentacle/tentacle/slots/maya/render.py#L9)**

<a id="slots--maya--rendering"></a>
### `slots/maya/rendering.py`

- **[`class Rendering(SlotsMaya)`](tentacle/tentacle/slots/maya/rendering.py#L17)**
  - `Rendering.cmb001_init(self, widget)` — Render: camera
  - `Rendering.tb000_init(self, widget)` — Export Playblast Init
  - `Rendering.tb000(self, widget)` — Export Playblast
  - `Rendering.b000(self)` — Render Current Frame
  - `Rendering.b001(self)` — Open Render Settings Window
  - `Rendering.b002(self)` — Redo Previous Render
  - `Rendering.b003(self)` — Editor: Render Setup
  - `Rendering.b004(self)` — Editor: Rendering Flags

<a id="slots--maya--rigging"></a>
### `slots/maya/rigging.py`

- **[`class Rigging(SlotsMaya)`](tentacle/tentacle/slots/maya/rigging.py#L11)**
  - `Rigging.header_init(self, widget)` — Init Rigging Header
  - `Rigging.cmb001_init(self, widget)` — Init Create
  - `Rigging.cmb001(self, index, widget)` — Create
  - `Rigging.cmb002_init(self, widget)` — Init Quick Rig
  - `Rigging.cmb002(self, index, widget)` — Quick Rig
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

- **[`class SceneSlots(SlotsMaya)`](tentacle/tentacle/slots/maya/scene.py#L15)**
  - `SceneSlots.header_init(self, widget)` — Initialize Header
  - `SceneSlots.txt000(self, widget)` — Workspace Scenes: Filter
  - `SceneSlots.cmb000_init(self, widget)` — Initialize Workspace Scenes
  - `SceneSlots.cmb000(self, index, widget)` — Workspace Scenes
  - `SceneSlots.cmb002_init(self, widget)` — Initialize Autosave
  - `SceneSlots.cmb002(self, index, widget)` — Autosave
  - `SceneSlots.cmb003_init(self, widget)` — Initialize Import
  - `SceneSlots.cmb003(self, index, widget)` — Import
  - `SceneSlots.cmb004_init(self, widget)` — Initialize Export
  - `SceneSlots.cmb004(self, index, widget)` — Export
  - `SceneSlots.cmb005_init(self, widget)` — Initialize Recent Files
  - `SceneSlots.cmb005(self, index: int, widget)` — Recent Files
  - `SceneSlots.tb000_init(self, widget)` — Initialize Set Workspace
  - `SceneSlots.tb000(self, widget)` — Set Workspace
  - `SceneSlots.list000_init(self, widget)` — Initialize Recent Files
  - `SceneSlots.list000(self, item)` — Recent Files
  - `SceneSlots.lbl004(self)` — Open current project root
  - `SceneSlots.lbl005(self)` — Auto Set Workspace
  - `SceneSlots.b000(self)` — Autosave: Open Directory
  - `SceneSlots.b001(self)` — Open Reference Manager
  - `SceneSlots.b002(self)` — Scene Exporter
  - `SceneSlots.tb003_init(self, widget)` — Initialize Export.
  - `SceneSlots.tb003(self, widget)` — Export Scene (FBX + optional GLB) using the configured options.
  - `SceneSlots.b004(self)` — Open Hierarchy Manager
  - `SceneSlots.b005(self)` — Open Naming Tool
  - `SceneSlots.b006(self)` — Scene Cleanup
  - `SceneSlots.b009(self)` — Fix OCIO
  - `SceneSlots.tb001_init(self, widget)` — Get Scene Info — option box.
  - `SceneSlots.tb001(self, widget)` — Get Scene Info — render the audit report to the viewer dialog.
  - `SceneSlots.b011(self)` — Fix Color Spaces
  - `SceneSlots.b012(self)` — Toggle Command Ports
  - `SceneSlots.b007(self)` — Import file
  - `SceneSlots.b008(self)` — Export Selection
  - `SceneSlots.b013(self)` — Mesh Converter (FBX -> GLB)
  - `SceneSlots.b014_init(self, widget)` — Initialize Save to Original Scene.
  - `SceneSlots.b014(self)` — Save to Original Scene.
  - `SceneSlots.b015(self)` — Remove String From Object Names.

<a id="slots--maya--select"></a>
### `slots/maya/select.py`

- **[`class SelectSlots(SlotsMaya)`](tentacle/tentacle/slots/maya/select.py#L9)**

<a id="slots--maya--selection"></a>
### `slots/maya/selection.py`

- **[`class Selection(SlotsMaya)`](tentacle/tentacle/slots/maya/selection.py#L11)**
  - `Selection.list000_init(self, widget)` — Select by Type: Hierarchical type list.
  - `Selection.list000(self, item)` — Select by Type
  - `Selection.cmb001_init(self, widget)` — Reorder Selection Init
  - `Selection.cmb001(self, index, widget)` — Reorder Selection
  - `Selection.cmb003_init(self, widget)`
  - `Selection.cmb003(self, index, widget)` — Convert To
  - `Selection.cmb005_init(self, widget)`
  - `Selection.cmb005(self, index, widget)` — Selection Contraints
  - `Selection.chk000(self, state, widget)` — Select Nth: uncheck other checkboxes
  - `Selection.chk001(self, state, widget)` — Select Nth: uncheck other checkboxes
  - `Selection.chk002(self, state, widget)` — Select Nth: uncheck other checkboxes
  - `Selection.chk005_init(self, widget)` — Create button group for radioboxes chk005, chk006, chk007
  - `Selection.chk005(self, state, widget)` — Select Style: Marquee
  - `Selection.chk006(self, state, widget)` — Select Style: Lasso
  - `Selection.chk007(self, state, widget)` — Select Style: Paint
  - `Selection.lbl003(self, *args)` — Grow Selection
  - `Selection.lbl004(self, *args)` — Shrink Selection
  - `Selection.chk004(self, state, widget)` — Ignore Backfacing (Camera Based Selection)
  - `Selection.chk008(self, state, widget)` — Toggle Soft Selection
  - `Selection.chkxxx(self, **kwargs)` — Transform Constraints: Constraint CheckBoxes
  - `Selection.tb000_init(self, widget)`
  - `Selection.tb000(self, widget)` — Select Nth
  - `Selection.tb001_init(self, widget)`
  - `Selection.tb001(self, widget)` — Select Similar
  - `Selection.tb002_init(self, widget)`
  - `Selection.tb002(self, widget)` — Select Island: Select Polygon Face Island
  - `Selection.tb003_init(self, widget)`
  - `Selection.tb003(self, widget)` — Select Edges By Angle
  - `Selection.b001(self)` — Toggle Selectability
  - `Selection.b016(self)` — Convert Selection To Vertices
  - `Selection.b017(self)` — Convert Selection To Edges
  - `Selection.b018(self)` — Convert Selection To Faces
  - `Selection.b019(self)` — Convert Selection To Edge Ring
  - `Selection.get_selection_tool()` *(static)* — Queries the current selection tool in Maya.
  - `Selection.set_selection_tool(tool)` *(static)* — Sets the selection tool in Maya.

<a id="slots--maya--settings"></a>
### `slots/maya/settings.py`

- **[`class Settings(SlotsMaya)`](tentacle/tentacle/slots/maya/settings.py#L14)**
  - `Settings.header_init(self, widget)` — Initialize header
  - `Settings.tb000(self)` — Update Package
  - `Settings.tb001(self)` — Reload Tentacle package with its dependencies.
  - `Settings.check_for_update(self)` — Check for Tentacle package updates
  - `Settings.b020(self)` — UI Style Editor
  - `Settings.b021(self)` — Hotkey Editor
  - `Settings.b022(self)` — UI Browser
  - `Settings.cmb_bind_default_init(self, widget)` — Default binding (key only).
  - `Settings.cmb_bind_left_init(self, widget)` — Left button binding.
  - `Settings.cmb_bind_middle_init(self, widget)` — Middle button binding.
  - `Settings.cmb_bind_right_init(self, widget)` — Right button binding.
  - `Settings.cmb_bind_left_right_init(self, widget)` — Left+Right button binding.
  - `Settings.kse_activation_key_init(self, widget)` — Initialize activation key sequence editor.
  - `Settings.kse_repeat_last_init(self, widget)` — Initialize repeat last command key sequence editor.
  - `Settings.b_reset_bindings(self)` — Reset bindings to defaults.

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
  - `Subdivision.cmb001(self, index, widget)` — Smooth Proxy
  - `Subdivision.cmb002(self, index, widget)` — Maya Subdivision Operations
  - `Subdivision.s000(self, value: int, widget: object) -> None` — Division Level
  - `Subdivision.s001(self, value: int, widget: object) -> None` — Tesselation Level
  - `Subdivision.b000(self)` — Quadrangulate
  - `Subdivision.b001(self)` — Triangulate
  - `Subdivision.b005(self)` — Reduce
  - `Subdivision.tb000_init(self, widget)` — Initialize Decimate
  - `Subdivision.tb000(self, widget)` — Decimate
  - `Subdivision.b008(self)` — Add Divisions - Subdivide Mesh
  - `Subdivision.b009(self)` — Smooth
  - `Subdivision.b011(self)` — Apply Smooth Preview
  - `Subdivision.b028(self)` — Quad Draw
  - `Subdivision.smoothProxy()` *(static)* — Subdiv Proxy

<a id="slots--maya--surfaces"></a>
### `slots/maya/surfaces.py`

- **[`class SurfacesSlots(SlotsMaya)`](tentacle/tentacle/slots/maya/surfaces.py#L9)**

<a id="slots--maya--symmetry"></a>
### `slots/maya/symmetry.py`

- **[`class Symmetry(SlotsMaya)`](tentacle/tentacle/slots/maya/symmetry.py#L7)**
  - `Symmetry.chk000_init(self, widget)` — Set initial symmetry state
  - `Symmetry.chk000(self, state, widget)` — Symmetry X
  - `Symmetry.chk001(self, state, widget)` — Symmetry Y
  - `Symmetry.chk002(self, state, widget)` — Symmetry Z
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
  - `TransformSlots.cmb002(self, index, widget)` — Align To
  - `TransformSlots.tb000_init(self, widget)` — Drop To Grid Init
  - `TransformSlots.tb000(self, widget)` — Drop To Grid
  - `TransformSlots.tb001_init(self, widget)` — Scale Connected Edges Init
  - `TransformSlots.tb001(self, widget)` — Scale Connected Edges
  - `TransformSlots.tb002_init(self, widget)` — Freeze Transformations Init
  - `TransformSlots.tb002(self, widget)` — Freeze Transformations
  - `TransformSlots.tb003_init(self, widget)` — Constraints Init
  - `TransformSlots.tb004_init(self, widget)` — Snap Init
  - `TransformSlots.tb005_init(self, widget)` — Move To Init
  - `TransformSlots.tb005(self, widget)` — Move To
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
  - `TransformSlots.b001(self)` — Match Scale
  - `TransformSlots.b002(self)` — Un-Freeze Transforms
  - `TransformSlots.setTransformSnap(self, ctx, state)` — Set the transform tool's move, rotate, and scale snap states.

<a id="slots--maya--utilities"></a>
### `slots/maya/utilities.py`

- **[`class Utilities(SlotsMaya)`](tentacle/tentacle/slots/maya/utilities.py#L8)**
  - `Utilities.b000(self)` — Measure
  - `Utilities.b001(self)` — Annotation
  - `Utilities.b002(self)` — Calculator
  - `Utilities.b003(self)` — Grease Pencil

<a id="slots--maya--uv"></a>
### `slots/maya/uv.py`

- **[`class UvSlots(SlotsMaya)`](tentacle/tentacle/slots/maya/uv.py#L12)**
  - `UvSlots.get_map_size(self)` — Get the map size from the combobox as an int.
  - `UvSlots.header_init(self, widget)` — Initialize UV Menu Header
  - `UvSlots.cmb002_init(self, widget)` — Initialize UV Transform Menu
  - `UvSlots.tb000_init(self, widget)` — Initialize UV packing tool interface.
  - `UvSlots.tb000(self, widget)` — Pack UVs with specified settings.
  - `UvSlots.tb001_init(self, widget)` — Initialize Auto Unwrap.
  - `UvSlots.tb001(self, widget)` — Auto Unwrap
  - `UvSlots.tb004_init(self, widget)` — Initialize Unfold UV
  - `UvSlots.tb004(self, widget)` — Unfold
  - `UvSlots.tb005_init(self, widget)` — Initialize Straighten UV
  - `UvSlots.tb005(self, widget)` — Straighten UV
  - `UvSlots.tb006_init(self, widget)` — Initialize Distribute
  - `UvSlots.tb006(self, widget)` — Distribute
  - `UvSlots.tb007_init(self, widget)` — Initialize Cleanup UV Sets
  - `UvSlots.tb007(self, widget)` — Cleanup UV Sets
  - `UvSlots.tb008_init(self, widget)` — Initialize Mirror UVs.
  - `UvSlots.tb008(self, widget)` — Mirror UVs (footprint-preserving by default).
  - `UvSlots.tb009_init(self, widget)` — Initialize Cut Cylinder.
  - `UvSlots.tb009(self, widget)` — Cut Cylinder
  - `UvSlots.cmb002(self, index, widget)` — Transform
  - `UvSlots.b000(self, widget)` — Transfer UV's
  - `UvSlots.b003(self)` — Get texel density.
  - `UvSlots.b004(self)` — Set Texel Density
  - `UvSlots.b005(self)` — Cut UV's
  - `UvSlots.b011(self)` — Sew UVs
  - `UvSlots.b021(self, widget)` — Unfold and Pack UVs
  - `UvSlots.tb022_init(self, widget)` — Initialize Cut Hard Edges option menu.
  - `UvSlots.tb022(self, widget)` — Cut UV hard edges (always), optionally also UV borders and auto-detected seams.
  - `UvSlots.b023(self)` — Move To Uv Space: Left
  - `UvSlots.b024(self)` — Move To Uv Space: Down
  - `UvSlots.b025(self)` — Move To Uv Space: Up
  - `UvSlots.b026(self)` — Move To Uv Space: Right
  - `UvSlots.b029_init(self, widget)` — Initialize Pin/Unpin button — static pin icon, non-checkable.
  - `UvSlots.b029(self, widget)` — Pin / Unpin selected UVs (dual-state toggle).
  - `UvSlots.b030_init(self, widget)` — Initialize Stack button — static stack icon, non-checkable.
  - `UvSlots.b030(self, widget)` — Stack / Unstack similar shells (dual-state toggle).
  - `UvSlots.b031(self)` — Open UV Editor
  - `UvSlots.b032(self)` — RizomUV Bridge

<a id="slots--maya--visualize"></a>
### `slots/maya/visualize.py`

- **[`class VisualizeSlots(SlotsMaya)`](tentacle/tentacle/slots/maya/visualize.py#L9)**

<a id="slots--maya--windows"></a>
### `slots/maya/windows.py`

- **[`class WindowsSlots(SlotsMaya)`](tentacle/tentacle/slots/maya/windows.py#L9)**

<a id="tcl_blender"></a>
### `tcl_blender.py`

Blender entry point for tentacle's Qt marking menu — host + keymap bridge + launcher in one.

- [`ensure_qapp()`](tentacle/tentacle/tcl_blender.py#L164) — Return the process QApplication, creating one if Blender has none.
- [`ensure_blender_widget(app)`](tentacle/tentacle/tcl_blender.py#L172) — Establish ``app.blender_widget`` — the parent for the marking menu.
- [`blender_native_window()`](tentacle/tentacle/tcl_blender.py#L186) — Blender's main GHOST window wrapped as a foreign ``QWindow`` (cached on the QApplication).
- [`start_event_pump(app, interval=0.01)`](tentacle/tentacle/tcl_blender.py#L233) — Pump Qt events from Blender's timer loop so the Qt UI stays responsive (idempotent).
- [`launch(**kwargs)`](tentacle/tentacle/tcl_blender.py#L482) — Stand up the Qt host (QApplication + ``blender_widget`` + event pump) and return a
- [`register()`](tentacle/tentacle/tcl_blender.py#L499) — Blender add-on / startup entry: stand up the host.
- [`unregister()`](tentacle/tentacle/tcl_blender.py#L522) — Blender add-on teardown: remove the keymap items + bridge operator.
- [`diagnose()`](tentacle/tentacle/tcl_blender.py#L527) — Return (and print) the live activation state — run in Blender's Python console to see why
- **[`class TclBlender(MarkingMenu)`](tentacle/tentacle/tcl_blender.py#L389)** — Marking Menu class overridden for use with Blender.
  - `TclBlender.get_main_window(cls)` *(class)* — Blender parent widget for the marking menu (set by :func:`ensure_blender_widget`).
  - `TclBlender.keyPressEvent(self, event)`

<a id="tcl_max"></a>
### `tcl_max.py`

- **[`class TclMax(MarkingMenu)`](tentacle/tentacle/tcl_max.py#L10)** — Marking Menu class overridden for use with Autodesk 3ds Max.
  - `TclMax.get_main_window(cls)` *(class)* — Get the 3DS MAX main window.
  - `TclMax.showEvent(self, event)`
  - `TclMax.hideEvent(self, event)`

<a id="tcl_maya"></a>
### `tcl_maya.py`

- **[`class TclMaya(MarkingMenu)`](tentacle/tentacle/tcl_maya.py#L11)** — Marking Menu class overridden for use with Autodesk Maya.
