# tentacle / blendertk — Maya↔Blender Porting Plan

> **The actionable open-work doc.** What still needs porting, how to port it, and how the
> parity system keeps the 1:1 goal honest. Shipped history lives in
> [`archive/PARITY_PORTING_HISTORY_2026-06.md`](archive/PARITY_PORTING_HISTORY_2026-06.md)
> *(local archive — untracked, not rendered on GitHub)*
> (realized mappings + divergence essays for everything landed through 2026-06) and in each
> package's `CHANGELOG.md` — do not re-accrete it here.

## The parity system (read this before porting anything)

The port is tracked per **UI element**, not per file. Three relationship classes:

1. **Shared marking-menu slots** — `tentacle/slots/maya/<d>.py` ↔ `slots/blender/<d>.py` over
   ONE shared `ui/<d>*.ui`. Parity = every Maya-handled widget is handled (or consciously
   hidden) on Blender, and the runtime-built option-box/menu controls match.
2. **Co-located tool panels** — mayatk `<tool>.py`+`.ui` ↔ blendertk twins. Parity = twin `.ui`
   widget inventories match AND the code-built control surface matches.
3. **Counterpart sets** — different-shaped equivalents, not same-name mirrors: the 33
   Maya-native-menu stubs ↔ `slots/blender/blender.py` (`btk.call_native_menu`), and
   `BlenderBridge` ↔ `MayaBridge`. Never port these as-is.

Four artifacts drive it:

| Artifact | Role |
|:--|:--|
| [`parity_map.py`](parity_map.py) | **The triage ledger** — every conscious divergence, per element, with status (`na` / `renamed` / `relocated` / `replaced` / `divergent` / `done-elsewhere` / `pending`) + reason. Hand-maintained; the SSoT for "why is this different". |
| [`PARITY_SURFACE.md`](PARITY_SURFACE.md) | Auto-gen per-element matrix (`compare_panel_surface.py --all --write`). Unrolls loop-built controls, resolves menu aliases + f-string names, skips `__main__` blocks, diffs twin `.ui` XML, diffs defaults/ranges/combo-items, classifies through the ledger. **UNTRIAGED rows fail the sweep (exit 1).** |
| [`PARITY_AUDIT.md`](PARITY_AUDIT.md) | Auto-gen coarse depth scoreboard (`generate_parity_audit.py`). Refuses stale registry inputs; its per-panel `surface` column comes from the classified diff — trust that over the line ratios. |
| [`DCC_COVERAGE.md`](DCC_COVERAGE.md) | Auto-gen presence floor (handled/hidden contract, backed by `test_blender_slots.py`). |

**The contract:** every Maya→Blender delta is either *fixed*, or *ledgered with a reason*.
`pending` = acknowledged open work (sweep still passes); an unledgered delta fails CI. When
mayatk gains a feature after a panel was ported (**drift** — it has happened: HdrManager grew
4 controls three days after its port), the next sweep flags it untriaged automatically.

**Workflow per port:** implement → run `compare_panel_surface.py --panel <name>` → fix or
ledger every delta → `--all --write` (must exit 0) → `generate_parity_audit.py` → update
`CHANGELOG.md`. The status claim for a panel is its **surface column**, not prose.

## How to port a panel (the established pattern)

Proven end-to-end on `telescope_rig` / `wheel_rig` (use those files as the template):

1. **Engine + Slots co-located** in `blendertk/blendertk/<module>/<tool>.py` (or `<tool>/`
   package when mayatk splits one). Engine `Foo(ptk.LoggingMixin)` — no Qt at module top,
   `import bpy` deferred into bodies; logic unit-testable headless. Slots `FooSlots` with
   widget-named methods; defer `uitk` imports into `header_init`.
