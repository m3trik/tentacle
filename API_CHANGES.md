# tentacle — API Changes

_Diff vs the last release (origin/main @ d26fb9a3)._

## Added (12)

- `slots/_uv.py::UvMixin.b000(self)`
- `slots/blender/lighting.py::LightingSlots.b002(self)`
- `slots/blender/lighting.py::LightingSlots.b002_init(self, widget)`
- `slots/blender/rigging.py::RiggingSlots.tb005(self, widget)`
- `slots/blender/rigging.py::RiggingSlots.tb005_init(self, widget)`
- `slots/blender/selection.py::SelectionSlots.cmb002(self, index, widget)`
- `slots/blender/selection.py::SelectionSlots.cmb002_init(self, widget)`
- `slots/maya/lighting.py::LightingSlots.b002(self)`
- `slots/maya/rigging.py::RiggingSlots.tb005(self, widget)`
- `slots/maya/rigging.py::RiggingSlots.tb005_init(self, widget)`
- `slots/maya/selection.py::SelectionSlots.cmb002(self, index, widget)`
- `slots/maya/selection.py::SelectionSlots.cmb002_init(self, widget)`

## Moved (2)

_Still resolvable at the same call site -- hoisted to a base class or re-exported from another module. NOT a removal: no alias or minor bump is owed._

- `slots/blender/uv.py::UvSlots.b000`
- `slots/maya/uv.py::UvSlots.b000`
