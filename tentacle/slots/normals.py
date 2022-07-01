# !/usr/bin/python
# coding=utf-8
from slots import Slots



class Normals(Slots):
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
		dh = self.normals_ui.draggable_header
		dh.contextMenu.add(self.ComboBox, setObjectName='cmb000', setToolTip='')

		tb000 = self.normals_ui.tb000
		tb000.contextMenu.add('QSpinBox', setPrefix='Display Size: ', setObjectName='s001', setMinMax_='1-100 step1', setValue=1, setToolTip='Normal display size.')

		tb001 = self.normals_ui.tb001
		tb001.contextMenu.add('QSpinBox', setPrefix='Angle: ', setObjectName='s002', setMinMax_='0-180 step1', setValue=0, setToolTip='The normal angle in degrees.')
		tb001.contextMenu.add('QCheckBox', setText='Harden Creased Edges', setObjectName='chk005', setChecked=True, setToolTip='Soften all non-creased edges.')
		tb001.contextMenu.add('QCheckBox', setText='Harden UV Borders', setObjectName='chk006', setChecked=True, setToolTip='Harden UV shell border edges.')
		tb001.contextMenu.add('QCheckBox', setText='Soften All Other', setObjectName='chk004', setChecked=True, setToolTip='Soften all non-hard edges.')
		tb001.contextMenu.add('QCheckBox', setText='Soft Edge Display', setObjectName='chk007', setChecked=True, setToolTip='Turn on soft edge display for the object.')

		tb002 = self.normals_ui.tb002
		tb002.contextMenu.add('QSpinBox', setPrefix='Angle: ', setObjectName='s000', setMinMax_='0-180 step1', setValue=60, setToolTip='Angle degree.')

		tb003 = self.normals_ui.tb003
		tb003.contextMenu.add('QCheckBox', setText='Lock', setObjectName='chk002', setChecked=True, setToolTip='Toggle Lock/Unlock.')
		tb003.contextMenu.add('QCheckBox', setText='All', setObjectName='chk001', setChecked=True, setToolTip='Lock/Unlock All.')
		tb003.contextMenu.chk002.toggled.connect(lambda state, w=tb003.contextMenu.chk002: w.setText('Lock') if state else w.setText('Unlock')) 

		tb004 = self.normals_ui.tb004
		tb004.contextMenu.add('QCheckBox', setText='By UV Shell', setObjectName='chk003', setChecked=True, setToolTip='Average the normals of each object\'s faces per UV shell.')


	def draggable_header(self, state=None):
		'''Context menu
		'''
		dh = self.normals_ui.draggable_header
