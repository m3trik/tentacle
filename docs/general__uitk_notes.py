# Tentacle Documentation


# ======================================================================
"EXAMPLES:"
# ======================================================================


# decorators:
@Slots.hideMain  # Hides the stacked widget main window.
@Slots.progress  # Displays a progress bar. (currently disabled)
@undo  # A decorator to allow undoing an executed function in one chunk.


#add widgets to menu|ctx_menu:
ctx.add('QRadioButton', setText='Current Material', setObjectName='chk007', setChecked=True, setToolTip='Re-Assign the current stored material.')
ctx.add('QCheckBox', setText='Current Material', setObjectName='chk010', setChecked=True, setToolTip='Use the current material, <br>else use the current viewport selection to get a material.')
ctx.add('QDoubleSpinBox', setPrefix='Width: ', setObjectName='s000', set_limits='0.00-100 step.05', setValue=0.25, set_height=20, setToolTip='Bevel Width.')
ctx.add(self.sb.Label, setText='Open in Editor', setObjectName='lbl000', setToolTip='Open material in editor.')
ctx.add('QPushButton', setObjectName='b002', setText='Delete All', setToolTip='Delete all autosave files.') #delete all
ctx.add('QSpinBox', setPrefix='Interval: ', setObjectName='s001', set_limits='1-60 step1', setValue=interval, set_height=20, setToolTip='The autosave interval in minutes.') #autosave interval

#add items to a custom combobox:
cmb.addItems_(zip(self.get_recent_files(timestamp=True), self.get_recent_files(timestamp=False)), "Recent Files", clear=True) #add item|data


# creating additional connections for those widgets:
cmb.beforePopupShown.connect(self.cmb001) #refresh comboBox contents before showing it's popup.
cmb.returnPressed.connect(lambda: self.lbl001(setEditable=False))
cmb.returnPressed.connect(lambda m=ctx.lastActiveChild: getattr(self, m(name=1))()) #connect to the last pressed child widget's corresponding method after return pressed. ie. self.lbl000 if cmb.lbl000 was clicked last.
cmb.currentIndexChanged.connect(self.lbl005) #select current set on index change.
s000.valueChanged.connect(lambda v: rt.autosave.setmxsprop('NumberOfFiles', v))
chk013.toggled.connect(lambda state: ctx.s006.setEnabled(True if state else False))
chk015.stateChanged.connect(lambda state: self.toggle_widgets(ctx, setDisabled='t000-1,s001,chk005-11') if state
    else self.toggle_widgets(ctx, setEnabled='t000-1,s001,chk005-11')) #disable non-relevant options.

#setText on state change.
chk004.stateChanged.connect(lambda state: chk004.setText('Repair' if state else 'Select Only')) #set button text to reflect current state.
chk026.stateChanged.connect(lambda state: chk026.setText('Stack Similar: '+str(state)))

#set multiple connections using the Slots.connect method.
self.sb.connect_multi('chk006-9', 'toggled', self.chk006_9, ctx)
self.sb.connect_multi((ctx.chk012,ctx.chk013,ctx.chk014), 'toggled',
    [lambda state: self.rigging_ui.tb004.setText('Lock Attributes'
        if any((ctx.chk012.isChecked(),ctx.chk013.isChecked(),ctx.chk014.isChecked())) else 'Unlock Attributes'),
    lambda state: self.rigging_submenu_ui.tb004.setText('Lock Transforms'
        if any((ctx.chk012.isChecked(),ctx.chk013.isChecked(),ctx.chk014.isChecked())) else 'Unlock Attributes')])


# call a method from another class.
self.sb.file.slots.b005() #get method 'b005' from the 'file' module.


# comboBox standard:
def cmb000(self, *args, **kwargs):
    """Editors"""
    cmb = self.edit_ui.cmb000

    if index > 0:
        text = cmb.items[index]
        if text == "Cleanup":
            pm.mel.CleanupPolygonOptions()
        if text == "Transfer: Attribute Values":
            pm.mel.TransferAttributeValuesOptions()
            # mel.eval('performTransferAttributes 1;') #Transfer Attributes Options
        if text == "Transfer: Shading Sets":
            pm.mel.performTransferShadingSets(1)
        cmb.setCurrentIndex(0)


# comboBox w/ctx_menu
def cmb002(self, *args, **kwargs):
    """Material list

    Parameters:
            index (int): parameter on activated, currentIndexChanged, and highlighted signals.
    """
    cmb = self.materials_ui.cmb002

    sceneMaterials = ctx.chk000.isChecked()
    idMapMaterials = ctx.chk001.isChecked()
    favoriteMaterials = ctx.chk002.isChecked()

    cmb.addItems_(list_, clear=True)


# comboBox w/menu:
def cmb006(self, *args, **kwargs):
    """Currently Selected Objects"""
    cmb = self.selection_ui.cmb006

    cmb.clear()
    items = [str(i) for i in pm.ls(sl=1, flatten=1)]
    widgets = [
        cmb.option_menu.add("QCheckBox", setText=t, setChecked=1) for t in items[:50]
    ]  # selection list is capped with a slice at 50 elements.


def cmb002(self, *args, **kwargs):
    """Recent Autosave"""
    cmb = self.file_ui.cmb002

    items = cmb.addItems_(
        self.get_recent_autosave(appendDatetime=True), "Recent Autosave", clear=True
    )

    if index > 0:
        file = Slots.fileTimeStamp(cmb.items[index], detach=True)[
            0
        ]  # cmb.items[index].split('\\')[-1]
        rt.loadMaxFile(file)
        cmb.setCurrentIndex(0)


# -------------------------------------------------------------------------------------------------------------------
