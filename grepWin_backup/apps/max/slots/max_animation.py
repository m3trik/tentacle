# !/usr/bin/python
# coding=utf-8
# from __future__ import print_function, absolute_import
from builtins import super
import os.path

from max_init import *



class Animation(Init):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)


	def draggable_header(self, state=None):
		'''Context menu
		'''
		dh = self.animation_ui.draggable_header

		if state is 'setMenu':
			dh.contextMenu.add(wgts.ComboBox, setObjectName='cmb000', setToolTip='')
			return


	def cmb000(self, index=-1):
		'''Editors
		'''
		cmb = self.animation_ui.cmb000

		if index is 'setMenu':
			list_ = ['Track View: Curve Editor','Track View: Dope Sheet','Track View: New Track View','Motion Mixer','Pose Mixer','MassFx Tools',
			'Dynamics Explorer','Reaction Manager','Walkthrough Assistant']
			cmb.addItems_(list_, 'Animation Editors')
			return

		if index>0:
			text = cmb.items[index]
			if text=='Track View: Curve Editor':
				maxEval('macros.run "Track View" "LaunchFCurveEditor"')
			elif text=='Track View: Dope Sheet':
				maxEval('macros.run "Track View" "LaunchDopeSheetEditor"')
			elif text=='Track View: New Track View':
				maxEval('actionMan.executeAction 0 "40278"') #Track View: New Track View
			elif text=='Motion Mixer':
				maxEval('macros.run "Mixer" "ToggleMotionMixerDlg"')
			elif text=='Pose Mixer':
				maxEval('macros.run "CAT" "catPoseMixer"')
			elif text=='MassFx Tools':
				maxEval('macros.run "PhysX" "PxShowToolsWindowMS"')
			elif text=='Dynamics Explorer':
				maxEval('macros.run "PhysX" "OpenDynamicsExplorer"')
			elif text=='Reaction Manager':
				maxEval('macros.run "Animation Tools" "OpenReactionManager"')
			elif text=='Walkthrough Assistant':
				maxEval('macros.run "Animation Tools" "walk_assist"')
			cmb.setCurrentIndex(0)


	def b000(self):
		'''Delete Keys on Selected
		'''
		rt.deleteKeys(rt.selection)


	@staticmethod
	def getSubAnimControllers(node, keyable=False, _result=[]):
		'''Returns a list of all the subanim controllers for a given node.

		:Parameters:
			node (obj) = The node in which to query controllers of.
			keyable (bool) = Return only keyable controllers.
			_result (obj) = Recursive call.

		:Return:
			(list) A List of sub level animation controllers.

		ex. ctrls = getSubAnimControllers(obj)
		'''
		if rt.iskindof(node, rt.subanim):
			_result.append(node)

		for i in range(1, node.numsubs):
			ctrl = rt.getSubAnim(node, i)
			Animation.getSubAnimControllers(ctrl, _result)

		if keyable:
			_result = Animation.getKeyableControllers(_result)

		return _result


	@staticmethod
	def getKeyableControllers(controllers):
		'''Filters a given list for controllers that are keyable.
		You can get the initial list of controllers using getSubAnimControllers.

		:Parameters:
			controllers (list) = A list of controller objects.

		:Return:
			(list) A list of keyable controllers.

		ex. ctrls = getSubAnimControllers(obj)
			kctrls = getKeyableControllers(ctrls)
		'''
		result=[]
		for c in controllers:
			if rt.classof(c.controller)==rt.undefinedClass:
				continue
			if not c.controller.keyable:
				continue
			result.append(c)

		return result


	@staticmethod
	def AssignController(currentController, newController):
		'''Attempts at assigning a given controller.

		:Parameters:
			currentController (obj) = 
			newController (obj) = 

		ex. ctrls = getSubAnimControllers(obj)
			kctrls = getKeyableControllers(ctrls)
			newCtrl = rt.noise_float()
			for k in kctrls:
				AssignController(k.controller, newCtrl)
		'''
		mxsexpr = rt.exprForMAXObject(currentController)
		mxstokens = mxsexpr.split('.')
		controller_to_change = rt.getNodeByName(mxstokens[0][1:]).controller

		for controller_name in mxstokens[1:-2:2]:
			controller_to_change = rt.getPropertyController(controller_to_change, controller_name)

		try:
			rt.setPropertyController(controller_to_change, mxstokens[-2], newController)
		except RuntimeError as error:
			print("# Error: Unable to assign new controller: {} #".format(error))









#module name
print(os.path.splitext(os.path.basename(__file__))[0])
# -----------------------------------------------
# Notes
# -----------------------------------------------