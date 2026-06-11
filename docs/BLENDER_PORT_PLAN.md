# Blender Port — Plan

Build Blender support in **tentacle**, modeled on the existing Maya design, sharing UI
files between DCCs. Develop **blendertk** to do for Blender what **mayatk** does for the
Maya slots.

> Scope note: the MenuButton nav-widget work (replacing the `i`-prefix convention) is
> **done and shipped** in uitk — see `reference_menubutton_nav_widget` in memory. It is a
> prerequisite for the coverage mechanism (Phase 5) but is otherwise out of scope here.

---

## 1. Decision: monorepo, not a fork

Develop in the existing monorepo. The multi-DCC seams already exist; a fork would duplicate
the entire slot/UI surface and immediately diverge. Dependency chain mirrors Maya:

```
pythontk → mayatk    → tentacle/slots/maya     (existing)
pythontk → blendertk → tentacle/slots/blender  (to build)
```

The contract that makes this work: **a shared `.ui` file defines the widget-name surface
(`tb000`, `chk008`, `b005`, …); each DCC's slot file implements those same widget names**
against its own toolkit. Maya's `PolygonsSlots.tb000` and Blender's `PolygonsSlots.tb000`
are driven by the *same* `polygons.ui`. Keeping `blendertk`'s public API **names** mirrored to
`mayatk`'s (`btk.X` ↔ `mtk.X`) lets the two slot bodies stay structurally parallel and keeps
each slot file branch-free (no `if dcc == ...`).

> Mirror **names and slot-visible behavior, not signatures**. mayatk's surface is built on
> Maya's string-node idioms (`"pCube1"`, `"pCube1.f[3]"`); bpy passes object references and
> bmesh layers. A literal signature mirror is impossible and not the goal — the hard
> contract is the widget-name surface of the shared `.ui`.

---

## 2. Current state (what exists vs. what's greenfield)

| Piece | State | Path |
|:---|:---|:---|
| Blender launcher | **Bare stub** — `ui_source="ui"` only; already has Ctrl+Z → `bpy.ops.ed.undo` passthrough | [tcl_blender.py](../tentacle/tcl_blender.py) |
| Maya launcher (reference) | Complete | [tcl_maya.py](../tentacle/tcl_maya.py) |
| Blender slots dir | **Does not exist** (`slots/` contains only `maya/`) | `tentacle/slots/blender/` |
| Maya slots (reference) | 60 concrete slot files | [slots/maya/](../tentacle/slots/maya/) |
| DCC-agnostic slot base | Exists | [slots/_slots.py](../tentacle/slots/_slots.py) → `Slots(QObject)` |
| Maya slot base | Trivial pass-through | [slots/maya/_slots_maya.py](../tentacle/slots/maya/_slots_maya.py) → `SlotsMaya(Slots)` |
| Shared UI (cross-DCC) | 60 `.ui` ≈ **29 domains** (the real port checklist — see §4) | `tentacle/ui/*.ui` |
| Maya-only UI overlay | 33 `.ui` | `tentacle/ui/maya_menus/*.ui` |
| `MayaUiHandler` (reference) | Exists | [maya_ui_handler.py](../../mayatk/mayatk/ui_utils/maya_ui_handler.py) |
| Structural tests | **Hardcoded to `slots/maya` + `maya_menus`** in 4 files (`test_slot_integrity`, `test_ui_integrity`, `test_slot_method_coverage`, `test/slots/_helpers`) | [test/](../test/) |
| Qt host inside Blender | **Does not exist.** Blender is not a Qt app: no `QApplication`, no bundled PySide. `QApplication.instance().blender_widget` (which the stub already reads) is the **bqt** convention | — |
| **blendertk** | **Greenfield** — GitHub repo empty, not checked out in monorepo | — |

### The seams already in place (the good news)

- `tcl_blender.py` already targets `slot_source="slots/blender"` and resolves the main window
  from `QApplication.instance().blender_widget` (i.e. it assumes a bqt-style host).
- The marking menu layers UI via a tuple `ui_source` (Maya uses `("ui", "ui/maya_menus")`).
  Blender's mirror is `("ui", "ui/blender_menus")`.
- **Layering is also the hiding mechanism for whole Maya-only menus**: everything in
  `ui/maya_menus/` simply never loads in Blender. No tagging needed for those (see Phase 5
  for the *widget-level* mechanism inside shared menus).
- Slot resolution, switchboard, the whole MarkingMenu shell are DCC-agnostic and already
  shipped.

