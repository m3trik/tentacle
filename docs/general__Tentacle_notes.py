# Tentacle notes



# ======================================================================
	'PROFILE:'
# ======================================================================



# ======================================================================
	'EXAMPLES:'
# ======================================================================

# decorators:
@Slots.hideMain		# Hides the stacked widget main window.
@Slots.progress		# Displays a progress bar. (currently disabled)
@Slots_maya.attr	# Launch a popup window containing the given objects attributes. A Decorator for setAttributeWindow (objAttrWindow).
@undo	# A decorator to allow undoing an executed function in one chunk.



#add widgets to menu|ctxMenu:
ctx.add('QRadioButton', setText='Current Material', setObjectName='chk007', setChecked=True, setToolTip='Re-Assign the current stored material.')
ctx.add('QCheckBox', setText='Current Material', setObjectName='chk010', setChecked=True, setToolTip='Use the current material, <br>else use the current viewport selection to get a material.')
ctx.add('QDoubleSpinBox', setPrefix='Width: ', setObjectName='s000', setMinMax_='0.00-100 step.05', setValue=0.25, setHeight_=20, setToolTip='Bevel Width.')
ctx.add(self.sb.Label, setText='Open in Editor', setObjectName='lbl000', setToolTip='Open material in editor.')
ctx.add('QPushButton', setObjectName='b002', setText='Delete All', setToolTip='Delete all autosave files.') #delete all
ctx.add('QSpinBox', setPrefix='Interval: ', setObjectName='s001', setMinMax_='1-60 step1', setValue=interval, setHeight_=20, setToolTip='The autosave interval in minutes.') #autosave interval

#add items to a custom combobox:
cmb.addItems_(zip(self.getRecentFiles(timestamp=True), self.getRecentFiles(timestamp=False)), "Recent Files", clear=True) #add item|data


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
chk004.stateChanged.connect(lambda state: chk004.setText('Repair' if state else 'Select Only')) #set button text to reflect current state.
chk026.stateChanged.connect(lambda state: chk026.setText('Stack Similar: '+str(state)))

#set multiple connections using the Slots.connect method.
self.sb.connect('chk006-9', 'toggled', self.chk006_9, ctx)
self.sb.connect((ctx.chk012,ctx.chk013,ctx.chk014), 'toggled', 
				[lambda state: self.rigging_ui.tb004.setText('Lock Attributes' 
					if any((ctx.chk012.isChecked(),ctx.chk013.isChecked(),ctx.chk014.isChecked())) else 'Unlock Attributes'), 
				lambda state: self.rigging_submenu_ui.tb004.setText('Lock Transforms' 
					if any((ctx.chk012.isChecked(),ctx.chk013.isChecked(),ctx.chk014.isChecked())) else 'Unlock Attributes')])


# call a method from another class.
self.sb.file.slots.b005() #get method 'b005' from the 'file' module.





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


# comboBox w/ctxMenu
def cmb002(self, index=-1):
		'''Material list

		:Parameters:
			index (int): parameter on activated, currentIndexChanged, and highlighted signals.
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





# -------------------------------------------------------------------------------------------------------------------









# ======================================================================
	'KNOWN BUGS AND GENERAL TO-DO'
# ======================================================================
'''

maya normals:
harden edge selection operation takes forever.

maya uv:
get/ set texel density broken.


ui:
dockable windows
create a dockable pyside output window, with text highlighting and clickable links.


the issue where some popup windows hide on key release and some do not is back.


maya:
interactive ncloth to static mesh tool
interactive generate> attach brush to curves
additional interactive pipe tools using other methods
use the 3 point align function to quickly align two objects using two selected faces, 
then click through the various vertex combinatons to get the correct alignment.


macros:
turn on transform constraints while modifier key down.


double left click always toggles between current and perspective cameras.


scene:
add invert option to naming find field combobox.


attribute windows pop up solution.  current pop up is far more annoying than useful.


create macro toolbutton where you are able to chain commands.


Treewidgets not registering click on mouse release.
# treewidgetExpandableList
# mousegrab being lost after using treewidget
# initial size incorrect (and first column not populating)
build history window instead of using tree widget.
replace other tree widget instances with popup windows.


maya macros:
'3' wireframe on shaded not working. (works after manually turning toggled)
extend 'ctl+d' to duplicate faces only when in face selection mode.
'f3' ghost selected instead of ghost other.
maya.macros: isolate selected: incorrect mod panel.
# Error: line 1: RuntimeError: file C:\Program Files\Autodesk\Maya2022\Python37\lib\site-packages\pymel\internal\pmcmds.py line 217: model panel 'outlinerPanel1' does not exist #



