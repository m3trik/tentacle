# tentacle — API Changes

_Diff vs the last release (origin/main @ aababffb)._

## Added (1)

- `slots/_hud_warnings.py::HudWarningsMixin.insert_prev_command(self, hud, method) -> None`

## Signature changed (1)

- `slots/_rendering.py::RenderingMixin.webxr_push`
  - was: `(self, widget, engine, has_selection, log_hint)`
  - now: `(self, widget, engine, log_hint)`
