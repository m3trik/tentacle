# !/usr/bin/python
# coding=utf-8
from tentacle.slots.maya import *
from tentacle.slots.init import Init


class Init_maya(Init, SlotsMaya):
    """ """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        try:  # set the 'hud_text' textEdit to connect to the 'contruct_hud' method on show.
            self.sb.init.hud_text.shown.connect(self.construct_hud)

        except AttributeError as error:  # (an inherited class)
            print(error)

    def construct_hud(self):
        """Add current scene attributes to the hud lineEdit.
        Only those with relevant values will be displayed.
        """
        hud = self.sb.init.hud_text

        try:
            selection = pm.ls(selection=1)
        except NameError:
            return

        if not selection:
            autoSaveState = pm.autoSave(q=True, enable=True)
            if not autoSaveState:
                hud.insertText(
                    'Autosave: <font style="color: {};">{}'.format(
                        "Green" if autoSaveState else "Red",
                        "On" if autoSaveState else "Off",
                    )
                )  # symmetry axis

            sceneUnits = pm.currentUnit(query=1, fullName=1, linear=1)
            hud.insertText(
                'Units: <font style="color: Yellow;">{}'.format(sceneUnits)
            )  # symmetry axis

            symmetry = pm.symmetricModelling(query=1, symmetry=1)
            if symmetry:
                axis = pm.symmetricModelling(query=1, axis=1)
                hud.insertText(
                    'Symmetry Axis: <font style="color: Yellow;">{}'.format(
                        axis.upper()
                    )
                )  # symmetry axis

            xformConstraint = pm.xformConstraint(query=True, type=True)
            if xformConstraint == "none":
                xformConstraint = None
            if xformConstraint:
                hud.insertText(
                    'Xform Constraint: <font style="color: Yellow;">{}'.format(
                        xformConstraint
                    )
                )  # transform constraits

        else:
            if pm.selectMode(query=1, object=1):  # object mode:
                if pm.selectType(query=1, allObjects=1):  # get object/s
                    selectedObjects = pm.ls(selection=1)  # , objectsOnly=1)
                    numberOfSelected = len(selectedObjects)
                    if numberOfSelected < 11:
                        name_and_type = [
                            '<font style="color: Yellow;">{0}<font style="color: LightGray;">:{1}<br/>'.format(
                                i.name(), pm.objectType(i)
                            )
                            for i in selectedObjects
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

                    objectFaces = pm.polyEvaluate(selectedObjects, face=True)
                    if type(objectFaces) == int:
                        hud.insertText(
                            'Faces: <font style="color: Yellow;">{}'.format(
                                objectFaces, ",d"
                            )
                        )  # add commas each 3 decimal places.

                    objectTris = pm.polyEvaluate(selectedObjects, triangle=True)
                    if type(objectTris) == int:
                        hud.insertText(
                            'Tris: <font style="color: Yellow;">{}'.format(
                                objectTris, ",d"
                            )
                        )  # add commas each 3 decimal places.

                    objectUVs = pm.polyEvaluate(selectedObjects, uvcoord=True)
                    if type(objectUVs) == int:
                        hud.insertText(
                            'UVs: <font style="color: Yellow;">{}'.format(
                                objectUVs, ",d"
                            )
                        )  # add commas each 3 decimal places.

            elif pm.selectMode(query=1, component=1):  # component mode:
                if pm.selectType(query=1, vertex=1):  # get vertex selection info
                    type_ = "Verts"
                    num_selected = pm.polyEvaluate(vertexComponent=1)
                    total_num = pm.polyEvaluate(selection, vertex=1)

                elif pm.selectType(query=1, edge=1):  # get edge selection info
                    type_ = "Edges"
                    num_selected = pm.polyEvaluate(edgeComponent=1)
                    total_num = pm.polyEvaluate(selection, edge=1)

                elif pm.selectType(query=1, facet=1):  # get face selection info
                    type_ = "Faces"
                    num_selected = pm.polyEvaluate(faceComponent=1)
                    total_num = pm.polyEvaluate(selection, face=1)

                elif pm.selectType(query=1, polymeshUV=1):  # get uv selection info
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


# module name
print(__name__)
# ======================================================================
# Notes
# ======================================================================


# deprecated -------------------------------------
