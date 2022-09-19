# !/usr/bin/python
# coding=utf-8
import pymel.core as pm



class CreateLocatorAtObject(object):
	'''
	'''
	def __init__(self):
		'''
		'''
		self.isLocator = lambda obj: self.getType(obj)=='locator'
		self.isGroup = lambda obj: all([type(c)==pm.nodetypes.Transform for c in obj.getChildren()])
		self.list = lambda x: list(x) if isinstance(x, (list, tuple, set, dict)) else [x] #assure that the arg is a list.


	def create_locator(self, scale=1):
		'''Create a locator with the given scale.
		:parameters:
			scale (int) = The desired scale of the locator.

		:return:
			(obj) locator
		'''
		loc = pm.spaceLocator()
		pm.scale(loc, scale, scale, scale) #scale the locator
		return loc


	def remove_locator(self, obj):
		'''Remove a parented locator from the child object.
		:parameters:
			obj (str)(obj)(list) = The child object or the locator itself.

		:return:
			(bool) True if successful
		'''
		if not self.isLocator(obj):
			try:
				obj = pm.listRelatives(obj, parent=1)[0]
				if not self.isLocator(obj):
					return False
			except IndexError as error:
				return False
		pm.ungroup(obj)
		pm.delete(obj)
		return True


	def formatName(self, name, stripTrailingInts=False, stripTrailingAlpha=False, strip='', suffix=''):
		'''
		:parameters:
			name (str)(obj) = The name string to format or the object itself (from which the name will be pulled).
			stripTrailingInts (bool) = Strip all trailing integers.
			stripTrailingAlpha (bool) = Strip all upper-case letters preceeded by an underscore.
			strip (str)(list) = Specific string(s) to strip. All occurances will be removed.
			suffix (str) = A suffix to apply to the end result.

		:return:
			(str)
		'''
		import re

		try:
			n = name.split('|')[-1]
		except Exception as error:
			n = name.name().split('|')[-1]

		for s in strip:
			n = n.replace(s, '')

		while ((n[-1]=='_' or n[-1].isdigit()) and stripTrailingInts) or ('_' in n and (n=='_' or n[-1].isupper())) and stripTrailingAlpha:

			if (n[-1]=='_' or n[-1].isdigit()) and stripTrailingInts: #trailing underscore and integers.
				n = re.sub(re.escape(n[-1:]) + '$', '', n)

			if ('_' in n and (n=='_' or n[-1].isupper())) and stripTrailingAlpha: #trailing underscore and uppercase alphanumeric char.
				n = re.sub(re.escape(n[-1:]) + '$', '', n)

		return n+suffix


	def unlockAttributes(self, obj, translate=False, rotate=False, scale=False):
		'''Extends the functionality of the 'lockAttributes' method to unlock.

		:parameters:
			obj (str)(obj)(list) = The object to lock/unlock attributes of.
			translate (bool) = Unlock the translate x,y,z values.
			rotate (bool) = Unlock the rotate x,y,z values.
			scale (bool) = Unlock the scale x,y,z values.
		'''
		self.lockAttributes(obj, translate=translate, rotate=rotate, scale=scale, _state=0)


	def lockAttributes(self, obj, translate=False, rotate=False, scale=False, _state=1):
		'''Lock the translate, rotate, and scale attributes for the given objects.

		:parameters:
			obj (str)(obj)(list) = The object to lock/unlock attributes of.
			translate (bool) = Lock the translate x,y,z values.
			rotate (bool) = Lock the rotate x,y,z values.
			scale (bool) = Lock the scale x,y,z values.
			_state (int) = Internal use. The lock state. A value of 0 unlocks the attributes. (default:1)
		'''
		if self.isLocator(obj):
			obj = pm.listRelatives(obj, children=1, type='transform')[0]

		if translate: #lock translation values
			[pm.setAttr(getattr(obj, attr), lock=_state) for attr in ('tx','ty','tz')] #pm.setAttr(obj[0].translate, lock=state)
		if rotate: #lock rotation values
			[pm.setAttr(getattr(obj, attr), lock=_state) for attr in ('rx','ry','rz')]
		if scale: #lock scale values
			[pm.setAttr(getattr(obj, attr), lock=_state) for attr in ('sx','sy','sz')]


	@staticmethod
	def getType(obj):
		'''Get the object type as a string.
		'''
		obj, *other = pm.ls(obj)
		try:
			return pm.listRelatives(obj, shapes=1)[0].type()
		except IndexError as error:
			return obj.type()


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


	def main(self, objects, parent=False, freezeTransforms=False, bakeChildPivot=False, grpSuffix='_GRP#', locSuffix='_LOC#', objSuffix='_GEO#', 
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

				loc = self.create_locator(scale)

				xmin, ymin, zmin, xmax, ymax, zmax = pm.exactWorldBoundingBox(vertices)
				x, y, z = pos = ((xmin + xmax) / 2, (ymin + ymax) / 2, (zmin + zmax) / 2)
				pm.move(x, y, z, loc)

			else: #object
				if remove:
					if pm.objExists(obj): #if the locator hasn't already been deleted by another child.
						self.unlockAttributes(obj, translate=1, rotate=1, scale=1) #unlock all.
						locator_removed = self.remove_locator(obj)
						if not locator_removed:
							pm.inViewMessage(statusMessage="Unable to remove locator for {}.".format(obj.name()), pos='topCenter', fade=True)
					continue

				loc = self.create_locator(scale)

				tempConst = pm.parentConstraint(obj, loc, maintainOffset=False)
				pm.delete(tempConst)

			try:
				if parent:
					origParent = pm.listRelatives(obj, parent=1)
					grpName = self.formatName(obj, stripTrailingInts=stripDigits, strip=(locSuffix, objSuffix), suffix=grpSuffix)
					grp = self.createGroup(obj, name=grpName, zeroTranslation=1, zeroRotation=1)
					pm.parent(obj, loc)
					pm.parent(loc, grp)
					pm.parent(grp, origParent)

				if freezeTransforms: #freeze transforms before baking pivot.
					self.unlockAttributes(obj, translate=1, rotate=1, scale=1) #assure attributes are unlocked.
					pm.makeIdentity(obj, apply=True, normal=1)
					pm.makeIdentity(loc, apply=True, normal=1) #1=the normals on polygonal objects will be frozen. 2=the normals on polygonal objects will be frozen only if its a non-rigid transformation matrix.

				pm.rename(loc, self.formatName(obj, stripTrailingInts=stripDigits, strip=(locSuffix, objSuffix, grpSuffix) if stripSuffix else '', suffix=locSuffix))
				pm.rename(obj, self.formatName(obj, stripTrailingInts=stripDigits, strip=(locSuffix, objSuffix, grpSuffix) if stripSuffix else '', suffix=objSuffix if not self.isLocator(obj) else locSuffix))

				self.lockAttributes(obj, translate=lockTranslate, rotate=lockRotation, scale=lockScale)

			except Exception as error:
				pm.delete(loc)
				raise (error)

		pm.undoInfo(closeChunk=1)









createLocatorAtObject = CreateLocatorAtObject().main

if __name__=='__main__':

	selection=pm.ls(sl=1)
	createLocatorAtObject(selection,
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