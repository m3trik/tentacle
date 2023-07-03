# Tentacle Documentation


# ======================================================================
"EXAMPLES:"
# ======================================================================


# decorators:
@undo  # A decorator to allow undoing an executed function in one chunk.
@hide_main  # Hides the stacked widget main window.

# Add widgets to menu|menu:
menu.add('QRadioButton', setText='Current Material', setObjectName='chk007', setChecked=True, setToolTip='Re-Assign the current stored material.')
menu.add('QCheckBox', setText='Current Material', setObjectName='chk010', setChecked=True, setToolTip='Use the current material, <br>else use the current viewport selection to get a material.')
menu.add('QDoubleSpinBox', setPrefix='Width: ', setObjectName='s000', set_limits=[0, 100, .05, 2], setValue=0.25, set_height=20, setToolTip='Bevel Width.')
menu.add(self.sb.Label, setText='Open in Editor', setObjectName='lbl000', setToolTip='Open material in editor.')
menu.add('QPushButton', setObjectName='b002', setText='Delete All', setToolTip='Delete all autosave files.')  # Delete all

# Set multiple connections using the Slots.connect method.
self.sb.connect_multi('chk006-9', 'toggled', self.chk006_9, menu)

# Call a method from another class.
self.sb.file.slots.b005()  # Get method 'b005' from the 'file' module.


# ComboBox slot example:
def cmb_init(self, widget):
    """Initialize the combo box"""
    items = []  # Your items to add
    widget.add(items)


def cmb(self, index, widget):
    """Combo box slot"""
    if index > 0:
        # do something
        cmb.setCurrentIndex(0)


# -------------------------------------------------------------------------------------------------------------------
