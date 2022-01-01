# !/usr/bin/python
# coding=utf-8
from slots.max import *



class Rendering(Slots_max):
	def __init__(self, *args, **kwargs):
		Slots_max.__init__(self, *args, **kwargs)

		ctx = self.rendering_ui.draggable_header.contextMenu
		ctx.add(self.tcl.wgts.ComboBox, setObjectName='cmb000', setToolTip='')

		cmb = self.rendering_ui.draggable_header.contextMenu.cmb000
		list_ = ['']
		cmb.addItems_(list_, '')


	def draggable_header(self, state=None):
		'''Context menu
		'''
		dh = self.rendering_ui.draggable_header


	def cmb000(self, index=-1):
		'''Editors
		'''
		cmb = self.rendering_ui.draggable_header.contextMenu.cmb000

		if index>0:
			text = cmb.items[index]
			if text=='':
				pass
			cmb.setCurrentIndex(0)


	def cmb001(self, index=-1):
		'''Render: camera
		'''
		cmb = self.rendering_ui.cmb001

		self.cams = [cam for cam in rt.cameras if 'Target' not in str(cam)]
		if self.cams:
			list_ = [str(cam.name) for cam in self.cams] #camera names
			cmb.addItems_(list_, clear=True)


	def b000(self):
		'''Render Current Frame
		'''
		cmb = self.rendering_ui.cmb001
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
print (__name__)
# -----------------------------------------------
# Notes
# -----------------------------------------------