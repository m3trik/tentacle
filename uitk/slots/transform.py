# !/usr/bin/python
# coding=utf-8
from uitk.slots import Slots



class Transform(Slots):
	'''
	'''
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		'''
		'''
		dh = self.sb.transform.draggable_header
		dh.ctxMenu.add(self.sb.ComboBox, setObjectName='cmb000', setToolTip='')

		tb000 = self.sb.transform.tb000 #drop to grid.
		tb000.ctxMenu.add('QComboBox', addItems=['Min','Mid','Max'], setObjectName='cmb004', setToolTip='Choose which point of the bounding box to align to.')
		tb000.ctxMenu.add('QCheckBox', setText='Move to Origin', setObjectName='chk014', setChecked=True, setToolTip='Move to origin (xyz 0,0,0).')
		tb000.ctxMenu.add('QCheckBox', setText='Center Pivot', setObjectName='chk016', setChecked=True, setToolTip='Center pivot on objects bounding box.')
		tb000.ctxMenu.add('QCheckBox', setText='Freeze Transforms', setObjectName='chk017', setChecked=True, setToolTip='Reset the selected transform and all of its children down to the shape level.')

		tb001 = self.sb.transform.tb001
		tb001.ctxMenu.add('QCheckBox', setText='X Axis', setObjectName='chk029', setDisabled=True, setToolTip='Align X axis')
		tb001.ctxMenu.add('QCheckBox', setText='Y Axis', setObjectName='chk030', setDisabled=True, setToolTip='Align Y axis')
		tb001.ctxMenu.add('QCheckBox', setText='Z Axis', setObjectName='chk031', setDisabled=True, setToolTip='Align Z axis')
		tb001.ctxMenu.add('QCheckBox', setText='Between Two Components', setObjectName='chk013', setToolTip='Align the path along an edge loop between two selected vertices or edges.')
		tb001.ctxMenu.add('QCheckBox', setText='Align Loop', setObjectName='chk007', setToolTip='Align entire edge loop from selected edge(s).')
		tb001.ctxMenu.add('QCheckBox', setText='Average', setObjectName='chk006', setToolTip='Align to last selected object or average.')
		tb001.ctxMenu.add('QCheckBox', setText='Auto Align', setObjectName='chk010', setChecked=True, setToolTip='')
		tb001.ctxMenu.add('QCheckBox', setText='Auto Align: Two Axes', setObjectName='chk011', setToolTip='')

		tb002 = self.sb.transform.tb002
		tb002.ctxMenu.add('QCheckBox', setText='Translate', setObjectName='chk032', setChecked=True, setToolTip='The translation will be changed to 0, 0, 0.')
		tb002.ctxMenu.add('QCheckBox', setText='Rotate', setObjectName='chk033', setToolTip='The rotation will be changed to 0, 0, 0.')
		tb002.ctxMenu.add('QCheckBox', setText='Scale', setObjectName='chk034', setChecked=True, setToolTip='The scale factor will be changed to 1, 1, 1.')
		tb002.ctxMenu.add('QCheckBox', setText='Center Pivot', setObjectName='chk035', setChecked=True, setToolTip="Move the objects pivot to the center of it's bounding box.")

		cmb001 = self.sb.transform.cmb001
		cmb001.popupStyle = 'qmenu'
		cmb001.menu_.setTitle('Constaints')

		cmb003 = self.sb.transform.cmb003
		cmb003.popupStyle = 'qmenu'
		cmb003.menu_.setTitle('Snap')
		cmb003.menu_.add(self.sb.CheckBox, setObjectName='chk021', setText='Snap Move: Off', setTristate=True)
		cmb003.menu_.add('QDoubleSpinBox', setObjectName='s021', setPrefix='Increment:', setValue=0, setMinMax_='1.0-1000 step1', setDisabled=True)
		cmb003.menu_.add(self.sb.CheckBox, setObjectName='chk022', setText='Snap Scale: Off', setTristate=True)
		cmb003.menu_.add('QDoubleSpinBox', setObjectName='s022', setPrefix='Increment:', setValue=0, setMinMax_='1.0-1000 step1', setDisabled=True)
		cmb003.menu_.add(self.sb.CheckBox, setObjectName='chk023', setText='Snap Rotate: Off', setTristate=True)
		cmb003.menu_.add('QDoubleSpinBox', setObjectName='s023', setPrefix='Degrees:', setValue=0, setMinMax_='1.40625-360 step1.40625', setDisabled=True)


	def draggable_header(self, state=None):
		'''Context menu
		'''
		dh = self.sb.transform.draggable_header


	def chk010(self, state=None):
		'''Align Vertices: Auto Align
		'''
		if self.sb.transform.tb001.ctxMenu.chk010.isChecked():
			self.sb.toggleWidgets(setDisabled='chk029-31')
		else:
			self.sb.toggleWidgets(setEnabled='chk029-31')


	def chk021(self, state=None):
		'''Transform Tool Snap Settings: Move
		'''
		cmb = self.sb.transform.cmb003
		tri_state = cmb.menu_.chk021.checkState_()
		text = {0:'Snap Move: Off', 1:'Snap Move: Relative', 2:'Snap Move: Absolute'}
		cmb.menu_.chk021.setText(text[tri_state])
		cmb.menu_.s021.setEnabled(tri_state)
		cmb.setCurrentText('Snap: OFF') if not any((tri_state, cmb.menu_.chk022.isChecked(), cmb.menu_.chk023.isChecked())) else cmb.setCurrentText('Snap: ON')

		self.setTransformSnap('move', tri_state)


	def chk022(self, state=None):
		'''Transform Tool Snap Settings: Scale
		'''
		cmb = self.sb.transform.cmb003
		tri_state = cmb.menu_.chk022.checkState_()
		text = {0:'Snap Scale: Off', 1:'Snap Scale: Relative', 2:'Snap Scale: Absolute'}
		cmb.menu_.chk022.setText(text[tri_state])
		cmb.menu_.s022.setEnabled(tri_state)
		cmb.setCurrentText('Snap: OFF') if not any((tri_state, cmb.menu_.chk021.isChecked(), cmb.menu_.chk023.isChecked())) else cmb.setCurrentText('Snap: ON')

		self.setTransformSnap('scale', tri_state)


	def chk023(self, state=None):
		'''Transform Tool Snap Settings: Rotate
		'''
		cmb = self.sb.transform.cmb003
		tri_state = cmb.menu_.chk023.checkState_()
		text = {0:'Snap Rotate: Off', 1:'Snap Rotate: Relative', 2:'Snap Rotate: Absolute'}
		cmb.menu_.chk023.setText(text[tri_state])
		cmb.menu_.s023.setEnabled(tri_state)
		cmb.setCurrentText('Snap: OFF') if not any((tri_state, cmb.menu_.chk021.isChecked(), cmb.menu_.chk022.isChecked())) else cmb.setCurrentText('Snap: ON')

		self.setTransformSnap('rotate', tri_state)









# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------



# deprecated ------------------------------------

# def chk014(self, state=None):
	# 	'''Snap: Toggle Rotation
	# 	'''
	# 	cmb = self.sb.transform.cmb003

	# 	cmb.menu_.chk023.setChecked(True)
	# 	cmb.menu_.s023.setValue(11.25)
	# 	state = 1 if self.sb.transform_submenu.chk014.isChecked() else 0
	# 	self.chk023(state=state)