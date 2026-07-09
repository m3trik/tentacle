# !/usr/bin/python
# coding=utf-8
import bpy
import blendertk as btk
from tentacle.slots.blender._slots_blender import SlotsBlender


class Duplicate(SlotsBlender):
    """Blender port of the shared ``duplicate`` menu.

    Maya "instances" (transforms sharing one shape) map onto Blender **linked duplicates**
    (objects sharing one ``obj.data``), backed by ``blendertk.node_utils``. The Mirror /
    Duplicate-Linear/Radial/Grid header buttons open the Blender-owned tool panels in
    ``ui/blender_menus/`` (slots ``mirror.py`` / ``duplicate_*.py``).
    """

    def __init__(self, switchboard):
        super().__init__(switchboard)

    def _ordered_source_first(self):
        """[source, *targets] with the active object as the source — matches Blender's own
        Link-Object-Data (Ctrl+L) convention where selected objects adopt the active's data."""
        objects = self.selected_objects()
        active = bpy.context.view_layer.objects.active
        if active and active in objects:
            return [active] + [o for o in objects if o is not active]
        return objects

    def header_init(self, widget):
        widget.menu.add(
            "QPushButton", setText="Mirror", setObjectName="b000",
            setToolTip="Open the mirror window.",
        )
        widget.menu.add(
            "QPushButton", setText="Duplicate Linear", setObjectName="b006",
            setToolTip="Open the duplicate linear window.",
        )
        widget.menu.add(
            "QPushButton", setText="Duplicate Radial", setObjectName="b007",
            setToolTip="Open the duplicate radial window.",
        )
        widget.menu.add(
            "QPushButton", setText="Duplicate Grid", setObjectName="b008",
            setToolTip="Open the duplicate grid window.",
        )

    # ------------------------------------------------------------------ tb000  Convert to Instances
    def tb000_init(self, widget):
        widget.option_box.menu.add(
            "QCheckBox", setText="Center Pivot", setObjectName="chk002", setChecked=True,
            setToolTip="Center the pivot on the object(s) before instancing.",
        )
        widget.option_box.menu.add(
            "QCheckBox", setText="Freeze Transforms", setObjectName="chk000",
            setToolTip="Freeze transforms on the object(s) before instancing.",
        )
        widget.option_box.menu.add(
            "QCheckBox", setText="Delete History", setObjectName="chk001", setChecked=True,
            setToolTip="No-op in Blender (no construction history) — kept for parity with Maya.",
        )

    @btk.undoable
    def tb000(self, widget):
        """Convert to Instances (selected objects share the active object's data)."""
        m = widget.option_box.menu
        objects = self._ordered_source_first()
        if len(objects) < 2:
            self.sb.message_box(
                "<strong>Insufficient selection</strong>.<br>Requires at least two objects: "
                "an active source and one or more targets."
            )
            return
        btk.replace_with_instances(
            objects,
            freeze_transforms=m.chk000.isChecked(),
            center_pivot=m.chk002.isChecked(),
            delete_history=m.chk001.isChecked(),
        )

    # ------------------------------------------------------------------ tb001  Select Instanced
    def tb001_init(self, widget):
        widget.option_box.menu.add(
            "QCheckBox", setText="All Instanced Objects", setObjectName="chk003", setChecked=True,
            setToolTip="Select every instanced object in the scene, not just instances of the selection.",
        )

    def tb001(self, widget):
        """Select Instanced Objects"""
        if widget.option_box.menu.chk003.isChecked():
            instances = btk.get_instances(objects=None)
        else:
            selection = self.selected_objects()
            if not selection:
                self.sb.message_box(
                    "<strong>Nothing selected</strong>.<br>Select objects to find their instances, "
                    "or enable 'All Instanced Objects'."
                )
                return
            instances = btk.get_instances(selection)
        if not instances:
            self.sb.message_box("<strong>No instanced objects found</strong>.")
            return
        bpy.ops.object.select_all(action="DESELECT")
        selected = []
        for o in instances:
            try:
                o.select_set(True)
                selected.append(o)
            except RuntimeError:
                pass  # not in the active view layer (excluded collection)
        if selected:
            bpy.context.view_layer.objects.active = selected[0]

    # ------------------------------------------------------------------ tb002  Auto Instance
    def tb002_init(self, widget):
        """Initialize Auto Instance — configure option-box menu."""
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
        # internally (AutoInstancer._run) — Match Whole Hierarchies has no
        # effect while it's on, so disable it to avoid a misleading control.
        chk_separate.toggled.connect(chk_combine.setEnabled)
        chk_separate.toggled.connect(lambda checked: chk_hierarchy.setEnabled(not checked))

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

    @btk.undoable
    def tb002(self, widget):
        """Auto Instance: find and convert geometrically identical meshes
        into instances of a single prototype (scans the selection, or the
        whole scene if nothing is selected)."""
        menu = widget.option_box.menu

        created = btk.auto_instance(
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
        )

        def _alive(o):
            try:  # a removed bpy object's wrapper raises ReferenceError
                return o is not None and o.name in bpy.data.objects
            except ReferenceError:
                return False

        survivors = [o for o in created if _alive(o)]
        if survivors:
            bpy.ops.object.select_all(action="DESELECT")
            selected = []
            for o in survivors:
                try:
                    o.select_set(True)
                    selected.append(o)
                except (RuntimeError, ReferenceError):
                    pass  # not in the active view layer / removed
            if selected:
                bpy.context.view_layer.objects.active = selected[0]
            self.sb.message_box(
                f"Auto Instance: <hl>{len(survivors)}</hl> object(s) instanced or combined."
            )
        else:
            self.sb.message_box(
                "<strong>No matching geometry found</strong>.<br>"
                "No identical meshes to instance and nothing to combine."
            )

    # ------------------------------------------------------------------ b005  Uninstance
    @btk.undoable
    def b005(self):
        """Uninstance Selected Objects (make their data single-user)."""
        btk.uninstance(self.selected_objects())

    # ------------------------------------------------------------------ tool panels (blender_menus)
    def b000(self):
        """Mirror"""
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


# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
