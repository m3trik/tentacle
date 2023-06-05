# !/usr/bin/python
# coding=utf-8
from tentacle.slots.max import *
from tentacle.slots.pivot import Pivot


class Pivot_max(Pivot, SlotsMax):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        cmb = self.sb.pivot.draggableHeader.ctx_menu.cmb000
        items = [""]
        cmb.addItems_(items, "")

        ctx = self.sb.pivot.tb000.option_menu
        if not ctx.contains_items:
            ctx.add(
                "QCheckBox",
                setText="Reset Pivot Position",
                setObjectName="chk000",
                setChecked=True,
                setToolTip="",
            )
            ctx.add(
                "QCheckBox",
                setText="Reset Pivot Orientation",
                setObjectName="chk001",
                setChecked=True,
                setToolTip="",
            )
            ctx.add(
                "QCheckBox",
                setText="Reset XForm",
                setObjectName="chk013",
                setToolTip="",
            )

        ctx = self.sb.pivot.tb001.option_menu
        if not ctx.contains_items:
            ctx.add(
                "QRadioButton",
                setText="Component",
                setObjectName="chk002",
                setToolTip="Center the pivot on the center of the selected component's bounding box",
            )
            ctx.add(
                "QRadioButton",
                setText="Object",
                setObjectName="chk003",
                setChecked=True,
                setToolTip="Center the pivot on the center of the object's bounding box",
            )
            ctx.add(
                "QRadioButton",
                setText="World",
                setObjectName="chk004",
                setToolTip="Center the pivot on world origin.",
            )
            ctx.add(
                "QRadioButton",
                setText="Object Top",
                setObjectName="chk005",
                setToolTip="Move the pivot to the top of the object.",
            )
            ctx.add(
                "QRadioButton",
                setText="Object Bottom",
                setObjectName="chk006",
                setToolTip="Move the pivot to the bottom of the object.",
            )
            ctx.add(
                "QRadioButton",
                setText="Object Center Left",
                setObjectName="chk007",
                setToolTip="Move the pivot to the center left of the object.",
            )
            ctx.add(
                "QRadioButton",
                setText="Object Center Right",
                setObjectName="chk008",
                setToolTip="Move the pivot to the center right of the object.",
            )
            ctx.add(
                "QRadioButton",
                setText="Object Bottom Left",
                setObjectName="chk009",
                setToolTip="Move the pivot to the bottom left of the object.",
            )
            ctx.add(
                "QRadioButton",
                setText="Object Bottom Right",
                setObjectName="chk010",
                setToolTip="Move the pivot to the bottom right of the object.",
            )
            ctx.add(
                "QRadioButton",
                setText="Object Top Left",
                setObjectName="chk011",
                setToolTip="Move the pivot to the top left of the object.",
            )
            ctx.add(
                "QRadioButton",
                setText="Object Top Right",
                setObjectName="chk012",
                setToolTip="Move the pivot to the top right of the object.",
            )

    def cmb000(self, *args, **kwargs):
        """Editors"""
        cmb = self.sb.pivot.draggableHeader.ctx_menu.cmb000

        if index > 0:
            text = cmb.items[index]
            if text == "":
                pass
            cmb.setCurrentIndex(0)

    def tb000(self, *args, **kwargs):
        """Reset Pivot"""
        tb = self.sb.pivot.tb000

        if tb.option_menu.chk000:  # Reset Pivot Scale
            rt.ResetScale(rt.selection)  # Same as Hierarchy/Pivot/Reset Scale.

        if tb.option_menu.chk001:  # Reset Pivot Transform
            rt.ResetTransform(rt.selection)  # Same as Hierarchy/Pivot/Reset Transform.

        if tb.option_menu.chk013:  # reset XForm
            rt.ResetXForm(
                rt.selection
            )  # Same as the Reset XForm utility in the Utilities tab - applies XForm modifier to node, stores the current transformations in the gizmo and resets the object transformations.
            self.sb.message_box("ResetXForm " + str([obj.name for obj in rt.selection]))
            return

        # rt.ResetPivot(rt.selection) #Same as Hierarchy/Pivot/Reset Pivot.

    def tb001(self, *args, **kwargs):
        """Center Pivot"""
        tb = self.sb.pivot.tb001

        component = tb.option_menu.chk002.isChecked()
        object_ = tb.option_menu.chk003.isChecked()
        world = tb.option_menu.chk004.isChecked()
        objectTop = tb.option_menu.chk005.isChecked()
        objectBottom = tb.option_menu.chk006.isChecked()
        objectCenterLeft = tb.option_menu.chk007.isChecked()
        objectCenterRight = tb.option_menu.chk008.isChecked()
        objectBottomLeft = tb.option_menu.chk009.isChecked()
        objectBottomRight = tb.option_menu.chk010.isChecked()
        objectTopLeft = tb.option_menu.chk011.isChecked()
        objectTopRight = tb.option_menu.chk012.isChecked()

        if component:  # Set pivot points to the center of the component's bounding box.
            rt.CenterPivot(
                rt.selection
            )  # Same as Hierarchy/Pivot/Affect Pivot Only - Center to Object.
        elif object_:  ##Set pivot points to the center of the object's bounding box
            self.center_pivot(rt.selection)
        elif world:
            rt.selection.pivot = [0, 0, 0]  # center pivot world 0,0,0
        elif objectTop:
            [
                setattr(obj, "pivot", [obj.position.x, obj.position.y, obj.max.z])
                for obj in rt.selection
            ]  # Move the pivot to the top of the object
        elif objectBottom:
            [
                setattr(obj, "pivot", [obj.position.x, obj.position.y, obj.min.z])
                for obj in rt.selection
            ]  # Move the pivot to the bottom of the object
        elif objectCenterLeft:
            [
                setattr(obj, "pivot", [obj.min.x, obj.position.y, obj.position.z])
                for obj in rt.selection
            ]  # Move the pivot to the Center left of the object
        elif objectCenterRight:
            [
                setattr(obj, "pivot", [obj.max.x, obj.position.y, obj.position.z])
                for obj in rt.selection
            ]  # Move the pivot to the Center right of the object
        elif objectBottomLeft:
            [
                setattr(obj, "pivot", [obj.min.x, obj.position.y, obj.min.z])
                for obj in rt.selection
            ]  # Move the pivot to the Bottom left of the object
        elif objectBottomRight:
            [
                setattr(obj, "pivot", [obj.max.x, obj.position.y, obj.min.z])
                for obj in rt.selection
            ]  # Move the pivot to the Bottom right of the object
        elif objectTopLeft:
            [
                setattr(obj, "pivot", [obj.min.x, obj.position.y, obj.max.z])
                for obj in rt.selection
            ]  # Move the pivot to the Top left of the object
        elif objectTopRight:
            [
                setattr(obj, "pivot", [obj.max.x, obj.position.y, obj.max.z])
                for obj in rt.selection
            ]  # Move the pivot to the Topright of the object

    def b004(self, *args, **kwargs):
        """Bake Pivot"""
        print("Command does not exist:", __name__)

    def center_pivot(self, objects):
        """Center the rotation pivot on the given objects."""
        for obj in objects:
            rt.toolMode.coordsys(obj)  # Center Pivot Object
            obj.pivot = obj.center


# module name
print(__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------

# maxEval('max tti')

# maxEval('macros.run \"PolyTools\" \"TransformTools\")
