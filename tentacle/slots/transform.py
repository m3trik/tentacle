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
					sb (class instance) = The switchboard instance.  Allows access to ui and slot objects across modules.
					<name>_ui (ui object) = The ui object of <name>. ie. self.polygons_ui
					<widget> (registered widget) = Any widget previously registered in the switchboard module. ie. self.PushButton
				functions:
					current_ui (lambda function) = Returns the current ui if it is either the parent or a child ui for the class; else, return the parent ui. ie. self.current_ui()
					<name> (lambda function) = Returns the slot class instance of that name.  ie. self.polygons()
		'''
		dh = self.transform_ui.draggable_header
		dh.contextMenu.add(self.ComboBox, setObjectName='cmb000', setToolTip='')

		tb000 = self.transform_ui.tb000 #drop to grid.
		tb000.contextMenu.add('QComboBox', addItems=['Min','Mid','Max'], setObjectName='cmb004', setToolTip='Choose which point of the bounding box to align to.')
		tb000.contextMenu.add('QCheckBox', setText='Move to Origin', setObjectName='chk014', setChecked=True, setToolTip='Move to origin (xyz 0,0,0).')
		tb000.contextMenu.add('QCheckBox', setText='Center Pivot', setObjectName='chk016', setChecked=True, setToolTip='Center pivot on objects bounding box.')
		tb000.contextMenu.add('QCheckBox', setText='Freeze Transforms', setObjectName='chk017', setChecked=True, setToolTip='Reset the selected transform and all of its children down to the shape level.')

		tb001 = self.transform_ui.tb001
		tb001.contextMenu.add('QCheckBox', setText='X Axis', setObjectName='chk029', setDisabled=True, setToolTip='Align X axis')
		tb001.contextMenu.add('QCheckBox', setText='Y Axis', setObjectName='chk030', setDisabled=True, setToolTip='Align Y axis')
		tb001.contextMenu.add('QCheckBox', setText='Z Axis', setObjectName='chk031', setDisabled=True, setToolTip='Align Z axis')
		tb001.contextMenu.add('QCheckBox', setText='Between Two Components', setObjectName='chk013', setToolTip='Align the path along an edge loop between two selected vertices or edges.')
		tb001.contextMenu.add('QCheckBox', setText='Align Loop', setObjectName='chk007', setToolTip='Align entire edge loop from selected edge(s).')
		tb001.contextMenu.add('QCheckBox', setText='Average', setObjectName='chk006', setToolTip='Align to last selected object or average.')
		tb001.contextMenu.add('QCheckBox', setText='Auto Align', setObjectName='chk010', setChecked=True, setToolTip='')
		tb001.contextMenu.add('QCheckBox', setText='Auto Align: Two Axes', setObjectName='chk011', setToolTip='')

		tb002 = self.transform_ui.tb002
		tb002.contextMenu.add('QCheckBox', setText='Translate', setObjectName='chk032', setChecked=True, setToolTip='The translation will be changed to 0, 0, 0.')
		tb002.contextMenu.add('QCheckBox', setText='Rotate', setObjectName='chk033', setToolTip='The rotation will be changed to 0, 0, 0.')
		tb002.contextMenu.add('QCheckBox', setText='Scale', setObjectName='chk034', setChecked=True, setToolTip='The scale factor will be changed to 1, 1, 1.')
		tb002.contextMenu.add('QCheckBox', setText='Center Pivot', setObjectName='chk035', setChecked=True, setToolTip="Move the objects pivot to the center of it's bounding box.")

		cmb001 = self.transform_ui.cmb001
		cmb001.popupStyle = 'qmenu'
		cmb001.menu_.setTitle('Constaints')

		cmb003 = self.transform_ui.cmb003
		cmb003.popupStyle = 'qmenu'
		cmb003.menu_.setTitle('Snap')
		cmb003.menu_.add(self.CheckBox, setObjectName='chk021', setText='Move: <b>Off</b>', setTristate=True)
		cmb003.menu_.add('QDoubleSpinBox', setObjectName='s021', setPrefix='Increment:', setValue=0, setMinMax_='1.00-1000 step2.8125', setDisabled=True)
		cmb003.menu_.add(self.CheckBox, setObjectName='chk022', setText='Scale: <b>Off</b>', setTristate=True)
		cmb003.menu_.add('QDoubleSpinBox', setObjectName='s022', setPrefix='Increment:', setValue=0, setMinMax_='1.00-1000 step2.8125', setDisabled=True)
		cmb003.menu_.add(self.CheckBox, setObjectName='chk023', setText='Rotate: <b>Off</b>', setTristate=True)
		cmb003.menu_.add('QDoubleSpinBox', setObjectName='s023', setPrefix='Degrees:', setValue=0, setMinMax_='1.00-360 step2.8125', setDisabled=True)
		# self.connect_('chk021-23', 'stateChanged', lambda state: self.setWidgetKwargs('chk021-23', setText='Off'))
		self.sb.setSyncAttributesConnections(cmb003.menu_.chk023, self.transform_submenu_ui.chk023, attributes='setChecked')


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


	def chk021(self, state=None):
		'''Transform Tool Snap Settings: Move
		'''
		cmb = self.transform_ui.cmb003
		tri_state = cmb.menu_.chk021.checkState_()
		text = {0:'Move: <b>Off</b>', 1:'Move: <b>Relative</b>', 2:'Move: <b>Absolute</b>'}
		cmb.menu_.chk021.setText(text[tri_state])
		cmb.menu_.s021.setEnabled(tri_state)
		cmb.setCurrentText('Snap: <hl style="color:white;">Off</hl>') if not any((tri_state, cmb.menu_.chk022.isChecked(), cmb.menu_.chk023.isChecked())) else cmb.setCurrentText('Snap: <hl style="color:green;">On</hl>')

		self.setTransformSnap('move', tri_state)


	def chk022(self, state=None):
		'''Transform Tool Snap Settings: Scale
		'''
		cmb = self.transform_ui.cmb003
		tri_state = cmb.menu_.chk022.checkState_()
		text = {0:'Scale: <b>Off</b>', 1:'Scale: <b>Relative</b>', 2:'Scale: <b>Absolute</b>'}
		cmb.menu_.chk022.setText(text[tri_state])
		cmb.menu_.s022.setEnabled(tri_state)
		cmb.setCurrentText('Snap: <hl style="color:white;">Off</hl>') if not any((tri_state, cmb.menu_.chk021.isChecked(), cmb.menu_.chk023.isChecked())) else cmb.setCurrentText('Snap: <hl style="color:green;">On</hl>')

		self.setTransformSnap('scale', tri_state)


	def chk023(self, state=None):
		'''Transform Tool Snap Settings: Rotate
		'''
		cmb = self.transform_ui.cmb003
		tri_state = cmb.menu_.chk023.checkState_()
		text = {0:'Rotate: <b>Off</b>', 1:'Rotate: <b>Relative</b>', 2:'Rotate: <b>Absolute</b>'}
		cmb.menu_.chk023.setText(text[tri_state])
		cmb.menu_.s023.setEnabled(tri_state)
		cmb.setCurrentText('Snap: <hl style="color:white;">Off</hl>') if not any((tri_state, cmb.menu_.chk021.isChecked(), cmb.menu_.chk022.isChecked())) else cmb.setCurrentText('Snap: <hl style="color:green;">On</hl>')

		self.setTransformSnap('rotate', tri_state)









# -----------------------------------------------
# Notes
# -----------------------------------------------



# deprecated ------------------------------------

# def chk014(self, state=None):
	# 	'''Snap: Toggle Rotation
	# 	'''
	# 	cmb = self.transform_ui.cmb003

	# 	cmb.menu_.chk023.setChecked(True)
	# 	cmb.menu_.s023.setValue(11.25)
	# 	state = 1 if self.transform_submenu_ui.chk014.isChecked() else 0
	# 	self.chk023(state=state)