### What the stub is missing (vs. `tcl_maya.py`)

Layered `ui_source`, a `BlenderUiHandler`, key/mouse `bindings`, `precompile=True`, a
`SlotsBlender` base, and the **`ExternalAppHandler`** registration (it's DCC-agnostic —
the extapps panels work anywhere Qt runs, so Blender gets them for free).

---

## 3. Workstreams

> Ordered riskiest-first. Phase 0 gates everything that runs live; Phase 1 is pure-Python
> and can proceed in parallel with it.

### Phase 0 — Qt-in-Blender host spike (the riskiest unknown — prove it first)
**Goal:** a uitk widget visible and interactive over a live Blender viewport.

Blender's event loop is GHOST, not Qt. Known approach: **bqt** (techartorg) — creates the
`QApplication`, wraps Blender's window, exposes `blender_widget`, and pumps Qt from a
Blender timer/modal operator. The stub's `get_main_window` already matches bqt's contract,
so bqt is the leading candidate; the fallback is a minimal hand-rolled
`bpy.app.timers`-driven `processEvents()` pump.

- Install PySide6 into Blender's bundled Python (4.x ships Python 3.11 — verify
  `qtpy`/`uitk`/`pythontk` import there).
- Stand up the host (bqt or minimal pump); show a bare uitk window parented to
  `blender_widget`.
- **Probe key capture**: Blender's GHOST loop consumes keyboard input before Qt sees it, so
  the Maya-style Qt-side `bindings` activation may never fire. Determine whether the
  marking menu's key handling works at all, or whether activation must come from a Blender
  add-on keymap operator that calls `tcl.show()` (expected outcome — see decisions §7.2/7.3).
- **Acceptance:** a uitk widget renders over a live (freshly launched) Blender, survives
  interaction, and the activation path (Qt-side or keymap-operator) is decided and demoed.

### Phase 1 — `blendertk` scaffold
**Goal:** an importable `blendertk` whose public surface mirrors `mayatk`, backed by stubs.

- Check out `m3trik/blendertk` into the monorepo; copy mayatk's bootstrap pattern verbatim:
  `bootstrap_package(globals(), include=DEFAULT_INCLUDE)` over `*_utils` subpackages
  (no import side effects; subpackage `__init__.py` = docstring only — root standard).
- Mirror the **names** mayatk exposes, implement only the **subset** the first ported slots
  call (lazy growth of `DEFAULT_INCLUDE`). Start with: `core_utils` (Components/Selection-equiv),
  `xform_utils`, `edit_utils`, `display_utils`, `uv_utils`. See §5 for the bpy mapping.
