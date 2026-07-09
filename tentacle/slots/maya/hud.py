# !/usr/bin/python
# coding=utf-8
import os
from typing import Optional

import maya.cmds as cmds
import pythontk as ptk
import mayatk as mtk
from tentacle.slots._hud_warnings import HudWarningsMixin
from tentacle.slots.maya._slots_maya import SlotsMaya


class StatusMixin:
    def insert_scene_status(self, hud) -> None:
        # New version? (Update via the settings header's "Update Package"
        # button — the old auto-update option is gone, and its stale
        # ``sb.settings.tb000.menu.auto_update`` widget-chain crashed here:
        # ``sb.settings`` is a SettingsManager now, not the settings window.)
        if self.new_version_available:
            hud.insertText(
                f'New release available: <font style="color: Cyan;">{self.latest_ver}</font>'
            )
        # Symmetry status
        if cmds.symmetricModelling(q=True, symmetry=True):
            axis = cmds.symmetricModelling(q=True, axis=True)
            hud.insertText(
                f'Symmetry Axis: <font style="color: Yellow;">{axis.upper()}</font>'
            )
        # Xform constraints
        xformConstraint = cmds.xformConstraint(query=True, type=True)
        if xformConstraint and xformConstraint != "none":
            hud.insertText(
                f'Xform Constraint: <font style="color: Cyan;">{xformConstraint}</font>'
            )
        # Workspace
        workspace = mtk.get_env_info("workspace_dir")
        if workspace and workspace != "default":
            hud.insertText(
                f'Workspace: <font style="color: Yellow;">{workspace}</font>'
            )
        # Units
        sceneUnits = cmds.currentUnit(q=True, fullName=True, linear=True)
        hud.insertText(f'Units: <font style="color: Yellow;">{sceneUnits}</font>')
        # Frame rate
        frame_rate_key = cmds.currentUnit(q=True, time=True)
        frame_rate_val = ptk.VidUtils.FRAME_RATES.get(frame_rate_key)
        if frame_rate_val is None:
            frame_rate_display = "Unknown Frame Rate"
        else:
            frame_rate_display = f"{frame_rate_val} fps {frame_rate_key.upper()}"
        hud.insertText(
            f'Frame Rate: <font style="color: Yellow;">{frame_rate_display}</font>'
        )


class SelectionMixin:
    def insert_selection_info(self, hud, selection) -> None:
        if cmds.selectMode(q=True, object=True) and cmds.selectType(
            q=True, allObjects=True
        ):
            numberOfSelected = len(selection)
            if numberOfSelected < 11:
                name_and_type = [
                    f'<font style="color: Yellow;">{i}<font style="color: LightGray;">:{cmds.objectType(i)}<br/>'
                    for i in selection
                ]
                name_and_type_str = "".join(name_and_type)
            else:
                name_and_type_str = ""
            hud.insertText(
                f'Selected: <font style="color: Yellow;">{numberOfSelected}<br/>{name_and_type_str}'
            )

            if numberOfSelected == 1 and cmds.nodeType(selection[0]) == "transform":
                shape_node = cmds.listRelatives(
                    selection[0], shapes=True, noIntermediate=True, fullPath=True
                ) or []
                if shape_node and cmds.objectType(shape_node[0]) == "mesh":
                    all_locked = cmds.polyNormalPerVertex(
                        f"{shape_node[0]}.vtxFace[*][*]",
                        query=True,
                        allLocked=True,
                    )
                    if all_locked and any(all_locked):
                        hud.insertText(
                            'Normals: <font style="color: Red;">LOCKED</font>'
                        )
                    instance_paths = cmds.ls(shape_node[0], allPaths=True) or []
                    if len(instance_paths) > 1:
                        hud.insertText(
                            f'Instances: <font style="color: Yellow;">{len(instance_paths)}</font>'
                        )

            objectFaces = cmds.polyEvaluate(selection, face=True)
            if isinstance(objectFaces, int):
                hud.insertText(f'Faces: <font style="color: Yellow;">{objectFaces:,d}')
            objectTris = cmds.polyEvaluate(selection, triangle=True)
            if isinstance(objectTris, int):
                hud.insertText(f'Tris: <font style="color: Yellow;">{objectTris:,d}')
            objectUVs = cmds.polyEvaluate(selection, uvcoord=True)
            if isinstance(objectUVs, int):
                hud.insertText(f'UVs: <font style="color: Yellow;">{objectUVs:,d}')

    def insert_component_info(self, hud, selection) -> None:
        type_, num_selected, total_num = None, None, None
        if cmds.selectType(q=True, vertex=1):
            type_ = "Verts"
            num_selected = cmds.polyEvaluate(vertexComponent=1)
            total_num = cmds.polyEvaluate(selection, vertex=1)
        elif cmds.selectType(q=True, edge=1):
            type_ = "Edges"
            num_selected = cmds.polyEvaluate(edgeComponent=1)
            total_num = cmds.polyEvaluate(selection, edge=1)
        elif cmds.selectType(q=True, facet=1):
            type_ = "Faces"
            num_selected = cmds.polyEvaluate(faceComponent=1)
            total_num = cmds.polyEvaluate(selection, face=1)
        elif cmds.selectType(q=True, polymeshUV=1):
            type_ = "UVs"
            num_selected = cmds.polyEvaluate(uvComponent=1)
            total_num = cmds.polyEvaluate(selection, uvcoord=1)

        if type_:
            hud.insertText(
                f'Selected {type_}: <font style="color: Yellow;">{num_selected} <font style="color: LightGray;">/{total_num}'
            )


