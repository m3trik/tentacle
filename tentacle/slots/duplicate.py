# !/usr/bin/python
# coding=utf-8
"""Duplicate: one Slots class for both hosts.

Instancing is the host's: Maya's shared shapes, Blender's linked duplicates
(objects sharing one ``data``), behind the same ``self.tk.NodeUtils`` /
``self.tk.AutoInstancer`` operations, each one undo step. The Mirror and
Duplicate Linear / Radial / Grid buttons open the shared tool panels.
"""

from tentacle import Slots


class DuplicateSlots(Slots):
    def header_init(self, widget):
        """Header menu: the Mirror / Duplicate Linear / Radial / Grid launchers."""
        # Every entry is a one-shot action: dismiss the menu once one is triggered.
        widget.menu.hide_on_trigger = True
        widget.menu.add(
            "QPushButton",
            setText="Mirror",
            setObjectName="b000",
            setToolTip="Open the mirror window.",
        )
        widget.menu.add(
            "QPushButton",
            setText="Duplicate Linear",
            setObjectName="b006",
            setToolTip="Open the duplicate linear window.",
        )
        widget.menu.add(
            "QPushButton",
            setText="Duplicate Radial",
            setObjectName="b007",
            setToolTip="Open the duplicate radial window.",
        )
        widget.menu.add(
            "QPushButton",
            setText="Duplicate Grid",
            setObjectName="b008",
            setToolTip="Open the duplicate grid window.",
        )

    # ------------------------------------------------------------------ tb002  Auto Instance
    def tb002_init(self, widget):
        """Initialize Auto Instance: configure the option-box menu."""
        menu = widget.option_box.menu
        menu.setTitle("Auto Instance")

        menu.add(
            "QDoubleSpinBox",
            setPrefix="Tolerance: ",
            setObjectName="s000",
            setDecimals=5,
            setMinimum=0.0,
            setMaximum=10.0,
            setSingleStep=0.0001,
            setValue=0.001,
            setToolTip="Maximum average vertex deviation for two meshes to be considered identical.",
        )
        menu.add(
            "QCheckBox",
            setText="Require Same Material",
            setObjectName="chk004",
            setChecked=True,
            setToolTip="Only match objects that share the same assigned material(s).",
        )
        menu.add(
            "QCheckBox",
            setText="Check UVs",
            setObjectName="chk005",
            setChecked=False,
            setToolTip="Additionally require matching UV layout (slower).",
        )
        chk_hierarchy = menu.add(
            "QCheckBox",
            setText="Match Whole Hierarchies",
            setObjectName="chk006",
            setChecked=False,
            setToolTip=(
                "On: compare and instance entire group/assembly hierarchies.\n"
                "Off: compare and instance individual mesh objects only (leaf mode).\n"
                "Ignored (grayed out) when Separate Combined Meshes is enabled — "
                "that mode determines hierarchy vs. leaf matching itself."
            ),
        )
        chk_separate = menu.add(
            "QCheckBox",
            setText="Separate Combined Meshes",
            setObjectName="chk007",
            setChecked=False,
            setToolTip="Split combined meshes into their original parts and reassemble matching assemblies before instancing.",
        )
        chk_combine = menu.add(
            "QCheckBox",
            setText="Combine Reassembled Assemblies",
            setObjectName="chk008",
            setChecked=True,
            setEnabled=False,
            setToolTip=(
                "Merge each reassembled assembly into a single combined mesh "
                "before instancing — assembly-level instances instead of many "
                "micro part instances. Uncheck to keep parts separate and "
                "instance assemblies as hierarchies."
            ),
        )
        # Separate Combined Meshes derives its own hierarchy/leaf mode
        # (AutoInstancer._run): Match Whole Hierarchies has no effect while it
        # is on, so it is disabled rather than left a misleading control.
        chk_separate.toggled.connect(chk_combine.setEnabled)
        chk_separate.toggled.connect(
            lambda checked: chk_hierarchy.setEnabled(not checked)
        )

        chk_combine_rest = menu.add(
            "QCheckBox",
            setText="Combine Non-Instanced",
            setObjectName="chk009",
            setChecked=True,
            setToolTip=(
                "After instancing, merge everything that did not become an "
                "instance (unique leftovers, one-off assemblies) into combined "
                "meshes — fewer draw calls for a game-ready result.\n"
                "Skipped automatically for non-static setups."
            ),
        )
        chk_by_mat = menu.add(
            "QCheckBox",
            setText="   By Material",
            setObjectName="chk010",
            setChecked=True,
            setToolTip="Combine into one mesh per assigned material.",
        )
        chk_by_dist = menu.add(
            "QCheckBox",
            setText="   By Distance",
            setObjectName="chk011",
            setChecked=True,
            setToolTip="Subdivide combine groups by spatial proximity (culling-friendly).",
        )
        s_dist = menu.add(
            "QDoubleSpinBox",
            setPrefix="Cluster Distance: ",
            setObjectName="s001",
            setDecimals=0,
            setMinimum=1.0,
            setMaximum=1000000.0,
            setSingleStep=100.0,
            setValue=10000.0,
            setToolTip="Maximum distance between meshes combined into the same cluster.",
        )
        chk_combine_rest.toggled.connect(chk_by_mat.setEnabled)
        chk_combine_rest.toggled.connect(chk_by_dist.setEnabled)
        chk_combine_rest.toggled.connect(s_dist.setEnabled)

    def tb002(self, widget):
        """Auto Instance: convert geometrically identical meshes into instances
        of one prototype (the selection, or the whole scene with nothing
        selected), then select what was made."""
        menu = widget.option_box.menu
        made, summary = self.tk.AutoInstancer.run_once(
            None,
            tolerance=menu.s000.value(),
            require_same_material=menu.chk004.isChecked(),
            check_uvs=menu.chk005.isChecked(),
            check_hierarchy=menu.chk006.isChecked(),
            separate_combined=menu.chk007.isChecked(),
            combine_assemblies=menu.chk008.isChecked(),
            combine_non_instanced=menu.chk009.isChecked(),
            combine_by_material=menu.chk010.isChecked(),
            combine_by_distance=menu.chk011.isChecked(),
            combine_distance_threshold=menu.s001.value(),
            return_summary=True,
            select=True,
        )
        report = self.tk.AutoInstancer.format_summary(summary, len(made))
        report_html = report.replace("\n", "<br>")
        # To the log too, so "why nothing was instanced" (too simple / count)
        # outlives the message box: a run that instanced nothing is a warning.
        (self.sb.logger.info if made else self.sb.logger.warning)(report)

        if made:
            self.sb.message_box(report_html)
        elif summary.get("matched_groups"):
            # Identical meshes were found, but the strategy instanced none of
            # them (too simple: combined instead; flagged individual or
            # non-static): say so, not the generic no-match text.
            self.sb.message_box(
                "<strong>No objects were instanced</strong>.<br>" + report_html
            )
        else:
            self.sb.message_box(
                "<strong>No matching geometry found</strong>.<br>"
                "No identical meshes to instance and nothing to combine."
            )

    # ------------------------------------------------------------------ tb000  Convert to Instances
    def tb000_init(self, widget):
        menu = widget.option_box.menu
        menu.add(
            "QCheckBox",
            setText="Center Pivot",
            setObjectName="chk002",
            setChecked=True,
            setToolTip="Center the pivot on the object(s) before instancing.",
        )
        menu.add(
            "QCheckBox",
            setText="Freeze Translate",
            setObjectName="chk000",
            setChecked=False,
            setToolTip=self.sb.tooltip.fmt(
                title="Freeze Translate",
                body="Zero the translation values before instancing.",
                notes=[
                    "Rotation and scale are deliberately left unfrozen so each "
                    "instance can keep its own orientation and size relative to "
                    "the shared shape.",
                ],
            ),
        )
        chk_retain = menu.add(
            "QCheckBox",
            setText="Retain Relative Scale",
            setObjectName="chk012",
            setChecked=False,
            setToolTip=self.sb.tooltip.fmt(
                title="Retain Relative Scale",
                body="Keep each object at its current apparent size: the instance "
                "is uniformly scaled until its world-space bounding box matches "
                "the object it replaced.",
                notes=[
                    "Use it when identical shapes differ in size at the geometry "
                    "level (frozen / baked scale), where the transform's own scale "
                    "values don't reflect what you see.",
                ],
            ),
        )
        chk_per_axis = menu.add(
            "QCheckBox",
            setText="   Non-Uniform (Per Axis)",
            setObjectName="chk013",
            setChecked=False,
            setEnabled=False,
            setToolTip=self.sb.tooltip.fmt(
                title="Non-Uniform (Per Axis)",
                body="Fit each axis independently instead of uniformly. Instances "
                "carry their own scale values, so a non-uniform result is legal.",
                notes=[
                    "Matched in the object's local frame, so it holds under "
                    "any rotation.",
                    "An axis with no size on either side (flat vs. solid) has no "
                    "ratio to match and is left alone.",
                    "Off is safer: a per-axis fit reaches the target's box by "
                    "stretching the shared shape whenever the proportions differ.",
                ],
            ),
        )
        chk_retain.toggled.connect(chk_per_axis.setEnabled)
        chk_history = menu.add(
            "QCheckBox",
            setText="Delete History",
            setObjectName="chk001",
            setChecked=True,
            setToolTip="Delete history on the object(s) before instancing.",
        )
        # Construction history is Maya's: Blender has none to delete, so the
        # option is hidden there (the engine takes the flag for parity only).
        self.requires(chk_history, "maya")

    def tb000(self, widget):
        """Convert to Instances: the other selected objects become instances of
        the source -- the first selected (Maya) or the active object (Blender)."""
        menu = widget.option_box.menu
        if self.require_selection(self.NOTHING_SELECTED) is None:
            return
        try:
            self.tk.NodeUtils.replace_with_instances(
                None,
                freeze_transforms=menu.chk000.isChecked(),
                center_pivot=menu.chk002.isChecked(),
                delete_history=menu.chk001.isChecked(),
                retain_bbox_scale=menu.chk012.isChecked(),
                retain_bbox_per_axis=menu.chk013.isChecked(),
            )
        except ValueError as error:  # fewer than two objects, or no compatible target
            self.sb.message_box(f"<strong>Insufficient selection</strong>.<br>{error}")
        except RuntimeError as error:  # the host refused to leave Edit Mode
            self.sb.message_box(str(error))

    # ------------------------------------------------------------------ tb001  Select Instanced
    def tb001_init(self, widget):
        widget.option_box.menu.add(
            "QCheckBox",
            setText="All Instanced Objects",
            setObjectName="chk003",
            setChecked=True,
            setToolTip="Select every instanced object in the scene, not just instances of the selection.",
        )

    def tb001(self, widget):
        """Select Instanced Objects: the selection and its instances, or every
        instanced object in the scene."""
        if widget.option_box.menu.chk003.isChecked():
            selected = self.tk.NodeUtils.select_instances(whole_scene=True)
        else:
            selection = self.require_selection(
                "<strong>Nothing selected</strong>.<br>Select objects to find their "
                "instances, or enable 'All Instanced Objects'."
            )
            if selection is None:
                return
            selected = self.tk.NodeUtils.select_instances(selection)
        if not selected:
            self.sb.message_box("<strong>No instanced objects found</strong>.")

    # ------------------------------------------------------------------ b005  Uninstance
    def b005(self):
        """Uninstance Selected Objects: each gets its own copy of the shared
        shape (Maya) or data (Blender). Nothing selected, nothing to do."""
        try:
            self.tk.NodeUtils.uninstance(None)
        except RuntimeError as error:  # the host refused to leave Edit Mode
            self.sb.message_box(str(error))

    # ------------------------------------------------------------------ tool panels
    def b000(self):
        """Mirror: open the Mirror tool window."""
        self.sb.handlers.marking_menu.show("mirror")

    def b006(self):
        """Duplicate Linear"""
        self.sb.handlers.marking_menu.show("duplicate_linear")

    def b007(self):
        """Duplicate Radial"""
        self.sb.handlers.marking_menu.show("duplicate_radial")

    def b008(self):
        """Duplicate Grid"""
        self.sb.handlers.marking_menu.show("duplicate_grid")
