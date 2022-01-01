# !/usr/bin/python
# coding=utf-8
from slots.maya import *



class Display(Slots_maya):
	def __init__(self, *args, **kwargs):
		Slots_maya.__init__(self, *args, **kwargs)

		ctx = self.display_ui.draggable_header.contextMenu
		ctx.add(self.tcl.wgts.ComboBox, setObjectName='cmb000', setToolTip='')

		cmb = self.display_ui.draggable_header.contextMenu.cmb000
		list_ = ['']
		cmb.addItems_(list_, '')


	def draggable_header(self, state=None):
		'''Context menu
		'''
		dh = self.display_ui.draggable_header


	def cmb000(self, index=-1):
		'''Editors
		'''
		cmb = self.display_ui.draggable_header.contextMenu.cmb000

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
		mel.eval('ToggleVisibilityAndKeepSelection();')


	def b002(self):
		'''Hide Selected
		'''
		mel.eval('HideSelectedObjects;')


	def b003(self):
		'''Show Selected
		'''
		mel.eval('ShowSelectedObjects;')


	def b004(self):
		'''Show Geometry
		'''
		mel.eval('hideShow -geometry -show;')


	def b005(self):
		'''Xray Selected
		'''
		mel.eval('''
		string $sel[] = `ls -sl -dag -s`;
		for ($object in $sel) 
			{
			int $xState[] = `displaySurface -query -xRay $object`;
			displaySurface -xRay ( !$xState[0] ) $object;
			}
		''')


	def b006(self):
		'''Un-Xray All
		'''
		mel.eval('''
		string $scene[] = `ls -visible -flatten -dag -noIntermediate -type surfaceShape`;
		for ($object in $scene)
			{
			int $state[] = `displaySurface -query -xRay $object`;
			if ($state[0] == 1)
				{
				displaySurface -xRay 0 $object;
				}
			}
		''')


	def b007(self):
		'''Xray Other
		'''
		mel.eval('''
		//xray all except currently selected
		{
		string $scene[] = `ls -visible -flatten -dag -noIntermediate -type surfaceShape`;
		string $selection[] = `ls -selection -dagObjects -shapes`;
		for ($object in $scene)
			{
			if (!stringArrayContains ($object, $selection))
				{
				int $state[] = `displaySurface -query -xRay $object`;
				displaySurface -xRay ( !$state[0] ) $object;
				}
			}
		}
		''')


	def b008(self):
		'''Filter Objects
		'''
		mel.eval("bt_filterActionWindow;")


	def b009(self):
		'''Toggle Material Override
		'''
		from maya.cmds import getPanel #pymel getPanel is broken in ver: 2022.
		currentPanel = getPanel(withFocus=True)
		state = pm.modelEditor(currentPanel, query=1, useDefaultMaterial=1)
		pm.modelEditor(currentPanel, edit=1, useDefaultMaterial=not state)
		self.viewPortMessage('Default Material Override: <hl>{}</hl>.'.format(state))


	def b010(self):
		'''
		'''
		pass


	@Slots.message
	def b011(self):
		'''Toggle Component Id Display
		'''
		index = self.cycle([0,1,2,3,4], 'componentID')

		visible = pm.polyOptions(query=1, displayItemNumbers=1)
		if not visible:
			return '# Error: Nothing selected. #'
		dinArray = [(1,0,0,0),(0,1,0,0),(0,0,1,0),(0,0,0,1)]

		if index==4:
			i=0
			for _ in range(4):
				if visible[i]==True:
					pm.polyOptions(relative=1, displayItemNumbers=dinArray[i], activeObjects=1)
				i+=1

		elif visible[index]!=True and index!=4:
			pm.polyOptions(relative=1, displayItemNumbers=dinArray[index], activeObjects=1)

			i=0
			for _ in range(4):
				if visible[i]==True and i!=index:
					pm.polyOptions(relative=1, displayItemNumbers=dinArray[i], activeObjects=1)
				i+=1

		if index==0:
			self.viewPortMessage("[1,0,0,0] <hl>vertIDs</hl>.")
		elif index==1:
			self.viewPortMessage("[0,1,0,0] <hl>edgeIDs</hl>.")
		elif index==2:
			self.viewPortMessage("[0,0,1,0] <hl>faceIDs</hl>.")
		elif index==3:
			self.viewPortMessage("[0,0,0,1] <hl>compIDs(UV)</hl>.")
		elif index==4:
			self.viewPortMessage("component ID <hl>Off</hl>.")


	def b012(self):
		'''Wireframe Non Active (Wireframe All But The Selected Item)
		'''
		current_panel = pm.getPanel (withFocus=1)
		state = pm.modelEditor (current_panel, query=1, activeOnly=1)
		pm.modelEditor (current_panel, edit=1, activeOnly=not state)


	def b021(self):
		'''Template Selected
		'''
		pm.toggle(template=1) #pm.toggle(template=1, query=1)









#module name
print (__name__)
# -----------------------------------------------
# Notes
# -----------------------------------------------
	
