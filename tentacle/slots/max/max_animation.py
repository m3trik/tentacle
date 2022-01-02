# !/usr/bin/python
# coding=utf-8
from slots.max import *



class Animation(Slots_max):
	def __init__(self, *args, **kwargs):
		Slots_max.__init__(self, *args, **kwargs)

		ctx = self.animation_ui.draggable_header.contextMenu
		if not ctx.containsMenuItems:
			ctx.add(self.tcl.wgts.ComboBox, setObjectName='cmb000', setToolTip='')

		cmb = self.animation_ui.draggable_header.contextMenu.cmb000
		items = ['Track View: Curve Editor','Track View: Dope Sheet','Track View: New Track View','Motion Mixer','Pose Mixer','MassFx Tools', 'Dynamics Explorer','Reaction Manager','Walkthrough Assistant']
		cmb.addItems_(items, 'Animation Editors')

		ctx = self.animation_ui.tb000.contextMenu
		if not ctx.containsMenuItems:
			ctx.add('QSpinBox', setPrefix='Frame: ', setObjectName='s000', setMinMax_='0-10000 step1', setValue=1, setToolTip='')
			ctx.add('QCheckBox', setText='Relative', setObjectName='chk000', setChecked=True, setToolTip='')
			ctx.add('QCheckBox', setText='Update', setObjectName='chk001', setChecked=True, setToolTip='')

		ctx = self.animation_ui.tb001.contextMenu
		if not ctx.containsMenuItems:
			ctx.add('QSpinBox', setPrefix='Time: ', setObjectName='s001', setMinMax_='0-10000 step1', setValue=1, setToolTip='The desired start time for the inverted keys.')
			ctx.add('QCheckBox', setText='Relative', setObjectName='chk002', setChecked=False, setToolTip='Start time position as relative or absolute.')


	def draggable_header(self, state=None):
		'''Context menu
		'''
		dh = self.animation_ui.draggable_header


	def cmb000(self, index=-1):
		'''Editors
		'''
		cmb = self.animation_ui.draggable_header.contextMenu.cmb000

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


	def tb000(self, state=None):
		'''Set Current Frame
		'''
		tb = self.current_ui.tb000

		frame = self.invertOnModifier(tb.contextMenu.s000.value())
		relative = tb.contextMenu.chk000.isChecked()
		update = tb.contextMenu.chk001.isChecked()

		Animation.setCurrentFrame(frame, relative=relative, update=update)


	@Slots.message
	def tb001(self, state=None):
		'''Invert Selected Keyframes
		'''
		tb = self.current_ui.tb001

		time = tb.contextMenu.s001.value()
		relative = tb.contextMenu.chk002.isChecked()

		Animation.invertSelectedKeyframes(time=time, relative=relative)


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


	@staticmethod
	def setCurrentFrame(frame=1, relative=False, update=True):
		'''Set the current frame on the timeslider.

		:Parameters:
		frame (int) = Desired from number.
		relative (bool) = If True; the frame will be moved relative to 
			it's current position using the frame value as a move amount.
		update (bool) = Change the current time, but do not update the world. (default=True)

		ex. call:
			setCurrentFrame(24, relative=True, update=1)
		'''
		currentTime=0
		if relative:
			currentTime = pm.currentTime(query=True)

		pm.currentTime(currentTime+frame, edit=True, update=update)


	@staticmethod
	def invertSelectedKeyframes(time=1, relative=True):
		'''Duplicate any selected keyframes and paste them inverted at the given time.

		:Parameters:
			time (int) = The desired start time for the inverted keys.
			relative (bool) = Start time position as relative or absolute.

		ex. call: invertSelectedKeyframes(time=48, relative=0)
		'''
		allActiveKeyTimes = pm.keyframe(query=True, sl=True, tc=True) #get times from all selected keys.
		if not allActiveKeyTimes:
			error = '# Error: No keys selected. #'
			print (error)
			return error
		range_ = max(allActiveKeyTimes) - min(allActiveKeyTimes)
		time = time - max(allActiveKeyTimes) if not relative else time

		selection = pm.ls(sl=1, transforms=1)
		for obj in selection:

			keys = pm.keyframe(obj, query=True, name=True, sl=True)
			for node in keys:

				activeKeyTimes = pm.keyframe(node, query=True, sl=True, tc=True)
				for t, rt in zip(activeKeyTimes, reversed(activeKeyTimes)):

					pm.copyKey(node, time=t)
					pm.pasteKey(node, time=rt+range_+time)

					inAngle = pm.keyTangent(node, query=True, time=t, inAngle=True)
					pm.keyTangent(node, edit=True, time=rt+range_+time, inAngle=-inAngle[0])








#module name
print (__name__)
# -----------------------------------------------
# Notes
# -----------------------------------------------