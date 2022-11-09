# !/usr/bin/python
# coding=utf-8
try:
	import pymel.core as pm
except ImportError as error:
	print (__file__, error)



class Rigging_utils_maya(object):
	'''
	'''
	from utils import Utils
	from node_utils_maya import Node_utils_maya
	formatName = Utils.formatName
	isGroup = Node_utils_maya.isGroup
	getType = Node_utils_maya.getType


	@classmethod
	def isLocator(cls, obj):
		'''
		'''
		return cls.getType(obj)=='locator'


	@staticmethod
	def create_locator(scale=1):
		'''Create a locator with the given scale.
		:parameters:
			scale (int) = The desired scale of the locator.

		:return:
			(obj) locator
		'''
		loc = pm.spaceLocator()
		pm.scale(loc, scale, scale, scale) #scale the locator
		return loc


	@classmethod
	def remove_locator(cls, obj):
		'''Remove a parented locator from the child object.
		:parameters:
			obj (str)(obj)(list) = The child object or the locator itself.

		:return:
			(bool) True if successful
		'''
		if not cls.isLocator(obj):
			try:
				obj = pm.listRelatives(obj, parent=1)[0]
				if not cls.isLocator(obj):
					return False
			except IndexError as error:
				return False
		pm.ungroup(obj)
		pm.delete(obj)
		return True


	@classmethod
	def unlockAttributes(cls, obj, translate=False, rotate=False, scale=False):
		'''Extends the functionality of the 'lockAttributes' method to unlock.

		:parameters:
			obj (str)(obj)(list) = The object to lock/unlock attributes of.
			translate (bool) = Unlock the translate x,y,z values.
			rotate (bool) = Unlock the rotate x,y,z values.
			scale (bool) = Unlock the scale x,y,z values.
		'''
		cls.lockAttributes(obj, translate=translate, rotate=rotate, scale=scale, _state=0)


	@classmethod
	def lockAttributes(cls, obj, translate=False, rotate=False, scale=False, _state=1):
		'''Lock the translate, rotate, and scale attributes for the given objects.

		:parameters:
			obj (str)(obj)(list) = The object to lock/unlock attributes of.
			translate (bool) = Lock the translate x,y,z values.
			rotate (bool) = Lock the rotate x,y,z values.
			scale (bool) = Lock the scale x,y,z values.
			_state (int) = Internal use. The lock state. A value of 0 unlocks the attributes. (default:1)
		'''
		if cls.isLocator(obj):
			obj = pm.listRelatives(obj, children=1, type='transform')[0]

		if translate: #lock translation values
			[pm.setAttr(getattr(obj, attr), lock=_state) for attr in ('tx','ty','tz')] #pm.setAttr(obj[0].translate, lock=state)
		if rotate: #lock rotation values
			[pm.setAttr(getattr(obj, attr), lock=_state) for attr in ('rx','ry','rz')]
		if scale: #lock scale values
			[pm.setAttr(getattr(obj, attr), lock=_state) for attr in ('sx','sy','sz')]


	@staticmethod
	def createGroup(objects, name='', zeroTranslation=False, zeroRotation=False):
		'''
		'''
		grp = pm.group(empty=True, n=name)
		pm.parent(grp, objects)

		if zeroTranslation:
			[pm.setAttr(getattr(grp, attr), 0) for attr in ('tx','ty','tz')] #pm.setAttr(node.translate, 0)
		if zeroRotation:
			[pm.setAttr(getattr(grp, attr), 0) for attr in ('rx','ry','rz')]

		pm.parent(grp, world=True)
		return grp


	@classmethod
	def createLocatorAtObject(cls, objects, parent=False, freezeTransforms=False, bakeChildPivot=False, grpSuffix='_GRP#', locSuffix='_LOC#', objSuffix='_GEO#', 
		stripDigits=False, stripSuffix=False, scale=1, lockTranslate=False, lockRotation=False, lockScale=False, remove=False):
		'''Create locators with the same transforms as any selected object(s).
		If there are vertices selected it will create a locator at the center of the selected vertices bounding box.

		:Parameters:
			objects (str)(obj)(list) = A list of objects, or an object name to create locators at.
			parent (bool) = Parent the object to the locator. (default=False)
			freezeTransforms (bool) = Freeze transforms on the locator. (default=True)
			bakeChildPivot (bool) = Bake pivot positions on the child object. (default=True)
			grpSuffix (str) = A string appended to the end of the created groups name. (default: '_GRP#')
			locSuffix (str) = A string appended to the end of the created locators name. (default: '_LOC#')
			objSuffix (str) = A string appended to the end of the existing objects name. (default: '_GEO#')
			stripDigits (bool) = Strip numeric characters from the string. If the resulting name is not unique, maya will append a trailing digit. (default=False)
			stripSuffix (str) = Strip any existing suffix. A suffix is defined by the last '_' (if one exists) and any chars trailing. (default=False)
			scale (float) = The scale of the locator. (default=1)
			lockTranslate (bool) = Lock the translate values of the child object. (default=False)
			lockRotation (bool) = Lock the rotation values of the child object. (default=False)
			lockScale (bool) = Lock the scale values of the child object. (default=False)
			remove (bool) = Removes the locator and any child locks. (not valid with component selections) (default=False)

		ex. call: createLocatorAtSelection(strip='_GEO', suffix='', stripDigits=True, parent=True, lockTranslate=True, lockRotation=True)
		'''
		pm.undoInfo(openChunk=1)

		for obj in pm.ls(objects, long=True, objectsOnly=True):

			if bakeChildPivot:
				from pivot_maya import Pivot_maya
				Pivot_maya.bakeCustomPivot(obj, position=1, orientation=1)

			vertices = pm.filterExpand(obj, sm=31) #returns a string list.
			if vertices:
				objName = vertices[0].split('.')[0]
				obj = pm.ls(objName)

				loc = cls.create_locator(scale)

				xmin, ymin, zmin, xmax, ymax, zmax = pm.exactWorldBoundingBox(vertices)
				x, y, z = pos = ((xmin + xmax) / 2, (ymin + ymax) / 2, (zmin + zmax) / 2)
				pm.move(x, y, z, loc)

			else: #object
				if remove:
					if pm.objExists(obj): #if the locator hasn't already been deleted by another child.
						cls.unlockAttributes(obj, translate=1, rotate=1, scale=1) #unlock all.
						locator_removed = cls.remove_locator(obj)
						if not locator_removed:
							pm.inViewMessage(statusMessage="Unable to remove locator for {}.".format(obj.name()), pos='topCenter', fade=True)
					continue

				loc = cls.create_locator(scale)

				tempConst = pm.parentConstraint(obj, loc, maintainOffset=False)
				pm.delete(tempConst)

			try:
				if parent:
					origParent = pm.listRelatives(obj, parent=1)
					grpName = cls.formatName(obj, stripTrailingInts=stripDigits, strip=(locSuffix, objSuffix), suffix=grpSuffix)
					grp = cls.createGroup(obj, name=grpName, zeroTranslation=1, zeroRotation=1)
					pm.parent(obj, loc)
					pm.parent(loc, grp)
					pm.parent(grp, origParent)

				if freezeTransforms: #freeze transforms before baking pivot.
					cls.unlockAttributes(obj, translate=1, rotate=1, scale=1) #assure attributes are unlocked.
					pm.makeIdentity(obj, apply=True, normal=1)
					pm.makeIdentity(loc, apply=True, normal=1) #1=the normals on polygonal objects will be frozen. 2=the normals on polygonal objects will be frozen only if its a non-rigid transformation matrix.

				pm.rename(loc, cls.formatName(obj, stripTrailingInts=stripDigits, strip=(locSuffix, objSuffix, grpSuffix) if stripSuffix else '', suffix=locSuffix))
				pm.rename(obj, cls.formatName(obj, stripTrailingInts=stripDigits, strip=(locSuffix, objSuffix, grpSuffix) if stripSuffix else '', suffix=objSuffix if not cls.isLocator(obj) else locSuffix))

				cls.lockAttributes(obj, translate=lockTranslate, rotate=lockRotation, scale=lockScale)

			except Exception as error:
				pm.delete(loc)
				raise (error)

		pm.undoInfo(closeChunk=1)










if __name__=='__main__':

	sel = pm.ls(sl=1)

	Rigging_utils_maya.createLocatorAtObject(sel,
		parent=1,
		freezeTransforms=1,
		bakeChildPivot=1,
		grpSuffix='_GRP_',
		locSuffix='_LCTR_',
		objSuffix='_GEO_',
		stripDigits=1,
		stripSuffix=1,
		scale=1,
		lockTranslate=0,
		lockRotation=0,
		lockScale=0,
		remove=0,
	)



#module name
# print (__name__)
# -----------------------------------------------
# Notes
# -----------------------------------------------





# Deprecated ------------------------------------