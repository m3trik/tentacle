# Tentacle notes



# ======================================================================
	'PROFILE:'
# ======================================================================



# ======================================================================
	'EXAMPLES:'
# ======================================================================

# decorators:
@Slots.sync				# Keep widgets (having the same objectName) in sync across parent and child uis. A decorator using the syncWidgets method. 'isChecked':'setChecked', 'isDisabled':'setDisabled', 'isEnabled':'setEnabled', 'value':'setValue', 'text':'setText', 'icon':'setIcon'
@Slots.message		# Pop up a message box displaying the returned str. also: self.viewPortMessage("Display Local Rotation Axes:<hl>"+str(state)+"</hl>")
									# ex. return 'Error: <hl>Nothing selected</hl>.<br>Operation requires an object or vertex selection.'
@Slots.hideMain		# Hides the stacked widget main window.
@Slots.progress		# Displays a progress bar. (currently disabled)
@Slots_maya.attr				# Launch a popup window containing the given objects attributes. A Decorator for setAttributeWindow (objAttrWindow).
@Slots_maya.undoChunk		# A decorator to place a function into Maya's undo chunk.



#add widgets to menu|contextMenu:
ctx.add('QRadioButton', setText='Current Material', setObjectName='chk007', setChecked=True, setToolTip='Re-Assign the current stored material.')
ctx.add('QCheckBox', setText='Current Material', setObjectName='chk010', setChecked=True, setToolTip='Use the current material, <br>else use the current viewport selection to get a material.')
ctx.add('QDoubleSpinBox', setPrefix='Width: ', setObjectName='s000', setMinMax_='0.00-100 step.05', setValue=0.25, setHeight_=20, setToolTip='Bevel Width.')
ctx.add(self.tcl.wgts.Label, setText='Open in Editor', setObjectName='lbl000', setToolTip='Open material in editor.')
ctx.add('QPushButton', setObjectName='b002', setText='Delete All', setToolTip='Delete all autosave files.') #delete all
ctx.add('QSpinBox', setPrefix='Interval: ', setObjectName='s001', setMinMax_='1-60 step1', setValue=interval, setHeight_=20, setToolTip='The autosave interval in minutes.') #autosave interval



# creating additional connections for those widgets:
cmb.beforePopupShown.connect(self.cmb001) #refresh comboBox contents before showing it's popup.
cmb.returnPressed.connect(lambda: self.lbl001(setEditable=False))
cmb.returnPressed.connect(lambda m=ctx.lastActiveChild: getattr(self, m(name=1))()) #connect to the last pressed child widget's corresponding method after return pressed. ie. self.lbl000 if cmb.lbl000 was clicked last.
cmb.currentIndexChanged.connect(self.lbl005) #select current set on index change.
s000.valueChanged.connect(lambda v: rt.autosave.setmxsprop('NumberOfFiles', v))
chk013.toggled.connect(lambda state: ctx.s006.setEnabled(True if state else False))
chk015.stateChanged.connect(lambda state: self.toggleWidgets(ctx, setDisabled='t000-1,s001,chk005-11') if state 
												else self.toggleWidgets(ctx, setEnabled='t000-1,s001,chk005-11')) #disable non-relevant options.

#setText on state change.
chk004.stateChanged.connect(lambda state: ctx.chk004.setText('Repair' if state else 'Select Only')) #set button text to reflect current state.
ctx.chk026.stateChanged.connect(lambda state: ctx.chk026.setText('Stack Similar: '+str(state)))

#set multiple connections using the Slots.connect_ method.
self.connect_('chk006-9', 'toggled', self.chk006_9, ctx)
self.connect_((ctx.chk012,ctx.chk013,ctx.chk014), 'toggled', 
				[lambda state: self.rigging_ui.tb004.setText('Lock Attributes' 
					if any((ctx.chk012.isChecked(),ctx.chk013.isChecked(),ctx.chk014.isChecked())) else 'Unlock Attributes'), 
				lambda state: self.rigging_submenu_ui.tb004.setText('Lock Transforms' 
					if any((ctx.chk012.isChecked(),ctx.chk013.isChecked(),ctx.chk014.isChecked())) else 'Unlock Attributes')])


# call a method from another class.
self.tcl.sb.getMethod('file', 'b005')()




