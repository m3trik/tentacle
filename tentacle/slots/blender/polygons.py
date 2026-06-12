# !/usr/bin/python
# coding=utf-8
import bpy
import blendertk as btk
from tentacle.slots.blender._slots_blender import SlotsBlender


class PolygonsSlots(SlotsBlender):
    """Blender port of the shared ``polygons`` menu.

    Per the §5 capability map almost everything is a native edit-mode operator
    (merge/inset/subdivide/bridge/bevel/poke/symmetrize/fill-holes) run on the user's
    component selection via :meth:`_edit_op`; combine/separate are object ops; boolean
    routes through ``btk.boolean_op`` (Boolean modifier). Modal Maya tools without a
    non-modal Blender analogue (interactive bridge, slide, target weld, edge flow,
    circularize, wedge, invisible faces, snap-closest) are deferred with messages.
    """

    def __init__(self, switchboard):
        super().__init__(switchboard)
        self.ui = self.sb.loaded_ui.polygons
        self.submenu = self.sb.loaded_ui.polygons_submenu

    def _edit_op(self, op, *args, **kwargs):
        """Run an edit-mode mesh operator on the user's component selection.

        Requires an active mesh already in Edit Mode (component workflows are selection-
        based — silently entering edit mode and select-all would operate on the wrong
        thing). Returns True when the op ran.
        """
        active = bpy.context.view_layer.objects.active
        if not (active and active.type == "MESH" and active.mode == "EDIT"):
            self.sb.message_box("Select components in Edit Mode first.")
            return False
        try:
            op(*args, **kwargs)
            return True
        except RuntimeError as e:
            self.sb.message_box(str(e))
            return False

    # ------------------------------------------------------------------ tb-slots
    def tb000_init(self, widget):
        widget.option_box.menu.setTitle("Merge Vertices")
        widget.option_box.menu.add(
            "QDoubleSpinBox", setPrefix="Distance: ", setObjectName="s006",
            set_limits=[0, 10, 0.0001, 4], setValue=0.0001,
            setToolTip="Vertices within this distance are merged.",
        )

    @btk.undoable
    def tb000(self, widget):
        """Merge Vertices"""
        self._edit_op(
            bpy.ops.mesh.remove_doubles,
            threshold=widget.option_box.menu.s006.value(),
        )

    @btk.undoable
    def tb002(self, widget):
        """Separate (split the mesh into loose parts)."""
        objects = [o for o in self.selected_objects() if o.type == "MESH"]
        if not objects:
            self.sb.message_box("Separate requires a mesh selection.")
            return
        active = bpy.context.view_layer.objects.active
        prior = getattr(active, "mode", "OBJECT")
        if prior != "EDIT":
            bpy.ops.object.mode_set(mode="EDIT")
        try:
            bpy.ops.mesh.separate(type="LOOSE")
        except RuntimeError as e:
            self.sb.message_box(str(e))
        finally:
            bpy.ops.object.mode_set(mode="OBJECT")

    @btk.undoable
    def tb003(self, widget):
        """Extrude (in place — move with G after)."""
        self._edit_op(bpy.ops.mesh.extrude_region)

    @btk.undoable
    def tb004(self, widget):
        """Combine Selected Meshes"""
        objects = [o for o in self.selected_objects() if o.type == "MESH"]
        if len(objects) < 2:
            self.sb.message_box("Combine requires 2+ selected meshes.")
            return
        try:
            bpy.ops.object.join()
        except RuntimeError as e:
            self.sb.message_box(str(e))

    @btk.undoable
    def tb005(self, widget):
        """Detach (separate the selected components into a new object)."""
        self._edit_op(bpy.ops.mesh.separate, type="SELECTED")

    def tb006_init(self, widget):
        widget.option_box.menu.setTitle("Inset Face Region")
        widget.option_box.menu.add(
            "QDoubleSpinBox", setPrefix="Thickness: ", setObjectName="s008",
            set_limits=[0, 100, 0.01, 3], setValue=0.1,
            setToolTip="Inset thickness.",
        )

    @btk.undoable
    def tb006(self, widget):
        """Inset Face Region"""
        self._edit_op(
            bpy.ops.mesh.inset, thickness=widget.option_box.menu.s008.value()
        )

    def tb007_init(self, widget):
        widget.option_box.menu.setTitle("Divide Facet")
        widget.option_box.menu.add(
            "QSpinBox", setPrefix="Cuts: ", setObjectName="s009",
            set_limits=[1, 10], setValue=1,
            setToolTip="Number of subdivision cuts.",
        )

    @btk.undoable
    def tb007(self, widget):
        """Divide Facet (subdivide the selected components)."""
        self._edit_op(
            bpy.ops.mesh.subdivide, number_cuts=widget.option_box.menu.s009.value()
        )

    def tb008_init(self, widget):
        widget.option_box.menu.setTitle("Boolean Operation")
        widget.option_box.menu.add(
            "QComboBox", addItems=["Difference", "Union", "Intersect"],
            setObjectName="cmb012", setToolTip="Boolean operation (active = base).",
        )

    @btk.undoable
    def tb008(self, widget):
        """Boolean Operation (active mesh = base, other selected = operands)."""
        objects = [o for o in self.selected_objects() if o.type == "MESH"]
        active = bpy.context.view_layer.objects.active
        if active in objects:  # base first (Maya's order-matters convention)
            objects = [active] + [o for o in objects if o is not active]
        if len(objects) < 2:
            self.sb.message_box("Boolean requires 2+ selected meshes (active = base).")
            return
        operation = {
            "Difference": "DIFFERENCE", "Union": "UNION", "Intersect": "INTERSECT"
        }[widget.option_box.menu.cmb012.currentText()]
        btk.boolean_op(objects, operation=operation)

    def tb009(self, widget):
        """Snap Closest Verts — not yet ported (use snap + Auto Merge)."""
        self.sb.message_box("Snap Closest Verts is not yet implemented for Blender.")

    # ------------------------------------------------------------------ b-slots (component ops)
    @btk.undoable
    def b001(self):
        """Fill Holes"""
        self._edit_op(bpy.ops.mesh.fill_holes, sides=0)

    @btk.undoable
    def b003(self):
        """Symmetrize"""
        self._edit_op(bpy.ops.mesh.symmetrize)

    @btk.undoable
    def b006(self):
        """Bridge (selected edge loops)."""
        self._edit_op(bpy.ops.mesh.bridge_edge_loops)

    @btk.undoable
    def b008(self):
        """Weld Center (merge selected at center)."""
        self._edit_op(bpy.ops.mesh.merge, type="CENTER")

    @btk.undoable
    def b009(self):
        """Collapse Component"""
        self._edit_op(bpy.ops.mesh.merge, type="COLLAPSE")

    @btk.undoable
    def b011(self):
        """Bevel"""
        self._edit_op(bpy.ops.mesh.bevel, offset=0.1)

    def b012(self):
        """Multi-Cut Tool (Knife)."""
        try:
            bpy.ops.wm.tool_set_by_id(name="builtin.knife")
        except Exception as e:
            self.sb.message_box(str(e))

    def b022(self):
        """Attach (join the selected meshes)."""
        self.tb004(None)  # tb004 carries the undoable wrap — no second push here

    @btk.undoable
    def b032(self):
        """Poke"""
        self._edit_op(bpy.ops.mesh.poke)

    def b047(self):
        """Insert Edgeloop (Loop Cut tool)."""
        try:
            bpy.ops.wm.tool_set_by_id(name="builtin.loop_cut")
        except Exception as e:
            self.sb.message_box(str(e))

    @btk.undoable
    def b051(self):
        """Offset Edgeloop"""
        self._edit_op(bpy.ops.mesh.offset_edge_loops)

    def b043(self):
        """Target Weld (toggle vertex snap + Auto Merge — Blender's equivalent workflow:
        grab a vert, snap it onto another, and they merge)."""
        ts = bpy.context.scene.tool_settings
        state = not (ts.use_snap and ts.use_mesh_automerge)
        ts.use_snap = state
        ts.use_mesh_automerge = state
        if state:
            try:
                ts.snap_elements = {"VERTEX"}
            except AttributeError:  # 4.x split: snap_elements_base/_individual
                ts.snap_elements_base = {"VERTEX"}
        self.sb.message_box(
            f"Target Weld <hl>{'enabled' if state else 'disabled'}</hl> "
            "(vertex snap + auto-merge)."
        )

    # ------------------------------------------------------------------ deferred (modal / no analogue)
    def b000(self):
        """Circularize — needs the LoopTools add-on (Circle); not ported."""
        self.sb.message_box("Circularize is not yet implemented for Blender (see LoopTools).")

    def b007(self):
        """Interactive Bridge — modal Maya tool; use Bridge on selected loops instead."""
        self.sb.message_box("Interactive Bridge is not applicable in Blender (use Bridge).")

    def b034(self):
        """Wedge — no non-modal Blender analogue (use Spin)."""
        self.sb.message_box("Wedge is not yet implemented for Blender (use Spin).")

    def b038(self):
        """Assign Invisible — Maya invisible faces have no Blender analogue."""
        self.sb.message_box("Assign Invisible is not applicable in Blender.")

    def b049(self):
        """Slide Edge — modal in Blender (GG); no persistent tool."""
        self.sb.message_box("Slide Edge is modal in Blender — press GG on an edge selection.")

    def b053(self):
        """Edit Edge Flow — needs the Edit-Flow add-on; not ported."""
        self.sb.message_box("Edit Edge Flow is not yet implemented for Blender.")


# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
