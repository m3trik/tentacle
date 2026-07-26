# tentacle

**Role**: Desktop app. Slots architecture integrates Maya / Max / Blender / Standalone DCCs (engine per DCC: `mayatk`, `blendertk`).

**Nav**: [← root](../CLAUDE.md) · [docs](docs/README.md) · **Deps**: [pythontk](../pythontk/CLAUDE.md) · [uitk](../uitk/CLAUDE.md) · [mayatk](../mayatk/CLAUDE.md)

## API surface

**Before adding a helper, check the registry** (navigation rules: [root](../CLAUDE.md)):

- [`API_INDEX.md`](API_INDEX.md) (compact — read first) · [`API_REGISTRY.md`](API_REGISTRY.md) (grep, don't Read whole) · [`API_CHANGES.md`](API_CHANGES.md)
- Upstream: [pythontk](../pythontk/API_INDEX.md) · [uitk](../uitk/API_INDEX.md) · [mayatk](../mayatk/API_INDEX.md) · [blendertk](../blendertk/API_INDEX.md)
- Cross-package shadows: [`m3trik/docs/API_SHADOWS.md`](../m3trik/docs/API_SHADOWS.md)

## Architecture

- `tentacle/slots/<dcc>/*.py` — DCC-specific slot handlers (e.g. `slots/maya/rendering.py`).
- **Behavior shared by a panel's Maya + Blender forks** → ONE underscore-prefixed mixin module per panel: `slots/_<panel>.py` defining a single `<Panel>Mixin` **class** (a plain mixin, NOT a `Slots{Maya,Blender}` subclass). Concrete slot: `class <Panel>Slots(<Panel>Mixin, SlotsDcc)`. Grow the panel's existing mixin — never drop loose per-feature helper modules or module-level `def`s into `slots/` (that's the pre-encapsulation regression). The `_` prefix keeps it out of slot/UI discovery (concrete panels live in `slots/<dcc>/` and pair with a `.ui`). Exemplar: [`slots/_hud_warnings.py`](tentacle/slots/_hud_warnings.py).
- `tentacle/tcl_maya.py` — Maya integration entry + MarkingMenu. `tcl_blender.py` is a full Blender integration (drives `slots/blender` + the `blendertk` engine); `tcl_max.py` is a thin wrapper.
- **UI**: Qt via [uitk](../uitk/CLAUDE.md). Widget naming: `tb###`, `b###`, `list###`, etc.

## Conventions

- Slot classes inherit from the DCC base; slot methods are named after their widget (`tb000`, `b005`).
- UI files pair with slot files (same basename). Enforced by `test_ui_integrity.py`.
- **No PyMEL.** `pymel.core` was migrated out — use `maya.cmds` / `maya.mel` only. (`import pymel.core` at module top blocks Maya's UI for minutes during init.)
- Heavy scenes: suspend viewport refresh around bulk edits.

## Tests

Structural suite: `test_package.py`, `test_slot_integrity.py`, `test_ui_integrity.py` (runs in CI — `.github/workflows/tests.yml`).

See [CHANGELOG.md](CHANGELOG.md) for history.
