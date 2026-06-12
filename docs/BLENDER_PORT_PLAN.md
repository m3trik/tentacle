# Blender Port — Plan

Build Blender support in **tentacle**, modeled on the existing Maya design, sharing UI
files between DCCs. Develop **blendertk** to do for Blender what **mayatk** does for the
Maya slots.

> The MenuButton nav-widget work (replacing the `i`-prefix convention) is **done/shipped** in
> uitk — see `reference_menubutton_nav_widget` in memory. It's a prerequisite for the coverage
> mechanism (Phase 5) but otherwise out of scope here.

---

## 1. Decision: monorepo, not a fork

Develop in the existing monorepo. The multi-DCC seams already exist; a fork would duplicate the
entire slot/UI surface and immediately diverge. Chain mirrors Maya:

```
pythontk → mayatk  → tentacle/slots/maya     (existing)
pythontk → blendertk → tentacle/slots/blender (to build)
```

**Two contracts make sharing work:**

1. **Shared-`.ui` widget-name contract.** A shared `ui/*.ui` defines the widget-name surface
   (`tb000`, `chk008`, `b005`, …). Each DCC's slot file implements those *same* widget names
   against its own toolkit. Maya's and Blender's `selection.py` are driven by the *same*
   `selection.ui`.
2. **API-name mirror (names + slot-visible behavior, NOT signatures).** Mirror `blendertk`'s
   public names to `mayatk`'s (`btk.X` ↔ `mtk.X`) so slot bodies stay structurally parallel and
   branch-free. Signatures differ by necessity — mayatk speaks string-node idioms, bpy speaks
   object refs — so the mirror is at the *name + behavior* level, not the parameter level. And
   the mirror often wraps a **native Blender operator**, not a reimplementation — see the §5
   capability map / don't-reinvent guardrail. The mirror holds where concepts align (EASY tier);
   for domains whose data model diverges (rigging, NURBS, shader graphs) **relax it** — use
   Blender-idiomatic names rather than cargo-culting a Maya concept (§5 MEDIUM tier).

---

## 2. Current state (verified 2026-06-11)

| Piece | State |
|:---|:---|
| [tcl_blender.py](../tentacle/tcl_blender.py) | **Consolidated entry point** (2026-06-12) — Qt host (`launch`/`ensure_qapp`/pump), keymap bridge (`_install_keymap` → `tentacle.show_marking_menu`), `TclBlender` (layered `ui_source`, bindings, `Ctrl+Z → undo`), and add-on surface (`bl_info` + `register`/`unregister`). `blender_host.py` + `blender_addon.py` folded in & deleted. |
| [tcl_maya.py](../tentacle/tcl_maya.py) | Complete reference. |
| `tentacle/slots/blender/` | **Does not exist.** |
| [slots/maya/](../tentacle/slots/maya/) | ~60 files reference impl. |
| [slots/_slots.py](../tentacle/slots/_slots.py) → `Slots(QObject)` | DCC-agnostic base (exists). |
| [slots/maya/_slots_maya.py](../tentacle/slots/maya/_slots_maya.py) → `SlotsMaya(Slots)` | Trivial pass-through. |
| Shared UI `tentacle/ui/*.ui` | **60 `.ui` ≈ 29 domains** — the REAL port checklist / coverage denominator. |
| Maya-only overlay `tentacle/ui/maya_menus/*.ui` | **33 overlays Blender never loads.** |
| [maya_ui_handler.py](../../mayatk/mayatk/ui_utils/maya_ui_handler.py) → `MayaUiHandler` | Template **only if** blendertk later ships co-located tool panels — **not needed for MVP** (see Validated architecture). |
| **blendertk** | **Greenfield** — GitHub repo empty, not checked out in monorepo. |

**Key free win — UI layering hides whole Maya-only menus for nothing.** Maya loads
`ui_source=("ui", "ui/maya_menus")`; Blender will load `("ui", "ui/blender_menus")` and simply
*never* layer `maya_menus/`. So the 33 Maya-only menus (arnold, mash, ncloth, nhair, fluids,
stereo, toon, …) disappear from Blender with **zero `requires` tags**. The visibility mechanisms
(Phase 5) only need to handle widget-level differences *inside* the 29 shared menus.

**Qt host — SPIKED & LARGELY DE-RISKED (2026-06-11).** Blender is not a Qt app (GHOST loop,
ships no PySide6), but the make-or-break question is answered: on the actual machine
(**Blender 5.1.2 / Python 3.13.9**, not the 4.x/3.11 the plan first assumed) a uitk Qt UI
**renders and processes events over live GUI Blender via a plain `bpy.app.timers` event pump —
no bqt required.** Proven end-to-end (see `_blender_spike` recipe in memory):
- PySide6 **6.11.1** (stable-ABI `abi3` wheels) + qtpy install into Blender's py3.13 via
  `pip install --target <dir>` (admin-free, off the synced O: drive); the whole chain
  (PySide6 → qtpy → pythontk → uitk → `MarkingMenu`) imports with **zero code changes**.
- A real shared tentacle `.ui` (`selection.ui`) loads through a uitk `Switchboard` with **all
  custom widgets promoted + styled** (`Header`, `CollapsableGroup`, `ComboBox`, `Footer`,
  `ProgressBar`, `CornerSizeGrip`); `main#startmenu.ui` promotes **12 `MenuButton`s** with their
  `target` routing + `class=MenuButton` QSS prop intact.

**Remaining Qt-host unknowns (narrowed, lower risk):** (a) real **OS input routing** to the Qt
window — a synthetic click worked; it's a genuine top-level Win32 window so the OS should route
input natively, but confirm interactively; (b) **parenting** to Blender's window (`blender_widget`)
for correct popup z-order/modality — a top-level window already works, bqt-style HWND wrapping is
a refinement; (c) **global activation hotkey** — still almost certainly a Blender **add-on keymap
operator** calling `show()` (GHOST consumes keys before Qt; F12 collides with Render);
(d) marking-menu **sizing** (`fit_to_window`) when shown outside the handler path.

**Key maintainability debt — the structural tests are hardcoded to Maya.** Four files pin a
module-level `SLOTS_DIR = PKG / "slots" / "maya"` (two also pin `maya_menus`), so they would
**silently never cover Blender**: [test_slot_integrity.py](../test/test_slot_integrity.py),
[test_ui_integrity.py](../test/test_ui_integrity.py),
[test_slot_method_coverage.py](../test/test_slot_method_coverage.py),
[test/slots/_helpers.py](../test/slots/_helpers.py). See M1.

### Validated architecture (confirmed in code 2026-06-11)

Checked against the source so the plan doesn't over-build:

- **A working launcher needs no custom UI handler.** `MarkingMenu` carries a class-default
  `HANDLERS = {"ui": UiHandler}`; passing no `handlers` yields a functional generic handler that
  serves the shared menu `.ui` via `ui_source`. `tcl_maya` *overrides* it with `MayaUiHandler`;
  [tcl_max.py](../tentacle/tcl_max.py) (the other non-Maya DCC) passes **no handler at all**.
  → **`BlenderUiHandler` is deferred, not MVP** (see Phase 2).
