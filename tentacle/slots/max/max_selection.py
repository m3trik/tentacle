# !/usr/bin/python
# coding=utf-8
import os.path

from max_init import *



class Selection(Init):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)


	def draggable_header(self, state=None):
		'''Context menu
		'''
		dh = self.selection_ui.draggable_header

		if state is 'setMenu':
			dh.contextMenu.add(self.tcl.wgts.ComboBox, setObjectName='cmb000', setToolTip='')
			dh.contextMenu.add(self.tcl.wgts.ComboBox, setObjectName='cmb004', setToolTip='Set the select tool type.')
			dh.contextMenu.add('QCheckBox', setText='Ignore Backfacing', setObjectName='chk004', setToolTip='Ignore backfacing components during selection.')
			dh.contextMenu.add('QCheckBox', setText='Soft Selection', setObjectName='chk008', setToolTip='Toggle soft selection mode.')
			dh.contextMenu.add(self.tcl.wgts.Label, setText='Grow Selection', setObjectName='lbl003', setToolTip='Grow the current selection.')
			dh.contextMenu.add(self.tcl.wgts.Label, setText='Shrink Selection', setObjectName='lbl004', setToolTip='Shrink the current selection.')
			return


	def txt001(self):
		'''Select By Name
		'''
		searchStr = str(self.selection_ui.txt001.text()) #asterisk denotes startswith*, *endswith, *contains* 
		if searchStr:
			selection = rt.select(searchStr)


	def lbl000(self):
		'''Selection Sets: Create New
		'''
		cmb = self.selection_ui.cmb001
		if not cmb.isEditable():
			cmb.addItems_('', ascending=True)
			cmb.setEditable(True)
			cmb.lineEdit().setPlaceholderText('New Set:')
		else:
			name = cmb.currentText()
			self.creatNewSelectionSet(name)
			self.cmb001() #refresh the sets comboBox
			cmb.setCurrentIndex(0)


	def lbl001(self):
		'''Selection Sets: Modify Current
		'''
		cmb = self.selection_ui.cmb001
		if not cmb.isEditable():
			name = cmb.currentText()
			self._oldSetName = name
			cmb.setEditable(True)
			cmb.lineEdit().setPlaceholderText(name)
		else:
			name = cmb.currentText()
			self.modifySet(self._oldSetName)
			cmb.setItemText(cmb.currentIndex(), name)
			# self.cmb001() #refresh the sets comboBox


	def lbl002(self):
		'''Selection Sets: Delete Current
		'''
		cmb = self.selection_ui.cmb001
		name = cmb.currentText()

		set_ = self.getSet(name)
		set_array = self.getSet(name, 'set_array')

		if set_:
			rt.deleteItem(set_array, set_)

		self.cmb001() #refresh the sets comboBox


	def lbl003(self):
		'''Grow Selection
		'''
		# expand functionalitly to grow according to selection type
		#grow line #PolytoolsSelect.Pattern7 1
		#grow loop #PolytoolsSelect.GrowLoop()
		#grow ring #PolytoolsSelect.GrowRing()
		for obj in rt.selection:
			obj.EditablePoly.GrowSelection()


	def lbl004(self):
		'''Shrink Selection
		'''
		for obj in rt.selection:
			obj.EditablePoly.ShrinkSelection()


	def lbl005(self):
		'''Selection Sets: Select Current
		'''
		cmb = self.selection_ui.cmb001
		name = cmb.currentText()

		set_ = self.getSet(name)
		obj = self.getSet(name, 'object')
		level = self.getSet(name, 'objectLevel')

		if obj:
			rt.select(obj)
			rt.subObjectLevel = level #set the appropriate object level.
		if set_:
			rt.select(set_)

		rt.redrawViews()


	def s002(self, value=None):
		'''Select Island: tolerance x
		'''
		tb = self.current_ui.tb002
		if tb.menu_.chk003.isChecked():
			text = tb.menu_.s002.value()
			tb.menu_.s004.setValue(text)
			tb.menu_.s005.setValue(text)


	def s004(self, value=None):
		'''Select Island: tolerance y
		'''
		tb = self.current_ui.tb002
		if tb.menu_.chk003.isChecked():
			text = tb.menu_.s004.value()
			tb.menu_.s002.setValue(text)
			tb.menu_.s005.setValue(text)


	def s005(self, value=None):
		'''Select Island: tolerance z
		'''
		tb = self.current_ui.tb002
		if tb.menu_.chk003.isChecked():
			text = tb.menu_.s005.value()
			tb.menu_.s002.setValue(text)
			tb.menu_.s004.setValue(text)


	def chk000(self, state=None):
		'''Select Nth: uncheck other checkboxes
		'''
		self.toggleWidgets(setUnChecked='chk001-2')


	def chk001(self, state=None):
		'''Select Nth: uncheck other checkboxes
		'''
		self.toggleWidgets(setUnChecked='chk000,chk002')


	def chk002(self, state=None):
		'''Select Nth: uncheck other checkboxes
		'''
		self.toggleWidgets(setUnChecked='chk000-1')


	@Slots.message
	def chk004(self, state=None):
		'''Ignore Backfacing (Camera Based Selection)
		'''
		for obj in rt.selection:
			if self.selection_submenu_ui.chk004.isChecked():
				sel.ignoreBackfacing = True
				return 'Camera-based selection <hl>On</hl>.'
			else:
				sel.ignoreBackfacing = False
				return 'Camera-based selection <hl>Off</hl>.'


	@Slots.message
	def chk005(self, state=None):
		'''Select Style: Marquee
		'''
		self.toggleWidgets(setChecked='chk005', setUnChecked='chk006-7')
		self.selection_ui.draggable_header.contextMenu.cmb004.setCurrentIndex(0)
		return 'Select Style: <hl>Marquee</hl>'


	@Slots.message
	def chk006(self, state=None):
		'''Select Style: Lasso
		'''
		self.toggleWidgets(setChecked='chk006', setUnChecked='chk005,chk007')
		self.selection_ui.draggable_header.contextMenu.cmb004.setCurrentIndex(3)
		return 'Select Style: <hl>Lasso</hl>'


	@Slots.message
	def chk007(self, state=None):
		'''Select Style: Paint
		'''
		self.toggleWidgets(setChecked='chk007', setUnChecked='chk005-6')
		self.selection_ui.draggable_header.contextMenu.cmb004.setCurrentIndex(4)
		return 'Select Style: <hl>Paint</hl>'


	@Slots.message
	def chk008(self, state=None):
		'''Toggle Soft Selection
		'''
		if self.selection_submenu_ui.chk008.isChecked():
			pm.softSelect(edit=1, softSelectEnabled=True)
			return 'Soft Select <hl>On</hl>.'
		else:
			pm.softSelect(edit=1, softSelectEnabled=False)
			return 'Soft Select <hl>Off</hl>.'


	def cmb000(self, index=-1):
		'''Editors
		'''
		cmb = self.selection_ui.draggable_header.contextMenu.cmb000
		
		if index is 'setMenu':
			list_ = ['Selection Set Editor']
			cmb.addItems_(list_, 'Selection Editors:')
			return

		if index>0:
			text = cmb.items[index]
			if text=='Selection Set Editor':
				maxEval('macros.run "Edit" "namedSelSets"')
			cmb.setCurrentIndex(0)


	def cmb001(self, index=-1):
		'''Selection Sets
		'''
		cmb = self.selection_ui.cmb001

		if index is 'setMenu':
			cmb.contextMenu.add(self.tcl.wgts.Label, setText='Select', setObjectName='lbl005', setToolTip='Select the current set elements.')
			cmb.contextMenu.add(self.tcl.wgts.Label, setText='New', setObjectName='lbl000', setToolTip='Create a new selection set.')
			cmb.contextMenu.add(self.tcl.wgts.Label, setText='Modify', setObjectName='lbl001', setToolTip='Modify the current set by renaming and/or changing the selection.')
			cmb.contextMenu.add(self.tcl.wgts.Label, setText='Delete', setObjectName='lbl002', setToolTip='Delete the current set.')

			cmb.returnPressed.connect(lambda m=cmb.contextMenu.lastActiveChild: getattr(self, m(name=1))()) #connect to the last pressed child widget's corresponding method after return pressed. ie. self.lbl000 if cmb.lbl000 was clicked last.
			cmb.currentIndexChanged.connect(self.lbl005) #select current set on index change.
			cmb.beforePopupShown.connect(self.cmb001) #refresh comboBox contents before showing it's popup.
			return

		sets_ = Selection.getSelectionSets(rt.geometry)
		cmb.addItems_([s for s in sets_], clear=True)


	def cmb002(self, index=-1):
		'''Select All Of Type
		'''
		cmb = self.selection_ui.cmb002
	
		if index is 'setMenu':
			list_ = ['Geometry', 'Shapes', 'Lights', 'Cameras', 'Helpers', 'Space Warps', 'Particle Systems', 'Bone Objects']
			cmb.addItems_(list_, 'Select by Type:')
			return

		if index>0:
			text = cmb.items[index]
			if text=='Geometry': #Select all Geometry
				rt.select(rt.geometry)
			elif text=='Shapes': #Select all Geometry
				rt.select(rt.shapes)
			elif text=='Lights': #Select all Geometry
				rt.select(rt.lights)
			elif text=='Cameras': #Select all Geometry
				rt.select(rt.cameras)
			elif text=='Helpers': #Select all Geometry
				rt.select(rt.helpers)
			elif text=='Space Warps': #Select all Geometry
				rt.select(rt.spacewarps)
			elif text=='Particle Systems': #Select all Geometry
				rt.select(rt.particelsystems)
			elif text=='Bone Objects': #Select all Geometry
				rt.select(rt.boneobjects)

			cmb.setCurrentIndex(0)


	def cmb003(self, index=-1):
		'''Convert To
		'''
		cmb = self.selection_ui.cmb003

		if index is 'setMenu':
			list_ = ['Vertex', 'Edge', 'Border', 'Face', 'Element']
			cmb.addItems_(list_, 'Convert To:')
			return

		if index>0:
			text = cmb.items[index]
			for obj in rt.selection:
				for i in cmb.items:
					if index==cmb.items.index(i):
						obj.convertSelection('CurrentLevel', i) #Convert current selection to index of string i
						# rt.setSelectionLevel(obj, i) #Change component mode to i
						rt.subObjectLevel = cmb.items.index(i) #the needed component level corresponds to the item's index.
			cmb.setCurrentIndex(0)


	def cmb004(self, index=-1):
		'''Select Style: Set Context
		'''
		cmb = self.selection_ui.draggable_header.contextMenu.cmb004

		if index is 'setMenu':
			list_ = ['Marquee', 'Circular', 'Fence', 'Lasso', 'Paint'] 
			cmb.addItems_(list_, 'Select Tool Style:')
			return

		if index>0:
			text = cmb.items[index]
			if text=='Marquee':
				maxEval('actionMan.executeAction 0 "59232"') #Rectangular select region
			elif text=='Circular':
				maxEval('actionMan.executeAction 0 "59233"') #Circular select region
			elif text=='Fence':
				maxEval('actionMan.executeAction 0 "59234"') #Fence select region
			elif text=='Lasso':
				maxEval('actionMan.executeAction 0 "59235"') #Lasso select region
			elif text=='Paint':
				maxEval('actionMan.executeAction 0 "59236"') #Paint select region
			cmb.setCurrentIndex(0)


	def cmb005(self, index=-1):
		'''Selection Contraints
		'''
		cmb = self.selection_ui.cmb005

		if index is 'setMenu':
			list_ = ['Off', 'Angle', 'Border', 'Edge Loop', 'Edge Ring', 'Shell', 'UV Edge Loop']
			cmb.addItems_(list_, 'Off')
			return

		if index>0:
			text = cmb.items[index]
			if text=='Angle':
				mel.eval('dR_selConstraintAngle;') #dR_DoCmd("selConstraintAngle");
			elif text=='Border':
				mel.eval('dR_selConstraintBorder;') #dR_DoCmd("selConstraintBorder");
			elif text=='Edge Loop':
				mel.eval('dR_selConstraintEdgeLoop;') #dR_DoCmd("selConstraintEdgeLoop");
			elif text=='Edge Ring':
				mel.eval('dR_selConstraintEdgeRing;') #dR_DoCmd("selConstraintEdgeRing");
			elif text=='Shell':
				mel.eval('dR_selConstraintElement;') #dR_DoCmd("selConstraintElement");
			elif text=='UV Edge Loop':
				mel.eval('dR_selConstraintUVEdgeLoop;') #dR_DoCmd("selConstraintUVEdgeLoop");
		else:
			mel.eval('dR_selConstraintOff;') #dR_DoCmd("selConstraintOff");


	def cmb006(self, index=-1):
		'''Currently Selected Objects
		'''
		cmb = self.selection_ui.draggable_header.contextMenu.cmb006

		if index is 'setMenu':
			cmb.popupStyle = 'qmenu'
			cmb.beforePopupShown.connect(self.cmb006) #refresh the comboBox contents before showing it's popup.
			cmb.setCurrentText('Current Selection')
			return

		cmb.clear()
		list_ = [str(i) for i in rt.selection]
		widgets = [cmb.menu_.add('QCheckBox', setText=t, setChecked=1) for t in list_[:50]] #selection list is capped with a slice at 50 elements.

		for w in widgets:
			try:
				w.disconnect() #disconnect all previous connections.
			except TypeError:
				pass #if no connections are present; pass
			w.toggled.connect(lambda state, widget=w: self.chkxxx(state=state, widget=widget))


	def chkxxx(self, **kwargs):
		'''Transform Constraints: Constraint CheckBoxes
		'''
		try:
			if kwargs['state']==True:
				rt.deselect(kwargs['widget'].text())
			else:
				rt.select(kwargs['widget'].text())
		except KeyError:
			pass


	def tb000(self, state=None):
		'''Select Nth
		'''
		tb = self.current_ui.tb000
		if state is 'setMenu':
			tb.menu_.add('QRadioButton', setText='Component Ring', setObjectName='chk000', setToolTip='Select component ring.')
			tb.menu_.add('QRadioButton', setText='Component Loop', setObjectName='chk001', setChecked=True, setToolTip='Select all contiguous components that form a loop with the current selection.')
			tb.menu_.add('QRadioButton', setText='Path Along Loop', setObjectName='chk009', setToolTip='The path along loop between two selected edges, vertices or UV\'s.')
			tb.menu_.add('QRadioButton', setText='Shortest Path', setObjectName='chk002', setToolTip='The shortest component path between two selected edges, vertices or UV\'s.')
			tb.menu_.add('QRadioButton', setText='Border Edges', setObjectName='chk010', setToolTip='Select the object(s) border edges.')
			tb.menu_.add('QSpinBox', setPrefix='Step: ', setObjectName='s003', setMinMax_='1-100 step1', setValue=1, setToolTip='Step Amount.')
			return

		edgeRing = tb.menu_.chk000.isChecked()
		edgeLoop = tb.menu_.chk001.isChecked()
		pathAlongLoop = tb.menu_.chk009.isChecked()
		shortestPath = tb.menu_.chk002.isChecked()
		borderEdges = tb.menu_.chk010.isChecked()
		step = tb.menu_.s003.value()


		if edgeRing: # rt.macros.run('PolyTools', 'Ring')
			obj = rt.selection[0]
			Init.selectRing(obj)

		elif edgeLoop: #rt.macros.run('PolyTools', 'Loop')
			obj = rt.selection[0]
			Init.selectLoop(obj)

		elif pathAlongLoop:
			pm.select(self.getPathAlongLoop(selection, step=step))

		elif shortestPath:
			pm.select(self.getShortestPath(selection, step=step))

		elif borderEdges:
			pm.select(self.getBorderComponents(selection, returnType='edges'))


	def tb001(self, state=None):
		'''Select Similar
		'''
		tb = self.current_ui.tb001
		if state is 'setMenu':
			tb.menu_.add('QDoubleSpinBox', setPrefix='Tolerance: ', setObjectName='s000', setMinMax_='0.0-10 step.1', setValue=0.3, setToolTip='Select similar objects or components, depending on selection mode.')
			return

		tolerance = str(tb.menu_.s000.value()) #string value because mel.eval is sending a command string
		
		level = rt.subObjectLevel
		if level is 0: #object
			maxEval('actionMan.executeAction 0 "40099"') #Selection: Select Similar
		else:
			print ('# Error: No support for sub-object level selections. #')


	def tb002(self, state=None):
		'''Select Island: Select Polygon Face Island
		'''
		tb = self.current_ui.tb002
		if state is 'setMenu':
			tb.menu_.add('QCheckBox', setText='Lock Values', setObjectName='chk003', setChecked=True, setToolTip='Keep values in sync.')
			tb.menu_.add('QDoubleSpinBox', setPrefix='x: ', setObjectName='s002', setMinMax_='0.00-1 step.01', setValue=0.01, setToolTip='Normal X range.')
			tb.menu_.add('QDoubleSpinBox', setPrefix='y: ', setObjectName='s004', setMinMax_='0.00-1 step.01', setValue=0.01, setToolTip='Normal Y range.')
			tb.menu_.add('QDoubleSpinBox', setPrefix='z: ', setObjectName='s005', setMinMax_='0.00-1 step.01', setValue=0.01, setToolTip='Normal Z range.')
			return

		rangeX = float(tb.menu_.s002.value())
		rangeY = float(tb.menu_.s004.value())
		rangeZ = float(tb.menu_.s005.value())

		curmod = rt.Modpanel.getcurrentObject()
		curmod.selectAngle = rangeX
		curmod.selectByAngle = not curmod.selectByAngle

		# $.selectAngle=rangeX
		# $.selectByAngle = on
		# sel = $.selectedfaces as bitarray #maintains current single selection. need to reselect with angle contraint active to make work.
		# $.selectByAngle = off
		# print(sel)
		# setFaceSelection sel #{}


	def tb003(self, state=None):
		'''Select Edges By Angle
		'''
		tb = tb = self.selection_ui.tb003
		if state is 'setMenu':
			tb.menu_.add('QDoubleSpinBox', setPrefix='Angle Low:  ', setObjectName='s006', setMinMax_='0.0-180 step1', setValue=50, setToolTip='Normal angle low range.')
			tb.menu_.add('QDoubleSpinBox', setPrefix='Angle High: ', setObjectName='s007', setMinMax_='0.0-180 step1', setValue=130, setToolTip='Normal angle high range.')
			return

		angleLow = tb.menu_.s006.value()
		angleHigh = tb.menu_.s007.value()

		objects = pm.ls(sl=1, objectsOnly=1)
		edges = Init.getEdgesByNormalAngle(objects, lowAngle=angleLow, highAngle=angleHigh)
		rt.select(edges)


	def generateUniqueSetName(self):
		'''Generate a generic name based on the object's name.

		<objectName>_Set<int>
		'''
		num = self.cycle(list(range(99)), 'selectionSetNum')
		name = '{0}_Set{1}'.format(rt.selection[0].name, num) #ie. pCube1_Set0
		return name


	@Slots.message
	def creatNewSelectionSet(self, name=None):
		'''Selection Sets: Create a new selection set.

		:Parameters:
			name (str) = The desired name of the new set.
		'''
		if rt.isValidObj(name): # obj!=rt.undefined
			return 'Error: Set with name <hl>{}</hl> already exists.'.format(name)

		else: #create set
			sel = self.currentSelection
			if sel:
				if not name:
					name = self.generateUniqueSetName()

				try: #object level set.
					rt.selectionSets[name] = sel #create a standard object set.
				except IndexError: #sub-object level set.
					set_array = Selection.getSetArray(rt.selection[0], rt.subObjectLevel) #ie. rt.selection[0].faces
					set_array[name] = sel #create a sub-object level set for the selected currently selected components.
			else:
				return 'Error: Nothing selected.'


	@Slots.message
	def modifySet(self, name):
		'''Selection Sets: Modify Current by renaming or changing the set members.

		:Parameters:
			name (str) = Name of an existing selection set.
		'''
		sel = self.currentSelection
		if sel:
			newName = self.selection_ui.cmb001.currentText()
			if not newName:
				newName = self.generateUniqueSetName()

			set_ = self.getSet(name)

			try: #object level set.
				set_.name = newName #rename the old set with the comboBoxes current text.
				rt.selectionSets[name] = sel #create a standard object set.
			except IndexError: #sub-object level set.
				set_array = self.getSet(name, 'set_array')
				set_array[name] = sel #create a sub-object level set for the selected currently selected components.
				# if not newName==name:
				# 	rt.deleteItem(set_array, set_) #delete the old if a new set name is given.
		else:
			return 'Error: Nothing selected.'


	def getSet(self, name, index=0, objects=[]):
		'''Get a set or set info by name.

		:Parameters:
			name (str) = Set name.
			index (str)(int) = Desired return value type. Valid values are: 0:'set'(default), 1:'object', 2:'objectLevel' 4:'set_array'.
			objects (list) = The group of objects to get the set from.

		:Return:
			depending on the given index:
			(obj) <set> <object>
			(int) <object level>
			(array) <set_array>

		ex. self.getSet(name, 'set_array') #using string 'set_array' as index value instead of int 4 for readability.
		'''
		if not objects:
			objects = rt.geometry
		sets = Selection.getSelectionSets(objects)

		try:
			if index in ('set', 0):
				value = sets[name][0]
			elif index in ('object', 1):
				value = sets[name][1]
			elif index in ('objectLevel', 2):
				value = sets[name][2]
			elif index in ('set_array', 3):
				value = sets[name][3]
		except (IndexError, KeyError):
			value = None

		return value


	@staticmethod
	def getSelectionSets(objects=[], includeEmptySets=True):
		'''Get selection sets for a group of objects in the given list.
		Returns Object and Sub-Object Level sets.

		:Parameters:
			objects (list) = The objects to get sets from. ie. rt.cameras (default is rt.geometry)

		:Return:
			(dict) {'set name':[<set>, <object>, <object level as int>, <set array>]}
		'''
		if includeEmptySets:
			objects = [i for i in objects]+[None]

		sets={}
		for level in [0,1,2,4]: #range(5) omitting 'borders' because of attribute error: <obj.borders>
			for obj in objects:
				_sets = Selection.selectionSets(obj, level)
				for setName, set_ in _sets.items():
					set_array = Selection.getSetArray(obj, level)
					sets[str(setName)] = [set_, obj, level, set_array]

		return sets


	@staticmethod
	def getSetArray(obj=None, index=0):
		'''Get the array containing a set by array type.

		:Parameters:
			obj (obj) = Parent obj of the array.
			index (int) = Array type. 

		:Return:
			(array) maxscript array object.
		'''
		type_ = {0:'', 1:'vertices', 2:'edges', 3:'borders', 4:'faces'}

		if index==0:
			_set_array = rt.selectionSets
		else:
			_set_array = getattr(obj, type_[index], None) #ie. <obj.faces>

		return _set_array


	@staticmethod
	def selectionSets(obj=None, level=None):
		'''Gets any existing selection sets for the given object.

		:Parameters:
			obj (obj) = The object to get sets for. If no object is given, any empty sets will be returned.
			level (int) = The sub-object level. Valid values are: 0(obj), 1(vertices), 2(edges), 3(borders), 4(faces)

		:Return:
			(dict) {'set name':<set>}
		'''
		if level is None: #if level isn't given:
			level = rt.subObjectLevel #use the current object level.

		set_array = Selection.getSetArray(obj, level)

		try:
			if obj is None: #empty sets
				sets = {s.name:s for s in rt.selectionSets if len(s)==0}
			elif level in (0, None):
				sets = {s.name:s for n,s in enumerate(rt.selectionSets, 1) for i in range(1, rt.getNamedSelSetItemCount(n)+1) if rt.getNamedSelSetItem(n, i)==obj}
			elif level==1: #verts
				sets = {s:set_array[s] for s in obj.vertices.selSetNames}
			elif level==2: #edges
				sets = {s:set_array[s] for s in obj.edges.selSetNames}
			elif level==3: #borders
				sets = {s:set_array[s] for s in obj.borders.selSetNames}
			elif level==4: #faces
				sets = {s:set_array[s] for s in obj.faces.selSetNames}
		except AttributeError: #skip if the obj type doesn't have an attribute of the given level: ie. object has no attribute 'selSetNames' (ex. non-editable mesh)
			sets = {}

		return sets









#module name
print(os.path.splitext(os.path.basename(__file__))[0])
# -----------------------------------------------
# Notes
# -----------------------------------------------