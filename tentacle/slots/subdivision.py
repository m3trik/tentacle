# !/usr/bin/python
# coding=utf-8
"""Subdivision: one Slots class for both hosts.

Every operation is the host toolkit's ``EditUtils`` / ``DisplayUtils``
(``self.tk``), given ``None`` for the selection; each is one undo step in its
host, and with no mesh to act on returns ``[]`` without running. Maya runs its
own menu commands (Quadrangulate, Add Divisions, Convert Smooth Preview, with
the settings their option boxes last applied) and its smooth mesh preview;
Blender edits the mesh with bmesh and drives a Subdivision Surface modifier.

Decimate's two algorithms honor different options in each host -- Maya's
quadric-error reduce holds borders, hard edges and UV borders, Blender's
planar dissolve does -- so the option box greys out what the host's
``EditUtils.DECIMATE_OPTIONS`` says the chosen algorithm ignores.
"""

from tentacle import Slots


class SubdivisionSlots(Slots):
    #: The Decimate option box: widget -> (the ``DECIMATE_OPTIONS`` keyword it
    #: sets, the reader of its value).
    _DECIMATE_WIDGETS = {
        "s010": ("percentage", "value"),
        "chk010": ("preserve_borders", "isChecked"),
        "chk011": ("preserve_hard_edges", "isChecked"),
        "chk012": ("preserve_uv_borders", "isChecked"),
        "chk013": ("preserve_quads", "isChecked"),
        "chk014": ("symmetry", "isChecked"),
        "s011": ("angle_tolerance", "value"),
    }

    NO_MESH = (
        "<strong>No mesh in the selection</strong>.<br>"
        "Select polygon meshes or their components."
    )

    def __init__(self, switchboard):
        super().__init__(switchboard)
        self.ui = self.sb.loaded_ui.subdivision
        self.submenu = self.sb.loaded_ui.subdivision_submenu

    def _report(self, result):
        """Say so when an operation found no mesh to act on (it returned ``[]``)."""
        if result == []:
            self.sb.message_box(self.NO_MESH)

    # --------------------------------------------------- s000/s001  smooth preview
    # The mesh owns these levels (Maya: its smooth preview; Blender: its Subdivision
    # Surface modifier), so the spinboxes mirror the selection rather than persisting
    # their own copy: a restored value re-fires the slot on panel open, which would
    # smooth (and re-tessellate) whatever happened to be selected.
    def _init_smooth_level(self, widget, key):
        levels = self.tk.DisplayUtils.get_smooth_level()
        self.mirror_app_state(
            widget, (lambda: widget.setValue(levels[key])) if levels else None
        )

    def s000_init(self, widget):
        """Division Level: reflect the selection's live preview division level."""
        self._init_smooth_level(widget, "level")

    def s001_init(self, widget):
        """Tessellation Level: reflect the selection's live tessellation level."""
        self._init_smooth_level(widget, "adaptive_level")

    def _set_smooth_level(self, label, value, **level):
        """Set a smooth-preview level on the selection and say how many meshes
        took it (a locked or connected one keeps its own)."""
        try:
            meshes = self.tk.DisplayUtils.set_smooth_level(None, **level)
        except ValueError as error:
            self.sb.message_box(f"{label} <hl>{value}</hl>: {error}")
            return
        if meshes:
            self.sb.message_box(
                f"{label}: <hl>{value}</hl> on <hl>{len(meshes)}</hl> mesh(es)."
            )

    def s000(self, value: int, widget: object) -> None:
        """Division Level (Maya: the smooth preview's divisions; Blender: the
        Subdivision Surface viewport level)."""
        self._set_smooth_level("Division Level", value, level=value)

    def s001(self, value: int, widget: object) -> None:
        """Tessellation Level (Maya: OpenSubdiv adaptive tessellation; Blender: the
        Subdivision Surface render level)."""
        self._set_smooth_level("Tessellation Level", value, adaptive_level=value)

    # ------------------------------------------------------------------ buttons
    def b000(self):
        """Quadrangulate: merge triangles into quads."""
        self._report(self.tk.EditUtils.quadrangulate(None))

    def b001(self):
        """Triangulate: split the selected faces into triangles."""
        self._report(self.tk.EditUtils.triangulate(None))

    def b005(self):
        """Reduce: halve the polygon count -- the one-click form of tb000's Reduce
        (Maya keeps the polyReduce node, so it stays tweakable); whole meshes or,
        given a component selection (Blender: in Edit Mode), only that region."""
        if self.require_selection() is None:
            return
        if not self.tk.EditUtils.decimate(None, percentage=50.0, delete_history=False):
            self.sb.message_box(self.NO_MESH)

    def b008(self):
        """Add Divisions: subdivide the selected mesh."""
        self._report(self.tk.EditUtils.subdivide_mesh(None))

    def b011(self):
        """Convert Preview: bake the smooth preview into polygons."""
        applied = self.tk.EditUtils.apply_subdivision(None)
        if not applied:
            self.sb.message_box("No smooth preview to convert on the selection.")
            return
        self.sb.message_box(
            f"Converted the smooth preview on <hl>{len(applied)}</hl> object(s)."
        )

    def b028(self):
        """Quad Draw: Maya's retopology tool (Blender: Poly Build)."""
        self.activate_tool("Quad Draw")

    # ------------------------------------------------------------------ tb000  Decimate
    @staticmethod
    def _algorithm(menu):
        """The chosen Decimate algorithm: ``"reduce"`` or ``"planar"``."""
        return "planar" if menu.cmb000.currentData() == "planar" else "reduce"

    def tb000_init(self, widget):
        """Initialize Decimate."""
        menu = widget.option_box.menu
        menu.setTitle("Decimate")
        cmb = menu.add(
            "QComboBox",
            setObjectName="cmb000",
            setToolTip="Decimation algorithm.\n"
            "• Reduce: remove a percent of the faces (Maya: quadric-error polyReduce; "
            "Blender: a Decimate collapse).\n"
            "• Planar: dissolve the edges between near-coplanar faces; lossless on "
            "hard-surface meshes.",
        )
        for text, data in (
            ("Reduce (Face %)", "reduce"),
            ("Planar (Coplanar Dissolve)", "planar"),
        ):
            cmb.addItem(text, data)
        menu.add(
            "QDoubleSpinBox",
            setPrefix="Reduce %: ",
            setObjectName="s010",
            set_limits=[0, 99, 1, 1],
            setValue=50.0,
            set_fixed_height=20,
            setToolTip="Percent of faces to remove.",
        )
        menu.add(
            "QCheckBox",
            setText="Preserve Borders",
            setObjectName="chk010",
            setChecked=True,
            setToolTip="Hold open mesh borders fixed.",
        )
        menu.add(
            "QCheckBox",
            setText="Preserve Hard/Crease Edges",
            setObjectName="chk011",
            setChecked=True,
            setToolTip="Hold hard and crease edges (Blender: sharp edges).",
        )
        menu.add(
            "QCheckBox",
            setText="Preserve UV Borders",
            setObjectName="chk012",
            setChecked=True,
            setToolTip="Hold UV borders.",
        )
        menu.add(
            "QCheckBox",
            setText="Preserve Quads",
            setObjectName="chk013",
            setChecked=True,
            setToolTip="Bias the reduction toward keeping quads.",
        )
        menu.add(
            "QCheckBox",
            setText="Symmetry (X)",
            setObjectName="chk014",
            setChecked=False,
            setToolTip="Reduce symmetrically about X.",
        )
        menu.add(
            "QDoubleSpinBox",
            setPrefix="Angle Tolerance: ",
            setObjectName="s011",
            set_limits=[0, 180, 0.5, 1],
            setValue=1.0,
            set_fixed_height=20,
            setToolTip="Max dihedral angle (degrees) treated as coplanar; "
            "near 0 is lossless on hard-surface meshes.",
        )

        # Grey out what the host's chosen algorithm ignores.
        def _sync(*_):
            honored = self.tk.EditUtils.DECIMATE_OPTIONS[self._algorithm(menu)]
            for name, (option, _reader) in self._DECIMATE_WIDGETS.items():
                getattr(menu, name).setEnabled(option in honored)

        menu.cmb000.currentIndexChanged.connect(_sync)
        _sync()

    def tb000(self, widget):
        """Decimate: reduce the face count by percentage, or dissolve coplanar faces.

        Acts on the selection as-is: whole meshes, or a component selection
        (Blender: in Edit Mode) to decimate only that region.
        """
        if (
            self.require_selection(
                "<strong>Nothing selected</strong>.<br>Select one or more meshes, "
                "or mesh components (Blender: in Edit Mode), to decimate."
            )
            is None
        ):
            return
        menu = widget.option_box.menu
        algorithm = self._algorithm(menu)
        honored = self.tk.EditUtils.DECIMATE_OPTIONS[algorithm]
        options = {
            option: getattr(getattr(menu, name), reader)()
            for name, (option, reader) in self._DECIMATE_WIDGETS.items()
            if option in honored
        }
        if algorithm == "planar":
            processed = self.tk.EditUtils.dissolve_coplanar(None, **options)
        else:
            processed = self.tk.EditUtils.decimate(None, **options)
        if not processed:
            self.sb.message_box(self.NO_MESH)


# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
