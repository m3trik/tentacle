# tentacle / blendertk — Maya↔Blender Porting Plan

> **Hand-maintained companion to the auto-generated [`PARITY_AUDIT.md`](PARITY_AUDIT.md).**
> The audit *measures* the gap (reproducible, never edit by hand). **This doc is the actionable
> recipe for closing it** — what each missing/thin panel does, how it maps to Blender, the
> divergence decisions, effort, dependencies, and menu wiring. A second pass should be able to
> pick up any task **without re-reading the mayatk source to figure out scope** — that is the bar.
> If a task here is missing the Blender mapping or the divergence call, treat the entry as
> incomplete and fix it *before* coding (insufficient specs caused three wasted audits).

**Status legend:** ✅ done · 🔨 in progress · ⬜ pending
**Effort:** **S** ≤~250 src ln · **M** ~250–800 · **L** ~800–1500 · **XL** ~1500–4000 · **XXL** >4000
(src ln = mayatk engine+slots, excludes generated `*_ui.py`; a faithful Blender port is usually 30–70% of that.)

## How to port a panel (the established pattern)

Proven end-to-end on `telescope_rig` / `wheel_rig` (see those files as the reference template):

1. **Engine + Slots co-located** in a `blendertk/blendertk/<module>/<tool>.py` (single file) or
   `<module>/<tool>/` package (mirrors mayatk's split when the Maya tool is a package).
   - Engine class `Foo(ptk.LoggingMixin)` — **no Qt import at module top**; `import bpy` deferred
     into method bodies (no-import-side-effects rule). Logic must be unit-testable headless.
   - Slots class `FooSlots(ptk.LoggingMixin)` — widget-named methods (`b000`, `tb000`, `cmb000_init`).
     Defer the `uitk` tooltip import into `header_init`.
2. **`.ui`** — copy mayatk's `<tool>.ui` verbatim when it's DCC-neutral (most are); hide vestigial
   widgets via `setVisible(False)` in `__init__` (don't `deleteLater` — runtime loader invalidates
   deleted wrappers). The `.ui` is the *contract*; the slot file implements every objectName in it.
3. **Register** in `blendertk/blendertk/__init__.py` `DEFAULT_INCLUDE` (engine class only; the
   `*Slots` are discovered by `BlenderUiHandler`, NOT listed in `DEFAULT_INCLUDE`, NOT compiled).
4. **Menu wiring** — add a button/combo entry in the matching `tentacle/tentacle/slots/blender/
   <domain>.py` that calls `marking_menu.show("<tool>")`. Mirror the Maya slot's wiring.
5. **Test** — headless `blendertk/test/test_<tool>.py` run via fresh Blender
   (`blender --background --factory-startup --python ...`). Slots-logic tests stub `ui`/`sb`.
   Add the tool to `test_blender_ui_handler.py`'s `PANELS` list.

**Driver gotcha (rigs):** script-built drivers cache a stale compile. Build ALL variables before
the expression, then call `RigUtils.refresh_drivers(objs)` as the LAST op, and decorate the build
with `@undo_checkpoint` (pushes undo BEFORE the body). See
`memory/reference_blender_script_built_driver_gotcha.md`.

**Session safety (HARD RULE):** never test against a running Blender. Always `--factory-startup`
fresh instance. Forbidden: `--reuse`, attaching to a live session.

---

## Tier A — Low-hanging fruit (faithful, headless-testable, do first)

### ShadowRig — L ✅ SHIPPED 2026-06-16 (test_shadow_rig 34/34, handler 111/111)
- **Built:** `blendertk/rig_utils/shadow_rig.py` (`ShadowRig` engine + `ShadowRigSlots` + co-located
  `shadow_rig.ui`), registered in `DEFAULT_INCLUDE`, wired into the blender rigging `cmb002` Quick Rig
  (`"Shadow Rig"` → `marking_menu.show("shadow_rig")`). Both modes (`stretch` default + `orbit`) are
  full **driver** ports of the Maya MEL expressions, **remapped Y-up→Z-up** (ground = XY, plane
  rotates about **Z**). One driver per channel via the shared `RigUtils` (gained `add_transform_var`,
  the multi-input companion to `add_prop_var`), each reading the light + contact WORLD position
  (`TRANSFORMS` vars) + the plane's keyable props (`SINGLE_PROP`). Expressions are **branchless**
  (`min`/`max`/`sqrt`/`atan2`/`pow`) so they stay on Blender's fast driver parser; the two Maya
  branches (pivot sign, scaleInfluence gate) are `abs`-sign / clamped-`max` (exact for the default
  `scaleInfluence=0`; bounded harmless divergence only in a degenerate pose — documented inline).
  Unlit material = black **Emission** mixed with a **Transparent BSDF** by `tex.alpha × opacity`
  (opacity a driven Value node). Silhouette via the shared `ImgUtils.rasterize_silhouette` (Y/Z
  column swap presents Blender-Z as its "up"), persisted to PNG via `bpy.data.images` (no cv2/PIL).
- **Foundation fix (pythontk):** `rasterize_silhouette` claimed "PIL-free" but its default blur went
  through `_gaussian_blur_array` → PIL → crashed under Blender's PIL-less Python. Added a pure-numpy
  separable-Gaussian fallback (`_gaussian_blur_array_numpy`, used when `Image is None`) so the
  contract holds; tests pin it (PIL-path parity + RGBA channel-restrict + end-to-end PIL-free
  rasterize). pythontk img tests 10/10 for the cluster.
- **Verified (headless, structural — visual not asserted, per below):** stretch evaluates to the
  hand-derived scale 1.5 / loc −0.55 / opacity 0.6147; orbit rotates −135° about Z; lowering the
  source grows the stretch; rebuild doesn't stack drivers; empty-target guard.
- **Divergence:** Maya bakes the expression to keys for FBX; Blender leaves the drivers live (bake
  via Bake Action when needed). StingrayPBS → Emission/Transparent unlit. Y-up→Z-up throughout.
- **Re-scoping note (historical):** the silhouette rasterizer foundation was done first, then the bulk —
  translating mayatk's two ~80-line MEL **expressions** (`_expr_orbit` / `_expr_stretch`) into
  Blender **drivers** — one per driven channel (plane translateX/Y/Z, rotateZ, scaleX/Y, material
  opacity), each an inlined expression reading the light + contact world positions via `TRANSFORMS`
  vars, with `atan2`/`sqrt`/`clamp`/conditionals. That's the hard 80%, error-prone, and *visually*
  unverifiable headless (only the driver/material/texture *structure* is assertable, like the other
  rigs). **Do it as a dedicated focused pass, not squeezed in** — give the driver math its own
  attention. Use telescope/wheel as the driver template + the `refresh_drivers`/`@undo_checkpoint`
  gotcha. Conditionals (`a if c else b`) force Blender's slow full-Python driver parser — prefer
  branchless arithmetic where possible (as `wheel_rig` does).
- **mayatk:** `rig_utils/shadow_rig.py` (1000 ln). Foundation **already extracted**:
  `pythontk.ImgUtils.rasterize_silhouette` (+ `_fill_triangle`, `_contact_falloff`), 6/6 tests.
- **Purpose:** projected-shadow rig for engine export — a quad plane with the object's silhouette
  baked to a PNG, plane transform driven to follow a light/orbit so it reads as a contact/cast
  shadow. Two modes: `"orbit"` (plane rotates to face away from source) and `"stretch"` (axis-aligned,
  scale+translate warp; bake-friendly, default).
- **Key API to port:** `create_contact_locator`, `get_or_create_shadow_source`, `create_shadow_plane`
  (custom attrs `shadowIntensity`/`falloffPower`/`scaleInfluence`/`basePlaneSize`),
  `create_silhouette_texture` (→ now `ImgUtils.rasterize_silhouette`), `create_material` (stingray →
  **unlit transparent**: Emission + alpha, EEVEE blend `HASHED`/`BLEND`), `setup_expression`
  (`_expr_orbit`/`_expr_stretch`), classmethod `create`.
- **Blender mapping:** plane mesh + image texture node (PNG written via `bpy.data.images` /
  `image.save_render`); silhouette from `rasterize_silhouette` fed mesh tris extracted from the
  evaluated depsgraph. Maya expression → **drivers** on the plane's loc/rot/scale (use `RigUtils`),
  refreshed via `refresh_drivers`. Unlit material = Emission shader + alpha, `blend_method`.
- **Divergence:** Maya bakes the expression to keys for FBX; Blender can bake drivers via
  `bpy.ops.nla.bake` or leave live. Stingray PBS → Principled/Emission unlit.
- **Deps:** `ImgUtils.rasterize_silhouette` (done), `RigUtils` (done).
- **Menu wiring:** rigging `cmb002` Quick Rig → add `"Shadow Rig"` → `marking_menu.show("shadow_rig")`.
- **Tests:** headless — extract tris from a cube, rasterize, assert plane+material+drivers created,
  re-run idempotent. Material visual is not asserted (offscreen).

### Bridge — S ✅ (shipped 2026-06-16, test_bridge 15/15)
- **Built:** `blendertk/edit_utils/bridge.py` (`Bridge` + `BridgeSlots`, `bmesh.ops.bridge_loops`,
  divisions→subdivide, Preview snapshot/rollback). Wired: blender `polygons.py` `b007`. Vestigial
  widgets (cmb000/s001/s003/s004/chk001) hidden — no `bmesh` analogue (documented in module).
- **mayatk:** `edit_utils/bridge.py` (259 ln). `Bridge.bridge(edges, **kwargs)` — bridge open edge
  loops grouped per owning mesh; on failure raises `OperationError` with a human-readable reason.
- **Blender mapping:** native `bpy.ops.mesh.bridge_edge_loops()` (edit mode, operates on selected
  edges). Blender's op is *richer* (twist, number_cuts, interpolation, smoothness, profile_factor)
  — expose those rather than Maya's narrower set (extend, don't shrink).
