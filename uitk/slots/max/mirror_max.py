# !/usr/bin/python
# coding=utf-8
from uitk.slots.max import *
from uitk.slots.mirror import Mirror



class Mirror_max(Mirror, Slots_max):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)

		cmb = self.sb.mirror.draggable_header.ctxMenu.cmb000
		items = ['']
		cmb.addItems_(items, '')

		ctx = self.sb.mirror.tb000.ctxMenu
		ctx.chk006.setDisabled(True) #disable: delete history.


		def cmb000(self, index=-1):
		'''Editors
		'''
		cmb = self.sb.mirror.draggable_header.ctxMenu.cmb000

		if index>0:
			if index==cmd.items.index(''):
				pass
			cmb.setCurrentIndex(0)


	@Slots_maya.attr
	def tb000(self, state=None):
		'''Mirror Geometry

		values for the direction (dict): ex. 'X': (0, 0, -1, 1, 1)
			key = axis (as str): 'X', '-X', 'Y', '-Y', 'Z', '-Z'
			0 = axisDirection (int): (0, 1) #Specify a positive or negative axis.
			1 = axis_as_int (as integer value): 0=-x, 1=x, 2=-y, 3=y, 4=-z, 5=z #Which axis to mirror.
			2-4 = scale values (int): (0, 1) for each x; y; z; #Used for scaling an instance.
		'''
		tb = self.sb.mirror.tb000

		axis = self.sb.getAxisFromCheckBoxes('chk000-3', tb.ctxMenu)
		worldSpace = tb.ctxMenu.chk008.isChecked()
		cutMesh = tb.ctxMenu.chk005.isChecked() #cut mesh on axis before mirror.
		instance = tb.ctxMenu.chk004.isChecked()
		merge = tb.ctxMenu.chk007.isChecked()
		mergeMode = tb.ctxMenu.s001.value()
		mergeThreshold = tb.ctxMenu.s000.value()
		deleteHistory = tb.ctxMenu.chk006.isChecked() #delete the object's non-deformer history.

		return self.mirrorGeometry(axis=axis, worldSpace=worldSpace, cutMesh=cutMesh, instance=instance, merge=merge, 
			mergeMode=mergeMode, mergeThreshold=mergeThreshold, deleteHistory=deleteHistory)


	def b000(self):
		'''Mirror: X
		'''
		self.sb.mirror.tb000.ctxMenu.chk001.setChecked(True)
		self.tb000()


	def b001(self):
		'''Mirror: Y
		'''
		self.sb.mirror.tb000.ctxMenu.chk002.setChecked(True)
		self.tb000()


	def b002(self):
		'''Mirror: Z
		'''
		self.sb.mirror.tb000.ctxMenu.chk003.setChecked(True)
		self.tb000()


	@undo
	def mirrorGeometry(self, objects=None, axis='-X', worldSpace=True, cutMesh=False, instance=False, 
					merge=False, mergeMode=1, mergeThreshold=0.005, deleteHistory=True):
		'''Mirror geometry across a given axis.

		:Parameters:
			objects (obj): The objects to mirror. If None; any currently selected objects will be used.
			axis (string) = The axis in which to perform the mirror along. case insensitive. (valid: 'X', '-X', 'Y', '-Y', 'Z', '-Z')
			worldSpace (bool): This flag specifies which reference to use. If True: all geometrical values are taken in world reference. If False: all geometrical values are taken in object reference.
			cutMesh (bool): Perform a delete along specified axis before mirror.
			instance (bool): Instance the mirrored object(s).
			merge (bool): Merge the mirrored geometry with the original.
			mergeMode (int): 0) Do not merge border edges. 1) Border edges merged. 2) Border edges extruded and connected.
			mergeThreshold (float) = Merge vertex distance.
			deleteHistory (bool): Delete non-deformer history on the object before performing the operation.

		:Return:
			(obj) The polyMirrorFace history node if a single object, else None.
		'''
		direction = {
			 'X': (0, 0,-1, 1, 1),
			'-X': (1, 1,-1, 1, 1),
			 'Y': (0, 2, 1,-1, 1),
			'-Y': (1, 3, 1,-1, 1),
			 'Z': (0, 4, 1, 1,-1),
			'-Z': (1, 5, 1, 1,-1)
		}

		axis = axis.upper()
		axisDirection, axis_as_int, x, y, z = direction[str(axis)] #ex. axisDirection=1, axis_as_int=5, x=1; y=1; z=-1

		pm.ls(objects, objectsOnly=1)
		if not objects:
			objects = pm.ls(sl=1, objectsOnly=1)
			if not objects:
				return 'Error: <b>Nothing selected.<b><br>Operation requires at least one selected polygon object.'

		# pm.undoInfo(openChunk=1)
		for obj in objects:
			if deleteHistory:
				pm.mel.BakeNonDefHistory(obj)

			if cutMesh:
				self.sb.edit.slots.deleteAlongAxis(obj, axis) #delete mesh faces that fall inside the specified axis.

			if instance: #create instance and scale negatively
				inst = pm.instance(obj) # bt_convertToMirrorInstanceMesh(0); #x=0, y=1, z=2, -x=3, -y=4, -z=5
				pm.xform(inst, scale=[x,y,z]) #pm.scale(z,x,y, pivot=(0,0,0), relative=1) #swap the xyz values to transform the instanced node
				return inst if len(objects)==1 else inst 

			else: #mirror
				polyMirrorFaceNode = pm.ls(pm.polyMirrorFace(obj, mirrorAxis=axisDirection, direction=axis_as_int, mergeMode=mergeMode, 
						mergeThresholdType=1, mergeThreshold=mergeThreshold, worldSpace=worldSpace, smoothingAngle=30, flipUVs=0, ch=1))[0] #mirrorPosition x, y, z - This flag specifies the position of the custom mirror axis plane

				if not merge:
					polySeparateNode = pm.ls(pm.polySeparate(obj, uss=1, inp=1))[2]

					pm.connectAttr(polyMirrorFaceNode.firstNewFace, polySeparateNode.startFace, force=True) 
					pm.connectAttr(polyMirrorFaceNode.lastNewFace, polySeparateNode.endFace, force=True)

			try:
				if len(objects)==1:
					return polyMirrorFaceNode
			except AttributeError as error:
				return None
		# pm.undoInfo(closeChunk=1)