uv:
uv_maya:  select by type:  move to selection_maya: select by type.
pack partial box by using float values in box arg:  u3dLayout -res 4096 -scl 1 -spc 0.00390625 -box 0 1 0.5 1 (top=0 1 0.5 1,  bottom=0 1 0 0.5, topleft=0 0.5 0.5 1, topright=0.5 1 0.5 1, bottomleft=0 0.5 0 0.5, bottomright=0.5 1 0 0.5)



materials:
modify the combobox custom widget to modify text fields on double click. (and change the rename function to work this way)
separate 'assign current', 'assign new' to their own buttons.
assign random:  give option to derive mat name from mesh name.
link bitmaps script.
materials_maya: 
rename not working.


transform:
combine 'move to' and 'match scale' to 'match transforms'.
match scale of multiple objects.
get the functions for these maya commands:
	pm.mel.performMatchTransform(0)
	performMatchTranslate 0;
	performMatchRotate 0;
	performMatchScale 0;
	performMatchPivots 0;
add duplicate and move match.
add delete after move.
use new window and class.
maya_transform:  make live on submenu disables make live when first pressed.



selection:
add convert to vertices and any other commonly used component type conversion to submenu.
selection_maya:
add quick store current selection list menu.
selection_maya:
select island not working.
bonus tools: select nth (use algorithm)
add: maya selection: camera based selection
selectPref -useDepth true;


