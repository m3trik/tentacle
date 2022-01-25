# !/usr/bin/python
# coding=utf-8
from slots import Slots



class Transform(Slots):
	'''
	'''
	def __init__(self, *args, **kwargs):
		'''
		:Parameters: 
			**kwargs (inherited from this class's respective slot child class, and originating from switchboard.setClassInstanceFromUiName)
				properties:
					tcl (class instance) = The tentacle stacked widget instance. ie. self.tcl
					<name> (ui object) = The ui of <name> ie. self.polygons for the ui of filename polygons. ie. self.polygons
				functions:
					current (lambda function) = Returns the current ui if it is either the parent or a child ui for the class; else, return the parent ui. ie. self.current()
					'<name>' (lambda function) = Returns the class instance of that name.  ie. self.polygons()
		'''
		ctx = self.transform_ui.draggable_header.contextMenu
		if not ctx.containsMenuItems:
			ctx.add(self.tcl.wgts.ComboBox, setObjectName='cmb000', setToolTip='')

		ctx = self.transform_ui.tb000.contextMenu #drop to grid.
		if not ctx.containsMenuItems:
			ctx.add('QComboBox', addItems=['Min','Mid','Max'], setObjectName='cmb004', setToolTip='Choose which point of the bounding box to align to.')
			ctx.add('QCheckBox', setText='Move to Origin', setObjectName='chk014', setChecked=True, setToolTip='Move to origin (xyz 0,0,0).')
			ctx.add('QCheckBox', setText='Center Pivot', setObjectName='chk016', setChecked=True, setToolTip='Center pivot on objects bounding box.')
			ctx.add('QCheckBox', setText='Freeze Transforms', setObjectName='chk017', setChecked=True, setToolTip='Reset the selected transform and all of its children down to the shape level.')

		ctx = self.transform_ui.tb001.contextMenu
		if not ctx.containsMenuItems:
			ctx.add('QCheckBox', setText='X Axis', setObjectName='chk029', setDisabled=True, setToolTip='Align X axis')
			ctx.add('QCheckBox', setText='Y Axis', setObjectName='chk030', setDisabled=True, setToolTip='Align Y axis')
			ctx.add('QCheckBox', setText='Z Axis', setObjectName='chk031', setDisabled=True, setToolTip='Align Z axis')
			ctx.add('QCheckBox', setText='Between Two Components', setObjectName='chk013', setToolTip='Align the path along an edge loop between two selected vertices or edges.')
			ctx.add('QCheckBox', setText='Align Loop', setObjectName='chk007', setToolTip='Align entire edge loop from selected edge(s).')
			ctx.add('QCheckBox', setText='Average', setObjectName='chk006', setToolTip='Align to last selected object or average.')
			ctx.add('QCheckBox', setText='Auto Align', setObjectName='chk010', setChecked=True, setToolTip='')
			ctx.add('QCheckBox', setText='Auto Align: Two Axes', setObjectName='chk011', setToolTip='')


	def draggable_header(self, state=None):
		'''Context menu
		'''
		dh = self.transform_ui.draggable_header


	def chk010(self, state=None):
		'''Align Vertices: Auto Align
		'''
		if self.transform_ui.tb001.contextMenu.chk010.isChecked():
			self.toggleWidgets(setDisabled='chk029-31')
		else:
			self.toggleWidgets(setEnabled='chk029-31')


	def chk014(self, state=None):
		'''Snap: Toggle Rotation
		'''
		cmb = self.transform_ui.cmb003

		cmb.menu_.chk023.setChecked(True)
		cmb.menu_.s023.setValue(11.25)
		state = 1 if self.transform_submenu_ui.chk014.isChecked() else 0
		self.chk023(state=state)


	def chk021(self, state=None):
		'''Transform Tool Snap Settings: Move
		'''
		cmb = self.transform_ui.cmb003
		text = {0:'Move: <b>Off</b>', 1:'Move: <b>Relative</b>', 2:'Move: <b>Absolute</b>'}

		cmb.menu_.chk021.setText(text[state])
		cmb.menu_.s021.setEnabled(state)
		pm.manipMoveContext('Move', edit=1, snap=False if state==0 else True, snapRelative=True if state==1 else False) #state: 0=off, 1=relative, 2=absolute
		pm.texMoveContext('texMoveContext', edit=1, snap=False if state==0 else True) #uv move context

		cmb.setCurrentText('Snap: <hl style="color:white;">Off</hl>') if not any((state, cmb.menu_.chk022.isChecked(), cmb.menu_.chk023.isChecked())) else cmb.setCurrentText('Snap: <hl style="color:green;">On</hl>')


	def chk022(self, state=None):
		'''Transform Tool Snap Settings: Scale
		'''
		cmb = self.transform_ui.cmb003
		text = {0:'Scale: <b>Off</b>', 1:'Scale: <b>Relative</b>', 2:'Scale: <b>Absolute</b>'}

		cmb.menu_.chk022.setText(text[state])
		cmb.menu_.s022.setEnabled(state)
		pm.manipScaleContext('Scale', edit=1, snap=False if state==0 else True, snapRelative=True if state==1 else False) #state: 0=off, 1=relative, 2=absolute
		pm.texScaleContext('texScaleContext', edit=1, snap=False if state==0 else True) #uv scale context

		cmb.setCurrentText('Snap: <hl style="color:white;">Off</hl>') if not any((state, cmb.menu_.chk021.isChecked(), cmb.menu_.chk023.isChecked())) else cmb.setCurrentText('Snap: <hl style="color:green;">On</hl>')


	def chk023(self, state=None):
		'''Transform Tool Snap Settings: Rotate
		'''
		cmb = self.transform_ui.cmb003
		text = {0:'Rotate: <b>Off</b>', 1:'Rotate: <b>Relative</b>', 2:'Rotate: <b>Absolute</b>'}

		cmb.menu_.chk023.setText(text[state])
		cmb.menu_.s023.setEnabled(state)
		pm.manipRotateContext('Rotate', edit=1, snap=False if state==0 else True, snapRelative=True if state==1 else False) #state: 0=off, 1=relative, 2=absolute
		pm.texRotateContext('texRotateContext', edit=1, snap=False if state==0 else True) #uv rotate context

		cmb.setCurrentText('Snap: <hl style="color:white;">Off</hl>') if not any((state, cmb.menu_.chk021.isChecked(), cmb.menu_.chk022.isChecked())) else cmb.setCurrentText('Snap: <hl style="color:green;">On</hl>')


