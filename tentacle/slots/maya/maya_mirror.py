# !/usr/bin/python
# coding=utf-8
import os.path
import traceback

from maya_init import *



class Mirror(Init):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)


	def draggable_header(self, state=None):
		'''Context menu
		'''
		dh = self.mirror_ui.draggable_header

		if state is 'setMenu':
			dh.contextMenu.add(wgts.ComboBox, setObjectName='cmb000', setToolTip='')
			return


	def cmb000(self, index=-1):
		'''Editors
		'''
		cmb = self.mirror_ui.cmb000

		if index is 'setMenu':
			list_ = ['']
			cmb.addItems_(list_, '')
			return

		if index>0:
			if index==cmd.items.index(''):
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
	@Init.attr
	def tb000(self, state=None):
		'''Mirror Geometry

		values for the direction (dict): ex. 'X': (0, 0, -1, 1, 1)
			key = axis (as str): 'X', '-X', 'Y', '-Y', 'Z', '-Z'
			0 = axisDirection (int): (0, 1) #Specify a positive or negative axis.
			1 = axis_as_int (as integer value): 0=-x, 1=x, 2=-y, 3=y, 4=-z, 5=z #Which axis to mirror.
			2-4 = scale values (int): (0, 1) for each x; y; z; #Used for scaling an instance.
		'''
		tb = self.current_ui.tb000
		if state is 'setMenu':
			tb.menu_.add('QCheckBox', setText='-', setObjectName='chk000', setChecked=True, setToolTip='Perform mirror along negative axis.')
			tb.menu_.add('QRadioButton', setText='X', setObjectName='chk001', setChecked=True, setToolTip='Perform mirror along X axis.')
			tb.menu_.add('QRadioButton', setText='Y', setObjectName='chk002', setToolTip='Perform mirror along Y axis.')
			tb.menu_.add('QRadioButton', setText='Z', setObjectName='chk003', setToolTip='Perform mirror along Z axis.')
			tb.menu_.add('QCheckBox', setText='Instance', setObjectName='chk004', setToolTip='Instance the mirrored object(s).')
			tb.menu_.add('QCheckBox', setText='Cut', setObjectName='chk005', setChecked=True, setToolTip='Perform a delete along specified axis before mirror.')
			tb.menu_.add('QDoubleSpinBox', setPrefix='Merge Threshold: ', setObjectName='s000', setMinMax_='0.000-10 step.001', setValue=0.005, setToolTip='Merge vertex distance.')
			tb.menu_.add('QCheckBox', setText='Delete History', setObjectName='chk006', setChecked=True, setToolTip='Delete non-deformer history on the object before performing the operation.')

			self.connect_('chk000-3', 'toggled', self.chk000_3, tb.menu_)
			return

		axis = self.getAxisFromCheckBoxes('chk000-3', tb.menu_)
		cutMesh = tb.menu_.chk005.isChecked() #cut mesh on axis before mirror.
		instance = tb.menu_.chk004.isChecked()
		mergeThreshold = tb.menu_.s000.value()
		deleteHistory = tb.menu_.chk006.isChecked() #delete the object's non-deformer history.

		Mirror.mirrorGeometry(axis=axis, cutMesh=cutMesh, instance=instance, mergeThreshold=mergeThreshold, deleteHistory=deleteHistory)


	@staticmethod
	@Init.undoChunk
	def mirrorGeometry(objects=None, axis='-X', cutMesh=False, instance=False, mergeThreshold=0.005, deleteHistory=True):
		'''Mirror geometry across a given axis.

		:Parameters:
			objects (obj) = The objects to mirror. If None; any currently selected objects will be used.
			axis = The axis in which to perform the mirror along.
			cutMesh = Perform a delete along specified axis before mirror.
			instance = Instance the mirrored object(s).
			mergeThreshold = Merge vertex distance.
			deleteHistory = Delete non-deformer history on the object before performing the operation.

		:Return:
			(obj) The polyMirrorFace history node.
		'''
		direction = {
			 'X': (0, 0,-1, 1, 1),
			'-X': (1, 1,-1, 1, 1),
			 'Y': (0, 2, 1,-1, 1),
			'-Y': (1, 3, 1,-1, 1),
			 'Z': (0, 4, 1, 1,-1),
			'-Z': (1, 5, 1, 1,-1)
		}
		print (axis, type(axis))
		axisDirection, axis_as_int, x, y, z = direction[str(axis)] #ex. axisDirection=1, axis_as_int=5, x=1; y=1; z=-1

		pm.ls(objects, objectsOnly=1)
		if not objects:
			objects = pm.ls(sl=1, objectsOnly=1)
			if not objects:
				return 'Warning: No object(s) given, or nothing selected.'

		# pm.undoInfo(openChunk=1)
		for obj in objects:
			if deleteHistory:
				pm.mel.BakeNonDefHistory(obj)

			if cutMesh:
				Init.deleteAlongAxis(obj, axis) #delete mesh faces that fall inside the specified axis.

			if instance: #create instance and scale negatively
				inst = pm.instance(obj) # bt_convertToMirrorInstanceMesh(0); #x=0, y=1, z=2, -x=3, -y=4, -z=5
				pm.xform(inst, scale=[x,y,z]) #pm.scale(z,x,y, pivot=(0,0,0), relative=1) #swap the xyz values to transform the instanced node
				return inst if len(objects)==1 else inst 

			else: #mirror
				polyMirrorFace = pm.polyMirrorFace(obj, mirrorAxis=axisDirection, direction=axis_as_int, mergeMode=1, mergeThresholdType=1, mergeThreshold=mergeThreshold, worldSpace=0, smoothingAngle=30, flipUVs=0, ch=1) #mirrorPosition x, y, z - This flag specifies the position of the custom mirror axis plane
				return polyMirrorFace if len(objects)==1 else polyMirrorFace
		# pm.undoInfo(closeChunk=1)









