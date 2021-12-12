# !/usr/bin/python
# coding=utf-8
from maya_init import *



class Pivot(Init):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)


	def draggable_header(self, state=None):
		'''Context menu
		'''
		dh = self.pivot_ui.draggable_header

		if state=='setMenu':
			dh.contextMenu.add(self.tcl.wgts.ComboBox, setObjectName='cmb000', setToolTip='')
			return


	def cmb000(self, index=-1):
		'''Editors
		'''
		cmb = self.pivot_ui.draggable_header.contextMenu.cmb000

		if index=='setMenu':
			list_ = ['']
			cmb.addItems_(list_, '')
			return

		if index>0:
			text = cmb.items[index]
			if text=='':
				pass
			cmb.setCurrentIndex(0)


	@Slots.message
	def tb000(self, state=None):
		'''Reset Pivot
		'''
		tb = self.current_ui.tb000
		if state=='setMenu':
			tb.contextMenu.add('QCheckBox', setText='Reset Pivot Position', setObjectName='chk000', setChecked=True, setToolTip='')
			tb.contextMenu.add('QCheckBox', setText='Reset Pivot Orientation', setObjectName='chk001', setChecked=True, setToolTip='')
			return

		resetPivotPosition = tb.contextMenu.chk000.isChecked() #Reset Pivot Position
		resetPivotOrientation = tb.contextMenu.chk001.isChecked() #Reset Pivot Orientation

		mel.eval('manipPivotReset({0},{1})'.format(int(resetPivotPosition), int(resetPivotOrientation)))
		return 'Reset Pivot Position <hl>{0}</hl>.<br>Reset Pivot Orientation <hl>{1}</hl>.'.format(resetPivotPosition, resetPivotOrientation)


	def tb001(self, state=None):
		'''Center Pivot
		'''
		tb = self.pivot_ui.tb001
		if state=='setMenu':
			tb.contextMenu.add('QRadioButton', setText='Component', setObjectName='chk002', setToolTip='Center the pivot on the center of the selected component\'s bounding box')
			tb.contextMenu.add('QRadioButton', setText='Object', setObjectName='chk003', setChecked=True, setToolTip='Center the pivot on the center of the object\'s bounding box')
			tb.contextMenu.add('QRadioButton', setText='World', setObjectName='chk004', setToolTip='Center the pivot on world origin.')
			return

		component = tb.contextMenu.chk002.isChecked()
		object_ = tb.contextMenu.chk003.isChecked()
		world = tb.contextMenu.chk004.isChecked()

		if component: #Set pivot points to the center of the component's bounding box.
			pm.xform(centerPivotsOnComponents=1)
		elif object_: ##Set pivot points to the center of the object's bounding box
			pm.xform(centerPivots=1)
		elif world:
			pm.xform(worldSpace=1, pivots=[0,0,0])


	def b000(self):
		'''Center Pivot: Object
		'''
		tb = self.pivot_ui.tb001
		tb.contextMenu.chk003.setChecked(True)
		self.tb001()


	def b001(self):
		'''Center Pivot: Component
		'''
		tb = self.pivot_ui.tb001
		tb.contextMenu.chk002.setChecked(True)
		self.tb001()


	def b002(self):
		'''Center Pivot: World
		'''
		tb = self.pivot_ui.tb001
		tb.contextMenu.chk004.setChecked(True)
		self.tb001()


	def b004(self):
		'''Bake Pivot
		'''
		pm.mel.BakeCustomPivot()


	@staticmethod
	def resetPivotTransforms(objects):
		'''Reset Pivot Transforms
		'''
		objs = pm.ls(type=['transform', 'geometryShape'], sl=1)

		if len(objs)>0:
			pm.xform(cp=1)
			
		pm.manipPivot(ro=1, rp=1)









#module name
print (__name__)
# -----------------------------------------------
# Notes
# -----------------------------------------------