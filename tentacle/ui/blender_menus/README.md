# `ui/blender_menus/`

Blender-specific marking-menu overlays, layered on top of the shared `ui/` menus by
`TclBlender` (`ui_source=("ui", "ui/blender_menus")`) — the Blender counterpart to
`ui/maya_menus/`.

Empty by design: the shared `ui/` menus drive Blender until a menu genuinely needs a
Blender-only variant. Add a `<name>#submenu.ui` (or `<name>#startmenu.ui`) here only when
overriding/extending the shared version for Blender.
