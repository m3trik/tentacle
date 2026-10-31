# tentacle

**Role**: The product's UI: the launcher, the UIs and the Slots classes, for Maya, Blender and standalone (3ds Max: a thin launcher), and no logic of its own: a tool's API is mayatk / blendertk, shared logic pythontk. Layout (root CLAUDE.md, [CODE_STANDARD](../m3trik/docs/CODE_STANDARD.md) §3, §14): a tool's UI is `ui/tools/<tool>.ui` and its one Slots class `slots/tools/<tool>.py` (shared by both hosts, paired by name; Qt helpers in `slots/tools/_<tool>/`); categories are `ui/<category>.ui` + `slots/<category>.py`. No library imports tentacle.

**Nav**: [← root](../CLAUDE.md) · [docs](docs/README.md) · **Deps**: [pythontk](../pythontk/CLAUDE.md) · [uitk](../uitk/CLAUDE.md) · [extapps](../extapps/CLAUDE.md) · **Host libraries**: [mayatk](../mayatk/CLAUDE.md) · [blendertk](../blendertk/CLAUDE.md) (host-provided, not pinned)

## API surface

[`API_INDEX.md`](API_INDEX.md) · [`API_REGISTRY.md`](API_REGISTRY.md) · [`API_CHANGES.md`](API_CHANGES.md) · shadows [`API_SHADOWS.md`](../m3trik/docs/API_SHADOWS.md) — registry rules in [root](../CLAUDE.md). Upstream: [pythontk](../pythontk/API_INDEX.md) · [uitk](../uitk/API_INDEX.md) · [extapps](../extapps/API_INDEX.md) · [mayatk](../mayatk/API_INDEX.md) · [blendertk](../blendertk/API_INDEX.md).

## Architecture

- **One `<Base>Slots(Slots)` per marking-menu category, shared by both hosts** (`slots/<category>.py`; exemplar [`slots/normals.py`](tentacle/slots/normals.py)): host behavior through `self.tk` or the tool's API, never a per-host fork or a mixin (§3); a control one host cannot serve is hidden there, never a stub (§15): a `requires` tag in the `.ui`, `Slots.requires(widget, host)` for one built in code, `Slots.hide_unless(widget, available)` where the host's engine lacks the operation.
- No per-host slot package: the chord menus' native-menu pages (`ui/maya_menus`, `ui/blender_menus`) are pure `MenuButton` navigation with no Slots class; each host's UI handler (mayatk / blendertk) builds its own menus when the switchboard resolves a release's target.
- `tentacle/tcl_maya.py` — Maya integration entry + MarkingMenu. `tcl_blender.py` is a full Blender integration (drives the `blendertk` engine); `tcl_max.py` is a thin wrapper.
- **Standalone panels** (`slots.tools.STANDALONE`, engines in `extapps` / pythontk) open in a switchboard of their own: `tcl_standalone.py` builds each (`<Tool>UI`), the `uitk.external_apps.in_process` entry points name them (a host launches them through its external-app handler, never its own switchboard), `__main__.py` is their hub (`python -m tentacle [panel]`).
- **UI**: Qt via [uitk](../uitk/CLAUDE.md). Widget naming: `tb###`, `b###`, `list###`, etc.

## Conventions

- Slot classes are `<Base>Slots` (`edit.py` -> `EditSlots`; the name keys users' shortcut overrides, pinned by `test_dcc_invariants.py`) and subclass `Slots`; slot methods are named after their widget (`tb000`, `b005`).
- UI files pair with slot files (same basename). Enforced by `test_ui_integrity.py`.
- Slots reach uitk off `self.sb` (any public uitk name: `self.sb.IconManager`), never a bare `from uitk import` (the class-body exceptions ride the `Slots` base: `Slots.Signals`, `Slots.AttributeSpec`).
- A tool one host serves is a `slots.tools.HOSTS` row (with its reason); a panel merged into or renamed to a tool is a `RENAMED_FROM` row plus a `RENAMED_HOSTS` row per former panel, so users' saved values carry over.
- **No PyMEL** (rule owned by [mayatk](../mayatk/CLAUDE.md)) — `maya.cmds` / `maya.mel` only.
- Heavy scenes: suspend viewport refresh around bulk edits.

## Tests

Structural suite: `test_package.py`, `test_slot_integrity.py`, `test_ui_integrity.py` (runs in CI — `.github/workflows/tests.yml`). Pointed: `python tentacle/test/run_tests.py <modules> [-k pat]` (offscreen; Maya-gated tests skip there, so add `--in-maya` for those — or let `m3trik/scripts/affected_tests.py <files> --run` split them). Canonical full run (review / release): `python tentacle/test/run_tests.py --in-maya` (launches a FRESH Maya via `MayaConnection`; the badge needs the Maya slot suites, so a plain no-Maya or pointed run never stamps it). Blender: `python tentacle/test/run_tests.py [checks] --in-blender` runs each headless `test/blender/*_check.py` (its usage line says `blender --background`) in a FRESH background Blender; the rest drive a window and are run by hand.

See [CHANGELOG.md](CHANGELOG.md) for history.