- `pyproject.toml` from day one (mirror mayatk's), so it's installable into Blender's
  Python; PyPI/cascade membership comes later (§6).
- Test harness: `blender --background --python <runner>` is the mayapy-equivalent for
  headless real-geometry tests (fresh instance every run — session safety).
- Add `blendertk/CLAUDE.md` (mirror mayatk's: session-safety rule, API-registry pointer,
  import conventions — `import bpy`, `import bmesh`).
- **Acceptance:** `import blendertk as btk` succeeds in Blender's bundled Python;
  `btk.<X>` resolves for the starter subset; headless runner executes one real-geometry test.

### Phase 2 — tentacle Blender plumbing
**Goal:** the launcher is feature-comparable to `tcl_maya.py`; an empty Blender slot loads.

- `BlenderUiHandler` (mirror `MayaUiHandler`) — wire into `tcl_blender.py`
  `handlers={"ui": BlenderUiHandler, "external_app": ExternalAppHandler}`. Home:
  `blendertk/ui_utils/` (mirrors the `MayaUiHandler` precedent).
- Flesh out `tcl_blender.py`: `ui_source=("ui", "ui/blender_menus")`, activation wiring per
  the Phase 0 outcome (Qt `bindings` and/or add-on keymap operator), `precompile=True`.
- Add `slots/blender/__init__.py` + `slots/blender/_slots_blender.py` (`SlotsBlender(Slots)`,
  mirror of `SlotsMaya`).
- Create `ui/blender_menus/` (can start empty; the shared `ui/` menus drive everything until a
  Blender-specific menu is needed).
- **Mirror the structural tests**: extend/parametrize `test_slot_integrity`,
  `test_ui_integrity`, `test_slot_method_coverage` (and `test/slots/_helpers`) to cover
  `slots/blender` + `ui/blender_menus` — they currently hardcode the Maya paths.
- **Acceptance:** launching `TclBlender()` inside Blender shows the marking menu with shared
  menus; widgets whose Blender slot doesn't exist yet are silently inert (`connect_slot`
  logs and returns — [slots.py:1010](../../uitk/uitk/switchboard/slots.py#L1010)); making
  them *visibly* greyed is Phase 5.

### Phase 3 — first vertical slice (prove the pipeline)
**Goal:** one EASY domain working **end-to-end** in a live Blender session.

- Pick **`selection`** or `transform` (small, high-confidence, exercises selection + xform).
  ⚠ Not `select` — `slots/maya/select.py` is a near-empty header loader and
  `select#submenu.ui` is Maya-only; the real shared domain is `selection`
  (`selection.ui` + `selection#submenu.ui`). Implement `slots/blender/<domain>.py` against
  the *same widget names* as the Maya counterpart, calling `btk` + `bpy`.
- Implement exactly the `blendertk` helpers that slice needs (drives Phase 1's real surface).
- **Acceptance:** every widget in that menu performs the analogous Blender action in a live
  (freshly launched) Blender. This validates UI sharing, slot resolution, the handler, and the
  btk/mtk API mirror in one shot.

### Phase 4 — port the portable tiers
Port EASY domains, then MEDIUM (see §4). Each domain = one `slots/blender/<domain>.py` +
whatever `blendertk` helpers it needs. Reuse the shared `.ui`; only add a `ui/blender_menus/`
override when a menu genuinely differs.

### Phase 5 — visibility / coverage mechanisms

Whole Maya-only **menus** are already invisible in Blender via `ui_source` layering (§2) —
no mechanism needed. What remains is **widget-level** granularity inside shared menus,
via three mechanisms:

1. **Nav buttons → auto-hide by target resolution.** A `MenuButton` in a shared menu whose
   `target` UI only exists in `ui/maya_menus/` dead-ends in Blender. The target is a
   Designer property (the shipped MenuButton work), so the switchboard can resolve it
   against the loaded UI registry and hide unresolvable nav buttons automatically — no
   manual tagging, stays correct as menus are added.
2. **`requires="maya|blender"` declarative tag → HIDE.** For leaf *action* widgets in shared
   menus unsupported *by design* in a DCC. Filtered the same way
   `hide_unmatched_groupboxes` already filters tags. Static, authoring-time, should be rare
   (most Maya-only surface lives in the overlay already).
3. **Auto-disable / grey widgets whose slot is missing → live "not-yet-built" map.** Seam =
   `connect_slot` in `uitk/switchboard/slots.py` (the `if not slot:` branch currently just
   logs+returns). Make it an **opt-in Switchboard policy hook**, dev-flag gated, deferred
   render, **off in prod** (must not drag init). Type filter is free via `default_signals`;
   only certain widget types are expected to have slots, and nav widgets are detected by
   **type** (`isinstance(MenuButton)`) — that's why the MenuButton work was a prerequisite.
   Same predicate powers a headless coverage report; the denominator is the **shared-ui
   domain list** (§4), not the Maya slot count.

---

## 4. Portable surface & tiers

The port checklist is the **shared `ui/` directory** (29 domains), *not* the Maya slot
inventory — Maya-only domains live in `ui/maya_menus/` and never load in Blender.

| Tier | Domains (shared `.ui`) | Approach |
|:---|:---|:---|
| **EASY** | selection, transform, pivot, duplicate, scene, display, polygons (+5 component submenus), subdivision, normals, uv, symmetry, crease, edit | Direct port; bmesh/bpy.ops analogues of mtk helpers |
| **MEDIUM** | materials, texturing, lighting, rendering→Cycles/EEVEE, animation, rigging→armature, deformation→modifiers, nurbs→curves, cameras | Conceptually parallel but different data model; port carefully |
| **NAV / APP** | hud, main, editors (re-target to Blender editors), preferences, settings, utilities, modify | Mostly nav + app-level actions; port early — they're the marking-menu entry points |

**Not ported (hidden for free by layering):** all 33 `ui/maya_menus/` overlays — arnold,
mash, ncloth, nhair, nparticles, fields_solvers, fluids, stereo, toon, cache, constrain,
control, curves, deform, edit_mesh, effects, generate, help, key, lighting_shading,
maya#startmenu, mesh, mesh_display, mesh_tools, nconstraint, playback, render,
select#submenu, skeleton, skin, surfaces, visualize, windows. No `requires` tags needed
for these. (Blender-side equivalents for the portable *concepts* among them — e.g. skin,
key, playback — arrive later as `ui/blender_menus/` overlays, not as ports of the Maya
menus.)

---

## 5. `blendertk` API surface — starter mapping

Mirror mayatk's public names; back each with bpy/bmesh. Implement lazily as slots demand.

| mayatk (mirror the name) | Blender backing |
|:---|:---|
| `core_utils` — `Components`, `Selection` | `bpy.context.selected_objects`, `bmesh` select history |
| `xform_utils` — matrices, translation, pivot | `object.matrix_world`, `object.location`, 3D-cursor pivot |
| `edit_utils` — `Bevel`, `Bridge`, `Duplicate*`, `Mirror`, primitives | `bmesh.ops.*`, `bpy.ops.mesh.*`, array/mirror modifiers |
| `uv_utils` | `bpy.ops.uv.*`, `bmesh` uv layers |
| `display_utils` | viewport shading / overlay toggles |
| `env_utils` — scene/export | `bpy.ops.wm.*`, `bpy.ops.export_scene.fbx` |
| `mat_utils` | Principled BSDF node graphs |
| `node_utils`, `anim_utils`, `rig_utils`, `light_utils` | as MEDIUM tier reaches them |

---

## 6. Hard constraints / standards

- **Session safety (root CLAUDE.md):** never test against an existing Maya/Blender session —
  always launch a **fresh** instance. No `--reuse`, no attaching to a live session.
- **Shared-`.ui` widget-name contract:** Blender slot methods must match the shared UI's widget
  object names exactly (that's the whole sharing mechanism). When a Maya menu has widgets with
  no Blender analogue, hide them (§3 Phase 5) rather than renaming the shared UI.
- **No import side effects:** subpackage `__init__.py` = docstring only; register via root
  `DEFAULT_INCLUDE` (mirror mayatk).
- **Check the API registry before adding any helper** (DRY/SSoT) — upstream `pythontk` first,
  then `blendertk`'s own once generated. Add blendertk to
  `m3trik/scripts/generate_api_registry.py` when it has a public surface.
- **Release:** once blendertk publishes to PyPI it joins the `m3trik/push.ps1` ecosystem
  cascade (`pythontk → blendertk` dependency sync) — standalone git flow until then.
- **Naming:** `class FooBar` → `foo_bar.py` (Python); widgets `tb###`/`b###`/`chk###`.

---

## 7. Open decisions (resolve in/right after the Phase 0 spike)

1. **Qt host** — bqt vs. minimal hand-rolled timer pump. bqt is the leading candidate (the
   stub already assumes its `blender_widget` contract); verify it's maintained against
   current Blender/PySide6 before committing.
2. **Activation key + chord layout** — Maya uses F12 + L/M/R mouse chords → `*#startmenu`
   UIs (`hud`/`cameras`/`editors`/`main` startmenus are shared; only `maya#startmenu` is
   Maya-only, so Blender reuses the shared four + a future `blender#startmenu`). **F12 =
   Render in Blender** — pick another key. Expect Qt-side `bindings` not to receive keys
   under GHOST (Phase 0 probe); the likely activation is an add-on keymap operator calling
   `show()`.
3. **Delivery into Blender** — an add-on is effectively required (registers the keymap
   operator + the Qt pump timer at startup); remaining choice is dependency strategy:
   pip-install into Blender's Python vs. vendored wheels.
4. **Coverage hook ergonomics** — env var / config flag name; default OFF.

---

## 8. First concrete steps for the next thread

1. **Phase 0 spike**: PySide6 into Blender's Python, stand up bqt (or minimal pump), bare
   uitk window over a live Blender, probe key capture. Highest information per hour —
   do this before any scaffolding.
2. Check out `blendertk`, add the mayatk-style bootstrap + `pyproject.toml` + `CLAUDE.md`
   (Phase 1 — parallelizable with the spike).
3. Flesh out `tcl_blender.py` to parity with `tcl_maya.py` minus Maya-isms (incl.
   `ExternalAppHandler`); add `SlotsBlender` base + `slots/blender/__init__.py`; mirror the
   structural tests (Phase 2).
4. Implement the **`selection`** (not `select`) or `transform` vertical slice end-to-end in
   a live Blender, growing `blendertk` to exactly what it calls (Phase 3).

Everything after that is repeating Phase 3 per EASY domain, then the coverage mechanism.