- **Divergence:** minimal. Maya groups multi-mesh selections; in Blender the op runs per edit-mode
  mesh, so iterate selected mesh objects. Keep the friendly error wrapper (catch `RuntimeError`).
- **Menu wiring:** `edit` menu (mirror Maya's edit slot button that calls `Bridge`).
- **Tests:** headless — make a tube with two open loops, select boundary edges, bridge, assert face
  count increased and mesh closed. Pairs with the shared `edit.py` slot.

### ExplodedView — S/M ✅ (shipped 2026-06-16, test_wedge_snap_explode 25/25)
- **Built:** `blendertk/display_utils/exploded_view.py` (`ExplodedViewSlots` b000–b003). Engine
  already existed in `_display_utils` (`explode_view`/`unexplode_view`/`is_exploded`); added
  `unexplode_all` for Maya's b002 parity. Wired: blender `display.py` `b013` → panel (was inline
  toggle). `.ui` copied verbatim.
- **mayatk:** `display_utils/exploded_view.py` (291 ln). Offsets objects outward from a shared
  center by a scalar factor; stores originals in a class dict to restore; supports per-object
  direction from bbox-center delta.
- **Blender mapping:** pure transform math on `obj.location` / `matrix_world` — directly portable.
  Store original world matrices in a class dict keyed by object (like Maya's `exploded_objects`).
- **Divergence:** none of substance. Use `xform_utils` bbox-center helpers (check blendertk has
  them; `get_bounding_box`-equivalent).
- **Menu wiring:** `display` menu.
- **Tests:** headless — 3 cubes at known offsets, explode factor=2, assert each moved along its
  center→object vector by the expected amount; restore returns to original. Fully deterministic.

### Snap — M ✅ (shipped 2026-06-16, test_snap 18/18, handler 75/75)
- **Built:** `blendertk/edit_utils/snap.py` (`SnapSlots` — b000 Surface / b001 Closest-Vertex /
  b002 Grid, with option boxes). Added engines `snap_to_grid` (object origin + edit-mode verts,
  axis filter) and `snap_to_surface` (`Object.closest_point_on_mesh`, signed-distance push-out)
  to `_edit_utils`; `snap_closest_verts` already existed. Wired blender transform `b_snap_ts`
  ("Snap") → panel — this **fixed a cross-DCC objectName semantic divergence** (Maya's `b_snap_ts`
  opens the snap panel; Blender's had been repurposed to a transform-snapping toggle). Selection:
  active object = target (Maya's last-ordered). `.ui` copied verbatim.
- **mayatk:** `edit_utils/snap.py` (400 ln). `snap_to_closest_vertex(obj1, obj2, tolerance, ...)`,
  snap-to-grid, snap object/component to nearest vertex.
- **Blender mapping:** `mathutils.kdtree.KDTree` over target verts (world space) for nearest lookup;
  move source verts/object within tolerance. Snap-to-grid = round loc/verts to increment.
- **Divergence:** Maya `freeze_transforms` → `bpy.ops.object.transform_apply`. Component vs object
  mode via `obj.mode`/edit-mesh `BMesh`.
- **Menu wiring:** `edit` or a dedicated Snap panel button (mirror Maya).
- **Tests:** headless — two offset planes, snap closest within tolerance, assert moved verts
  coincide; outside tolerance → unchanged.

### Naming — M ✅ (shipped 2026-06-16, test_naming 25/25, handler 83/83)
- **Built:** `blendertk/edit_utils/naming/` (package: `Naming` engine + `NamingSlots` + `.ui`).
  All 6 ops: Find / Rename / Convert Case / Strip Chars / Suffix by Location / Suffix by Type, each
  with option boxes + a Scope header combo. Reuses the shared `pythontk` string layer
  (`find_str_and_format`/`find_str`/`format_suffix`); `cmds.rename`→`obj.name`. Wired blender scene
  `b005` → panel (**replaced the native Batch Rename op**). Divergences: Blender type map for
  suffix-by-type (EMPTY→_GRP w/children else _LOC, ARMATURE→_JNT, no _LYR); `append_location_based_suffix`
  calls `view_layer.update()` before distance ordering (stale-matrix_world gotcha).
- **mayatk:** `edit_utils/naming/` (1087 ln). `Naming.rename` (+ prefix/suffix, search-replace,
  auto-number/padding, strip, case, find-duplicates). Pure string + `cmds.rename`.
- **Blender mapping:** `obj.name = ...` (and `obj.data.name`). Reuse `pythontk` string helpers if
  any exist (check `ptk` registry — do NOT duplicate). Auto-number/padding logic is DCC-neutral →
  could live in `pythontk` if mayatk's isn't already shared.
- **Divergence:** Blender auto-appends `.001` on name collision (Maya errors / uses `|` paths).
  Handle collisions explicitly. No DAG path uniqueness; names are globally unique per data-block.
- **Menu wiring:** `edit`/`scene` menu; Maya exposes it as a panel (`naming.ui`).
- **Tests:** headless — rename batch with padding, search-replace, prefix; assert resulting names.
  Mostly string logic → very testable.

### ImageToPlane — M ✅ (shipped 2026-06-16, test_image_to_plane 22/22, handler 79/79)
- **Built:** `blendertk/mat_utils/image_to_plane/` (package: `ImageToPlane` engine + `ImageToPlaneSlots`
  + `.ui`). Plane-per-image sized to aspect (upright XZ quad), Principled material with image→Base
  Color (+Alpha when RGBA), batch list / affix naming / grouping / remove. Wired blender materials
  `b021` → panel (**replaced the reduced-scope native `import_image.to_plane` op**). Divergences:
  `mat_type` always Principled (Blender's only shader); affix-mode menu simplified to inline auto
  resolution; `remove` also purges the orphaned mesh datablock (else material/image leak).
- **mayatk:** `mat_utils/image_to_plane/` (592 ln). Plane per image, sized to source aspect, fully
  wired material (Stingray PBS or standardSurface). Batch-capable, class-level methods.
- **Blender mapping:** create plane mesh, scale X/Y to image aspect (read via
  `bpy.data.images.load`), Principled BSDF + Image Texture node (or Emission for unlit). Native
  `bpy.ops.import_image.to_plane` exists (Images-as-Planes addon) but is **not guaranteed enabled**
  → build manually for robustness; optionally fast-path the addon if present.
- **Divergence:** material model (Stingray → Principled). Color-space: set image `colorspace_settings`
  to sRGB for albedo (mirrors the Toolbag sRGB lesson in memory).
- **Menu wiring:** `materials` menu.
- **Tests:** headless — load a tiny test PNG, build plane, assert plane dims match aspect and a
  material with an image node exists.

---

## Tier B — Medium (near-term, more divergence)

### DynamicPipe — M ✅ (shipped 2026-06-16)
- **mayatk:** `edit_utils/dynamic_pipe.py` (198 ln). Chain of locators each driving a NURBS circle;
  loft surface follows when locators move; optional interpolated in-between locators.
- **blendertk:** `edit_utils/dynamic_pipe.py` (engine `DynamicPipe` + co-located `DynamicPipeSlots`
  + `dynamic_pipe.ui`). Engine registered in `DEFAULT_INCLUDE`; Slots discovered by
  `BlenderUiHandler` (`marking_menu.show("dynamic_pipe")`).
- **Decision taken:** **hook-driven curve + bevel** (the recommended option — closest to Maya's
  "locators drive it live", no geometry-nodes dependency). Realized mapping:
  - One NURBS curve built **at the world origin** (identity matrix → clean hook bind), one control
    point per handle. `order_u = min(4, npts)` (degree-3 where ≥4 points, else linear — mirrors
    Maya's degree fallback); `use_endpoint_u = True` (passes through first/last handle).
  - **`bevel_depth` = radius** gives the round cross-section, folding Maya's per-locator NURBS
    circle into the curve. `bevel_resolution` = profile smoothness. `use_fill_caps = False` (open
    tube, like Maya's open loft).
  - One **Hook modifier** per handle (`falloff_type='NONE'`, `vertex_indices_set([i])`), bound so
    geometry doesn't jump: the hook deform is `mat = ob.world_to_object @ target.object_to_world @
    matrix_inverse`; for `mat = I` at bind time, `matrix_inverse = target.world_to_object @
    ob.object_to_world`, which (curve at origin) reduces to `target.matrix_world.inverted()`.
  - In-between locators → interpolated **Empties** (`spaceLocator` → Empty), each hooked too.
- **Divergences (documented):**
  - **No `create_pipe_geometry` / per-segment loft** — Maya's two-phase build (init then loft)
    collapses to one step; the curve built in `__init__` *is* the whole pipe.
  - **Name-ordered selection** — Blender has no `ls(orderedSelection=True)`, so the Slots sort the
    selected handles by name (user controls the chain via `handle_01`, `handle_02`, …).
  - **GOTCHA applied:** `matrix_world` is lazy → the engine calls `view_layer.update()` *before*
    reading handle positions and again after creating in-between Empties (else handles read at the
    origin; the original draft only passed because a stale-identity `matrix_inverse` cancelled the
    stale position — two bugs masking each other).
- **Menu wiring:** **none** (handler/shelf-launched only). Maya does **not** expose `dynamic_pipe`
  through any tentacle slot (BLENDER_FEATURE_GAPS.md lists it shelf-launched, out of tentacle parity
  scope) — adding a Blender nav button would be a *divergence*, not parity. Both DCCs reach it the
  same way: the handler (`*UiHandler.instance().get("dynamic_pipe")` / `marking_menu.show`).
- **Tests:** `blendertk/test/test_dynamic_pipe.py` (17/17) — build, bevel cross-section, hooks bound,
  **live follow** (move a handle → evaluated pipe follows in 3D, read via depsgraph `to_mesh` bbox),
  in-between insertion, under-selection guard, `DynamicPipeSlots.b000` name-ordered routing.
  Discovery: `test_blender_ui_handler.py` 87/87.
- **Sync note (mayatk debt):** mayatk's `dynamic_pipe.ui` carries a **stale copy-paste title** —
  `windowTitle` "Create Shader Network" + header "CREATE STINGRAY SHADER" on a pipe tool. The
  blendertk `.ui` was created correct ("Dynamic Pipe" / "DYNAMIC PIPE"); **fix mayatk's `.ui` to
  match** when next touching mayatk, so the pair stays in sync.

### ImageTracer — M/L ✅ (shipped 2026-06-16)
- **mayatk:** `nurbs_utils/image_tracer.py` (529 ln). cv2 contour detection → NURBS curves; also a
  `BluePencilMixin` (Maya Blue Pencil strokes → curves) — **Blender has Grease Pencil instead**.
- **blendertk:** `nurbs_utils/image_tracer.py` (`ImageTracer` engine + co-located `ImageTracerSlots`
  + `image_tracer.ui`). **Created the `nurbs_utils` subpackage** (was the Layer-4 gap) with the
  shared `NurbsUtils` base (`_nurbs_utils.py`) — see below.
- **Realized mapping:**
  - cv2 contour extraction split into the **pure** `ImageTracer._contours_from_image` (no bpy →
    unit-testable wherever cv2 lives) feeding `NurbsUtils.create_curve`/`add_spline`. Threshold /
    `approxPolyDP` epsilon (Simplify) / scale map directly.
  - **One curve object, one cyclic POLY spline per contour** (Maya: one transform per contour).
    Nested contours → **holes** under Blender's 2D even-odd fill, so `create_mesh` (Maya
    planarSrf+nurbsToPoly, positive space) and `create_negative_space_mesh` (boundary rect +
    contour holes) both reduce to `dimensions='2D'` + `fill_mode='BOTH'` + `curve_to_mesh` bake.
- **Divergences (documented):**
  - Curves on the **XY ground plane** (Z-up Blender), image-Y flipped so the trace is upright in
    top view — Maya placed them on XZ (Y-up) as `(x, 0, y)`.
  - **`project_on_plane` dropped** — Blender curves are born planar on Z=0, so it is vestigial; the
    `b005` button is hidden (`b005_init` `setVisible(False)`).
  - **`BluePencilMixin` dropped** — Maya Blue Pencil has no Blender analogue; **Grease-Pencil-stroke
    → curve is the deferred opt-in** (a future `_strokes_from_grease_pencil` feeding the same
    `NurbsUtils.create_curve`, mirroring the cv2 split). The Blue-Pencil header widgets are not added.
- **cv2 dependency:** Blender ships **no cv2**, the workspace `.venv` has it (4.13). So `trace_curves`
  only runs where cv2 is installed; the Slots guard it (`_tracer` warns when cv2 is absent or the path
  is empty, before constructing the engine). Per [[reference_pushps1_cascade_gotchas]] the test gates
  the cv2 path.
- **Menu wiring:** handler/shelf-launched (`marking_menu.show("image_tracer")`) — like the other
  co-located tools and like mayatk (the `nurbs` *menu* itself stays native `bpy.ops`).
- **Tests:** `blendertk/test/test_image_tracer.py` is **dual-mode** — under Blender (bpy, no cv2):
  `NurbsUtils.create_curve`/`add_spline`/`curve_to_mesh` (fill + bevel + orphan purge),
  `create_mesh` (fill + nested-hole area check), `create_negative_space_mesh`, Slots guards (15/15).
  Under `.venv` (cv2, no bpy): `_contours_from_image` on a synthetic square-with-hole image
  (contour count, ~4-corner simplify, XY/z=0 placement, scale, simplify=0 density, missing-file
  raise) (7/7). Discovery: `test_blender_ui_handler.py` 91/91.

### NurbsUtils (shared base) — created 2026-06-16
- **blendertk:** `nurbs_utils/_nurbs_utils.py`. Mirror of mayatk's `NurbsUtils` namespace at the
  **name + behavior** level, **relaxed (not a signature mirror)** — Blender's curve `bevel_depth` /
  `fill_mode` + one evaluated-mesh bake (`bpy.data.meshes.new_from_object`) replace Maya's entire
  `loft` / `planarSrf` / `nurbsToPoly` / `extrude` / MASH command layer.
- **Surface:** `add_spline(curve, points, cyclic, kind)`, `create_curve(points, …)` (point-list →
  curve object — the `cmds.curve` analogue), `curve_to_mesh(curve_obj, keep_curve=False)` (bakes the
  **evaluated** curve — bevel sweep *or* 2D fill — to a mesh, the `nurbsToPoly` analogue; purges the
  orphaned curve datablock, mirroring the ImageToPlane orphan fix).
- **Shared by:** ImageTracer (now) and CurveToTube (next — its tube bevel will reuse
  `curve_to_mesh`). Built upfront per the "extract shared infra now" rule, but scoped to the two
  primitives both tools provably need (YAGNI on CurveToTube's bevel/RDP internals).

### CurveToTube — L ✅ (shipped 2026-06-16)
- **mayatk:** `nurbs_utils/curve_to_tube.py` (837 ln). Sweep a circular profile along curve(s) →
  NURBS surface OR polygon mesh; RDP simplification places poly rings on bends; curveWarp deformer
  for live open tubes; normal-conform; UV-seamed; hermetic `Preview` for live/rollback.
- **blendertk:** `nurbs_utils/curve_to_tube.py` (`CurveToTube` engine + co-located `CurveToTubeSlots`
  + `curve_to_tube.ui`). **Native curve bevel collapses Maya's entire extrude→nurbsToPoly→curveWarp
  →normal-conform chain into curve properties + the shared `NurbsUtils.curve_to_mesh` bake** — the
  payoff of the "prefer native bpy" rule (837 mayatk lines → ~150 blendertk).
- **Realized mapping (probed empirically):**
  - **NURBS Tube** → a **beveled curve** (`bevel_mode='ROUND'`, `bevel_depth=radius`) — smooth and
    inherently live (curve drives the tube), Blender's analogue of Maya's NURBS surface. `Degree`
    → round-bevel resolution (1 → 0/faceted, 3 → `round(sections/4)`/smooth); `Sections` scales it.
  - **Polygon Tube** → a **mesh**: a `bevel_object` **POLY circle of exactly `sections` points**
    gives exactly `sections` sides (verified: 5-gon profile → 5 sides), `resolution_u` = Path Res
    (ring density), `use_fill_caps` = Caps; baked via `NurbsUtils.curve_to_mesh`. `Quads` off →
    bmesh triangulate.
- **Divergences (documented):**
  - **`output_type` decides the result TYPE** (Blender unifies curve+surface): nurbs → live beveled
    curve, polygon → baked mesh. The **source curve is always preserved** (as Maya does).
  - **`live` (Keep History):** honored for **nurbs** (bevel the source in place — the curve *is* the
    live tube — vs a beveled duplicate); for **polygon** Blender has **no live curve→mesh**, so the
    mesh is always baked and `live` only decides whether the source curve is kept (editable driver)
    or consumed. *(Maya keeps topology identical across Keep-History; Blender's faithful "live" form
    is the curve, so the curve↔mesh distinction is the documented divergence.)*
  - **No RDP curvature ring placement / curveWarp / normal-conform** — Blender's bevel gives uniform
    rings (use a finer Path Res for bends) with consistent outward normals natively. No UV-seaming
    (Blender auto-generates curve UVs).
- **Reuse:** `NurbsUtils.curve_to_mesh` (the bake, shared with ImageTracer) + `NurbsUtils.create_curve`
  (the profile circle). Hermetic `Preview` (blendertk's, snapshots curve data → rollback restores the
  in-place-beveled source); `PRESERVE_GEOMETRY=True`.
- **Menu wiring:** handler/shelf-launched (`marking_menu.show("curve_to_tube")`) — like mayatk (the
  `nurbs` *menu* itself stays native `bpy.ops`).
- **Tests:** `blendertk/test/test_curve_to_tube.py` 20/20 — nurbs live (in-place curve) / baked
  (duplicate, source preserved), polygon mesh (exact sides, Path-Res ring density, caps add faces,
  quads→triangulate), polygon-live keeps source, non-curve guard, `perform_operation` + Select
  Result routing. Discovery: `test_blender_ui_handler.py` 95/95.

### RenderOpacity — L ✅ SHIPPED 2026-06-16 (test_render_opacity 26/26, handler 115/115)
- **Built:** `blendertk/mat_utils/render_opacity/` (`RenderOpacity` engine + `RenderOpacitySlots` +
  co-located `render_opacity.ui`), registered in `DEFAULT_INCLUDE`, wired into the blender **rigging
  `b004`** (mirror of Maya's rigging b004 → `marking_menu.show("render_opacity")`; replaced the old
  "deferred" stub). Keyable `opacity` custom prop (0-1) + **driver → Principled BSDF Alpha** (Alpha is
  input index 4 in Blender 4.0+); `key_fade` keys opacity (linear) **and** mirrors render visibility
  (`hide_render`, stepped) — the Unity dual-key invariant; `sync_visibility_from_opacity` /
  `prepare_for_export` (scene-wide safety net), `objects_with_visibility_keys`, `ensure_connections`,
  `remove`. Reuses `anim_utils`' slot-aware fcurve helpers (`get_fcurves` / `_remove_fcurve` — Blender
  5.x dropped flat `action.fcurves`) and the script-built-driver refresh gotcha (re-assign expression
  after `view_layer.update`).
- **Divergences (documented, not reductions):** no StingrayPBS → Maya's attribute/material modes both
  collapse onto the Alpha driver (the `mode` arg is accepted for parity); the m_Enabled analogue is
  `hide_render` (no Maya `visibility` attr); **materials are made single-user per object** so opacity
  is per-object (Blender shares material datablocks — the equivalent of Maya's per-object proxy). The
  exact FBX visibility-channel mapping is finalized with the SceneExporter/`fbx_utils` port; this
  engine produces the dual-keyed Blender data (opacity curve + `hide_render` curve).
- **Verified (headless):** create seeds prop + Alpha driver (single-users a shared material);
  animated opacity drives Alpha (0.5 @ midframe); key_fade dual-keys (opacity linear + hide_render
  stepped, hidden where opacity 0); prepare_for_export mirrors + is idempotent; create guards on
  pre-existing vis keys; remove strips prop + curves + driver. Has the unitytk C# counterpart already.
- **Historical plan notes below.**

### RenderOpacity — original plan notes
- **mayatk:** `mat_utils/render_opacity/` (1341 ln). Keyable `opacity` transform attr + material
  graph wiring for viewport feedback; `key_fade` animates with visibility mirroring; attribute-mode
  and material-mode delegates. **Has a unitytk C# counterpart already** (`RenderOpacityImporter` /
  `RenderOpacityController` — see `memory/reference_unitytk_opacity_from_visibility.md`).
- **Blender mapping:** custom prop `opacity` on the object + **driver** → Principled BSDF `Alpha`
  (and/or material blend mode). `key_fade` → keyframe the prop; mirror to object visibility
  (`hide_render`/`m_Enabled` analogue) — Unity rebuilds opacity from the visibility track, so the
  **dual-key (opacity + visibility)** rule from the memory MUST be honored on export.
- **Divergence:** Maya's per-material graph wiring → Blender driver to Principled Alpha; EEVEE
  needs `blend_method = 'BLEND'/'HASHED'`. Keep the FBX custom-prop opacity curve for the Unity
  importer (it detects controllers from it).
- **Deps:** FBX export must carry the opacity custom prop + visibility key (coordinate with
  SceneExporter / blendertk `fbx_utils`).
- **Menu wiring:** `materials`/`animation` menu.
- **Tests:** headless — set opacity, assert driver on Principled Alpha; key_fade → assert both
  opacity and visibility keys exist (the unitytk-parity invariant).

---

## Tier C — Large / deferred (tracked; surface divergence decisions before coding)

### TubeRig — XL ✅ SHIPPED 2026-06-16 (test_tube_rig 21/21, rig_utils 37/37, math 160, handler 122/122)
- **Decision (user-chosen): HYBRID, multi-strategy.** The user redirected the "which deformation
  backend" question → wanted **all common tube-rig types in one tool** + Maya's **structure** kept +
  the panel evaluated against the uitk attribute window. Investigation showed Maya's `TubeRig`
  *already* is multi-strategy (`TubeStrategy` ABC + `RIG_MODES`). Built faithfully on **Armature +
  Spline IK** (Option 1) PLUS Anchor + FK, with the panel built on the attribute-window **factory**
  (`AttributeSpec`+`make_widget`) but NOT the popup itself (kept the docked Switchboard chrome).
- **Built (`blendertk/rig_utils/`):**
  - **Foundation in `RigUtils`** (shared, were the deferred "per-rig" anti-pattern): `create_armature`/
    `add_bone_chain` (joints→bones), `add_spline_ik` + `add_bone_constraint` (ikSplineSolver→**Spline
    IK** + the shared pose-bone constraint primitive), `bind_armature` (skinCluster→armature+auto
    weights), `_active_mode` (EDIT/POSE scope).
  - **`controls.py`** (`Controls`+`ControlNodes`) — curve-object control widgets via a `register_preset`
    registry (relaxed Maya's metaclass); circle/square/diamond/cube/sphere/arrow.
  - **`tube_path.py`** (`TubePath`) — centerline via the shared DCC-neutral
    **`ptk.MathUtils.centerline_from_points`** (dominant-axis slab slicing) + explicit edge override.
  - **`tube_rig.py`** — `TubeRig` engine + `TubeStrategy` ABC + `TUBE_STRATEGIES` registry +
    `register_strategy`: **SplineIK** (bone chain + Spline IK on a hook-driven driver curve, stretch via
    y_scale_mode), **Anchor** (2 controls + Stretch-To/Damped-Track), **FK** (bones-as-controls, native
    bone-hierarchy FK + curve custom shapes). Each strategy DECLARES its options as Qt-free **dicts**
    (the HYBRID source of defaults + widgets — `uitk.bridge.spec` imports Qt, so the engine can't hold
    `AttributeSpec`). `TubeRigSlots` + `tube_rig.ui` = the docked panel whose `cmb_preset` rebuilds the
    options body from the selected strategy's dicts.
- **Divergences (documented):** Maya joints→bones, ikSplineSolver→Spline-IK constraint, skinCluster→
  armature+auto-weights, separate FK control objects→**bones-as-controls**, RigModeConfig fixed-superset
  +editability-flags→**per-strategy dict options** (more extendable). `Naming`/`Attributes` deps not
  needed (Blender auto-names; option dicts replace the attr registry).
- **Verified:** each strategy DEFORMS (evaluated-depsgraph bbox) — spline bend, anchor stretch, FK swing.
- **Menu wiring:** rigging `cmb002` Quick Rig → `"Tube Rig"` → `marking_menu.show("tube_rig")` ✅.

### BlendshapeAnimator — XL ⬜
- **mayatk:** `anim_utils/blendshape_animator/` (2419 ln, 8 sub-modules: applicator, creator,
  helpers, keyframes, recovery, target, validator, weights). Maya blendShape morph-animation
  authoring/editing/export — facade over the 8 components.
- **Blender mapping:** Maya blendShape → **Blender shape keys** (`obj.data.shape_keys.key_blocks`).
  Keyframe `value` on key blocks. Tween creation = duplicate-mesh in-between → new shape key from
  mesh. Recovery/validator/weights map to shape-key value clamping and verification.
- **Divergence:** Maya blendShape is a deformer node with many targets + per-target weights; Blender
  shape keys are intrinsic to the mesh and relative/absolute. Inbetweens differ (Maya inbetween
  targets vs Blender's relative keys). Port the facade + sub-components 1:1 where the concept holds.
- **Menu wiring:** `animation` menu.

### SceneExporter — XL ⬜
- **mayatk:** `env_utils/scene_exporter/` (3059 ln: `_scene_exporter`, `task_factory`,
  `task_manager`). Orchestrated FBX export pipeline — a task graph (pre-export hooks, naming,
  opacity prep, etc.) with a manager/factory.
- **Blender mapping:** `bpy.ops.export_scene.fbx` wrapped by the same task-graph architecture.
  blendertk already has `env_utils/fbx_utils.py` — **reuse/extend it as the export primitive**;
  build the task_manager/task_factory on top (don't duplicate FBX flag logic).
- **Divergence:** FBX flag names differ (Blender's exporter vs Maya FBX plugin). The
  dense-mesh hard-edges perf lesson (memory `reference_fbx_export_dense_perf.md`) is Maya-specific
  (`FBXExportHardEdges`); Blender's exporter has its own normal/smoothing options — re-evaluate.
  RenderOpacity dual-key hook must run as a pre-export task (see RenderOpacity).
- **Menu wiring:** `scene`/`env` menu.

### HierarchyManager — XL ⬜
- **mayatk:** `env_utils/hierarchy_manager/` (7416 ln: `_hierarchy_manager`, `hierarchy_sidecar`,
  `tree_renderer`, `tree_utils`). Scene-hierarchy tree browser/editor with a metadata **sidecar**
  (per-node metadata persisted alongside the scene).
- **Blender mapping:** outliner-like tree over `bpy.data.objects` parent graph; sidecar = custom
  properties or a JSON sidecar keyed by object. `tree_renderer`/`tree_utils` are largely DCC-neutral
  (could be partly shared). SceneExporter and Shots depend on `hierarchy_sidecar` (note the import
  in `_scene_exporter`).
- **Divergence:** Maya DAG paths (`|a|b|c`) vs Blender flat names + parent pointers + collections.
  Blender adds **collections** (no Maya equivalent) — decide whether the tree shows collections.
- **Deps:** consumed by SceneExporter & Shots → consider porting the **sidecar** early (small,
  shared) even before the full tree UI.
- **Menu wiring:** `scene`/`env` menu.

### AudioClips — XL ⬜  (module prerequisite)
- **mayatk:** `audio_utils/audio_clips/` (1816 ln) on top of the whole `audio_utils` module
  (64 public names, **entirely absent in blendertk**). Scene-wide audio event manager; per-track DG
  nodes + a composite WAV for the single Time-Slider audio slot.
- **Blender mapping:** Blender's **VSE / sound strips** (`bpy.data.sounds`, sequence editor sound
  strips, or `bpy.ops.sequencer.sound_strip_add`) — Blender supports *multiple* audio strips
  natively, so the Maya "single slot → composite WAV mix" workaround is **unnecessary** (big
  simplification). The track/clip data model still ports.
- **Divergence:** large. Maya needs the composite-WAV mixdown; Blender plays many strips directly.
  Port `audio_utils` data model first (data_internal carrier → custom props / a scene block), then
  AudioClips as the manager.
- **Deps:** port `audio_utils` module first (Layer-4 absent module).
- **Menu wiring:** `animation` menu.

### Shots (+ ShotManifest + ShotSequencer) — XXL ⬜
- **mayatk:** `anim_utils/shots/` (15354 ln). `_shots` (ShotBlock data model + pluggable-persistence
  ShotStore), `shot_sequencer`, `shot_manifest`, plus detection/apply/plan helpers. A full shot/
  sequence pipeline.
- **Blender mapping:** **no native Maya-style shot system.** Closest building blocks: Timeline
  **markers** + camera binding (`marker.camera`), multiple **Scenes**, or the VSE for sequencing.
  The `ShotBlock`/`ShotStore` data model + pluggable persistence is DCC-neutral and ports cleanly;
  the apply/detection layer needs a Blender backend (markers/cameras).
- **Divergence:** very large; the apply layer is almost entirely new. Persistence backend
  (`MayaScenePersistence`) → a `BlenderScenePersistence` (scene custom props / text datablock).
- **Recommendation:** lowest priority — biggest divergence, least shared surface. Port the data
  model + manifest (read-only) before the sequencer (write/apply).
- **Menu wiring:** `animation` menu.

### WorkspaceMap — M, but DEFER/EVALUATE ⬜
- **mayatk:** `env_utils/workspace_map.py` (574 ln). Discovers & displays **Maya workspaces** (the
  `workspace.mel` project structure) in a filterable tree with scene counts / recent files.
- **Blender divergence:** Blender has **no Maya-workspace concept** (no project definition file).
  Closest: a `.blend` file browser / asset-library tree. **Parity value is questionable** — this is
  a Maya-project-management tool. **Recommend: do not port as-is.** If wanted, reframe as a
  `.blend`/asset browser, but confirm value with the user first rather than force a 1:1.
- **Menu wiring:** `env`/`scene` menu (if pursued).

---

## Thin-shell deepening (panels present but doing far less than Maya)

From the audit's Layer-3 "worst first by logic" table. Each *exists* (button + `.ui` + `*Slots`) but
the engine is a fraction of Maya's. Deepen in-place; the `.ui` and slot scaffolding already pair.

| panel | logic% | mayatk source | what's missing (read the slot pair to confirm) |
|:--|--:|:--|:--|
| ~~GameShader~~ ✅ | — | `mat_utils/game_shader.py` (1804 ln) | **DEEPENED 2026-06-16** — see below |
| ~~ReferenceManager~~ ✅ | — | `env_utils/reference_manager.py` (2914 ln) | **DEEPENED 2026-06-16** — see below |
| ~~HdrManager~~ ✅ | — | `light_utils/hdr_manager.py` (1248 ln) | **DEEPENED 2026-06-16** — see below |
| ~~ShaderTemplates~~ ✅ | — | `mat_utils/shader_templates.py` (698 ln) | **REBUILT 2026-06-16** (graph capture/restore) — see below |
| ~~MatUpdater~~ ✅ | — | `mat_utils/mat_updater.py` (974 ln) | **DEEPENED 2026-06-16** — see below |
| ~~Channels~~ ✅ | — | `node_utils/attributes/channels/channels_slots.py` (3127 ln) | **DEEPENED 2026-06-16** (scrub/wheel value editing + compact view) — see below |
| ~~TexturePathEditor~~ ✅ | — | `mat_utils/texture_path_editor.py` (1895 ln) | **DEEPENED 2026-06-16** — see below |
| ~~Curtain~~ ✅ | — | `edit_utils/curtain.py` (866 ln) | **DEEPENED 2026-06-16** (preset combo) — see below |

> A low logic% is a *prompt to read the slot pair*, not proof of a gap (the audit can't tell
> divergence from missing). Confirm against the Maya slot before deepening. RizomBridge (28%, 250%
> UI) is an external-bridge thin shell — likely fine; verify the bridge connects.

### ReferenceManager — FULLY REBUILT ✅ (2026-06-16, 2nd pass)
**Correction:** the first pass under-scoped this — it kept narrowing mayatk's panel to "link .blend
files" and labelled the rest Maya-only. mayatk's RM (2914 ln, inherits `WorkspaceManager`) is a
**workspace scene-file manager**, and almost all of it has a real Blender analogue. Rebuilt to the
**correct architecture**, mapping each feature:

| Maya feature | Blender analogue (engine `EnvUtils`) |
|:--|:--|
| `txt000` root + `cmb000` **workspace** combo (project dirs, per-dir history) | root dir + `cmb000` = project folders under it (`find_workspaces`) |
| scene-file table (`.ma`/`.mb`) | `tbl000` = `.blend` files in the workspace (File · Status · **Notes**) |
| **open scene** (dbl-click / action col) | `open_scene` → `wm.open_mainfile` (dbl-click; confirms if dirty) |
| **save scene** + naming (case/suffix/subfolder) | `save_scene_as` → `wm.save_as_mainfile` + `format_scene_name` (header Naming menu) |
| **rename / delete scene** | `rename_scene_file` / `delete_scene_file` (on disk, + `.blend1`) |
| reference toggle | Link / Append (`link_blend_file`) |
| import references | `make_library_local` (per-row + Make Local All) |
| update references | reload (per-row + Reload All) |
| un-reference all | remove (per-row + Remove All) |
| per-reference **display modes** (normal/reference/template) | `set/get_reference_display_mode` → object `display_type` + `hide_select` (off / locked / WIRE+locked) |
| **Notes** column | per-file notes persisted in the panel settings (DCC-agnostic) |
| open file location | `pythontk.FileUtils.reveal_in_file_manager` (shared, cross-platform) |

- **Engine (all headless-tested):** added `find_workspaces`, `open_scene`, `format_scene_name`,
  `save_scene_as`, `rename_scene_file`, `delete_scene_file`, `set/get_reference_display_mode`,
  `make_library_local` to `EnvUtils`. The display-mode tri-state maps cleanly: off = normal,
  reference = `hide_select` locked, template = `WIRE` + locked.
- **Genuinely Maya-only (dropped, documented):** **namespaces** and **assemblies**
  (`AssemblyManager` / `convert_references_to_assemblies`) — no Blender analogue.
- **Presentation divergence (only):** operations are driven from the row **context menu** +
  double-click + an editable **Notes** column rather than Maya's clickable **icon columns** (same
  capabilities; `widget.actions.add` exists but the per-row state machine is hard to verify headless).
- **Tests:** `blendertk/test/test_reference_manager.py` **41/41** — every engine helper
  (workspaces, open/save/rename/delete with naming + subfolder, display-mode tri-state incl. the
  all-must-agree rule, make-local) + the bulk slot ops. pythontk `test_reveal_in_file_manager`.
  The slot is now **bpy-guarded** (table degrades to a file list without live linked-status when bpy
  is absent), so it **loads + runs every `*_init` under the `.venv` handler test (98/98)** — the Qt
  wiring (workspace combo, Naming menu, table + full context menu) is load-verified, not just
  pattern-mirrored.

### HdrManager — DEEPENED ✅ (2026-06-16)
Measured first: the blendertk version was already substantially faithful (HDR map combo, intensity,
exposure, rotation, visible) — the low 16% reflects Blender's terse World API, not a missing half
like RM. Closed the genuine gaps, re-checking each "dropped" item against Cycles rather than assuming:
- **`aiDiffuse` / `aiSpecular`** (skydome diffuse/specular contribution) → **map** to Cycles **world
  ray visibility** (`world.cycles_visibility.diffuse`/`.glossy`, confirmed in 5.1). Added
  `LightUtils.set/get_world_ray_visibility` + an **Affects (Cycles)** group with Diffuse/Glossy
  toggles (boolean here vs Arnold's float; EEVEE ignores). This was wrongly listed as a drop before.
- **Reveal / open folder** (Maya's `ctx_reveal_in_explorer` / `open_sourceimages`) → header menu
  **Reveal Selected HDR** + **Open HDR Folder** via the shared `pythontk.FileUtils.reveal_in_file_manager`.
- **Genuinely Arnold-only (correctly dropped, documented):** importance-sampling **Resolution**
  (Cycles auto MIS), skydome **Samples** (Cycles samples globally), and select-skydome/transform/
  file-node (a Blender world isn't a selectable object).
- **Tests:** `test_light_utils.py` 18/18 (ray-visibility set/get + partial-update); panel is bpy-free
  at init → now in the handler **load** loop, header menu + Affects toggles load-verified (101/101).

### GameShader — DEEPENED ✅ (2026-06-16)
The 8% was misleading: mayatk's 1804 ln is mostly three Maya shader backends (Stingray / Standard
Surface / OpenPBR) — which **collapse to Blender's one Principled BSDF** — plus the texture
prep/pack helpers that already live in the **shared `pythontk.MapFactory`**. The real engine is
`blendertk.create_pbr_material` (texture-type → Principled input wiring). Measured map-type coverage
against mayatk's `connect_*_nodes` and closed the genuine gaps:

| Maya map type | Blender wiring (now in `create_pbr_material`) |
|:--|:--|
| `Albedo_Transparency` | one image node → Base Color (Color) **+ Alpha** (Alpha out) + HASHED blend |
| `Metallic_Smoothness` (Unity) | RGB → Metallic; **A → Invert → Roughness** |
| `MSAO` / Unity HDRP mask | Separate Color: R → Metallic, G → AO (multiply into Base); **A → Invert → Roughness** |
| packed `ORM` (already present) | Separate Color: R → AO, G → Roughness, B → Metallic |

- **Packed-map priority** mirrors mayatk's `_create_single_network`: `ORM` supersedes `MSAO` +
  `Metallic_Smoothness`; `MSAO` supersedes `Metallic_Smoothness` (so they don't fight over
  Metallic/Roughness). Explicit single maps still win over a packed split (guarded `not in by_type`).
- **Batch mode** (mayatk's `create_network` group-by-set): new `create_pbr_materials` orchestrator
  groups files by texture set (shared `MapFactory.group_textures_by_set`) and builds **one material
  per set**; an explicit Material Name collapses to a single material (mirrors `group_by_set = not
  bool(name)`). The slot's *From Folder* now builds N materials instead of one garbled merge;
  assign-to-selection is skipped when N>1 (ambiguous target — the Maya tool never assigns at all).
- **Genuinely Maya/Arnold-only (correctly dropped, documented):** the **shader-type** combo (one
  Principled BSDF), the **Arnold (`aiStandardSurface`) bridge** (Cycles is native), and the
  **map-export** knobs (Output Template / Ext) — this flow wires *existing* textures into a node
  graph; baking/writing maps is the Material Updater's job (and the `MapFactory` packing it would do
  is wrong for Blender's *separate*-input Principled, per the MatUpdater divergence note).
- **Tests:** `test_mat_anim_utils.py` game-shader block extended — Albedo+Transparency dual-output,
  Metallic_Smoothness, MSAO, packed-map priority (ORM drops the others → 1 image loaded), and batch
  (2 sets → 2 materials / explicit name → 1). Handler load still 101/101.

### TexturePathEditor — DEEPENED ✅ (2026-06-16)
Measured first: the blendertk slot was already substantially faithful (full General / Path Management
/ Selection header menu, editable 3-column table, row context menu, cell-edit repath+rename, 4 option
boxes, selection helpers) — the 34% undercounts. The audit's "2 option boxes absent (7→5)" was really
**one missing Resolve-Missing strategy** + engine safety depth. Closed both genuine gaps (engine-level):

- **Map-type-aware "Texture" resolve tier** — mayatk's Resolve Missing cascades stem → **texture** →
  fuzzy; the middle tier restricts fuzzy candidates to the **same map type** (shared
  `ptk.MapFactory.resolve_map_type` + `get_base_texture_name` + `FuzzyMatcher`) so an `_AO` never
  repaths to a `_Normal`. blendertk had only stem + fuzzy. Added `texture=` to
  `resolve_missing_textures` + a third `chk_texture` checkbox in the option box. **Fixed a latent bug
  mayatk shares:** map type must be resolved from the **original-case** filename — short aliases
  (`AO`, `MS`, …) are case-sensitive, so the lowercased index stem returned `None` and silently
  dropped them. blendertk now keeps an `orig_stems` map and resolves on original case.
- **Collision-safe relocation** — blendertk's Set-Directory / Normalize / Find-&-Copy all
  `shutil.copy2`/`move` straight onto the destination, **silently overwriting** a different-content
  same-name file (wrong-file rebind / data loss). Added a shared `_safe_relocate(src, dst, mode)`
  helper (DRYs what mayatk duplicates inline) with Maya's policy: same-size → safe rebind (reuse, no
  overwrite; move removes the redundant source), different-size → **skip** (no clobber), and wired it
  into all three relocate functions (skipped images keep their valid path; the count delta surfaces it).
- **Genuinely Maya-only (correctly dropped, documented):** separable *file-node* selection (Blender's
  image has no node-name handle distinct from it), *namespaces*, and *sourceimages* as the implicit
  search root (Blender has no project workspace — the commands prompt for a folder). Scene-change
  auto-refresh (Maya `ScriptJobManager`) → `refresh_on_show` + the manual refresh button (Blender
  `bpy.app.handlers` lifecycle isn't worth the cleanup complexity for the marginal gain).
- **Tests:** `test_mat_anim_utils.py` extended — the texture tier picks the same-map file over a
  closer wrong-type name; the collision guard skips a different-size dst (no overwrite, path
  unchanged) and safe-rebinds an identical one. Handler load 101/101.

### ShaderTemplates — REBUILT ✅ (2026-06-16, graph capture/restore — user-chosen direction)
Measured first: the blendertk port was a **fixed 9-preset parameter applier**; mayatk's is a full
**graph save/restore with a user-preset store** that rebinds textures by map type. That was a genuine
reduction (the docstring's "Blender has one Principled BSDF so a preset is the analogue" was the same
under-scoping flagged on RM — Blender *does* have arbitrary shader node graphs). Asked the user the
architecture fork (purpose-faithful graph capture vs. Blender asset-library vs. accept reduction);
they chose **purpose-faithful graph capture/restore** — mirror Maya's PURPOSE without cargo-culting
the `.sfx`/Stingray YAML specifics.

- **Engine (headless-tested):** `serialize_material(mat)` captures the node graph as a JSON-safe dict
  (node type, location, curated props, *unlinked* input values, links by node-name + socket index);
  image nodes store their **map type** (shared `ptk.MapFactory`), not the path. `restore_material(data,
  name, textures)` rebuilds it and **rebinds fresh textures by map type** (Maya's `GraphRestorer`),
  leaving an image node unbound when no match (Maya's "missing texture for X"). A `{"params": {...}}`
  shorthand shares the restore path so the fixed built-ins and saved graphs are one mechanism.
- **User store:** the shared `pythontk.PresetStore("shader_templates", package="blendertk")` (JSON, user
  tier — the same store that backs the photogrammetry runners + `uitk.PresetManager`), so Save / Rename
  / Delete / Open-folder come for free and stay Qt-free/bpy-free (load-verified under the .venv handler).
- **Panel:** header menu gains **Save Selected as Template** (serialize active material → store),
  **Load Textures** (Maya's b001 — files rebound on restore), and Rename / Delete / Open-folder.
  **Create New** (b000) dispatches by kind — built-in → `create_shader_template`, saved → `restore_material`
  + bound textures — then assigns. **Apply to Selected** (b001) stays the built-in parameter-preset path
  (graph templates create a new material → it says so).
- **Genuinely Maya-only (correctly dropped):** the `.sfx`/StingrayPBS `loadGraph` re-apply dance and
  Maya `nodeType`/classification specifics (Blender's `bl_idname` graph round-trips directly).
- **Tests:** `test_mat_anim_utils.py` — serialize captures nodes+links + map types (not paths);
  restore rebuilds topology + rebinds a FRESH texture set by map type (Non-Color preserved); JSON +
  **PresetStore** save/list/rename/load round-trip; param shorthand; unbound-when-no-textures. Handler 101/101.

### MatUpdater — DEEPENED ✅ (2026-06-16)
Measured first: the blendertk slot already matched most of mayatk's options (selection mode, convert
format, max-size, mask-scale, force-packed, in/out fallbacks + the disable-on-force-packed wiring,
dry-run, output folder, preset) — the 21% undercounts. The one genuinely-portable, valuable gap was
mayatk's third **"Browse…" selection scope** (pick texture files → update the materials that reference
them). Added engine `materials_for_textures(paths)` (Qt-free/bpy-only, mirrors Maya's
`_materials_from_texture_paths` via normalized-abspath match) + a `Browse…` combo item + a
`_browse_textures` file dialog in the slot.
- **Legitimate divergences (verified against the engine, docstring accurate):** **transfer-mode**
  (copy/move) and **archive folder** don't map — the blendertk engine's model writes processed
  outputs to `output_dir` via the shared `prepare_maps` and leaves sources in place (Maya's
  transfer/archive exists because its flow physically moves the files post-process). The **ORM/MSAO
  shader-rewire** stays dropped for the documented reason (Principled has separate inputs; packed
  maps still land on disk for engine export). The clickable-log-link dispatch is Maya-node-select.
- **Tests:** `test_mat_anim_utils.py` — `materials_for_textures` finds the referencing material and
  returns `[]` for an unreferenced path / empty input. Handler load 101/101.

### Curtain — DEEPENED ✅ (2026-06-16)
Measured first: the drape **math + mesh build are already fully shared** (`ptk.CurtainDrape` /
`ptk.CurtainRail` — identical to Maya, ~28 params), with live Preview, rail resolution (edges/curve/
objects), and post-ops. The 35% undercounts. Genuine differences were the **preset combo** and the
**wire-deformer rig**:
- **Preset combo (closed):** added a `cmb000` `WidgetComboBox` to `curtain.ui` + wired
  `cmb000_init` through the shared `uitk.PresetManager` (Save/Rename/Delete/Open), and **shipped the
  identical built-in presets** (`Stage Swag`, `Shower Curtain`) under `edit_utils/presets/curtain/`.
  They port verbatim from Maya — a curtain preset is a UI-state snapshot keyed by widget name, and
  the panel shares both the Maya widget names *and* the `CurtainDrape` engine, so a preset drapes the
  same.
  - **`.ui` gotcha (reusable):** the runtime loader registers a custom widget class with QUiLoader
    **only if it's listed in the `.ui`'s `<customwidgets>` block** (`RuntimeLoader.load` iterates
    `metadata["customwidgets"]`). A `WidgetComboBox` not in that block silently loads as nothing
    (`ui.cmb000 is None`, its `_init` never fires). Any future panel adding a preset combo must add
    the `<customwidget>` entry.
- **Wire-deformer rig — ✅ SHIPPED 2026-06-16** (`CurtainRig` engine, test_curtain 25/25, handler
  115/115): Maya's `CurtainRig` (driver **curve** + **wire deformer** + per-CV **cluster** handles
  to hand-animate the drape) ports to `blendertk/edit_utils/curtain.py::CurtainRig`. Blender has no
  wire deformer / no curve→mesh proximity deform, so all three Maya pieces **fuse into the native
  Hook modifier with smooth falloff**: the hook `falloff_radius` **is** the wire `dropoffDistance`,
  and **control Empties** collapse the curve-CVs + clusters into one grabbable handle per pin; a
  root Empty parents the controls + curtain (Maya's rig group). So Maya's two steps
  (`_add_wire`+`_add_clusters`) fuse into `_add_hook`; there's no driver curve or hidden base wire.
  `attach(curtain, controls=5|curve|positions, dropoff, name)` auto-places controls along the
  detected rail (top/max-Y edge — the shared `CurtainDrape` hangs in -Y) or reads a curve's CVs.
  Hook-bind reuses DynamicPipe's proven `matrix_inverse = control.world.inverted() @ curtain.world`
  (identity deform at bind → no jump). **Not wired into the panel — engine-level only, exactly like
  Maya** (`CurtainRig` has no tentacle slot; only `test_curtain` exercises it). Verified: builds N
  controls + N hooks, **moving a control lifts the cloth** (the wire-driver invariant), rigid root
  motion translates without deforming (group behavior), curve-CV-driven controls.
- **Minor divergences (left):** the visible auto-rail *driver curve* during preview (blendertk drapes
  from field-generated rail points directly), spinbox-prefix alignment + axis color-coding (Maya
  cosmetic polish), and the footer tri-count readout.
- **Tests:** `test_curtain.py` 14/14 (engine untouched); handler load **102/102** now asserts the
  preset combo populated from the shipped built-ins.

### Channels — DEEPENED ✅ (2026-06-16)
Measured first: the **25% was badly stale** — the panel mislabeled itself against `ui_utils/channel_box.py`
(the Maya channel-box embed widget) when the real peer is `node_utils/attributes/channels/`. The
blendertk slots already mirror the full context menu (lock/unlock/reset, copy/paste, key/breakdown/
mute/unmute, select-connection, break-animation, freeze/unfreeze, delete), the filter combo + invert,
create-attribute form, and lock/key action columns — **~80% faithful, not 25%.** The two genuine
**portable** gaps (the audit's "channel ops depth"), both wrongly dismissed in the old docstring as
"thinned," were closed:
- **Wheel + MMB scrub value editing (closed):** the heavy lifting is **shared `uitk.TableWidget`
  infra** (`set_scrub_columns` / `set_wheel_scrub_columns` / `set_single_click_edit_columns` +
  `cellScrub*` / `cellWheelScrolled` signals) — DCC-agnostic, *not* a Maya nicety. Mirrored the Maya
  `_wheel_step` ×10/÷10 modifier ladder verbatim and added per-object snapshot scrub + display/edit-mode
  wheel handlers that route deltas through the engine's existing `get/set_channel_value` (so angle
  channels round-trip degrees↔radians correctly).
- **Compact View (closed):** added the `chk_compact_view` header checkbox + handlers (shorter rows via
  `_apply_row_height`, hidden column header, txt001↔footer name swap) using the shared
  `uitk.FooterStatusController` + a footer single-object toggle button + footer inline-rename — full
  faithful mirror of the Maya footer machinery (blendertk had a dead `_compact_view` field proving it
  was intended).
- **Genuine divergences (documented, not closed):** no channel box → **Toggle Keyable / Hide / Show /
  Lock-and-Hide** (every channel keyable, no per-channel CB-visibility flag); no DAG transform/shape
  split → **Select Shape / Select History** (an object owns its mesh data directly; modifiers aren't
  selectable scene nodes); **Auto-fit window** + Channel-Box Qt-signal sync (Maya-editor-only); enum /
  double3 create types (ID props don't model enum/compound).
- **Tests:** engine `test_channels.py` 51/51 (untouched); handler load **107/107** now drives the real
  panel — compact view collapses rows + hides the column header, the wheel-step ladder scales per
  modifier, and stub-controller scrub/wheel checks prove the per-object delta + display-space
  round-trip.

---

## Shared-menu slot verification (Layer 2)

29 hollow handlers flagged + several low-% domains. **Per-domain % is an upper bound on the gap, not
the gap** — `selection` (53%) is ~90% faithful (loop-built criteria undercount), `pivot` (36%) is
legitimate Blender divergence (single baked origin). **Action:** read each flagged slot pair; only
fill genuine `pass`/`message_box("not implemented")` bodies. Do not "fix" intentional divergence.

Flagged for review (option-box deltas marked ⚠ in audit): animation (46→36), edit (6→2), pivot
(11→7), rigging (12→8), selection (11→8), transform (15→12). Hollow-handler count: 29 (Blender).

---

## Cross-cutting prerequisites (port these early — they unblock multiple panels)

- **`Naming`** (Tier A) — consumed by TubeRig and any auto-naming rig/exporter.
- **`hierarchy_sidecar`** — consumed by SceneExporter & Shots; small + shareable; port before the
  full HierarchyManager UI.
- **`audio_utils` module** — prerequisite for AudioClips (currently 0% / absent).
- **`nurbs_utils` module** — absent; CurveToTube + ImageTracer live here (create the module when
  porting the first of them).
- **Armature/bone primitives in `RigUtils`** — prerequisite for TubeRig (Blender armatures are a
  new primitive not yet needed by telescope/wheel).
- **`Controls` (`rig_utils/controls.py`)** — rig control-shape factory; needed by TubeRig.

---

## Maintenance

- Re-run `python m3trik/scripts/generate_parity_audit.py` after each port to refresh the metrics in
  `PARITY_AUDIT.md`; update the **Status** marks in this doc by hand (it's the human layer the
  generator can't infer).
- When a divergence decision is made (e.g. TubeRig → Spline IK), record it here so it isn't
  re-litigated.
