# !/usr/bin/python
# coding=utf-8
import os.path

from max_init import *



class Rigging(Init):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)


	def draggable_header(self, state=None):
		'''Context menu
		'''
		dh = self.rigging_ui.draggable_header

		if state is 'setMenu':
			dh.contextMenu.add(self.tcl.wgts.ComboBox, setObjectName='cmb000', setToolTip='')
			return


	def cmb000(self, index=-1):
		'''Editors
		'''
		cmb = self.rigging_ui.draggable_header.contextMenu.cmb000

		if index is 'setMenu':
			list_ = ['Bone Tools','Parameter Editor','Parameter Collector','Parameter Wire Dialog']
			cmb.addItems_(list_, 'Rigging Editors')
			return

		if index>0:
			text = cmb.items[index]
			if text=='Bone Tools':
				maxEval('macros.run "Animation Tools" "BoneAdjustmentTools"')
			elif text=='Parameter Editor':
				maxEval('macros.run "Customize User Interface" "Custom_Attributes"')
			elif text=='Parameter Collector':
				maxEval('macros.run "Parameter Collector" "ParamCollectorShow"')
			elif text=='Parameter Wire Dialog':
				maxEval('macros.run "Parameter Wire" "paramWire_dialog"')
			cmb.setCurrentIndex(0)


	def cmb001(self, index=-1):
		'''Create
		'''
		cmb = self.rigging_ui.cmb001

		if index is 'setMenu':
			list_ = ['Bones IK Chain','Point','Dummy','Grid','Expose Transform','Lattice','Biped']
			cmb.addItems_(list_, "Create")
			return

		if index>0:
			text = cmb.items[index]
			if text=='Bones IK Chain':
				maxEval('macros.run "Inverse Kinematics" "Bones"') #create joint tool
			elif text=='Point':
				maxEval('macros.run "Objects Helpers" "Point"') #Point pos:[46.5545,-11.1098,0] isSelected:on #locator
			elif text=='Dummy':
				maxEval('macros.run "Objects Helpers" "Dummy"')
			elif text=='Grid':
				maxEval('macros.run "Objects Helpers" "Grid"') #grid pos:[14.957,-79.0478,0] isSelected:on width:49.0621 length:51.0787
			elif text=='Expose Transform':
				maxEval('macros.run "Objects Helpers" "ExposeTM"') #ExposeTm pos:[1.12888,-35.9943,0] isSelected:on
			elif text=='Lattice':
				maxEval('modPanel.addModToSelection (Lattice ()) ui:on') #create lattice
			elif text=='macros.run "Objects Systems" "Biped"':
				maxEval('macros.run "Objects Systems" "Biped"')
			cmb.setCurrentIndex(0)


	def chk000(self, state=None):
		'''Scale Joint
		'''
		self.toggleWidgets(setUnChecked='chk001-2')
		# self.rigging_ui.tb000.menu_.s000.setValue(pm.jointDisplayScale(query=1)) #init global joint display size


	def chk001(self, state=None):
		'''Scale IK
		'''
		self.toggleWidgets(setUnChecked='chk000, chk002')
		# self.rigging_ui.s000.setValue(pm.ikHandleDisplayScale(query=1)) #init IK handle display size
		

	def chk002(self, state=None):
		'''Scale IK/FK
		'''
		self.toggleWidgets(setUnChecked='chk000-1')
		# self.rigging_ui.s000.setValue(pm.jointDisplayScale(query=1, ikfk=1)) #init IKFK display size


	def s000(self, value=None):
		'''Scale Joint/IK/FK
		'''
		value = self.rigging_ui.s000.value()

		# if self.rigging_ui.chk000.isChecked():
		# 	pm.jointDisplayScale(value) #set global joint display size
		# elif self.rigging_ui.chk001.isChecked():
		# 	pm.ikHandleDisplayScale(value) #set global IK handle display size
		# else: #self.rigging_ui.chk002.isChecked():
		# 	pm.jointDisplayScale(value, ikfk=1) #set global IKFK display size


	@Slots.message
	def tb000(self, state=None):
		'''Toggle Display Local Rotation Axes
		'''
		tb = self.current_ui.tb000
		if state is 'setMenu':
			tb.contextMenu.add('QCheckBox', setText='Joints', setObjectName='chk000', setChecked=True, setToolTip='Display Joints.')
			tb.contextMenu.add('QCheckBox', setText='IK', setObjectName='chk001', setChecked=True, setToolTip='Display IK.')
			tb.contextMenu.add('QCheckBox', setText='IK\\FK', setObjectName='chk002', setChecked=True, setToolTip='Display IK\\FK.')
			tb.contextMenu.add('QDoubleSpinBox', setPrefix='Tolerance: ', setObjectName='s000', setMinMax_='0.00-10 step.5', setValue=1.0, setToolTip='Global Display Scale for the selected type.')
			
			self.chk000() #init scale joint value
			return

		# joints = pm.ls(type="joint") #get all scene joints

		# state = pm.toggle(joints[0], query=1, localAxis=1)
		# if tb.contextMenu.isChecked():
		# 	if not state:
		# 		toggle=True
		# else:
		# 	if state:
		# 		toggle=True

		# if toggle:
		# 	pm.toggle(joints, localAxis=1) #set display off

		# return 'Display Local Rotation Axes:<hl>'+str(state)+'</hl>'


	def tb001(self, state=None):
		'''Orient Joints
		'''
		tb = self.current_ui.tb001
		if state is 'setMenu':
			tb.contextMenu.add('QCheckBox', setText='Align world', setObjectName='chk003', setToolTip='Align joints with the worlds transform.')
			return

		# orientJoint = 'xyz' #orient joints
		# if tb.contextMenu.isChecked():
		# 	orientJoint = 'none' #orient joint to world

		# pm.joint(edit=1, orientJoint=orientJoint, zeroScaleOrient=1, ch=1)


	def tb002(self, state=None):
		'''Constraint: Parent
		'''
		tb = self.current_ui.tb002
		if state is 'setMenu':
			tb.contextMenu.add('QCheckBox', setText='Template Child', setObjectName='chk004', setChecked=False, setToolTip='Template child object(s) after parenting.')		
			return

		template = tb.contextMenu.chk004.isChecked()

		objects = list(Init.bitArrayToArray(rt.selection))

		for obj in objects[:-1]:
			obj.parent = objects[-1]

			if template:
				obj.isFrozen = True


	@Slots.message
	def tb003(self, state=None):
		'''Create Locator at Selection
		'''
		tb = self.current_ui.tb003
		if state is 'setMenu':
			tb.contextMenu.add('QLineEdit', setPlaceholderText='Suffix:', setText='', setObjectName='t000', setToolTip='A string appended to the end of the created locators name.')
			tb.contextMenu.add('QCheckBox', setText='Strip Digits', setObjectName='chk005', setChecked=True, setToolTip='Strip numeric characters from the string. If the resulting name is not unique, maya will append a trailing digit.')
			tb.contextMenu.add('QLineEdit', setPlaceholderText='Strip:', setText='_GEO', setObjectName='t001', setToolTip='Strip a specific character set from the locator name. The locators name is based off of the selected objects name.')
			tb.contextMenu.add('QDoubleSpinBox', setPrefix='Scale: ', setObjectName='s001', setMinMax_='.000-1000 step1', setValue=1, setToolTip='The scale of the locator.')
			tb.contextMenu.add('QCheckBox', setText='Parent', setObjectName='chk006', setChecked=True, setToolTip='Parent to object to the locator.')
			tb.contextMenu.add('QCheckBox', setText='Freeze Transforms', setObjectName='chk010', setChecked=True, setToolTip='Freeze transforms on the locator.')
			tb.contextMenu.add('QCheckBox', setText='Bake Child Pivot', setObjectName='chk011', setChecked=True, setToolTip='Bake pivot positions on the child object.')
			tb.contextMenu.add('QCheckBox', setText='Lock Child Translate', setObjectName='chk007', setChecked=True, setToolTip='Lock the translate values of the child object.')
			tb.contextMenu.add('QCheckBox', setText='Lock Child Rotation', setObjectName='chk008', setChecked=True, setToolTip='Lock the rotation values of the child object.')
			tb.contextMenu.add('QCheckBox', setText='Lock Child Scale', setObjectName='chk009', setChecked=False, setToolTip='Lock the scale values of the child object.')
			tb.contextMenu.add('QCheckBox', setText='Remove Locators', setObjectName='chk015', setChecked=False, setToolTip='Removes the locator, and inverts the above process. (not valid with component selections)')
			
			tb.contextMenu.chk015.stateChanged.connect(lambda state: self.toggleWidgets(tb.contextMenu, setDisabled='t000-1,s001,chk005-11') if state 
															else self.toggleWidgets(tb.contextMenu, setEnabled='t000-1,s001,chk005-11')) #disable non-relevant options.
			return

		suffix = tb.contextMenu.t000.text()
		stripDigits = tb.contextMenu.chk005.isChecked()
		strip = tb.contextMenu.t001.text()
		parent = tb.contextMenu.chk006.isChecked()
		scale = tb.contextMenu.s001.value()
		lockTranslate = tb.contextMenu.chk007.isChecked()
		lockRotation = tb.contextMenu.chk008.isChecked()
		lockScale = tb.contextMenu.chk009.isChecked()
		freezeTransforms = tb.contextMenu.chk010.isChecked()
		bakeChildPivot = tb.contextMenu.chk011.isChecked()
		remove = tb.contextMenu.chk015.isChecked()

		selection = pm.ls(selection=True)
		Rigging.createLocatorAtObject(selection, suffix=suffix, stripDigits=stripDigits, strip=strip, scale=scale, parent=parent, bakeChildPivot=bakeChildPivot, 
			freezeTransforms=freezeTransforms, lockTranslate=lockTranslate, lockRotation=lockRotation, lockScale=lockScale, remove=remove)


	def tb004(self, state=None):
		'''Lock/Unlock Attributes
		'''
		tb = self.current_ui.tb004
		if state is 'setMenu':
			tb.contextMenu.add('QCheckBox', setText='Translate', setObjectName='chk012', setChecked=False, setToolTip='')
			tb.contextMenu.add('QCheckBox', setText='Rotate', setObjectName='chk013', setChecked=False, setToolTip='')
			tb.contextMenu.add('QCheckBox', setText='Scale', setObjectName='chk014', setChecked=False, setToolTip='')

			self.connect_((tb.contextMenu.chk012,tb.contextMenu.chk013,tb.contextMenu.chk014), 'toggled', 
				[lambda state: self.rigging_ui.tb004.setText('Lock Attributes' 
					if any((tb.contextMenu.chk012.isChecked(),tb.contextMenu.chk013.isChecked(),tb.contextMenu.chk014.isChecked())) else 'Unlock Attributes'), 
				lambda state: self.rigging_submenu_ui.tb004.setText('Lock Transforms' 
					if any((tb.contextMenu.chk012.isChecked(),tb.contextMenu.chk013.isChecked(),tb.contextMenu.chk014.isChecked())) else 'Unlock Attributes')])
			return

		lockTranslate = tb.contextMenu.chk012.isChecked()
		lockRotation = tb.contextMenu.chk013.isChecked()
		lockScale = tb.contextMenu.chk014.isChecked()

		sel = pm.ls(selection=True, transforms=1, long=True)
		for obj in sel:

			attrs_and_state = {
				('tx','ty','tz'):lockTranslate, #attributes and state. ex. ('tx','ty','tz'):False
				('rx','ry','rz'):lockRotation, 
				('sx','sy','sz'):lockScale
			}

			[[pm.setAttr('{}.{}'.format(obj, i), lock=v) for i in k] for k, v in attrs_and_state.items()]


	@Slots.message
	@Slots.hideMain
	def b000(self):
		'''Object Transform Limit Attributes
		'''
		node = rt.selection
		if not node:
			return 'Error: Operation requires a single selected object.'
		'finish converting from Maya version.  Init.getParameterValuesMax is not likely doable in the same sense getParameterValuesMEL was'
		params = ['enableTranslationX','translationX','enableTranslationY','translationY','enableTranslationZ','translationZ',
			'enableRotationX','rotationX','enableRotationY','rotationY','enableRotationZ','rotationZ',
			'enableScaleX','scaleX','enableScaleY','scaleY','enableScaleZ','scaleZ']

		attrs = Init.getParameterValuesMax(node, 'transformLimits', params)
		self.setAttributeWindow(node, attrs, fn=Init.setParameterValuesMax, fn_args='transformLimits')


	def b001(self):
		'''Connect Joints
		'''
		pm.connectJoint(cm=1)


	def b002(self):
		'''Insert Joint Tool
		'''
		pm.setToolTo('insertJointContext') #insert joint tool


	def b004(self):
		'''Reroot
		'''
		pm.reroot() #re-root joints


	def b006(self):
		'''Constraint: Point
		'''
		pm.pointConstraint(offset=[0,0,0], weight=1)


	def b007(self):
		'''Constraint: Scale
		'''
		pm.scaleConstraint(offset=[1,1,1], weight=1)


	def b008(self):
		'''Constraint: Orient
		'''
		pm.orientConstraint(offset=[0,0,0], weight=1)


	def b009(self):
		'''Constraint: Aim
		'''
		pm.aimConstraint(offset=[0,0,0], weight=1, aimVector=[1,0,0], upVector=[0,1,0], worldUpType="vector", worldUpVector=[0,1,0])


	def b010(self):
		'''Constraint: Pole Vector
		'''
		pm.orientConstraint(offset=[0,0,0], weight=1)


	@staticmethod
	def createLocatorAtObject(objects, suffix='_LOC', stripDigits=False, strip='', scale=1, parent=False, freezeTransforms=True, 
					bakeChildPivot=True, lockTranslate=False, lockRotation=False, lockScale=False, remove=False, _fullPath=False):
		'''Create locators with the same transforms as any selected object(s).
		If there are vertices selected it will create a locator at the center of the selected vertices bounding box.

		:Parameters:
			objects (str)(list) = A list of objects, or an object name to create locators at.
			suffix (str) = A string appended to the end of the created locators name. (default: '_LOC') '_LOC#'
			stripDigits (bool) = Strip numeric characters from the string. If the resulting name is not unique, maya will append a trailing digit. (default=False)
			strip (str) = Strip a specific character set from the locator name. The locators name is based off of the selected objects name. (default=None)
			scale (float) = The scale of the locator. (default=1)
			parent (bool) = Parent to object to the locator. (default=False)
			freezeTransforms (bool) = Freeze transforms on the locator. (default=True)
			bakeChildPivot (bool) = Bake pivot positions on the child object. (default=True)
			lockTranslate (bool) = Lock the translate values of the child object. (default=False)
			lockRotation (bool) = Lock the rotation values of the child object. (default=False)
			lockScale (bool) = Lock the scale values of the child object. (default=False)
			remove (bool) = Removes the locator and any child locks. (not valid with component selections) (default=False)
			_fullPath (bool) = Internal use only (recursion). Use full path names for Dag objects. This can prevent naming conflicts when creating the locator. (default=False)

		ex. call: createLocatorAtSelection(strip='_GEO', suffix='', stripDigits=True, parent=True, lockTranslate=True, lockRotation=True)
		'''
		def _formatName(name, stripDigits=stripDigits, strip=strip, suffix=suffix):
			if stripDigits:
				name_ = ''.join([i for i in name if not i.isdigit()])	
			return name_.replace(strip, '')+suffix

		def _create_locator(obj, objName, stripDigits=stripDigits, strip=strip, suffix=suffix, scale=scale, _fullPath=_fullPath):
			locName = _formatName(objName, stripDigits, strip, suffix)

			loc = pm.spaceLocator(name=locName)
			if not any([loc, _fullPath]): #if locator creation fails; try again using the objects fullpath name.
				_retry_using_fullPath()

			pm.scale(loc, scale, scale, scale) #scale the locator
			return loc

		def _parent(obj, loc, freezeTransforms=freezeTransforms, bakeChildPivot=bakeChildPivot, state=1):
			objParent = pm.listRelatives(obj, parent=1)
			pm.parent(obj, loc)
			pm.parent(loc, objParent)

			if freezeTransforms:
				_set_lock_state(obj, translate=1, rotate=1, scale=1, state=0) #assure attributes are unlocked.
				pm.makeIdentity(loc, apply=True, normal=1) #1=the normals on polygonal objects will be frozen. 2=the normals on polygonal objects will be frozen only if its a non-rigid transformation matrix.

			if bakeChildPivot:
				pm.select(obj); pm.mel.BakeCustomPivot() #bake pivot on child object. Requires a select

		def _set_lock_state(obj, translate=lockTranslate, rotate=lockRotation, scale=lockScale, state=1):
			if isinstance(obj, str):
				obj = pm.ls(obj.split('|')[-1], transforms=1)[0]

			if type_(obj)=='locator':
				obj = pm.listRelatives(obj, children=1, type='transform')[0]

			if translate: #lock translation values
				[pm.setAttr(getattr(obj, attr), lock=state) for attr in ('tx','ty','tz')] #pm.setAttr(obj[0].translate, lock=state)
			if rotate: #lock rotation values
				[pm.setAttr(getattr(obj, attr), lock=state) for attr in ('rx','ry','rz')]
			if scale: #lock scale values
				[pm.setAttr(getattr(obj, attr), lock=state) for attr in ('sx','sy','sz')]

		def _try_parent_and_lock(obj, loc, objName, parent=parent, _fullPath=_fullPath):
			try:
				if parent: #parent
					_parent(obj, loc)
				_set_lock_state(obj)
			except Exception as error:
				try:
					if not any([loc, _fullPath]): #try again using the objects full path name.
						_retry_using_fullPath()
				except:
					print ('# Error: {}: {} #'.format(objName, error))
					pm.delete(loc)

		def _remove_locators(obj):
			if not type_(obj) == 'locator':
				obj = pm.listRelatives(obj, parent=1)
				print (obj, type_(obj))
				if not obj or not type_(obj[0]) == 'locator':
					return False
			pm.ungroup(obj)
			pm.delete(obj)

		type_ = lambda obj: pm.listRelatives(obj, shapes=1)[0].type()

		_retry_using_fullPath = lambda: Rigging.createLocatorAtObject(suffix=suffix, stripDigits=stripDigits, strip=strip, 
			parent=parent, scale=scale, lockTranslate=lockTranslate, lockRotation=lockRotation, lockScale=lockScale, _fullPath=1)

		# pm.undoInfo(openChunk=1)
		objects = pm.ls(objects, long=_fullPath, objectsOnly=True)

		sel_verts = pm.filterExpand(objects, sm=31) #returns a string list.
		if sel_verts: #vertex selection

			objName = sel_verts[0].split('.')[0]
			obj = pm.ls(objName)
			
			loc = _create_locator(obj, objName)

			xmin, ymin, zmin, xmax, ymax, zmax = pm.exactWorldBoundingBox(sel_verts)
			x, y, z = pos = ((xmin + xmax) / 2, (ymin + ymax) / 2, (zmin + zmax) / 2)
			pm.move(x, y, z, loc)

			_try_parent_and_lock(obj, loc, objName)

		else: #object selection
			for obj in objects:

				if remove:
					if pm.objExists(obj): #if the locator hasnt already been deleted by another child.
						_set_lock_state(obj, translate=1, rotate=1, scale=1, state=0)
						_remove_locators(obj)
					continue

				objName = obj.name()

				loc = _create_locator(obj, objName)

				tempConst = pm.parentConstraint(obj, loc, mo=False)
				pm.delete(tempConst)

				_try_parent_and_lock(obj, loc, objName)
		# pm.undoInfo(closeChunk=1)








#module name
print(os.path.splitext(os.path.basename(__file__))[0])
# -----------------------------------------------
# Notes
# -----------------------------------------------