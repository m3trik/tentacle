# !/usr/bin/python
# coding=utf-8
try:
	import pymel.core as pm
except ImportError as error:
	print (__file__, error)

from tentacle.slots.tk import strtk, itertk


class Riggingtls(object):
	'''
	'''
	from tentacle.slots.maya import mayatk as mtk

	@staticmethod
	def createLocator(name=None, pos=(), scale=1):
		'''Create a locator with the given scale.

		:Parameters:
			name (str) = Name the locator.
			pos (tuple) = The desired location in world space.
			scale (float) = The desired scale of the locator.

		:Return:
			(obj) locator
		'''
		loc = pm.spaceLocator()

		if name:
			pm.rename(loc, name)
		if pos:
			pm.move(pos[0], pos[1], pos[2], loc)
		if scale!=1:
			pm.scale(loc, scale, scale, scale) #scale the locator

		return loc


	@staticmethod
	def isLocator(obj):
		'''Check if the object is a locator.

		:Parameters:
			obj () = The object to query.

		:Return:
			(bool)
		'''
		if not obj:
			return False
		return mtk.getType(obj)=='locator'


	@classmethod
	def removeLocator(cls, objects):
		'''Remove a parented locator from the child object.

		:Parameters:
			obj (str)(obj)(list) = The child object or the locator itself.
		'''
		errorMsg = lambda: pm.inViewMessage(
			statusMessage="{} in removeLocator\n# Error: Unable to remove locator for the given object. #".format(__file__), 
			pos='topCenter', 
			fade=True
		)

		pm.undoInfo(openChunk=1)

		for obj in pm.ls(objects, long=True, objectsOnly=True):
			if not pm.objExists(obj):
				continue

			elif cls.isLocator(obj) and not mtk.getParent(obj) and not mtk.getChildren(obj):
				pm.delete(obj)
				continue

			#unlock attributes
			cls.setAttrLockState(obj, translate=False, rotate=False, scale=False) #unlock all.

			if not cls.isLocator(obj):
				try: #if the 'obj' is not a locator, check if it's parent is.
					obj = mtk.getParent(obj)
					if not cls.isLocator(obj):
						errorMsg()
						continue
				except IndexError as error:
					errorMsg()
					continue

			try: #remove from group
				grp = mtk.getParent(obj)
			except IndexError as error:
				errorMsg()
				continue
			if mtk.isGroup(grp):
				if grp.split('_')[0]==obj.split('_')[0]:
					pm.ungroup(grp)

			#remove locator
			pm.ungroup(obj)
			pm.delete(obj)

		pm.undoInfo(closeChunk=1)


	@classmethod
	def setAttrLockState(cls, objects, translate=None, rotate=None, scale=None, **kwargs):
		'''Lock/Unlock any attribute for the given objects, by passing it into kwargs as <attr>=<value>.
		A 'True' value locks the attribute, 'False' unlocks, while 'None' leaves the state unchanged.

		:Parameters:
			objects (str)(obj)(list) = The object(s) to lock/unlock attributes of.
			translate (bool) = Lock/Unlock all translate x,y,z values at once.
			rotate (bool) = Lock/Unlock all rotate x,y,z values at once.
			scale (bool) = Lock/Unlock all scale x,y,z values at once.
		'''
		objects = pm.ls(objects, transforms=1, long=True)

		attrs_and_state = {
			('tx','ty','tz'):translate, #attributes and state. ex. ('tx','ty','tz'):False
			('rx','ry','rz'):rotate, 
			('sx','sy','sz'):scale
		}

		attrs_and_state.update(kwargs) #update the dict with any values from kwargs.

		for obj in objects:
			try:
				if cls.isLocator(obj):
					obj = pm.listRelatives(obj, children=1, type='transform')[0]
			except IndexError as error:
				return

			for attrs, state in attrs_and_state.items():
				if state is None:
					continue
				for a in itertk.makeList(attrs):
					pm.setAttr('{}.{}'.format(obj, a), lock=state)


	@staticmethod
	def createGroup(objects=[], name='', zeroTranslation=False, zeroRotation=False, zeroScale=False):
		'''Create a group containing any given objects.

		:Parameters:
			objects (str)(obj)(list) = The object(s) to group.
			name (str) = Name the group.
			zeroTranslation (bool) = Freeze translation before parenting.
			zeroRotation (bool) = Freeze rotation before parenting.
			zeroScale (bool) = Freeze scale before parenting.

		:Return:
			(obj) the group.
		'''
		grp = pm.group(empty=True, n=name)
		try:
			pm.parent(grp, objects)
		except Exception as error:
			print ('{} in createGroup\n	# Error: Unable to parent object(s): {} #'.format(__file__, error))

		if zeroTranslation:
			for attr in ('tx','ty','tz'):
				pm.setAttr(getattr(grp, attr), 0) #pm.setAttr(node.translate, 0)
		if zeroRotation:
			for attr in ('rx','ry','rz'):
				pm.setAttr(getattr(grp, attr), 0)
		if zeroScale:
			for attr in ('sx','sy','sz'):
				pm.setAttr(getattr(grp, attr), 0)

		pm.parent(grp, world=True)
		return grp


	@classmethod
	def createLocatorAtObject(cls, objects, parent=False, freezeTransforms=False, bakeChildPivot=False, 
			grpSuffix='_GRP#', locSuffix='_LOC#', objSuffix='_GEO#', stripDigits=False, stripSuffix=False, 
			scale=1, lockTranslate=False, lockRotation=False, lockScale=False):
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
		getSuffix = lambda o: locSuffix if cls.isLocator(o) else grpSuffix if mtk.isGroup(o) else objSuffix #match the correct suffix to the object type.

		pm.undoInfo(openChunk=1)

		for obj in pm.ls(objects, long=True, type='transform'):

			if bakeChildPivot:
				from pivot_maya import Pivot_maya
				Pivot_maya.bakeCustomPivot(obj, position=1, orientation=1)

			vertices = pm.filterExpand(obj, sm=31) #returns a string list.
			if vertices:
				objName = vertices[0].split('.')[0]
				obj = pm.ls(objName)

				loc = cls.createLocator(scale=scale)

				xmin, ymin, zmin, xmax, ymax, zmax = pm.exactWorldBoundingBox(vertices)
				x, y, z = pos = ((xmin + xmax) / 2, (ymin + ymax) / 2, (zmin + zmax) / 2)
				pm.move(x, y, z, loc)

			else: #object:
				loc = cls.createLocator(scale=scale)
				tempConst = pm.parentConstraint(obj, loc, maintainOffset=False)
				pm.delete(tempConst)

			try:
				if parent:
					origParent = pm.listRelatives(obj, parent=1)

					grp = cls.createGroup(obj, zeroTranslation=1, zeroRotation=1)
					pm.rename(grp, strtk.formatSuffix(obj.name(), suffix=getSuffix(grp), strip=(objSuffix, grpSuffix, locSuffix), stripTrailingInts=stripDigits, stripTrailingAlpha=stripSuffix))

					pm.parent(obj, loc)
					pm.parent(loc, grp)
					pm.parent(grp, origParent)

				if freezeTransforms: #freeze transforms before baking pivot.
					cls.setAttrLockState(obj, translate=False, rotate=False, scale=False) #assure attributes are unlocked.
					pm.makeIdentity(obj, apply=True, normal=1)
					pm.makeIdentity(loc, apply=True, normal=1) #1=the normals on polygonal objects will be frozen. 2=the normals on polygonal objects will be frozen only if its a non-rigid transformation matrix.

				pm.rename(loc, strtk.formatSuffix(obj.name(), suffix=getSuffix(loc), strip=(objSuffix, grpSuffix, locSuffix), stripTrailingInts=stripDigits, stripTrailingAlpha=stripSuffix))
				pm.rename(obj, strtk.formatSuffix(obj.name(), suffix=getSuffix(obj), strip=(objSuffix, grpSuffix, locSuffix), stripTrailingInts=stripDigits, stripTrailingAlpha=stripSuffix))

				cls.setAttrLockState(obj, translate=lockTranslate, rotate=lockRotation, scale=lockScale)

			except Exception as error:
				pm.delete(loc)
				raise (error)

		pm.undoInfo(closeChunk=1)

# -----------------------------------------------






# -----------------------------------------------

if __name__=='__main__':

	sel = pm.ls(sl=1)

	Riggingtls.createLocatorAtObject(sel,
		parent=1,
		freezeTransforms=1,
		bakeChildPivot=1,
		grpSuffix='_GRP',
		locSuffix='_LCTR',
		objSuffix='_GEO',
		stripDigits=1,
		stripSuffix=1,
		scale=1,
		lockTranslate=0,
		lockRotation=0,
		lockScale=0,
	)

# -----------------------------------------------
from tentacle import addMembers
addMembers(__name__)









# print (__name__) #module name
# -----------------------------------------------
# Notes
# -----------------------------------------------


# deprecated: -----------------------------------