class WarningsMixin(HudWarningsMixin):
    """Maya HUD warnings — the framework lives in the shared
    :class:`tentacle.slots._hud_warnings.HudWarningsMixin`; this carries the
    Maya-specific checks (autosave / framerate / autosave-scene-open).
    """

    WARNING_DEFS = (
        {
            "key": "chk_warn_framerate",
            "icon": "⚠",
            "color": "Orange",
            "label": "FPS",
            "check": lambda self: self._warn_check_default_framerate(),
            "describe": lambda self: self._warn_describe_default_framerate(),
        },
        {
            "key": "chk_warn_autosave_off",
            "icon": "⚠",
            "color": "Red",
            "label": "Autosave",
            "check": lambda self: self._warn_check_autosave_off(),
            "describe": lambda self: 'Autosave: <font style="color: Red;">DISABLED</font> &mdash; enable it in Preferences to avoid losing work after a crash.',
        },
        {
            "key": "chk_warn_autosave_open",
            "icon": "⚠",
            "color": "Red",
            "label": "Autosave Open",
            "check": lambda self: self._warn_check_autosave_scene_open(),
            "describe": lambda self: 'Open file is an <font style="color: Red;">AUTOSAVE</font> &mdash; save to your main scene before continuing or your work will be lost on the next autosave cycle.',
        },
    )

    def _scene_is_unsaved(self) -> bool:
        """True if no saved scene file exists on disk (new/untitled scene)."""
        try:
            scene = str(cmds.file(query=True, sceneName=True) or "")
            return not scene or not os.path.isfile(scene)
        except (RuntimeError, TypeError):
            return False

    # ---- individual checks (kept lightweight: O(1) Maya state queries) ----

    def _warn_check_default_framerate(self) -> bool:
        try:
            default = cmds.optionVar(q="workingUnitTimeDefault")
        except (RuntimeError, TypeError):
            default = "film"  # Maya factory default
        return cmds.currentUnit(q=True, time=True) == default

    def _warn_describe_default_framerate(self) -> str:
        key = cmds.currentUnit(q=True, time=True)
        val = ptk.VidUtils.FRAME_RATES.get(key)
        display = f"{val} fps {key.upper()}" if val else key
        return (
            f'Frame Rate: <font style="color: Orange;">{display}</font> '
            "matches Maya's default &mdash; verify this is intentional."
        )

    def _warn_check_autosave_off(self) -> bool:
        return not cmds.autoSave(q=True, enable=True)

    def _warn_check_autosave_scene_open(self) -> bool:
        scene = str(cmds.file(query=True, sceneName=True) or "")
        if not scene:
            return False
        scene_norm = os.path.normpath(scene).lower()
        try:
            folders = mtk.EnvUtils.find_autosave_directories()
        except Exception:
            folders = []
        for folder in folders:
            try:
                if scene_norm.startswith(os.path.normpath(folder).lower()):
                    return True
            except (OSError, ValueError):
                continue
        return False


class HudSlots(
    SlotsMaya, ptk.PackageManager, StatusMixin, SelectionMixin, WarningsMixin
):
    """HUD Slots for Maya, providing scene and selection information."""

    _hud_request_token: int = 0

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        mayapy = os.path.join(mtk.get_env_info("install_path"), "bin", "mayapy.exe")
        self.start_version_check(package_name="tentacletk", python_path=mayapy)

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

        selection = cmds.ls(sl=True) or []
        if not selection:
            self.insert_scene_status(hud)
        else:
            if cmds.selectMode(q=True, object=True):
                self.insert_selection_info(hud, selection)
            elif cmds.selectMode(q=True, component=1):
                self.insert_component_info(hud, selection)

        method = self.sb.prev_slot
        if method:
            # Get button text from last used command
            hud.insertText(
                'Prev Command: <font style="color: Yellow;">{}'.format(method.__doc__)
            )


# --------------------------------------------------------------------------------------------

# module name
# print(__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
