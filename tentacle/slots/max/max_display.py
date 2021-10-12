# !/usr/bin/python
# coding=utf-8
import os.path
import traceback

from max_init import *



class Display(Init):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)



	def draggable_header(self, state=None):
		'''Context menu
		'''
		dh = self.display_ui.draggable_header

		if state is 'setMenu':
			dh.contextMenu.add(wgts.ComboBox, setObjectName='cmb000', setToolTip='')
			return


	def cmb000(self, index=-1):
		'''Editors
		'''
		cmb = self.display_ui.cmb000

		if index is 'setMenu':
			list_ = ['']
			cmb.addItems_(list_, '')
			return

		if index>0:
			text = cmb.items[index]
			if text=='':
				pass
			cmb.setCurrentIndex(0)


	def b000(self):
		'''Set Wireframe color
		'''
		pm.mel.objectColorPalette()


	def b001(self):
		'''Toggle Visibility
		'''
		sel = [s for s in rt.getCurrentSelection()]

		for obj in sel:
			if obj.visibility == True:
				obj.visibility = False
			else:
				obj.visibility = True


	def b002(self):
		'''Hide Selected
		'''
		sel = [s for s in rt.getCurrentSelection()]
	
		for obj in sel:
			if not obj.isHiddenInVpt:
				obj.isHidden = True


	def b003(self):
		'''Show Selected
		'''
		sel = [s for s in rt.getCurrentSelection()]
	
		for obj in sel:
			if obj.isHiddenInVpt:
				obj.isHidden = False


	def b004(self):
		'''Show Geometry
		'''
		geometry = rt.geometry

		for obj in geometry:
			if obj.isHiddenInVpt:
				obj.isHidden = False


	def b005(self):
		'''Xray Selected
		'''
		sel = [s for s in rt.getCurrentSelection()]

		for s in sel:
			s.xray = True


	def b006(self):
		'''Un-Xray All
		'''
		geometry = [g for g in rt.geometry]

		for g in geometry:
			g.xray = False


	def b007(self):
		'''Xray Other
		'''
		sel = [s for s in rt.getCurrentSelection()]
		geometry = [g for g in rt.geometry]

		for g in geometry:
			if g not in sel:
				g.xray = True


	def b008(self):
		'''Filter Objects
		'''
		mel.eval("bt_filterActionWindow;")


	def b009(self):
		'''Override Material
		'''
		if self.display_ui.chk000.isChecked(): #override with UV checker material
			self.toggleMaterialOverride(checker=1)
		else:
			self.toggleMaterialOverride()


	def b010(self):
		''''''
		pass


	@Slots.message
	def b011(self):
		'''Toggle Component ID Display
		'''
		index = self.cycle([0,1,2,3,4], 'componentID')

		visible = pm.polyOptions (query=1, displayItemNumbers=1)
		dinArray = [[1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1]]

		if index == 4:
			i=0
			for _ in range(4):
				if visible[i] == True:
					pm.polyOptions (relative=1, displayItemNumbers=dinArray[i], activeObjects=1)
				i+=1

		if visible[index] != True and index != 4:
			pm.polyOptions (relative=1, displayItemNumbers=dinArray[index], activeObjects=1)

			i=0
			for _ in range(4):
				if visible[i] == True and i != index:
					pm.polyOptions (relative=1, displayItemNumbers=dinArray[i], activeObjects=1)
				i+=1

		if index == 0:
			return '<hl>Vertex IDs</hl>.' #[1,0,0,0]
		elif index == 1:
			return '<hl>Edge IDs</hl>.' #[0,1,0,0]
		elif index == 2:
			return '<hl>Face IDs</hl>.' #[0,0,1,0]
		elif index == 3:
			return '<hl>Component IDs (UV)</hl>.' #[0,0,0,1]
		elif index == 4:
			return 'Component ID <hl>Off</hl>.'


	def b012(self):
		'''Wireframe Non Active (Wireframe All But The Selected Item)
		'''
		viewport = rt.viewport.activeViewport

		state = self.cycle([0,1], 'wireframeInactive')

		if state:
			if not rt.viewport.isWire():
				self.maxUiSetChecked("415", 62, 163, True) #set viewport to wireframe
			self.maxUiSetChecked("40212", 62, 130, True) #Shade selected objects Checked
		else:
			self.maxUiSetChecked("40212", 62, 130, False) #Shade selected objects unchecked


	def b013(self):
		'''Viewport Configuration
		'''
		maxEval('actionMan.executeAction 0 "40023"')


	def b021(self):
		'''Template Selected
		'''
		sel = [s for s in rt.getCurrentSelection()]

		for obj in sel:
			if obj.isFrozen == True:
				obj.isFrozen = False
			else:
				obj.isFrozen = True


	def b024(self):
		'''Polygon Display Options
		'''
		mel.eval("CustomPolygonDisplayOptions")
		# mel.eval("polysDisplaySetup 1;")








#module name
print(os.path.splitext(os.path.basename(__file__))[0])
# -----------------------------------------------
# Notes
# -----------------------------------------------


