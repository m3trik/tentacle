# !/usr/bin/python
# coding=utf-8
"""Edit: one Slots class for both hosts.

Every operation is the host toolkit's (``self.tk``) and one undo step in its
host. Mesh Cleanup is ``Diagnostics.cleanup_meshes``: one call returning a
report this panel words, two ways (a short popup, a console breakdown); each
host runs the checks it has (Maya's ``polyCleanup``, Blender's bmesh scan), and
an option only one host serves is tagged ``requires`` and hidden on the other.
The Create, Convert and Transfer menus list what the host's library offers
(``Primitives.get_primitive_types``, ``EditUtils.get_conversion_types``,
``Components.get_transfer_types``), so every row runs; Create's Control rows
are the host's ``Controls`` shapes. Delete History is Maya's (construction
history); Optimize, Blender's purge of unused data-blocks, takes its place in
Blender.
"""

from tentacle import Slots


class EditSlots(Slots):
    #: Mesh Cleanup's checks: ``(check, objectName)`` -- the name
    #: ``Diagnostics.cleanup_meshes(checks=...)`` takes and the checkbox that
    #: turns it on. A host runs the ones it has.
    _CLEANUP_CHECKS = (
        ("ngons", "chk002"),
        ("nonplanar", "chk003"),
        ("quads", "chk010"),
        ("concave", "chk011"),
        ("holed", "chk012"),
        ("zero_area_faces", "chk013"),
        ("zero_length_edges", "chk014"),
        ("zero_uv_area", "chk015"),
        ("shared_uvs", "chk016"),
        ("nonmanifold", "chk017"),
        ("lamina", "chk018"),
    )

    #: How a report names each check's matches.
    _CHECK_LABELS = {
        "ngons": "N-Gons",
        "nonplanar": "Non-Planar",
        "quads": "Quads",
        "concave": "Concave",
        "holed": "Holed",
        "zero_area_faces": "Zero-Area Faces",
        "zero_length_edges": "Zero-Length Edges",
        "zero_uv_area": "Zero-UV-Area Faces",
        "shared_uvs": "Shared UVs",
        "nonmanifold": "Non-Manifold edges",
        "lamina": "Lamina",
    }

    #: Create > Control: the control shapes offered, in menu order. A host lists
    #: the ones its ``Controls`` registers (``Controls.shapes``); each row's label
    #: is the shape's name, title-cased.
    _CONTROL_SHAPES = (
        "circle",
        "square",
        "diamond",
        "arrow",
        "two_way_arrow",
        "four_way_arrow",
        "chevron",
        "target",
        "box",
        "beveled_cube",
        "ball",
        "torus",
        "helix",
        "geosphere",
        "pyramid",
        "star",
    )

    #: The scope combos' items: ``(label, data)``.
    _SCOPES = (("Selected", "selected"), ("Visible", "visible"), ("All Geometry", "all"))

    _SCOPE_TOOLTIP = (
        "• Selected: only the current selection.\n"
        "• Visible: every visible mesh in the scene.\n"
        "• All Geometry: every mesh in the scene."
    )

    def __init__(self, switchboard):
        super().__init__(switchboard)
        self.ui = self.sb.loaded_ui.edit
        self.submenu = self.sb.loaded_ui.edit_submenu

    def _requires(self, widget, host):
        """Tag an option only *host* serves; uitk hides it on the other host."""
        widget.setProperty("requires", host)
        self.sb.apply_visibility_policy(widget)
        return widget

    def header_init(self, widget):
        """Header menu: the submenu's Create / Convert lists, Channels and Cut On Axis."""
        # Every entry is a one-shot action: dismiss the menu once one is triggered.
        widget.menu.hide_on_trigger = True
        # The Create / Convert rows' flyouts fan right on hover (list000_init /
        # list001_init apply the hover_menu preset here).
        for list_name in ("list000", "list001"):
            widget.menu.add(
                self.sb.registered_widgets.ExpandableList,
                setObjectName=list_name,
            )
        widget.menu.add(
            "QPushButton",
            setText="Channels",
            setObjectName="b_channels",
            setToolTip="Open the Channels panel: inspect, edit, lock and key the "
            "selected object's channels and custom attributes (Blender: custom "
            "properties).",
        )
        widget.menu.add(
            "QPushButton",
            setText="Cut On Axis",
            setObjectName="b000",
            setToolTip="Cut the selected objects on an axis.",
        )

    def b_channels(self):
        """Channels: open the Channels panel."""
        self.sb.handlers.marking_menu.show("channels")

    def b000(self):
        """Cut On Axis: open the Cut On Axis tool (slice objects along an axis plane)."""
        self.sb.handlers.marking_menu.show("cut_on_axis")

    # ------------------------------------------------------------------ tb000  Mesh Cleanup
    def mesh_cleanup_tooltip(self):
        """Rich tooltip for the Mesh Cleanup button (``tb000``)."""
        return self.sb.tooltip.fmt(
            title="Mesh Cleanup",
            body="Find, or repair, common topology problems (n-gons, non-planar and "
            "non-manifold geometry, zero-area faces, zero-length edges, overlapping "
            "faces and objects, and more).",
            rows=[
                ("Scope", "Selected / Visible / All Geometry"),
                ("Mode", "Select (diagnose) or Repair (fix)"),
            ],
            notes=[
                "Use the option box to set scope, mode, and exactly which checks run."
            ],
        )

    def tb000_init(self, widget):
        """Initialize Mesh Cleanup."""
        widget.setToolTip(self.mesh_cleanup_tooltip())
        menu = widget.option_box.menu
        menu.setTitle("Mesh Cleanup")
        self._cleanup_general_options(menu)
        self._cleanup_repair_options(menu)
        self._cleanup_check_options(menu)
        self._cleanup_overlap_options(menu)
        self._cleanup_enable_rules(menu)

    def _cleanup_general_options(self, menu):
        menu.add("Separator", setTitle="General")
        cmb = menu.add(
            "QComboBox",
            setObjectName="cmb_scope",
            setToolTip=f"Which meshes Mesh Cleanup acts on:\n{self._SCOPE_TOOLTIP}",
        )
        for label, data in self._SCOPES:
            cmb.addItem(label, data)
        cmb = menu.add(
            "QComboBox",
            setObjectName="cmb_mode",
            setToolTip="What Mesh Cleanup does with the matches:\n"
            "• Select (diagnose): select the problem geometry so you can inspect it.\n"
            "• Repair (fix): fix the geometry in place.",
        )
        for label, data in (("Select (diagnose)", "select"), ("Repair (fix)", "repair")):
            cmb.addItem(label, data)
        # Construction history is Maya's: Blender has none to bake.
        self._requires(
            menu.add(
                "QCheckBox",
                setText="Delete History",
                setObjectName="chk026",
                setChecked=True,
                setToolTip="Bake non-deformer history before the cleanup runs.",
            ),
            "maya",
        )

    def _cleanup_repair_options(self, menu):
        menu.add("Separator", setTitle="Repair")
        menu.add(
            "QCheckBox",
            setText="Merge Vertices",
            setObjectName="chk024",
            setChecked=False,
            setToolTip="Repair: merge overlapping vertices first.",
        )
        menu.add(
            "QDoubleSpinBox",
            setPrefix="Merge Distance: ",
            setObjectName="s000",
            set_limits=[0, 1, 0.0001, 4],
            setValue=0.0001,
            set_fixed_height=20,
            setToolTip="Vertices closer than this are merged.",
        )
        # Blender's repair passes (bmesh); Maya's polyCleanup repairs what the
        # checks below find instead.
        blender = (
            menu.add(
                "QCheckBox",
                setText="Delete Loose",
                setObjectName="chk032",
                setChecked=True,
                setToolTip="Remove loose (wire) edges and unconnected vertices.",
            ),
            menu.add(
                "QCheckBox",
                setText="Dissolve Degenerate",
                setObjectName="chk033",
                setChecked=True,
                setToolTip="Dissolve zero-area faces and zero-length edges.",
            ),
            menu.add(
                "QCheckBox",
                setText="Recalculate Normals",
                setObjectName="chk028",
                setChecked=True,
                setToolTip="Make the face normals consistent (outward).",
            ),
            menu.add(
                "QCheckBox",
                setText="Fill Holes",
                setObjectName="chk029",
                setChecked=False,
                setToolTip="Fill open boundary holes.",
            ),
        )
        for box in blender:
            self._requires(box, "blender")

    def _cleanup_check_options(self, menu):
        menu.add("Separator", setTitle="Topology")
        menu.add(
            "QCheckBox",
            setText="N-Gons",
            setObjectName="chk002",
            setChecked=True,
            setToolTip="Faces with more than four sides.",
        )
        menu.add(
            "QCheckBox",
            setText="Non-Manifold Geometry",
            setObjectName="chk017",
            setChecked=True,
            setToolTip="Edges bordering other than two faces.",
        )
        menu.add(
            "QCheckBox",
            setText="Quads",
            setObjectName="chk010",
            setToolTip="Faces with exactly four sides.",
        )
        menu.add(
            "QCheckBox",
            setText="Concave",
            setObjectName="chk011",
            setToolTip="Non-convex faces.",
        )
        menu.add(
            "QCheckBox",
            setText="Non-Planar",
            setObjectName="chk003",
            setToolTip="Faces whose vertices don't lie in one plane.",
        )
        # Maya's: a Blender face holds no hole, and bmesh refuses a second face on
        # one vertex set.
        for box in (
            menu.add(
                "QCheckBox",
                setText="Holed",
                setObjectName="chk012",
                setToolTip="Faces with holes.",
            ),
            menu.add(
                "QCheckBox",
                setText="Lamina",
                setObjectName="chk018",
                setChecked=True,
                setToolTip="Faces sharing all their edges with another face.",
            ),
        ):
            self._requires(box, "maya")
        menu.add("Separator", setTitle="UVs")
        # Maya's: Blender's UVs are per face corner, so none can be shared.
        self._requires(
            menu.add(
                "QCheckBox",
                setText="Shared UVs",
                setObjectName="chk016",
                setToolTip="Unshare UVs shared across vertices.",
            ),
            "maya",
        )
        menu.add(
            "QCheckBox",
            setText="Zero UV Face Area",
            setObjectName="chk015",
            setToolTip="Faces whose area in the current UV set is at or below the tolerance.",
        )
        self._cleanup_tolerance(menu, "s008", "UV Face Area Tolerance:")
        menu.add("Separator", setTitle="Tolerances")
        menu.add(
            "QCheckBox",
            setText="Zero Face Area",
            setObjectName="chk013",
            setChecked=True,
            setToolTip="Faces whose area is at or below the tolerance (degenerate).",
        )
        self._cleanup_tolerance(menu, "s006", "Face Area Tolerance:   ")
        menu.add(
            "QCheckBox",
            setText="Zero Length Edges",
            setObjectName="chk014",
            setChecked=True,
            setToolTip="Edges at or below the length tolerance (degenerate).",
        )
        self._cleanup_tolerance(menu, "s007", "Edge Length Tolerance: ")

    @staticmethod
    def _cleanup_tolerance(menu, name, prefix):
        """The tolerance spin box of the check above it."""
        menu.add(
            "QDoubleSpinBox",
            setPrefix=prefix,
            setObjectName=name,
            set_limits=[0, 10, 0.00001, 6],
            setValue=0.000010,
            set_fixed_height=20,
            setToolTip="The tolerance for the check above.",
        )

    @staticmethod
    def _cleanup_overlap_options(menu):
        menu.add("Separator", setTitle="Overlapping")
        menu.add(
            "QCheckBox",
            setText="Overlapping Faces",
            setObjectName="chk025",
            setToolTip="Find faces coincident with another (doubled geometry): Repair "
            "deletes them, Select selects them. Can be slow on dense meshes.",
        )
        menu.add(
            "QCheckBox",
            setText="Overlapping Duplicate Objects",
            setObjectName="chk022",
            setToolTip="Find duplicate objects overlapping in the scene instead (the "
            "scope is not read): Repair deletes them, Select selects them.",
        )
        menu.add(
            "QCheckBox",
            setText="Omit Selected Objects",
            setObjectName="chk023",
            setToolTip="Overlapping Duplicate Objects: find the duplicates of the "
            "selected objects, keeping the selected ones.",
        )

    def _cleanup_enable_rules(self, menu):
        """Overlapping Duplicate Objects is a whole-object search: the mesh
        options don't apply while it is on, and Omit Selected only applies then.
        Each tolerance is live only while its check is on and the object search
        off -- one rule per pair, so neither owner stomps the other's state."""
        self.sb.enable_when(
            menu,
            "chk002-3,cmb_scope,chk010-18,chk024,chk026,chk028-29,chk032-33",
            "chk022",
            invert=True,
        )
        self.sb.enable_when(menu, "chk023", "chk022")
        for check, spin in (
            ("chk013", "s006"),
            ("chk014", "s007"),
            ("chk015", "s008"),
            ("chk024", "s000"),
        ):
            self.sb.enable_when(
                menu, spin, [check, "chk022"], lambda on, dup: bool(on) and not dup
            )

    def _cleanup_options(self, menu):
        """The option box, as ``Diagnostics.cleanup_meshes`` keyword arguments."""
        return dict(
            checks=[
                name
                for name, object_name in self._CLEANUP_CHECKS
                if getattr(menu, object_name).isChecked()
            ],
            area_tolerance=menu.s006.value(),
            edge_length_tolerance=menu.s007.value(),
            uv_area_tolerance=menu.s008.value(),
            merge_vertices=menu.chk024.isChecked(),
            merge_distance=menu.s000.value(),
            delete_history=menu.chk026.isChecked(),
            delete_loose=menu.chk032.isChecked(),
            dissolve_degenerate=menu.chk033.isChecked(),
            recalculate_normals=menu.chk028.isChecked(),
            fill_holes=menu.chk029.isChecked(),
            overlapping_faces=menu.chk025.isChecked(),
            overlapping_objects=menu.chk022.isChecked(),
            omit_selected=menu.chk023.isChecked(),
        )

    @Slots.Cancelable(120)
    def tb000(self, widget):
        """Mesh Cleanup: repair the problem geometry, or (Select) select it.

        Reported twice: a minimal popup and a console breakdown. A failing pass
        is reported the same way, never as a traceback."""
        menu = widget.option_box.menu
        scope = menu.cmb_scope.currentData() or "selected"
        repair = menu.cmb_mode.currentData() == "repair"
        mode = "Repair" if repair else "Select"
        try:
            report = self.tk.Diagnostics.cleanup_meshes(
                scope, repair, **self._cleanup_options(menu)
            )
        except (RuntimeError, ValueError) as error:
            self.report_cleanup_failure(scope, mode, error)
            return
        if report["duplicates"] is not None:
            self._report_duplicates(mode, report["duplicates"], repair)
        elif not report["objects"]:
            self.sb.message_box(
                f"<hl>Mesh Cleanup — {mode}</hl><br>"
                f"No mesh found for scope '<hl>{scope}</hl>'.<br>Select a mesh or change Scope."
            )
        elif repair:
            self._report_repair(scope, report, menu.chk025.isChecked())
        elif not (report["checks"] or menu.chk025.isChecked()):
            self.sb.message_box(
                "<hl>Mesh Cleanup — Select</hl><br>"
                "Enable a check (N-Gons, Concave, …) or Overlapping Faces to select."
            )
        else:
            self._report_select(scope, report)

    def _report_duplicates(self, mode, count, repair):
        verb = "deleted" if repair else "selected"
        self.cleanup_console_report(
            f"{mode} · Overlapping Duplicate Objects",
            [f"{count} overlapping duplicate object(s) ({verb})"],
        )
        self.sb.message_box(
            self.cleanup_popup_html(
                f"<hl>Mesh Cleanup — {mode}</hl>",
                [(count, f"overlapping duplicate objects {verb}")],
            )
        )

    def _report_repair(self, scope, report, overlapping):
        count = len(report["objects"])
        (verts_before, verts_after), (faces_before, faces_after) = (
            report["vertices"],
            report["faces"],
        )
        removed_v, removed_f = verts_before - verts_after, faces_before - faces_after
        lines = [
            f"scope: {scope} · {count} mesh(es)",
            f"operations: {', '.join(report['repairs']) or 'none'}",
            f"verts: {verts_before} -> {verts_after} (removed {removed_v})",
            f"faces: {faces_before} -> {faces_after} (removed {removed_f})",
        ]
        if overlapping:
            lines.append(f"overlapping faces deleted: {report['overlapping_faces']}")
        self.cleanup_console_report("Repair", lines)
        self.sb.message_box(
            self.cleanup_popup_html(
                f"<hl>Mesh Cleanup — Repair</hl> · <hl>{count}</hl> mesh(es)",
                [
                    (removed_v, "verts removed"),
                    (removed_f, "faces removed"),
                    (report["overlapping_faces"], "overlapping faces deleted"),
                ],
            )
        )

    def _report_select(self, scope, report):
        """Matches per check where the host counts them (Blender), else in all
        (Maya's polyCleanup selects them together); overlapping faces apart."""
        rows = [
            (count, self._CHECK_LABELS.get(name, name))
            for name, count in report["problems"].items()
            if count
        ]
        if not rows and report["selected"]:
            rows.append((report["selected"], "Problem components"))
        if report["overlapping_faces"]:
            rows.append((report["overlapping_faces"], "Overlapping Faces"))
        total = sum(count for count, _ in rows)
        self.cleanup_console_report(
            "Select",
            [
                f"scope: {scope} · {len(report['objects'])} mesh(es)",
                *[f"{label}: {count}" for count, label in rows],
                f"total problem components: {total}",
            ],
        )
        self.sb.message_box(
            self.cleanup_popup_html(
                f"<hl>Mesh Cleanup — Select</hl> · <hl>{total}</hl> total", rows
            )
        )

    @staticmethod
    def cleanup_popup_html(header, rows):
        """Minimal HTML for the Mesh Cleanup popup -- glanceable, one fact per line.

        Parameters:
            header (str): a short, already-marked-up lead line.
            rows (iterable): ``(count, label)`` pairs. Zero counts are dropped, so the
                popup shows only what happened; with none left it reads "nothing found".

        Returns:
            str: ``header`` followed by one ``<hl>count</hl> label`` line per non-zero row.
        """
        body = "<br>".join(f"<hl>{count}</hl> {label}" for count, label in rows if count)
        return f"{header}<br>{body}" if body else f"{header}<br>nothing found"

    def cleanup_console_report(self, title, lines):
        """The detailed Mesh Cleanup report, to the host's console (Maya's Script
        Editor, Blender's system console): a ``# Mesh Cleanup — <title>`` header,
        then one ``#   <line>`` per fact. Written raw (``log_raw``), so no log
        level holds it back."""
        self.sb.logger.log_raw(f"# Mesh Cleanup — {title}")
        for line in lines:
            self.sb.logger.log_raw(f"#   {line}")

    def report_cleanup_failure(self, scope, mode, error):
        """Report a failed Mesh Cleanup on both channels: the console and the popup."""
        self.cleanup_console_report(f"{mode} — FAILED", [f"scope: {scope}", str(error)])
        self.sb.message_box(f"<hl>Mesh Cleanup failed</hl><br>{error}")

    # ------------------------------------------------------------------ tb001  Delete History (Maya)
    def tb001_init(self, widget):
        """Initialize Delete History: construction history is Maya's (the
        ``.ui`` tags the button ``requires="maya"``)."""
        menu = widget.option_box.menu
        scope = menu.add(
            "QComboBox",
            setObjectName="cmb_del_scope",
            setToolTip=f"Which objects to delete history on:\n{self._SCOPE_TOOLTIP}",
        )
        for label, data in self._SCOPES:
            scope.addItem(label, data)
        # The narrowest scope by default: history deletion is destructive, and a
        # scene-wide default would silently widen the wipe for a user with a selection.
        scope.setCurrentText("Selected")
        menu.add(
            "QCheckBox",
            setText="Delete Unused Nodes",
            setObjectName="chk019",
            setChecked=True,
            setToolTip="Delete unused shading nodes and orphaned empty groups.\n"
            "Scene-wide (Maya's own MLdeleteUnused cannot be scoped) — but an\n"
            "empty transform that anything is connected to is left alone.",
        )
        menu.add(
            "QCheckBox",
            setText="Delete Deformers",
            setObjectName="chk020",
            setToolTip="Delete the deformers too (a full Delete History); off, the "
            "deformer stack stays (Delete Non-Deformer History).",
        )
        menu.add(
            "QCheckBox",
            setText="Optimize Scene",
            setObjectName="chk030",
            setToolTip="Also run Optimize Scene Size: remove unused scene nodes.",
        )

    def tb001(self, widget):
        """Delete History: on the scope's objects, plus the option box's scene cleanups."""
        menu = widget.option_box.menu
        deformers = menu.chk020.isChecked()
        done = self.tk.NodeUtils.delete_history_in_scope(
            menu.cmb_del_scope.currentData() or "selected",
            preserve_deformers=not deformers,
            delete_unused=menu.chk019.isChecked(),
            optimize_scene=menu.chk030.isChecked(),
        )
        if done:
            self.sb.message_box(
                "<hl>Delete history</hl>"
                if deformers
                else "<hl>Delete non-deformer history</hl>"
            )
        else:
            # The scene-wide cleanups may still have run: only the scoped
            # history deletion had nothing to do.
            self.sb.message_box("<hl>Delete history</hl>: no objects in scope.")

    # ------------------------------------------------------------------ tb005  Optimize (Blender)
    def tb005_init(self, widget):
        """Initialize Optimize: Blender's purge of unused data-blocks (the ``.ui``
        tags the button ``requires="blender"``; Maya's Delete History carries
        Delete Unused Nodes and Optimize Scene)."""
        menu = widget.option_box.menu
        menu.setTitle("Optimize")
        menu.add(
            "QCheckBox",
            setText="Recursive",
            setObjectName="chk_purge_recursive",
            setChecked=True,
            setToolTip="Also purge the data-blocks only the purged ones used "
            "(whole chains of unused data in one pass).",
        )
        menu.add(
            "QCheckBox",
            setText="Include Linked Data",
            setObjectName="chk_purge_linked",
            setChecked=True,
            setToolTip="Also purge unused data-blocks linked from libraries, "
            "not just local ones.",
        )

    def tb005(self, widget):
        """Optimize: purge the data-blocks nothing uses."""
        menu = widget.option_box.menu
        removed = self.tk.CoreUtils.purge_unused_data(
            recursive=menu.chk_purge_recursive.isChecked(),
            linked=menu.chk_purge_linked.isChecked(),
        )
        self.sb.logger.log_raw(f"# Optimize: purged {removed} unused data-block(s).")
        self.sb.message_box(
            f"<hl>Optimize</hl><br>Purged <hl>{removed}</hl> unused data-block(s)."
        )

    # ------------------------------------------------------------------ tb002  Delete
    def tb002(self, widget):
        """Delete: the selected components, or the selected objects whole."""
        try:
            self.tk.EditUtils.delete_selected()
        except RuntimeError as error:  # the host refused (leaving a mode, a poll)
            self.sb.message_box(str(error))

    # ------------------------------------------------------------------ tb004  Lock / Unlock
    def tb004_init(self, widget):
        """Initialize Lock / Unlock: the combo names both states, and its text is
        the button's."""
        action = widget.option_box.menu.add(
            "QComboBox",
            setObjectName="cmb_lock",
            setToolTip="Lock or unlock.\n"
            "Maya: the selected nodes, or every node when nothing is selected.\n"
            "Blender: Lock makes the selected objects unselectable; Unlock clears "
            "it on every object (a locked object cannot be selected).",
        )
        action.addItems(["Unlock", "Lock"])
        action.setCurrentText("Unlock")
        action.currentTextChanged.connect(widget.setText)
        widget.setText(action.currentText())

    def tb004(self, widget):
        """Lock / Unlock: protect objects from accidental edits."""
        lock = widget.option_box.menu.cmb_lock.currentText() == "Lock"
        changed = self.tk.NodeUtils.lock_nodes(None, lock=lock)
        if not changed:
            self.sb.message_box(
                "Select the object(s) to lock." if lock else "Nothing to unlock."
            )
            return
        verb = "Locked" if lock else "Unlocked"
        self.sb.message_box(f"<hl>{verb}</hl> {len(changed)} object(s).")

    # ------------------------------------------------------------------ list000  Create
    def list000_init(self, widget):
        """Initialize Create: the host's primitives by category, then its controls."""
        widget.fixed_item_height = 18
        widget.apply_preset(
            "expand_left" if widget.ui.has_tags("submenu") else "hover_menu"
        )
        root = widget.add("Create")
        categories = dict(self.tk.Primitives.get_primitive_types())
        shapes = set(self.tk.Controls.shapes())
        categories["Control"] = [
            shape.replace("_", " ").title()
            for shape in self._CONTROL_SHAPES
            if shape in shapes
        ]
        for category, items in categories.items():
            if items:
                root.sublist.add(category).sublist.add(items)

    @Slots.Signals("on_item_interacted")
    def list000(self, item):
        """Create the picked primitive, helper, light or control; a category row
        only expands."""
        if getattr(item, "sublist", None) and item.sublist.get_items():
            return
        text = item.item_text()
        category = item.parent_item_text() or ""
        try:
            if category == "Control":
                self.tk.Controls.create(
                    text.lower().replace(" ", "_"),
                    name=text.replace(" ", ""),
                    select=True,
                )
            else:
                self.tk.Primitives.create(category, text)
        except (RuntimeError, ValueError) as error:
            self.sb.message_box(f"Error creating {category} {text}: {error}")

    # ------------------------------------------------------------------ list001  Convert
    def list001_init(self, widget):
        """Initialize Convert: the host's conversions."""
        widget.fixed_item_height = 18
        widget.apply_preset(
            "expand_down" if widget.ui.has_tags("submenu") else "hover_menu"
        )
        root = widget.add("Convert")
        root.sublist.setMinimumWidth(180)
        root.sublist.add(list(self.tk.EditUtils.get_conversion_types()))

    @Slots.Signals("on_item_interacted")
    def list001(self, item):
        """Convert the selection: the picked conversion."""
        if getattr(item, "sublist", None) and item.sublist.get_items():
            return
        text = item.item_text()
        if text not in self.tk.EditUtils.get_conversion_types():
            return
        try:
            result = self.tk.EditUtils.convert_objects(None, text)
        except (RuntimeError, ValueError) as error:
            self.sb.message_box(f"Convert '{text}' failed: {error}")
            return
        if result == []:
            self.sb.message_box("Convert requires a selection.")

    # ------------------------------------------------------------------ cmb000  Transfer
    def cmb000_init(self, widget):
        """Initialize Transfer: the host's transfers."""
        widget.add(list(self.tk.Components.get_transfer_types()), header="Transfer:")

    def cmb000(self, index, widget):
        """Transfer: from the source (Maya: the first selected; Blender: the
        active object) to the other selected objects."""
        if index < 0:  # header / reset emission
            return
        label = widget.items[index]
        try:
            result = self.tk.Components.transfer(None, label)
        except ValueError as error:  # the selection does not fit
            self.sb.message_box(f"<b>{label}</b>: {error}")
            return
        except RuntimeError as error:  # the host refused
            self.sb.message_box(f"<b>{label}</b> failed.<br>{error}")
            return
        if result is None:  # a window or tool the user finishes
            tip = self.tk.Components.get_transfer_types().get(label, "")
            self.sb.message_box(f"<b>{label}</b><br>{tip}")
        elif not result:
            self.sb.message_box(
                f"<b>{label}</b> needs a source and at least one target: select "
                "the source first (Blender: make it active), then the target(s)."
            )
        else:
            self._report_transfer(label, result)

    def _report_transfer(self, label, objects):
        """Console: the source and targets; popup: a one-line summary."""
        source, *targets = [self.tk.CoreUtils.leaf_name(o) for o in objects]
        self.sb.logger.log_raw(
            f"# Transfer '{label}': source=<{source}> target(s)={targets}"
        )
        plural = "" if len(targets) == 1 else "s"
        self.sb.message_box(
            f"<b>Transferred {label}</b><br><hl>{source}</hl> → "
            f"{len(targets)} target{plural}"
        )


# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
