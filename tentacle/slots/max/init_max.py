# !/usr/bin/python
# coding=utf-8
from tentacle.slots.max import *
from tentacle.slots.init import Init


class Init_max(Init, Slots_max):
    """ """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        try:
            self.sb.init.hud_text.shown.connect(self.construct_hud)

        except AttributeError:  # (an inherited class)
            pass

    def construct_hud(self):
        """Add current scene attributes to a lineEdit.
        Only those with relevant values will be displayed.
        """
        hud = self.sb.init.hud_text

        try:
            selection = rt.selection
        except AttributeError:
            selection = None

        if selection:
            if len(selection) is 1:
                obj = selection[0]
                symmetry = obj.modifiers[rt.Symmetry]
                if symmetry:
                    int_ = symmetry.axis
                    axis = {0: "x", 1: "y", 2: "z"}
                    hud.insertText(
                        'Symmetry Axis: <font style="color: Yellow;">{}'.format(
                            axis[int_].upper()
                        )
                    )  # symmetry axis

                level = rt.subObjectLevel if rt.subObjectLevel else 0
                if level == 0:  # object level
                    numberOfSelected = len(selection)
                    if numberOfSelected < 11:
                        name_and_type = [
                            '<font style="color: Yellow;">{0}<font style="color: LightGray;">:{1}'.format(
                                obj.name, rt.classOf(obj.baseObject)
                            )
                            for obj in selection
                        ]
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

                elif level > 0:  # component level
                    obj = selection[0]
                    objType = rt.classOf(obj.baseObject)

                    if objType == rt.Editable_Poly or objType == rt.Edit_Poly:
                        if level == 1:  # get vertex info
                            type_ = "Verts"
                            components = Slots_max.bitArrayToArray(
                                rt.polyop.getVertSelection(obj)
                            )
                            total_num = rt.polyop.getNumVerts(obj)

                        elif level == 2:  # get edge info
                            type_ = "Edges"
                            components = Slots_max.bitArrayToArray(
                                rt.polyop.getEdgeSelection(obj)
                            )
                            total_num = rt.polyop.getNumEdges(obj)

                        elif level == 3:  # get border info
                            type_ = "Borders"
                            # rt.polyop.SetSelection #Edge ((polyOp.getOpenEdges $) as bitarray)
                            components = Slots_max.bitArrayToArray(
                                rt.polyop.getBorderSelection(obj)
                            )
                            total_num = rt.polyop.getNumBorders(obj)

                        elif level == 4:  # get face info
                            type_ = "Faces"
                            components = Slots_max.bitArrayToArray(
                                rt.polyop.getFaceSelection(obj)
                            )
                            total_num = rt.polyop.getNumFaces(obj)

                        elif level == 5:  # get element info
                            type_ = "Elements"
                            components = Slots_max.bitArrayToArray(
                                rt.polyop.getElementSelection(obj)
                            )
                            total_num = rt.polyop.getNumElements(obj)

                        try:
                            hud.insertText(
                                'Selected {}: <font style="color: Yellow;">{} <font style="color: LightGray;">/{}'.format(
                                    type_, len(components), total_num
                                )
                            )  # selected components
                        except NameError:
                            pass

        method = self.sb.prev_command
        if method:
            hud.insertText(
                'Prev Command: <font style="color: Yellow;">{}'.format(method.__doc__)
            )  # get button text from last used command


# module name
print(__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------


# --------------------------------------------------------------------------------------------
# deprecated:
# --------------------------------------------------------------------------------------------
