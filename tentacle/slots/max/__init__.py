# !/usr/bin/python
# coding=utf-8
import os

from PySide2 import QtGui, QtWidgets, QtCore

try:  # 3ds Max dependancies
    from pymxs import runtime as rt

    maxEval = rt.execute  # rt.executeScriptFile

except ImportError as error:
    print(__file__, error)
    rt = None
    maxEval = lambda s: None

from tentacle.slots import Slots
from .staticUi_max import StaticUi_max

staticUiInitialized = False


class Slots_max(Slots):
    """App specific methods inherited by all other slot classes."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        global staticUiInitialized
        if not staticUiInitialized:
            StaticUi_max.__init__(self, *args, **kwargs)
            staticUiInitialized = True

        # -----------------------------------------------------------------------------------------------
        "ATTRIBUTES:"

    # -----------------------------------------------------------------------------------------------
    @staticmethod
    def getAttributesMax(node, inc=[], exc=[]):
        """Get node attributes and their corresponding values as a dict.

        Parameters:
                node (obj): Transform node.
                inc (list): Attributes to include. All other will be omitted. Exclude takes dominance over include. Meaning, if the same attribute is in both lists, it will be excluded.
                exc (list): Attributes to exclude from the returned dictionay. ie. [u'Position',u'Rotation',u'Scale',u'renderable',u'isHidden',u'isFrozen',u'selected']

        Returns:
                (dict) {'string attribute': current value}

        # print (rt.showProperties(obj))
        # print (rt.getPropNames(obj))
        """
        if not all((inc, exc)):
            exc = [
                "getmxsprop",
                "setmxsprop",
                "typeInHeight",
                "typeInLength",
                "typeInPos",
                "typeInWidth",
                "typeInDepth",
                "typeInRadius",
                "typeInRadius1",
                "typeInRadius2",
                "typeinCreationMethod",
                "edgeChamferQuadIntersections",
                "edgeChamferType",
                "hemisphere",
                "realWorldMapSize",
                "mapcoords",
            ]

        attributes = {
            attr: node.getmxsprop(attr)
            for attr in [str(n) for n in rt.getPropNames(node)]
            if not attr in exc and (attr in inc if inc else attr not in inc)
        }

        return attributes

    @staticmethod
    def setAttributesMax(node, attributes):
        """Set history node attributes using the transform node.

        Parameters:
                node (obj): Transform node.
                attributes (dict): Attributes and their correponding value to set. ie. {'string attribute': value}
        """
        [
            setattr(node, attribute, value)
            for attribute, value in attributes.items()
            if attribute and value
        ]

        rt.redrawViews()

        # ---------------------------------------------------------------------------------------------
        "COMPONENT LEVEL:"

    # ---------------------------------------------------------------------------------------------

    @staticmethod
    def getFacesByNormal(normal, tolerance, includeBackFaces):
        """Get all faces in a mesh/poly that have normals within the given tolerance range.

        Parameters:
                normal (obj): Polygon face normal.
                tolerance (float) = Normal tolerance.
                includeBackFaces (bool): Include back-facing faces.
        """
        maxEval(
            """
		local collected_faces = for i = 1 to num_faces
			where (local norm_vect = normalize (get_face_normal obj i)).x <= (normal.x + tolerance.x) AND norm_vect.x >= (normal.x - tolerance.x) AND
				norm_vect.y <= (normal.y + tolerance.y) AND norm_vect.y >= (normal.y - tolerance.y) AND
				norm_vect.z <= (normal.z + tolerance.z) AND norm_vect.z >= (normal.z - tolerance.z) collect i

		if includeBackFaces do
		(
			local collected_back_faces = for i = 1 to num_faces
				where (local norm_vect = - (normalize (get_face_normal obj i))).x <= (normal.x + tolerance.x) AND norm_vect.x >= (normal.x - tolerance.x) AND
					norm_vect.y <= (normal.y + tolerance.y) AND norm_vect.y >= (normal.y - tolerance.y) AND
					norm_vect.z <= (normal.z + tolerance.z) AND norm_vect.z >= (normal.z - tolerance.z) collect i
			join collected_faces collected_back_faces
		)
		"""
        )
        return collected_faces

    @staticmethod
    def getEdgesByAngle(minAngle, maxAngle):
        """Get edges between min and max angle.

        Parameters:
                minAngle (float) = minimum search angle tolerance.
                maxAngle (float) = maximum search angle tolerance.

        Returns:
                (list) edges within the given range.
        """
        edgelist = []
        for obj in rt.selection:
            for edge in list(range(1, obj.edges.count)):
                faces = rt.polyOp.getEdgeFaces(obj, edge)
                if faces.count == 2:
                    v1 = rt.polyop.getFaceNormal(obj, faces[0])
                    v2 = rt.polyop.getFaceNormal(obj, faces[1])

                    angle = rt.acos(rt.dot(rt.normalize(v1), rt.normalize(v2)))
                    if angle >= minAngle and angle <= maxAngle:
                        edgelist.append(edge)

            return edgelist

    @staticmethod
    def getComponents(obj=None, componentType=None, selection=False, returnType="List"):
        """Get the components of the given type. (editable mesh or polygon)

        Parameters:
                obj (obj): An Editable mesh or Editable polygon object. If None; the first currently selected object will be used.
                componentType (str)(int): The desired component mask. (valid: 'vertex', 'vertices', 'edge', 'edges', 'face', 'faces').
                selection (bool): Filter to currently selected components.
                returnType (type) = The desired returned object type. (valid: 'Array', 'BitArray', 'List'(default))

        Returns:
                (array) Dependant on flags.

        ex. getComponents(obj, 'vertices', selection=True, returnType='BitArray')
        """
        if not obj:
            obj = rt.selection[0]

        if not any(
            (rt.isKindOf(obj, rt.Editable_Mesh), rt.isKindOf(obj, rt.Editable_Poly))
        ):  # filter for valid objects.
            return "# Error: Invalid object type: {} #".format(obj)

        c = (
            []
        )  # for cases when no componentType given; initialize c with an empty list.
        if componentType in ("vertex", "vertices"):
            if selection:
                try:
                    c = rt.polyop.getVertSelection(obj)  # polygon
                except:
                    c = rt.getVertSelection(obj)  # mesh
            else:
                try:
                    c = range(1, rt.polyop.getNumVerts(obj))
                except:
                    c = range(1, rt.getNumVerts(obj))

        elif componentType in ("edge", "edges"):
            if selection:
                try:
                    c = rt.polyop.getEdgeSelection(obj)  # polygon
                except:
                    c = rt.getEdgeSelection(obj)  # mesh
            else:
                try:
                    c = range(1, rt.polyop.getNumEdges(obj))
                except:
                    c = range(1, obj.edges.count)

        elif componentType in ("face", "faces"):
            if selection:
                try:
                    c = rt.polyop.getFaceSelection(obj)  # polygon
                except:
                    c = rt.getFaceSelection(obj)  # mesh
            else:
                try:
                    c = range(1, rt.polyop.getNumFaces(obj))
                except:
                    c = range(1, obj.faces.count)

        if returnType in ("Array", "List"):
            result = Slots_max.bitArrayToArray(c)
            if returnType is "List":
                result = list(result)
        else:
            result = Slots_max.arrayToBitArray(c)

        return result

    @staticmethod
    def convertComponents(
        obj=None, components=None, convertFrom=None, convertTo=None, returnType="List"
    ):
        """Convert the components to the given type. (editable mesh, editable poly)

        Parameters:
                obj (obj): An Editable mesh or Editable polygon object. If None; the first currently selected object will be used.
                components (list): The component id's of the given object.  If None; all components of the given convertFrom type will be used.
                convertFrom (str): Starting component type. (valid: 'vertex', 'vertices', 'edge', 'edges', 'face', 'faces').
                convertTo (str): Resulting component type.  (valid: 'vertex', 'vertices', 'edge', 'edges', 'face', 'faces').
                returnType (type) = The desired returned object type. (valid: 'Array', 'BitArray', 'List'(default))

        Returns:
                (array) Component ID's. ie. [1, 2, 3]

        ex. obj = rt.selection[0]
                edges = rt.getEdgeSelection(obj)
                faces = convertComponents(obj, edges, 'edges', 'faces')
                rt.setFaceSelection(obj, faces)
        """
        if not obj:
            obj = rt.selection[0]
        if not components:
            components = Slots_max.getComponents(obj, convertFrom)

        if not any(
            (rt.isKindOf(obj, rt.Editable_Mesh), rt.isKindOf(obj, rt.Editable_Poly))
        ):  # filter for valid objects.
            return "# Error: Invalid object type: {} #".format(obj)

        if convertFrom in ("vertex", "vertices") and convertTo in (
            "edge",
            "edges",
        ):  # vertex to edge
            c = rt.polyop.getEdgesUsingVert(obj, components)

        elif convertFrom in ("vertex", "vertices") and convertTo in (
            "face",
            "faces",
        ):  # vertex to edge
            c = rt.polyop.getFacesUsingVert(obj, components)

        elif convertFrom in ("edge", "edges") and convertTo in (
            "vertex",
            "vertices",
        ):  # vertex to edge
            c = rt.polyop.getVertsUsingEdge(obj, components)

        elif convertFrom in ("edge", "edges") and convertTo in (
            "face",
            "faces",
        ):  # vertex to edge
            c = rt.polyop.getFacesUsingEdge(obj, components)

        elif convertFrom in ("face", "faces") and convertTo in (
            "vertex",
            "vertices",
        ):  # vertex to edge
            c = rt.polyop.getVertsUsingFace(obj, components)

        elif convertFrom in ("face", "faces") and convertTo in (
            "edge",
            "edges",
        ):  # vertex to edge
            c = rt.polyop.getEdgesUsingFace(obj, components)

        else:
            return "# Error: Cannot convert from {} to type: {}: #".format(
                convertFrom, convertTo
            )

        if returnType in ("Array", "List"):
            result = Slots_max.bitArrayToArray(c)
            if returnType is "List":
                result = list(result)
        else:
            result = Slots_max.arrayToBitArray(c)

        return result

        # ----------------------------------------------------------------------------------------------------------
        ":"

    # ----------------------------------------------------------------------------------------------------------

    @staticmethod
    def arrayToBitArray(array):
        """Convert an integer array to a bitArray.

        Parameters:
                array (list): The array that will be converted to a bitArray.
        """
        maxEval("fn _arrayToBitArray a = (return a as bitArray)")
        result = rt._arrayToBitArray(array)

        return result

    @staticmethod
    def bitArrayToArray(bitArray):
        """Convert a bitArray to an integer array.

        Parameters:
                bitArray (list): The bitArray that will be converted to a standard array.
        """
        maxEval("fn _bitArrayToArray b = (return b as array)")
        result = rt._bitArrayToArray(bitArray)

        return result

    @staticmethod
    def toggleMaterialOverride(checker=False):
        """Toggle override all materials in the scene.

        Parameters:
                checker (bool): Override with UV checkered material.
        """
        state = Slots.cycle([0, 1], "OverrideMateridal")  # toggle 0/1
        if state:
            rt.actionMan.executeAction(0, "63574")  # Views: Override Off
        else:
            if checker:
                rt.actionMan.executeAction(
                    0, "63573"
                )  # Views: Override with UV Checker
            else:
                rt.actionMan.executeAction(
                    0, "63572"
                )  # Views: Override with Fast Shader
        rt.redrawViews

    @staticmethod
    def setSubObjectLevel(level):
        """
        Parameters:
                level (int): set component mode. 0(object), 1(vertex), 2(edge), 3(border), 4(face), 5(element)
        """
        maxEval("max modify mode")  # set focus: modifier panel.

        selection = rt.selection

        for obj in selection:
            rt.modPanel.setCurrentObject(obj.baseObject)
            rt.subObjectLevel = level

            if level == 0:  # reset the modifier selection to the top of the stack.
                toggle = Slots.cycle([0, 1], "toggle_baseObjectLevel")
                if toggle:
                    rt.modPanel.setCurrentObject(obj.baseObject)
                else:
                    try:
                        rt.modPanel.setCurrentObject(obj.modifiers[0])
                    except:
                        rt.modPanel.setCurrentObject(obj.baseObject)  # if index error

    @staticmethod
    def getModifier(obj, modifier, index=0):
        """Gets (and sets (if needed)) the given modifer for the given object at the given index.

        Parameters:
                obj = <object> - the object to add or retrieve the modifier from.
                modifier (str): modifier name.
                index (int): place modifier before given index. default is at the top of the stack.
                                        Negative indices place the modifier from the bottom of the stack.
        Returns:
                (obj) modifier object.
        """
        m = obj.modifiers[modifier]  # check the stack for the given modifier.

        if not m:
            m = getattr(rt, modifier)()
            if index < 0:
                index = index + len(obj.modifiers) + 1  # place from the bottom index.
            rt.addModifier(obj, m, before=index)

        if not rt.modPanel.getCurrentObject() == m:
            rt.modPanel.setCurrentObject(
                m
            )  # set modifier in stack (if it is not currently active).

        return m

    @staticmethod
    def undo(state=True):
        """ """
        import pymxs

        pymxs.undo(state)
        return state

        # ---------------------------------------------------------------------------------------------
        "UI:"

    # ---------------------------------------------------------------------------------------------

    @classmethod
    def attr(cls, fn):
        """Decorator for objAttrWindow."""

        def wrapper(self, *args, **kwargs):
            self.setAttributeWindow(fn(self, *args, **kwargs))

        return wrapper

    def setAttributeWindow(
        self, obj, inc=[], exc=[], checkableLabel=False, fn=None, *fn_args, **attributes
    ):
        """Launch a popup window containing the given objects attributes.

        Parameters:
                obj (str/obj/list): The object to get the attributes of, or it's name. If given as a list, only the first index will be used.
                inc (list): Attributes to include. All other will be omitted. Exclude takes dominance over include. Meaning, if the same attribute is in both lists, it will be excluded.
                exc (list): Attributes to exclude from the returned dictionay. ie. ['Position','Rotation','Scale','renderable','isHidden','isFrozen','selected']
                checkableLabel (bool): Set the attribute labels as checkable.
                fn (method) = Set an alternative method to call on widget signal. ex. setParameterValuesMEL
                                The first parameter of fn is always the given object. ex. fn(obj, {'attr':<value>})
                fn_args (args) = Any additonal args to pass to fn.
                attributes (kwargs) = Explicitly pass in attribute:values pairs. Else, attributes will be pulled from self.getNodeAttributes for the given obj.

        Example: self.setAttributeWindow(obj, attributes=attrs, checkableLabel=True)
        """
        if not obj:
            return
        elif isinstance(obj, (list, set, tuple)):
            obj = obj[0]

        fn = fn if fn else self.setAttributesMax

        if attributes:
            attributes = {
                k: v
                for k, v in attributes.items()
                if not k in exc and (k in inc if inc else k not in inc)
            }
        else:
            attributes = self.getAttributesMax(obj, inc=inc, exc=exc)

        menu = self.objAttrWindow(
            obj, checkableLabel=checkableLabel, fn=fn, *fn_args, **attributes
        )

        if checkableLabel:
            for c in menu.childWidgets:
                if c.__class__.__name__ == "QCheckBox":
                    attr = getattr(obj, c.objectName())
                    c.stateChanged.connect(
                        lambda state, obj=obj, attr=attr: pm.select(
                            attr, deselect=not state, add=1
                        )
                    )
                    # if attr in list(rt.selection):
                    # c.setChecked(True)

    def maxUiSetChecked(self, id, table, item, state=True, query=False):
        """
        Parameters:
                id (str): The actionMan ID
                table (int): The actionMan table
                item (int): The actionMan item number
                state (bool): Set the check state.
                query (bool): Query the check state.

        Returns:
                (bool) The check state.
        """
        atbl = rt.actionMan.getActionTable(table)
        if atbl:
            aitm = atbl.getActionItem(item)
            if query:
                return aitm.isChecked
            else:
                if state:  # check
                    if not aitm.isChecked:
                        rt.actionMan.executeAction(0, id)
                        return aitm.isChecked
                else:  # uncheck
                    if aitm.isChecked:
                        rt.actionMan.executeAction(0, id)
                        return aitm.isChecked


# module name
# print (__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------


# --------------------------------------------------------------------------------------------
# deprecated:
# --------------------------------------------------------------------------------------------
