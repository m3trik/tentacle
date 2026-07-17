# !/usr/bin/python
# coding=utf-8
import maya.cmds as cmds
import maya.mel as mel
import mayatk as mtk
from uitk import Signals
from uitk.switchboard import Cancelable
from tentacle.slots._mesh_cleanup import (
    cleanup_popup_html,
    cleanup_console_report,
    report_cleanup_failure,
)
from tentacle.slots.maya._slots_maya import SlotsMaya


class Edit(SlotsMaya):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.ui = self.sb.loaded_ui.edit
        self.submenu = self.sb.loaded_ui.edit_submenu

    def header_init(self, widget):
        """Initialize header menu"""
        widget.menu.add(
            "QPushButton",
            setText="Channels",
            setObjectName="b_channels",
            setToolTip="Open the Channels UI.",
        )
        widget.menu.add(
            "QPushButton",
            setText="Cut On Axis",
            setObjectName="b000",
            setToolTip="Cut selected objects on axis.",
        )

    def tb000_init(self, widget):
        """Initialize Mesh Cleanup"""
        widget.option_box.menu.add("Separator", setTitle="General")
        # Scope (cmb_scope) replaces the old "All Geometry" checkbox: which meshes to act on. Items
        # are identical to the Blender panel (shared QSettings namespace + parity sweep both key off
        # objectName); the data values drive _cleanup_pool below.
        cmb = widget.option_box.menu.add(
            "QComboBox",
            setObjectName="cmb_scope",
            setToolTip="Which meshes Mesh Cleanup acts on:\n"
            "• Selected: only the current selection.\n"
            "• Visible: every visible mesh in the scene.\n"
            "• All Geometry: every mesh in the scene.",
        )
        for label, data in [("Selected", "selected"), ("Visible", "visible"), ("All Geometry", "all")]:
            cmb.addItem(label, data)
        # Mode (cmb_mode) replaces the old "Repair" checkbox: same two states, now self-labeling.
        cmb = widget.option_box.menu.add(
            "QComboBox",
            setObjectName="cmb_mode",
            setToolTip="What Mesh Cleanup does with the matches:\n"
            "• Select (diagnose): just select the problem geometry so you can inspect it.\n"
            "• Repair (fix): fix the geometry in place.",
        )
        for label, data in [("Select (diagnose)", "select"), ("Repair (fix)", "repair")]:
            cmb.addItem(label, data)
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Delete History",
            setObjectName="chk026",
            setChecked=True,
            setToolTip="Bake non-deformer history before executing the cleanup operation.",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Merge vertices",
            setObjectName="chk024",
            setChecked=False,
            setToolTip="Merge overlapping vertices on the object(s) before executing the clean command.",
        )
        widget.option_box.menu.add("Separator", setTitle="Topology")
        widget.option_box.menu.add(
            "QCheckBox",
            setText="N-Gons",
            setObjectName="chk002",
            setChecked=True,
            setToolTip="Find N-gons.",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Non-Manifold Geometry",
            setObjectName="chk017",
            setChecked=True,
            setToolTip="Check for nonmanifold polys.",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Quads",
            setObjectName="chk010",
            setToolTip="Check for quad sided polys.",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Concave",
            setObjectName="chk011",
            setToolTip="Check for concave polys.",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Non-Planar",
            setObjectName="chk003",
            setToolTip="Check for non-planar polys.",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Holed",
            setObjectName="chk012",
            setToolTip="Check for holed polys.",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Lamina",
            setObjectName="chk018",
            setChecked=True,
            setToolTip="Check for lamina polys.",
        )
        widget.option_box.menu.add("Separator", setTitle="UVs")
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Shared UV's",
            setObjectName="chk016",
            setToolTip="Unshare uvs that are shared across vertices.",
        )
        widget.option_box.menu.add("Separator", setTitle="Tolerances")
        # widget.option_box.menu.add('QCheckBox', setText='Invalid Components', setObjectName='chk019', setToolTip='Check for invalid components.')
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Zero Face Area",
            setObjectName="chk013",
            setChecked=True,
            setToolTip="Check for 0 area faces.",
        )
        widget.option_box.menu.add(
            "QDoubleSpinBox",
            setPrefix="Face Area Tolerance:   ",
            setObjectName="s006",
            set_limits=[0, 10, 0.00001, 6],
            setValue=0.000010,
            setToolTip="Tolerance for face areas.",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Zero Length Edges",
            setObjectName="chk014",
            setChecked=True,
            setToolTip="Check for 0 length edges.",
        )
        widget.option_box.menu.add(
            "QDoubleSpinBox",
            setPrefix="Edge Length Tolerance: ",
            setObjectName="s007",
            set_limits=[0, 10, 0.00001, 6],
            setValue=0.000010,
            setToolTip="Tolerance for edge length.",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Zero UV Face Area",
            setObjectName="chk015",
            setToolTip="Check for 0 uv face area.",
        )
        widget.option_box.menu.add(
            "QDoubleSpinBox",
            setPrefix="UV Face Area Tolerance:",
            setObjectName="s008",
            setDisabled=True,
            set_limits=[0, 10, 0.00001, 6],
            setValue=0.000010,
            setToolTip="Tolerance for uv face areas.",
        )
        widget.option_box.menu.add("Separator", setTitle="Overlapping")
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Overlapping Faces",
            setObjectName="chk025",
            setToolTip="Find any overlapping duplicate faces. (can be very slow on dense objects)",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Overlapping Duplicate Objects",
            setObjectName="chk022",
            setToolTip="Find any duplicate overlapping geometry at the object level.",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Omit Selected Objects",
            setObjectName="chk023",
            setDisabled=True,
            setToolTip="Overlapping Duplicate Objects: Search for duplicates of any selected objects while omitting the initially selected objects.",
        )
        widget.option_box.menu.chk013.toggled.connect(
            lambda state: widget.option_box.menu.s006.setEnabled(
                True if state else False
            )
        )
        widget.option_box.menu.chk014.toggled.connect(
            lambda state: widget.option_box.menu.s007.setEnabled(
                True if state else False
            )
        )
        widget.option_box.menu.chk015.toggled.connect(
            lambda state: widget.option_box.menu.s008.setEnabled(
                True if state else False
            )
        )
        widget.option_box.menu.chk022.stateChanged.connect(
            lambda state: (
                self.sb.toggle_multi(
                    widget.menu,
                    setDisabled="chk002-3,cmb_scope,chk010-21,chk024,s006-8",
                    setEnabled="chk023",
                )
                if state
                else self.sb.toggle_multi(
                    widget.menu,
                    setEnabled="chk002-3,cmb_scope,chk010-21,s006-8",
                    setDisabled="chk023",
                )
            )
        )  # disable non-relevant options.

    @staticmethod
    def _cleanup_pool(scope):
        """Transform(s) for the Mesh Cleanup ``scope``: 'selected' -> the current selection;
        'visible' -> every visible mesh; 'all' -> every mesh in the scene. Non-selected scopes
        resolve mesh shapes (skipping intermediates) back to their transforms — what
        ``clean_geometry`` / ``polyEvaluate`` operate on."""
        if scope == "selected":
            return cmds.ls(sl=1, transforms=1) or []
        kwargs = {"type": "mesh"}
        if scope == "visible":
            kwargs["visible"] = True
        shapes = [
            s
            for s in (cmds.ls(**kwargs) or [])
            if not cmds.getAttr(f"{s}.intermediateObject")
        ]
        transforms = cmds.listRelatives(shapes, parent=True, fullPath=True) or []
        return list(dict.fromkeys(transforms))  # de-dupe, preserve order

    @staticmethod
    def _poly_counts(objects):
        """``(total verts, total faces)`` across ``objects`` via ``polyEvaluate`` — before/after
        feedback for the Repair path. Guarded: ``polyEvaluate`` returns a non-int string for an
        empty / incompatible selection, so anything unexpected reports 0."""

        def _count(**kw):
            try:
                v = cmds.polyEvaluate(objects, **kw)
            except (RuntimeError, ValueError):
                return 0
            return v if isinstance(v, int) else 0

        return _count(vertex=True), _count(face=True)

    def _cleanup_failed(self, scope, mode_label, exc):
        """Report a Mesh Cleanup failure through both feedback channels (console + popup)."""
        report_cleanup_failure(self.sb.message_box, scope, mode_label, exc)

    @Cancelable(120)
    def tb000(self, widget):
        """Mesh Cleanup — Repair (fix) or, in Select mode, select the matched problem geometry.

        Two-channel feedback (see ``tentacle.slots._mesh_cleanup``): a minimal HTML popup summary
        plus a detailed console breakdown. Every underlying pass (duplicate search, merge,
        polyCleanup) is guarded so an error surfaces as a message box, not a traceback."""
        m = widget.option_box.menu
        scope = m.cmb_scope.currentData() or "selected"
        repair = m.cmb_mode.currentData() == "repair"
        mode_label = "Repair" if repair else "Select"

        objects = self._cleanup_pool(scope)

        # Object-level duplicates are a distinct domain — handle and return.
        if m.chk022.isChecked():
            try:
                duplicates = mtk.get_overlapping_duplicates(
                    retain_given_objects=m.chk023.isChecked(), select=True, verbose=True
                )
            except (RuntimeError, ValueError) as exc:
                self._cleanup_failed(scope, mode_label, exc)
                return
            n = len(duplicates)
            verb = "deleted" if repair else "selected"
            if duplicates:
                cmds.delete(duplicates) if repair else cmds.select(duplicates)
            cleanup_console_report(
                f"{mode_label} · Overlapping Duplicate Objects",
                [f"scope: {scope}", f"{n} overlapping duplicate object(s) ({verb})"],
            )
            self.sb.message_box(cleanup_popup_html(
                f"<hl>Mesh Cleanup — {mode_label}</hl>",
                [(n, f"overlapping duplicate objects {verb}")],
            ))
            return

        if not objects:
            self.sb.message_box(
                f"<hl>Mesh Cleanup — {mode_label}</hl><br>"
                f"No mesh found for scope '<hl>{scope}</hl>'.<br>Select a mesh or change Scope."
            )
            return

        # Overlapping faces: Repair deletes them; Select unions them into the diagnostic selection
        # after the polyCleanup pass below. Detection is non-destructive either way.
        overlapping = []
        if m.chk025.isChecked():
            try:
                overlapping = mtk.get_overlapping_faces(objects) or []
            except (RuntimeError, ValueError) as exc:
                self._cleanup_failed(scope, mode_label, exc)
                return
            if repair and overlapping:
                cmds.delete(overlapping)
        overlap_n = len(overlapping)

        # Merge vertices is a repair step (it edits geometry) — skip it in the non-destructive
        # Select mode rather than mutating the mesh the user only asked to diagnose.
        if repair and m.chk024.isChecked():
            try:
                mtk.merge_vertices(objects, tolerance=0.0001)
            except (RuntimeError, ValueError) as exc:
                self._cleanup_failed(scope, mode_label, exc)
                return

        before_v, before_f = self._poly_counts(objects) if repair else (0, 0)
        try:
            selected = mtk.Diagnostics.clean_geometry(
                objects,
                repair=repair,
                quads=int(m.chk010.isChecked()),
                nsided=int(m.chk002.isChecked()),
                concave=int(m.chk011.isChecked()),
                holed=int(m.chk012.isChecked()),
                nonplanar=int(m.chk003.isChecked()),
                zeroGeom=int(m.chk013.isChecked()),
                zeroGeomTol=m.s006.value(),
                zeroEdge=int(m.chk014.isChecked()),
                zeroEdgeTol=m.s007.value(),
                zeroMap=int(m.chk015.isChecked()),
                zeroMapTol=m.s008.value(),
                sharedUVs=int(m.chk016.isChecked()),
                nonmanifold=int(m.chk017.isChecked()),
                bakePartialHistory=m.chk026.isChecked(),
            )
        except (ValueError, RuntimeError) as exc:
            self._cleanup_failed(scope, mode_label, exc)
            return

        if repair:
            after_v, after_f = self._poly_counts(objects)
            removed_v, removed_f = before_v - after_v, before_f - after_f
            cleanup_console_report(
                "Repair",
                [
                    f"scope: {scope} · {len(objects)} object(s)",
                    f"verts: {before_v} -> {after_v} (removed {removed_v})",
                    f"faces: {before_f} -> {after_f} (removed {removed_f})",
                    *([f"overlapping faces deleted: {overlap_n}"] if m.chk025.isChecked() else []),
                ],
            )
            self.sb.message_box(cleanup_popup_html(
                f"<hl>Mesh Cleanup — Repair</hl> · <hl>{len(objects)}</hl> object(s)",
                [
                    (removed_v, "verts removed"),
                    (removed_f, "faces removed"),
                    (overlap_n, "overlapping faces deleted"),
                ],
            ))
            return

        # Select mode — clean_geometry now leaves the matched components selected and returns them;
        # union the overlapping faces back in so both diagnostics stay visible.
        if overlapping:
            cmds.select(overlapping, add=1)
        n_selected = len(selected or [])
        cleanup_console_report(
            "Select",
            [
                f"scope: {scope} · {len(objects)} object(s)",
                f"problem components selected: {n_selected}",
                *([f"overlapping faces: {overlap_n}"] if m.chk025.isChecked() else []),
            ],
        )
        self.sb.message_box(cleanup_popup_html(
            "<hl>Mesh Cleanup — Select</hl>",
            [(n_selected, "problem components"), (overlap_n, "overlapping faces")],
        ))

    def tb001_init(self, widget):
        """Initialize Delete History"""
        widget.option_box.menu.add(
            "QCheckBox",
            setText="For All Objects",
            setObjectName="chk031",
            setChecked=True,
            setToolTip="Delete history on All objects or just those selected.",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Delete Unused Nodes",
            setObjectName="chk019",
            setChecked=True,
            setToolTip="Delete unused nodes.",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Delete Deformers",
            setObjectName="chk020",
            setToolTip="Delete deformers.",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Optimize Scene",
            setObjectName="chk030",
            setToolTip="Remove unused scene objects.",
        )

    def tb001(self, widget):
        """Delete History"""
        unused_nodes, deformers, optimize = map(
            lambda chk: chk.isChecked(),
            (
                widget.option_box.menu.chk019,
                widget.option_box.menu.chk020,
                widget.option_box.menu.chk030,
            ),
        )

        # Use cmds for bulk queries (avoids PyMEL object wrapping overhead)
        sel = cmds.ls(sl=True, objectsOnly=True, long=True)
        if sel:
            objects = sel
            # Batch-extract non-intermediate shapes from all selected at once
            shapes = set(
                cmds.listRelatives(sel, shapes=True, fullPath=True, noIntermediate=True)
                or []
            )
        else:
            # All non-intermediate mesh shapes in scene
            all_meshes = cmds.ls(typ="mesh", long=True) or []
            intermediates = set(cmds.ls(intermediateObjects=True, long=True) or [])
            shapes = set(all_meshes) - intermediates
            objects = list(shapes)

        result_msg = None

        # Suspend viewport refresh for the duration of the cleanup
        cmds.refresh(suspend=True)
        try:
            if unused_nodes:
                mel.eval("MLdeleteUnused")
                # Fast empty-group deletion via DAG path parsing
                # A "group" is an exact-type transform with no shape children.
                # An "empty group" is a group with no DAG children at all.
                # allPaths=True enumerates every DAG path of instanced nodes;
                # without it, instance siblings look like empty groups and get deleted.
                all_dag = cmds.ls(dag=True, long=True, allPaths=True) or []
                exact_transforms = set(
                    cmds.ls(dag=True, exactType="transform", long=True, allPaths=True) or []
                )
                shape_parents = {
                    s.rsplit("|", 1)[0]
                    for s in (
                        cmds.ls(dag=True, shapes=True, long=True, allPaths=True) or []
                    )
                }
                dag_parents = {p.rsplit("|", 1)[0] for p in all_dag if "|" in p} - {""}
                groups = exact_transforms - shape_parents
                empty_groups = [g for g in groups if g not in dag_parents]
                if empty_groups:
                    # Re-validate existence (MLdeleteUnused may have removed some)
                    existing = cmds.ls(empty_groups, long=True) or []
                    if existing:
                        cmds.delete(existing)

            if deformers:
                if objects:
                    cmds.delete(objects, constructionHistory=True)
                result_msg = "<hl>Delete history</hl>"
            else:
                if shapes:
                    try:
                        cmds.bakePartialHistory(list(shapes), prePostDeformers=True)
                        result_msg = "<hl>Delete non-deformer history</hl>"
                    except RuntimeError as error:
                        print(f"Bake Partial History Failed: {error}")

            if optimize:
                mel.eval("OptimizeScene")
        finally:
            cmds.refresh(suspend=False)
            cmds.refresh(force=True)

        if result_msg:
            self.sb.message_box(result_msg)

    def tb002(self, widget):
        """Delete Selected"""
        mtk.delete_selected()

    def tb004_init(self, widget):
        """Init Lock/Unlock Nodes"""
        # Lock vs Unlock is a two-valued choice, not a modifier — a combobox names both
        # states (its item text drives the button label); extend with e.g. "Toggle" later.
        action = widget.option_box.menu.add(
            "QComboBox",
            setObjectName="cmb_lock",
            setToolTip="Whether the button locks or unlocks the affected nodes.",
        )
        action.addItems(["Unlock Nodes", "Lock Nodes"])
        action.setCurrentText("Unlock Nodes")  # preserve prior default (checkbox on = unlock)
        action.currentTextChanged.connect(widget.setText)
        widget.setText(action.currentText())

    @mtk.undoable
    def tb004(self, widget):
        """Node Locking"""
        unlock = widget.option_box.menu.cmb_lock.currentText() == "Unlock Nodes"

        selection = cmds.ls(sl=True) or []
        # If not selection use all nodes
        nodes = selection if selection else (cmds.ls() or [])
        for node in nodes:
            cmds.lockNode(node, lock=not unlock)

    def b_channels(self):
        """Channels: open the Channels panel."""
        self.sb.handlers.marking_menu.show("channels")

    def b000(self):
        """Cut On Axis: open the Cut On Axis tool (slice objects along an axis plane)."""
        self.sb.handlers.marking_menu.show("cut_on_axis")

    # --- Create Expandable List -----------------------------------------

    _CURVE_COMMANDS = {
        "Ep Curve Tool": "EPCurveToolOptions;",
        "CV Curve Tool": "CVCurveToolOptions;",
        "Bezier Curve Tool": "CreateBezierCurveToolOptions;",
        "Pencil Curve Tool": "PencilCurveToolOptions;",
        "2 Point Circular Arc": "TwoPointArcToolOptions;",
        "3 Point Circular Arc": "ThreePointArcToolOptions;",
    }

    _HELPER_COMMANDS = {
        "Null Group": lambda: cmds.group(empty=True, name="null"),
        "Locator": lambda: cmds.spaceLocator(p=[0, 0, 0]),
        "Set": lambda: cmds.sets(name="set1"),
    }

    def list000_init(self, widget):
        """Initialize Create Primitives list."""
        widget.fixed_item_height = 18
        widget.apply_preset("expand_left")

        root = widget.add("Create")

        primitives = {
            "Polygon": [
                "Cube",
                "Sphere",
                "Cylinder",
                "Plane",
                "Circle",
                "Cone",
                "Pyramid",
                "Torus",
                "Helix",
                "Tube",
                "GeoSphere",
                "Platonic Solids",
                "Text",
            ],
            "NURBS": [
                "Cube",
                "Sphere",
                "Cylinder",
                "Cone",
                "Plane",
                "Torus",
                "Circle",
                "Square",
            ],
            "Curve": list(self._CURVE_COMMANDS),
            "Helper": list(self._HELPER_COMMANDS),
            "Light": [
                "Ambient",
                "Directional",
                "Point",
                "Spot",
                "Area",
                "Volume",
            ],
            "Control": [
                "Diamond",
                "Arrow",
                "Two Way Arrow",
                "Four Way Arrow",
                "Chevron",
                "Target",
                "Box",
                "Beveled Cube",
                "Ball",
                "Torus",
                "Helix",
                "Geosphere",
                "Pyramid",
                "Star",
            ],
        }

        for category, types in primitives.items():
            w = root.sublist.add(category)
            w.sublist.add(types)

    @Signals("on_item_interacted")
    def list000(self, item):
        """Create Primitive"""
        if getattr(item, "sublist", None) and item.sublist.get_items():
            return

        text = item.item_text()
        parent_text = item.parent_item_text() or ""

        if parent_text == "Control":
            control_map = {
                "Diamond": ("diamond", {}),
                "Arrow": ("arrow", {}),
                "Two Way Arrow": ("two_way_arrow", {}),
                "Four Way Arrow": ("four_way_arrow", {}),
                "Chevron": ("chevron", {}),
                "Target": ("target", {}),
                "Box": ("box", {}),
                "Beveled Cube": ("beveled_cube", {}),
                "Ball": ("ball", {}),
                "Torus": ("torus", {}),
                "Helix": ("helix", {}),
                "Geosphere": ("geosphere", {}),
                "Pyramid": ("pyramid", {}),
                "Star": ("star", {}),
            }
            if text in control_map:
                preset, kwargs = control_map[text]
                ctrl = mtk.Controls.create(preset, name=text.replace(" ", ""), **kwargs)
                cmds.select(ctrl)
        elif parent_text == "Curve":
            cmd = self._CURVE_COMMANDS.get(text)
            if cmd:
                try:
                    mel.eval(cmd)
                except Exception as e:
                    self.sb.message_box(f"Error creating curve '{text}': {e}")
        elif parent_text == "Helper":
            fn = self._HELPER_COMMANDS.get(text)
            if fn:
                try:
                    fn()
                except Exception as e:
                    self.sb.message_box(f"Error creating helper '{text}': {e}")
        else:
            try:
                mtk.Primitives.create_default_primitive(parent_text, text)
                cmds.selectMode(object=True)
            except Exception as e:
                self.sb.message_box(f"Error creating {parent_text} {text}: {e}")

    # --- Convert Expandable List ----------------------------------------

    _CONVERT_COMMANDS = {
        "NURBS to Polygons": "performnurbsToPoly 0;",
        "NURBS to Subdiv": "performSubdivCreate 0;",
        "Polygons to Subdiv": "performSubdivCreate 0;",
        "Smooth Mesh Preview to Polygons": "performSmoothMeshPreviewToPolygon;",
        "Polygon Edges to Curve": "polyToCurve -form 2 -degree 3 -conformToSmoothMeshPreview 1;",
        "Type to Curves": "convertTypeCapsToCurves;",
        "Subdiv to Polygons": "performSubdivTessellate  false;",
        "Subdiv to NURBS": "performSubdToNurbs 0;",
        "NURBS Curve to Bezier": "nurbsCurveToBezier;",
        "Bezier Curve to NURBS": "bezierCurveToNurbs;",
        "Paint Effects to NURBS": "performPaintEffectsToNurbs  false;",
        "Paint Effects to Curves": "performPaintEffectsToCurve  false;",
        "Texture to Geometry": "performTextureToGeom 0;",
        "Displacement to Polygons": "displacementToPoly;",
        "Displacement to Poly w/ History": "setupAnimatedDisplacement;",
        "Fluid to Polygons": "fluidToPoly;",
        "nParticle to Polygons": "particleToPoly;",
        "Instance to Object": "convertInstanceToObject;",
        "Geometry to Bounding Box": "performGeomToBBox 0;",
    }

    def list001_init(self, widget):
        """Initialize Convert list."""
        widget.fixed_item_height = 18
        widget.apply_preset("expand_down")

        root = widget.add("Convert")
        root.sublist.setMinimumWidth(180)
        root.sublist.add(list(self._CONVERT_COMMANDS))

    @Signals("on_item_interacted")
    def list001(self, item):
        """Convert: convert the selected geometry between types (NURBS / polygon / subdiv / curve, etc.)."""
        if getattr(item, "sublist", None) and item.sublist.get_items():
            return

        text = item.item_text()
        cmd = self._CONVERT_COMMANDS.get(text)
        if cmd:
            try:
                mel.eval(cmd)
            except Exception as e:
                self.sb.message_box(f"Convert '{text}' failed: {e}")

    # --- Transfer ComboBox -----------------------------------------------

    # label -> operation spec. ``command`` is the MEL it drives; ``min``
    # is the minimum number of source+target surfaces the selection must
    # hold; ``interactive`` marks ops that open a tool/window rather than
    # transferring immediately; ``done``/``tip`` feed the user feedback.
    _TRANSFER_OPS = {
        "Maps": {
            "command": "performSurfaceSampling 1",
            "min": 0,
            "interactive": True,
            "done": "Opened Transfer Maps",
            "tip": "Add source and target surfaces in the window, then bake.",
        },
        "Attribute Values": {
            "command": "TransferAttributeValues",
            "min": 2,
            "interactive": False,
            "done": "Transferred attribute values",
            "tip": "UVs, vertex positions and colors copied source → target(s).",
        },
        "Shading Sets": {
            "command": "performTransferShadingSets 0",
            "min": 2,
            "interactive": False,
            "done": "Transferred shading sets",
            "tip": "Shader / shading-group assignments copied source → target(s).",
        },
        "Vertex Order": {
            "command": "TransferVertexOrder",
            "min": 2,
            "interactive": True,
            "done": "Vertex Order tool active",
            "tip": "Click a source vertex, then the matching target vertex.",
        },
    }

    def cmb000_init(self, widget):
        """Initialize the Transfer operations menu."""
        widget.add(list(self._TRANSFER_OPS), header="Transfer:")

    def cmb000(self, index, widget):
        """Transfer — dispatch the selected transfer operation."""
        if index < 0:  # header / reset emission
            return
        label = widget.items[index]
        op = self._TRANSFER_OPS.get(label)
        if op:
            self._run_transfer(label, op)

    @staticmethod
    def _transfer_surfaces():
        """Resolve the active selection to an ordered source/target surface list.

        Returns a de-duplicated list of transform names whose shape is a
        polygon or NURBS surface, preserving selection order so the first
        entry is the transfer *source* and the rest are *targets*.

        Components are resolved to their owning object before the
        shape→transform walk (mtk's ``list_transforms`` can't resolve a
        ``.vtx[...]`` string to its shape), so a vertex/face selection
        still counts as its surface.
        """
        objects = [
            node.split(".")[0]  # drop any component suffix
            for node in cmds.ls(sl=True, flatten=True) or []
        ]
        return mtk.NodeUtils.list_transforms(
            objects, dag=True, type="surfaceShape", noIntermediate=True
        )

    def _run_transfer(self, label, op):
        """Validate the selection, run the transfer, and report the result.

        Quick formatted feedback goes to the message box; the full
        source → target breakdown and the underlying MEL command go to
        the console.
        """
        surfaces = self._transfer_surfaces()

        if len(surfaces) < op["min"]:
            self.sb.message_box(
                f"<b>{label}</b> needs a source and at least one target surface."
                f"<br>Select the <hl>source</hl> first, then the target(s)."
                f"<br>{len(surfaces)} of {op['min']} required surface(s) selected."
            )
            return

        source = surfaces[0] if surfaces else None
        targets = surfaces[1:]

        try:
            mel.eval(op["command"])
        except Exception as e:
            self.sb.message_box(
                f"<b>{label}</b> failed running <hl>{op['command']}</hl>.<br>{e}"
            )
            return

        # Console: detailed breakdown of what ran.
        if surfaces:
            print(
                f"# Transfer '{label}': source=<{source}> "
                f"target(s)={targets or '(set in tool)'} via `{op['command']}`"
            )
        else:
            print(f"# Transfer '{label}': `{op['command']}` (no pre-selection)")

        # Message box: quick formatted summary.
        if op["interactive"]:
            summary = f"<b>{op['done']}</b><br>{op['tip']}"
        else:
            plural = "" if len(targets) == 1 else "s"
            summary = (
                f"<b>{op['done']}</b><br><hl>{source}</hl> → "
                f"{len(targets)} target{plural}"
            )
        self.sb.message_box(summary)


# --------------------------------------------------------------------------------------------

# module name
# print(__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
