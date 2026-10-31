# !/usr/bin/python
# coding=utf-8
"""Polygons: one Slots class for both hosts.

Every operation is the host toolkit's (``self.tk``): component work on
``Components``, object work on ``EditUtils``, each given ``None`` for the
selection and each one undo step in its host. An operation with nothing to act
on returns ``[]`` and the slot says so; a state the user can fix raises
``ValueError`` and a host refusal ``RuntimeError``, both shown as the host words
them. Maya acts on the component selection (an object stands for all of its
components where Maya's own command allows it); Blender acts on the Edit-Mode
selection. The viewport tools go through :meth:`Slots.activate_tool`.
"""

from tentacle import Slots


class PolygonsSlots(Slots):
    #: The message when a component operation finds nothing to act on.
    NO_COMPONENTS = (
        "<b>Nothing selected.</b><br>"
        "{op} needs a component selection (Blender: in Edit Mode)."
    )

    #: Merge Vertices' default distance (``s002``), restored by Set Distance
    #: when it cannot measure.
    MERGE_DISTANCE = 0.0005

    def __init__(self, switchboard):
        super().__init__(switchboard)
        self.ui = self.sb.loaded_ui.polygons
        self.submenu = self.sb.loaded_ui.polygons_submenu

    def header_init(self, widget):
        """Initialize Header"""
        # Every entry is a one-shot action: dismiss the menu once one is triggered.
        widget.menu.hide_on_trigger = True
        widget.menu.add(
            "QPushButton",
            setText="Bridge Interactive",
            setObjectName="b007",
            setToolTip="Open the bridge window.",
        )
        widget.menu.add(
            "QPushButton",
            setText="Bevel",
            setObjectName="b011",
            setToolTip="Open the bevel window.",
        )

    # ------------------------------------------------------------------ tb000  Merge Vertices
    def tb000_init(self, widget):
        """Initialize Merge Vertices"""
        menu = widget.option_box.menu
        menu.setTitle("Merge Vertices")
        menu.add(
            "QDoubleSpinBox",
            setPrefix="Distance: ",
            setObjectName="s002",
            set_limits=[0, 1000, 0.0001, 5],
            setValue=self.MERGE_DISTANCE,
            set_fixed_height=20,
            setToolTip="Vertices within this distance are merged.",
        )
        menu.add(
            "QPushButton",
            setText="Set Distance",
            setObjectName="b005",
            set_fixed_height=20,
            setToolTip="Set the distance from two selected vertices (their gap, "
            "+0.1% so a merge welds them), then return to object mode so Merge "
            "acts on the whole object.\nWith any other selection, reset it to the "
            "default.",
        )

    def tb000(self, widget):
        """Merge Vertices: the selected components, else every vertex of the
        selected meshes."""
        self.run_operation(
            self.tk.EditUtils.merge_vertices,
            None,
            tolerance=widget.option_box.menu.s002.value(),
            empty="<b>Nothing selected.</b><br>"
            "Merge Vertices needs a mesh or component selection.",
        )

    def b005(self):
        """Merge Vertices: Set Distance"""
        spinbox = self.ui.tb000.option_box.menu.s002
        distance = self.tk.Components.adjusted_distance_between_vertices(
            None, None, adjust=0.1, as_percentage=True
        )
        if distance is None:
            spinbox.setValue(self.MERGE_DISTANCE)
            self.sb.message_box(
                "Select exactly two vertices to set the merge distance.<br>"
                "The distance was reset to its default."
            )
            return
        spinbox.setValue(distance)
        try:  # Merge then acts on the whole object, at the measured distance
            self.tk.CoreUtils.ensure_object_mode()
        except RuntimeError as error:
            self.sb.message_box(str(error))

    # ------------------------------------------------------------------ tb002  Separate
    def tb002_init(self, widget):
        """Initialize Separate"""
        menu = widget.option_box.menu
        menu.setTitle("Separate")
        menu.add(
            "QCheckBox",
            setText="By Material",
            setObjectName="chk021",
            setChecked=False,
            setToolTip=(
                "Split each mesh so every result has exactly one material, then "
                "parent the results under per-material groups (mirror of Combine "
                "> Group by Material). Off: split into the loose parts."
            ),
        )
        menu.add(
            "QCheckBox",
            setText="Rename",
            setObjectName="chk022",
            setChecked=False,
            setToolTip=(
                "Rename the results after the source object. Disabled while "
                "'By Material' is on: the grouped results are named by the groups."
            ),
        )
        menu.add(
            "QCheckBox",
            setText="Uninstance",
            setObjectName="chk024",
            setChecked=True,
            setToolTip=self.sb.tooltip.fmt(
                title="Uninstance",
                body="Break instance links before separating. On by default, "
                "because leaving it off loses data.",
                notes=[
                    "Separating geometry an instance shares edits the shared "
                    "mesh, which silently deletes the separated faces from every "
                    "sibling instance.",
                ],
            ),
        )
        # Rename is redundant whenever By Material drives the grouped naming.
        chk_by_material, chk_rename = menu.chk021, menu.chk022
        chk_rename.setEnabled(not chk_by_material.isChecked())
        chk_by_material.toggled.connect(lambda on: chk_rename.setEnabled(not on))

    def tb002(self, widget):
        """Separate: split each selected mesh into its loose parts (or per material)."""
        menu = widget.option_box.menu
        by_material = menu.chk021.isChecked()
        self.run_operation(
            self.tk.EditUtils.separate_objects,
            None,
            by_material=by_material,
            group_by_material=by_material,
            rename=menu.chk022.isChecked(),
            uninstance=menu.chk024.isChecked(),
            select=True,
            empty="<b>Nothing to separate.</b><br>"
            "Select a mesh made of more than one part.",
        )

    # ------------------------------------------------------------------ tb003  Extrude
    def tb003_init(self, widget):
        """Initialize Extrude"""
        menu = widget.option_box.menu
        menu.setTitle("Extrude")
        menu.add(
            "QCheckBox",
            setText="Keep Faces Together",
            setObjectName="chk002",
            setChecked=True,
            set_fixed_height=20,
            setToolTip=(
                "Extrude connected faces and edges as one region.<br>"
                "Off: each face extrudes on its own, along its own normal."
            ),
        )
        menu.add(
            "QSpinBox",
            setPrefix="Divisions: ",
            setObjectName="s004",
            set_limits=[1],
            setValue=1,
            set_fixed_height=20,
            setToolTip="The number of segments along the extrusion.",
        )
        menu.add(
            "QDoubleSpinBox",
            setPrefix="Thickness: ",
            setObjectName="s011",
            set_limits=[-1000, 1000, 0.01, 3],
            setValue=0.0,
            set_fixed_height=20,
            setToolTip="Push the extrusion along the normals by this distance; 0 "
            "extrudes in place (Maya leaves its extrude manipulator up to drag).",
        )

    def tb003(self, widget):
        """Extrude the selected faces, edges or vertices."""
        menu = widget.option_box.menu
        self.run_operation(
            self.tk.Components.extrude,
            None,
            keep_faces_together=menu.chk002.isChecked(),
            divisions=menu.s004.value(),
            thickness=menu.s011.value(),
            empty=self.NO_COMPONENTS.format(op="Extrude"),
        )

    # ------------------------------------------------------------------ tb004  Combine
    def tb004_init(self, widget):
        """Initialize Combine"""
        menu = widget.option_box.menu
        menu.setTitle("Combine")
        menu.add(
            "QCheckBox",
            setText="Group by Material",
            setObjectName="chk003",
            setChecked=False,
            setToolTip="Combine into one mesh per material assignment instead of "
            "a single mesh.",
        )
        menu.add(
            "QCheckBox",
            setText="Cluster by Distance",
            setObjectName="chk004",
            setChecked=False,
            setToolTip="Further split each material group by spatial proximity: "
            "objects farther apart than the threshold stay in separate meshes.",
        )
        menu.add(
            "QDoubleSpinBox",
            setPrefix="Threshold: ",
            setObjectName="s003",
            set_limits=[0, 100000, 1, 2],
            setValue=10000.0,
            setToolTip="Maximum distance between objects to be considered part of "
            "the same cluster.",
        )
        menu.add(
            "QCheckBox",
            setText="Uninstance",
            setObjectName="chk023",
            setChecked=True,
            setToolTip=self.sb.tooltip.fmt(
                title="Uninstance",
                body="Break instance links before combining. On by default, "
                "because leaving it off loses data.",
                notes=[
                    "Combining geometry an instance shares rebuilds the shared "
                    "mesh, so a sibling instance outside the selection silently "
                    "changes or disappears.",
                ],
            ),
        )
        # Threshold only matters while clustering.
        chk_cluster, spin_threshold = menu.chk004, menu.s003
        spin_threshold.setEnabled(chk_cluster.isChecked())
        chk_cluster.toggled.connect(spin_threshold.setEnabled)

    def tb004(self, widget):
        """Combine the selected meshes (optionally one mesh per material)."""
        if self.require_selection() is None:
            return
        menu = widget.option_box.menu
        combined = self.run_operation(
            self.tk.EditUtils.combine_objects,
            None,
            group_by_material=menu.chk003.isChecked(),
            cluster_by_distance=menu.chk004.isChecked(),
            threshold=menu.s003.value(),
            uninstance=menu.chk023.isChecked(),
        )
        if combined is None or combined == []:
            self.sb.message_box("Combine needs two or more selected meshes.")

    # ------------------------------------------------------------------ tb005  Detach
    def tb005_init(self, widget):
        """Initialize Detach"""
        menu = widget.option_box.menu
        menu.setTitle("Detach")
        menu.add(
            "QCheckBox",
            setText="Duplicate",
            setObjectName="chk014",
            setChecked=True,
            setToolTip="Detach a copy of the faces, leaving the original mesh "
            "unchanged.",
        )
        menu.add(
            "QCheckBox",
            setText="Extract To New Object",
            setObjectName="chk015",
            setChecked=True,
            setToolTip=self.sb.tooltip.fmt(
                title="Extract To New Object",
                body="Move the extracted faces into a <b>new</b> object.",
                notes=[
                    "Off: the faces are split off in place and stay within the "
                    "source mesh.",
                ],
            ),
        )
        menu.add(
            "QCheckBox",
            setText="One Object Per Face",
            setObjectName="chk020",
            setChecked=False,
            setToolTip=self.sb.tooltip.fmt(
                title="One Object Per Face",
                body="Break the extraction apart face by face instead of keeping "
                "it as one connected shell.",
                notes=[
                    "With <b>Extract To New Object</b> off, the faces are still "
                    "split apart individually inside the source mesh.",
                ],
            ),
        )

    def tb005(self, widget):
        """Detach the selected faces (optionally a copy, a new object, per face)."""
        if (
            self.require_selection(self.NO_COMPONENTS.format(op="Detach")) is None
        ):
            return
        menu = widget.option_box.menu
        separate = menu.chk015.isChecked()
        result = self.run_operation(
            self.tk.EditUtils.detach_components,
            None,
            duplicate=menu.chk014.isChecked(),
            separate=separate,
            keep_faces_together=not menu.chk020.isChecked(),
        )
        if not separate:
            return
        if not result:
            self.sb.message_box(self.NO_COMPONENTS.format(op="Detach"))
            return
        try:  # the new object(s) read as objects, selected
            self.tk.CoreUtils.ensure_object_mode()
        except RuntimeError as error:
            self.sb.message_box(str(error))

    # ------------------------------------------------------------------ tb006  Inset
    def tb006_init(self, widget):
        """Initialize Inset Face Region"""
        menu = widget.option_box.menu
        menu.setTitle("Inset Face Region")
        menu.add(
            "QDoubleSpinBox",
            setPrefix="Offset: ",
            setObjectName="s001",
            set_limits=[0, 100, 0.01, 3],
            setValue=self.tk.Units.convert(2.0, "cm", "working"),
            set_fixed_height=20,
            setToolTip="How far the inset border sits inside the region's edge.",
        )
        menu.add(
            "QDoubleSpinBox",
            setPrefix="Depth: ",
            setObjectName="s010",
            set_limits=[-100, 100, 0.01, 3],
            setValue=0.0,
            setToolTip="Raise or lower the inset region along its normal.",
        )
        menu.add(
            "QCheckBox",
            setText="Individual Faces",
            setObjectName="chk018",
            setToolTip="Inset each selected face on its own instead of the region "
            "as one.",
        )

    def tb006(self, widget):
        """Inset Face Region"""
        menu = widget.option_box.menu
        self.run_operation(
            self.tk.Components.inset_faces,
            None,
            offset=menu.s001.value(),
            depth=menu.s010.value(),
            individual=menu.chk018.isChecked(),
            empty=self.NO_COMPONENTS.format(op="Inset"),
        )

    # ------------------------------------------------------------------ tb007  Divide Facet
    def chk008(self, state, widget):
        """Divide Facet: Split U"""
        self.sb.toggle_multi(widget.ui, setUnChecked="chk010")

    def chk009(self, state, widget):
        """Divide Facet: Split V"""
        self.sb.toggle_multi(widget.ui, setUnChecked="chk010")

    def chk010(self, state, widget):
        """Divide Facet: Tris"""
        self.sb.toggle_multi(widget.ui, setUnChecked="chk008,chk009")

    def tb007_init(self, widget):
        """Initialize Divide Facet"""
        menu = widget.option_box.menu
        menu.setTitle("Divide Facet")
        split_u = menu.add(
            "QCheckBox",
            setText="U",
            setObjectName="chk008",
            setChecked=True,
            set_fixed_height=20,
            setToolTip="Split the faces along U (their first edge's direction).",
        )
        split_v = menu.add(
            "QCheckBox",
            setText="V",
            setObjectName="chk009",
            setChecked=True,
            set_fixed_height=20,
            setToolTip="Split the faces along V. With U too: both ways.",
        )
        # Maya's: Blender's subdivide has no one-direction face split, so a
        # face always divides both ways there.
        for one_way in (split_u, split_v):
            self.requires(one_way, "maya")
        menu.add(
            "QCheckBox",
            setText="Tris",
            setObjectName="chk010",
            set_fixed_height=20,
            setToolTip="Divide into triangles.",
        )
        menu.add(
            "QSpinBox",
            setPrefix="Cuts: ",
            setObjectName="s009",
            set_limits=[1, 10],
            setValue=1,
            set_fixed_height=20,
            setToolTip="The number of cuts in each split direction (Blender: "
            "both ways).",
        )

    def tb007(self, widget):
        """Divide Facet"""
        menu = widget.option_box.menu
        self.run_operation(
            self.tk.Components.divide_faces,
            None,
            u=menu.chk008.isChecked(),
            v=menu.chk009.isChecked(),
            cuts=menu.s009.value(),
            tris=menu.chk010.isChecked(),
            empty=self.NO_COMPONENTS.format(op="Divide"),
        )

    # ------------------------------------------------------------------ tb008  Boolean
    def tb008_init(self, widget):
        """Initialize Boolean Operation"""
        menu = widget.option_box.menu
        menu.setTitle("Boolean Operation")
        menu.add(
            "QComboBox",
            addItems=["Union", "Difference", "Intersection"],
            setObjectName="cmb011",
            setCurrentText="Difference",
            set_fixed_height=20,
            setToolTip="The boolean operation. The first selected object (Blender: "
            "the active one) is the base.",
        )
        menu.add(
            "QCheckBox",
            setText="Interactive",
            setObjectName="chk017",
            set_fixed_height=20,
            setToolTip="Keep the boolean live and editable (Maya: its interactive "
            "boolean tool; Blender: the Boolean modifier, unapplied).",
        )

    def tb008(self, widget):
        """Boolean Operation"""
        menu = widget.option_box.menu
        self.run_operation(
            self.tk.EditUtils.boolean_objects,
            None,
            operation=menu.cmb011.currentText().lower(),
            interactive=menu.chk017.isChecked(),
            empty="<b>Nothing selected.</b><br>"
            "Boolean needs two or more selected meshes.",
        )

    # ------------------------------------------------------------------ tb009  Snap Closest Verts
    def tb009_init(self, widget):
        """Initialize Snap Closest Verts"""
        menu = widget.option_box.menu
        menu.setTitle("Snap Closest Verts")
        menu.add(
            "QDoubleSpinBox",
            setPrefix="Tolerance: ",
            setObjectName="s005",
            set_limits=[0, 100, 0.05, 3],
            setValue=10,
            setToolTip="The maximum snap distance: vertices farther than this are "
            "left where they are.",
        )
        chk_freeze = menu.add(
            "QCheckBox",
            setText="Freeze Transforms",
            setObjectName="chk016",
            setChecked=True,
            setToolTip="Freeze the transformations of the object snapped to.",
        )
        # Maya's: it works around a world-space query cmds needs. Blender's
        # world math is exact under any transform, so freezing there would only
        # zero the channels.
        self.requires(chk_freeze, "maya")

    def tb009(self, widget):
        """Snap Closest Verts: the first selected mesh's vertices onto the last
        selected (Blender: the active) mesh's closest ones."""
        sources, target = self.tk.Snap.source_and_target()
        if target is None or len(sources) != 1:
            self.sb.message_box(
                "<b>Select two meshes</b>: the one to snap, then the target "
                "(Blender: the target active)."
            )
            return
        menu = widget.option_box.menu
        moved = self.tk.Snap.snap_to_closest_vertex(
            sources[0],
            target,
            tolerance=menu.s005.value(),
            freeze_transforms=menu.chk016.isChecked(),
        )
        if not moved:
            self.sb.message_box("No vertices within the snap tolerance.")

    # ------------------------------------------------------------------ component buttons
    def b000(self):
        """Circularize: reshape the selected vertices, edges or faces into an even circle."""
        return self.run_operation(
            self.tk.Components.circularize,
            None,
            empty=self.NO_COMPONENTS.format(op="Circularize"),
        )

    def b001(self):
        """Fill Hole: cap the open holes bounded by the selection's border edges."""
        self.run_operation(
            self.tk.Components.fill_holes,
            None,
            empty=self.NO_COMPONENTS.format(op="Fill Hole"),
        )

    def b003(self):
        """Symmetrize: mirror the selected components across the symmetry axis."""
        self.run_operation(
            self.tk.Components.symmetrize,
            None,
            empty=self.NO_COMPONENTS.format(op="Symmetrize"),
        )

    def b006(self):
        """Bridge: span two edge selections with new faces."""
        self.run_operation(
            self.tk.Components.bridge_edges,
            None,
            empty="<b>Nothing selected.</b><br>"
            "Bridge needs an edge selection (Blender: in Edit Mode).",
        )

    def b007(self):
        """Bridge Interactive: open the Bridge tool window."""
        self.sb.handlers.marking_menu.show("bridge")

    def b008(self):
        """Target Weld Center: drag a vertex onto another; they weld at their midpoint."""
        self._target_weld(merge_to_center=True)

    def b009(self):
        """Collapse: each selected face to its own point; edges and vertices to one center."""
        try:
            collapsed, skipped = self.tk.Components.collapse_components(None)
        except (ValueError, RuntimeError) as error:
            self.sb.message_box(str(error))
            return
        if not collapsed:
            self.sb.message_box(
                "<b>Nothing to collapse.</b><br>Select faces, edges or vertices."
            )
        elif skipped:
            self.sb.message_box(
                "Collapsed the selected faces; the edges and vertices picked with "
                "them were left as they are."
            )

    def b011(self):
        """Bevel: open the Bevel tool window."""
        self.sb.handlers.marking_menu.show("bevel")

    def b012(self):
        """Multi-Cut Tool"""
        self.activate_tool("Multi-Cut")

    def b022(self):
        """Attach: connect the selected vertices and edges with new edges."""
        self.run_operation(
            self.tk.Components.connect_components,
            None,
            empty="<b>Nothing connected.</b><br>Select two or more vertices or "
            "edges across a face.",
        )

    def b032(self):
        """Poke: add a center vertex to each selected face, fanning it into triangles."""
        self.run_operation(
            self.tk.Components.poke_faces,
            None,
            empty=self.NO_COMPONENTS.format(op="Poke"),
        )

    def b034(self):
        """Wedge: sweep the selected faces around a selected edge into an arc."""
        wedged = self.run_operation(self.tk.EditUtils.wedge, None)
        if wedged is not None and not wedged:
            self.sb.message_box(
                "<b>Nothing to wedge.</b><br>Select faces and one of their edges "
                "as the hinge (Blender: in Edit Mode)."
            )

    def b038(self):
        """Assign Hole: toggle the selected faces' hole (invisible) state."""
        result = self.run_operation(
            self.tk.Components.toggle_face_holes,
            None,
            empty="<b>Nothing selected.</b><br>Assign Hole needs a face selection.",
        )
        if result:
            state, faces = result
            self.sb.message_box(
                f"<hl>{len(faces)}</hl> face(s) "
                f"{'assigned as holes' if state else 'restored'}."
            )

    def b043(self):
        """Target Weld: drag a vertex onto another to weld it there."""
        self._target_weld(merge_to_center=False)

    def _target_weld(self, merge_to_center):
        """Start the host's interactive Target Weld (Maya's Merge Vertex Tool)."""
        try:
            self.tk.TargetWeld.activate(merge_to_center=merge_to_center)
        except (ValueError, RuntimeError) as error:
            self.sb.message_box(str(error))

    def b047(self):
        """Insert Edgeloop"""
        self.activate_tool("Insert Edgeloop")

    def b049(self):
        """Slide: slide the selected edge loops along their neighboring edges."""
        self.run_operation(self.tk.Components.slide_edges, None)

    def b051(self):
        """Offset Edgeloop: add a loop on each side of the selected edges."""
        self.run_operation(
            self.tk.Components.offset_edge_loops,
            None,
            empty="<b>Nothing selected.</b><br>"
            "Offset Edgeloop needs an edge selection (Blender: in Edit Mode).",
        )

    def b053(self):
        """Edit Edge Flow: adjust the selected edges to follow the surface curvature."""
        self.run_operation(
            self.tk.Components.edit_edge_flow,
            None,
            empty="<b>Nothing selected.</b><br>"
            "Edit Edge Flow needs an edge selection (Blender: in Edit Mode).",
        )


# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
