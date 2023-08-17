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
