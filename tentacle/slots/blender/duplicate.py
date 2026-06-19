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
        for o in instances:
            o.select_set(True)
        bpy.context.view_layer.objects.active = instances[0]

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
