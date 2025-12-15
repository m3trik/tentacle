# !/usr/bin/python
# coding=utf-8
try:
    import pymel.core as pm
except ImportError as error:
    print(__file__, error)
from qtpy import QtWidgets
from uitk import WidgetComboBox, ToolBox
import mayatk as mtk
from tentacle.slots.maya import SlotsMaya


class Selection(SlotsMaya):
    def __init__(self, switchboard):
        super().__init__(switchboard)

        self.ui = self.sb.loaded_ui.selection
        self.submenu = self.sb.loaded_ui.selection_submenu

    def cmb001_init(self, widget):
        """Reorder Selection Init"""
        widget.option_box.menu.setTitle("Reorder Selection")
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Reverse Order",
            setObjectName="chk009",
            setChecked=False,
            setToolTip="Reverse the reordered selection.",
        )
        # Get available reorder methods
        items = [
            "Name",
            "Hierarchy",
            "X Position",
            "Y Position",
            "Z Position",
            "Distance from Origin",
            "Volume",
            "Vertex Count",
            "Random",
            "Creation Time",
        ]
        widget.add(items, header="Reorder By:")

    def cmb001(self, index, widget):
        """Reorder Selection"""
        reverse = widget.option_box.menu.chk009.isChecked()

        # Map display names to method names
        method_map = {
            "Name": "name",
            "Hierarchy": "hierarchy",
            "X Position": "x",
            "Y Position": "y",
            "Z Position": "z",
            "Distance from Origin": "distance",
            "Volume": "volume",
            "Vertex Count": "vertex_count",
            "Random": "random",
            "Creation Time": "creation_time",
        }

        selected_option = widget.items[index]
        method = method_map.get(selected_option, "name")

        # Get current selection
        objects = pm.selected()
        if not objects:
            self.sb.message_box("No objects selected to reorder.")
            return

        # Reorder the objects
        reordered = mtk.reorder_objects(objects, method=method, reverse=reverse)

        # Reselect in new order
        if reordered:
            pm.select(reordered)
            print(
                f"Reordered {len(reordered)} objects by {selected_option}{' (reversed)' if reverse else ''}"
            )

    def cmb002_init(self, widget):
        """Select By Type Init"""
        widget.option_box.menu.setTitle("Select By Type")
        widget.option_box.menu.add(
            "QComboBox",
            setObjectName="cmb000",
            addItems=["Mode: Replace", "Mode: Add", "Mode: Remove"],
            setToolTip="Selection Mode.",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Search Current Selection Only",
            setObjectName="chk013",
            setChecked=False,
            setToolTip=(
                "Search within the current selection instead of all scene objects."
            ),
        )

        # Get categories and types
        categories = mtk.Selection.get_selection_categories()
        # Flatten into a single list including category names
        items = sorted(
            list(categories.keys())
            + [t for types in categories.values() for t in types]
        )
        widget.add(items, header="By Type:")

    def cmb002(self, index, widget):
        """Select by Type"""
        mode_text = widget.option_box.menu.cmb000.currentText()
        search_selection = widget.option_box.menu.chk013.isChecked()

        # Determine selection mode
        if "Add" in mode_text:
            mode = "add"
        elif "Remove" in mode_text:
            mode = "remove"
        else:
            mode = "replace"

        # Get the selection type
        selection_type = widget.items[index]

        # Get objects to work with
        if search_selection:
            # Search within current selection only
            objects = pm.selected()
            if not objects:
                self.sb.message_box("No objects selected to search within.")
                return
        else:
            # Search all scene objects
            objects = pm.ls()

        try:
            result = mtk.Selection.select_by_type(selection_type, objects, mode)
            print(f"Selected {len(result)} objects of type: {selection_type}")
        except ValueError:
            pass
        except Exception as e:
            pm.warning(f"Error selecting by type '{selection_type}': {str(e)}")

    def cmb003_init(self, widget):
        """ """
        items = [
            "Verts",
            "Vertex Faces",
            "Vertex Perimeter",
            "Edges",
            "Edge Loop",
            "Edge Ring",
            "Contained Edges",
            "Edge Perimeter",
            "Border Edges",
            "Faces",
            "Face Path",
            "Contained Faces",
            "Face Perimeter",
            "UV's",
            "UV Shell",
            "UV Shell Border",
            "UV Perimeter",
            "UV Edge Loop",
            "Shell",
            "Shell Border",
        ]
        widget.add(items, header="Convert To:")

    def cmb003(self, index, widget):
        """Convert To"""
        text = widget.items[index]
        if text == "Verts":  # Convert Selection To Vertices
            pm.mel.PolySelectConvert(3)
        elif text == "Vertex Faces":  #
            pm.mel.PolySelectConvert(5)
        elif text == "Vertex Perimeter":  #
            pm.mel.ConvertSelectionToVertexPerimeter()
        elif text == "Edges":  # Convert Selection To Edges
            pm.mel.PolySelectConvert(2)
        elif text == "Edge Loop":  #
            pm.mel.polySelectSp(loop=1)
        elif text == "Edge Ring":  # Convert Selection To Edge Ring
            pm.mel.SelectEdgeRingSp()
        elif text == "Contained Edges":  #
            pm.mel.PolySelectConvert(20)
        elif text == "Edge Perimeter":  #
            pm.mel.ConvertSelectionToEdgePerimeter()
        elif text == "Border Edges":  #
            pm.select(self.getBorderEdgeFromFace())
        elif text == "Faces":  # Convert Selection To Faces
            pm.mel.PolySelectConvert(1)
        elif text == "Face Path":  #
            pm.mel.polySelectEdges("edgeRing")
        elif text == "Contained Faces":  #
            pm.mel.PolySelectConvert(10)
        elif text == "Face Perimeter":  #
            pm.mel.polySelectFacePerimeter()
        elif text == "UV's":  #
            pm.mel.PolySelectConvert(4)
        elif text == "UV Shell":  #
            pm.mel.polySelectBorderShell(0)
        elif text == "UV Shell Border":  #
            pm.mel.polySelectBorderShell(1)
        elif text == "UV Perimeter":  #
            pm.mel.ConvertSelectionToUVPerimeter()
        elif text == "UV Edge Loop":  #
            pm.mel.polySelectEdges("edgeUVLoopOrBorder")
        elif text == "Shell":  #
            pm.mel.polyConvertToShell()
        elif text == "Shell Border":  #
            pm.mel.polyConvertToShellBorder()

    def cmb005_init(self, widget):
        """ """
        items = [
            "OFF",
            "Angle",
            "Border",
            "Edge Loop",
            "Edge Ring",
            "Shell",
            "UV Edge Loop",
        ]
        widget.add(items)

    def cmb005(self, index, widget):
        """Selection Contraints"""
        text = widget.items[index]
        if text == "Angle":
            pm.mel.dR_selConstraintAngle()
        elif text == "Border":
            pm.mel.dR_selConstraintBorder()
        elif text == "Edge Loop":
            pm.mel.dR_selConstraintEdgeLoop()
        elif text == "Edge Ring":
            pm.mel.dR_selConstraintEdgeRing()
        elif text == "Shell":
            pm.mel.dR_selConstraintElement()
        elif text == "UV Edge Loop":
            pm.mel.dR_selConstraintUVEdgeLoop()
        elif text == "OFF":
            pm.mel.dR_selConstraintOff()
        self.sb.message_box(f"Select Constaints: <hl>{text}</hl>")

    def chk000(self, state, widget):
        """Select Nth: uncheck other checkboxes"""
        self.sb.toggle_multi(widget.ui, setUnChecked="chk001-2")

    def chk001(self, state, widget):
        """Select Nth: uncheck other checkboxes"""
        self.sb.toggle_multi(widget.ui, setUnChecked="chk000,chk002")

    def chk002(self, state, widget):
        """Select Nth: uncheck other checkboxes"""
        self.sb.toggle_multi(widget.ui, setUnChecked="chk000-1")

    def chk005_init(self, widget):
        """Create button group for radioboxes chk005, chk006, chk007"""
        self.sb.create_button_groups(widget.ui, "chk005-7")

        ctx = self.get_selection_tool()
        if ctx == "selectSuperContext":
            widget.ui.chk005.setChecked(True)
        elif ctx == "lassoSelectContext":
            widget.ui.chk006.setChecked(True)
        elif ctx == "artSelectContext":
            widget.ui.chk007.setChecked(True)

    def chk005(self, state, widget):
        """Select Style: Marquee"""
        if state:
            self.set_selection_tool("selectSuperContext")

    def chk006(self, state, widget):
        """Select Style: Lasso"""
        if state:
            self.set_selection_tool("lassoSelectContext")

    def chk007(self, state, widget):
        """Select Style: Paint"""
        if state:
            self.set_selection_tool("artSelectContext")

    def lbl003(self, *args):
        """Grow Selection"""
        pm.mel.GrowPolygonSelectionRegion()

    def lbl004(self, *args):
        """Shrink Selection"""
        pm.mel.ShrinkPolygonSelectionRegion()

    def chk004(self, state, widget):
        """Ignore Backfacing (Camera Based Selection)"""
        if state:
            pm.selectPref(useDepth=True)
            self.sb.message_box("Camera-based selection <hl>ON</hl>.")
        else:
            pm.selectPref(useDepth=False)
            self.sb.message_box("Camera-based selection <hl>OFF</hl>.")

    def chk008(self, state, widget):
        """Toggle Soft Selection"""
        if state:
            pm.softSelect(edit=1, softSelectEnabled=True)
            self.sb.message_box("Soft Select <hl>ON</hl>.")
        else:
            pm.softSelect(edit=1, softSelectEnabled=False)
            self.sb.message_box("Soft Select <hl>OFF</hl>.")

    def chkxxx(self, **kwargs):
        """Transform Constraints: Constraint CheckBoxes"""
        widget = kwargs.get("widget")
        state = kwargs.get("state")
        try:
            pm.select(widget.text(), deselect=(not state))
        except KeyError:
            pass

    def tb000_init(self, widget):
        """ """
        widget.option_box.menu.add(
            "QRadioButton",
            setText="Edge Ring",
            setObjectName="chk000",
            setToolTip="Select component ring.",
        )
        widget.option_box.menu.add(
            "QRadioButton",
            setText="Edge Loop",
            setObjectName="chk001",
            setChecked=True,
            setToolTip="Select all contiguous components that form a loop with the current selection.",
        )
        widget.option_box.menu.add(
            "QRadioButton",
            setText="Edge Loop Path",
            setObjectName="chk009",
            setToolTip="The path along loop between two selected edges, vertices or UV's.",
        )
        widget.option_box.menu.add(
            "QRadioButton",
            setText="Shortest Edge Path",
            setObjectName="chk002",
            setToolTip="The shortest component path between two selected edges, vertices or UV's.",
        )
        widget.option_box.menu.add(
            "QRadioButton",
            setText="Border Edges",
            setObjectName="chk010",
            setToolTip="Select the object(s) border edges.",
        )
        widget.option_box.menu.add(
            "QSpinBox",
            setPrefix="Step: ",
            setObjectName="s003",
            set_limits=[1, 100],
            setValue=1,
            setToolTip="Step Amount.",
        )

    def tb000(self, widget):
        """Select Nth"""
        edgeRing = widget.option_box.menu.chk000.isChecked()
        edgeLoop = widget.option_box.menu.chk001.isChecked()
        pathAlongLoop = widget.option_box.menu.chk009.isChecked()
        shortestPath = widget.option_box.menu.chk002.isChecked()
        borderEdges = widget.option_box.menu.chk010.isChecked()
        step = widget.option_box.menu.s003.value()

        selection = pm.ls(orderedSelection=True)
        if not selection:
            self.sb.message_box("Operation requires a valid selection.")
            return

        result = []
        if edgeRing:
            result = mtk.Components.get_edge_path(selection, "edgeRing")

        elif edgeLoop:
            result = mtk.Components.get_edge_path(selection, "edgeLoop")

        elif pathAlongLoop:
            result = mtk.Components.get_edge_path(selection, "edgeLoopPath")

        elif shortestPath:
            result = mtk.Components.get_shortest_path(selection)

        elif borderEdges:
            all_edges = mtk.Components.get_components(selection, "edges")
            result = mtk.Components.get_border_components(all_edges)

        pm.select(result[::step])

    def tb001_init(self, widget):
        """ """
        widget.option_box.menu.add(
            "QDoubleSpinBox",
            setPrefix="Tolerance: ",
            setObjectName="s000",
            set_limits=[0, 9999, 0.0, 3],
            setValue=0.0,
            setToolTip="The allowed difference in any of the compared results.\nie. A tolerance of 4 allows for a difference of 4 components.\nie. A tolerance of 0.05 allows for that amount of variance between any of the bounding box values.",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Vertex",
            setObjectName="chk011",
            setChecked=True,
            setToolTip="The number of vertices.",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Edge",
            setObjectName="chk012",
            setChecked=True,
            setToolTip="The number of edges.",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Face",
            setObjectName="chk013",
            setChecked=True,
            setToolTip="The number of faces.",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Triangle",
            setObjectName="chk014",
            setToolTip="The number of triangles.",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Shell",
            setObjectName="chk015",
            setToolTip="The number of shells shells (disconnected pieces).",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Uv Coord",
            setObjectName="chk016",
            setToolTip="The number of uv coordinates (for the current map).",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Area",
            setObjectName="chk017",
            setToolTip="The surface area of the object's faces in local space.",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="World Area",
            setObjectName="chk018",
            setChecked=True,
            setToolTip="The surface area of the object's faces in world space.",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Bounding Box",
            setObjectName="chk019",
            setToolTip="The object's bounding box in 3d space.\nCannot be used with the topological flags.",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Include Original",
            setObjectName="chk020",
            setToolTip="Include the original selected object(s) in the final selection.",
        )
        widget.option_box.menu.chk018.stateChanged.connect(
            lambda state: (
                self.sb.toggle_multi(widget.menu, setDisabled="chk011-18")
                if state
                else self.sb.toggle_multi(widget.menu, setEnabled="chk011-18")
            )
        )

    def tb001(self, widget):
        """Select Similar"""
        tolerance = widget.option_box.menu.s000.value()  # tolerance
        v = widget.option_box.menu.chk011.isChecked()  # vertex
        e = widget.option_box.menu.chk012.isChecked()  # edge
        f = widget.option_box.menu.chk013.isChecked()  # face
        t = widget.option_box.menu.chk014.isChecked()  # triangle
        s = widget.option_box.menu.chk015.isChecked()  # shell
        uv = widget.option_box.menu.chk016.isChecked()  # uvcoord
        a = widget.option_box.menu.chk017.isChecked()  # area
        wa = widget.option_box.menu.chk018.isChecked()  # world area
        b = widget.option_box.menu.chk019.isChecked()  # bounding box
        inc = widget.option_box.menu.chk020.isChecked()  # select the original objects

        objMode = pm.selectMode(q=True, object=1)
        if objMode:
            selection = pm.ls(sl=1, objectsOnly=1, type="transform")
            pm.select(clear=1)
            for obj in selection:
                similar = mtk.get_similar_mesh(
                    obj,
                    tolerance=tolerance,
                    inc_orig=inc,
                    vertex=v,
                    edge=e,
                    face=f,
                    uvcoord=uv,
                    triangle=t,
                    shell=s,
                    boundingBox=b,
                    area=a,
                    worldArea=wa,
                )
                pm.select(similar, add=True)
        else:
            pm.mel.doSelectSimilar(1, {tolerance})

    def tb002_init(self, widget):
        """ """
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Lock Values",
            setObjectName="chk003",
            setChecked=True,
            setToolTip="Keep values in sync.",
        )
        widget.option_box.menu.add(
            "QDoubleSpinBox",
            setPrefix="x: ",
            setObjectName="s002",
            set_limits=[0, 1, 0.01, 2],
            setValue=0.05,
            setToolTip="Normal X range.",
        )
        widget.option_box.menu.add(
            "QDoubleSpinBox",
            setPrefix="y: ",
            setObjectName="s004",
            set_limits=[0, 1, 0.01, 2],
            setValue=0.05,
            setToolTip="Normal Y range.",
        )
        widget.option_box.menu.add(
            "QDoubleSpinBox",
            setPrefix="z: ",
            setObjectName="s005",
            set_limits=[0, 1, 0.01, 2],
            setValue=0.05,
            setToolTip="Normal Z range.",
        )

        def update_normal_ranges(value, widget):
            """Update all spin boxes if checkbox is checked."""
            if widget.option_box.menu.chk003.isChecked():
                # Update all spin boxes
                widget.option_box.menu.s002.setValue(value)
                widget.option_box.menu.s004.setValue(value)
                widget.option_box.menu.s005.setValue(value)

        # Connect signals
        widget.option_box.menu.s002.valueChanged.connect(
            lambda v: update_normal_ranges(v, widget)
        )
        widget.option_box.menu.s004.valueChanged.connect(
            lambda v: update_normal_ranges(v, widget)
        )
        widget.option_box.menu.s005.valueChanged.connect(
            lambda v: update_normal_ranges(v, widget)
        )

    def tb002(self, widget):
        """Select Island: Select Polygon Face Island"""
        range_x = float(widget.option_box.menu.s002.value())
        range_y = float(widget.option_box.menu.s004.value())
        range_z = float(widget.option_box.menu.s005.value())

        sel = pm.ls(sl=1)
        selected_faces = mtk.Components.get_components(sel, component_type="faces")
        if not selected_faces:
            self.sb.message_box("The operation requires a face selection.")
            return

        similar_faces = mtk.Components.get_faces_with_similar_normals(
            selected_faces, range_x=range_x, range_y=range_y, range_z=range_z
        )
        islands = mtk.Components.get_contigious_islands(similar_faces)
        island = [i for i in islands if bool(set(i) & set(selected_faces))]
        pm.select(island)

    def tb003_init(self, widget):
        """ """
        widget.option_box.menu.add(
            "QDoubleSpinBox",
            setPrefix="Angle Low:  ",
            setObjectName="s006",
            set_limits=[0, 180],
            setValue=70,
            setToolTip="Normal angle low range.",
        )
        widget.option_box.menu.add(
            "QDoubleSpinBox",
            setPrefix="Angle High: ",
            setObjectName="s007",
            set_limits=[0, 180],
            setValue=160,
            setToolTip="Normal angle high range.",
        )

    def tb003(self, widget):
        """Select Edges By Angle"""
        angleLow = widget.option_box.menu.s006.value()
        angleHigh = widget.option_box.menu.s007.value()

        objects = pm.ls(sl=1, objectsOnly=1)
        edges = mtk.Components.get_edges_by_normal_angle(
            objects, low_angle=angleLow, high_angle=angleHigh
        )
        pm.select(edges)

        pm.selectMode(component=1)
        pm.selectType(edge=1)

    def b001(self):
        """Toggle Selectability"""
        mtk.Macros.m_toggle_selectability()

    def b016(self):
        """Convert Selection To Vertices"""
        pm.mel.PolySelectConvert(3)

    def b017(self):
        """Convert Selection To Edges"""
        pm.mel.PolySelectConvert(2)

    def b018(self):
        """Convert Selection To Faces"""
        pm.mel.PolySelectConvert(1)

    def b019(self):
        """Convert Selection To Edge Ring"""
        pm.mel.SelectEdgeRingSp()

    @staticmethod
    def get_selection_tool():
        """Queries the current selection tool in Maya.

        Returns:
            str: The current selection tool.
        """
        try:
            return pm.currentCtx()
        except Exception as e:
            print(f"# Error: {e}")
            return None

    @staticmethod
    def set_selection_tool(tool):
        """Sets the selection tool in Maya.

        Parameters:
            tool (str): The tool to set. Should be one of 'selectSuperContext', 'artSelectContext', 'lassoToolContext'.
        """
        valid_tools = ["selectSuperContext", "lassoSelectContext", "artSelectContext"]
        if tool not in valid_tools:
            print(f"Invalid tool. Tool should be one of {','.join(valid_tools)}.")
            return

        try:
            pm.setToolTo(tool)
        except Exception as e:
            print(f"# Error: {e}")


# --------------------------------------------------------------------------------------------

# module name
# print(__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
