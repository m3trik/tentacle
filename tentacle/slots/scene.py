# !/usr/bin/python
# coding=utf-8
from tentacle.slots import Slots



class Scene(Slots):
	'''
	'''
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		'''
		'''
		dh = self.sb.scene.draggable_header
		dh.ctxMenu.add(self.sb.ComboBox, setObjectName='cmb000', setToolTip='Scene Editors')

		t000 = self.sb.scene.t000
		t000.ctxMenu.add('QCheckBox', setText='Ignore Case', setObjectName='chk000', setToolTip='Search case insensitive.')
		t000.ctxMenu.add('QCheckBox', setText='Regular Expression', setObjectName='chk001', setToolTip='When checked, regular expression syntax is used instead of the default \'*\' and \'|\' wildcards.')

		tb000 = self.sb.scene.tb000
		tb000.ctxMenu.add('QComboBox', addItems=['capitalize', 'upper', 'lower', 'swapcase', 'title'], setObjectName='cmb001', setToolTip='Set desired python case operator.')

		tb001 = self.sb.scene.tb001
		tb001.ctxMenu.add('QCheckBox', setText='Alphanumeric', setObjectName='chk005', setToolTip='When True use an alphanumeric character as a suffix when there is less than 26 objects else use integers.')
		tb001.ctxMenu.add('QCheckBox', setText='Strip Trailing Integers', setObjectName='chk002', setChecked=True, setToolTip="Strip any trailing integers. ie. '123' of 'cube123'")
		tb001.ctxMenu.add('QCheckBox', setText='Strip Trailing Alphanumeric', setObjectName='chk003', setChecked=True, setToolTip="Strip any trailing uppercase alphanumeric chars that are prefixed with an underscore.  ie. 'A' of 'cube_A'")
		tb001.ctxMenu.add('QCheckBox', setText='Reverse', setObjectName='chk004', setToolTip='Reverse the naming order. (Farthest object first)')


	def draggable_header(self, state=None):
		'''Context menu
		'''
		dh = self.sb.scene.draggable_header


	def t000(self, state=None):
		'''Find
		'''
		t000 = self.sb.scene.t000









# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------


#deprecated: