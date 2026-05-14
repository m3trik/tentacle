# tentacle — API Changes

_Diff vs prior baseline. Generated 2026-05-14._

## Removed (6)

- `bench/option_box.py::TentacleOptionBoxBench` — was `(class)`
- `bench/option_box.py::TentacleOptionBoxBench.post_switchboard` — was `(self, sb) -> None`
- `bench/option_box.py::TentacleOptionBoxBench.setup_switchboard` — was `(self)`
- `bench/run_in_maya.py::main` — was `() -> int`
- `slots/maya/uv.py::UvSlots.b002` — was `(self)`
- `slots/maya/uv.py::UvSlots.b022` — was `(self)`

## Added (9)

- `slots/maya/editors.py::Editors.b010(self)`
- `slots/maya/scene.py::SceneSlots.b014(self)`
- `slots/maya/scene.py::SceneSlots.b014_init(self, widget)`
- `slots/maya/uv.py::UvSlots.b029(self, widget)`
- `slots/maya/uv.py::UvSlots.b029_init(self, widget)`
- `slots/maya/uv.py::UvSlots.b030(self, widget)`
- `slots/maya/uv.py::UvSlots.b030_init(self, widget)`
- `slots/maya/uv.py::UvSlots.tb022(self, widget)`
- `slots/maya/uv.py::UvSlots.tb022_init(self, widget)`
