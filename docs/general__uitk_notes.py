# Tentacle Documentation


# ======================================================================
"EXAMPLE:"


# ======================================================================
class MyProject:
    ...


class MyProjectSlots(MyProject):
    def __init__(self):
        # Slot classes are given the `switchboard` function when they are initialized.
        self.sb = self.switchboard()
        # Access your UI using it filename.
        self.ui = self.sb.my_project
        print(self.ui)

        # Call a method from another class.
        self.sb.your_other_ui.slots.b005()

    def tb000_init(self, widget):
        """ """
        # Add widgets to menu:
        widget.menu.add(
            "QPushButton",
            setObjectName="b000",
            setText="Delete All",
            setToolTip="Pushbutton example",
        )
        widget.menu.add(
            "QCheckBox",
            setText="Current Material",
            setObjectName="chk000",
            setChecked=True,
            setToolTip="Checkbox example",
        )
        widget.menu.add(
            "QDoubleSpinBox",
            setPrefix="Width: ",
            setObjectName="s000",
            set_limits=[0, 100, 0.05, 2],
            setValue=0.25,
            set_height=20,
            setToolTip="Spinbox example",
        )
        widget.menu.add(
            self.sb.Label,
            setText="Open in Editor",
            setObjectName="lbl000",
            setToolTip="Custom label example",
        )

        # Set multiple connections using the Slots.connect method.
        self.sb.connect_multi(widget.menu, "chk006-9", "toggled", self.chk006_9)

    def tb002_init(self, widget):
        """Toggle UV Display Options"""
        widget.menu.mode = "popup"
        widget.menu.position = "bottom"
        widget.menu.setTitle("DISPLAY OPTIONS")

        panel = mtk.get_panel(scriptType="polyTexturePlacementPanel")
        checkered_state = pm.textureWindow(panel, q=True, displayCheckered=True)
        borders_state = True if pm.polyOptions(q=True, displayMapBorder=True) else False
        distortion_state = pm.textureWindow(panel, q=True, displayDistortion=True)

        values = [
            ("chk014", "Checkered", checkered_state),
            ("chk015", "Borders", borders_state),
            ("chk016", "Distortion", distortion_state),
        ]
        [
            widget.menu.add(
                self.sb.CheckBox, setObjectName=chk, setText=typ, setChecked=state
            )
            for chk, typ, state in values
        ]

        widget.menu.chk014.toggled.connect(
            lambda state: pm.textureWindow(panel, edit=True, displayCheckered=state)
        )
        widget.menu.chk015.toggled.connect(
            lambda state: pm.polyOptions(displayMapBorder=state)
        )
        widget.menu.chk016.toggled.connect(
            lambda state: pm.textureWindow(panel, edit=True, displayDistortion=state)
        )

    # ComboBox slot example:
    def cmb000_init(self, widget):
        """Initialize the Combo Box"""
        # Optional: Clear the combo box of any previous items.
        widget.clear()

        # Optional: Call this method each time the combo box is shown.
        widget.refresh = True

        # Your items to add. Can be list of strings, or dict with data.
        items = {"Item A": 1, "Item B": 2, "Item C": 3}

        widget.add(items, header="Combo Box")

    def cmb000(self, index, widget):
        """Combo Box Slot"""
        if index > 0:
            print("Item Data:", widget.currentData())
            widget.setCurrentIndex(0)


# -------------------------------------------------------------------------------------------------------------------
