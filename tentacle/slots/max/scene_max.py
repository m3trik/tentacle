# !/usr/bin/python
# coding=utf-8
from tentacle.slots.max import *
from tentacle.slots.scene import Scene



class Scene_max(Scene, Slots_max):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)

		cmb = self.sb.scene.draggable_header.ctxMenu.cmb000
		items = []
		cmb.addItems_(items, 'Scene Editors')


	def cmb000(self, index=-1):
		'''Editors
		'''
		cmb = self.sb.scene.draggable_header.ctxMenu.cmb000

		if index>0:
			text = cmb.items[index]
			if text=='':
				pass
			cmb.setCurrentIndex(0)


	def tb000(self, state=None):
		'''Convert Case
		'''
		tb = self.sb.scene.tb000

		case = tb.ctxMenu.cmb001.currentText()

		selection = pm.ls(sl=1)
		objects = selection if selection else pm.ls(objectsOnly=1)
		self.setCase(objects, case)


	def b000(self):
		'''Rename
		'''
		find = self.sb.scene.t000.text() #an asterisk denotes startswith*, *endswith, *contains* 
		to = self.sb.scene.t001.text()
		regEx = self.sb.scene.t000.ctxMenu.chk001.isChecked()
		ignoreCase = self.sb.scene.t000.ctxMenu.chk000.isChecked()

		selection = pm.ls(sl=1)
		objects = selection if selection else pm.ls(objectsOnly=1)
		self.rename(find, to, objects, regEx=regEx, ignoreCase=ignoreCase)


	def rename(self, frm, to, regEx=False, ignoreCase=False):
		'''Rename scene objects.

		:Parameters:
			frm (str) = Current name. An asterisk denotes startswith*, *endswith, *contains*, and multiple search strings can be separated by pipe ('|') chars.
				frm - Search exact.
				*frm* - Search contains chars.
				*frm - Search endswith chars.
				frm* - Search startswith chars.
				frm|frm - Search any of.  can be used in conjuction with other modifiers.
			to (str) = Desired name: An optional asterisk modifier can be used for formatting
				to - replace all.
				*to* - replace only 'frm'.
				*to - replace suffix.
				**to - append suffix.
				to* - replace prefix.
				to** - append prefix.
			regEx (bool) = If True, regular expression syntax is used instead of the default '*' and '|' modifiers.
			ignoreCase (bool) = Ignore case when searching. Applies only to the 'frm' parameter's search.

		ex. rename(r'Cube', '*001', regEx=True) #replace chars after frm on any object with a name that contains 'Cube'. ie. 'polyCube001' from 'polyCube'
		ex. rename(r'Cube', '**001', regEx=True) #append chars on any object with a name that contains 'Cube'. ie. 'polyCube1001' from 'polyCube1'
		'''
		names = self.findStrAndFormat(frm, to, [obj.name for obj in rt.objects], regEx=regEx, ignoreCase=ignoreCase, returnOldNames=True) #[o for o in rt.objects if rt.matchPattern(o.name, pattern=f, ignoreCase=0)]
		print ('# Rename: Found {} matches. #'.format(len(names)))

		for oldName, newName in names:
			try:
				n = rt.uniqueName(oldName, newName) #assure the object name is unique.
				oldName.name = n #Rename the object with the new name
				if not n==newName:
					print ('# Warning: Attempt to rename "{}" to "{}" failed. Renamed instead to "{}". #'.format(oldName, newName, n))
				else:
					print ('# Result: Successfully renamed "{}" to "{}". #'.format(oldName, newName))

			except Exception as e:
				print ('# Error: Attempt to rename "{}" to "{}" failed. {} #'.format(oldName, newName, str(e).rstrip()))


	def setCase(self, objects=[], case='caplitalize'):
		'''Rename objects following the given case.

		:Parameters:
			objects (str)(list) = The objects to rename. default:all scene objects
			case (str) = Desired case using python case operators. 
				valid: 'upper', 'lower', 'caplitalize', 'swapcase' 'title'. default:'caplitalize'

		ex. call: setCase(pm.ls(sl=1), 'upper')
		'''
		for obj in objects:
			name = obj.name
			newName = getattr(name, case)()
			try:
				name = newName
			except Exception as error:
				if pm.ls(obj, readOnly=True): #ignore read-only errors.
					print (name+': ', error)









#module name
print (__name__)
# -----------------------------------------------
# Notes
# -----------------------------------------------