#module name
print(os.path.splitext(os.path.basename(__file__))[0])
# -----------------------------------------------
# Notes
# -----------------------------------------------



#deprecated:


# if axis=='X': #'x'
# 			axisDirection = 0 #positive axis
# 			axis_ = 0 #axis
# 			x=-1; y=1; z=1 #scale values

# 		elif axis=='-X': #'-x'
# 			axisDirection = 1 #negative axis
# 			axis_ = 1 #0=-x, 1=x, 2=-y, 3=y, 4=-z, 5=z 
# 			x=-1; y=1; z=1 #if instance: used to negatively scale

# 		elif axis=='Y': #'y'
# 			axisDirection = 0
# 			axis_ = 2
# 			x=1; y=-1; z=1

# 		elif axis=='-Y': #'-y'
# 			axisDirection = 1
# 			axis_ = 3
# 			x=1; y=-1; z=1

# 		elif axis=='Z': #'z'
# 			axisDirection = 0
# 			axis_ = 4
# 			x=1; y=1; z=-1

# 		elif axis=='-Z': #'-z'
# 			axisDirection = 1
# 			axis_ = 5
# 			x=1; y=1; z=-1

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
	# 	self.mirror_ui.tb000.setText('Mirror '+axis)
	# 	self.mirror_ui.tb003.setText('Delete '+axis)


	# #set check states
	# def chk000(self, state=None):
	# 	'''
	# 	Delete: X Axis
	# 	'''
	# 	self.toggleWidgets(setUnChecked='chk002,chk003')
	# 	axis = "X"
	# 	if self.mirror_ui.chk000.isChecked():
	# 		axis = '-'+axis
	# 	self.mirror_ui.tb000.setText('Mirror '+axis)
	# 	self.mirror_ui.tb003.setText('Delete '+axis)


	# def chk002(self, state=None):
	# 	'''
	# 	Delete: Y Axis
	# 	'''
	# 	self.toggleWidgets(setUnChecked='chk001,chk003')
	# 	axis = "Y"
	# 	if self.mirror_ui.chk000.isChecked():
	# 		axis = '-'+axis
	# 	self.mirror_ui.tb000.setText('Mirror '+axis)
	# 	self.mirror_ui.tb003.setText('Delete '+axis)


	# def chk003(self, state=None):
	# 	'''
	# 	Delete: Z Axis
	# 	'''
	# 	self.toggleWidgets(setUnChecked='chk001,chk002')
	# 	axis = "Z"
	# 	if self.mirror_ui.chk000.isChecked():
	# 		axis = '-'+axis
	# 	self.mirror_ui.tb000.setText('Mirror '+axis)
	# 	self.mirror_ui.tb003.setText('Delete '+axis)


	# def chk005(self, state=None):
		# '''
		# Mirror: Cut
		# '''
		#keep menu and submenu in sync:
		# if self.mirror_submenu.chk005.isChecked():
		# 	self.toggleWidgets(setChecked='chk005')
		# else:
		# 	self.toggleWidgets(setUnChecked='chk005')