# !/usr/bin/python
# coding=utf-8
import bpy
import blendertk as btk
from tentacle.slots.blender._slots_blender import SlotsBlender


class Blender(SlotsBlender):
    """Blender port of Maya's both-button menu (``F12 + L + R`` → the DCC's native menu sets).

    Slot resolves to the ``blender#startmenu`` UI by class name (the switchboard maps the UI's
    base stem ``blender`` → capitalized ``Blender``, the ``Editors``/``Cameras`` convention; the
    file-name fallback is not used).

    Maya's ``maya#startmenu`` harvests live ``QAction``s out of Maya's Qt menu bar
    (``MayaNativeMenus``). Blender draws its UI in OpenGL — there are **no** ``QMenu``/``QAction``
    objects to harvest — so each wedge instead pops Blender's **own** native menu at the cursor via
    ``btk.call_native_menu`` (``bpy.ops.wm.call_menu``). Always accurate, add-on/mode-aware, with
    ~zero content maintenance (the don't-reinvent answer, same as the native Batch Rename / Outliner).

    The popup is deferred one timer tick so the Qt overlay has hidden and Blender has regained OS
    focus first (see :meth:`_call_menu`). Each wedge resolves its menu by ``context.mode`` at click
    time — object-mode menus in Object mode, edit-mesh menus in Edit mode — and the edit-only wedges
    (Vertex/Edge/Face/UV) disable themselves in Object mode.
    """

    # objectName -> menu resolution. ``"*"`` = mode-agnostic; otherwise per-mode menu idname.
    # ``edit_label`` relabels the wedge in edit mode (Object → Mesh). Single source of truth: every
    # idname is validated against ``btk.menu_exists`` by the headless no-dead-links check, so no
    # wedge can dead-end on a renamed/removed Blender menu.
    _BUTTON_MENUS = {
        "b000": {"label": "Add",       "OBJECT": "VIEW3D_MT_add",           "EDIT_MESH": "VIEW3D_MT_mesh_add"},
        "b001": {"label": "Object",    "OBJECT": "VIEW3D_MT_object",        "EDIT_MESH": "VIEW3D_MT_edit_mesh", "edit_label": "Mesh"},
        "b002": {"label": "Select",    "OBJECT": "VIEW3D_MT_select_object", "EDIT_MESH": "VIEW3D_MT_select_edit_mesh"},
        "b003": {"label": "Transform", "*": "VIEW3D_MT_transform"},
        "b004": {"label": "Snap",      "*": "VIEW3D_MT_snap"},
        "b005": {"label": "View",      "*": "VIEW3D_MT_view"},
        "b006": {"label": "Vertex",    "EDIT_MESH": "VIEW3D_MT_edit_mesh_vertices"},
        "b007": {"label": "Edge",      "EDIT_MESH": "VIEW3D_MT_edit_mesh_edges"},
        "b008": {"label": "Face",      "EDIT_MESH": "VIEW3D_MT_edit_mesh_faces"},
        "b009": {"label": "UV",        "EDIT_MESH": "VIEW3D_MT_uv_map"},
    }
    # Edit-only wedges relabel/disable per mode (the rest keep their authored .ui label + stay on).
    _MODE_SENSITIVE = ("b001", "b006", "b007", "b008", "b009")

    def __init__(self, switchboard):
        super().__init__(switchboard)
        self.ui = self.sb.loaded_ui.blender

    # ------------------------------------------------------------------ helpers
    @staticmethod
    def _mode():
        """Current interaction mode bucketed to the two menu sets we route between."""
        return "EDIT_MESH" if bpy.context.mode == "EDIT_MESH" else "OBJECT"

    def _menu_for(self, name):
        """The native menu idname for ``name`` in the current mode (``None`` if N/A here)."""
        spec = self._BUTTON_MENUS.get(name, {})
        return spec.get("*") or spec.get(self._mode())

    def _init_button(self, widget):
        """Per-show init: relabel Object↔Mesh and disable edit-only wedges outside Edit mode.
        Fires each time the radial is shown, so it always reflects the live mode."""
        spec = self._BUTTON_MENUS.get(widget.objectName())
        if not spec:
            return
        edit = self._mode() == "EDIT_MESH"
        widget.setText(spec["edit_label"] if edit and spec.get("edit_label") else spec["label"])
        if not (spec.get("*") or spec.get("OBJECT")):  # edit-only menu
            widget.setEnabled(edit)
            widget.setToolTip("" if edit else f"{spec['label']} menu — available in Edit Mode.")

    def _open(self, name):
        """Resolve + pop the native menu for a wedge (or message when N/A in this mode)."""
        idname = self._menu_for(name)
        if not idname:
            spec = self._BUTTON_MENUS.get(name, {})
            self.sb.message_box(f"'{spec.get('label', name)}' is only available in Edit Mode.")
            return
        self._call_menu(idname)

    def _call_menu(self, idname):
        """Pop Blender's native menu one timer tick later — by then the gesture has unwound (the Qt
        overlay hid and ``_restore_blender_foreground`` handed OS focus back), so the menu pops at
        the cursor instead of behind the always-on-top overlay."""
        def _popup():
            try:
                btk.call_native_menu(idname)
            except Exception:
                pass
            return None  # one-shot

        bpy.app.timers.register(_popup, first_interval=0.05)

    # ------------------------------------------------------------------ wedges
    def b000(self):
        """Add (Object mode) / Mesh ▸ Add (Edit mode)"""
        self._open("b000")

    def b001_init(self, widget):
        """Relabel Object ↔ Mesh by mode."""
        self._init_button(widget)

    def b001(self):
        """Object menu (Object mode) / Mesh menu (Edit mode)"""
        self._open("b001")

    def b002(self):
        """Select menu (mode-appropriate)"""
        self._open("b002")

    def b003(self):
        """Transform menu"""
        self._open("b003")

    def b004(self):
        """Snap menu"""
        self._open("b004")

    def b005(self):
        """View menu"""
        self._open("b005")

    def b006_init(self, widget):
        """Vertex — Edit-mode only (disabled in Object mode)."""
        self._init_button(widget)

    def b006(self):
        """Vertex menu (Edit mode)"""
        self._open("b006")

    def b007_init(self, widget):
        """Edge — Edit-mode only (disabled in Object mode)."""
        self._init_button(widget)

    def b007(self):
        """Edge menu (Edit mode)"""
        self._open("b007")

    def b008_init(self, widget):
        """Face — Edit-mode only (disabled in Object mode)."""
        self._init_button(widget)

    def b008(self):
        """Face menu (Edit mode)"""
        self._open("b008")

    def b009_init(self, widget):
        """UV — Edit-mode only (disabled in Object mode)."""
        self._init_button(widget)

    def b009(self):
        """UV menu (Edit mode)"""
        self._open("b009")


# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
