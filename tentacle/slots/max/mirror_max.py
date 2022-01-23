# !/usr/bin/python
# coding=utf-8
from slots.max import *
from slots.mirror import Mirror
from ui.static.max.mirror_ui_max import Mirror_ui_max



class Mirror(Slots_max):
	def __init__(self, *args, **kwargs):
		Slots_max.__init__(self, *args, **kwargs)
		Mirror_ui_max.__init__(self, *args, **kwargs)
		Mirror.__init__(self, *args, **kwargs)


	def draggable_header(self, state=None):
		'''Context menu
		'''
		dh = self.mirror_ui.draggable_header


	def cmb000(self, index=-1):
		'''Editors
		'''
		cmb = self.mirror_ui.draggable_header.contextMenu.cmb000

		if index>0:
			text = cmb.items[index]
			if text=='':
				pass
			cmb.setCurrentIndex(0)


	def chk000_3(self):
		'''Set the tb000's text according to the checkstates.
		'''
		axis = self.getAxisFromCheckBoxes('chk000-3')
		self.mirror_ui.tb000.setText('Mirror '+axis)


	@Slots.sync
	def chk005(self, state=None):
		'''Mirror: Cut
		'''
		pass


	@Slots.message
	def tb000(self, state=None):
		'''Mirror Geometry
		'''
		tb = self.mirror_ui.tb000

		axis = self.getAxisFromCheckBoxes('chk000-3', tb.contextMenu)
		cutMesh = tb.contextMenu.chk005.isChecked() #cut
		instance = tb.contextMenu.chk004.isChecked()
		mergeThreshold = tb.contextMenu.s000.value()

		if axis=='X': #'x'
			axisDirection = 0 #positive axis
			a = 0
			x=-1; y=1; z=1

		elif axis=='-X': #'-x'
			axisDirection = 1 #negative axis
			a = 1 #0=-x, 1=x, 2=-y, 3=y, 4=-z, 5=z 
			x=-1; y=1; z=1 #if instance: used to negatively scale

		elif axis=='Y': #'y'
			axisDirection = 0
			a = 2
			x=1; y=-1; z=1

		elif axis=='-Y': #'-y'
			axisDirection = 1
			a = 3
			x=1; y=-1; z=1

		elif axis=='Z': #'z'
			axisDirection = 0
			a = 4
			x=1; y=1; z=-1

		elif axis=='-Z': #'-z'
			axisDirection = 1
			a = 5
			x=1; y=1; z=-1

		selection = pm.ls(sl=1, objectsOnly=1)
		if not selection:
			return 'Warning: Nothing Selected.'

		pm.undoInfo(openChunk=1)
		for obj in [n for n in pm.listRelatives(selection, allDescendents=1) if pm.objectType(n, isType='mesh')]: #get any mesh type child nodes of obj.
			if cutMesh:
				self.deleteAlongAxis(obj, axis) #delete mesh faces that fall inside the specified axis.
			if instance: #create instance and scale negatively
				inst = pm.instance(obj) # bt_convertToMirrorInstanceMesh(0); #x=0, y=1, z=2, -x=3, -y=4, -z=5
				pm.xform(inst, scale=[x,y,z]) #pm.scale(z,x,y, pivot=(0,0,0), relative=1) #swap the xyz values to transform the instanced node
			else: #mirror
				pm.polyMirrorFace(obj, mirrorAxis=axisDirection, direction=a, mergeMode=1, mergeThresholdType=1, mergeThreshold=mergeThreshold, worldSpace=0, smoothingAngle=30, flipUVs=0, ch=0) #mirrorPosition x, y, z - This flag specifies the position of the custom mirror axis plane
		pm.undoInfo(closeChunk=1)









#module name
print (__name__)
# -----------------------------------------------
# Notes
# -----------------------------------------------


#deprecated:

	# def chk000(self, state=None):
	# 	'''
	# 	Delete: Negative Axis. Set Text Mirror Axis
	# 	'''
	# 	axis = "X"
	# 	if self.mirror_ui.chk002.isChecked():
	# 		axis = "Y"
	# 	if self.mirror_ui.chk003.isChecked():
	# 		axis = "Z"
	# 	if self.mirror_ui.chk000.isChecked():
	# 		axis = '-'+axis
	# 	self.mirror_ui.b000.setText('Mirror '+axis)
	# 	self.mirror_ui.b008.setText('Delete '+axis)


	# #set check states
	# def chk000(self, state=None):
	# 	'''
	# 	Delete: X Axis
	# 	'''
	# 	self.toggleWidgets(setUnChecked='chk002,chk003')
	# 	axis = "X"
	# 	if self.mirror_ui.chk000.isChecked():
	# 		axis = '-'+axis
	# 	self.mirror_ui.b000.setText('Mirror '+axis)
	# 	self.mirror_ui.b008.setText('Delete '+axis)


	# def chk002(self, state=None):
	# 	'''
	# 	Delete: Y Axis
	# 	'''
	# 	self.toggleWidgets(setUnChecked='chk001,chk003')
	# 	axis = "Y"
	# 	if self.mirror_ui.chk000.isChecked():
	# 		axis = '-'+axis
	# 	self.mirror_ui.b000.setText('Mirror '+axis)
	# 	self.mirror_ui.b008.setText('Delete '+axis)


	# def chk003(self, state=None):
	# 	'''
	# 	Delete: Z Axis
	# 	'''
	# 	self.toggleWidgets(setUnChecked='chk001,chk002')
	# 	axis = "Z"
	# 	if self.mirror_ui.chk000.isChecked():
	# 		axis = '-'+axis
	# 	self.mirror_ui.b000.setText('Mirror '+axis)
	# 	self.mirror_ui.b008.setText('Delete '+axis)