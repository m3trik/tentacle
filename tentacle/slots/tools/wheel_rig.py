# !/usr/bin/python
# coding=utf-8
"""Wheel Rig: wheels that roll as their driver (control) moves, sized by wheel
height.

One Slots class for both hosts over the host toolkit's ``WheelRig``
(``self.tk``), which also splits the selection into the driver and its wheels
the way the host orders it (Maya: the last selected drives; Blender, which
keeps no order: the active object).
"""

from tentacle import Slots


class WheelRigSlots(Slots):
    #: The Axis combo's entries, in order (the combo saves its index): its
    #: label, the driver's travel channel and the wheel rotation it drives, in
    #: mayatk's channel names, which both hosts' ``WheelRig`` take.
    AXES = (
        ("Move X → Rotate Z", "translateX", "rotateZ"),
        ("Move Y → Rotate Y", "translateY", "rotateY"),
        ("Move Z → Rotate X", "translateZ", "rotateX"),
    )
    #: The entry the combo starts on: forward Z travel pitches on X.
    DEFAULT_AXES = 2

    def __init__(self, switchboard):
        super().__init__(switchboard)
        self.ui = self.sb.loaded_ui.wheel_rig
        self._use_world_space = False  # the header menu's Space combo

        self.ui.cmb000.clear()
        self.ui.cmb000.addItems([label for label, _, _ in self.AXES])
        self.ui.cmb000.setCurrentIndex(self.DEFAULT_AXES)

        # chk000 (Reverse) and cmb001 (Rot Axis) predate the combined Axis
        # combo and the driver's spinDirection attribute. Hidden, not deleted:
        # their objectNames are saved settings, and the .ui loader can hold a
        # deleted widget's wrapper when it re-shows the window.
        for widget in (self.ui.chk000, self.ui.cmb001):
            widget.setVisible(False)

        # The rig-name placeholder follows the selection's driver. The
        # subscription ends with the window (connect_cleanup); it is not ended
        # on close, which left a reopened panel deaf to the selection.
        mgr = self.tk.ScriptJobManager.instance()
        mgr.subscribe("SelectionChanged", self._on_selection_changed, owner=self)
        mgr.connect_cleanup(self.ui, owner=self)
        self.update_rig_name_placeholder()

        self._init_tooltips()

    def header_init(self, widget):
        """Configure header menu with mode toggle and instructions."""
        widget.menu.add("Separator", setTitle="Mode")
        # Local vs World Space is a two-valued mode, not a modifier — a combobox
        # names both states; extend with a third space here without a relayout.
        cmb_space = widget.menu.add(
            "QComboBox",
            setObjectName="cmb_space",
            setToolTip=self.sb.tooltip.fmt(
                title="Space",
                bullets=[
                    "<b>Local</b> (default) — reads the driver's own translate "
                    "channel. Simpler, and sufficient when the driver itself is "
                    "animated.",
                    "<b>World Space</b> — reads the driver's world-space "
                    "position, so movement inherited from parent transforms is "
                    "captured (Maya: a decomposeMatrix node on its "
                    "<i>worldMatrix</i>; Blender: the driver variable's World "
                    "Space).",
                ],
            ),
        )
        cmb_space.addItems(["Local", "World Space"])
        cmb_space.setCurrentText("Local")  # the prior default (checkbox off = local)
        cmb_space.currentTextChanged.connect(self._on_space_changed)

        widget.set_help_text(
            self.sb.tooltip.fmt(
                title="Wheel Rig",
                body="Drive wheel rotation from a control's linear movement. "
                "Wheel diameter (Wheel Height) and travel axis determine the "
                "rotation speed.",
                sections=[
                    (
                        "Selection order",
                        [
                            "Select one or more <b>wheel</b> objects.",
                            f"{self.sb.tooltip.kbd('Shift')}-select the <b>driver / "
                            "control</b> object last (in Blender that makes it the "
                            "<b>active</b> object, which is what Blender reads).",
                            "Click <b>Rig Rotation</b>.",
                        ],
                    ),
                    (
                        "Settings",
                        [
                            "<b>Axis</b> — which travel axis drives which rotation "
                            "axis. e.g. <i>Move Z → Rotate X</i> means forward Z "
                            "movement produces pitch on X.",
                            "<b>Wheel Height</b> — diameter used to compute rotation "
                            "speed. Use <b>Get Wheel Size</b> (its option box) to "
                            "measure it from the selected wheel's bounding box.",
                        ],
                    ),
                    (
                        "Modes",
                        [
                            "<b>Local</b> (default) — reads the driver's own "
                            "translate channel. Best when the driver itself is "
                            "animated.",
                            "<b>World Space</b> — reads the driver's world-space "
                            "position, so parent transform movement is captured. "
                            "Toggle via the header menu.",
                        ],
                    ),
                    (
                        "Driver attributes added",
                        [
                            "<b>wheelHeight</b> — animation-friendly diameter control.",
                            "<b>enableRotation</b> — on/off toggle (0..1).",
                            "<b>spinDirection</b> — flip direction (+1 / -1).",
                        ],
                    ),
                ],
                notes=[
                    "Re-running on the same driver updates its rig in place: the "
                    "rig ID stored on the driver (Maya: <i>wheelRigId</i>; "
                    "Blender: the <i>wheel_rig_id</i> custom property) is the "
                    "idempotency key, so nothing is duplicated.",
                    "Each Rig Rotation is one undo step.",
                ],
            )
        )

    def _on_space_changed(self, text: str):
        self._use_world_space = text == "World Space"

    @property
    def rig_name(self) -> str:
        """The Rig Name field's text ("" when left to the default)."""
        return self.ui.txt000.text().strip()

    def _axes(self):
        """The Axis combo's entry: ``(label, movement_axis, rotation_axis)``."""
        index = self.ui.cmb000.currentIndex()
        if not 0 <= index < len(self.AXES):
            index = self.DEFAULT_AXES
        return self.AXES[index]

    @property
    def movement_axis(self) -> str:
        """The driver's travel channel the Axis combo names (``translateZ``)."""
        return self._axes()[1]

    @property
    def rotation_axis(self) -> str:
        """The wheel rotation channel the Axis combo pairs with it (``rotateX``)."""
        return self._axes()[2]

    def set_wheel_height(self):
        """Get Wheel Size: Wheel Height from the selected wheel's bounding box,
        across the axes it turns in for the current movement axis."""
        size = self.tk.WheelRig.wheel_size(movement_axis=self.movement_axis)
        if size is None:
            self.sb.message_box("Select a single object to determine wheel height.")
            return
        self.ui.s000.setText(str(round(size, 3)))

    def _init_tooltips(self):
        """Set the polished (uitk ``fmt``) tooltips for every option and action."""
        ui = self.ui

        ui.txt000.setToolTip(
            self.sb.tooltip.fmt(
                title="Rig Name",
                body="Name of the rig, stored on the driver so a re-run updates "
                "it in place (Maya also prefixes the rig's expressions, and its "
                "World Space decomposeMatrix node, with it).",
                notes=[
                    "Empty = the driver's stored rig name, else derived from the "
                    "driver (control) name, as the placeholder shows.",
                ],
            )
        )
        ui.s000.setToolTip(
            self.sb.tooltip.fmt(
                title="Wheel Height",
                body="Wheel diameter, used to convert the driver's travel into "
                "rotation — a larger wheel turns slower over the same distance.",
                notes=[
                    "Use the <b>Get Wheel Size</b> option box to measure this "
                    "from the selected object's bounding box.",
                ],
            )
        )
        ui.cmb000.setToolTip(
            self.sb.tooltip.fmt(
                title="Movement → Rotation Axis",
                body="Which translation axis drives which rotation axis.",
                rows=[
                    ("Move X → Rotate Z", "sideways X travel rolls on Z"),
                    ("Move Y → Rotate Y", "vertical Y travel spins on Y"),
                    ("Move Z → Rotate X", "forward Z travel pitches on X (default)"),
                ],
            )
        )
        ui.chk010.setToolTip(
            self.sb.tooltip.fmt(
                title="Freeze Transforms",
                body="Freezes <b>translation</b> on the driver and wheel(s) "
                "before rigging, so travel is measured from a clean zero.",
                notes=[
                    "Rotation is preserved (needed for mirrored-wheel auto-flip).",
                ],
            )
        )
        ui.b000.setToolTip(
            self.sb.tooltip.fmt(
                title="Rig Rotation",
                body="Creates (or updates) the rotation that spins the wheel(s) "
                "from the driver's movement (Maya: an expression per wheel; "
                "Blender: a driver per wheel).",
                steps=[
                    "Select one or more <b>wheel</b> objects.",
                    "<b>Shift</b>-select the <b>driver / control</b> last "
                    "(Blender: the active object).",
                    "Press <b>Rig Rotation</b>.",
                ],
                notes=[
                    "Freeze or correctly set transforms first (or tick "
                    "<b>Freeze Transforms</b>).",
                    "Re-running on the same driver updates its rig in place — "
                    "no duplicates.",
                ],
            )
        )

    def txt000_init(self, widget):
        """Rig-name field — optional, so clearing back to auto-naming is a state."""
        widget.option_box.clear_option = True

    def s000_init(self, widget):
        """Initialize the wheel height field's option-box menu."""
        widget.option_box.menu.add(
            "QPushButton",
            setText="Get Wheel Size",
            setObjectName="b010",
            setToolTip=self.sb.tooltip.fmt(
                title="Get Wheel Size",
                body="Sets <b>Wheel Height</b> from the selected object's "
                "bounding box, based on the current movement axis.",
            ),
        )
        widget.option_box.menu.b010.clicked.connect(self.set_wheel_height)

    def _on_selection_changed(self):
        """Selection changed: re-name the rig the new selection would build."""
        self.update_rig_name_placeholder()

    def update_rig_name_placeholder(self):
        """Show, as the Rig Name placeholder, the name a rig on the selection's
        driver takes: its stored rig name, else ``<driver>_wheel_rig``."""
        name = self.tk.WheelRig.default_rig_name()
        if name:
            self.ui.txt000.setPlaceholderText(name)

    def b000(self):
        """Rig Rotation: rig the selected wheels to the selected driver, or
        update the rig the driver already carries (one undo step)."""
        try:
            wheel_height = float(self.ui.s000.text() or 1.0)
        except ValueError:
            self.sb.message_box("Wheel Height must be a number.")
            return
        try:
            self.tk.WheelRig.from_selection(
                rig_name=self.rig_name or None,
                freeze_transforms=self.ui.chk010.isChecked(),
                movement_axis=self.movement_axis,
                rotation_axis=self.rotation_axis,
                wheel_height=wheel_height,
                use_world_space=self._use_world_space,
            )
        except ValueError as error:  # the selection or a value, refused up front
            self.sb.message_box(str(error))
        except Exception as error:
            self.sb.message_box(f"Error setting up wheel rig: {error}")
