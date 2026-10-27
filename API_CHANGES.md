# tentacle — API Changes

_Diff vs the last release (origin/main @ 08708eb0)._

## Moved out (2)

- `slots/_normals.py::NormalsMixin` → `tentacle.slots.normals.NormalsSlots` (from 0.17.0)
- `slots/_normals.py::NormalsMixin.tb010_init` → `tentacle.slots.normals.NormalsSlots` (from 0.17.0)

## Added (41)

- `__init__.py::MOVED_NAMES(constant)`
- `slots/_slots.py::Slots.tk(self)`
- `slots/normals.py::NormalsSlots(class)`
- `slots/normals.py::NormalsSlots.b000(self)`
- `slots/normals.py::NormalsSlots.b001(self)`
- `slots/normals.py::NormalsSlots.b002(self)`
- `slots/normals.py::NormalsSlots.b004(self)`
- `slots/normals.py::NormalsSlots.b006(self)`
- `slots/normals.py::NormalsSlots.tb001(self, widget)`
- `slots/normals.py::NormalsSlots.tb001_init(self, widget)`
- `slots/normals.py::NormalsSlots.tb004(self, widget)`
- `slots/normals.py::NormalsSlots.tb004_init(self, widget)`
- `slots/normals.py::NormalsSlots.tb010(self, widget)`
- `slots/normals.py::NormalsSlots.tb010_init(self, widget)`
- `tcl.py::Tcl.register_shared(switchboard)`
- `ui/panels/duplicate_radial/duplicate_radial.py::DuplicateRadialSlots(class)`
- `ui/panels/duplicate_radial/duplicate_radial.py::DuplicateRadialSlots.b001_init(self, widget)`
- `ui/panels/duplicate_radial/duplicate_radial.py::DuplicateRadialSlots.header_init(self, widget)`
- `ui/panels/duplicate_radial/duplicate_radial.py::DuplicateRadialSlots.perform_operation(self, objects, contract=None)`
- `ui/panels/duplicate_radial/duplicate_radial.py::DuplicateRadialSlots.regroup_copies(self)`
- `ui/panels/duplicate_radial/duplicate_radial.py::DuplicateRadialSlots.s015_init(self, widget)`
- `ui/panels/duplicate_radial/duplicate_radial.py::DuplicateRadialSlots.s016_init(self, widget)`
- `ui/panels/emissive_groups/emissive_groups.py::EmissiveGroupsSlots(class)`
- `ui/panels/emissive_groups/emissive_groups.py::EmissiveGroupsSlots.b000(self) -> None`
- `ui/panels/emissive_groups/emissive_groups.py::EmissiveGroupsSlots.b001(self) -> None`
- `ui/panels/emissive_groups/emissive_groups.py::EmissiveGroupsSlots.b002(self) -> None`
- `ui/panels/emissive_groups/emissive_groups.py::EmissiveGroupsSlots.b003(self) -> None`
- `ui/panels/emissive_groups/emissive_groups.py::EmissiveGroupsSlots.compact_slots(self) -> None`
- `ui/panels/emissive_groups/emissive_groups.py::EmissiveGroupsSlots.header_init(self, widget) -> None`
- `ui/panels/emissive_groups/emissive_groups.py::EmissiveGroupsSlots.key_weights(self) -> None`
- `ui/panels/emissive_groups/emissive_groups.py::EmissiveGroupsSlots.make_weights_keyable(self) -> None`
- `ui/panels/emissive_groups/emissive_groups.py::EmissiveGroupsSlots.remove_group(self) -> None`
- `ui/panels/emissive_groups/emissive_groups.py::EmissiveGroupsSlots.remove_keyable_weights(self) -> None`
- `ui/panels/emissive_groups/emissive_groups.py::EmissiveGroupsSlots.republish_export(self) -> None`
- `ui/panels/emissive_groups/emissive_groups.py::EmissiveGroupsSlots.select_members(self) -> None`
- `ui/panels/emissive_groups/emissive_groups.py::EmissiveGroupsSlots.tb000(self, widget) -> None`
- `ui/panels/emissive_groups/emissive_groups.py::EmissiveGroupsSlots.tb000_init(self, widget) -> None`
- `ui/panels/emissive_groups/emissive_groups.py::EmissiveGroupsSlots.tbl000_init(self, widget) -> None`
- `ui/panels/emissive_groups/emissive_groups.py::EmissiveGroupsSlots.txt000_init(self, widget) -> None`
- `ui/panels/emissive_groups/emissive_groups.py::EmissiveGroupsSlots.weights_all_off(self) -> None`
- `ui/panels/emissive_groups/emissive_groups.py::EmissiveGroupsSlots.weights_all_on(self) -> None`

## Moved (22)

_Still resolvable at the same call site -- hoisted to a base class or re-exported from another module. NOT a removal: no alias or minor bump is owed._

- `slots/blender/normals.py::NormalsSlots`
- `slots/blender/normals.py::NormalsSlots.b000`
- `slots/blender/normals.py::NormalsSlots.b001`
- `slots/blender/normals.py::NormalsSlots.b002`
- `slots/blender/normals.py::NormalsSlots.b004`
- `slots/blender/normals.py::NormalsSlots.b006`
- `slots/blender/normals.py::NormalsSlots.tb001`
- `slots/blender/normals.py::NormalsSlots.tb001_init`
- `slots/blender/normals.py::NormalsSlots.tb004`
- `slots/blender/normals.py::NormalsSlots.tb004_init`
- `slots/blender/normals.py::NormalsSlots.tb010`
- `slots/maya/normals.py::NormalsSlots`
- `slots/maya/normals.py::NormalsSlots.b000`
- `slots/maya/normals.py::NormalsSlots.b001`
- `slots/maya/normals.py::NormalsSlots.b002`
- `slots/maya/normals.py::NormalsSlots.b004`
- `slots/maya/normals.py::NormalsSlots.b006`
- `slots/maya/normals.py::NormalsSlots.tb001`
- `slots/maya/normals.py::NormalsSlots.tb001_init`
- `slots/maya/normals.py::NormalsSlots.tb004`
- `slots/maya/normals.py::NormalsSlots.tb004_init`
- `slots/maya/normals.py::NormalsSlots.tb010`