file_maya:
workspace contextmenu> 'set' project method being called twice. :(
file_maya:
create reference
pm.mel.CreateReference()
maya_file
# Error: uitk.childEvents.EventFactoryFilter.initWidgets(): Call: <bound method File.tb000 of <maya_file.File(0x1e0b2f0ca40) at 0x000001E0DB9769C8>>('setMenu') failed: 'PySide2.QtWidgets.QMainWindow' object has no attribute 'draggable_header'. #



mirror_maya:
fix mirror pivot using the method in test_004
the axis parameter is new. may help fix the issue.
add center pivot on mirrored object option and set as default.


polygons_maya:
create 'weld all' button.
target weld:  switch to vertex component selection on activation.
add segments option to bevel.
polygons_maya: (polygons_vertices_maya)
merge vertex in object mode not working.
polygons_maya: (polygons_mesh_maya)
add to mesh groupbox:
Quadrangulate;
performPolyQuadrangulate 0;
pm.polyQuad(selection, angle=30, -kgb 1 -ktb 1 -khe 0 -ws 1 -ch 1)


create_maya:
use transform_maya: 'move to' to move the objects after creation.


# animation_maya: delete all keys:
O:/Cloud/Code/_scripts/uitk\uitk\slots\maya\animation_maya.py
line 34, in b000
#     rt.deleteKeys(rt.selection)
# NameError: name 'rt' is not defined
cutKey -cl -t ":" -f ":" -at "tx" -at "ty" -at "tz" -at "rx" -at "ry" -at "rz" -at "sx" -at "sy" -at "sz" -at "v" polySurface1600;



duplicate_maya:
convert to instances needs an undo chunk.
also:  move to object center rather than object pivot.



maya_preferences:
ctx menu's commented out because of issues:
	

scene: 
naming needs clearer docstring w/example results. replace suffix is instead appending. should replace 1 occurance from right of anything in the find field, possibly only if searching for suffix.


# Traceback (most recent call last):
#   File "O:/Cloud/Code/_scripts/uitk\uitk\slots\maya\__init__.py", line 1154, in wrapper
#     self.setAttributeWindow(fn(self, *args, **kwargs))
#   File "O:/Cloud/Code/_scripts/uitk\uitk\slots\__init__.py", line 472, in wrapper
#     self.messageBox(fn(self, *args, **kwargs))
#   File "O:/Cloud/Code/_scripts/uitk\uitk\slots\maya\polygons_maya.py", line 209, in tb006
#     return pm.polyExtrudeFacet(selected_faces, keepFacesTogether=1, pvx=0, pvy=40.55638003, pvz=33.53797107, divisions=1, twist=0, taper=1, offset=offset, thickness=0, smoothingAngle=30)
#   File "C:\Program Files\Autodesk\Maya2022\Python37\lib\site-packages\pymel\internal\pmcmds.py", line 217, in polyExtrudeFacet_wrapped
#     res = new_cmd(*new_args, **new_kwargs)
# TypeError: Object 1 is invalid


# Traceback (most recent call last):
#   File "O:/Cloud/Code/_scripts/uitk\uitk\slots\maya\crease_maya.py", line 50, in tb000
#     pm.polySoftEdge (angle=0, constructionHistory=0) #Harden edge normal
#   File "C:\Program Files\Autodesk\Maya2022\Python37\lib\site-packages\pymel\core\modeling.py", line 987, in polySoftEdge
#     res = cmds.polySoftEdge(*args, **kwargs)
#   File "C:\Program Files\Autodesk\Maya2022\Python37\lib\site-packages\pymel\internal\pmcmds.py", line 217, in polySoftEdge_wrapped
#     res = new_cmd(*new_args, **new_kwargs)
# TypeError: Error retrieving default arguments


# Traceback (most recent call last):
#   File "O:/Cloud/Code/_scripts/uitk\uitk\slots\__init__.py", line 499, in wrapper
#     self.messageBox(fn(self, *args, **kwargs))
#   File "O:/Cloud/Code/_scripts/uitk\uitk\slots\maya\__init__.py", line 57, in wrapper
#     rtn = fn(*args, **kwargs)
#   File "O:/Cloud/Code/_scripts/uitk\uitk\slots\maya\maya_animation.py", line 53, in tb001
#     return Animation.invertSelectedKeyframes(time=time, relative=relative)
#   File "O:/Cloud/Code/_scripts/uitk\uitk\slots\maya\__init__.py", line 57, in wrapper
#     rtn = fn(*args, **kwargs)
# TypeError: 'staticmethod' object is not callable


# Traceback (most recent call last):
#   File "O:/Cloud/Code/_scripts/uitk\uitk\slots\maya\maya_polygons.py", line 511, in b053
#     pm.polyEditEdgeFlow(adjustEdgeFlow=1)
#   File "C:\Program Files\Autodesk\Maya2022\Python37\lib\site-packages\pymel\core\modeling.py", line 650, in polyEditEdgeFlow
#     res = cmds.polyEditEdgeFlow(*args, **kwargs)
#   File "C:\Program Files\Autodesk\Maya2022\Python37\lib\site-packages\pymel\internal\pmcmds.py", line 217, in polyEditEdgeFlow_wrapped
#     res = new_cmd(*new_args, **new_kwargs)
# TypeError: Error retrieving default arguments


# Traceback (most recent call last):
#   File "O:/Cloud/Code/_scripts/uitk\uitk\slots\maya\maya_uv.py", line 366, in tb004
#     pm.u3dUnfold(iterations=1, pack=0, borderintersection=1, triangleflip=1, mapsize=2048, roomspace=0) #pm.mel.performUnfold(0)
# AttributeError: module 'pymel.core' has no attribute 'u3dUnfold'
unfold -i 5000 -ss 0.001 -gb 0 -gmb 0.5 -pub 0 -ps  0 -oa  0 -us off pCylinder1.f[0:59];

# Traceback (most recent call last):
#   File "O:/Cloud/Code/_scripts/uitk\uitk\childEvents.py", line 236, in eventFilter
#     getattr(self, eventName)(event) #handle the event locally. #ie. self.enterEvent(event)
#   File "O:/Cloud/Code/_scripts/uitk\uitk\childEvents.py", line 348, in mouseReleaseEvent
#     ui = self.tcl.setUi(self.widget.whatsThis()) #switch the stacked layout to the given ui.
#   File "O:/Cloud/Code/_scripts/uitk\uitk\tcl.py", line 83, in setUi
#     ui = self.sb.getUi(name, setAsCurrent=True) #Get the ui of the given name, and set it as the current ui in the switchboard module, which amoung other things, sets connections.
#   File "O:/Cloud/Code/_scripts/uitk\uitk\switchboard.py", line 489, in getUi
#     self.uiName = uiName #set the property for the current ui name.
#   File "O:/Cloud/Code/_scripts/uitk\uitk\switchboard.py", line 532, in setUiName
#     index = self.getUiIndex(index) #get index using name
#   File "O:/Cloud/Code/_scripts/uitk\uitk\switchboard.py", line 673, in getUiIndex
#     return self.uiList(names=True).index(uiName)
# ValueError: 'main_lower' is not in list


# get a menu to pop up directly:
def hk_tentacle_show(profile=False, uiName='init'):
	'''Display the uitk marking menu.

	:Parameters:
		profile (bool): Prints the total running time, times each function separately, and tells you how many times each function was called.
	'''
	if 'uitk' not in globals():
		global uitk
		from tcl_maya import Instance
		uitk = Instance(key_show='key_F12')

	# if profile:
	# 	import cProfile
	# 	cProfile.run("uitk.show('init')")
	# else:
	print (uitk)
	uitk.show(uiName)
	# uitk.setUi(uiName)


# hk_tentacle_show('init')



# -------------------------------------------------------------------------------------------------------------------


