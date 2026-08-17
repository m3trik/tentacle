# tentacle — API Changes

_Diff vs the last release (origin/main @ d22c7176). Generated 2026-08-17._

## Removed (10)

- `slots/blender/selection.py::Selection.cmb003` — was `(self, index, widget)`
- `slots/blender/selection.py::Selection.cmb003_init` — was `(self, widget)`
- `slots/blender/selection.py::Selection.cmb005` — was `(self, index, widget)`
- `slots/blender/selection.py::Selection.cmb005_init` — was `(self, widget)`
- `slots/blender/uv.py::Uv.b030_init` — was `(self, widget)`
- `slots/maya/selection.py::Selection.cmb003` — was `(self, index, widget)`
- `slots/maya/selection.py::Selection.cmb003_init` — was `(self, widget)`
- `slots/maya/selection.py::Selection.cmb005` — was `(self, index, widget)`
- `slots/maya/selection.py::Selection.cmb005_init` — was `(self, widget)`
- `slots/maya/uv.py::UvSlots.b030_init` — was `(self, widget)`

## Added (32)

- `slots/_main.py::MainMixin(class)`
- `slots/_selection.py::SelectionMixin(class)`
- `slots/_selection.py::SelectionMixin.list001_init(self, widget)`
- `slots/_uv.py::UvMixin.b030_init(self, widget)`
- `slots/blender/selection.py::Selection.b002(self, widget)`
- `slots/blender/selection.py::Selection.b002_init(self, widget)`
- `slots/blender/selection.py::Selection.b003(self, widget)`
- `slots/blender/selection.py::Selection.b003_init(self, widget)`
- `slots/blender/selection.py::Selection.b004(self, widget)`
- `slots/blender/selection.py::Selection.b004_init(self, widget)`
- `slots/blender/selection.py::Selection.b005(self, widget)`
- `slots/blender/selection.py::Selection.b005_init(self, widget)`
- `slots/blender/selection.py::Selection.b006(self, widget)`
- `slots/blender/selection.py::Selection.b006_init(self, widget)`
- `slots/blender/selection.py::Selection.b007(self, widget)`
- `slots/blender/selection.py::Selection.b007_init(self, widget)`
- `slots/blender/selection.py::Selection.list001(self, item)`
- `slots/maya/selection.py::Selection.b002(self, widget)`
- `slots/maya/selection.py::Selection.b002_init(self, widget)`
- `slots/maya/selection.py::Selection.b003(self, widget)`
- `slots/maya/selection.py::Selection.b003_init(self, widget)`
- `slots/maya/selection.py::Selection.b004(self, widget)`
- `slots/maya/selection.py::Selection.b004_init(self, widget)`
- `slots/maya/selection.py::Selection.b005(self, widget)`
- `slots/maya/selection.py::Selection.b005_init(self, widget)`
- `slots/maya/selection.py::Selection.b006(self, widget)`
- `slots/maya/selection.py::Selection.b006_init(self, widget)`
- `slots/maya/selection.py::Selection.b007(self, widget)`
- `slots/maya/selection.py::Selection.b007_init(self, widget)`
- `slots/maya/selection.py::Selection.list001(self, item)`
- `slots/maya/subdivision.py::Subdivision.s000_init(self, widget)`
- `slots/maya/subdivision.py::Subdivision.s001_init(self, widget)`
