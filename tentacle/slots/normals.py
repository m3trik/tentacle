# !/usr/bin/python
# coding=utf-8
from slots import Slots



class Normals(Slots):
	'''
	'''
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		'''
		'''
		dh = self.sb.normals.draggable_header
		dh.ctxMenu.add(self.sb.ComboBox, setObjectName='cmb000', setToolTip='')

		tb000 = self.sb.normals.tb000
		tb000.ctxMenu.add('QSpinBox', setPrefix='Display Size: ', setObjectName='s001', setMinMax_='1-100 step1', setValue=1, setToolTip='Normal display size.')

		tb001 = self.sb.normals.tb001
		tb001.ctxMenu.add('QSpinBox', setPrefix='Angle: ', setObjectName='s002', setMinMax_='0-180 step1', setValue=0, setToolTip='The normal angle in degrees.')
		tb001.ctxMenu.add('QCheckBox', setText='Harden Creased Edges', setObjectName='chk005', setChecked=True, setToolTip='Soften all non-creased edges.')
		tb001.ctxMenu.add('QCheckBox', setText='Harden UV Borders', setObjectName='chk006', setChecked=True, setToolTip='Harden UV shell border edges.')
		tb001.ctxMenu.add('QCheckBox', setText='Soften All Other', setObjectName='chk004', setChecked=True, setToolTip='Soften all non-hard edges.')
		tb001.ctxMenu.add('QCheckBox', setText='Soft Edge Display', setObjectName='chk007', setChecked=True, setToolTip='Turn on soft edge display for the object.')

		tb002 = self.sb.normals.tb002
		tb002.ctxMenu.add('QSpinBox', setPrefix='Angle: ', setObjectName='s000', setMinMax_='0-180 step1', setValue=60, setToolTip='Angle degree.')

		tb003 = self.sb.normals.tb003
		tb003.ctxMenu.add('QCheckBox', setText='Lock', setObjectName='chk002', setChecked=True, setToolTip='Toggle Lock/Unlock.')
		tb003.ctxMenu.add('QCheckBox', setText='All', setObjectName='chk001', setChecked=True, setToolTip='Lock/Unlock All.')
		tb003.ctxMenu.chk002.toggled.connect(lambda state, w=tb003.ctxMenu.chk002: w.setText('Lock') if state else w.setText('Unlock')) 

		tb004 = self.sb.normals.tb004
		tb004.ctxMenu.add('QCheckBox', setText='By UV Shell', setObjectName='chk003', setChecked=True, setToolTip='Average the normals of each object\'s faces per UV shell.')


	def draggable_header(self, state=None):
		'''Context menu
		'''
		dh = self.sb.normals.draggable_header
