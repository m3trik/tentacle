# Blender Feature Gaps (vs the Maya version)

> ⚠️ **SUPERSEDED 2026-06-15 by [`PARITY_AUDIT.md`](PARITY_AUDIT.md).** This list was assembled
> from the button-coverage view and undercounts the real gaps (missing tool-panels, absent
> blendertk modules, the helper-surface deficit). Use `PARITY_AUDIT.md` as the source of truth for
> "how done is it." Kept for historical S/M/L/XL notes only.

[`DCC_COVERAGE.md`](DCC_COVERAGE.md) measures the **widget-name surface** — a
deferred-with-message stub counts as "handled" there. This doc tracks **feature parity**: every
place the Maya version does something real that the Blender version doesn't, with a difficulty
rating. Work top-down within a tier; flip a row to ✅ (with date) when it ships.

**Difficulty**: S = ≤ half a day · M = 1–2 days · L = multi-day · XL = a project.

---

## 1. In-menu gaps — deferred-with-message stubs in the shared menus — ✅ COMPLETE 2026-06-12 (one row closed N/A)

| Where | Feature | Blender path | Diff. | Status |
|:---|:---|:---|:--:|:---|
| subdivision `b028` | Quad Draw (retopo) | `builtin.poly_build` tool (same idiom as knife/loop-cut) | S | ✅ 2026-06-12 |
| crease `b002` | Transfer Crease Edges | native Data-Transfer `CREASE` (active → selected) | S | ✅ 2026-06-12 |
| transform `tb004` (+ shared `chk023`) | Transform Snap (move/scale + Snap Rotate toggle) | `tool_settings.use_snap_translate/scale/rotate` + INCREMENT base (no per-value increment in Blender — grid-based; the Maya increment spinboxes are not mirrored) | S | ✅ 2026-06-12 |
| edit `b000` | Cut On Axis | `btk.cut_along_axis` (bmesh bisect) behind the §2 `cut_on_axis` panel | M | ✅ 2026-06-12 |
| polygons `b034` | Wedge | `btk.wedge` (bmesh spin about the selected hinge edge, sweep oriented along the face normal, hinge welded) | M | ✅ 2026-06-12 |
| polygons `tb009` | Snap Closest Verts | `btk.snap_closest_verts` (KD-tree; the other selected mesh snaps onto the active) | M | ✅ 2026-06-12 |
| polygons `b000` | Circularize | LoopTools wrap-if-present (`_addon_op` → `looptools_circle`; message points at Get Extensions otherwise) | M | ✅ 2026-06-12 |
| polygons `b053` | Edit Edge Flow | same wrap (`set_edge_flow` — Edit Mesh Tools / Loop Flow) | M | ✅ 2026-06-12 |
| transform `tb001` | Scale Connected Edges | `btk.scale_connected_edges` (per connected set about its own centroid, edit-mode selection) | M | ✅ 2026-06-12 |
| transform `b002` | Un-Freeze Transforms | `btk.freeze_transforms` stamps cumulative `btk_{T,R,S}_bake` custom props; `btk.restore_transforms` composes them back, world position preserved | M | ✅ 2026-06-12 |
| transform `tb003` (+ `chk024/25`) | Transform Constraints (edge/surface) | snap-to-EDGE/FACE during move (`snap_elements`, single-element like Maya); Make Live (`chk026`) is not mirrored | M | ✅ 2026-06-12 |
| selection `cmb005` | Selection Constraints (dR_) | one-shot selection expansion (Angle/Border/Loop/Ring/Shell → native `mesh.*` selects) — Blender has no persistent drag-select constraint | M | ✅ 2026-06-12 |
| cameras `b007` | Align View | native Align-View-to-Active (`view3d.view_axis(align_active=True)` + frame) via `_view3d_context` | M | ✅ 2026-06-12 |
| settings `tb000` | Package update check | `ptk.PackageManager` driven by Blender's bundled python (`sys.executable`) — same flow as the Maya slot | M | ✅ 2026-06-12 |
| settings `tb001` | Reload Scripts | `tcl_blender.reload()` — guarded in-place `ptk.reload_package` (teardown → reload → deferred re-register; the event pump retires via a generation token) | M | ✅ 2026-06-12 |
| scene `b001` | Reference Manager | `blender_menus/reference_manager` panel — lists `bpy.data.libraries` (missing flagged) with Link / Reload / Relocate / Remove / Refresh | L | ✅ 2026-06-12 |
| uv `tb005`/`tb006` | Straighten / Distribute UVs | `btk.straighten_uvs` (near-axis UV edges snap flat, co-located loops move together) / `btk.distribute_uv_shells` (even centers between endpoints) | L | ✅ 2026-06-12 |
| uv `b030` | Stack/Unstack shells | `btk` UV-island detection + `stack_uv_shells` + `get/set_uv_coords` snapshot (dual-state slot toggle) | L | ✅ 2026-06-12 |
| selection `cmb001` | Reorder Selection | ❌ closed N/A 2026-06-12 — no ordered *object* selection in Blender (operators receive an unordered set; `select_history` is component-only); hidden + messaged | L | closed |
| nurbs `b056` | Image Tracer | native wrap: active image-empty → Grease Pencil `trace_image`, otherwise SVG-import-as-curves (`import_curve.svg`) | L | ✅ 2026-06-12 |

