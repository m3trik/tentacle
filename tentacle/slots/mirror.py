# !/usr/bin/python
# coding=utf-8
from slots import Slots



class Mirror(Slots):
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
		dh = self.mirror_ui.draggable_header
		dh.contextMenu.add(self.ComboBox, setObjectName='cmb000', setToolTip='')

		tb000 = self.mirror_ui.tb000
		tb000.contextMenu.add('QCheckBox', setText='-', setObjectName='chk000', setChecked=True, setToolTip='Perform mirror along the negative axis.')
		tb000.contextMenu.add('QRadioButton', setText='X', setObjectName='chk001', setChecked=True, setToolTip='Perform mirror along X axis.')
		tb000.contextMenu.add('QRadioButton', setText='Y', setObjectName='chk002', setToolTip='Perform mirror along Y axis.')
		tb000.contextMenu.add('QRadioButton', setText='Z', setObjectName='chk003', setToolTip='Perform mirror along Z axis.')
		tb000.contextMenu.add('QCheckBox', setText='World Space', setObjectName='chk008', setChecked=True, setToolTip='Mirror in world space instead of object space.')
		tb000.contextMenu.add('QCheckBox', setText='Un-Instance', setObjectName='chk009', setChecked=True, setToolTip='Un-Instance any previously instanced objects before mirroring.')
		tb000.contextMenu.add('QCheckBox', setText='Instance', setObjectName='chk004', setToolTip='Instance the mirrored object(s).')
		tb000.contextMenu.add('QCheckBox', setText='Cut', setObjectName='chk005', setToolTip='Perform a delete along specified axis before mirror.')
		tb000.contextMenu.add('QCheckBox', setText='Merge', setObjectName='chk007', setChecked=True, setToolTip='Merge the mirrored geometry with the original.')
		tb000.contextMenu.add('QSpinBox', setPrefix='Merge Mode: ', setObjectName='s001', setMinMax_='0-2 step1', setValue=0, setToolTip='0) Do not merge border edges.<br>1) Border edges merged.<br>2) Border edges extruded and connected.')
		tb000.contextMenu.add('QDoubleSpinBox', setPrefix='Merge Threshold: ', setObjectName='s000', setMinMax_='0.000-10 step.001', setValue=0.005, setToolTip='Merge vertex distance.')
		tb000.contextMenu.add('QCheckBox', setText='Delete Original', setObjectName='chk010', setToolTip='Delete the original objects after mirroring.')
		tb000.contextMenu.add('QCheckBox', setText='Delete History', setObjectName='chk006', setChecked=True, setToolTip='Delete non-deformer history on the object before performing the operation.')

		#sync widgets
		self.sb.setSyncAttributesConnections(tb000.contextMenu.chk000, self.mirror_submenu_ui.chk000, attributes='setChecked')
		self.sb.setSyncAttributesConnections(tb000.contextMenu.chk007, self.mirror_submenu_ui.chk007, attributes='setChecked')
		self.sb.setSyncAttributesConnections(tb000.contextMenu.chk008, self.mirror_submenu_ui.chk008, attributes='setChecked')


	def draggable_header(self, state=None):
		'''Context menu
		'''
		dh = self.mirror_ui.draggable_header









# -----------------------------------------------
# Notes
# -----------------------------------------------



#deprecated:
	# def chk000_3(self):
	# 	'''Set the tb000's text according to the checkstates.

	# 	ex call: self.connect_('chk000-3', 'toggled', self.chk000_3, ctx)
	# 	'''
	# 	axis = self.getAxisFromCheckBoxes('chk000-3', self.mirror_ui.tb000.contextMenu)
	# 	self.mirror_ui.tb000.setText('Mirror '+axis)

		