# pushButton w/contextMenu:
def tb002(self, state=None):
		'''Assign Material
		'''
		tb = self.materials_ui.tb002

		selection = pm.ls(selection=1, flatten=1)
		if not selection:
			return 'Error: No renderable object is selected for assignment.'

		assignCurrent = ctx.chk007.isChecked()


@Init.attr
@Slots.message
def tb006(self, state=None):
	'''Inset Face Region
	'''
	tb = self.current_ui.tb006

	selected_faces = pm.polyEvaluate(faceComponent=1)
	if isinstance(selected_faces, str): #'Nothing counted : no polygonal object is selected.'
		return 'Error: <hl>Nothing selected</hl>.<br>Operation requires a face selection.'

	offset = float(ctx.s001.value())
	return pm.polyExtrudeFacet(selected_faces, keepFacesTogether=1, pvx=0, pvy=40.55638003, pvz=33.53797107, divisions=1, twist=0, taper=1, offset=offset, thickness=0, smoothingAngle=30)


# comboBox standard:
def cmb000(self, index=-1):
		'''Editors
		'''
		cmb = self.edit_ui.cmb000

		if index>0:
			text = cmb.items[index]
			if text=='Cleanup':
				pm.mel.CleanupPolygonOptions()
			if text=='Transfer: Attribute Values':
				pm.mel.TransferAttributeValuesOptions()
				# mel.eval('performTransferAttributes 1;') #Transfer Attributes Options
			if text=='Transfer: Shading Sets':
				pm.mel.performTransferShadingSets(1)
			cmb.setCurrentIndex(0)


# comboBox w/contextMenu
def cmb002(self, index=-1):
		'''Material list

		:Parameters:
			index (int) = parameter on activated, currentIndexChanged, and highlighted signals.
		'''
		cmb = self.materials_ui.cmb002

		sceneMaterials = ctx.chk000.isChecked()
		idMapMaterials = ctx.chk001.isChecked()
		favoriteMaterials = ctx.chk002.isChecked()

		cmb.addItems_(list_, clear=True)



#comboBox w/menu:
def cmb006(self, index=-1):
		'''Currently Selected Objects
		'''
		cmb = self.selection_ui.cmb006

		cmb.clear()
		items = [str(i) for i in pm.ls(sl=1, flatten=1)]
		widgets = [cmb.menu_.add('QCheckBox', setText=t, setChecked=1) for t in items[:50]] #selection list is capped with a slice at 50 elements.



def cmb002(self, index=-1):
		'''Recent Autosave
		'''
		cmb = self.file_ui.cmb002

		items = cmb.addItems_(self.getRecentAutosave(appendDatetime=True), "Recent Autosave", clear=True)

		if index>0:
			file = Slots.fileTimeStamp(cmb.items[index], detach=True)[0] #cmb.items[index].split('\\')[-1]
			rt.loadMaxFile(file)
			cmb.setCurrentIndex(0)



# expandable_treewidget:
def tree000(self, wItem=None, column=None):
	'''
	'''
	tree = self.current_ui.tree000

	if not any([wItem, column]): #refresh list items -----------------------------
		#command history
		recentCommandInfo = self.tcl.sb.prevCommand(docString=1, toolTip=1, as_list=1) #Get a list of any recent command names and their toolTips
		[tree.add('QLabel', 'Recent Commands', refresh=1, setText=s[0], setToolTip=s[1]) for s in recentCommandInfo]
		return

	# widget = tree.getWidget(wItem, column)
	header = tree.getHeaderFromColumn(column)
	text = tree.getWidgetText(wItem, column)
	index = tree.getIndexFromWItem(wItem, column)

	if header=='Recent Commands':
		recentCommands = self.tcl.sb.prevCommand(method=1, as_list=1) #Get a list of any recent commands
		method = recentCommands[index]
		if callable(method):
			method()

	# # if header=='':
	# #   if text=='':
	# #     pass
	# #   if text=='':
	# #     pass

# ----------------------------------------------------------------------









# ======================================================================
	'KNOWN BUGS'
