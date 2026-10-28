# tentacle

**Role**: The product's UI: the launcher, the UIs and the Slots classes, for Maya, Blender and standalone (3ds Max: a thin launcher), and no logic of its own: a tool's API is mayatk / blendertk, shared logic pythontk. Layout (root CLAUDE.md, [CODE_STANDARD](../m3trik/docs/CODE_STANDARD.md) §3, §14): a tool's UI is `ui/tools/<tool>.ui` and its one Slots class `slots/tools/<tool>.py` (shared by both hosts, paired by name; Qt helpers in `slots/tools/_<tool>/`); categories are `ui/<category>.ui` + `slots/<category>.py`. Tool UIs arrive from mayatk and blendertk one tool per milestone; no library imports tentacle.

**Nav**: [← root](../CLAUDE.md) · [docs](docs/README.md) · **Deps**: [pythontk](../pythontk/CLAUDE.md) · [uitk](../uitk/CLAUDE.md) · **Host libraries**: [mayatk](../mayatk/CLAUDE.md) · [blendertk](../blendertk/CLAUDE.md) (host-provided, not pinned)

## API surface

[`API_INDEX.md`](API_INDEX.md) · [`API_REGISTRY.md`](API_REGISTRY.md) · [`API_CHANGES.md`](API_CHANGES.md) · shadows [`API_SHADOWS.md`](../m3trik/docs/API_SHADOWS.md) — registry rules in [root](../CLAUDE.md). Upstream: [pythontk](../pythontk/API_INDEX.md) · [uitk](../uitk/API_INDEX.md) · [mayatk](../mayatk/API_INDEX.md) · [blendertk](../blendertk/API_INDEX.md).

## Architecture

- **One `<Base>Slots(Slots)` per marking-menu category, shared by both hosts** (`slots/<category>.py`; exemplar [`slots/normals.py`](tentacle/slots/normals.py)): host behavior through `self.tk` or the tool's API, never a per-host fork or a mixin (§3); a widget only one host serves carries a `requires` tag (§15, hidden, never a stub). The categories still forked in `slots/<dcc>/` (with their `slots/_<category>.py` mixin) fold in during the composition phase; never add to a fork.
- `slots/<dcc>/*.py` otherwise holds each host's native-menu wrappers (`ui/maya_menus`, `ui/blender_menus`).
- `tentacle/tcl_maya.py` — Maya integration entry + MarkingMenu. `tcl_blender.py` is a full Blender integration (drives `slots/blender` + the `blendertk` engine); `tcl_max.py` is a thin wrapper.
- **UI**: Qt via [uitk](../uitk/CLAUDE.md). Widget naming: `tb###`, `b###`, `list###`, etc.

## Conventions

- Slot classes are `<Base>Slots` (`edit.py` -> `EditSlots`; the name keys users' shortcut overrides, pinned by `test_dcc_invariants.py`) and subclass `Slots`; slot methods are named after their widget (`tb000`, `b005`).
- UI files pair with slot files (same basename). Enforced by `test_ui_integrity.py`.
- **No PyMEL** (rule owned by [mayatk](../mayatk/CLAUDE.md)) — `maya.cmds` / `maya.mel` only.
- Heavy scenes: suspend viewport refresh around bulk edits.

## Tests

Structural suite: `test_package.py`, `test_slot_integrity.py`, `test_ui_integrity.py` (runs in CI — `.github/workflows/tests.yml`). Pointed: `python tentacle/test/run_tests.py <modules> [-k pat]` (offscreen; Maya-gated tests skip there, so add `--in-maya` for those — or let `m3trik/scripts/affected_tests.py <files> --run` split them). Canonical full run (review / release): `python tentacle/test/run_tests.py --in-maya` (launches a FRESH Maya via `MayaConnection`; the badge needs the Maya slot suites, so a plain no-Maya or pointed run never stamps it). Blender: `python tentacle/test/run_tests.py [checks] --in-blender` runs each headless `test/blender/*_check.py` (its usage line says `blender --background`) in a FRESH background Blender; the rest drive a window and are run by hand.

See [CHANGELOG.md](CHANGELOG.md) for history.
