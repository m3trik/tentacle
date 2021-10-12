# !/usr/bin/python
# coding=utf-8
import os.path
from datetime import datetime

from max_init import *


class Scene(Init):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)

		self.scene_ui.t000.returnPressed.connect(self.t001) #preform rename on returnPressed


	def draggable_header(self, state=None):
		'''Context menu
		'''
		dh = self.scene_ui.draggable_header

		if state is 'setMenu':
			dh.contextMenu.add(wgts.ComboBox, setObjectName='cmb000', setToolTip='')
			return


	def cmb000(self, index=-1):
		'''Editors
		'''
		cmb = self.scene_ui.cmb000

		if index is 'setMenu':
			list_ = ['']
			cmb.addItems_(list_, '')
			return

		if index>0:
			text = cmb.items[index]
			if text=='':
				pass
			cmb.setCurrentIndex(0)


	def t000(self, state=None):
		'''Find
		'''
		t000 = self.scene_ui.t000

		if state is 'setMenu':
			t000.contextMenu.add('QCheckBox', setText='Ignore Case', setObjectName='chk000', setToolTip='Search case insensitive.')
			t000.contextMenu.add('QCheckBox', setText='Regular Expression', setObjectName='chk001', setToolTip='When checked, regular expression syntax is used instead of the default \'*\' and \'|\' wildcards.')
			return


	def t001(self, state=None):
		'''Replace
		'''
		t001 = self.scene_ui.t001

		if state is 'setMenu':
			return

		find = self.scene_ui.t000.text() #asterisk denotes startswith*, *endswith, *contains* 
		to = self.scene_ui.t001.text()
		regEx = self.scene_ui.t000.contextMenu.chk001.isChecked()
		ignoreCase = self.scene_ui.t000.contextMenu.chk000.isChecked()

		Scene.rename(find, to, regEx=regEx, ignoreCase=ignoreCase)


	def tb000(self, state=None):
		'''Convert Case
		'''
		tb = self.current_ui.tb000
		if state is 'setMenu':
			tb.menu_.add('QLineEdit', setPlaceholderText='Case', setText='capitalize', setObjectName='t004', setToolTip='Desired case using python case operators. valid: upper, lower, caplitalize, swapcase, title')
			return

		case = tb.menu_.t004.text().lower()

		selection = pm.ls(sl=1)
		objects = selection if selection else pm.ls(objectsOnly=1)
		Scene.setCase(objects, case)


	@staticmethod
	def rename(frm, to, regEx=False, ignoreCase=False):
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
		pm.undoInfo (openChunk=1)
		names = Init.findStrAndFormat(frm, to, [obj.name for obj in rt.objects], regEx=regEx, ignoreCase=ignoreCase) #[o for o in rt.objects if rt.matchPattern(o.name, pattern=f, ignoreCase=0)]
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
		pm.undoInfo (closeChunk=1)


	@staticmethod
	def setCase(objects=[], case='caplitalize'):
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
print(os.path.splitext(os.path.basename(__file__))[0])
# -----------------------------------------------
# Notes
# -----------------------------------------------