#module name
print (__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------


#deprecated:

	# def chk000(self, state=None):
	# 	'''
	# 	Delete: Negative Axis. Set Text Mirror Axis
	# 	'''
	# 	axis = "X"
	# 	if self.sb.mirror.chk002.isChecked():
	# 		axis = "Y"
	# 	if self.sb.mirror.chk003.isChecked():
	# 		axis = "Z"
	# 	if self.sb.mirror.chk000.isChecked():
	# 		axis = '-'+axis
	# 	self.sb.mirror.b000.setText('Mirror '+axis)
	# 	self.sb.mirror.b008.setText('Delete '+axis)


	# #set check states
	# def chk000(self, state=None):
	# 	'''
	# 	Delete: X Axis
	# 	'''
	# 	self.sb.toggleWidgets(setUnChecked='chk002,chk003')
	# 	axis = "X"
	# 	if self.sb.mirror.chk000.isChecked():
	# 		axis = '-'+axis
	# 	self.sb.mirror.b000.setText('Mirror '+axis)
	# 	self.sb.mirror.b008.setText('Delete '+axis)


	# def chk002(self, state=None):
	# 	'''
	# 	Delete: Y Axis
	# 	'''
	# 	self.sb.toggleWidgets(setUnChecked='chk001,chk003')
	# 	axis = "Y"
	# 	if self.sb.mirror.chk000.isChecked():
	# 		axis = '-'+axis
	# 	self.sb.mirror.b000.setText('Mirror '+axis)
	# 	self.sb.mirror.b008.setText('Delete '+axis)


	# def chk003(self, state=None):
	# 	'''
	# 	Delete: Z Axis
	# 	'''
	# 	self.sb.toggleWidgets(setUnChecked='chk001,chk002')
	# 	axis = "Z"
	# 	if self.sb.mirror.chk000.isChecked():
	# 		axis = '-'+axis
	# 	self.sb.mirror.b000.setText('Mirror '+axis)
	# 	self.sb.mirror.b008.setText('Delete '+axis)