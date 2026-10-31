# tentacle / blendertk — Maya↔Blender Porting Plan

> **The actionable open-work doc.** What still needs porting, how to port it, and how the
> parity system keeps the 1:1 goal honest. Shipped history lives in
> [`archive/PARITY_PORTING_HISTORY_2026-06.md`](archive/PARITY_PORTING_HISTORY_2026-06.md)
> *(local archive — untracked, not rendered on GitHub)*
> (realized mappings + divergence essays for everything landed through 2026-06) and in each
> package's `CHANGELOG.md` — do not re-accrete it here.

## The parity system (read this before porting anything)

The port is tracked per **UI element**, not per file. Three relationship classes:

1. **Shared panels and marking-menu categories** — one tentacle `.ui` and one Slots class for
   both hosts (a tool: `ui/tools/<tool>.ui` + `slots/tools/<tool>.py`; a category:
   `ui/<category>.ui` + `slots/<category>.py`), reaching each host through `self.tk` or the
   tool's API. Parity = every control works in both hosts, or carries a `requires` tag that
   hides it where its host cannot serve it (never a stub).
2. **The API halves** — mayatk ↔ blendertk, by name and behavior, and by signature where a
   shared panel calls the operation (CODE_STANDARD §5). Parity = every library call a shared
   panel makes resolves, and behaves alike, on both toolkits.
3. **Counterpart sets** — different-shaped equivalents, not same-name mirrors: Maya's
   native-menu wrappers ↔ Blender's (`btk.call_native_menu`), and `BlenderBridge` ↔
   `MayaBridge`. Never port these as-is.

Three artifacts drive it:

| Artifact | Role |
|:--|:--|
| [`PARITY_SURFACE.md`](PARITY_SURFACE.md) | Auto-gen parity gate (`compare_panel_surface.py --all --write`): every `self.tk` chain a shared Slots class calls (an engine instance's members included), resolved statically on mayatk and blendertk — name and signature. Its **Gaps** fail the gate (exit 1); its **One-host operations** list each chain one library lacks with what hides it there. Also lints every `.ui`'s `<customwidgets>`. |
| [`PARITY_AUDIT.md`](PARITY_AUDIT.md) | Auto-gen scoreboard (`generate_parity_audit.py`): the gate per category and per tool, the `requires`-hidden buttons per host, and the libraries' helper coverage. Refuses stale registry inputs. |
| [`parity_map.py`](parity_map.py) | The twin-panel era's triage ledger, read by no tool now: a live divergence is stated where the code hides it (`requires`, `slots.tools.HOSTS`, a guard and its comment). |

**The contract:** every call a shared panel makes resolves on both hosts, or is hidden or
guarded on the one that lacks it (a widget's `requires` tag, `slots.tools.HOSTS`, a
`hasattr` / `getattr` test). A library rename or signature change that leaves a caller behind
fails the gate the same day, on whichever host it breaks.

**Workflow per port:** implement → run `compare_panel_surface.py --panel <name>` → close
every gap (the operation in the host's library, or the call hidden there) → `--all --write`
(must exit 0) → `generate_parity_audit.py` → update
`CHANGELOG.md`. The status claim for a panel is its **surface column**, not prose.

## How to port a tool (the established pattern)

A tool is one shared tentacle panel over two API halves (CODE_STANDARD §3, §14); the template is
`telescope_rig` / `wheel_rig` (blendertk `rig_utils/`, tentacle `slots/tools/` + `ui/tools/`):

1. **API half** in `blendertk/blendertk/<sub>/<tool>.py` (or a `<tool>/` subpackage when mayatk
   splits one), mirroring mayatk's names and behavior, and the signatures the panel calls.
   Engine `Foo(ptk.LoggingMixin)`: no Qt, `import bpy` deferred into bodies, logic testable
   headless. Host-free logic both hosts share goes to pythontk behind an adapter (CODE_STANDARD
   §0, Adapters). Register it in `DEFAULT_INCLUDE`.
2. **Panel** — the shared `ui/tools/<tool>.ui` + `slots/tools/<tool>.py` serves both hosts: it
   calls the API through `self.tk` and never a host module. A control Blender cannot serve
   carries a `requires` tag (hidden, never a stub). Any promoted uitk class MUST be in the
   `.ui`'s `<customwidgets>` (else it silently loads as a plain QWidget — the sweep's lint
   catches this).
3. **Menu wiring** — the shared category Slots open it (`marking_menu.show("<tool>")`).
4. **Test** — headless `blendertk/test/test_<tool>.py` via fresh
   `blender --background --factory-startup` (session safety: NEVER attach to a running DCC);
   the panel's own `tentacle/test/test_<tool>_panel.py`.
5. **Gate** — `compare_panel_surface.py --panel <tool>`: close every gap (the operation in
   the host's library, or the call hidden or guarded where it is missing).

**Driver gotcha (rigs):** build ALL driver variables before the expression, call
`RigUtils.refresh_drivers(objs)` LAST, decorate with `@undo_checkpoint`, keep expressions
branchless (fast parser).

## Open work

### Panels — big-ticket ports (recipes condensed; full mappings in the archive)

| Panel | Effort | Blender mapping sketch | Deps / notes |
|:--|:--|:--|:--|
| **SceneExporter** | Shipped | Same task-graph architecture over `bpy.ops.export_scene.fbx`; reuses `env_utils/fbx_utils`. RenderOpacity dual-key hook runs as a pre-export task. | **Done** — the FBX export-option preset combo (`cmb000`) + its option-box `b003`/`b004`/`b007`/`b008` are built 1:1 against a `pythontk.PresetStore`-backed named-JSON preset engine (sweep: clean, 0 triaged). |
| **Shots + ShotManifest + ShotSequencer** | Shipped 2026-07-11 | `ShotBlock`/`ShotStore` data model extracted to pythontk; apply layer → timeline **markers** + `marker.camera` / Scenes / VSE. | **Done** — all three panels ship 1:1 (sweep: 0 element deltas each). |
| **WorkspaceMap** | Shipped 2026-10-28 | The scan, measure and tree are pythontk's `WorkspaceMapBase`; each host binds its adapter (`MayaWorkspaceMapHost` / `BlenderWorkspaceMapHost`: what a workspace and its scenes are). | **Done** — the map part of tentacle's shared Workspaces tool serves both hosts. |

> **No big-ticket ports remain open.** Every tool is one shared tentacle panel over both API halves, or ledgered N/A (counterpart bridges).

**Closed 2026-07-08**: `duplicate.py` `tb002` Auto Instance — blendertk `core_utils/auto_instancer/`
(`btk.auto_instance`), with the matching math + assembly clustering extracted to pythontk
(`PointCloud.match_clouds` / `AssemblySorter`) and mayatk refactored onto the shared
implementation; slot + option box mirror Maya's 1:1. **SmartBake** also shows clean on the sweep
(its 2026-07-04 untriaged block is resolved). Open panel ports are now the Shots pipeline only.

**Closed 2026-07-03/04**: BlendshapeAnimator (shape-key authoring, `anim_utils/blendshape_animator/`), HierarchyManager, AudioClips (VSE sound-strip CRUD, `audio_utils/`), MacroManager (`edit_utils/macro_manager/`, wraps the pre-existing `Macros` engine), and UnityBridge (native co-located bridge, `env_utils/unity_bridge/` — the "evaluate" question resolved in favor of building it: Unity's own asset pipeline ingests anything dropped into `Assets/` on focus, so, like Maya's, it needs no live-RPC relay). All five verified clean via `compare_panel_surface.py --panel <name>`; see `parity_map.py`'s `PANELS` dict for the per-panel verification notes.

### Element-level pendings (twin-panel era, closed; `parity_map.py`)

**Closed 2026-09-05 — Render Effects (was RenderOpacity; `render_effects_slots` in `parity_map.py`)**: the panel was redesigned and renamed on both sides the same day — the Create / Manage sections are gone, **Key Opacity Fade** and **Key Highlight Pulse** create their channel on demand, each option box carries a remove action, and the header gained *Viewport Preview*. blendertk's panel was rebuilt 1:1 by objectName (`tb001` + `b_pulse_color` / `chk001` / `s001`–`s003`, header `chk_preview`), so the eight pending rows (and the never-ported `cmb_channel` / `chk_auto_create_hl`, which no longer exist on the Maya side) are closed; the ledger block is empty.

**As of 2026-07-13 there are 0 open `pending` items — the sweep reports 0 open-work.** The last
batch closed that day: **scene `b013`** Mesh Converter (extapps/mesh_convert via the shared
`external_app` handler); **selection `cmb003`** UV Shell Border / UV Perimeter / UV Edge Loop
(bmesh UV-graph helpers on `btk.Selection`) + `list000` Back-/Front-Facing (object-level signed-UV-
area leaves); **LightmapBaker `cmb002`** Atlas-by-Material packing (new `LightmapBaker.pack_atlas`
— per-material grouping + area-weighted rects reusing pythontk's `ImgUtils` layout math + bpy-native
EXR assembly/UV-repack, revert-restorable); and the stale `color_id` preset-combo /
`shader_templates` "Open Template File" rows (both already built). All engine work verified in
fresh headless Blender 5.1 (`test_selection.py`, `test_lightmap_baker.py`). Remaining differences
are all by-design (`na`/`replaced`/`counterpart`) — ArnoldBridge, the native-menu
stub set, per-camera visibility, NURBS-parametric / Channel-Box / node-locking families, etc.

**Closed 2026-07-11**: **TubeRig** granular step-workflow (b001–b004 + reverse-chain chk000) +
twist/squash/volume/auto-bend deformation toggles (the "needs live-Blender rig verification" ruling
was refuted — deform is verified numerically via the evaluated depsgraph in `test_tube_rig.py`).
**Closed 2026-07-03**: HdrManager full drift (config_buttons, clear_network, add_hdr_btn,
cmb_add_mode, add_value, .ui promotion), WheelRig `b010`, LightmapBaker header chrome, TubeRig
`cmb_preset`/`txt000` .ui promotion, and the whole slot default-flip channel. **Closed
2026-07-04**: `animation.py` Invert/Adjust-Spacing/Scale-Keys/Snap-Delete-Copy-Paste-Keys/
Go-To-Frame/Get-Animation-Info/Intermediate-Keys drift (down to the one genuine `chk006`
value-relative-paste gap); `edit.py` `cmb000` Transfer menu (UV / vertex-color / vertex-group /
custom-normal via `bpy.ops.object.data_transfer` + the Data Transfer modifier); `rendering.py`
`chk057` Show Ornaments + `cmb003` renderer picker; `uv.py` Straighten Shell, Stack Similar
(+ `s000` tolerance), Include Auto Seams, Mirror Per Shell, Preserve Footprint, target-UDIM
pack tile (`s004`).

### Default-flip review (twin-panel era, closed)

Same-named controls shipping different defaults silently change first-use behavior. The
**slot default-flip channel was resolved 2026-07-03**: 13 genuine drift flips fixed in the
Blender slots (transform chk014/chk016, selection chk018, edit chk002/004/013/017/024 +
s006–s008 tolerances, animation chk031/d001/s000/s004/s013, subdivision chk012, nurbs, polygons,
uv s016/s017), the rest ledgered as `accepted-delta` in `DEFAULT_DELTAS` with evidence
(renderer/unit/paradigm differences). One class per category and per tool now builds every
control for both hosts, so a same-named control can no longer ship two defaults; the `.ui`-diff
channel went with the twin `.ui` files.

### Modules (Layer-4)

- `render_utils` — new mayatk module (2026-06-21, 7 names); mirror when a Blender slot needs it.

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
# after ANY slot/.ui change, or a library rename / signature change (must exit 0):
python m3trik/scripts/compare_panel_surface.py --all --write
# refresh the scoreboard (refuses stale registries):
python m3trik/scripts/generate_parity_audit.py
```

- A divergence is stated where the code hides it, **when made**: the `requires` tag's or the
  guard's comment says which host lacks the operation and why, so it isn't re-litigated.
- **CI gate**: the `parity` job in `tentacle/.github/workflows/tests.yml` checks out the
  sibling repos at `dev` beside this one (pythontk, uitk, mayatk, blendertk), runs the gate
  (`--all --write` + git-diff on PARITY_SURFACE.md — a gap AND a stale committed doc both
  fail), then
  `generate_parity_audit.py --check --allow-stale` (mtimes are meaningless in a fresh
  checkout; `--check` is content-based).
