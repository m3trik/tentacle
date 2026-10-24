# tentacle — API Changes

_Diff vs the last release (origin/main @ 99a96f5c)._

## Removed (9)

- `slots/blender/materials.py::MaterialsSlots.b002` — was `(self, widget=None)`
- `slots/blender/materials.py::MaterialsSlots.cmb002` — was `(self, index, widget)`
- `slots/blender/materials.py::MaterialsSlots.cmb002_init` — was `(self, widget)`
- `slots/blender/materials.py::MaterialsSlots.tb000` — was `(self, widget)`
- `slots/blender/materials.py::MaterialsSlots.tb000_init` — was `(self, widget)`
- `slots/maya/materials.py::MaterialsSlots.b002` — was `(self, widget)`
- `slots/maya/materials.py::MaterialsSlots.cmb002_init` — was `(self, widget)`
- `slots/maya/materials.py::MaterialsSlots.tb000` — was `(self, widget)`
- `slots/maya/materials.py::MaterialsSlots.tb000_init` — was `(self, widget)`

## Added (13)

- `slots/_materials.py::MaterialsMixin.b006(self, widget=None)`
- `slots/_materials.py::MaterialsMixin.b006_init(self, widget)`
- `slots/_materials.py::MaterialsMixin.b014(self, widget=None)`
- `slots/_materials.py::MaterialsMixin.b028(self, widget=None)`
- `slots/_materials.py::MaterialsMixin.b029(self, widget=None)`
- `slots/_materials.py::MaterialsMixin.b030(self, widget=None)`
- `slots/_materials.py::MaterialsMixin.b031(self, widget=None)`
- `slots/_materials.py::MaterialsMixin.b032(self, widget=None)`
- `slots/_materials.py::MaterialsMixin.b033(self, widget=None)`
- `slots/_materials.py::MaterialsMixin.header_init(self, widget)`
- `slots/_materials.py::MaterialsMixin.lbl002(self, widget=None)`
- `slots/_materials.py::MaterialsMixin.tbl000_init(self, widget)`
- `slots/_materials.py::MaterialsMixin.txt000_init(self, widget)`

## Moved (6)

_Still resolvable at the same call site -- hoisted to a base class or re-exported from another module. NOT a removal: no alias or minor bump is owed._

- `slots/blender/materials.py::MaterialsSlots.b006`
- `slots/blender/materials.py::MaterialsSlots.b014`
- `slots/blender/materials.py::MaterialsSlots.lbl002`
- `slots/maya/materials.py::MaterialsSlots.b006`
- `slots/maya/materials.py::MaterialsSlots.b014`
- `slots/maya/materials.py::MaterialsSlots.lbl002`
