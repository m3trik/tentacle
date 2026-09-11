# tentacle — API Changes

_Diff vs the last release (origin/main @ 9d68de73)._

## Removed (6)

- `slots/_rendering.py::RenderingMixin.webxr_init` — was `(self, widget, sidecar_tooltip)`
- `slots/_rendering.py::RenderingMixin.webxr_push` — was `(self, widget, engine, log_hint)`
- `slots/blender/rendering.py::Rendering.tb002` — was `(self, widget)`
- `slots/blender/rendering.py::Rendering.tb002_init` — was `(self, widget)`
- `slots/maya/rendering.py::Rendering.tb002` — was `(self, widget)`
- `slots/maya/rendering.py::Rendering.tb002_init` — was `(self, widget)`

## Added (5)

- `slots/blender/rendering.py::Rendering.b000(self, widget)`
- `slots/maya/rendering.py::Rendering.b000(self, widget)`
- `tcl.py::Tcl.dispose_retired(instances)`
- `tcl.py::Tcl.prepare_reload(cls, host=None)`
- `tcl.py::Tcl.reload_packages(cls, host=None)`
