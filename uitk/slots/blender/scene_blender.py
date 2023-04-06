# !/usr/bin/python
# coding=utf-8
from uitk.slots.blender import *
from uitk.slots.scene import Scene



class Scene_blender(Scene, Slots_blender):
	def __init__(self, *args, **kwargs):
		Slots_blender.__init__(self, *args, **kwargs)
		Scene.__init__(self, *args, **kwargs)

		cmb = self.sb.scene.draggable_header.ctxMenu.cmb000
		items = ['Node Editor', 'Outlinder', 'Content Browser', 'Optimize Scene Size', 'Prefix Hierarchy Names', 'Search and Replace Names']
		cmb.addItems_(items, 'Maya Scene Editors')


	def cmb000(self, index=-1):
		'''Editors
		'''
		cmb = self.sb.scene.draggable_header.ctxMenu.cmb000

		if index>0:
			text = cmb.items[index]
			if text=='Node Editor':
				mel.eval('NodeEditorWindow;') #
			elif text=='Outlinder':
				mel.eval('OutlinerWindow;') #
			elif text=='Content Browser':
				mel.eval('ContentBrowserWindow;') #
			elif text=='Optimize Scene Size':
				mel.eval('cleanUpScene 2;')
			elif text=='Prefix Hierarchy Names':
				mel.eval('prefixHierarchy;') #Add a prefix to all hierarchy names.
			elif text=='Search and Replace Names':
				mel.eval('SearchAndReplaceNames;') #performSearchReplaceNames 1; #Rename objects in the scene.
			cmb.setCurrentIndex(0)


	def tb000(self, state=None):
		'''Convert Case
		'''
		tb = self.sb.scene.tb000

		case = tb.ctxMenu.cmb001.currentText()

		selection = pm.ls(sl=1)
		objects = selection if selection else pm.ls(objectsOnly=1)
		self.setCase(objects, case)


	@Slots_blender.undoChunk
	def rename(self, frm, to, objects=[], regEx=False, ignoreCase=False):
		'''Rename scene objects.

		Parameters:
			frm (str): Current name. An asterisk denotes startswith*, *endswith, *contains*, and multiple search strings can be separated by pipe ('|') chars.
				frm - Search exact.
				*frm* - Search contains chars.
				*frm - Search endswith chars.
				frm* - Search startswith chars.
				frm|frm - Search any of.  can be used in conjuction with other modifiers.
			to (str): Desired name: An optional asterisk modifier can be used for formatting
				to - replace all.
				*to* - replace only.
				*to - replace suffix.
				**to - append suffix.
				to* - replace prefix.
				to** - append prefix.
			objects (list): The objects to rename. If nothing is given, all scene objects will be renamed.
			regEx (bool): If True, regular expression syntax is used instead of the default '*' and '|' modifiers.
			ignoreCase (bool): Ignore case when searching. Applies only to the 'frm' parameter's search.

		ex. rename(r'Cube', '*001', regEx=True) #replace chars after frm on any object with a name that contains 'Cube'. ie. 'polyCube001' from 'polyCube'
		ex. rename(r'Cube', '**001', regEx=True) #append chars on any object with a name that contains 'Cube'. ie. 'polyCube1001' from 'polyCube1'
		'''
		# pm.undoInfo (openChunk=1)
		objects = pm.ls(objectsOnly=1) if not objects else objects
		names = self.findStrAndFormat([obj.name() for obj in objects], to, frm, regEx=regEx, ignoreCase=ignoreCase, returnOldNames=True)
		print ('# Rename: Found {} matches. #'.format(len(names)))

		for oldName, newName in names:
			try:
				if pm.objExists(oldName):
					n = pm.rename(oldName, newName) #Rename the object with the new name
					if not n==newName:
						print ('# Warning: Attempt to rename "{}" to "{}" failed. Renamed instead to "{}". #'.format(oldName, newName, n))
					else:
						print ('# Result: Successfully renamed "{}" to "{}". #'.format(oldName, newName))

			except Exception as e:
				if not pm.ls(oldName, readOnly=True)==[]: #ignore read-only errors.
					print ('# Error: Attempt to rename "{}" to "{}" failed. {} #'.format(oldName, newName, str(e).rstrip()))
		# pm.undoInfo (closeChunk=1)


	@Slots_blender.undoChunk
	def setCase(self, objects=[], case='caplitalize'):
		'''Rename objects following the given case.

		Parameters:
			objects (str/list): The objects to rename. default:all scene objects
			case (str): Desired case using python case operators. 
				valid: 'upper', 'lower', 'caplitalize', 'swapcase' 'title'. default:'caplitalize'

		Example: setCase(pm.ls(sl=1), 'upper')
		'''
		# pm.undoInfo(openChunk=1)
		for obj in pm.ls(objects):
			name = obj.name()

			newName = getattr(name, case)()
			try:
				pm.rename(name, newName)
			except Exception as error:
				if not pm.ls(obj, readOnly=True)==[]: #ignore read-only errors.
					print (name+': ', error)
		# pm.undoInfo(closeChunk=1)









#module name
print (__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------