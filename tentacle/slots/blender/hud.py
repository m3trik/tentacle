# !/usr/bin/python
# coding=utf-8
import os

import bpy
import blendertk as btk
from tentacle.slots._hud_warnings import HudWarningsMixin
from tentacle.slots.blender._slots_blender import SlotsBlender


def _effective_fps() -> float:
    """The scene frame rate as the user understands it — ``fps / fps_base``. A fractional
    NTSC-style scene stores fps=24, fps_base=1.001 (23.98 fps); reading raw ``fps`` alone
    misreports it as 24."""
    render = bpy.context.scene.render
    return render.fps / render.fps_base


class StatusMixin:
    def insert_scene_status(self, hud) -> None:
        # Symmetry status (per-mesh mirror flags on the active mesh)
        active = bpy.context.view_layer.objects.active
        if active and active.type == "MESH":
            axes = "".join(
                axis.upper()
                for axis in "xyz"
                if getattr(active.data, f"use_mirror_{axis}", False)
            )
            if axes:
                hud.insertText(
                    f'Symmetry Axis: <font style="color: Yellow;">{axes}</font>'
                )
        # Workspace (current-workspace resolver: pin → workspace.mel root → the .blend's dir)
        workspace = btk.get_env_info("workspace_dir")
        if workspace:
            hud.insertText(
                f'Workspace: <font style="color: Yellow;">{workspace}</font>'
            )
        # Units
        us = bpy.context.scene.unit_settings
        units = f"{us.system.lower()} {us.length_unit.lower()}" if us.system != "NONE" else "none"
        hud.insertText(f'Units: <font style="color: Yellow;">{units}</font>')
        # Frame rate (effective — see _effective_fps)
        hud.insertText(
            f'Frame Rate: <font style="color: Yellow;">{round(_effective_fps(), 2):g} fps</font>'
        )


class SelectionMixin:
    @staticmethod
    def _poly_counts(objects):
        """(faces, tris, uvs) across the given mesh objects — C-speed via foreach_get
        (a Python per-polygon loop would hang the HUD on dense photogrammetry meshes)."""
        import numpy as np

        faces = tris = uvs = 0
        for o in objects:
            if o.type != "MESH":
                continue
            me = o.data
            n = len(me.polygons)
            faces += n
            if n:
                loop_total = np.empty(n, dtype=np.int32)
                me.polygons.foreach_get("loop_total", loop_total)
                tris += int(np.clip(loop_total - 2, 0, None).sum())
            if me.uv_layers.active:
                uvs += len(me.uv_layers.active.data)
        return faces, tris, uvs

    def insert_selection_info(self, hud, selection) -> None:
        numberOfSelected = len(selection)
        if numberOfSelected < 11:
            name_and_type = [
                f'<font style="color: Yellow;">{o.name}<font style="color: LightGray;">:{o.type.lower()}<br/>'
                for o in selection
            ]
            name_and_type_str = "".join(name_and_type)
        else:
            name_and_type_str = ""
        hud.insertText(
            f'Selected: <font style="color: Yellow;">{numberOfSelected}<br/>{name_and_type_str}'
        )

        instances = btk.get_instances(selection)
        if instances:
            hud.insertText(
                f'Instances: <font style="color: Yellow;">{len(instances)}</font>'
            )

        faces, tris, uvs = self._poly_counts(selection)
        if faces:
            hud.insertText(f'Faces: <font style="color: Yellow;">{faces:,d}')
            hud.insertText(f'Tris: <font style="color: Yellow;">{tris:,d}')
        if uvs:
            hud.insertText(f'UVs: <font style="color: Yellow;">{uvs:,d}')

    def insert_component_info(self, hud, active) -> None:
        """Selected/total component counts for the mesh being edited (cheap:
        ``total_*_sel`` are maintained by Blender for exactly this purpose)."""
        active.update_from_editmode()  # sync the *_sel totals from the live edit-mesh
        me = active.data
        vert, edge, face = bpy.context.tool_settings.mesh_select_mode
        if face:
            type_, num_selected, total_num = "Faces", me.total_face_sel, len(me.polygons)
        elif edge:
            type_, num_selected, total_num = "Edges", me.total_edge_sel, len(me.edges)
        else:
            type_, num_selected, total_num = "Verts", me.total_vert_sel, len(me.vertices)
        hud.insertText(
            f'Selected {type_}: <font style="color: Yellow;">{num_selected} '
            f'<font style="color: LightGray;">/{total_num}'
        )


