# tentacle

**Role**: The product: every tool, panel and Slots class, for Maya, Blender and standalone (3ds Max: a thin launcher). Target layout (root CLAUDE.md, [CODE_STANDARD](../m3trik/docs/CODE_STANDARD.md) §3, §14): `tools/<tool>/` (`model/`, adapter Protocol, `maya.py` / `blender.py`), `ui/panels/<panel>/` (`.ui` + one shared Slots class), `core/<engine>/`. Panels and tools arrive from mayatk and blendertk one tool per release; no library imports tentacle.

**Nav**: [← root](../CLAUDE.md) · [docs](docs/README.md) · **Deps**: [pythontk](../pythontk/CLAUDE.md) · [uitk](../uitk/CLAUDE.md) · **Host libraries**: [mayatk](../mayatk/CLAUDE.md) · [blendertk](../blendertk/CLAUDE.md) (host-provided, not pinned)

## API surface

[`API_INDEX.md`](API_INDEX.md) · [`API_REGISTRY.md`](API_REGISTRY.md) · [`API_CHANGES.md`](API_CHANGES.md) · shadows [`API_SHADOWS.md`](../m3trik/docs/API_SHADOWS.md) — registry rules in [root](../CLAUDE.md). Upstream: [pythontk](../pythontk/API_INDEX.md) · [uitk](../uitk/API_INDEX.md) · [mayatk](../mayatk/API_INDEX.md) · [blendertk](../blendertk/API_INDEX.md).

## Architecture

- `tentacle/slots/<dcc>/*.py` — DCC-specific slot handlers (e.g. `slots/maya/rendering.py`).
- **Target: one `<Base>Slots` per category, shared by both hosts**, reaching the host through `self.tk` or the tool's API, never a per-host fork (§3). The normals pilot opens it; each category folds its forks and mixin into one class when next touched. Until then:
- **Behavior shared by a panel's Maya + Blender forks** → ONE underscore-prefixed mixin module per panel: `slots/_<panel>.py` defining a single `<Panel>Mixin` **class** (a plain mixin, NOT a `Slots{Maya,Blender}` subclass). This is the sanctioned exception to root's composition-over-mixins rule: Switchboard binds a slot by *method name on the slots class*, so shared slot bodies can only be inherited. Concrete slot: `from tentacle import <Panel>Mixin, SlotsDcc` → `class <Panel>Slots(<Panel>Mixin, SlotsDcc)`. Grow the panel's existing mixin — never drop loose per-feature helper modules or module-level `def`s into `slots/` (that's the pre-encapsulation regression). The `_` prefix keeps it out of slot/UI discovery (concrete panels live in `slots/<dcc>/` and pair with a `.ui`). Exemplar: [`slots/_hud_warnings.py`](tentacle/slots/_hud_warnings.py).
  - **Never fold a mixin into `SlotsMaya`/`SlotsBlender`.** Mixins define widget-named slots (`SceneMixin.tb002`, `MaterialsMixin.b003`) and objectNames are reused across panels — on a shared base, a panel that has a `tb002` widget but no `tb002` method silently binds to another panel's slot. Register new mixins in `tentacle/__init__.py`'s `DEFAULT_INCLUDE`; mix in per panel.
- `tentacle/tcl_maya.py` — Maya integration entry + MarkingMenu. `tcl_blender.py` is a full Blender integration (drives `slots/blender` + the `blendertk` engine); `tcl_max.py` is a thin wrapper.
- **UI**: Qt via [uitk](../uitk/CLAUDE.md). Widget naming: `tb###`, `b###`, `list###`, etc.

## Conventions

- Slot classes are `<Base>Slots` (`edit.py` -> `EditSlots`; the name keys users' shortcut overrides, pinned by `test_dcc_invariants.py`) and inherit from the DCC base; slot methods are named after their widget (`tb000`, `b005`).
- UI files pair with slot files (same basename). Enforced by `test_ui_integrity.py`.
- **No PyMEL** (rule owned by [mayatk](../mayatk/CLAUDE.md)) — `maya.cmds` / `maya.mel` only.
- Heavy scenes: suspend viewport refresh around bulk edits.

## Tests

Structural suite: `test_package.py`, `test_slot_integrity.py`, `test_ui_integrity.py` (runs in CI — `.github/workflows/tests.yml`). Pointed: `python tentacle/test/run_tests.py <modules> [-k pat]` (offscreen; Maya-gated tests skip there, so add `--in-maya` for those — or let `m3trik/scripts/affected_tests.py <files> --run` split them). Canonical full run (review / release): `python tentacle/test/run_tests.py --in-maya` (launches a FRESH Maya via `MayaConnection`; the badge needs the Maya slot suites, so a plain no-Maya or pointed run never stamps it).

See [CHANGELOG.md](CHANGELOG.md) for history.
