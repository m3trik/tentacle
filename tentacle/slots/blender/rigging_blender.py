# !/usr/bin/python
# coding=utf-8
from tentacle.slots.blender import *
from tentacle.slots.rigging import Rigging



class Rigging_blender(Rigging, SlotsBlender):
	def __init__(self, *args, **kwargs):
		SlotsBlender.__init__(self, *args, **kwargs)
		Rigging.__init__(self, *args, **kwargs)

		cmb = self.sb.rigging.draggableHeader.ctx_menu.cmb000
		items = []
		cmb.addItems_(items, 'Rigging Editors')

		cmb = self.sb.rigging.cmb001
		items = []
		cmb.addItems_(items, "Create")


	def cmb000(self, *args, **kwargs):
		'''Editors
		'''
		cmb = self.sb.rigging.draggableHeader.ctx_menu.cmb000

		if index>0:
			text = cmb.items[index]
			if text=='Quick Rig':
				mel.eval('QuickRigEditor;') #Quick Rig
			elif text=='HumanIK':
				mel.eval('HIKCharacterControlsTool;') #HumanIK
			elif text=='Expression Editor':
				mel.eval('ExpressionEditor;') #Expression Editor
			elif text=='Shape Editor':
				mel.eval('ShapeEditor;') #Shape Editor
			elif text=='Connection Editor':
				mel.eval('ConnectionEditor;') #Connection Editor
			elif text=='Channel Control Editor':
				mel.eval('ChannelControlEditor;') #Channel Control Editor
			elif text=='Set Driven Key':
				mel.eval('SetDrivenKeyOptions;') #Set Driven Key
			cmb.setCurrentIndex(0)


	def cmb001(self, *args, **kwargs):
		'''Create
		'''
		cmb = self.sb.rigging.cmb001

		if index>0:
			text = cmb.items[index]
			if text=='Joints':
				pm.setToolTo('jointContext') #create joint tool
			elif text=='Locator':
				pm.spaceLocator(p=[0,0,0]) #locator
			elif text=='IK Handle':
				pm.setToolTo('ikHandleContext') #create ik handle
			elif text=='Lattice':
				pm.lattice(divisions=[2,5,2], objectCentered=1, ldv=[2,2,2]) ##create lattice
			elif text=='Cluster':
				mel.eval('CreateCluster;') #create cluster
			cmb.setCurrentIndex(0)


	def chk000(self, *args, **kwargs):
		'''Scale Joint
		'''
		self.sb.toggle_widgets(setUnChecked='chk001-2')
		self.sb.rigging.tb000.option_menu.s000.setValue(pm.jointDisplayScale(query=1)) #init global joint display size


	def chk001(self, *args, **kwargs):
		'''Scale IK
		'''
		self.sb.toggle_widgets(setUnChecked='chk000, chk002')
		self.sb.rigging.tb000.option_menu.setValue(pm.ikHandleDisplayScale(query=1)) #init IK handle display size
		

	def chk002(self, *args, **kwargs):
		'''Scale IK/FK
		'''
		self.sb.toggle_widgets(setUnChecked='chk000-1')
		self.sb.rigging.tb000.option_menu.setValue(pm.jointDisplayScale(query=1, ikfk=1)) #init IKFK display size


	def s000(self, *args, **kwargs):
		'''Scale Joint/IK/FK
		'''
		value = self.sb.rigging.tb000.option_menu.value()

		if self.sb.rigging.chk000.isChecked():
			pm.jointDisplayScale(value) #set global joint display size
		elif self.sb.rigging.chk001.isChecked():
			pm.ikHandleDisplayScale(value) #set global IK handle display size
		else: #self.sb.rigging.chk002.isChecked():
			pm.jointDisplayScale(value, ikfk=1) #set global IKFK display size


	def tb000(self, *args, **kwargs):
		'''Toggle Display Local Rotation Axes
		'''
		tb = self.sb.rigging.tb000

		joints = pm.ls(type="joint") #get all scene joints

		state = pm.toggle(joints[0], query=1, localAxis=1)
		if tb.option_menu.isChecked():
			if not state:
				toggle=True
		else:
			if state:
				toggle=True

		if toggle:
			pm.toggle(joints, localAxis=1) #set display off

		self.mtk.viewport_message("Display Local Rotation Axes:<hl>"+str(state)+"</hl>")


	def tb001(self, *args, **kwargs):
		'''Orient Joints
		'''
		tb = self.sb.rigging.tb001

		orientJoint = 'xyz' #orient joints
		if tb.option_menu.isChecked():
			orientJoint = 'none' #orient joint to world

		pm.joint(edit=1, orientJoint=orientJoint, zeroScaleOrient=1, ch=1)


	def tb002(self, *args, **kwargs):
		'''Constraint: Parent
		'''
		tb = self.sb.rigging.tb002

		template = tb.option_menu.chk004.isChecked()

		objects = pm.ls(sl=1, objectsOnly=1)

		for obj in objects[:-1]:
			pm.parentConstraint(obj, objects[:-1], maintainOffset=1, weight=1)

			if template:
				if not pm.toggle(obj, template=1, query=1):
					pm.toggle(obj, template=1, query=1)


	@SlotsBlender.undoChunk
	def tb003(self, *args, **kwargs):
		'''Create Locator at Selection
		'''
		tb = self.sb.rigging.tb003

		suffix = tb.option_menu.t000.text()
		strip_digits = tb.option_menu.chk005.isChecked()
		strip = tb.option_menu.t001.text()
		parent = tb.option_menu.chk006.isChecked()
		scale = tb.option_menu.s001.value()
		lock_translate = tb.option_menu.chk007.isChecked()
		lock_rotation = tb.option_menu.chk008.isChecked()
		lock_scale = tb.option_menu.chk009.isChecked()
		freeze_transforms = tb.option_menu.chk010.isChecked()
		bake_child_pivot = tb.option_menu.chk011.isChecked()
		remove = tb.option_menu.chk015.isChecked()

		selection = pm.ls(selection=True)
		self.create_locator_at_object(selection, suffix=suffix, strip_digits=strip_digits, strip=strip, scale=scale, parent=parent, bake_child_pivot=bake_child_pivot, 
			freeze_transforms=freeze_transforms, lock_translate=lock_translate, lock_rotation=lock_rotation, lock_scale=lock_scale, remove=remove)


	def tb004(self, *args, **kwargs):
		'''Lock/Unlock Attributes
		'''
		tb = self.sb.rigging.tb004

		lock_translate = tb.option_menu.chk012.isChecked()
		lock_rotation = tb.option_menu.chk013.isChecked()
		lock_scale = tb.option_menu.chk014.isChecked()

		sel = pm.ls(selection=True, transforms=1, long=True)
		for obj in sel:

			attrs_and_state = {
				('tx','ty','tz'):lock_translate, #attributes and state. ex. ('tx','ty','tz'):False
				('rx','ry','rz'):lock_rotation, 
				('sx','sy','sz'):lock_scale
			}

			[[pm.setAttr('{}.{}'.format(obj, i), lock=v) for i in k] for k, v in attrs_and_state.items()]


	@Slots.hideMain
	def b000(self, *args, **kwargs):
		'''Object Transform Limit Attributes
		'''
		node = pm.ls(sl=1, objectsOnly=1)
		if not node:
			return 'Error: Operation requires a single selected object.'

		params = ['enableTranslationX','translationX','enableTranslationY','translationY','enableTranslationZ','translationZ',
			'enableRotationX','rotationX','enableRotationY','rotationY','enableRotationZ','rotationZ',
			'enableScaleX','scaleX','enableScaleY','scaleY','enableScaleZ','scaleZ']

		attrs = SlotsBlender.get_parameter_values(node, 'transformLimits', params)
		self.setAttributeWindow(node, fn=SlotsBlender.set_parameter_values, 'transformLimits', **attrs)


	def b001(self, *args, **kwargs):
		'''Connect Joints
		'''
		pm.connectJoint(cm=1)


	def b002(self, *args, **kwargs):
		'''Insert Joint Tool
		'''
		pm.setToolTo('insertJointContext') #insert joint tool


	def b004(self, *args, **kwargs):
		'''Reroot
		'''
		pm.reroot() #re-root joints


	def b006(self, *args, **kwargs):
		'''Constraint: Point
		'''
		pm.pointConstraint(offset=[0,0,0], weight=1)


	def b007(self, *args, **kwargs):
		'''Constraint: Scale
		'''
		pm.scaleConstraint(offset=[1,1,1], weight=1)


	def b008(self, *args, **kwargs):
		'''Constraint: Orient
		'''
		pm.orientConstraint(offset=[0,0,0], weight=1)


	def b009(self, *args, **kwargs):
		'''Constraint: Aim
		'''
		pm.aimConstraint(offset=[0,0,0], weight=1, aimVector=[1,0,0], upVector=[0,1,0], worldUpType="vector", worldUpVector=[0,1,0])


	def b010(self, *args, **kwargs):
		'''Constraint: Pole Vector
		'''
		pm.orientConstraint(offset=[0,0,0], weight=1)


	@SlotsBlender.undoChunk
	def create_locator_at_object(self, objects, suffix='_LOC', strip_digits=False, strip='', scale=1, parent=False, freeze_transforms=True, 
					bake_child_pivot=True, lock_translate=False, lock_rotation=False, lock_scale=False, remove=False, _fullPath=False):
		'''Create locators with the same transforms as any selected object(s).
		If there are vertices selected it will create a locator at the center of the selected vertices bounding box.

		Parameters:
			objects (str/list): A list of objects, or an object name to create locators at.
			suffix (str): A string appended to the end of the created locators name. (default: '_LOC') '_LOC#'
			strip_digits (bool): Strip numeric characters from the string. If the resulting name is not unique, maya will append a trailing digit. (default=False)
			strip (str): Strip a specific character set from the locator name. The locators name is based off of the selected objects name. (default=None)
			scale (float) = The scale of the locator. (default=1)
			parent (bool): Parent to object to the locator. (default=False)
			freeze_transforms (bool): Freeze transforms on the locator. (default=True)
			bake_child_pivot (bool): Bake pivot positions on the child object. (default=True)
			lock_translate (bool): Lock the translate values of the child object. (default=False)
			lock_rotation (bool): Lock the rotation values of the child object. (default=False)
			lock_scale (bool): Lock the scale values of the child object. (default=False)
			remove (bool): Removes the locator and any child locks. (not valid with component selections) (default=False)
			_fullPath (bool): Internal use only (recursion). Use full path names for Dag objects. This can prevent naming conflicts when creating the locator. (default=False)

		Example: createLocatorAtSelection(strip='_GEO', suffix='', strip_digits=True, parent=True, lock_translate=True, lock_rotation=True)
		'''
		def _formatName(name, strip_digits=strip_digits, strip=strip, suffix=suffix):
			if strip_digits:
				name = ''.join([i for i in name if not i.isdigit()])	
			return name.replace(strip, '')+suffix

		def _create_locator(obj, objName, strip_digits=strip_digits, strip=strip, suffix=suffix, scale=scale, _fullPath=_fullPath):
			locName = _formatName(objName, strip_digits, strip, suffix)

			loc = pm.spaceLocator(name=locName)
			if not any([loc, _fullPath]): #if locator creation fails; try again using the objects fullpath name.
				_retry_using_fullPath()

			pm.scale(loc, scale, scale, scale) #scale the locator
			return loc

		def _parent(obj, loc, freeze_transforms=freeze_transforms, bake_child_pivot=bake_child_pivot, state=1):
			objParent = pm.listRelatives(obj, parent=1)
			pm.parent(obj, loc)
			pm.parent(loc, objParent)

			if freeze_transforms:
				_set_lock_state(obj, translate=1, rotate=1, scale=1, state=0) #assure attributes are unlocked.
				pm.makeIdentity(loc, apply=True, normal=1) #1=the normals on polygonal objects will be frozen. 2=the normals on polygonal objects will be frozen only if its a non-rigid transformation matrix.

			if bake_child_pivot:
				pm.select(obj); pm.mel.BakeCustomPivot() #bake pivot on child object. Requires a select

		def _set_lock_state(obj, translate=lock_translate, rotate=lock_rotation, scale=lock_scale, state=1):
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
				if not obj or not type_(obj[0]) == 'locator':
					return False
			pm.ungroup(obj)
			pm.delete(obj)

		type_ = lambda obj: pm.listRelatives(obj, shapes=1)[0].type()

		_retry_using_fullPath = lambda: self.create_locator_at_object(suffix=suffix, strip_digits=strip_digits, strip=strip, 
			parent=parent, scale=scale, lock_translate=lock_translate, lock_rotation=lock_rotation, lock_scale=lock_scale, _fullPath=1)

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
print (__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------


#deprecated:

# def createLocatorAtSelection(suffix='_LOC', strip_digits=False, strip='', scale=1, parent=False, freezeChildTransforms=False, bake_child_pivot=False, lock_translate=False, lock_rotation=False, lock_scale=False, _fullPath=False):
# 	'''Create locators with the same transforms as any selected object(s).
# 	If there are vertices selected it will create a locator at the center of the selected vertices bounding box.

# 	Parameters:
# 		suffix (str): A string appended to the end of the created locators name. (default: '_LOC') '_LOC#'
# 		strip_digits (bool): Strip numeric characters from the string. If the resulting name is not unique, maya will append a trailing digit. (default=False)
# 		strip (str): Strip a specific character set from the locator name. The locators name is based off of the selected objects name. (default=None)
# 		scale (float) = The scale of the locator. (default=1)
# 		parent (bool): Parent to object to the locator. (default=False)
# 		freezeChildTransforms (bool): Freeze transforms on the child object. (Valid only with parent flag) (default=False)
# 		bake_child_pivot (bool): Bake pivot positions on the child object. (Valid only with parent flag) (default=False)
# 		lock_translate (bool): Lock the translate values of the child object. (default=False)
# 		lock_rotation (bool): Lock the rotation values of the child object. (default=False)
# 		lock_scale (bool): Lock the scale values of the child object. (default=False)
# 		_fullPath (bool): Internal use only (recursion). Use full path names for Dag objects. This can prevent naming conflicts when creating the locator. (default=False)

# 	Example:
# 		createLocatorAtSelection(strip='_GEO', suffix='', strip_digits=True, scale=10, parent=True, lock_translate=True, lock_rotation=True)
# 	'''
# 	import pymel.core as pm
# 	sel = pm.ls(selection=True, long=_fullPath, objectsOnly=True)
# 	sel_verts = pm.filterExpand(sm=31)

# 	if not sel:
# 		error = '# Error: Nothing Selected. #'
# 		print (error)
# 		return error

# 	def _formatName(name, strip_digits=strip_digits, strip=strip, suffix=suffix):
# 		if strip_digits:
# 			name_ = ''.join([i for i in name if not i.isdigit()])	
# 		return name_.replace(strip, '')+suffix

# 	def _parent(obj, loc, parent=parent, freezeChildTransforms=freezeChildTransforms, bake_child_pivot=bake_child_pivot):
# 		if parent: #parent
# 			if freezeChildTransforms:
# 				pm.makeIdentity(obj, apply=True, t=1, r=1, s=1, normal=2) #normal parameter: 1=the normals on polygonal objects will be frozen. 2=the normals on polygonal objects will be frozen only if its a non-rigid transformation matrix.
# 			if bake_child_pivot:
# 				pm.select(obj); pm.mel.BakeCustomPivot() #bake pivot on child object.
# 			objParent = pm.listRelatives(obj, parent=1)
# 			pm.parent(obj, loc)
# 			pm.parent(loc, objParent)

# 	def _lockChildAttributes(obj, lock_translate=lock_translate, lock_rotation=lock_rotation, lock_scale=lock_scale):
# 		try: #split in case of long name to get the obj attribute.  ex. 'f15e_door_61_bellcrank|Bolt_GEO.tx' to: Bolt_GEO.tx
# 			setAttrs = lambda attrs: [pm.setAttr('{}.{}'.format(obj.split('|')[-1], attr), lock=True) for attr in attrs]
# 		except: #if obj is type object:
# 			setAttrs = lambda attrs: [pm.setAttr('{}.{}'.format(obj, attr), lock=True) for attr in attrs]

# 		if lock_translate: #lock translation values
# 			setAttrs(('tx','ty','tz'))

# 		if lock_rotation: #lock rotation values
# 			setAttrs(('rx','ry','rz'))
				
# 		if lock_scale: #lock scale values
# 			setAttrs(('sx','sy','sz'))

# 	_fullPath = lambda: self.createLocatorAtSelection(suffix=suffix, strip_digits=strip_digits, 
# 				strip=strip, parent=parent, scale=scale, _fullPath=True, 
# 				lock_translate=lock_translate, lock_rotation=lock_rotation, lock_scale=lock_scale)

# 	if sel_verts: #vertex selection

# 		objName = sel_verts[0].split('.')[0]
# 		locName = _formatName(objName, strip_digits, strip, suffix)

# 		loc = pm.spaceLocator(name=locName)
# 		if not any([loc, _fullPath]): #if locator creation fails; try again using the objects full path name.
# 			_fullPath()

# 		pm.scale(scale, scale, scale)

# 		bb = pm.exactWorldBoundingBox(sel_verts)
# 		pos = ((bb[0] + bb[3]) / 2, (bb[1] + bb[4]) / 2, (bb[2] + bb[5]) / 2)
# 		pm.move(pos[0], pos[1], pos[2], loc)

# 		_parent(objName, loc)
# 		_lockChildAttributes(objName)

# 	else: #object selection
# 		for obj in sel:

# 			objName = obj.name()
# 			locName = _formatName(objName, strip_digits, strip, suffix)

# 			loc = pm.spaceLocator(name=locName)
# 			if not any([loc, _fullPath]): #if locator creation fails; try again using the objects fullpath name.
# 				_fullPath()

# 			pm.scale(scale, scale, scale)

# 			tempConst = pm.parentConstraint(obj, loc, mo=False)
# 			pm.delete(tempConst)
# 			pm.select(clear=True)

# 			_parent(obj, loc)
# 			_lockChildAttributes(objName)