- **`MayaUiHandler` is mostly Maya-only.** Beyond a thin base-`UiHandler` config (discovery rooted
  at the *mayatk package dir* for co-located tool panels), its substance is wrapping **live Maya
  native menus** into Qt (`_load_maya_ui` / `MayaNativeMenus`) — no required Blender analogue. Do
  **not** replicate that for Blender at MVP.
- **The shared `.ui` files are structurally DCC-neutral.** Maya-specific content (menu items,
  option-box spinboxes/checkboxes) is built in the slot's `*_init` methods, **not** in the `.ui`.
  → a Blender slot must reimplement the same `tb###_init` option-box trees (matching widget
  objectNames) too, not just the top-level widget methods.
- **Slot↔UI pairing is by file basename** (`selection.ui` ↔ `selection.py`), enforced by
  `test_ui_integrity`; the slot *class name* is irrelevant to resolution (M4).
- **`tcl_max` is the structural template for `tcl_blender`** — wrapper-only, `ui_source="ui"`, no
  handler/bindings. The *only* Blender-specific delta is the Qt host (Max is already Qt; Blender
  is not → Phase 0).

---

## 3. Phases (renumbered — riskiest first)

### Phase 0 — Qt-in-Blender host spike — ✅ **CORE PROVEN** (2026-06-11)
Prove tentacle's Qt UI can live over a running Blender *before* investing in scaffold.
- [x] PySide6 into Blender's bundled Python — **done**: PySide6 6.11.1 `abi3` + qtpy via
      `pip install --target` on Blender 5.1.2 / py3.13.9; full chain imports unchanged.
- [x] Pump vs bqt — **done**: a `bpy.app.timers` `processEvents` pump works; **bqt not needed**
      for rendering/events.
- [x] uitk widget + real `.ui` over live Blender — **done**: `selection.ui` (custom widgets
      promoted + styled) and `main#startmenu.ui` (12 `MenuButton`s with `target` routing).
- [x] **Global activation** — ✅ **SHIPPED (2026-06-12), Maya-parity install:** the activation key is
      wired **automatically by `TclBlender.__init__`** — the Blender analogue of MarkingMenu's
      `QShortcut` (which fires app-wide in a Qt host like Maya but can't, since GHOST owns the keyboard).
      [tcl_blender.py](../tentacle/tcl_blender.py) `_install_keymap` registers operator
      `tentacle.show_marking_menu` (→ `tcl.show(ui_name)`) + a 3D-View keymap item from `key_show`
      (default `F12` → `main#startmenu`). So **constructing/`launch()`-ing TclBlender is all it takes**,
      exactly like instantiating `Tcl` in Maya — no separate add-on to enable. The host bootstrap
      (`launch()` = QApplication + `blender_widget` parent + `bpy.app.timers` pump) and the add-on
      surface (`bl_info` + `register`/`unregister` + `_bootstrap_paths`) are now **consolidated into
      [tcl_blender.py](../tentacle/tcl_blender.py)** (one entry point; `blender_host.py` + `blender_addon.py`
      folded in & deleted 2026-06-12). A startup snippet `from tentacle import tcl_blender; tcl_blender.register()`
      (≈ Maya `userSetup.py`) is all an install needs. **Qt provisioning** is automatic & asymmetric:
      Maya bundles PySide6 (used as-is — tentacle/uitk pyproject exclude qtpy/PySide from deps so pip
      never touches it); Blender's Qt-less Python gets PySide6 + qtpy **pip-installed on first launch**
      (`_ensure_qt`, gated on `import bpy`; `TENTACLE_QT_DEPS` skips the download with a pre-staged folder).
      **F12 collision resolved** (kept for Maya-parity): `_install_keymap` deactivates the bare-F12
      `render.render` item in the dispatched keyconfig (`user`/`active`, not just `default`) so tentacle
      wins, restoring it on `unregister` (modified combos untouched; a deferred one-shot re-mute covers
      early-startup timing). Key translation is alias-mapped (`Key_Meta`→`OSKEY` etc.) so the key is
      freely reconfigurable. Verified headless 19/19
      (`phase0_addon_test.py`: key-translate inc. special keys / register / keymap / mute+restore /
      activation-routes-to-show / re-install-safe / error-report / no-active-menu / teardown / host+add-on
      fns). *(in-menu L/M/R nav bindings are Qt-internal.)*
- [x] **Native z-order parenting** — ✅ SHIPPED (2026-06-12): the overlay is **transient-parented
      to Blender's GHOST window** (`blender_native_window()` wraps the `GHOST_WindowClass` HWND as
      a foreign `QWindow`; `TclBlender.__init__` sets it as the menu's transient parent — an OS
      "owned window", stacked above Blender natively). Light-touch by design — NO bqt-style
      `createWindowContainer` reparenting (which would take ownership of the GHOST window);
      best-effort with full fallback to the proven top-level behavior off-Windows/on failure.
- [x] **Real OS input routing** — ✅ VERIFIED CONCLUSIVELY (2026-06-12) via
      [test/blender/gui_keypress_check.py](../test/blender/gui_keypress_check.py): the keymap is
      pointed at a **stub** (the real overlay is always-visible + focus-grabbing, so `isVisible()`
      was a false-positive signal), the GHOST window is forced foreground (injected-Alt +
      `SetForegroundWindow` — Windows denies foreground to background-launched processes), the
      cursor parks over the viewport, and a **real scancode F12** is injected: **OUR KEYMAP WINS**
      (`operator_fired=True`, `show('main#startmenu')` recorded, render did NOT fire) — the
      viewport-scoped `3D View` item genuinely beats the `Screen` render shortcut. Sizing +
      transient-parent confirmed in the same-day live runs (overlay exactly fills the screen it
      opened on; owned by the GHOST window). **Phase 0 COMPLETE.**
- [x] Delivery decided: **single-file entry point** (`tcl_blender.py` carries `bl_info` +
      `register`/`unregister`; startup-snippet, Run-Script, or Install-from-file when loaded from its
      package location).
