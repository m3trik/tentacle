# tentacle — API Changes

_Diff vs the last release (origin/main @ f5d097be)._

## Added (2)

- `slots/_scene.py::SceneMixin.tb001(self, widget)`
- `slots/_scene.py::SceneMixin.tb001_init(self, widget)`

## Moved (4)

_Still resolvable at the same call site -- hoisted to a base class or re-exported from another module. NOT a removal: no alias or minor bump is owed._

- `slots/blender/scene.py::SceneSlots.tb001`
- `slots/blender/scene.py::SceneSlots.tb001_init`
- `slots/maya/scene.py::SceneSlots.tb001`
- `slots/maya/scene.py::SceneSlots.tb001_init`
