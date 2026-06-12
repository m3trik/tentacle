# Blender Feature Gaps (vs the Maya version)

[`DCC_COVERAGE.md`](DCC_COVERAGE.md) measures the **widget-name surface** — a
deferred-with-message stub counts as "handled" there. This doc tracks **feature parity**: every
place the Maya version does something real that the Blender version doesn't, with a difficulty
rating. Work top-down within a tier; flip a row to ✅ (with date) when it ships.

**Difficulty**: S = ≤ half a day · M = 1–2 days · L = multi-day · XL = a project.

---

## 1. In-menu gaps — deferred-with-message stubs in the shared menus

| Where | Feature | Blender path | Diff. | Status |
|:---|:---|:---|:--:|:---|
| subdivision `b028` | Quad Draw (retopo) | `builtin.poly_build` tool (same idiom as knife/loop-cut) | S | ✅ 2026-06-12 |
| crease `b002` | Transfer Crease Edges | native Data-Transfer `CREASE` (active → selected) | S | ✅ 2026-06-12 |
| transform `tb004` (+ shared `chk023`) | Transform Snap (move/scale + Snap Rotate toggle) | `tool_settings.use_snap_translate/scale/rotate` + INCREMENT base (no per-value increment in Blender — grid-based; the Maya increment spinboxes are not mirrored) | S | ✅ 2026-06-12 |
| edit `b000` | Cut On Axis | `mesh.bisect` (axis/position/fill) — needs a `ui/blender_menus/cut_on_axis.ui` panel or an option-box redesign (Maya's is a co-located mayatk panel, §2) | M | open |
| polygons `b034` | Wedge | `mesh.spin` (needs axis/center UX from the selection) | M | open |
| polygons `tb009` | Snap Closest Verts | bmesh nearest-vert pairing + weld between two meshes | M | open |
| polygons `b000` | Circularize | LoopTools **extension** (left the bundled set in 4.2+ — extensions.blender.org); wrap-if-present, message otherwise | M | open |
| polygons `b053` | Edit Edge Flow | same extension story (LoopTools / Edit Mesh Tools) | M | open |
| transform `tb001` | Scale Connected Edges | bmesh connected-edge scaling math | M | open |
| transform `b002` | Un-Freeze Transforms | store originals at freeze time (custom prop), restore on demand | M | open |
| transform `tb003` (+ `chk024/25`) | Transform Constraints (edge/surface) | partially maps to snap-to-edge/face (`snap_elements`); the Maya make-live workflow does not | M | open |
| selection `cmb005` | Selection Constraints (dR_) | mode/tool mapping onto Blender select tools | M | open |
| cameras `tb000` | Align View | region/view matrix math (GUI-only) | M | open |
| settings `tb000` | Package update check | pip/git version probe (DCC-agnostic — consider pythontk) | M | open |
| settings `tb001` | Reload Scripts | `script.reload()` exists but tears down the Qt host — needs a guarded reload that re-registers tentacle | M | open |
| scene `b001` | Reference Manager | library-link (File ▸ Link) manager panel | L | open |
| uv `tb005`/`tb006` | Straighten / Distribute UVs | UV-editor selection+align semantics in bmesh | L | open |
| uv `b030` | Stack/Unstack shells | UV-shell detection + overlap/restore math | L | open |
| selection `cmb001` | Reorder Selection | no object-level ordered selection in Blender (`select_history` is component-only) — questionable value | L | open |
| nurbs `b056` | Image Tracer | SVG import / trace add-on wrap | L | open |

## 2. Co-located tool panels (mayatk `edit_utils` marking-menu panels)

Maya's `duplicate b000/b006/b007/b008` and `edit b000` open separate marking-menu panels whose
`.ui` ships **co-located in mayatk** (`mayatk/edit_utils/mirror.ui`, `duplicate_linear/radial/
grid.ui`) via `MayaUiHandler` discovery. Two Blender routes:

- **(a) tentacle-owned panels** in `ui/blender_menus/` + `slots/blender/<name>.py` — zero new
  infra, the `ui_source` layering already loads `blender_menus/`. **Recommended first.**
- **(b) blendertk co-located panels + a `BlenderUiHandler`** (mirrors MayaUiHandler discovery) —
  the plan's deferred infra; only worth it once blendertk ships several real tool UIs.

| Panel | Blender backing | Diff. | Status |
|:---|:---|:--:|:---|
| Mirror | new `btk.mirror` (bmesh symmetrize / mirror-modifier apply; axis + pivot options — see the mayatk axis-sign memory before porting semantics) | M | open |
| Duplicate Linear | new `btk.duplicate_linear` (pure transform math — headless-testable) | M | open |
| Duplicate Radial | new `btk.duplicate_radial` (rotation about pivot/axis) | M | open |
| Duplicate Grid | new `btk.duplicate_grid` (rows × cols × depth offsets) | M | open |
| Cut On Axis | `mesh.bisect` + fill (shares the §1 edit `b000` row) | M | open |

## 3. mayatk tool windows (real applications behind a button)

| Where | Tool | Note | Diff. |
|:---|:---|:---|:--:|
| display `b013` | Explode View | offset-from-centroid toggle — mostly math | M |
| lighting `b000` | HDR Manager | world-shader HDRI browser/manager | L |
| scene `b005` | Naming (batch rename) | Blender has decent native batch rename (Ctrl+F2); a port is a uitk panel over `bpy` renaming | L |
| scene `b004` | Hierarchy Manager | outliner-grade tree panel | L |
| display `b014` | Color Manager | Blender color management differs structurally | L |
| deformation `b000` | Curtain Generator | cloth-sim setup generator | L |
| rigging `b004` | Render Opacity | unitytk-coupled (FBX custom-prop pipeline) | L |
| rigging `cmb002` | Quick Rig | a thin Rigify wrapper (enable add-on + meta-rig) could be M; HumanIK-parity is XL | M–XL |
| scene `b002` | Scene Exporter | batch/preset FBX pipeline | XL |
| animation `b000`/`b004` | Shot Sequencer / Shot Manifest | timeline binning, markers, audio | XL |
| lighting `b001` | Lightmap Baker | Cycles-bake orchestration (the Maya one was its own project) | XL |

## 4. Not portable as such — do not port

- The **33 `ui/maya_menus/` overlays** (arnold, mash, ncloth, fluids, …) wrap **live Maya native
  menus** via `MayaUiHandler`. Blender's native menus are already native; wrapping them into
  tentacle would be XL with questionable value.
- `texturing` — the Maya slot is a header-only nav stub (no feature content); `modify#submenu`
  is nav-only in both DCCs.

## 5. Closed as not-applicable (messaged in the UI)

Delete History / Node Locking (no construction history), Bake Pivot (origins always baked),
Loft (bridge edge loops instead), Interactive Bridge, Assign Invisible, Slide Edge (modal `GG`),
camera dolly/roll/truck/orbit (modal nav), Render Setup / Rendering Flags (View Layers),
Dependency Graph editor, Status Line / Shelf / Help Line / Tool Box chrome toggles,
RizomUV bridge, command ports / OCIO repair.