## 2. Co-located tool panels (mayatk `edit_utils` marking-menu panels) — ✅ COMPLETE 2026-06-12

Maya's `duplicate b000/b006/b007/b008` and `edit b000` open separate marking-menu panels whose
`.ui` ships **co-located in mayatk** (`mayatk/edit_utils/mirror.ui`, `duplicate_linear/radial/
grid.ui`) via `MayaUiHandler` discovery. Shipped via route **(a)**: tentacle-owned panels in
`ui/blender_menus/` + `slots/blender/<name>.py` (zero new infra — the `ui_source` layering
already loads `blender_menus/`), with live preview via the new **`btk.Preview`**
(snapshot/restore analogue of mayatk's hermetic preview, same slot-facing API). Route (b) —
blendertk co-located panels + a `BlenderUiHandler` — remains deferred until blendertk ships
several real tool UIs. Diverging combos took fresh objectNames (cross-DCC state rule).

| Panel | Blender backing | Diff. | Status |
|:---|:---|:--:|:---|
| Mirror | `btk.mirror` (bmesh duplicate+reflect; OFF/Combine/Border-weld merge modes; object/world/bbox pivots; bbox-center routes through `cut_along_axis` symmetrize like the Maya slot) | M | ✅ 2026-06-12 |
| Duplicate Linear | `btk.duplicate_linear` (matrix math over shared `ptk.ProgressionCurves`) | M | ✅ 2026-06-12 |
| Duplicate Radial | `btk.duplicate_radial` (matrix orbit about pivot/axis; Empty grouping; combine) | M | ✅ 2026-06-12 |
| Duplicate Grid | `btk.duplicate_grid` (bbox+spacing steps; instance/copy/combine; cap-guarded) | M | ✅ 2026-06-12 |
| Cut On Axis | `btk.cut_along_axis` (bmesh bisect + delete side + mirror/symmetrize; shares the §1 edit `b000` row) | M | ✅ 2026-06-12 |

## 3. mayatk tool windows (real applications behind a button)

| Where | Tool | Note | Diff. |
|:---|:---|:---|:--:|
| utilities `b002` | Calculator | ✅ 2026-06-13 — `blendertk/ui_utils/calculator` co-located panel. DCC-agnostic engine (safe expression eval + length-unit conversion) extracted to shared `ptk.MathUtils.eval_expression`/`convert_length_unit` (Maya panel delegates too — one SSoT); Blender-specific FPS/time helpers (`scene.render.fps`/`frame_current`). **Surfaced by the 2026-06-13 side-by-side audit as a silent dead-end** — the button called `show("calculator")` but the panel shipped only in mayatk. | M |
| display `b013` | Explode View | ✅ 2026-06-12 — `btk.explode_view` toggle (bbox-driven separation, exact restore via stamped origins; the Maya slider window is not mirrored) | M |
| lighting `b000` | HDR Manager | ✅ 2026-06-12 — `blender_menus/hdr_manager` panel over `btk.set_world_hdri` (world Environment-Texture rig; folder-scanned map combo, intensity×2^exposure, Z rotation, visible→`film_transparent`); Arnold-only advanced fields not mirrored | L |
| scene `b005` | Naming (batch rename) | ✅ 2026-06-12 — invokes Blender's **native** Batch Rename (the don't-reinvent answer; full mayatk Naming-panel parity not mirrored) | L |
| scene `b004` | Hierarchy Manager | ✅ 2026-06-12 — opens Blender's **native Outliner** in a new window (don't-reinvent; the mayatk diff/pull workflow is Maya-specific and not mirrored) | L |
| display `b014` | Color Manager | ✅ 2026-06-12 — `blendertk/display_utils/color_manager` co-located panel over `btk.ColorManager` (swatch palette → apply/select-by/reset across **material** ID, **object color** (`obj.color`), and **vertex** color attribute; Maya's separate outliner + wireframe tints collapse to Blender's single `obj.color`) | L |
| deformation `tb001` | Curtain Generator | ✅ 2026-06-12 — `blender_menus/curtain` panel over the **shared `ptk.CurtainDrape` engine** (extracted from mayatk same day; identical params drape identically) + `btk.create_curtain` bmesh build; presets + the Maya wire rig not mirrored | L |
| rigging `b004` | Render Opacity | unitytk-coupled: animated opacity custom-prop + visibility dual-keys consumed by `RenderOpacityImporter` — needs Blender's animated-custom-prop FBX export verified against that importer (Unity readback untestable on dev machines) | L |
| rigging `cmb002` | Quick Rig | ✅ 2026-06-12 — thin Rigify wrapper (enable add-on → Human/Basic meta-rig → `rigify_generate` on the active meta-rig); HumanIK-parity remains out of scope (XL) | M–XL |
| lighting `b001` | Lightmap Baker | ✅ 2026-06-13 — `blendertk/light_utils/lightmap_baker` panel (`show("lightmap_baker")`): native Cycles bake (lighting-only `DIFFUSE` no-color = white-card irradiance; fused `COMBINED`), native `bake.margin` seams, non-destructive commit/revert, Unity bridge on a `data_export` Empty | XL |
| scene `b002` | Scene Exporter | batch/preset FBX pipeline — **still open** (XL) | XL |
| animation `b000`/`b004` | Shot Sequencer / Shot Manifest | timeline binning, markers, audio — **still open** (XL) | XL |

