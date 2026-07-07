# `ui/blender_menus/`

Blender-specific marking-menu overlays, layered on top of the shared `ui/` menus by
`TclBlender` (`ui_source=("ui", "ui/blender_menus")`) — the Blender counterpart to
`ui/maya_menus/`.

## Both-button chord menu — a thin launcher for Blender's own menus

`F12 + L + R` opens `blender#startmenu.ui`. **These menus are not part of tentacle's custom
marking-menu system** (polygons / cameras / editors); like `ui/maya_menus/`, they are a fast
radial way to reach the DCC's **built-in** menus. The `.ui` files author almost nothing — they are
pure navigation, and the real menu is Blender's own.

## Exact parity with `maya_menus` — pure MenuButtons, flat files

Every node — startmenu, hub, and leaf — is a `MenuButton` (there are **no** plain `QPushButton`s,
exactly like `maya_menus`). Each `MenuButton`'s `target` is a **bare** node name, and every target
`X` has its own **flat** `X#submenu.ui` — mirroring Maya's `edit_mesh#submenu.ui` /
`select#submenu.ui` (never a nested `blender#mesh#vertex#submenu`).

Each `MenuButton` does two things:

- **Hover** → opens `<target>#submenu` (the drill-in: a hub, or a one-button leaf).
- **Release** → resolves the bare `target` through `BlenderUiHandler.can_resolve` and pops
  Blender's **native** menu — bypassing the submenu.

Two file kinds:

- **Branch files** (`blender#startmenu` + 5 hubs — `mesh` / `curve` / `armature` / `pose` /
  `render`) list self + child `MenuButton`s.
- **Leaf files** (16) hold exactly one self-referencing `MenuButton`.

### The tree

| Branch file | MenuButtons (bare targets) |
|:---|:---|
| `blender#startmenu.ui` | view, select, add, object, mesh, curve, armature, render |
| `mesh#submenu.ui` | mesh, vertex, edge, face, mesh_uv, mesh_normals |
| `curve#submenu.ui` | curve, ctrl_points, segments, surface |
| `armature#submenu.ui` | armature, pose |
| `pose#submenu.ui` | pose, constraints, ik |
| `render#submenu.ui` | render, window, help |

8 startmenu categories (matching Maya's count); Mesh / Curve / Render mirror Maya's
Mesh / Surfaces / Render hubs; Armature → Pose mirrors Maya's Key → Skeleton 3-level pattern.
**Deliberately omitted** (no `wm.call_menu`-reachable Blender equivalent — Properties-panel /
modifier-stack driven): Maya's Lighting/Shading, Deform, Effects/dynamics.

`mesh_uv` / `mesh_normals` are compound (not bare `uv` / `normals`) because the shared `ui/` custom
menus already own those bare targets and `can_resolve` is global — Maya disambiguates the same way
(`edit_mesh` / `mesh_display` vs bare `mesh`).

### Wrapped, not recreated — the resolution lives in blendertk

Maya harvests its live `QAction` rows into a floating Qt window (`MayaNativeMenus` / `MayaUiHandler`
in **mayatk**). Blender draws its UI in OpenGL — no `QAction`s to harvest — so the faithful wrap is
`btk.call_native_menu("VIEW3D_MT_add")`, which invokes Blender's **real** menu via `wm.call_menu`
(all native depth, add-on/mode-aware, zero content to maintain). The Blender mirror lives in
**blendertk**, exactly where Maya's lives in mayatk:

- `BlenderNativeMenus` (`blendertk/ui_utils/blender_native_menus.py`) — the bare-name → `*_MT_*`
  menu-id table (Select is mode-adaptive, like Maya's harvested Select menu).
- `BlenderUiHandler` (`blendertk/ui_utils/blender_ui_handler.py`) — `can_resolve` recognises those
  names; a per-name proxy is pre-registered so the release path (`get_ui`) resolves to it, and
  `show` pops the native menu.

So — like `maya_menus` — **these `MenuButton`s carry no tentacle slots**; `slots/blender/blender.py`
is just the base-name (`blender`) anchor the startmenu resolves to.

### Editing

After changing a `.ui`, refresh its companion:
`python -m uitk.compile tentacle/tentacle/ui/blender_menus --force`. Structure is guarded by
`test/test_blender_menu_nav.py` (offscreen); native-menu ids + firing by
`test/blender/blender_menus_check.py` (live Blender). Add any other `<name>#submenu.ui` /
`<name>#startmenu.ui` here only when a *shared* `ui/` menu needs a Blender-only override.
