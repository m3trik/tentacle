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
- **Release** → resolves the bare `target` through `BlenderUiHandler.can_resolve` and shows the
  **wrapped clone of Blender's native menu** — bypassing the submenu.

Two file kinds:

- **Branch files** (`blender#startmenu` + 7 hubs — `mesh` / `curve` / `object` /
  `object_animation` / `rig` / `pose` / `render`) list self + child `MenuButton`s.
- **Leaf files** (19) hold exactly one self-referencing `MenuButton`.

### The tree

| Branch file | MenuButtons (bare targets) |
|:---|:---|
| `blender#startmenu.ui` | view, select, add, object, mesh, curve, object_animation, render |
| `mesh#submenu.ui` | mesh, vertex, edge, face, mesh_uv, mesh_normals |
| `curve#submenu.ui` | curve, ctrl_points, segments, surface |
| `object#submenu.ui` | object, modifiers, quick_effects |
| `object_animation#submenu.ui` | object_animation ("Animation"), rig ("Rigging") |
| `rig#submenu.ui` | rig, armature, pose, object_constraints |
| `pose#submenu.ui` | pose, constraints, ik |
| `render#submenu.ui` | render, window, help |

8 startmenu categories (matching Maya's count); Mesh / Curve / Render mirror Maya's
Mesh / Surfaces / Render hubs. The **Animation → Rigging chain** mirrors Maya's Key → Skeleton
branch: the startmenu "Animation" node wraps `VIEW3D_MT_object_animation`, its hub leads to
"Rigging" (`rig` — mode-adaptive like Select: the Pose menu in Pose mode, Edit Armature
otherwise), whose hub holds the subcategories (armature / pose / object constraints; pose keeps
its constraints / IK hub). The harvest removed the old `wm.call_menu` reachability constraint,
so Maya's Deform / Effects domains are covered too (`modifiers` / `quick_effects` under the
Object hub — Object-menu submenus with no menu-bar entry of their own). Still omitted: Maya's
Lighting/Shading (no viewport-native Blender menu).

`mesh_uv` / `mesh_normals` / `object_animation` / `rig` / `object_constraints` are compound or
shortened (not bare `uv` / `normals` / `animation` / `rigging` / `constraints`) because
`can_resolve` is global and those bare targets are taken — the shared `ui/` custom menus own
`animation` / `rigging` / `uv` / `normals`, and the pose node owns bare `constraints`. Maya
disambiguates the same way (`edit_mesh` / `mesh_display` vs bare `mesh`).

### Wrapped like Maya — harvested `draw()`, hosted in a Switchboard window

Maya harvests its live `QAction` rows into a floating Qt window (`MayaNativeMenus` /
`MayaUiHandler` in **mayatk**). Blender draws its menus in OpenGL — no `QAction`s to lift — but
every Blender menu **is a Python class**: `blendertk`'s `menu_harvest` executes the menu's
`draw(self, context)` against a recorder layout and rebuilds the recording as a `QMenu`
(operators via deferred `bpy.ops` invokes, enum submenus from RNA, boolean props as checkable
rows, `poll()`-greyed like Blender's own rows). Content is re-harvested on **every show**, so it
tracks the live mode and installed add-ons — nothing is hand-authored. Hosting is byte-for-byte
Maya's: the shared `uitk.EmbeddedMenuWidget` inside a Switchboard `MainWindow` — **pin header,
hides on `key_show` release**, exactly like every other marking-menu window. The mirror lives in
**blendertk**, exactly where Maya's lives in mayatk:

- `BlenderNativeMenus` (`blendertk/ui_utils/blender_native_menus.py`) — the bare-name → `*_MT_*`
  menu-id table (Select is mode-adaptive) + `get_menu` (the harvest → `EmbeddedMenuWidget` build,
  the mirror of `MayaNativeMenus.get_menu`).
- `BlenderUiHandler` (`blendertk/ui_utils/blender_ui_handler.py`) — `can_resolve` recognises those
  names; a per-name proxy is pre-registered so the release path (`get_ui`) resolves to it, and
  `show` swaps in the wrapped menu window (`_wrap_native_menu`).

So — like `maya_menus` — **these `MenuButton`s carry no tentacle slots**; `slots/blender/blender.py`
is just the base-name (`blender`) anchor the startmenu resolves to.

### Known deltas from Maya's wrap

- **Out-of-mode menus open with `poll()`-greyed rows, like Maya's always-openable menus.** A few
  native draws hard-deref `context.edit_object` (`VIEW3D_MT_edit_armature`,
  `VIEW3D_MT_edit_curve_ctrlpoints`), so the harvest injects the **active object** as
  `edit_object` when nothing is being edited — any object satisfies the deref and the rows come
  out greyed. Only when there is no active object at all does the release fall back to the
  hand-authored `<name>#submenu` overlay (Maya's exact fallback for an unbuildable menu).
- **Snapshot rows, minor fidelity gaps.** The clone is rebuilt per show (not live-updating while
  open, unlike Maya's real actions); asset-catalog entries (`layout.template_*`), icons, and
  shortcut hints are not reproduced.

Guarded by `test/blender/blender_menus_check.py` (headless, fresh Blender).

### Editing

After changing a `.ui`, refresh its companion:
`python -m uitk.compile tentacle/tentacle/ui/blender_menus --force`. Structure is guarded by
`test/test_blender_menu_nav.py` (offscreen); native-menu ids + firing by
`test/blender/blender_menus_check.py` (live Blender); hover-nav + anchor alignment by
`test/blender/chord_nav_check.py` (fresh GUI Blender, real cursor).

`MenuButton` **objectNames are free** — the marking menu pairs a launcher with the arriving
submenu's self-anchor by `target` (uitk `_find_pair_widget`), so there is no cross-file naming
convention to keep in sync. (`maya_menus`' global `iNNN` numbering is historical, not load-bearing.) Add any other `<name>#submenu.ui` /
`<name>#startmenu.ui` here only when a *shared* `ui/` menu needs a Blender-only override.
