# !/usr/bin/python
# coding=utf-8
# from __future__ import print_function, absolute_import
from builtins import super
import os.path

from max_init import *



class Rendering(Init):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)

		# #checkable comboBox not working
		# comboBox = self.CheckableComboBox(self.rendering_ui.cmb000)
		# for num in range(6):
		# 	comboBox.addItem("checkbox " + str(num))
		# comboBox.checkIndex(1)
		# comboBox.checkIndex(2)


	def draggable_header(self, state=None):
		'''Context menu
		'''
		dh = self.rendering_ui.draggable_header

		if state is 'setMenu':
			dh.contextMenu.add(wgts.ComboBox, setObjectName='cmb001', setToolTip='')
			return


	def cmb001(self, index=-1):
		'''Editors
		'''
		cmb = self.rendering_ui.cmb001

		if index is 'setMenu':
			list_ = ['']
			cmb.addItems_(list_, '')
			return

		if index>0:
			text = cmb.items[index]
			if text=='':
				pass
			cmb.setCurrentIndex(0)


	def cmb000(self, index=-1):
		'''Render: camera
		'''
		cmb = self.rendering_ui.cmb000

		if index is 'setMenu':
			return

		self.cams = [cam for cam in rt.cameras if 'Target' not in str(cam)]
		if self.cams:
			list_ = [str(cam.name) for cam in self.cams] #camera names
			cmb.addItems_(list_, clear=True)


	def b000(self):
		'''Render Current Frame
		'''
		cmb = self.rendering_ui.cmb000
		index = cmb.currentIndex()

		try:
			rt.render (camera=self.cams[index]) #render with selected camera
		except:
			rt.render()


	def b001(self):
		'''Open Render Settings Window
		'''
		maxEval('unifiedRenderGlobalsWindow;')


	def b002(self):
		'''Redo Previous Render
		'''
		pass


	def b003(self):
		'''Editor: Render Setup
		'''
		maxEval('max render scene')


	def b004(self):
		'''Editor: Rendering Flags
		'''
		maxEval('renderFlagsWindow;')


	def b005(self):
		'''Apply Vray Attributes To Selected Objects
		'''
		selection = pm.ls(selection=1)
		currentID=1
		for obj in selection:
			# get renderable shape nodes relative to transform, iterate through and apply subdivision
			shapes = pm.listRelatives(obj,s=1,ni=1)
			if shapes:
				for shape in shapes:
					mel.eval ("vray addAttributesFromGroup "+shape+" vray_subdivision 1;")
					mel.eval ("vray addAttributesFromGroup "+shape+" vray_subquality 1;")
			# apply object ID to xform. i don't like giving individual shapes IDs.
			mel.eval ("vray addAttributesFromGroup "+obj+" vray_objectID 1;")
			pm.setAttr(obj+'.vrayObjectID',currentID)
			currentID+=1


	@Slots.message
	def b006(self):
		'''Load Vray Plugin
		'''
		vray = ['vrayformaya.mll','vrayformayapatch.mll']
		if pm.pluginInfo ('vrayformaya.mll', query=1, loaded=1):
			try:
				pm.unloadPlugin(vray)
			except:
				pm.unloadPlugin(vray, force=1)
				return 'Result: Force unloadPlugin:'+str(vray)
		else:
			pm.loadPlugin (vray)








#module name
print(os.path.splitext(os.path.basename(__file__))[0])
# -----------------------------------------------
# Notes
# -----------------------------------------------