class WarningsMixin(HudWarningsMixin):
    """Blender HUD warnings — the framework lives in the shared
    :class:`tentacle.slots._hud_warnings.HudWarningsMixin`; this carries the
    Blender-specific checks (autosave / default framerate / autosave-file-open).
    """

    _DEFAULT_FPS = 24  # Blender factory default

    WARNING_DEFS = (
        {
            "key": "chk_warn_framerate",
            "icon": "⚠",
            "color": "Orange",
            "label": "FPS",
            # Effective rate (fps / fps_base) — a 23.98 scene (fps=24, base=1.001) is
            # NOT the default and must not be flagged/reported as 24.
            "check": lambda self: _effective_fps() == self._DEFAULT_FPS,
            "describe": lambda self: (
                f'Frame Rate: <font style="color: Orange;">{round(_effective_fps(), 2):g} fps</font> '
                "matches Blender's default &mdash; verify this is intentional."
            ),
        },
        {
            "key": "chk_warn_autosave_off",
            "icon": "⚠",
            "color": "Red",
            "label": "Autosave",
            "check": lambda self: not bpy.context.preferences.filepaths.use_auto_save_temporary_files,
            "describe": lambda self: 'Autosave: <font style="color: Red;">DISABLED</font> &mdash; enable it in Preferences to avoid losing work after a crash.',
        },
        {
            "key": "chk_warn_autosave_open",
            "icon": "⚠",
            "color": "Red",
            "label": "Autosave Open",
            "check": lambda self: self._warn_check_autosave_file_open(),
            "describe": lambda self: 'Open file is an <font style="color: Red;">AUTOSAVE</font> &mdash; save to your main scene before continuing or your work will be lost on the next autosave cycle.',
        },
    )

    def _scene_is_unsaved(self) -> bool:
        """True if no saved .blend exists on disk (new/untitled scene)."""
        filepath = bpy.data.filepath
        return not filepath or not os.path.isfile(filepath)

    def _warn_check_autosave_file_open(self) -> bool:
        """True when the open .blend lives in Blender's autosave/temp directory."""
        filepath = bpy.data.filepath
        if not filepath:
            return False
        import tempfile

        temp_dir = (
            bpy.context.preferences.filepaths.temporary_directory
            or tempfile.gettempdir()
        )
        return os.path.normpath(filepath).lower().startswith(
            os.path.normpath(temp_dir).lower()
        )


class HudSlots(SlotsBlender, StatusMixin, SelectionMixin, WarningsMixin):
    """HUD Slots for Blender, providing scene and selection information."""

    _hud_request_token: int = 0

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.ui = self.sb.loaded_ui.hud_startmenu
        self.ui.hudTextEdit.shown.connect(self.request_hud_build)
        self._active_warnings: list = []

    def request_hud_build(self) -> None:
        """Start a new HUD build request, only the latest token will be used."""
        self._hud_request_token += 1
        my_token = self._hud_request_token

        # Lightweight pre-build phase: evaluate opted-in warnings synchronously
        # and surface their icons immediately so the user gets feedback even if
        # they dismiss the HUD before the delayed full build runs.
        self._active_warnings = self.evaluate_warnings()
        self.insert_warning_icons(self.ui.hudTextEdit, self._active_warnings)

        self.sb.QtCore.QTimer.singleShot(500, lambda: self._delayed_hud_build(my_token))

    def _delayed_hud_build(self, token: int) -> None:
        if token != self._hud_request_token:
            return  # Outdated request, ignore.
        if not (self.ui.isVisible() and self.ui.hudTextEdit.isVisible()):
            return
        self.construct_hud()

    def construct_hud(self) -> None:
        hud = self.ui.hudTextEdit

        self.insert_warning_details(hud, self._active_warnings)

        selection = self.selected_objects()
        active = bpy.context.view_layer.objects.active
        if active and active.mode == "EDIT" and active.type == "MESH":
            self.insert_component_info(hud, active)
        elif selection:
            self.insert_selection_info(hud, selection)
        else:
            self.insert_scene_status(hud)

        method = self.sb.prev_slot
        if method:
            hud.insertText(
                'Prev Command: <font style="color: Yellow;">{}'.format(method.__doc__)
            )


# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
