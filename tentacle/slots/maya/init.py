# !/usr/bin/python
# coding=utf-8
import os
import threading

try:
    import pymel.core as pm
except ImportError as error:
    print(__file__, error)
import pythontk as ptk
import mayatk as mtk
from tentacle.slots.maya import SlotsMaya


class Init(SlotsMaya):
    """ """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Start the version check in a separate thread
        threading.Thread(target=self.check_version, daemon=True).start()

        self.ui = self.sb.get_ui("init#startmenu")
        self.ui.hud_text.shown.connect(self.construct_hud)

    @property
    def new_version_available(self):
        """Check if a new version is available; initiates version check on first access."""
        try:
            return self.installed_ver != self.latest_ver
        except AttributeError:
            return

    def check_version(self):
        """Check the installed and latest versions in a separate thread."""
        mayapy = os.path.join(mtk.get_env_info("install_path"), "bin", "mayapy.exe")
        pkg_mgr = ptk.PkgManager(python_path=mayapy)
        this_pkg = "tentacletk"
        self._installed_ver = pkg_mgr.installed_version(this_pkg)
        self._latest_ver = pkg_mgr.latest_version(this_pkg)

    def construct_hud(self):
        """Add current scene attributes to the hud lineEdit.
        Only those with relevant values will be displayed.
        """
        hud = self.ui.hud_text

        try:
            selection = pm.ls(sl=True)
        except NameError:
            return

        if not selection:
            if self.new_version_available:
                hud.insertText(
                    f'New release available: <font style="color: Cyan;">{self._latest_ver}</font>'
                )

            # Display the autosave state if it is not on
            if not pm.autoSave(q=True, enable=True):
                hud.insertText('Autosave: <font style="color: Red;">OFF</font>')

            # Display the symmetry state if it is on
            if pm.symmetricModelling(q=True, symmetry=True):
                axis = pm.symmetricModelling(q=True, axis=True)
                hud.insertText(
                    'Symmetry Axis: <font style="color: Yellow;">{}</font>'.format(
                        axis.upper()
                    )
                )

            # Display any transform constraints
            xformConstraint = pm.xformConstraint(query=True, type=True)
            if xformConstraint and xformConstraint != "none":
                hud.insertText(
                    'Xform Constraint: <font style="color: Cyan;">{}</font>'.format(
                        xformConstraint
                    )
                )

            # Display current workspace if one is set
            workspace = mtk.get_env_info("workspace_dir")
            if workspace and workspace != "default":
                hud.insertText(
                    'Project: <font style="color: Yellow;">{}</font>'.format(workspace)
                )

            # Display the scene units
            sceneUnits = pm.currentUnit(q=True, fullName=True, linear=True)
            hud.insertText(
                'Units: <font style="color: Yellow;">{}</font>'.format(sceneUnits)
            )

            # Display animation frame rate
            frame_rate_key = pm.currentUnit(q=True, time=True)
            frame_rate_display = mtk.format_frame_rate_str(frame_rate_key)
            hud.insertText(
                f'Frame Rate: <font style="color: Yellow;">{frame_rate_display}</font>'
            )

        else:
            if pm.selectMode(q=True, object=True):  # object mode:
                if pm.selectType(q=True, allObjects=True):  # get object/s
                    numberOfSelected = len(selection)
                    if numberOfSelected < 11:
                        name_and_type = [
                            '<font style="color: Yellow;">{0}<font style="color: LightGray;">:{1}<br/>'.format(
                                i.name(), pm.objectType(i)
                            )
                            for i in selection
                        ]  # ie. ['pCube1:transform', 'pSphere1:transform']
                        name_and_type_str = str(name_and_type).translate(
                            str.maketrans("", "", ",[]'")
                        )  # format as single string. remove brackets, single quotes, and commas.
                    else:
                        name_and_type_str = ""  # if more than 10 objects selected, don't list each object.
                    hud.insertText(
                        'Selected: <font style="color: Yellow;">{0}<br/>{1}'.format(
                            numberOfSelected, name_and_type_str
                        )
                    )  # currently selected objects by name and type.

                    if (
                        numberOfSelected == 1
                        and pm.nodeType(selection[0]) == "transform"
                    ):
                        # Get the shape node associated with the transform
                        shape_node = pm.listRelatives(
                            selection[0],
                            shapes=True,
                            noIntermediate=True,
                            fullPath=True,
                        )
                        if shape_node and isinstance(shape_node[0], pm.nt.Mesh):
                            # Get all vertex faces from the shape node
                            vertex_faces = shape_node[0].vtxFace
                            # Check if any of the vertex faces have locked normals
                            all_locked = pm.polyNormalPerVertex(
                                vertex_faces, query=True, allLocked=True
                            )
                            if all_locked:
                                if any(all_locked):
                                    hud.insertText(
                                        'Normals: <font style="color: Red;">LOCKED</font>'
                                    )
                            # Check if the object is instanced
                            instance_count = (
                                pm.objectType(shape_node[0], isType="mesh")
                                and shape_node[0].isInstanced()
                            )
                            if instance_count:
                                hud.insertText(
                                    'Instances: <font style="color: Yellow;">{}</font>'.format(
                                        shape_node[0].instanceCount()
                                    )
                                )

                    objectFaces = pm.polyEvaluate(selection, face=True)
                    if type(objectFaces) == int:
                        hud.insertText(
                            'Faces: <font style="color: Yellow;">{}'.format(
                                objectFaces, ",d"
                            )
                        )  # add commas each 3 decimal places.

                    objectTris = pm.polyEvaluate(selection, triangle=True)
                    if type(objectTris) == int:
                        hud.insertText(
                            'Tris: <font style="color: Yellow;">{}'.format(
                                objectTris, ",d"
                            )
                        )  # add commas each 3 decimal places.

                    objectUVs = pm.polyEvaluate(selection, uvcoord=True)
                    if type(objectUVs) == int:
                        hud.insertText(
                            'UVs: <font style="color: Yellow;">{}'.format(
                                objectUVs, ",d"
                            )
                        )  # add commas each 3 decimal places.

            elif pm.selectMode(q=True, component=1):  # component mode:
                if pm.selectType(q=True, vertex=1):  # get vertex selection info
                    type_ = "Verts"
                    num_selected = pm.polyEvaluate(vertexComponent=1)
                    total_num = pm.polyEvaluate(selection, vertex=1)

                elif pm.selectType(q=True, edge=1):  # get edge selection info
                    type_ = "Edges"
                    num_selected = pm.polyEvaluate(edgeComponent=1)
                    total_num = pm.polyEvaluate(selection, edge=1)

                elif pm.selectType(q=True, facet=1):  # get face selection info
                    type_ = "Faces"
                    num_selected = pm.polyEvaluate(faceComponent=1)
                    total_num = pm.polyEvaluate(selection, face=1)

                elif pm.selectType(q=True, polymeshUV=1):  # get uv selection info
                    type_ = "UVs"
                    num_selected = pm.polyEvaluate(uvComponent=1)
                    total_num = pm.polyEvaluate(selection, uvcoord=1)

                try:
                    hud.insertText(
                        'Selected {}: <font style="color: Yellow;">{} <font style="color: LightGray;">/{}'.format(
                            type_, num_selected, total_num
                        )
                    )  # selected components
                except NameError:
                    pass

        method = self.sb.prev_slot
        if method:
            hud.insertText(
                'Prev Command: <font style="color: Yellow;">{}'.format(method.__doc__)
            )  # get button text from last used command


# --------------------------------------------------------------------------------------------

# module name
# print(__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