2. **`.ui`** — copy mayatk's verbatim when DCC-neutral; hide vestigial widgets via
   `setVisible(False)` in `__init__` (don't `deleteLater`). The `.ui` is the contract; any
   promoted uitk class MUST be in `<customwidgets>` (else it silently loads as a plain QWidget
   — the sweep's lint catches this).
3. **Register** the engine in `DEFAULT_INCLUDE` (Slots are discovered by `BlenderUiHandler`).
4. **Menu wiring** — mirror the Maya slot's button/combo (`marking_menu.show("<tool>")`).
5. **Test** — headless `blendertk/test/test_<tool>.py` via fresh
   `blender --background --factory-startup` (session safety: NEVER attach to a running DCC).
   Add the panel to `test_blender_ui_handler.py`'s `PANELS` list.
6. **Triage** — `compare_panel_surface.py --panel <tool>`: fix or ledger every delta.

**Driver gotcha (rigs):** build ALL driver variables before the expression, call
`RigUtils.refresh_drivers(objs)` LAST, decorate with `@undo_checkpoint`, keep expressions
branchless (fast parser).

## Open work

### Panels — big-ticket ports (recipes condensed; full mappings in the archive)

| Panel | Effort | Blender mapping sketch | Deps / notes |
|:--|:--|:--|:--|
| **SceneExporter** | XL (3059 ln) | Same task-graph architecture over `bpy.ops.export_scene.fbx`; **reuse `env_utils/fbx_utils`** as the export primitive. RenderOpacity dual-key hook runs as a pre-export task. | Panel shipped; 4 preset-management buttons (`b003`/`b004`/`b007`/`b008`) remain `pending` — no Blender-native FBX external-preset-file mechanism (see `parity_map.py`) |
| **Shots + ShotManifest + ShotSequencer** | XXL (15354 ln) | `ShotBlock`/`ShotStore` data model is DCC-neutral; apply layer → timeline **markers** + `marker.camera` / multiple Scenes / VSE. Port data model + manifest (read-only) before the sequencer. | Lowest priority — biggest divergence; out of scope for the 2026-07 push |
| **SmartBake** | — | mayatk module landed 2026-07-02; blendertk port (engine + Slots + `.ui` under `anim_utils/smart_bake/`) in progress as a background workflow started 2026-07-03. | Re-run `compare_panel_surface.py --panel smart_bake` once it lands — still 9 untriaged widgets as of 2026-07-04 |
| **WorkspaceMap** | N/A (ledgered) | Maya-workspace tool; no Blender project concept. Reframe as a `.blend`/asset browser only if wanted. | |

**Closed 2026-07-03/04**: BlendshapeAnimator (shape-key authoring, `anim_utils/blendshape_animator/`), HierarchyManager, AudioClips (VSE sound-strip CRUD, `audio_utils/`), MacroManager (`edit_utils/macro_manager/`, wraps the pre-existing `Macros` engine), and UnityBridge (native co-located bridge, `env_utils/unity_bridge/` — the "evaluate" question resolved in favor of building it: Unity's own asset pipeline ingests anything dropped into `Assets/` on focus, so, like Maya's, it needs no live-RPC relay). All five verified clean via `compare_panel_surface.py --panel <name>`; see `parity_map.py`'s `PANELS` dict for the per-panel verification notes.

### Element-level pendings (SSoT = `parity_map.py` `pending` entries; rollup in PARITY_SURFACE)

Current highlights (as of 2026-07-03): **TubeRig** granular step-workflow (b001–b004 +
reverse-chain chk000) + twist/squash/volume/auto-bend deformation toggles + the unreachable
Auto joint count (spec `minimum=2` blocks the engine's supported `-1`) — the step-workflow is
the single largest open item: it needs standalone step-engine methods operating on
user-selected existing armature/bones plus **live-Blender rig-deformation verification**
(structural headless tests can confirm bones/constraints exist but not correct deform), so
it's deferred to a dedicated session rather than shipped unverified; **LightmapBaker** `cmb002`
Atlas-by-Material packing (needs a Blender-native `pack_atlas` engine — per-material grouping +
EXR atlas assembly via bpy image I/O + the already-present scaleOffset metadata carrier).
**Closed 2026-07-03**: HdrManager full drift (config_buttons, clear_network, add_hdr_btn,
cmb_add_mode, add_value, .ui promotion), WheelRig `b010`, LightmapBaker header chrome, TubeRig
`cmb_preset`/`txt000` .ui promotion, and the whole slot default-flip channel. **Closed
2026-07-04**: `animation.py` Invert/Adjust-Spacing/Scale-Keys/Snap-Delete-Copy-Paste-Keys/
Go-To-Frame/Get-Animation-Info/Intermediate-Keys drift (down to the one genuine `chk006`
value-relative-paste gap); `edit.py` `cmb000` Transfer menu (UV / vertex-color / vertex-group /
custom-normal via `bpy.ops.object.data_transfer` + the Data Transfer modifier); `rendering.py`
`chk057` Show Ornaments + `cmb003` renderer picker; `uv.py` Straighten Shell, Stack Similar
(+ `s000` tolerance), Include Auto Seams, Mirror Per Shell, Preserve Footprint, target-UDIM
pack tile (`s004`). Run `compare_panel_surface.py --all` for the live list.

### Default-flip review (report-only channel of the sweep)

Same-named controls shipping different defaults silently change first-use behavior. The
**slot default-flip channel was resolved 2026-07-03**: 13 genuine drift flips fixed in the
Blender slots (transform chk014/chk016, selection chk018, edit chk002/004/013/017/024 +
s006–s008 tolerances, animation chk031/d001/s000/s004/s013, subdivision chk012, nurbs, polygons,
uv s016/s017), the rest ledgered as `accepted-delta` in `DEFAULT_DELTAS` with evidence
(renderer/unit/paradigm differences). **Still open**: the co-located-panel `.ui` twin diffs
(class-promotion + DCC-appropriate label differences like Locators/Empties, and combo-item
deltas — selection cmb003 Convert-To 20→7, cameras list000 11→5, normals cmb000 5→3) — a
separate review channel; triage per panel as those panels are deepened.

### Modules (Layer-4)

- `render_utils` — new mayatk module (2026-06-21, 7 names); mirror when a Blender slot needs it.
- `anim_utils/segment_keys.py` — deferred (YAGNI) until a Blender anim slot needs it.

### Maya-side cleanup

The sweep's **stale** list (`no widget anywhere, no reference`) is dead Maya code to delete —
deleting it is Maya housekeeping, not Blender porting. Current list in PARITY_SURFACE.

## Phase 2 — runtime UI fingerprint (planned)

The static sweep cannot see: unresolvable dynamic controls (DCC-queried combos/trees),
effective visibility, whether a control *works*. The measurement that closes this is a
**runtime widget-tree fingerprint**: instantiate each panel offscreen, drive `header_init` +
every `*_init`, walk `findChildren` (+ per-mode states for dynamic panels like TubeRig), and
serialize objectName/class/label/enabled/min/max/default to JSON; diff Maya vs Blender by name.

The Blender half already exists as a template: `blendertk/test/test_blender_ui_handler.py`
loads all panels under the workspace `.venv` (`QT_QPA_PLATFORM=offscreen`, no bpy) and already
drives TubeRig mode switches + Channels behavior probes. The Maya half runs the same walk
under `mayapy` (standalone + offscreen Qt). Session safety applies: fresh instances only.

## Maintenance

```powershell
# after ANY public-API change:
python m3trik/scripts/generate_api_registry.py mayatk blendertk
# after ANY slot/panel/.ui change (must exit 0 — fix or ledger every delta):
python m3trik/scripts/compare_panel_surface.py --all --write
# refresh the depth scoreboard (refuses stale registries):
python m3trik/scripts/generate_parity_audit.py
```

- Divergence decisions go in `parity_map.py` **when made**, so they aren't re-litigated.
- **CI gate**: the `parity` job in `tentacle/.github/workflows/tests.yml` checks out the
  sibling repos at `dev` beside this one, runs the sweep (`--all --write` + git-diff on
  PARITY_SURFACE.md — untriaged deltas AND a stale committed doc both fail), then
  `generate_parity_audit.py --check --allow-stale` (mtimes are meaningless in a fresh
  checkout; `--check` is content-based).
