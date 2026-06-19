# !/usr/bin/python
# coding=utf-8
import bpy
import blendertk as btk
from tentacle.slots.blender._slots_blender import SlotsBlender


class Subdivision(SlotsBlender):
    """Blender port of the shared ``subdivision`` menu.

    Backed by ``blendertk.edit_utils``: reduce/decimate + coplanar-dissolve (Decimate modifier),
    triangulate / tris-to-quads / subdivide (bmesh), and a live Subsurf modifier for smooth
    preview + division levels; Quad Draw maps to the Poly Build tool. The Maya smooth-proxy
    workflow and the option-dialog combos are deferred (no clean Blender analogue).
    """

    def __init__(self, switchboard):
        super().__init__(switchboard)
        self.ui = self.sb.loaded_ui.subdivision
        self.submenu = self.sb.loaded_ui.subdivision_submenu

    # ------------------------------------------------------------------ tb000  Decimate
    def tb000_init(self, widget):
        menu = widget.option_box.menu
        menu.setTitle("Decimate")
        cmb = menu.add("QComboBox", setObjectName="cmb000", setToolTip="Decimation algorithm.")
        for text, data in [
            ("Reduce (Collapse %)", "collapse"),
            ("Planar (Coplanar Dissolve)", "planar"),
        ]:
            cmb.addItem(text, data)
        menu.add(
            "QDoubleSpinBox", setPrefix="Reduce %: ", setObjectName="s010",
            set_limits=[0, 99, 1, 1], setValue=50.0, set_fixed_height=20,
            setToolTip="Percent of faces to remove (Decimate collapse).",
        )
        menu.add("QCheckBox", setText="Preserve Quads", setObjectName="chk013", setChecked=True,
                 setToolTip="Keep quads (skip collapse-triangulate).")
        menu.add("QCheckBox", setText="Symmetry (X)", setObjectName="chk014",
                 setToolTip="Reduce symmetrically about X.")
        menu.add(
            "QDoubleSpinBox", setPrefix="Angle Tolerance: ", setObjectName="s011",
            set_limits=[0, 180, 0.5, 1], setValue=1.0, set_fixed_height=20,
            setToolTip="Max dihedral angle (degrees) treated as coplanar (~0 is lossless).",
        )
        # chk010/chk011/chk012 reuse the Maya names for the SAME options. They map onto the PLANAR
        # decimate's boundary/delimit flags (collapse can't preserve features), so pair with s011.
        menu.add("QCheckBox", setText="Preserve Borders", setObjectName="chk010", setChecked=True,
                 setToolTip="Hold open mesh boundaries fixed (planar dissolve keeps border verts).")
        menu.add("QCheckBox", setText="Preserve Hard/Crease Edges", setObjectName="chk011",
                 setChecked=True, setToolTip="Planar dissolve won't cross sharp edges.")
        menu.add("QCheckBox", setText="Preserve UV Borders", setObjectName="chk012",
                 setToolTip="Planar dissolve won't cross UV island borders.")

        collapse_widgets = [menu.s010, menu.chk013, menu.chk014]
        planar_widgets = [menu.s011, menu.chk010, menu.chk011, menu.chk012]

        def _sync(*_):
            planar = menu.cmb000.currentData() == "planar"
            for w in collapse_widgets:
                w.setEnabled(not planar)
            for w in planar_widgets:
                w.setEnabled(planar)

        menu.cmb000.currentIndexChanged.connect(_sync)
        _sync()

    @btk.undoable
    def tb000(self, widget):
        """Decimate"""
        objects = self.selected_objects()
        if not objects:
            self.sb.message_box("<strong>Nothing selected</strong>.<br>Select mesh(es) to decimate.")
            return
        menu = widget.option_box.menu
        if menu.cmb000.currentData() == "planar":
            delimit = set()
            if menu.chk011.isChecked():
                delimit.add("SHARP")
            if menu.chk012.isChecked():
                delimit.add("UV")
            btk.dissolve_coplanar(
                objects, angle_tolerance=menu.s011.value(), delimit=delimit,
                preserve_borders=menu.chk010.isChecked(),
            )
        else:
            btk.decimate(
                objects, percentage=menu.s010.value(),
                preserve_quads=menu.chk013.isChecked(), symmetry=menu.chk014.isChecked(),
            )

    # ------------------------------------------------------------------ s000/s001  subsurf levels
    @btk.undoable
    def s000(self, value, widget):
        """Division Level (live Subdivision-Surface viewport level)."""
        btk.set_subdivision(self.selected_objects(), viewport_levels=value)

    @btk.undoable
    def s001(self, value, widget):
        """Tesselation Level (Subdivision-Surface render level)."""
        btk.set_subdivision(self.selected_objects(), render_levels=value)

    # ------------------------------------------------------------------ b-slots
    @btk.undoable
    def b000(self):
        """Quadrangulate (tris -> quads)."""
        btk.tris_to_quads(self.selected_objects())

    @btk.undoable
    def b001(self):
        """Triangulate"""
        btk.triangulate(self.selected_objects())

    @btk.undoable
    def b005(self):
        """Reduce (decimate to 50%)."""
        objects = self.selected_objects()
        if not objects:
            return
        btk.decimate(objects, percentage=50.0)

    @btk.undoable
    def b008(self):
        """Add Divisions - Subdivide Mesh"""
        btk.subdivide_mesh(self.selected_objects(), cuts=1)

    @btk.undoable
    def b011(self):
        """Apply Smooth Preview (live Subdivision-Surface modifier)."""
        btk.set_subdivision(self.selected_objects(), viewport_levels=1)

    # ------------------------------------------------------------------ deferred (Maya-specific)
    # (cmb001 Smooth-Proxy / cmb002 option-dialogs exist in no shared .ui — Maya's own handlers
    # are unreachable legacy — so no stubs are carried here.)
    def b028(self):
        """Quad Draw (Blender's retopo equivalent: the Poly Build tool)."""
        self.set_viewport_tool("builtin.poly_build", "Quad Draw")


# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
