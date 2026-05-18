# tentacle

**Role**: Desktop app. Slots architecture integrates Maya / Max / Standalone DCCs.

**Nav**: [← root](../CLAUDE.md) · **Deps**: [pythontk](../pythontk/CLAUDE.md) · [uitk](../uitk/CLAUDE.md) · [mayatk](../mayatk/CLAUDE.md)

## API surface

Before writing a new helper, **check the registry first** — duplicates undermine the SSoT goal.

- This package: [`API_REGISTRY.md`](API_REGISTRY.md) · [`API_CHANGES.md`](API_CHANGES.md) (diff vs last refresh)
- Upstream: [`pythontk` API](../pythontk/API_REGISTRY.md) · [`uitk` API](../uitk/API_REGISTRY.md) · [`mayatk` API](../mayatk/API_REGISTRY.md)
- Cross-package shadows: [`m3trik/docs/API_SHADOWS.md`](../m3trik/docs/API_SHADOWS.md)

Refresh manually: `python m3trik/scripts/generate_api_registry.py tentacle` — otherwise auto-refreshed bi-weekly.

## Architecture

- `tentacle/slots/<dcc>/*.py` — DCC-specific slot handlers (e.g. `slots/maya/rendering.py`).
- `tentacle/tcl_maya.py` — Maya integration entry + MarkingMenu (`tcl_max.py`, `tcl_blender.py` are wrapper-only).
- **UI**: Qt via [uitk](../uitk/CLAUDE.md). Widget naming: `tb###`, `b###`, `list###`, etc.

## Conventions

- Slot classes inherit from the DCC base; slot methods are named after their widget (`tb000`, `b005`).
- UI files pair with slot files (same basename). Enforced by `test_ui_integrity.py`.
- **No PyMEL.** `pymel.core` was migrated out — use `maya.cmds` / `maya.mel` only. (`import pymel.core` at module top blocks Maya's UI for minutes during init.)
- Heavy scenes: suspend viewport refresh around bulk edits.

## Tests

Structural suite: `test_package.py`, `test_slot_integrity.py`, `test_ui_integrity.py` (runs in CI — `.github/workflows/tests.yml`).

See [CHANGELOG.md](CHANGELOG.md) for history.
