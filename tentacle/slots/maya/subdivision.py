# !/usr/bin/python
# coding=utf-8
import maya.cmds as cmds
import maya.mel as mel
import mayatk as mtk
from tentacle import SlotsMaya


class Subdivision(SlotsMaya):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.ui = self.sb.loaded_ui.subdivision
        self.submenu = self.sb.loaded_ui.subdivision_submenu

    # --------------------------------------------------- s000/s001  smooth preview
    # The mesh owns these levels, so the spinboxes mirror the selection rather than
    # persisting their own copy: a restored value re-fires the slot on panel open,
    # which would smooth (and re-tessellate) whatever happened to be selected.
    def _init_smooth_level(self, widget, attr):
        shapes = mtk.NodeUtils.get_shapes(
            cmds.ls(selection=True), descend=True, type="mesh"
        )
        self.mirror_app_state(
            widget,
            (lambda: widget.setValue(cmds.getAttr(f"{shapes[0]}.{attr}")))
            if shapes
            else None,
        )

    def s000_init(self, widget):
        """Division Level — reflect the selection's live preview division level."""
        self._init_smooth_level(widget, "smoothLevel")

    def s001_init(self, widget):
        """Adaptive Level — reflect the selection's live adaptive tessellation level."""
        self._init_smooth_level(widget, "smoothTessLevel")

    def _report_smooth_level(self, label: str, attr: str, value: int, meshes) -> int:
        """Message the count that actually took the value, and return it.

        ``set_smooth_preview`` returns every RESOLVED shape by design (one
        locked mesh must not abort the rest of the selection), so its length
        is not a success count: on a referenced mesh with a locked plug the
        panel would report "on 1 mesh(es)" having changed nothing. Read the
        plugs back instead of trusting the write.
        """
        applied = []
        for mesh in meshes:
            try:
                if cmds.getAttr(f"{mesh}.{attr}") == value:
                    applied.append(mesh)
            except Exception:  # plug gone with the shape mid-drag
                continue
        skipped = len(meshes) - len(applied)
        if not applied:
            self.sb.message_box(
                f"{label} <hl>{value}</hl>: no mesh accepted the change "
                f"(locked or connected)."
            )
        else:
            suffix = f" ({skipped} skipped — locked or connected)" if skipped else ""
            self.sb.message_box(
                f"{label}: <hl>{value}</hl> on <hl>{len(applied)}</hl> mesh(es){suffix}."
            )
        return len(applied)

    def s000(self, value: int, widget: object) -> None:
        """Division Level (smooth mesh preview divisions)."""
        # ``display=2`` because the level is only observable with the smooth
        # preview actually on -- dragging this with it off looked like a no-op.
        meshes = mtk.DisplayUtils.set_smooth_preview(
            cmds.ls(selection=True), display=2, level=value
        )
        if meshes:
            applied = self._report_smooth_level(
                "Division Level", "smoothLevel", value, meshes
            )
            # SubDivision proxy options: 'divisions' -- only once the level
            # is real, so a fully-skipped drag can't shift the global default.
            if applied:
                cmds.optionVar(intValue=("proxyDivisions", value))

    def s001(self, value: int, widget: object) -> None:
        """Adaptive Level (OpenSubdiv adaptive tessellation)."""
        # Setting the adaptive level also switches the meshes to the OpenSubdiv
        # Adaptive draw type -- no other draw type reads ``smoothTessLevel``.
        meshes = mtk.DisplayUtils.set_smooth_preview(
            cmds.ls(selection=True), display=2, adaptive_level=value
        )
        if meshes:
            self._report_smooth_level(
                "Adaptive Level", "smoothTessLevel", value, meshes
            )

    def b000(self):
        """Quadrangulate"""
        mel.eval("performPolyQuadrangulate 0")

    def b001(self):
        """Triangulate: split the selected faces into triangles."""
        mel.eval("polyTriangulate")

    def b005(self):
        """Reduce: halve the polygon count while preserving border, hard, crease, and UV edges.

        The one-click form of tb000's Reduce (same ``polyReduce`` flags via
        ``mtk.EditUtils.decimate``, history kept so the node stays tweakable);
        acts on whole meshes or, given a component selection, only that region.
        """
        selection = cmds.ls(sl=True) or []
        if not selection:
            return
        mtk.EditUtils.decimate(selection, percentage=50.0, delete_history=False)

    def tb000_init(self, widget):
        """Initialize Decimate"""
        menu = widget.option_box.menu
        menu.setTitle("Decimate")

        cmb = menu.add(
            "QComboBox",
            setObjectName="cmb000",
            setToolTip="Decimation algorithm.",
        )
        for text, data in [
            ("Reduce (Quadric Error %)", "qem"),
            ("Planar (Coplanar Dissolve)", "planar"),
        ]:
            cmb.addItem(text, data)

        # Reduce (quadric error metric) options.
        menu.add(
            "QDoubleSpinBox",
            setPrefix="Reduce %: ",
            setObjectName="s010",
            set_limits=[0, 99, 1, 1],
            setValue=50.0,
            set_fixed_height=20,
            setToolTip="Percent of faces to remove (quadric-error polyReduce).",
        )
        menu.add("QCheckBox", setText="Preserve Borders", setObjectName="chk010",
                 setChecked=True, setToolTip="Hold open mesh and face-group borders fixed.")
        menu.add("QCheckBox", setText="Preserve Hard/Crease Edges", setObjectName="chk011",
                 setChecked=True, setToolTip="Hold hard and crease edges.")
        menu.add("QCheckBox", setText="Preserve UV Borders", setObjectName="chk012",
                 setChecked=True, setToolTip="Hold UV (map) and color borders.")
        menu.add("QCheckBox", setText="Preserve Quads", setObjectName="chk013",
                 setChecked=True, setToolTip="Bias the reduction toward keeping quads.")
        menu.add("QCheckBox", setText="Symmetry (X)", setObjectName="chk014",
                 setChecked=False, setToolTip="Reduce symmetrically about X (virtual symmetry).")

        # Planar (coplanar dissolve) options.
        menu.add(
            "QDoubleSpinBox",
            setPrefix="Angle Tolerance: ",
            setObjectName="s011",
            set_limits=[0, 180, 0.5, 1],
            setValue=1.0,
            set_fixed_height=20,
            setToolTip="Max dihedral angle (degrees) treated as coplanar. ~0 is lossless on hard-surface.",
        )

        # Grey out the options that don't apply to the chosen algorithm.
        qem_widgets = [menu.s010, menu.chk010, menu.chk011, menu.chk012, menu.chk013, menu.chk014]

        def _sync(*_):
            planar = menu.cmb000.currentData() == "planar"
            for w in qem_widgets:
                w.setEnabled(not planar)
            menu.s011.setEnabled(planar)

        menu.cmb000.currentIndexChanged.connect(_sync)
        _sync()

    def tb000(self, widget):
        """Decimate: reduce face count by quadric-error percentage or coplanar-face dissolve.

        Acts on the selection as-is — whole meshes, or a COMPONENT selection to
        decimate only that region: faces reduce / dissolve within themselves
        (the region's outline is held), verts and edges resolve to their faces
        (Reduce) or the edges between them (Planar). Mixed selections work.
        """
        selection = cmds.ls(sl=True) or []
        if not selection:
            self.sb.message_box(
                "<strong>Nothing selected</strong>.<br>Select one or more "
                "meshes, or mesh components, to decimate."
            )
            return

        menu = widget.option_box.menu
        if menu.cmb000.currentData() == "planar":
            processed = mtk.EditUtils.dissolve_coplanar(
                selection, angle_tolerance=menu.s011.value()
            )
        else:
            processed = mtk.EditUtils.decimate(
                selection,
                percentage=menu.s010.value(),
                preserve_borders=menu.chk010.isChecked(),
                preserve_hard_edges=menu.chk011.isChecked(),
                preserve_uv_borders=menu.chk012.isChecked(),
                preserve_quads=menu.chk013.isChecked(),
                symmetry=menu.chk014.isChecked(),
            )
        if not processed:
            self.sb.message_box(
                "<strong>No mesh in the selection</strong>.<br>Select polygon "
                "meshes or their components to decimate."
            )

    def b008(self):
        """Add Divisions - Subdivide Mesh"""
        mel.eval("SubdividePolygon")

    def b011(self):
        """Apply Smooth Preview"""
        mel.eval("performSmoothMeshPreviewToPolygon")

    def b028(self):
        """Quad Draw: enter Maya's Quad Draw retopology tool."""
        mel.eval("dR_quadDrawTool")

    @staticmethod
    def smoothProxy():
        """Subdiv Proxy"""
        global polySmoothBaseMesh
        polySmoothBaseMesh = []
        # disable creating seperate layers for subdiv proxy
        cmds.optionVar(intValue=("polySmoothLoInLayer", 0))
        cmds.optionVar(intValue=("polySmoothHiInLayer", 0))
        # query smooth proxy state.
        sel = mel.eval('polyCheckSelection "polySmoothProxy" "o" 0') or []

        if len(sel) == 0 and len(polySmoothBaseMesh) == 0:
            return "Error: Nothing selected."

        if len(sel) != 0:
            del polySmoothBaseMesh[:]
            for object_ in sel:
                polySmoothBaseMesh.append(object_)
        elif len(polySmoothBaseMesh) != 0:
            sel = polySmoothBaseMesh

        transform = cmds.listRelatives(sel[0], fullPath=1, parent=1) or []
        if not transform:
            return
        shape = cmds.listRelatives(transform[0], pa=1, shapes=1) or []
        if not shape:
            return

        # check shape for an existing output to a smoothProxy
        attachedSmoothProxies = cmds.listConnections(
            shape[0], type="polySmoothProxy", s=0, d=1
        ) or []
        if len(attachedSmoothProxies) != 0:  # subdiv off
            mel.eval("smoothingDisplayToggle 0")

        # toggle performSmoothProxy
        mel.eval("performSmoothProxy 0")  # toggle SubDiv Proxy


# --------------------------------------------------------------------------------------------

# module name
# print(__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
