# !/usr/bin/python
# coding=utf-8
try:
    import pymel.core as pm
except ImportError as error:
    print(__file__, error)
import mayatk as mtk
from tentacle.slots.maya import SlotsMaya


class Crease(SlotsMaya):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.ui = self.sb.crease
        self.submenu = self.sb.crease_submenu

    def tb000_init(self, widget):
        """ """
        widget.menu.setTitle("Crease")
        widget.menu.add(
            "QSpinBox",
            setPrefix="Amount: ",
            setObjectName="s003",
            set_limits=[0, 10],
            setValue=10,
            setToolTip="Sets the amount of creasing to apply to the selected edges. Range from 0 (no crease) to 10 (maximum crease).",
        )
        widget.menu.add(
            "QCheckBox",
            setText="Set Smoothing Angle",
            setObjectName="chk000",
            setToolTip="Enable this to set a custom smoothing angle for the edges. When checked, you can specify the angle in the adjacent spin box.",
        )
        widget.menu.add(
            "QSpinBox",
            setPrefix="Angle: ",
            setObjectName="s004",
            set_limits=[0, 180],
            setValue=30,
            setDisabled=True,
            setToolTip="Sets the smoothing angle for the edges. Range from 0 degrees (hard edge) to 180 degrees (soft edge). Only active if 'Set Smoothing Angle' is checked.",
        )

        widget.menu.chk000.toggled.connect(widget.menu.s004.setEnabled)
        #  Suffix the widget text with the current crease value.
        widget.setText(f"Crease {widget.menu.s003.value()}")
        # Update the widget text when the spinbox value changes.
        widget.menu.s003.valueChanged.connect(
            lambda value: widget.setText(f"Crease {value}")
        )

    @mtk.undo
    def tb000(self, widget):
        """Crease"""
        crease_amount = widget.menu.s003.value()
        smoothing_angle = widget.menu.s004.value()

        self.crease_edges(amount=crease_amount, angle=smoothing_angle)

    @mtk.undo
    def b002(self, widget):
        """Transfer Crease Edges"""
        try:
            source, *targets = pm.ls(orderedSelection=True, objectsOnly=True)
            self.transfer_creased_edges(source, targets)
        except ValueError:
            self.sb.message_box(
                "<hl>Incorrect object selection.</hl><br>Please select at least one source and one target object."
            )

    @staticmethod
    def crease_edges(edges=None, amount=None, angle=None):
        """Adjust properties of the given edges with optional crease and edge softening/hardening.

        Parameters:
            edges (str/obj/list/None): List of edges or None. If None, uses current selection.
            amount (float/None): Value of the crease to apply, or None to skip.
            angle (int/None): Angle for softening (180) or hardening (0) the edges, or None to skip.
        """
        # If edges are not provided, determine the selection context
        if edges is None:
            if pm.selectMode(q=True, object=True):
                # Object mode: Get all edges of the selected objects
                selected_objects = pm.ls(sl=True, o=True)
                edges = pm.polyListComponentConversion(selected_objects, toEdge=True)
            else:
                # Edge selection mode: Use the current edge selection
                edges = pm.ls(sl=True, fl=True)

        # Apply crease if specified
        if amount is not None:
            pm.polyCrease(edges, value=amount, vertexValue=amount)

        # Soften/harden edges if edge_angle is specified
        if angle is not None:
            pm.polySoftEdge(edges, angle=angle)

    @staticmethod
    def get_creased_edges(edges):
        """Return any creased edges from a list of edges.

        Parameters:
            edges (str/obj/list): The edges to query.

        Returns:
            list: edges.
        """
        creased_edges = [
            e
            for e in pm.ls(edges, flatten=1)
            if pm.polyCrease(e, query=True, value=True)[0] > 0
        ]
        return creased_edges

    @staticmethod
    def transfer_creased_edges(frm, to):
        """Transfers creased edges from the 'frm' object to the 'to' objects.

        Parameters:
            frm (str/obj/list): The name(s) of the source object(s).
            to (str/obj/list): The name(s) of the target object(s).
        """
        # Convert frm and to into lists of PyNode objects
        source = pm.ls(frm, objectsOnly=True)
        targets = pm.ls(to, objectsOnly=True)

        # Ensure there is at least one source and one target object
        if not all(source, targets):
            raise ValueError("Both source and target objects must exist.")

        # Retrieve creased edges from the source
        creased_edges = pm.polyCrease(source[0], query=True, value=True)

        # Loop through each target object
        for target in targets:
            # Apply crease values to corresponding edges in the target object
            for edge_id, crease_value in enumerate(creased_edges):
                if crease_value > 0:  # Apply only to creased edges
                    pm.polyCrease(f"{target}.e[{edge_id}]", value=crease_value)


# --------------------------------------------------------------------------------------------

# module name
# print(__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