- **Done when:** ✅ the marking menu opens over live Blender from an activation gesture (wired + verified;
  awaiting the user's literal keypress confirmation).
- **Output:** the `_blender_spike` recipe (in memory) is the seed for the Phase-2 `tcl_blender`
  host bootstrap (path setup + QApplication + timer pump).

### Phase 1 — `blendertk` scaffold
### Phase 1 — `blendertk` scaffold — ✅ **DONE & TESTED** (2026-06-11)
- [x] Package created at `o:/Cloud/Code/_scripts/blendertk/` with `pyproject.toml` (mirrors
      mayatk; deps `pythontk` only — `bpy` is the runtime; `uitk` deferred to BlenderUiHandler).
- [x] `bootstrap_package(globals(), include=DEFAULT_INCLUDE)` mirroring mayatk; subpackage
      `__init__.py` = docstring only; **`import bpy` deferred into call bodies** (no side effects).
- [x] Starter helpers (grounded, not speculative): `core_utils` → `undoable` (single Blender
      undo step) + `get_env_info` (scene/env). Exposed module-level **and** on `CoreUtils` via the
      list-form include `["CoreUtils", "undoable", "get_env_info"]` (mayatk's `["SmartBake",
      "smart_bake"]` pattern). More helpers grow lazily per slice (§5).
- [x] `blendertk/CLAUDE.md` (session-safety, mirror-mayatk/don't-reinvent design, `bpy`/`bmesh`
      conventions) + `docs/README.md` + `CHANGELOG.md`.
- [x] **Headless harness:** `test/blender_smoke_test.py` runs under `blender --background
      --factory-startup --python` (fresh instance). **All checks PASS** on Blender 5.1.2:
      `import blendertk`, `btk.undoable`/`btk.get_env_info`/`btk.CoreUtils` resolve,
      `get_env_info('blenderVersion')` → `5.1.2`, `undoable` wraps/runs/pushes-undo.
- [ ] *(Deferred)* API registry (M3) + wire into the push.ps1 cascade (M7) — once the surface
      is real (3 symbols today); git-wire the empty `m3trik/blendertk` remote when publishing.
- **Done when:** ✅ `import blendertk as btk` works in Blender's Python and `btk.<X>` resolves.

### Phase 2 — tentacle plumbing — ✅ **DONE & TESTED LIVE** (2026-06-11)
- [x] [tcl_blender.py](../tentacle/tcl_blender.py) fleshed out: `ui_source=("ui",
      "ui/blender_menus")`, `slot_source="slots/blender"`, bindings (mirror tcl_maya),
      `log_level="WARNING"`, **no custom handler** (default `UiHandler` serves the shared menus),
      robust `get_main_window` (returns `blender_widget` or `None`, never raises).
- [x] Host bootstrap (`launch()` = QApplication + `blender_widget` parent + `bpy.app.timers` pump +
      `TclBlender`) productized from the Phase-0 recipe — **consolidated into `tcl_blender.py`**
      (was `blender_host.py`, folded in 2026-06-12).
- [x] `slots/blender/__init__.py` + `_slots_blender.py` (`SlotsBlender(Slots)`); `ui/blender_menus/`
      (README placeholder, empty by design).
- [x] **M1 (focused):** [test_blender_slots.py](../test/test_blender_slots.py) guards the package
      + `SlotsBlender` base + launcher parse + carries the DCC-agnostic slot invariants
      (one-base-subclass, unique objectNames) ready for Phase 3. 6 tests pass in `.venv`.
- [x] **PROVEN LIVE:** `host.launch()` constructs `TclBlender` in Blender 5.1.2, establishes
      `blender_widget`, and `tcl.show("main#startmenu")` renders the real marking menu (12
      MenuButtons, radial layout, styled) over live Blender. Screenshot captured.
- [ ] *(Deferred)* `BlenderUiHandler` (only when blendertk ships co-located tool panels — not MVP).
- **Done when:** ✅ `TclBlender()` launches in Blender and shows the shared menus.

### Phase 3 — first vertical slice: **`selection`** — ✅ **DONE & TESTED LIVE** (2026-06-11)
`select.py` is a thin Maya header stub and `select#submenu.ui` is Maya-only; the fleshed-out
*shared* domain is `selection` / `selection.ui`.
- [x] [slots/blender/selection.py](../tentacle/slots/blender/selection.py) — `Selection(SlotsBlender)`
      implementing `selection.ui` widget names against native `bpy.ops` (+ option-box `_init`s).
      Clean-mapping widgets done: tb000 (Nth: loop/ring/border/shortest), tb001 (Similar →
      `select_similar`/`select_grouped`), tb002 (Island → `select_linked`), tb003 (By Angle →
      `edges_select_sharp`), cmb003 (Convert → `select_mode`), chk004 (backface→xray),
      chk005-007 (style → `wm.tool_set` box/lasso/circle), b001 (selectability → `hide_select`).
      Maya-tool-specific deferred with a message: cmb001 (reorder), cmb005 (dR_ constraints),
      list000 (type list).
- [x] **blendertk grew by ~zero** — validates the §5 thesis: selection is **all native bpy.ops**;
      only `btk.undoable` is used (on `b001`). No new btk helpers needed.
- [x] **Tested live (GUI Blender, against geometry):** tb003 selects all 12 cube edges, tb002
      grows island to 6 faces, cmb003 'Verts' sets VERT mode, b001 toggles `hide_select` — 4/4.
- [x] **End-to-end auto-connection PROVEN:** `tcl.show("selection")` → switchboard discovers +
      wires a `Selection` slot instance; `tb003`/`tb002`/`cmb003` present + `call_slot`-wired;
      slot `__init__` (`loaded_ui.selection` + `selection_submenu`) loads both UIs cleanly.
- [x] **Resolved the bpy.ops-context unknown:** `bpy.ops.mesh.*` work **directly from the Qt
      event pump** (a `VIEW_3D` area is present; `temp_override` also available) — no mandatory
      context-override helper (YAGNI; add only if a real failure appears). NOTE: op-based slot
      logic can't be unit-tested headless (no viewport) → Blender slot tests are GUI-based.
- [x] `test_blender_slots.py` invariants now genuinely cover `selection.py` (6 pass).
- **Done when:** ✅ the `selection` menu loads, auto-connects, and its core widgets perform real
  Blender actions live.

### Phase 4 — port the tiers — ✅ **COMPLETE (2026-06-12): 100% of the 238-widget shared surface**
Every shared domain now has a Blender slot — implemented, deferred-with-message, or
hidden-via-`_init` (the [DCC_COVERAGE.md](DCC_COVERAGE.md) handled-predicate): full EASY tier
(incl. the straggler **`polygons`** — native edit-mode ops via `_edit_op` on the user's component
selection; boolean via new `btk.boolean_op`), full NAV-APP (incl. **`hud`** — shared
`slots/_hud_warnings.py` framework extracted from Maya, dense-safe numpy poly counts,
`total_*_sel` component counts; **`editors`** — `btk.open_editor` new-window `ui_type` switch,
22 curated editors; **`utilities`** — builtin measure/annotate tools), and the full **MEDIUM
tier** (`scene` recent-files/autosave/import-export, `materials` via new `btk.mat_utils`,
`rendering` camera/playblast/render, `animation` via new `btk.anim_utils` fcurve key-timing
math — **5.x gotcha: legacy `Action.fcurves` is GONE (slotted/layered actions); resolve via
`layers → strips → channelbag(slot)`** — `lighting`/`deformation` deferred launchers,
`rigging` (mirror relaxed: Empties-as-locators, `show_axis`, transform locks), `nurbs`
(largely hide; curve-bevel + Screw map cleanly)). blendertk = 9 util modules. Original
tier/order notes follow for reference.

- [x] **`transform`** (EASY) — ✅ DONE & TESTED (2026-06-11).
      [slots/blender/transform.py](../tentacle/slots/blender/transform.py) = `TransformSlots`:
      tb000 Drop-To-Grid, tb002 Freeze, tb005 Move-To, b001 Match-Scale → backed by new
      **`blendertk.xform_utils`** (`freeze_transforms`/`drop_to_grid`/`match_scale`/`move_to`/
      `get_world_bbox`, mirroring mtk). Deferred (no Blender analogue): tb001 scale-connected-edges,
      b002 un-freeze, cmb002 align, tb003 constraints, tb004 snap, chk023-025.
      **Two findings:** (1) the EASY tier is **not** uniformly native-bpy — `transform` genuinely
      **grows blendertk** (object-transform logic), unlike `selection` (grew it by zero). (2) those
      xform helpers operate on `obj.location`/`matrix`/`scale` (no viewport) so they're
      **headless-testable** — `test_xform_utils.py` (5/5) + the slot itself headless (5/5), vs
      selection's GUI-only ops. Gotcha fixed: set `obj.location` then `view_layer.update()` before
      reading `matrix_world` (else stale). `test_blender_slots.py` now covers transform.py (6 pass).
- [x] **`pivot`** (EASY) — ✅ DONE & TESTED (2026-06-11).
      [slots/blender/pivot.py](../tentacle/slots/blender/pivot.py) = `Pivot`: tb000 Reset-Pivot,
      tb001 Center-Pivot (Component/Object/World radio), b000/b001/b002 shortcuts → backed by new
      **`btk.center_pivot`** (`bpy.ops.object.origin_set` BOUNDS/MEDIAN/CURSOR-world) + `get_pivot_modes`.
      Headless-testable like transform (origin ops need no viewport): `test_xform_utils.py` now 9/9,
      slot headless 5/5 (incl. a 3D-cursor-restore guard — world mode borrows then restores the
      scene cursor). **Divergence honored:** Blender has one baked object origin → deferred the
      Maya-only concepts with honest messages — tb002 Transfer-Pivot (per-channel translate/rotate/
      scale), tb003 World-Aligned manip pivot, b004 Bake-Pivot (no-op: origins always baked).
      **Two reusable patterns landed in the critique (apply to all future object-operator domains):**
      (1) `blendertk._object_mode` decorator — object operators (`origin_set`, `transform_apply`)
      *require* OBJECT mode and raise from a component/edit context (verified: `origin_set` →
      RuntimeError in edit mode), but Center-Pivot's *Component* option is naturally invoked from
      edit mode. The decorator runs the helper in OBJECT mode and restores the caller's prior mode;
      now wraps `center_pivot`/`freeze_transforms`/`drop_to_grid`. (2) `SlotsBlender.selected_objects()`
      shared base helper replaces the `[o for o in (bpy.context.selected_objects or []) if o]` filter
      duplicated across pivot + transform slots.
- [x] **`duplicate`** (EASY) — ✅ DONE & TESTED (2026-06-11).
      [slots/blender/duplicate.py](../tentacle/slots/blender/duplicate.py) = `Duplicate`: tb000
      Convert-to-Instances, tb001 Select-Instanced, b005 Uninstance → backed by NEW
      **`blendertk.node_utils`** (`replace_with_instances`/`get_instances`/`uninstance`, mirroring
      mtk's `node_utils`). **Model mapping:** Maya instances (transforms sharing one shape) →
      Blender **linked duplicates** (objects sharing one `obj.data`); convert = `t.data = source.data`,
      select-instanced = `data.users > 1`, uninstance = `data.copy()`. Source = the **active** object
      (Blender's Ctrl+L Link-Object-Data convention), so the slot reorders `[active, *targets]`.
      Headless-testable (datablock refs, no viewport): `test_node_utils.py` 18/18 + slot headless 7/7.
      `delete_history` flag kept for signature parity but is a documented no-op (Blender has no
      construction history). Deferred (separate unported menus): b000 Mirror, b006/b007/b008
      Duplicate-Linear/Radial/Grid.
      **Two correctness fixes from the critique (Blender datablock gotchas):** (1) instance detection
      counts *object* users (one pass via `Counter(o.data …)`), NOT `data.users` — the latter also
      counts fake users / other-datablock refs, so a 1-object mesh with `use_fake_user` would
      false-positive. (2) `replace_with_instances` pre-cleans (`center_pivot`/`freeze_transforms`)
      the **source only** — a target's data is discarded when it adopts the source's, and freezing a
      target would zero its location, *relocating it to the origin* instead of leaving it in place.
- [x] **`cameras`** (EASY) — ✅ DONE & TESTED (2026-06-12).
      [slots/blender/cameras.py](../tentacle/slots/blender/cameras.py) = `Cameras`. list000 Create/
      Select/Clip-options + b004 persp toggle backed by NEW **`blendertk.cam_utils.adjust_camera_clipping`**
      (auto from scene-bbox vs camera pos: far=dist×1.2, near=far/3000 floored 0.1; reset=0.1/1000 —
      mirrors mtk). Standard views b000-b006 → `view3d.view_axis` under an explicit VIEW_3D context
      override (`_view3d_context()` — viewport ops are region-centric and the Qt menu isn't the active
      area; **GUI-only**, can't headless-test). Headless-tested: `test_cam_utils.py` 9/9 + list000 slot
      7/7. Deferred (Maya-specific): per-camera exclusive/hidden visibility (Blender uses collections/
      holdout), b007 align-to-poly, b010-b013 dolly/roll/truck/orbit (Blender viewport nav is modal,
      not a persistent tool). `toggle_camera_view` double-click ported (DCC-agnostic switchboard logic).
- [x] **`subdivision`** (EASY) — ✅ DONE & TESTED (2026-06-12).
      [slots/blender/subdivision.py](../tentacle/slots/blender/subdivision.py) = `Subdivision` →
      NEW **`blendertk.edit_utils`** (`decimate`/`dissolve_coplanar` via Decimate modifier mirroring
      `mtk.EditUtils`; `triangulate`/`tris_to_quads`/`subdivide_mesh` via bmesh; `set_subdivision`
      = live Subsurf modifier for smooth-preview + division/tess levels). All headless-testable
      (modifiers + bmesh, no viewport): `test_edit_utils.py` 16/16 + slot 9/9. Deferred: b028 Quad-Draw
      (modal retopo), cmb001 Smooth-Proxy (Blender uses live Subsurf), cmb002 option dialogs.
      **Refactor:** promoted the `_object_mode` guard from `xform_utils` → **`core_utils`** (now shared
      by xform + edit utils — `modifier_apply` and bmesh `to_mesh` both need OBJECT mode; the latter
      gets clobbered if written while the object is in edit mode). bmesh helpers loop via `_bmesh_each`.
- [x] **`display`** (EASY) — ✅ DONE & TESTED (2026-06-12).
      [slots/blender/display.py](../tentacle/slots/blender/display.py) = `DisplaySlots`. Widget surface
      is just list000 + b013/b014 (the Maya `b0xx` are internal list handlers). list000 curated to the
      object-property toggles that map cleanly: visibility (`hide_set`), wireframe (`display_type`),
      see-through (`show_in_front`). Headless-tested 10/10. **No blendertk helper** (trivial slot-level
      property toggles, no `undoable` — non-destructive view state). Omitted (Maya modelEditor/
      textureWindow editor state, no per-object Blender analogue): component-ID, material-override,
      wireframe-on-inactive, UV-editor displays, normal overlays, template, wireframe-color palette.
      Deferred: b013 Explode-View, b014 Color-Manager (unported sub-windows).
- [x] **`symmetry`** (EASY) — ✅ DONE & TESTED (2026-06-12).
      [slots/blender/symmetry.py](../tentacle/slots/blender/symmetry.py) = `Symmetry`. Maya
      `symmetricModelling` → Blender per-mesh flags `mesh.use_mirror_x/y/z` (chk000-2 radio) +
      `use_mirror_topology` (chk005), applied to selected mesh(es); chk000_init reflects the active
      mesh. Mesh-data props → headless-tested 9/9. No blendertk helper (trivial property toggles).
- [x] **`normals`** (EASY) — ✅ DONE & TESTED (2026-06-12).
      [slots/blender/normals.py](../tentacle/slots/blender/normals.py) = `Normals` → extended
      **`blendertk.edit_utils`** with `set_shading`/`set_edge_hardness`/`flip_normals`/
      `recalculate_normals` (bmesh, reuse `_bmesh_each`/`_object_mode`). b000 soften / b001 harden /
      b006 set-to-face = smooth vs flat shading; tb001 set-by-angle marks sharp edges (Blender split
      normals follow them automatically in 4.1+); tb004 average = smooth shading; tb010 Flip/Recalc
      Outside/Inside. Headless-tested: edit_utils +8 cases + slot 9/9. Deferred: b002 Transfer-Normals
      (Data-Transfer custom-normal setup), b004 lock/unlock vertex normals (no Blender analogue),
      tb004 by-UV-shell option.
- [x] **`crease`** (EASY) — ✅ DONE & TESTED (2026-06-12).
      [slots/blender/crease.py](../tentacle/slots/blender/crease.py) = `Crease` → `btk.crease_edges`
      (edit_utils). Maya edge crease → Blender Subsurf edge crease. **5.1 gotcha:** the bmesh crease
      layer moved — `bm.edges.layers.crease` is GONE; it's now `bm.edges.layers.float["crease_edge"]`
      (the `crease_edge` mesh attribute). `crease_edges` is **mode-aware (NOT `@_object_mode`)**: edit
      mode creases selected edges, object mode all edges; Maya 0–10 → Blender 0–1. Headless-tested both
      paths + slot 4/4. Deferred: b002 transfer-crease, Maya smoothing-angle option (no Blender analogue).
- [x] **`uv`** (EASY, partial) — ✅ DONE & TESTED (2026-06-12).
      [slots/blender/uv.py](../tentacle/slots/blender/uv.py) = `Uv`. **Finding:** `bpy.ops.uv.*`
      (smart_project/unwrap/pack/cylinder_project) + `mesh.mark_seam` all run **headless from edit
      mode** (no UV editor area needed). Core ops via `_uv_op` (enter edit, select-all, run, restore
      mode); seam cut/sew via `_seam_op` (selection-based — does NOT select-all, requires edit mode).
      Move-to-UV-space + cleanup-UV-sets via NEW **`blendertk.uv_utils`** (`move_uvs` mode-aware,
      `delete_extra_uv_sets`). Headless-tested: uv_utils 7/7 + slot 14/14. **Critique fix:** the
      whole-mesh select-all was wrong for Cut/Sew (marked all 12 cube edges instead of the 3 selected)
      → split into `_seam_op`. Deferred (UV-editor/Maya-specific): straighten, distribute, mirror,
      transfer, texel density, pin, stack/unstack, RizomUV, transform combos, open-UV-editor.
      uv_utils imports `_meshes`/`_bmesh_edit` from edit_utils (canonical mesh-bmesh infra home).
- [x] **`edit`** (EASY) — ✅ DONE & TESTED (2026-06-12). **EASY tier COMPLETE.**
      [slots/blender/edit.py](../tentacle/slots/blender/edit.py) = `Edit` → NEW
      **`blendertk.edit_utils.clean_geometry`** (bmesh: remove_doubles + dissolve_degenerate + delete
      loose wire/verts + recalc + optional fill-holes — the §5-predicted `Diagnostics.clean_geometry`
      btk helper). tb000 Mesh-Cleanup (options) + tb002 Delete-Selected (mode-aware: objects, then
      components **by select mode** — FACE/EDGE/VERT; an always-VERT delete in face mode also nuked
      neighboring faces). **Review pass (2026-06-12)** added list000 Create-Primitive
      (`bpy.ops.mesh.primitive_*`) + list001 Convert (`object.convert` Mesh/Curve) — previously dead
      shared-`.ui` widgets — and `clean_geometry` gained `merge=` (degenerate dissolve no longer
      silently disabled when merging is off). Headless-tested: edit_utils suite + durable harness
      [test/blender/edit_slot_check.py](../test/blender/edit_slot_check.py) 6/6. Deferred (no Blender
      analogue / Data-Transfer): tb001 delete-history (no construction history), tb004 node-lock,
      b000 axis-cut, b021/b022/b023 transfers, b027 shading-sets.
- [x] **NAV-APP `main`/`preferences`/`settings`** — ✅ DONE & TESTED (2026-06-12).
      `main` = workspace dir-browser (DCC-agnostic tree logic; added `workspace`/`workspace_dir` keys
      to `btk.get_env_info` = the saved `.blend` dir); tested 6/6. `preferences` = scene units
      (`unit_settings`), frame rate (`render.fps`), autosave (filepaths prefs: `save_version` /
      `auto_save_time` — note: NOT `save_version_count`), open-prefs buttons; tested 6/6. `settings` =
      DCC-agnostic uitk delegations (editors.show, reset bindings; live-reload deferred — Maya-specific
      mechanism); structural-covered.
- [x] **`hud`** — ✅ DONE (2026-06-12). Shared warning framework extracted to
      [slots/_hud_warnings.py](../tentacle/slots/_hud_warnings.py) (DCC subclasses supply checks);
      Blender HudSlots: symmetry-flag/workspace/units/fps status, dense-safe selection counts
      (numpy `foreach_get` — a Python per-poly loop would hang on photogrammetry meshes),
      edit-mode `total_*_sel` component counts, autosave/default-fps warnings. Harness 12/12;
      F12 default binding now `hud#startmenu` (Maya parity).
- [x] **`editors` + `utilities`** — ✅ DONE (2026-06-12). NEW `btk.ui_utils.open_editor`
      (new window + `Area.ui_type` switch; 22 curated editors — Maya relationship/XGen-style
      editors are simply absent); measure/annotate → builtin viewport tools; UI-chrome toggles
      honestly deferred. **NAV-APP tier COMPLETE.**
- [x] **MEDIUM tier** (scene/materials/lighting/rendering/animation/deformation/rigging/nurbs)
      — ✅ DONE (2026-06-12), see the Phase-4 header above. **+ `polygons`** (EASY straggler,
      27 widgets). Headless: `test_mat_anim_utils.py` 16/16, edit_utils suite incl. boolean,
      structural 9/9 incl. the cross-DCC semantic guard (caught a `chk007` label drift live).

### Phase 5 — visibility / coverage — ✅ **SHIPPED (2026-06-12)**
All three landed as uitk features, applied centrally at `MainWindow.register_widget` /
`connect_slot` (12 new uitk tests, `test_visibility_policy.py`; mainwindow 91/91 + switchboard
133/133 regression-clean):
- [x] **(1) Nav auto-hide:** `Switchboard.apply_visibility_policy` hides a `MenuButton` whose
      `target` doesn't resolve in the UI registry (`is_registered_ui` — exact-stem lookup, no
      load). Reason recorded on `widget.hidden_by_policy`.
- [x] **(2) `requires` tag:** Designer dynamic string property (`"maya"`, `"maya|blender"`;
      `|`/comma/space alternatives) checked against the switchboard's new `context_tags`
      (passed through `MarkingMenu`; `tcl_maya`={maya}, `tcl_blender`={blender},
      `tcl_max`={max}). Empty `context_tags` (standalone/dev) disables filtering.
- [x] **(3) Missing-slot policy hook:** `connect_slot`'s no-slot branch calls
      `notify_missing_slot` → the switchboard's `on_missing_slot` hook (default **None** = the
      old silent behavior, zero prod cost). `UITK_MARK_MISSING_SLOTS` env installs the built-in
      `mark_missing_slot` grey-out marker (live "not-yet-built" map). Only fires for
      signal-bearing widget types, never nav `MenuButton`s.
- [x] **(M5) Coverage report:** [generate_dcc_coverage.py](../../m3trik/scripts/generate_dcc_coverage.py)
      → [DCC_COVERAGE.md](DCC_COVERAGE.md) — per-domain handled-% per DCC + the exact
      missing-widget lists, from the same handled-predicate as the hook/M2 test (static AST/XML,
      headless). First run: Maya 99%, Blender 54% of the 238-widget shared surface.
      **2026-06-12 final: 100%/100%** — the last gaps closed (symmetry `chk004` in both DCCs —
      the Maya side was a real latent bug, `about` stayed "topo" after any Topo session; Maya
      `uv cmb003`/`s003` passive-input slots). Stubs deepened where the btk primitive existed
      (`uv b031` → `btk.open_editor`, `animation tb006` → new `btk.move_keys_to_frame`).
      **2026-06-12 stub-deepening batch**: 14 more deferred stubs became real (select-by-type,
      object-align, normal/UV Data-Transfer, target-weld toggle, texel density get/set, UV
      pin/transform/cut-hard-edges, key spacing/transfer/align/visibility-keys) — see the
      tentacle + blendertk CHANGELOGs. **Every Blender menu verified in a live GUI session**
      (`test/blender/menus_load_check.py`, 27/27 through the real `tcl.show()` path). Still
      deferred by design: external-addon (LoopTools), Maya-window (shot sequencer/manifest,
      Quick Rig, Render Opacity), modal-tool, and UV-editor-align-bound features.

---

## 4. Portability tiers (from the shared `ui/`, not the Maya slot list)

| Tier | Domains | Approach |
|:---|:---|:---|
| **NAV-APP** (port early — entry points) | hud, main, editors\*, preferences, settings, utilities, modify | Menu shells + app wiring; `hud`/`main`/`preferences`/`settings` are light (≈`get_env_info`). \* `editors` is a `mel.eval` Maya-editor dispatcher — **many entries HIDE** (no Blender analogue), rest map to Blender areas (rewrite). Startmenus hud/cameras/editors/main are **shared** (only `maya#startmenu` is Maya-only). |
| **EASY** | selection, transform, pivot, duplicate, **cameras**, display, polygons (+5 component submenus), subdivision, normals, uv, symmetry, crease, edit | Direct port; `bmesh` / `bpy.ops` analogues of mtk helpers. Mechanical once the slice is proven. (`cameras` is native camera/viewport props — moved here from MEDIUM.) |
| **MEDIUM** | materials, texturing, lighting, rendering, animation, deformation, **rigging**\*, **scene**†, **nurbs**‡ | Different data model (nodes, modifiers, armatures, Cycles/EEVEE) — see §5. \* `rigging` is the most divergent (skinCluster→Armature+vertex groups); relax the name mirror. † `scene` is **MIXED** — DCC-agnostic recent-files logic + Maya-only widgets to **hide** (command ports, OCIO). ‡ `nurbs` is **largely HIDE** — Blender lacks a Maya-grade NURBS/loft toolkit. |
| **HARD / HIDE — do not port** | (whole `maya_menus/`) arnold, mash, ncloth, nhair, nparticles, fields_solvers, fluids, stereo, toon, … | Maya-only; hidden **for free** by UI layering (Blender never loads `maya_menus/`). |

---

## 5. `blendertk` API surface — scope & capability map

Mirror the public **class/function names the slots call** (so `btk.Selection`, `btk.Components`,
`btk.Bevel` resolve like mayatk); group into subpackages naturally for Blender — don't slavishly
replicate mayatk's internal `*_utils` taxonomy or pre-create empty groups (YAGNI). Implement
lazily as slices demand.

### Design guardrail — blendertk wraps for naming + adaptation, NOT reimplementation

**Many mayatk helpers exist only because Maya's `cmds` API is low-level. Blender provides the
same capability as a single native operator.** So: *default to the native `bpy.ops` / `bmesh.ops`
/ object property; write blendertk logic ONLY where Blender has no native equivalent.* A btk
helper's job is usually to give the native op a mayatk-mirrored name + adapt args/selection
context — not to re-derive the algorithm.

### Capability map (grounded in the actual `mtk.*` calls in the EASY-tier slots)

**A — Native in Blender → slot calls `bpy` directly or btk is a ~1-line passthrough** (confirm
exact operator names against the target Blender 5.x API — a few were renamed historically):

| mayatk helper (Maya hand-rolled) | Blender native |
|:---|:---|
| `Components.get_edge_path` / `get_shortest_path` | `bpy.ops.mesh.shortest_path_select` / `shortest_path_pick` |
| `Components.get_faces_with_similar_normals` | `bpy.ops.mesh.select_similar(type='NORMAL')` |
| `Components.get_edges_by_normal_angle` | `bpy.ops.mesh.edges_select_sharp` |
| `Components.get_contiguous_islands` / `get_border_components` | `select_linked` / `region_to_loop` (bmesh `edge.is_boundary`) |
| `Components.bridge_connected_edges` | `bpy.ops.mesh.bridge_edge_loops` |
| `EditUtils.dissolve_coplanar` | `bpy.ops.mesh.dissolve_limited` |
| `EditUtils.decimate` | Decimate modifier |
| `EditUtils.combine_objects` / `separate_objects` / `detach_components` | `bpy.ops.object.join` / `bpy.ops.mesh.separate` |
| `Macros.m_boolean` | Boolean modifier |
| `merge_vertices` | `bpy.ops.mesh.remove_doubles` (merge by distance) |
| `Components.average_normals` / `set_edge_hardness` | `average_normals` / `normals_make_consistent` / `mark_sharp` / `shade_smooth` |
| `Components.transfer_normals` / `transfer_uvs` | `bpy.ops.object.data_transfer` |
| `UvUtils.unwrap_cylinder` (+ planar/sphere) | `bpy.ops.uv.cylinder_project` (+ `cube`/`sphere_project`, `smart_project`) |
| `freeze_transforms` / `drop_to_grid` | `transform_apply` / bbox-min + move |
| `NodeUtils.get_parent` / `set_visibility` / `Macros.m_toggle_selectability` | `object.parent` / `hide_set` / `hide_select` (native props) |
| `Macros.m_wireframe/normals/soft_edge/material_override` toggles | `space_data.overlay.*` / `shading.*` booleans |
| `Primitives.create_default_primitive` | `bpy.ops.mesh.primitive_*` |
| `Attributes.set_attributes` | direct python attribute assignment — **no wrapper** |

**B — Genuine blendertk logic (no native equivalent / custom orchestration → real work):**

| mayatk helper | Why it needs btk |
|:---|:---|
| `Diagnostics.clean_geometry` / `cleanup_uv_sets` | orchestration of several bmesh ops + reporting — no single native "clean" |
| `get_texel_density` / `set` / `calculate_uv_padding` | custom math — or **wrap the TexTools addon, don't rebuild** |
| pivot suite — `transfer_pivot` / `world_align_pivot` / `bake_pivot` | Blender's origin + 3D-cursor model differs → adapter logic over `origin_set` / `transform_apply` |
| `get_similar_mesh` / `get_overlapping_duplicates` / `get_overlapping_faces` | custom geometric analysis (`find_doubles` only covers part) |
| `transfer_creased_edges` / `scale_connected_edges` | custom |
| `undoable` | thin decorator over `bpy.ops.ed.undo_push` — **cross-cutting, needed by nearly every slot → build first** |
| `map_components_to_objects` | likely **N/A** — bmesh is already per-object; drop, don't port |

**Scope implication:** blendertk ≈ a small adapter surface over native operators **+ ~6–8 real
helpers** (clean-geometry, texel density, pivot adaptation, similarity/overlap analysis, the
`undoable` decorator) — **not** a mayatk-sized reimplementation. The EASY tier is lighter than
it looks. **Reference, don't rebuild:** community addons already solve some of this (TexTools for
texel density/UV; the bundled Bool Tool) — learn from / optionally wrap them, but weigh
license + coupling before vendoring.

### MEDIUM tier — where Maya and Blender concepts diverge (grounded in those slots' `mtk.*`)

Here the EASY pattern (thin adapter over a native op) breaks down: the *data models* differ.
Three outcomes per helper:

- **Maps fine** (assignment / query / native props): materials get/assign/create
  (`bpy.data.materials`, `material_slots`), texture-path queries (walk shader-node image nodes),
  camera clip/active (`camera.data.clip_*`, `scene.camera`), most animation key ops
  (`scene.frame_set`, `bpy.ops.graph.*` copy/paste/snap/scale), render settings
  (`scene.render` / `scene.cycles`).
- **Divergent → relax the name mirror, use Blender-idiomatic names** (no clean Maya↔Blender
  concept map): `rebind_skin_clusters` (skinCluster → Armature modifier + vertex groups),
  `connect_switch_to_constraint` (IK/FK → bone constraints), `graph_materials` / `find_by_mat_id`
  (shading network → shader nodes), `loft` / NURBS surfaces (Blender has no Maya-grade NURBS/loft).
- **Hide (Maya-only widget)**: `MayaConnection.toggle_command_ports` (no Blender command port);
  `fix_ocio` / color-space repair (Blender has its own color management).

**Animation is large but mechanically portable:** the bulk (`stagger_keys`, `optimize_keys`,
`invert_keys`, intermediate-key insert/remove, `adjust_key_spacing`) is **key-timing math, not
Maya-specific** — it ports almost directly onto `fcurve.keyframe_points`. Volume, not difficulty.

### Two cross-cutting findings

- **NAV-APP coupling is uneven — and "no `mtk.*`" ≠ DCC-agnostic.** `editors.py` and
  `utilities.py` make zero `mtk.*` calls but reach **straight into `mel.eval` / `cmds`**:
  `editors.py` is a Maya-editor dispatcher (`HypershadeWindow`, `GraphEditor`, `Trax`, `HumanIK`,
  `XGen`, light-linking, …) — many entries have **no Blender analogue → HIDE**, the rest map to
  Blender editors/areas via different calls (rewrite, not free); `utilities.py` (measure /
  annotate / grease pencil) maps to **Blender-native** tools but via different calls. By contrast
  `hud` / `main` / `preferences` / `settings` are light — essentially one `btk.get_env_info()`
  (scene name, units, fps) + unit values. **Methodology caveat:** grepping `mtk.*` alone
  *understates* Maya coupling — slots that bypass mayatk and call `mel` / `cmds` directly are the
  most Maya-bound. The §5 maps cover the **mtk-routed** surface; per-domain there is additional
  direct `cmds` / `mel` to assess (in the EASY tier it mostly maps to the same native ops, e.g.
  `cmds.polyBevel` → `bmesh.ops.bevel`).
- **Before reimplementing a mayatk helper in blendertk, check if it belongs in `pythontk`.**
  Several "custom" helpers are pure logic over normalized data, not Maya calls: the HTML
  formatters (`format_mat_info_html`, `format_texture_info_html`, `format_audit_html`),
  recent-files / autosave-pattern file logic, key-timing math. Per the repo's SSoT/DRY goal,
  prefer extracting these to `pythontk` (shared) with thin DCC adapters over duplicating them in
  blendertk — **check the pythontk API registry first.**

### Starter subset (Phase 1)

| mayatk (mirror the name) | Blender backing |
|:---|:---|
| `core_utils` — `Components` | `bpy.context.selected_objects`, `bmesh` select history |
| `edit_utils` — `Selection`, `Bevel`, `Bridge`, `Duplicate*`, `Mirror`, primitives | `bmesh.ops.*`, `bpy.ops.mesh.*`, array/mirror modifiers |
| `xform_utils` — matrices, translation, pivot | `object.matrix_world`, `object.location`, 3D-cursor pivot |
| `core_utils` — `undoable` | `bpy.ops.ed.undo_push` (build first — cross-cutting) |

---

## 6. Maintainability — build these in, don't bolt on later

| # | Lever | Why it matters | Effort |
|:--|:---|:---|:--|
| **M1** | **DCC-coverage for the structural tests — ✅ COMPLETE (2026-06-12).** The DCC-agnostic invariants (package/base wiring, exactly-one-base-subclass, unique objectNames) now live ONCE in the parametrized [test_dcc_invariants.py](../test/test_dcc_invariants.py) (`DCCS = {maya: SlotsMaya, blender: SlotsBlender}` — a new DCC is one entry); the per-DCC files keep only what is genuinely DCC-specific ([test_slot_integrity.py](../test/test_slot_integrity.py): pymel ban + cmds perf; [test_blender_slots.py](../test/test_blender_slots.py): launcher/add-on surface, cross-DCC objectName semantics, the M2 contract). | Blender slots get structural CI coverage as they land. | S |
| **M2** | **Shared-UI contract test.** For each shared domain, assert the Blender slot implements the same widget-named methods the Maya slot does — or the widget is explicitly hidden (Phase 5). | This is the real safety net for contract #1; catches a renamed/dropped widget that would otherwise be a silent dead button. | S–M |
| **M3** | **`blendertk` API registry from day one.** Wire it into [generate_api_registry.py](../../m3trik/scripts/generate_api_registry.py) + the shadow report. | Enforces the name-mirror, surfaces drift vs. mayatk, prevents DRY violations (re-implementing an upstream pythontk helper). | S |
| **M4** | **Pick one slot-class naming convention for blender.** Maya is mixed (≈half bare `Selection`/`Transform`, half `PolygonsSlots`/`SceneSlots`); resolution is by class-not-name so it's cosmetic, but mirror the Maya counterpart's name per domain for grep-ability. | Low-stakes polish, but cheap to get right at greenfield and annoying to retrofit. | S |
| **M5** | **Headless coverage report** driven by the *same* predicate as the Phase-5 disable hook → a generated "what % of each DCC is built" artifact. | Turns "what's supported" from tribal knowledge into a living, regenerable doc. | M |
| **M6** | **Keep blendertk lean / zero import side-effects** (mirror mayatk: docstring-only subpackage `__init__`, register via root `DEFAULT_INCLUDE`). | Architectural guardrail — import side effects in a DCC package block the UI for seconds at startup. | — (discipline) |
| **M7** | **blendertk joins the release cascade.** Add to `m3trik/push.ps1` ecosystem packages so dep-sync + PyPI guard cover it (`pythontk → blendertk → tentacle`). | Keeps the new layer in the same guarded release flow as the rest of the chain. | S |

---

## 7. Difficulty rating & recommended order

Effort = build cost (S/M/L/XL). Risk = uncertainty / chance of blowing up. **Order is
risk-driven, not effort-driven:** the hardest+riskiest item (Qt host) goes *first* to de-risk
the whole effort before any investment; prerequisites precede the work they unblock; one
vertical slice precedes bulk porting.

| Order | Item | Phase | Effort | Risk | Note |
|:--:|:---|:--:|:--:|:--:|:---|
| 1 | **Qt-in-Blender host spike** | 0 | M | ⛔ **Highest** | Blender isn't Qt; make-or-break. Everything downstream assumes it works. |
| 2 | blendertk scaffold | 1 | S–M | 🟢 Low | Mechanical copy of the mayatk bootstrap pattern. |
| 3 | tentacle plumbing | 2 | M | 🟡 Med | Activation path depends on the Phase-0 outcome (bindings vs add-on operator). |
| 4 | **M1** parametrize structural tests | 2 | S | 🟢 Low | High leverage; do alongside plumbing so Blender has CI from its first slot. |
| 5 | Vertical slice `selection` | 3 | M | 🟡 Med | First real proof; grows blendertk to a true surface. |
| 6 | **M2** shared-UI contract test + **M3** API registry | 2–3 | S–M | 🟢 Low | Safety nets; cheap once the slice exists. |
| 7 | NAV-APP tier ports | 4 | M | 🟡 Med | Menu shells + `get_env_info` are light; `editors` is a Maya-editor dispatcher (many HIDE, rest rewrite) — not free. |
| 8 | EASY tier ports (~13 domains) | 4 | L (volume) | 🟢 Low each | Mechanical once the slice is proven; mostly thin adapters over native Blender ops (§5). Cost is breadth, not depth. |
| 9 | MEDIUM tier ports (~9 domains) | 4 | XL | 🟠 Med–High | Different data models (nodes/modifiers/armatures/Cycles). The real long tail. |
| 10 | Visibility / coverage + **M5** report | 5 | M | 🟢 Low | Additive; layering already hides the Maya-only menus for free. |

**Pure-difficulty ranking** (hardest → easiest), independent of order: Qt host ▸ MEDIUM ports ▸
vertical slice / plumbing ▸ EASY ports (by sheer volume) ▸ NAV-APP ▸ coverage ▸ scaffold ▸
test/registry plumbing. Execution order diverges from this on purpose — see the note above.

---

## 8. Open decisions (resolve early)

1. **Qt host mechanism** — bqt vs. timer-pump (Phase 0 answers this).
2. **Activation gesture** — add-on keymap operator (likely) + which key (F12 collides with Render).
3. **Delivery** — Blender add-on vs. startup script; where `blender_widget` is established.
4. **`BlenderUiHandler` home** — `blendertk/ui_utils/` (recommended, mirrors `MayaUiHandler`).
5. **Coverage hook flag** — env var / config name; default OFF in prod.

---

## 9. Hard constraints / standards

- **Session safety (root CLAUDE.md):** never test against an existing Maya/Blender session —
  always launch a **fresh** instance (`blender --background` for headless btk tests). No
  attaching to a live session.
- **Shared-`.ui` widget-name contract:** Blender slot methods must match the shared UI's widget
  object names exactly. When a Maya menu has widgets with no Blender analogue, hide them
  (Phase 5) rather than renaming the shared UI.
- **Cross-DCC objectName semantics (hard rule, guarded):** widget state persists per loaded UI
  (`MainWindow` → `SettingsManager(app=<ui name>)`, keys `<objectName>/<signal>`), and both DCCs
  load the *same* shared `.ui` — so a Blender slot may reuse a Maya objectName **only for the
  same option** (same label/meaning); a new Blender-only option must take a number unused by the
  Maya counterpart file (state would otherwise bleed between DCCs; different domains have
  separate stores and don't collide). Enforced by
  `test_blender_slots.py::TestCrossDccObjectNameSemantics` (caught 3 conflicts in the
  2026-06-12 review: edit chk025/chk027, selection chk003).
- **No import side effects** (M6); **check the API registry before adding any helper** (DRY/SSoT,
  blendertk's own + upstream pythontk); **naming:** `class FooBar` → `foo_bar.py`,
  widgets `tb###`/`b###`/`chk###`.
