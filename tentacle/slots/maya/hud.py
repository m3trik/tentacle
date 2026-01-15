# !/usr/bin/python
# coding=utf-8
import os
from typing import Optional

try:
    import pymel.core as pm
except ImportError as error:
    print(__file__, error)
import pythontk as ptk
import mayatk as mtk
from tentacle.slots.maya import SlotsMaya


class StatusMixin:
    def insert_scene_status(self, hud) -> None:
        # New version?
        if self.new_version_available:
            hud.insertText(
                f'New release available: <font style="color: Cyan;">{self.latest_ver}</font>'
            )
            if self.sb.preferences.tb000.menu.auto_update:
                self.sb.check_for_update()
        # Autosave status
        if not pm.autoSave(q=True, enable=True):
            hud.insertText('Autosave: <font style="color: Red;">OFF</font>')
        # Symmetry status
        if pm.symmetricModelling(q=True, symmetry=True):
            axis = pm.symmetricModelling(q=True, axis=True)
            hud.insertText(
                f'Symmetry Axis: <font style="color: Yellow;">{axis.upper()}</font>'
            )
        # Xform constraints
        xformConstraint = pm.xformConstraint(query=True, type=True)
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
        sceneUnits = pm.currentUnit(q=True, fullName=True, linear=True)
        hud.insertText(f'Units: <font style="color: Yellow;">{sceneUnits}</font>')
        # Frame rate
        frame_rate_key = pm.currentUnit(q=True, time=True)
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
        if pm.selectMode(q=True, object=True) and pm.selectType(
            q=True, allObjects=True
        ):
            numberOfSelected = len(selection)
            if numberOfSelected < 11:
                name_and_type = [
                    f'<font style="color: Yellow;">{i.name()}<font style="color: LightGray;">:{pm.objectType(i)}<br/>'
                    for i in selection
                ]
                name_and_type_str = "".join(name_and_type)
            else:
                name_and_type_str = ""
            hud.insertText(
                f'Selected: <font style="color: Yellow;">{numberOfSelected}<br/>{name_and_type_str}'
            )

            if numberOfSelected == 1 and pm.nodeType(selection[0]) == "transform":
                shape_node = pm.listRelatives(
                    selection[0], shapes=True, noIntermediate=True, fullPath=True
                )
                if shape_node and isinstance(shape_node[0], pm.nt.Mesh):
                    vertex_faces = shape_node[0].vtxFace
                    all_locked = pm.polyNormalPerVertex(
                        vertex_faces, query=True, allLocked=True
                    )
                    if all_locked and any(all_locked):
                        hud.insertText(
                            'Normals: <font style="color: Red;">LOCKED</font>'
                        )
                    if (
                        pm.objectType(shape_node[0], isType="mesh")
                        and shape_node[0].isInstanced()
                    ):
                        hud.insertText(
                            f'Instances: <font style="color: Yellow;">{shape_node[0].instanceCount()}</font>'
                        )

            objectFaces = pm.polyEvaluate(selection, face=True)
            if isinstance(objectFaces, int):
                hud.insertText(f'Faces: <font style="color: Yellow;">{objectFaces:,d}')
            objectTris = pm.polyEvaluate(selection, triangle=True)
            if isinstance(objectTris, int):
                hud.insertText(f'Tris: <font style="color: Yellow;">{objectTris:,d}')
            objectUVs = pm.polyEvaluate(selection, uvcoord=True)
            if isinstance(objectUVs, int):
                hud.insertText(f'UVs: <font style="color: Yellow;">{objectUVs:,d}')

    def insert_component_info(self, hud, selection) -> None:
        type_, num_selected, total_num = None, None, None
        if pm.selectType(q=True, vertex=1):
            type_ = "Verts"
            num_selected = pm.polyEvaluate(vertexComponent=1)
            total_num = pm.polyEvaluate(selection, vertex=1)
        elif pm.selectType(q=True, edge=1):
            type_ = "Edges"
            num_selected = pm.polyEvaluate(edgeComponent=1)
            total_num = pm.polyEvaluate(selection, edge=1)
        elif pm.selectType(q=True, facet=1):
            type_ = "Faces"
            num_selected = pm.polyEvaluate(faceComponent=1)
            total_num = pm.polyEvaluate(selection, face=1)
        elif pm.selectType(q=True, polymeshUV=1):
            type_ = "UVs"
            num_selected = pm.polyEvaluate(uvComponent=1)
            total_num = pm.polyEvaluate(selection, uvcoord=1)

        if type_:
            hud.insertText(
                f'Selected {type_}: <font style="color: Yellow;">{num_selected} <font style="color: LightGray;">/{total_num}'
            )


class HudSlots(SlotsMaya, ptk.PackageManager, StatusMixin, SelectionMixin):
    """HUD Slots for Maya, providing scene and selection information."""

    _hud_request_token: int = 0

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        mayapy = os.path.join(mtk.get_env_info("install_path"), "bin", "mayapy.exe")
        self.start_version_check(package_name="tentacletk", python_path=mayapy)

        self.ui = self.sb.loaded_ui.hud_startmenu
        self.ui.hudTextEdit.shown.connect(self.request_hud_build)

    def request_hud_build(self) -> None:
        """Start a new HUD build request, only the latest token will be used."""
        self._hud_request_token += 1
        my_token = self._hud_request_token
        self.sb.QtCore.QTimer.singleShot(500, lambda: self._delayed_hud_build(my_token))

    def _delayed_hud_build(self, token: int) -> None:
        if token != self._hud_request_token:
            return  # Outdated request, ignore.
        if not (self.ui.isVisible() and self.ui.hudTextEdit.isVisible()):
            return
        self.construct_hud()

    def construct_hud(self) -> None:
        hud = self.ui.hudTextEdit

        selection = pm.ls(sl=True)
        if not selection:
            self.insert_scene_status(hud)
        else:
            if pm.selectMode(q=True, object=True):
                self.insert_selection_info(hud, selection)
            elif pm.selectMode(q=True, component=1):
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
