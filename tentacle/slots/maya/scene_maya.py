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
		mtk.edittk.setCase(objects, case)


	def tb001(self, state=None):
		'''Convert Case
		'''
		tb = self.sb.scene.tb001

		alphanumeric = tb.ctxMenu.chk005.isChecked()
		stripTrailingInts = tb.ctxMenu.chk002.isChecked()
		stripTrailingAlpha = tb.ctxMenu.chk003.isChecked()
		reverse = tb.ctxMenu.chk004.isChecked()

		selection = pm.ls(sl=1, objectsOnly=1)
		mtk.edittk.setSuffixByObjLocation(selection, alphanumeric=alphanumeric, stripTrailingInts=stripTrailingInts, stripTrailingAlpha=stripTrailingAlpha, reverse=reverse)


	def b000(self):
		'''Rename
		'''
		find = self.sb.scene.t000.text() #an asterisk denotes startswith*, *endswith, *contains* 
		to = self.sb.scene.t001.text()
		regEx = self.sb.scene.t000.ctxMenu.chk001.isChecked()
		ignoreCase = self.sb.scene.t000.ctxMenu.chk000.isChecked()

		selection = pm.ls(sl=1)
		objects = selection if selection else pm.ls(objectsOnly=1)
		mtk.edittk.rename(objects, to, find, regEx=regEx, ignoreCase=ignoreCase)

# -----------------------------------------------









#module name
print (__name__)
# -----------------------------------------------
# Notes
# -----------------------------------------------