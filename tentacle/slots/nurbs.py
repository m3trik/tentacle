# !/usr/bin/python
# coding=utf-8
"""NURBS: one Slots class for both hosts.

The curve actions -- the Nurbs list and Extrude -- are the host toolkit's
``NurbsUtils.curve_action`` (``self.tk``), named in the vocabulary both
libraries' ``NurbsUtils.CURVE_ACTIONS`` share: Maya runs its own menu command,
with the settings its option box last applied; Blender a curve-data
equivalent. Each is one undo step in its host. The parametric-NURBS actions
Blender has no counterpart for (curve-length locks, isoparms, knots, the
tolerance and on-surface extends) are Maya's: their rows are tagged
``requires="maya"`` and hidden in Blender.

Revolve and Loft build a NURBS surface in Maya and a mesh in Blender, so the
options only a parametric surface carries (degree, parameterization, range,
tolerance, polygon output, the angle loft) are Maya's alike. Image Tracer and
Curve to Tube open their shared tool panels.
"""

from tentacle import Slots


class NurbsSlots(Slots):
    #: The Nurbs list: ``{category: [(label, action, requires), ...]}``. *action*
    #: is a ``NurbsUtils.CURVE_ACTIONS`` key, or a viewport tool's name for the
    #: rows in :attr:`_TOOLS`; *requires* names the one host that serves the row
    #: (``None``: both), applied through uitk's visibility policy like a ``.ui``
    #: widget's ``requires`` tag. Labels and order are Maya's menu's.
    _LIST000_ITEMS = {
        "Create": [
            ("Project", "project", None),
            ("Extract", "extract", None),
            ("Duplicate", "duplicate", None),
        ],
        "Modify": [
            ("Lock", "lock_length", "maya"),
            ("Unlock", "unlock_length", "maya"),
            ("Bend", "bend", None),
            ("Curl", "curl", None),
            ("Curvature", "scale_curvature", None),
            ("Smooth", "smooth", None),
            ("Straighten", "straighten", None),
        ],
        "Surfaces": [
            ("Planar", "planar", None),
            ("Insert Isoparm", "insert_isoparm", "maya"),
        ],
        "Edit": [
            ("Edit Curve Tool", "Edit Curve Tool", None),
            ("Attach", "attach", None),
            ("Detach", "detach", None),
            ("Cut", "cut", None),
            ("Open/Close", "open_close", None),
            ("Insert Knot", "insert_knot", "maya"),
            ("Add Points Tool", "Add Points Tool", None),
            ("Rebuild", "rebuild", None),
            ("Reverse", "reverse", None),
            ("Extend (Options)", "extend_options", "maya"),
            ("Extend", "extend", None),
            ("Extend on Surface", "extend_on_surface", "maya"),
        ],
    }

    #: Rows that activate a viewport tool (:meth:`Slots.activate_tool`, a name
    #: ``UiUtils.set_tool`` knows in both hosts) instead of running an action.
    _TOOLS = frozenset({"Edit Curve Tool", "Add Points Tool"})

    def __init__(self, switchboard):
        super().__init__(switchboard)
        self.ui = self.sb.loaded_ui.nurbs
        self.submenu = self.sb.loaded_ui.nurbs_submenu

    def _curve_action(self, label, action):
        """Run the curve action *action* on the selection; a refusal (the wrong
        selection, the host's own error) reaches the user as the host words it."""
        try:
            self.tk.NurbsUtils.curve_action(action)
        except (RuntimeError, ValueError) as error:
            self.sb.message_box(f"Nurbs <hl>{label}</hl>: {error}")

    # ------------------------------------------------------------------ list000  Nurbs actions
    def list000_init(self, widget):
        """Initialize the Nurbs expandable list (root -> category -> curve action)."""
        widget.fixed_item_height = 18
        widget.apply_preset(
            "expand_overlay" if widget.ui.has_tags("submenu") else "hover_menu"
        )
        root = widget.add("Nurbs")
        for category, rows in self._LIST000_ITEMS.items():
            cat = root.sublist.add(category)
            items = cat.sublist.add([label for label, _action, _requires in rows])
            for item, (_label, _action, requires) in zip(items, rows):
                self.requires(item, requires)

    @Slots.Signals("on_item_interacted")
    def list000(self, item):
        """Run a Nurbs leaf: its curve action, or its viewport tool. A category row
        (one with a populated sublist) is navigation only."""
        if getattr(item, "sublist", None) and item.sublist.get_items():
            return
        text = item.item_text()
        parent = item.parent_item_text() or ""
        for label, action, _requires in self._LIST000_ITEMS.get(parent, ()):
            if label == text:
                if action in self._TOOLS:
                    self.activate_tool(action)
                else:
                    self._curve_action(label, action)
                return

    # ------------------------------------------------------------------ buttons
    def b030(self):
        """Extrude: sweep the selected profile curve along a path curve, or
        extrude a single curve into a surface."""
        self._curve_action("Extrude", "extrude")

    def b056(self):
        """Image Tracer"""
        self.sb.handlers.marking_menu.show("image_tracer")

    def b058(self):
        """Curve to Tube"""
        self.sb.handlers.marking_menu.show("curve_to_tube")

    # ------------------------------------------------------------------ tb000  Revolve
    def tb000_init(self, widget):
        """Initialize Revolve."""
        menu = widget.option_box.menu
        menu.setTitle("Revolve")
        self.requires(
            menu.add(
                "QSpinBox",
                setPrefix="Degree:",
                setObjectName="s002",
                setValue=3,
                set_limits=[0],
                setToolTip="The degree of the resulting surface.",
            ),
            "maya",
        )
        menu.add(
            "QSpinBox",
            setPrefix="Start Sweep:",
            setObjectName="s003",
            setValue=0,
            set_limits=[0, 360],
            setToolTip="The start angle of the swept arc (degrees).",
        )
        menu.add(
            "QSpinBox",
            setPrefix="End Sweep:",
            setObjectName="s004",
            setValue=360,
            set_limits=[0, 360],
            setToolTip="The end angle of the swept arc (degrees).",
        )
        menu.add(
            "QSpinBox",
            setPrefix="Sections:",
            setObjectName="s005",
            setValue=8,
            set_limits=[2, 256],
            setToolTip="The number of segments around the revolution.",
        )
        menu.add(
            "QComboBox",
            addItems=["Y", "Z", "X"],
            setObjectName="cmb_screw_axis",
            setToolTip="The axis to revolve about, through the profile's own pivot "
            "(Blender: its origin).",
        )
        self.requires(
            menu.add(
                "QCheckBox",
                setText="Range",
                setObjectName="chk006",
                setChecked=False,
                setToolTip="Force a curve range on the complete input curve.",
            ),
            "maya",
        )
        self.requires(
            menu.add(
                "QCheckBox",
                setText="Polygon",
                setObjectName="chk007",
                setChecked=True,
                setToolTip="Output a polygon mesh rather than a NURBS surface.",
            ),
            "maya",
        )
        menu.add(
            "QCheckBox",
            setText="Auto Correct Normal",
            setObjectName="chk008",
            setChecked=False,
            setToolTip="Reverse the surface direction where needed so its normals point "
            "outward (Blender: the Screw modifier's Calculate Order).",
        )
        self.requires(
            menu.add(
                "QCheckBox",
                setText="Use Tolerance",
                setObjectName="chk009",
                setChecked=False,
                setToolTip="Build to the tolerance rather than the number of sections.",
            ),
            "maya",
        )
        self.requires(
            menu.add(
                "QDoubleSpinBox",
                setPrefix="Tolerance:",
                setObjectName="s006",
                setValue=0.001,
                set_limits=[0],
                setToolTip="The tolerance to build to (when Use Tolerance is on).",
            ),
            "maya",
        )

    def tb000(self, widget):
        """Revolve: sweep the selected profile curve around an axis into a surface."""
        menu = widget.option_box.menu
        try:
            surfaces = self.tk.NurbsUtils.revolve(
                None,
                axis=menu.cmb_screw_axis.currentText(),
                start_sweep=menu.s003.value(),
                end_sweep=menu.s004.value(),
                sections=menu.s005.value(),
                degree=menu.s002.value(),
                range_=menu.chk006.isChecked(),
                polygon=menu.chk007.isChecked(),
                use_tolerance=menu.chk009.isChecked(),
                tolerance=menu.s006.value(),
                auto_correct_normal=menu.chk008.isChecked(),
            )
        except (RuntimeError, ValueError) as error:
            self.sb.message_box(f"Revolve: {error}")
            return
        if surfaces == []:
            self.sb.message_box(
                "<b>Revolve</b> needs a selected profile curve "
                "(Blender: a curve or mesh object)."
            )

    # ------------------------------------------------------------------ tb001  Loft
    def tb001_init(self, widget):
        """Initialize Loft."""
        menu = widget.option_box.menu
        menu.setTitle("Loft")
        self.requires(
            menu.add(
                "QCheckBox",
                setText="Uniform",
                setObjectName="chk000",
                setChecked=True,
                setToolTip="Uniform parameterization in the loft direction; off, chord "
                "length.",
            ),
            "maya",
        )
        menu.add(
            "QCheckBox",
            setText="Close",
            setObjectName="chk001",
            setChecked=False,
            setToolTip="Close the surface: the last profile bridges back to the first.",
        )
        self.requires(
            menu.add(
                "QSpinBox",
                setPrefix="Degree:",
                setObjectName="s000",
                setValue=3,
                set_limits=[0],
                setToolTip="The degree of the resulting surface.",
            ),
            "maya",
        )
        self.requires(
            menu.add(
                "QCheckBox",
                setText="Auto Reverse",
                setObjectName="chk002",
                setChecked=False,
                setToolTip="Compute the direction of the profiles automatically.",
            ),
            "maya",
        )
        menu.add(
            "QSpinBox",
            setPrefix="Section Spans:",
            setObjectName="s001",
            setValue=1,
            set_limits=[0],
            setToolTip="The number of spans between consecutive profiles.",
        )
        self.requires(
            menu.add(
                "QCheckBox",
                setText="Range",
                setObjectName="chk003",
                setChecked=False,
                setToolTip="Force a curve range on the complete input curve.",
            ),
            "maya",
        )
        self.requires(
            menu.add(
                "QCheckBox",
                setText="Polygon",
                setObjectName="chk004",
                setChecked=True,
                setToolTip="Output a polygon mesh rather than a NURBS surface.",
            ),
            "maya",
        )
        menu.add(
            "QCheckBox",
            setText="Reverse Surface Normals",
            setObjectName="chk005",
            setChecked=True,
            setToolTip="Reverse the surface normals (Maya swaps the U and V directions; "
            "Blender flips the winding).",
        )
        self.requires(
            menu.add(
                "QCheckBox",
                setText="Angle Loft Between Two Curves",
                setObjectName="chk010",
                setChecked=False,
                setToolTip="Loft at an angle between two selected curves or polygon edge "
                "sets (edges are extracted as curves).",
            ),
            "maya",
        )
        self.requires(
            menu.add(
                "QSpinBox",
                setPrefix="Angle Loft: Spans:",
                setObjectName="s007",
                setValue=6,
                set_limits=[2],
                setToolTip="Angle loft: the number of spans.",
            ),
            "maya",
        )

    def tb001(self, widget):
        """Loft: build a surface lofted across the selected profile curves."""
        menu = widget.option_box.menu
        try:
            lofted = self.tk.NurbsUtils.loft(
                uniform=menu.chk000.isChecked(),
                close=menu.chk001.isChecked(),
                degree=menu.s000.value(),
                autoReverse=menu.chk002.isChecked(),
                sectionSpans=menu.s001.value(),
                range_=menu.chk003.isChecked(),
                polygon=menu.chk004.isChecked(),
                reverseSurfaceNormals=menu.chk005.isChecked(),
                angle_loft_between_two_curves=menu.chk010.isChecked(),
                angleLoftSpans=menu.s007.value(),
            )
        except (RuntimeError, ValueError) as error:
            self.sb.message_box(f"Loft: {error}")
            return
        if not lofted:
            self.sb.message_box(
                "<b>Loft</b> needs two or more profiles: select the curves "
                "(Blender: or meshes) to loft across."
            )


# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
