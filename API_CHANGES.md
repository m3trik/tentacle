# tentacle — API Changes

_Diff vs the last release (origin/main @ ea99eb62). Generated 2026-08-20._

## Removed (11)

- `slots/_materials.py::MaterialsMixin.lbl005` — was `(self)`
- `slots/blender/hud.py::SelectionMixin` — was `(class)`
- `slots/blender/hud.py::SelectionMixin.insert_component_info` — was `(self, hud, active) -> None`
- `slots/blender/hud.py::SelectionMixin.insert_selection_info` — was `(self, hud, selection) -> None`
- `slots/blender/materials.py::MaterialsSlots.lbl007` — was `(self)`
- `slots/blender/materials.py::MaterialsSlots.lbl007_global` — was `(self)`
- `slots/maya/hud.py::SelectionMixin` — was `(class)`
- `slots/maya/hud.py::SelectionMixin.insert_component_info` — was `(self, hud, selection) -> None`
- `slots/maya/hud.py::SelectionMixin.insert_selection_info` — was `(self, hud, selection) -> None`
- `slots/maya/materials.py::MaterialsSlots.lbl007` — was `(self)`
- `slots/maya/materials.py::MaterialsSlots.lbl007_global` — was `(self)`

## Added (16)

- `slots/_preferences.py::PreferencesMixin.cmb006(self, index, widget)`
- `slots/_preferences.py::PreferencesMixin.cmb006_init(self, widget)`
- `slots/_preferences.py::PreferencesMixin.header_init(self, widget)`
- `slots/_preferences.py::PreferencesMixin.tb000(self)`
- `slots/_settings.py::SettingsMixin.ecosystem_dists(cls, installed=None)`
- `slots/_slots.py::Slots.gate_on_app(self, widget, resolve_spec) -> bool`
- `slots/_slots.py::Slots.recheck_app_gates(self) -> int`
- `slots/blender/hud.py::HudSelectionMixin(class)`
- `slots/blender/hud.py::HudSelectionMixin.insert_component_info(self, hud, active) -> None`
- `slots/blender/hud.py::HudSelectionMixin.insert_selection_info(self, hud, selection) -> None`
- `slots/maya/hud.py::HudSelectionMixin(class)`
- `slots/maya/hud.py::HudSelectionMixin.insert_component_info(self, hud, selection) -> None`
- `slots/maya/hud.py::HudSelectionMixin.insert_selection_info(self, hud, selection) -> None`
- `tcl.py::Tcl.declared_dists(cls, host=None, include_self=True)`
- `tcl.py::Tcl.engine_dists(cls, host)`
- `tcl.py::Tcl.engine_install_hint(cls, host=None)`