# ======================================================================
'''
move slots.max methods to their corresponding sub-classes.


Treewidgets not registering click on mouse release.


ctx menu's commented out because of issues:
	maya_preferences



Slots.scene: naming needs clearer docstring w/example results. replace suffix is instead appending. should replace 1 occurance from right of anything in the find field, possibly only if searching for suffix.


# Traceback (most recent call last):
#   File "O:/Cloud/Code/_scripts/tentacle\tentacle\slots\maya\maya_polygons.py", line 511, in b053
#     pm.polyEditEdgeFlow(adjustEdgeFlow=1)
#   File "C:\Program Files\Autodesk\Maya2022\Python37\lib\site-packages\pymel\core\modeling.py", line 650, in polyEditEdgeFlow
#     res = cmds.polyEditEdgeFlow(*args, **kwargs)
#   File "C:\Program Files\Autodesk\Maya2022\Python37\lib\site-packages\pymel\internal\pmcmds.py", line 217, in polyEditEdgeFlow_wrapped
#     res = new_cmd(*new_args, **new_kwargs)
# TypeError: Error retrieving default arguments


maya_transform:  make live on submenu disables make live when first pressed.


# treewidgetExpandableList
# mousegrab being lost after using treewidget
# initial size incorrect (and first column not populating)


# Traceback (most recent call last):
#   File "O:/Cloud/Code/_scripts/tentacle\tentacle\slots\maya\maya_uv.py", line 366, in tb004
#     pm.u3dUnfold(iterations=1, pack=0, borderintersection=1, triangleflip=1, mapsize=2048, roomspace=0) #pm.mel.performUnfold(0)
# AttributeError: module 'pymel.core' has no attribute 'u3dUnfold'
unfold -i 5000 -ss 0.001 -gb 0 -gmb 0.5 -pub 0 -ps  0 -oa  0 -us off pCylinder1.f[0:59];

# Traceback (most recent call last):
#   File "O:/Cloud/Code/_scripts/tentacle\tentacle\childEvents.py", line 236, in eventFilter
#     getattr(self, eventName)(event) #handle the event locally. #ie. self.enterEvent(event)
#   File "O:/Cloud/Code/_scripts/tentacle\tentacle\childEvents.py", line 348, in mouseReleaseEvent
#     ui = self.tcl.setUi(self.widget.whatsThis()) #switch the stacked layout to the given ui.
#   File "O:/Cloud/Code/_scripts/tentacle\tentacle\tcl.py", line 83, in setUi
#     ui = self.sb.getUi(name, setAsCurrent=True) #Get the ui of the given name, and set it as the current ui in the switchboard module, which amoung other things, sets connections.
#   File "O:/Cloud/Code/_scripts/tentacle\tentacle\switchboard.py", line 489, in getUi
#     self.uiName = uiName #set the property for the current ui name.
#   File "O:/Cloud/Code/_scripts/tentacle\tentacle\switchboard.py", line 532, in setUiName
#     index = self.getUiIndex(index) #get index using name
#   File "O:/Cloud/Code/_scripts/tentacle\tentacle\switchboard.py", line 673, in getUiIndex
#     return self.uiList(names=True).index(uiName)
# ValueError: 'main_lower' is not in list


maya_file
# Error: tentacle.childEvents.EventFactoryFilter.initWidgets(): Call: <bound method File.tb000 of <maya_file.File(0x1e0b2f0ca40) at 0x000001E0DB9769C8>>('setMenu') failed: 'PySide2.QtWidgets.QMainWindow' object has no attribute 'draggable_header'. #


#maya_uv: transfer uv's
#fix transfer UV's by trying new method below:
polyTransfer -uv 1 -v 0 -ao $souceMesh $destMesh[$i];



# get a menu to pop up directly:
def hk_tentacle_show(profile=False, uiName='init'):
	'''Display the tentacle marking menu.

	:Parameters:
		profile (bool) = Prints the total running time, times each function separately, and tells you how many times each function was called.
	'''
	if 'tentacle' not in globals():
		global tentacle
		from tcl_maya import Instance
		tentacle = Instance(key_show='key_F12')

	# if profile:
	# 	import cProfile
	# 	cProfile.run("tentacle.show('init')")
	# else:
	print (tentacle)
	tentacle.show(uiName)
	# tentacle.setUi(uiName)


# hk_tentacle_show('init')



# ----------------------------------------------------------------------


