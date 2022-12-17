# !/usr/bin/python
# coding=utf-8
from tentacle.slots.maya import *
from tentacle.slots.scene import Scene


class Scene_maya(Scene, Slots_maya):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)

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
				pm.mel.eval('NodeEditorWindow;') #
			elif text=='Outlinder':
				pm.mel.eval('OutlinerWindow;') #
			elif text=='Content Browser':
				pm.mel.eval('ContentBrowserWindow;') #
			elif text=='Optimize Scene Size':
				pm.mel.eval('cleanUpScene 2;')
			elif text=='Prefix Hierarchy Names':
				pm.mel.eval('prefixHierarchy;') #Add a prefix to all hierarchy names.
			elif text=='Search and Replace Names':
				pm.mel.eval('SearchAndReplaceNames;') #performSearchReplaceNames 1; #Rename objects in the scene.
			cmb.setCurrentIndex(0)


	def tb000(self, state=None):
		'''Convert Case
		'''
		tb = self.sb.scene.tb000

		case = tb.ctxMenu.cmb001.currentText()

		selection = pm.ls(sl=1)
		objects = selection if selection else pm.ls(objectsOnly=1)
		self.setCase(objects, case)


	def tb001(self, state=None):
		'''Convert Case
		'''
		tb = self.sb.scene.tb001

		alphanumeric = tb.ctxMenu.chk005.isChecked()
		stripTrailingInts = tb.ctxMenu.chk002.isChecked()
		stripTrailingAlpha = tb.ctxMenu.chk003.isChecked()
		reverse = tb.ctxMenu.chk004.isChecked()

		selection = pm.ls(sl=1, objectsOnly=1)
		self.setSuffixByObjLocation(selection, alphanumeric=alphanumeric, stripTrailingInts=stripTrailingInts, stripTrailingAlpha=stripTrailingAlpha, reverse=reverse)


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


	@Slots_maya.undo
	def rename(self, frm, to, objects=[], regEx=False, ignoreCase=False):
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
				*to* - replace only.
				*to - replace suffix.
				**to - append suffix.
				to* - replace prefix.
				to** - append prefix.
			objects (list) = The objects to rename. If nothing is given, all scene objects will be renamed.
			regEx (bool) = If True, regular expression syntax is used instead of the default '*' and '|' modifiers.
			ignoreCase (bool) = Ignore case when searching. Applies only to the 'frm' parameter's search.

		ex. rename(r'Cube', '*001', regEx=True) #replace chars after frm on any object with a name that contains 'Cube'. ie. 'polyCube001' from 'polyCube'
		ex. rename(r'Cube', '**001', regEx=True) #append chars on any object with a name that contains 'Cube'. ie. 'polyCube1001' from 'polyCube1'
		'''
		# pm.undoInfo (openChunk=1)
		objects = pm.ls(objectsOnly=1) if not objects else objects

		#get the short names from the long in order to correctly format. ex. 'NUT_' from: 'CENTER_HINGE_FEMALE_GRP|NUT_'
		long_names = [obj.name() for obj in objects]
		short_names = [ii if ii else i for i, ii in self.splitAtChars(long_names)] #split the long names at the last '|' to get the short name.

		names = self.findStrAndFormat(frm, to, short_names, regEx=regEx, ignoreCase=ignoreCase, returnOldNames=True)
		print ('# Rename: Found {} matches. #'.format(len(names)))

		for i, (oldName, newName) in enumerate(names):
			oldName = long_names[i] #use the long name to reference the object instead.
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


	@Slots_maya.undo
	def setCase(self, objects=[], case='caplitalize'):
		'''Rename objects following the given case.

		:Parameters:
			objects (str)(list) = The objects to rename. default:all scene objects
			case (str) = Desired case using python case operators. 
				valid: 'upper', 'lower', 'caplitalize', 'swapcase' 'title'. default:'caplitalize'

		ex. call: setCase(pm.ls(sl=1), 'upper')
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


	@Slots_maya.undo
	def setSuffixByObjLocation(self, objects, alphanumeric=False, stripTrailingInts=True, stripTrailingAlpha=True, reverse=False):
		'''Rename objects with a suffix defined by its location from origin.

		:Parameters:
			objects (str)(int)(list) = The object(s) to rename.
			alphanumeric (str) = When True use an alphanumeric character as a suffix when there is less than 26 objects else use integers.
			stripTrailingInts (bool) = Strip any trailing integers. ie. 'cube123'
			stripTrailingAlpha (bool) = Strip any trailing uppercase alphanumeric chars that are prefixed with an underscore.  ie. 'cube_A'
			reverse (bool) = Reverse the naming order. (Farthest object first)
		'''
		import string
		import re

		length = len(objects)
		if alphanumeric:
			if length<=26:
				suffix = string.ascii_lowercase.upper()
		else:
			suffix = [str(n).zfill(len(str(length))) for n in range(length)]

		ordered_objs = self.sb.transform.slots.orderByDistance(objects, reverse=reverse)

		newNames={} #the object with the new name set as a key.
		for n, obj in enumerate(ordered_objs):

			current_name = obj.name()

			while ((current_name[-1]=='_' or current_name[-1].isdigit()) and stripTrailingInts) or ((current_name[-2]=='_' and current_name[-1].isupper()) and stripTrailingAlpha):
				if (current_name[-2]=='_' and current_name[-1].isupper()) and stripTrailingAlpha: #trailing underscore and uppercase alphanumeric char.
					current_name = re.sub(re.escape(current_name[-2:]) + '$', '', current_name)

				if (current_name[-1]=='_' or current_name[-1].isdigit()) and stripTrailingInts: #trailing underscore and integers.
					current_name = re.sub(re.escape(current_name[-1:]) + '$', '', current_name)

			newNames[obj] = current_name+'_'+suffix[n]

		#rename all with a placeholder first so that there are no conflicts.
		[pm.rename(obj, 'p0000000000') for obj in ordered_objs]
		#rename all with the new names.
		[pm.rename(obj, newNames[obj]) for obj in ordered_objs]









#module name
print (__name__)
# -----------------------------------------------
# Notes
# -----------------------------------------------