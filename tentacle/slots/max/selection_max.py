# !/usr/bin/python
# coding=utf-8
from tentacle.slots.max import *
from tentacle.slots.selection import Selection



class Selection_max(Selection, Slots_max):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)

		cmb = self.sb.selection.draggable_header.ctxMenu.cmb000
		items = ['Selection Set Editor']
		cmb.addItems_(items, 'Selection Editors:')

		cmb = self.sb.selection.cmb002
		items = ['Geometry', 'Shapes', 'Lights', 'Cameras', 'Helpers', 'Space Warps', 'Particle Systems', 'Bone Objects']
		cmb.addItems_(items, 'Select by Type:')

		cmb = self.sb.selection.cmb003
		items = ['Vertex', 'Edge', 'Border', 'Face', 'Element']
		cmb.addItems_(items, 'Convert To:')

		cmb = self.sb.selection.cmb005
		items = ['Angle', 'Border', 'Edge Loop', 'Edge Ring', 'Shell', 'UV Edge Loop']
		cmb.addItems_(items, 'Off')


	@property
	def currentSelection(self):
		'''Gets the currently selected objects or object components.

		:Return:
			(array) current selection as a maxscript array.
		'''
		sel = rt.selection
		if not sel:
			return 'Error: Nothing Selected.'

		level = rt.subObjectLevel
		if level in (0, None): #objs
			s = [i for i in sel]
		elif level==1: #verts
			s = Slots_max.getComponents(sel[0], 'vertices', selection=True)
		elif level==2: #edges
			s = Slots_max.getComponents(sel[0], 'edges', selection=True)
		elif level==3: #borders
			s = rt.getBorderSelection(sel[0])
		elif level==4: #faces
			s = Slots_max.getComponents(sel[0], 'faces', selection=True)

		return rt.array(*s) #unpack list s and convert to an array.


	def txt001(self):
		'''Select By Name
		'''
		searchStr = str(self.sb.selection.txt001.text()) #asterisk denotes startswith*, *endswith, *contains* 
		if searchStr:
			selection = rt.select(searchStr)


	def lbl000(self):
		'''Selection Sets: Create New
		'''
		cmb = self.sb.selection.cmb001
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
		cmb = self.sb.selection.cmb001
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
		cmb = self.sb.selection.cmb001
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
		cmb = self.sb.selection.cmb001
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


	def chk004(self, state=None):
		'''Ignore Backfacing (Camera Based Selection)
		'''
		for obj in rt.selection:
			if self.selection_submenu_ui.chk004.isChecked():
				sel.ignoreBackfacing = True
				self.messageBox('Camera-based selection <hl>On</hl>.', messageType='Result')
			else:
				sel.ignoreBackfacing = False
				self.messageBox('Camera-based selection <hl>Off</hl>.', messageType='Result')


	def chk008(self, state=None):
		'''Toggle Soft Selection
		'''
		if self.selection_submenu_ui.chk008.isChecked():
			pm.softSelect(edit=1, softSelectEnabled=True)
			self.messageBox('Soft Select <hl>On</hl>.', messageType='Result')
		else:
			pm.softSelect(edit=1, softSelectEnabled=False)
			self.messageBox('Soft Select <hl>Off</hl>.', messageType='Result')


	def cmb000(self, index=-1):
		'''Editors
		'''
		cmb = self.sb.selection.draggable_header.ctxMenu.cmb000

		if index>0:
			text = cmb.items[index]
			if text=='Selection Set Editor':
				maxEval('macros.run "Edit" "namedSelSets"')
			cmb.setCurrentIndex(0)


	def cmb001(self, index=-1):
		'''Selection Sets
		'''
		cmb = self.sb.selection.cmb001

		sets_ = self.getSelectionSets(rt.geometry)
		cmb.addItems_([s for s in sets_], clear=True)


	def cmb002(self, index=-1):
		'''Select All Of Type
		'''
		cmb = self.sb.selection.cmb002

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
		cmb = self.sb.selection.cmb003

		if index>0:
			text = cmb.items[index]
			for obj in rt.selection:
				for i in cmb.items:
					if index==cmb.items.index(i):
						obj.convertSelection('CurrentLevel', i) #Convert current selection to index of string i
						# rt.setSelectionLevel(obj, i) #Change component mode to i
						rt.subObjectLevel = cmb.items.index(i) #the needed component level corresponds to the item's index.
			cmb.setCurrentIndex(0)


	def cmb005(self, index=-1):
		'''Selection Contraints
		'''
		cmb = self.sb.selection.cmb005

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
		cmb = self.sb.selection.draggable_header.ctxMenu.cmb006

		cmb.clear()
		items = [str(i) for i in rt.selection]
		widgets = [cmb.menu_.add('QCheckBox', setText=t, setChecked=1) for t in items[:50]] #selection list is capped with a slice at 50 elements.

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
		tb = self.sb.selection.tb000

		edgeRing = tb.ctxMenu.chk000.isChecked()
		edgeLoop = tb.ctxMenu.chk001.isChecked()
		pathAlongLoop = tb.ctxMenu.chk009.isChecked()
		shortestPath = tb.ctxMenu.chk002.isChecked()
		borderEdges = tb.ctxMenu.chk010.isChecked()
		step = tb.ctxMenu.s003.value()


		if edgeRing: # rt.macros.run('PolyTools', 'Ring')
			obj = rt.selection[0]
			self.selectRing(obj)

		elif edgeLoop: #rt.macros.run('PolyTools', 'Loop')
			obj = rt.selection[0]
			self.selectLoop(obj)

		elif pathAlongLoop:
			pm.select(self.getPathAlongLoop(selection))

		elif shortestPath:
			pm.select(self.getShortestPath(selection))

		elif borderEdges:
			pm.select(self.getBorderComponents(selection, returnCompType='edges'))


	def tb001(self, state=None):
		'''Select Similar
		'''
		tb = self.sb.selection.tb001

		tolerance = str(tb.ctxMenu.s000.value()) #string value because mel.eval is sending a command string
		
		level = rt.subObjectLevel
		if level is 0: #object
			maxEval('actionMan.executeAction 0 "40099"') #Selection: Select Similar
		else:
			print ('# Error: No support for sub-object level selections. #')


	def tb002(self, state=None):
		'''Select Island: Select Polygon Face Island
		'''
		tb = self.sb.selection.tb002

		rangeX = float(tb.ctxMenu.s002.value())
		rangeY = float(tb.ctxMenu.s004.value())
		rangeZ = float(tb.ctxMenu.s005.value())

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
		tb = self.sb.selection.tb003

		angleLow = tb.ctxMenu.s006.value()
		angleHigh = tb.ctxMenu.s007.value()

		objects = pm.ls(sl=1, objectsOnly=1)
		edges = Slots_max.getEdgesByNormalAngle(objects, lowAngle=angleLow, highAngle=angleHigh)
		rt.select(edges)


	def setSelectionStyle(self, ctx):
		'''Set the selection style context.

		:Parameters:
			ctx (str) = Selection style context. valid: 'marquee', 'circular', 'fence', 'lasso', 'paint'.
		'''
		if ctx=='marquee':
			maxEval('actionMan.executeAction 0 "59232"') #Rectangular select region
		elif ctx=='circular':
			maxEval('actionMan.executeAction 0 "59233"') #Circular select region
		elif ctx=='fence':
			maxEval('actionMan.executeAction 0 "59234"') #Fence select region
		elif ctx=='lasso':
			maxEval('actionMan.executeAction 0 "59235"') #Lasso select region
		elif ctx=='paint':
			maxEval('actionMan.executeAction 0 "59236"') #Paint select region


	def generateUniqueSetName(self):
		'''Generate a generic name based on the object's name.

		<objectName>_Set<int>
		'''
		num = tk.cycle(list(range(99)), 'selectionSetNum')
		name = '{0}_Set{1}'.format(rt.selection[0].name, num) #ie. pCube1_Set0
		return name


	def creatNewSelectionSet(self, name=None):
		'''Selection Sets: Create a new selection set.

		:Parameters:
			name (str) = The desired name of the new set.
		'''
		if rt.isValidObj(name): # obj!=rt.undefined
			self.messageBox('Set with name <hl>{}</hl> already exists.'.format(name))
			return

		else: #create set
			sel = self.currentSelection
			if sel:
				if not name:
					name = self.generateUniqueSetName()

				try: #object level set.
					rt.selectionSets[name] = sel #create a standard object set.
				except IndexError: #sub-object level set.
					set_array = self.getSetArray(rt.selection[0], rt.subObjectLevel) #ie. rt.selection[0].faces
					set_array[name] = sel #create a sub-object level set for the selected currently selected components.
			else:
				self.messageBox('Nothing selected.')
				return


	def modifySet(self, name):
		'''Selection Sets: Modify Current by renaming or changing the set members.

		:Parameters:
			name (str) = Name of an existing selection set.
		'''
		sel = self.currentSelection
		if sel:
			newName = self.sb.selection.cmb001.currentText()
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
			self.messageBox('Nothing selected.')
			return


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
		sets = self.getSelectionSets(objects)

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


	def getSelectionSets(self, objects=[], includeEmptySets=True):
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
				_sets = self.selectionSets(obj, level)
				for setName, set_ in _sets.items():
					set_array = self.getSetArray(obj, level)
					sets[str(setName)] = [set_, obj, level, set_array]

		return sets


	def getSetArray(self, obj=None, index=0):
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


	def selectionSets(self, obj=None, level=None):
		'''Gets any existing selection sets for the given object.

		:Parameters:
			obj (obj) = The object to get sets for. If no object is given, any empty sets will be returned.
			level (int) = The sub-object level. Valid values are: 0(obj), 1(vertices), 2(edges), 3(borders), 4(faces)

		:Return:
			(dict) {'set name':<set>}
		'''
		if level is None: #if level isn't given:
			level = rt.subObjectLevel #use the current object level.

		set_array = self.getSetArray(obj, level)

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


	def selectLoop(self, obj):
		'''Select a component loop from two or more selected adjacent components (or a single edge).

		:Parameters:
			obj (obj) = An Editable polygon object.

		ex. obj = rt.selection[0]
			selectLoop(obj)
		'''
		level = rt.subObjectLevel
		if level is 1: #vertex
			obj.convertselection('Vertex',  'Edge', requireAll=True)
			obj.SelectEdgeLoop()
			obj.convertselection('Edge', 'Vertex')

		elif level is 2: #edge
			obj.SelectEdgeLoop()

		elif level is 4: #face
			obj.convertselection('Face', 'Edge', requireAll=True)
			obj.SelectEdgeRing()
			obj.convertselection('Edge', 'Face')

		rt.redrawViews()


	def selectRing(self, obj):
		'''Select a component ring from two or more selected adjacent components (or a single edge).

		:Parameters:
			obj (obj) = An Editable polygon object.

		ex. obj = rt.selection[0]
			selectRing(obj)
		'''
		level = rt.subObjectLevel
		if level is 1: #vertex
			obj.convertselection('Vertex',  'Edge', requireAll=True)
			obj.SelectEdgeRing()
			obj.convertselection('Edge', 'Vertex')

		elif level is 2: #edge
			obj.SelectEdgeRing()

		elif level is 4: #face
			obj.convertselection('Face', 'Edge', requireAll=True)
			obj.SelectEdgeLoop()
			obj.convertselection('Edge', 'Face')

		rt.redrawViews()









#module name
print (__name__)
# -----------------------------------------------
# Notes
# -----------------------------------------------