## 3b. Method-level transfers / pivots (edit + pivot menus)

Maya slot methods that aren't separate tool windows — filled in place (or deferred with a note).

| Where | Feature | Blender path | Diff. | Status |
|:---|:---|:---|:--:|:---|
| edit `b023` | Transfer Attribute Values | native **Data Transfer** (`object.data_transfer`, active → selected; invoked interactively so its redo panel exposes the per-layer choice) | S | ✅ 2026-06-12 |
| edit `b027` | Shading Sets | native `object.material_slot_copy` (active mesh's material slots/shading → the other selected) | S | ✅ 2026-06-12 |
| pivot `tb002` | Transfer Pivot | `btk.transfer_pivot` — the active object's origin location is transferred onto the other selected objects' origins (3D-cursor → ORIGIN_CURSOR, geometry preserved); only Maya's *translate* pivot maps (Blender's origin is a single point) | S | ✅ 2026-06-12 |
| edit `b021` | Transfer Maps | Cycles selected-to-active **bake** (render-engine + UV + image-target setup) — deferred as its own task; messaged to use Render Properties ▸ Bake meanwhile | L | deferred |
| edit `b022` | Transfer Vertex Order | no Blender built-in (and no in-place vertex reindex) — deferred | M | deferred |
| pivot `tb003` | World-Aligned Pivot | Maya manipulator-pivot orientation — Blender has no separate manip pivot (origin is a point) → not applicable | — | N/A |
| rigging `tb001` | Constraint Switch | a switch attribute blending/snapping between constraint targets; Blender constraints differ structurally (native per-constraint `influence` + drivers cover the manual case) — deferred | M–L | deferred |
| rigging `b004` | Render Opacity | pipeline-blocked — half of a Maya→FBX→Unity flow (animated opacity custom-prop + visibility dual-keys read back by unitytk's `RenderOpacityImporter`, untestable on dev machines) — deferred | L | deferred |

## 3c. mayatk tool panels exposed via Maya-slot **dynamic** menus / **repurposed** combos

The earlier audit (and `DCC_COVERAGE.md`) measured the **shared static `ui/*.ui` widget surface**.
But several mayatk tools are reached through buttons the **Maya slot builds at runtime** (`header_init`
`widget.menu.add(...)`) or through a **combo whose Blender version was repurposed** — so they never
appear in the shared `.ui` and were invisible to that audit. **None dead-end in Blender** (the Blender
slot simply never builds the button — unlike the calculator, which *was* a live `show()` with no panel
and is now fixed); they are **absent features**. The full mayatk co-located tool set is 42 panels; the
ones with no Blender equivalent and no prior row here:

| mayatk tool | Maya exposure | Blender status today | Diff. |
|:---|:---|:---|:--:|
| `channels` (node_utils/attributes) | edit `header_init` "Channels" button | ✅ 2026-06-13 — edit `b_channels` opens the native **Properties** editor (transform channels + custom properties) via `btk.open_editor("Properties")`, the don't-reinvent analogue; mayatk's full attribute-**table** editor (lock/keyable/mute/break-conn/create-attr) is not mirrored | M |
| `image_to_plane` (mat_utils) | materials `header_init` "Image to Plane" | ✅ 2026-06-13 — materials `b021` → native **Import Images as Planes** (`import_image.to_plane` via `invoke_op`) | S |
| `texture_path_editor` (mat_utils) | materials `header_init` "Find Missing Textures" | ✅ 2026-06-13 — **full co-located blendertk panel** (`mat_utils/texture_path_editor`, `b010` → `show("texture_path_editor")`): list every file texture (missing flagged), repath, resolve-missing-by-folder, normalize (relative/absolute/copy-into-project) over new `MatUtils` engine fns. Supersedes the earlier native-`find_missing_files` stub | M |
| `mat_updater` (mat_utils) | materials dynamic btn | ✅ 2026-06-13 — co-located blendertk panel (`mat_utils/mat_updater`, `b018`): batch-reprocess material textures via the SHARED `ptk.MapFactory` (convert/resize/optimize) + repath image nodes (fallback-aware). Pillow provisioned on demand by `btk.ensure_image_deps`. ORM/MSAO shader-rewire intentionally not mirrored (Blender's Principled uses separate channels) | M |
| `game_shader` (mat_utils) | materials dynamic btn | ✅ 2026-06-13 — co-located blendertk panel (`mat_utils/game_shader`, `b009`) over `btk.create_pbr_material`: classify a PBR texture set (shared `MapFactory`) → wired Principled BSDF (Base Color, Metallic, Roughness/glossiness-invert, Normal + DirectX green-flip, AO multiply, Emission, Alpha, packed ORM split, Bump/Height, Displacement). No image lib needed | M–L |
| `shader_templates` (mat_utils) | materials dynamic btn | ✅ 2026-06-13 — co-located blendertk panel (`mat_utils/shader_templates`, `b011`): Principled-BSDF *parameter* presets (Metal/Glass/Emission/Skin…) create-new / apply-to-selected. Distinct from `game_shader` (textures) | L |
| `substance_bridge` (mat_utils) | materials dynamic btn | ✅ 2026-06-13 — materials `b020` **bridge**: export selection → FBX (`btk.export_selection_fbx`) → launch the DCC-agnostic **extapps `substance_workflow`** with the mesh pre-filled (`set_mesh_path`). "Reuse extapps" approach | L |
| `marmoset_bridge` (mat_utils) | materials dynamic btn | ✅ 2026-06-13 — materials `b019` **bridge**: export selection → FBX → launch **extapps `marmoset_workflow`** pre-filled (`set_model_path`) | L |
| `wheel_rig` / `tube_rig` / `telescope_rig` / `shadow_rig` (rig_utils) | rigging `cmb002` (combo, **repurposed to Quick Rig/Rigify** in Blender) | absent — 4 procedural rig generators dropped when `cmb002` became Quick Rig | M each |

Standalone mayatk tools **not exposed through any tentacle slot** (shelf/menu-launched only — out of
tentacle parity scope): `blendshape_animator`, `audio_clips`, `shots`, `workspace_map`, `dynamic_pipe`.

`rizom_bridge` (RizomUV) — ✅ 2026-06-13: focused bundled blendertk bridge (`uv_utils/rizom_bridge`, uv `b032` + uv-header `btn_rizom_bridge`): discover the RizomUV exe → export selection → Lua `ZomLoad` script → launch detached (`-cfi`). The Maya UV *round-trip* is not mirrored (Blender's native UV tools cover it).
N/A bridges (renderer-specific, not portable): `arnold_bridge` (Arnold — a parallel `aiStandardSurface` *preview* shader for in-Maya Arnold rendering, not an external-app bridge; renamed "Arnold Preview Shader").

Native-covered (no panel needed, already wired the Blender-idiomatic way):
`bridge`→`mesh.bridge_edge_loops`, `curve_to_tube`→nurbs `b058`, `exploded_view`→`btk.explode_view`,
`image_tracer`→native wrap, `naming`→native Batch Rename, `hierarchy_manager`→native Outliner,
`snap`→transform `tb004` Transform Snap.

Faithful-panel parity (upgraded past the native-substitute decision):
- `bevel` — ✅ 2026-06-15 — **full co-located blendertk panel** (`edit_utils/bevel`, polygons `b011` →
  `show("bevel")`) over new `btk.Bevel` (native `bmesh.ops.bevel` on the Edit-Mode selection),
  mirroring Maya's bevel window (Width / Segments / Profile / Clamp Overlap + live `btk.Preview`).
  Supersedes the earlier `b011`→`mesh.bevel(offset=0.1)` one-shot. The remaining "native-covered"
  rows above are candidates for the same upgrade if panel-for-panel parity is wanted.

## 4. Not portable as such — do not port

- The **33 `ui/maya_menus/` overlays** (arnold, mash, ncloth, fluids, …) wrap **live Maya native
  menus** via `MayaUiHandler` — harvesting `QAction`s out of Maya's Qt menu bar, only possible
  because Maya's UI *is* Qt. Blender draws its UI in OpenGL, so there are no `QMenu`/`QAction`
  objects to harvest; these specific Qt-wrapped overlays stay Maya-only.
  **But the both-button feature itself IS ported** (2026-06-12, the Blender-idiomatic way):
  `F12 + L + R` → `blender#startmenu`, a Qt radial whose wedges pop Blender's **own** native menus
  at the cursor via `btk.call_native_menu` (`wm.call_menu`) — always accurate + add-on/mode-aware,
  zero content maintenance. See the tentacle CHANGELOG.
- `texturing` — the Maya slot is a header-only nav stub (no feature content); `modify#submenu`
  is nav-only in both DCCs.

## 5. Closed as not-applicable (messaged in the UI)

Delete History / Node Locking (no construction history), Bake Pivot (origins always baked),
Loft (bridge edge loops instead), Interactive Bridge, Assign Invisible, Slide Edge (modal `GG`),
camera dolly/roll/truck/orbit (modal nav), Render Setup / Rendering Flags (View Layers),
Dependency Graph editor, Status Line / Shelf / Help Line / Tool Box chrome toggles,
command ports / OCIO repair, Reorder Selection (no ordered object selection).
