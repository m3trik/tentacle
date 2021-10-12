# !/usr/bin/python
# coding=utf-8
# from __future__ import print_function, absolute_import
from builtins import super
import os.path

from maya_init import *



class Rigging(Init):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)


	def draggable_header(self, state=None):
		'''Context menu
		'''
		dh = self.rigging_ui.draggable_header

		if state is 'setMenu':
			dh.contextMenu.add(wgts.ComboBox, setObjectName='cmb000', setToolTip='Maya Rigging Editors')
			return


	def cmb000(self, index=-1):
		'''Editors
		'''
		cmb = self.rigging_ui.cmb000

		if index is 'setMenu':
			list_ = ['Quick Rig','HumanIK','Expression Editor','Shape Editor','Connection Editor','Channel Control Editor','Set Driven Key']
			cmb.addItems_(list_, 'Maya Rigging Editors')
			return

		if index>0:
			text = cmb.items[index]
			if text=='Quick Rig':
				mel.eval('QuickRigEditor;') #Quick Rig
			elif text=='HumanIK':
				mel.eval('HIKCharacterControlsTool;') #HumanIK
			elif text=='Expression Editor':
				mel.eval('ExpressionEditor;') #Expression Editor
			elif text=='Shape Editor':
				mel.eval('ShapeEditor;') #Shape Editor
			elif text=='Connection Editor':
				mel.eval('ConnectionEditor;') #Connection Editor
			elif text=='Channel Control Editor':
				mel.eval('ChannelControlEditor;') #Channel Control Editor
			elif text=='Set Driven Key':
				mel.eval('SetDrivenKeyOptions;') #Set Driven Key
			cmb.setCurrentIndex(0)


	def cmb001(self, index=-1):
		'''Create
		'''
		cmb = self.rigging_ui.cmb001

		if index is 'setMenu':
			list_ = ['Joints','Locator','IK Handle', 'Lattice', 'Cluster']
			cmb.addItems_(list_, "Create")
			return

		if index>0:
			text = cmb.items[index]
			if text=='Joints':
				pm.setToolTo('jointContext') #create joint tool
			elif text=='Locator':
				pm.spaceLocator(p=[0,0,0]) #locator
			elif text=='IK Handle':
				pm.setToolTo('ikHandleContext') #create ik handle
			elif text=='Lattice':
				pm.lattice(divisions=[2,5,2], objectCentered=1, ldv=[2,2,2]) ##create lattice
			elif text=='Cluster':
				mel.eval('CreateCluster;') #create cluster
			cmb.setCurrentIndex(0)


	def chk000(self, state=None):
		'''Scale Joint
		'''
		self.toggleWidgets(setUnChecked='chk001-2')
		self.rigging_ui.tb000.menu_.s000.setValue(pm.jointDisplayScale(query=1)) #init global joint display size


	def chk001(self, state=None):
		'''Scale IK
		'''
		self.toggleWidgets(setUnChecked='chk000, chk002')
		self.rigging_ui.s000.setValue(pm.ikHandleDisplayScale(query=1)) #init IK handle display size
		

	def chk002(self, state=None):
		'''Scale IK/FK
		'''
		self.toggleWidgets(setUnChecked='chk000-1')
		self.rigging_ui.s000.setValue(pm.jointDisplayScale(query=1, ikfk=1)) #init IKFK display size


	def s000(self, value=None):
		'''Scale Joint/IK/FK
		'''
		value = self.rigging_ui.s000.value()

		if self.rigging_ui.chk000.isChecked():
			pm.jointDisplayScale(value) #set global joint display size
		elif self.rigging_ui.chk001.isChecked():
			pm.ikHandleDisplayScale(value) #set global IK handle display size
		else: #self.rigging_ui.chk002.isChecked():
			pm.jointDisplayScale(value, ikfk=1) #set global IKFK display size


	def tb000(self, state=None):
		'''Toggle Display Local Rotation Axes
		'''
		tb = self.current_ui.tb000
		if state is 'setMenu':
			tb.menu_.add('QCheckBox', setText='Joints', setObjectName='chk000', setChecked=True, setToolTip='Display Joints.')
			tb.menu_.add('QCheckBox', setText='IK', setObjectName='chk001', setChecked=True, setToolTip='Display IK.')
			tb.menu_.add('QCheckBox', setText='IK\\FK', setObjectName='chk002', setChecked=True, setToolTip='Display IK\\FK.')
			tb.menu_.add('QDoubleSpinBox', setPrefix='Tolerance: ', setObjectName='s000', setMinMax_='0.00-10 step.5', setValue=1.0, setToolTip='Global Display Scale for the selected type.')
			
			try:
				self.chk000() #init scale joint value
			except NameError:
				pass
			return

		joints = pm.ls(type="joint") #get all scene joints

		state = pm.toggle(joints[0], query=1, localAxis=1)
		if tb.menu_.isChecked():
			if not state:
				toggle=True
		else:
			if state:
				toggle=True

		if toggle:
			pm.toggle(joints, localAxis=1) #set display off

		self.viewPortMessage("Display Local Rotation Axes:<hl>"+str(state)+"</hl>")


	def tb001(self, state=None):
		'''Orient Joints
		'''
		tb = self.current_ui.tb001
		if state is 'setMenu':
			tb.menu_.add('QCheckBox', setText='Align world', setObjectName='chk003', setToolTip='Align joints with the worlds transform.')
			return

		orientJoint = 'xyz' #orient joints
		if tb.menu_.isChecked():
			orientJoint = 'none' #orient joint to world

		pm.joint(edit=1, orientJoint=orientJoint, zeroScaleOrient=1, ch=1)


	def tb002(self, state=None):
		'''Constraint: Parent
		'''
		tb = self.current_ui.tb002
		if state is 'setMenu':
			tb.menu_.add('QCheckBox', setText='Template Child', setObjectName='chk004', setChecked=False, setToolTip='Template child object(s) after parenting.')		
			return

		template = tb.menu_.chk004.isChecked()

		objects = pm.ls(sl=1, objectsOnly=1)

		for obj in objects[:-1]:
			pm.parentConstraint(obj, objects[:-1], maintainOffset=1, weight=1)

			if template:
				if not pm.toggle(obj, template=1, query=1):
					pm.toggle(obj, template=1, query=1)


	def b001(self):
		'''Connect Joints
		'''
		pm.connectJoint(cm=1)


	def b002(self):
		'''Insert Joint Tool
		'''
		pm.setToolTo('insertJointContext') #insert joint tool


	def b004(self):
		'''Reroot
		'''
		pm.reroot() #re-root joints


	def b006(self):
		'''Constraint: Point
		'''
		pm.pointConstraint(offset=[0,0,0], weight=1)


	def b007(self):
		'''Constraint: Scale
		'''
		pm.scaleConstraint(offset=[1,1,1], weight=1)


	def b008(self):
		'''Constraint: Orient
		'''
		pm.orientConstraint(offset=[0,0,0], weight=1)


	def b009(self):
		'''Constraint: Aim
		'''
		pm.aimConstraint(offset=[0,0,0], weight=1, aimVector=[1,0,0], upVector=[0,1,0], worldUpType="vector", worldUpVector=[0,1,0])


	def b010(self):
		'''Constraint: Pole Vector
		'''
		pm.orientConstraint(offset=[0,0,0], weight=1)






#module name
print(os.path.splitext(os.path.basename(__file__))[0])
# -----------------------------------------------
# Notes
# -----------------------------------------------