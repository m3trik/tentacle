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
		self.unlock_attrs = lambda obj: self.set_lock_state(obj, translate=1, rotate=1, scale=1, state=0)
		self.list_ = lambda x: list(x) if isinstance(x, (list, tuple, set, dict)) else [x] #assure that the arg is a list.


	def create_locator(self, scale=1):
		'''
		'''
		loc = pm.spaceLocator()
		pm.scale(loc, scale, scale, scale) #scale the locator
		return loc


	def remove_locator(self, obj):
		'''
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


	def set_lock_state(self, obj, translate=False, rotate=False, scale=False, state=1):
		'''
		'''
		if self.isLocator(obj):
			obj = pm.listRelatives(obj, children=1, type='transform')[0]

		if translate: #lock translation values
			[pm.setAttr(getattr(obj, attr), lock=state) for attr in ('tx','ty','tz')] #pm.setAttr(obj[0].translate, lock=state)
		if rotate: #lock rotation values
			[pm.setAttr(getattr(obj, attr), lock=state) for attr in ('rx','ry','rz')]
		if scale: #lock scale values
			[pm.setAttr(getattr(obj, attr), lock=state) for attr in ('sx','sy','sz')]


	def format_name(self, name, stripTrailingInts=False, stripTrailingAlpha=False, strip='', suffix=''):
		'''
		:parameters:
			name (str)(obj) = The string to format or the object itself.
			stripTrailingInts (bool) = 
			stripTrailingAlpha (bool) = 
			strip (str)(list) = 
			suffix (str) = 
		'''
		import re

		try:
			n = name.split('|')[-1]
		except Exception as error:
			n = name.name().split('|')[-1]

		n = ''.join([n.replace(s, '') for s in self.list_(strip)])

		while ((n[-1]=='_' or n[-1].isdigit()) and stripTrailingInts) or ('_' in n and (n=='_' or n[-1].isupper())) and stripTrailingAlpha:

			if (n[-1]=='_' or n[-1].isdigit()) and stripTrailingInts: #trailing underscore and integers.
				n = re.sub(re.escape(n[-1:]) + '$', '', n)

			if ('_' in n and (n=='_' or n[-1].isupper())) and stripTrailingAlpha: #trailing underscore and uppercase alphanumeric char.
				n = re.sub(re.escape(n[-1:]) + '$', '', n)

		return n+suffix


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
	def createGroup(objects, name=''):
		'''
		'''
		grp = pm.group(empty=True, name=name)
		pm.parent(grp, objects)

		for axis in ('X', 'Y', 'Z'):
			for transform in ('.translate', '.rotate'):
				pm.setAttr(grp + transform + axis, 0)

		pm.parent(grp, world=True)
		return grp


	def main(self, objects, parent=False, freezeTransforms=False, bakeChildPivot=False, locSuffix='_LOC#', objSuffix='_GEO#', 
		stripDigits=False, stripSuffix=False, scale=1, lockTranslate=False, lockRotation=False, lockScale=False, remove=False):
		'''Create locators with the same transforms as any selected object(s).
		If there are vertices selected it will create a locator at the center of the selected vertices bounding box.

		:Parameters:
			objects (str)(obj)(list) = A list of objects, or an object name to create locators at.
			parent (bool) = Parent the object to the locator. (default=False)
			freezeTransforms (bool) = Freeze transforms on the locator. (default=True)
			bakeChildPivot (bool) = Bake pivot positions on the child object. (default=True)
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
						self.unlock_attrs(obj) #unlock all.
						self.remove_locator(obj)
					continue

				loc = self.create_locator(scale)

				tempConst = pm.parentConstraint(obj, loc, maintainOffset=False)
				pm.delete(tempConst)

			try:
				objParent = pm.listRelatives(obj, parent=1)
				if not objParent:
					n = self.format_name(obj, stripTrailingInts=stripDigits, strip=(locSuffix, objSuffix), suffix='_GRP')
					objParent = self.createGroup(obj, name=n)
				if parent:
					pm.parent(obj, loc)
					if objParent:
						pm.parent(loc, objParent)

				if freezeTransforms: #freeze transforms before baking pivot.
					self.unlock_attrs(obj) #assure attributes are unlocked.
					pm.makeIdentity(obj, apply=True, normal=1)
					pm.makeIdentity(loc, apply=True, normal=1) #1=the normals on polygonal objects will be frozen. 2=the normals on polygonal objects will be frozen only if its a non-rigid transformation matrix.

				pm.rename(loc, self.format_name(obj, stripTrailingInts=stripDigits, strip=(locSuffix, objSuffix), suffix=locSuffix))
				pm.rename(obj, self.format_name(obj, stripTrailingInts=stripDigits, strip=(locSuffix, objSuffix), suffix=objSuffix if not self.isLocator(obj) else locSuffix))

				self.set_lock_state(obj, translate=lockTranslate, rotate=lockRotation, scale=lockScale, state=1)

			except Exception as error:
				print ('# Error: {}: {} #'.format(obj.name(), error))
				pm.delete(loc)

		pm.undoInfo(closeChunk=1)









createLocatorAtObject = CreateLocatorAtObject().main

if __name__=='__main__':

	selection=pm.ls(sl=1)
	createLocatorAtObject(selection,
		parent=1,
		freezeTransforms=1,
		bakeChildPivot=1,
		locSuffix='_LCTR',
		objSuffix='_GEO',
		stripDigits=1,
		stripSuffix=1,
		scale=1,
		lockTranslate=0,
		lockRotation=0,
		lockScale=0,
		remove=0,
	)