# !/usr/bin/python
# coding=utf-8
from maya_init import *



class Cameras(Init):
	def __init__(self, *args, **kwargs):
		Init.__init__(self, *args, **kwargs)

		self.cameras_lower_ui = self.tcl.sb.getUi('cameras_lower_submenu')

		tree = self.cameras_lower_ui.tree000
		tree.expandOnHover = True
		tree.convert(tree.getTopLevelItems(), 'QLabel') #construct the tree using the existing contents.

		l = ['Camera Sequencer', 'Camera Set Editor']
		[tree.add('QLabel', 'Editors', setText=s) for s in l]

		l = ['Exclusive to Camera', 'Hidden from Camera', 'Remove from Exclusive', 'Remove from Hidden', 'Remove All for Camera', 'Remove All']
		[tree.add('QLabel', 'Per Camera Visibility', setText=s) for s in l]


	@property
	def clippingMenu(self):
		'''Menu: Camera clip plane settings.

		:Return:
			(obj) menu as a property.
		'''
		if not hasattr(self, '_clippingMenu'):
			self._clippingMenu = self.tcl.wgts.Menu(self.cameras_ui, position='cursorPos')
			self._clippingMenu.add('QPushButton', setText='Auto Clip', setObjectName='chk000', setCheckable=True, setToolTip='When Auto Clip is ON, geometry closer to the camera than 3 units is not displayed. Turn OFF to manually define.')
			self._clippingMenu.add('QDoubleSpinBox', setPrefix='Far Clip:  ', setObjectName='s000', setMinMax_='.01-10 step.1', setToolTip='Adjust the current cameras near clipping plane.')
			self._clippingMenu.add('QSpinBox', setPrefix='Near Clip: ', setObjectName='s001', setMinMax_='10-10000 step1', setToolTip='Adjust the current cameras far clipping plane.')

		#set widget states for the current activeCamera
		activeCamera = self.getCurrentCam()
		if not activeCamera:
			self.toggleWidgets(self._clippingMenu, setDisabled='s000-1,chk000')

		elif pm.viewClipPlane(activeCamera, query=1, autoClipPlane=1): #if autoClipPlane is active:
			self._clippingMenu.chk000.setChecked(True)
			self.toggleWidgets(self._clippingMenu, setDisabled='s000-1')

		nearClip = pm.viewClipPlane(activeCamera, query=1, nearClipPlane=1) if activeCamera else 1.0
		farClip = pm.viewClipPlane(activeCamera, query=1, farClipPlane=1) if activeCamera else 1000.0

		self._clippingMenu.s000.setValue(nearClip)
		self._clippingMenu.s001.setValue(farClip)

		return self._clippingMenu


	@Slots.message
	def chk000(self, state=None):
		'''Camera Clipping: Auto Clip
		'''
		if self.clippingMenu.chk000.isChecked():
			self.toggleWidgets(self.clippingMenu, setDisabled='s000-1')
		else:
			self.toggleWidgets(self.clippingMenu, setEnabled='s000-1')

		activeCamera = self.getCurrentCam()
		if not activeCamera:
			return 'Error: No Active Camera.'

		pm.viewClipPlane(activeCamera, autoClipPlane=True)


	def s000(self, value=None):
		'''Camera Clipping: Near Clip
		'''
		value = self.clippingMenu.s000.value()

		activeCamera = self.getCurrentCam()
		if not activeCamera:
			return 'Error: No Active Camera.'

		pm.viewClipPlane(activeCamera, nearClipPlane=widget.value())


	def s001(self, value=None):
		'''Camera Clipping: Far Clip
		'''
		value = self.clippingMenu.s001.value()

		activeCamera = self.getCurrentCam()
		if not activeCamera:
			return 'Error: No Active Camera.'

		pm.viewClipPlane(activeCamera, farClipPlane=widget.value())


	def tree000(self, wItem=None, column=None):
		'''
		'''
		tree = self.cameras_lower_ui.tree000

		if not any([wItem, column]): # code here will run before each show event. generally used to refresh tree contents. -----------------------------
			try:
				cameras = pm.ls(type=('camera'), l=True) #Get all cameras
				startup_cameras = [camera for camera in cameras if pm.camera(camera.parent(0), startupCamera=True, q=True)] #filter all startup / default cameras
				non_startup_cameras_pynodes = list(set(cameras) - set(startup_cameras)) #get non-default cameras. these are all PyNodes
				non_startup_cameras_transform_pynodes = map(lambda x: x.parent(0), non_startup_cameras_pynodes) #get respective transform names
				non_startup_cameras = map(str, non_startup_cameras_pynodes) #non-PyNode, regular string name list
				non_startup_cameras_transforms = map(str, non_startup_cameras_transform_pynodes)

			except AttributeError:
				non_startup_cameras=[]
			[tree.add('QLabel', 'Cameras', refresh=True, setText=s) for s in non_startup_cameras]
			return

		widget = tree.getWidget(wItem, column)
		text = tree.getWidgetText(wItem, column)
		header = tree.getHeaderFromColumn(column)

		if header=='Create':
			if text=='Custom Camera':
				mel.eval('camera -centerOfInterest 5 -focalLength 35 -lensSqueezeRatio 1 -cameraScale 1 -horizontalFilmAperture 1.41732 -horizontalFilmOffset 0 -verticalFilmAperture 0.94488 -verticalFilmOffset 0 -filmFit Fill -overscan 1 -motionBlur 0 -shutterAngle 144 -nearClipPlane 0.1 -farClipPlane 10000 -orthographic 0 -orthographicWidth 30 -panZoomEnabled 0 -horizontalPan 0 -verticalPan 0 -zoom 1; objectMoveCommand; cameraMakeNode 1 "";')
			if text=='Set Custom Camera':
				mel.eval('string $homeName = `cameraView -camera persp`;') #cameraView -edit -camera persp -setCamera $homeName;
			if text=='Camera From View':
				Cameras.createCameraFromView()

		if header=='Cameras':
			pm.select(text)
			pm.lookThru(text)

		if header=='Editors':
			if text=='Camera Sequencer':
				mel.eval('SequenceEditor;')
			if text=='Camera Set Editor':
				mel.eval('cameraSetEditor;')

		if header=='Per Camera Visibility':
			if text=='Exclusive to Camera':
				mel.eval('SetExclusiveToCamera;') #doPerCameraVisibility 0; Make selected objects exclusive to the selected (or current) camera.
			if text=='Hidden from Camera':
				mel.eval('SetHiddenFromCamera;') #doPerCameraVisibility 1; Make selected objects hidden from the selected (or current) camera.
			if text=='Remove from Exclusive':
				mel.eval('CameraRemoveFromExclusive;') #doPerCameraVisibility 2; Remove selected objects from the selected (or current) camera's exclusive list.
			if text=='Remove from Hidden':
				mel.eval('CameraRemoveFromHidden;') #doPerCameraVisibility 3; Remove the selected objects from the selected (or current) camera's hidden list.
			if text=='Remove All for Camera': #Remove all hidden or exclusive objects for the selected (or current) camera.
				mel.eval('CameraRemoveAll;') #doPerCameraVisibility 4; 
			if text=='Remove All':
				mel.eval('CameraRemoveAllForAll;') #doPerCameraVisibility 5; Remove all hidden or exclusive objects for all cameras.

		if header=='Options':
			if text=='Group Cameras':
				self.groupCameras()
			if text=='Adjust Clipping':
				self.clippingMenu.show()
			if text=='Toggle Safe Frames': #Viewport Safeframes Toggle
				self.toggleSafeFrames()


	def v000(self):
		'''Cameras: Back View
		'''
		if pm.objExists('back'):
			pm.lookThru('back')

		else:
			cameraName=pm.camera()
			#create camera
			#cameraName[0] = camera node
			#cameraName[1] = camera shape node
			#rename camera node
			pm.rename(cameraName[0], "back")
			pm.lookThru('back')

			#initialize the camera view
			pm.viewSet(back=1)

			#add to camera group
			if pm.objExists('cameras'):
				pm.parent('back', 'cameras')


	def v001(self):
		'''Cameras: Top View
		'''
		pm.lookThru("topShape")


	def v002(self):
		'''Cameras: Right View
		'''
		pm.lookThru("sideShape")


	def v003(self):
		'''Cameras: Left View
		'''
		if pm.objExists('left'):
			pm.lookThru('left')

		else:
			cameraName = pm.camera()
			#cameraName[0] = camera node
			#cameraName[1] = camera shape node
			pm.rename(cameraName[0], "left")
			pm.lookThru('left')

			#initialize the camera view
			pm.viewSet(leftSide=1)

			#add to camera group
			if pm.objExists('cameras'):
				pm.parent('left', 'cameras')


	def v004(self):
		'''Cameras: Perspective View
		'''
		pm.lookThru("perspShape")


	def v005(self):
		'''Cameras: Front View
		'''
		pm.lookThru("frontShape")


	def v006(self):
		'''Cameras: Bottom View
		'''
		if pm.objExists('bottom'):
			pm.lookThru('bottom')

		else:
			cameraName = pm.camera()
			#create camera
			#cameraName[0] = camera node
			#cameraName[1] = camera shape node
			pm.rename(cameraName[0], "bottom") #rename camera node
			pm.lookThru('bottom')

			#initialize the camera view
			pm.viewSet(bottom=1)
			#add to camera group
			if pm.objExists('cameras'):
				pm.parent('bottom', 'cameras')


	def v007(self):
		'''Cameras: Align View
		'''
		cameraExists = pm.objExists('alignToPoly')

		if cameraExists != 1: #if no camera exists; create camera
			camera = pm.camera()
			cameraShape = camera[1]
			pm.rename(camera[0], 
				("alignToPoly"))
			pm.hide('alignToPoly')
			
		isPerspective = int(not pm.camera('alignToPoly', query=1, orthographic=1))
		#check if camera view is orthoraphic
		if isPerspective:
			pm.viewPlace('alignToPoly', ortho=1)

		pm.lookThru('alignToPoly')
		pm.AlignCameraToPolygon()
		pm.viewFit(fitFactor=5.0)

		#add to camera group
		if pm.objExists('cameras'):
			pm.parent('alignToPoly', 'cameras')


	@staticmethod
	def groupCameras():
		'''Group Cameras
		'''
		if pm.objExists('cameras'):
			print ("# Error: Group 'cameras' already exists. #")
			return

		pm.group(world=1, name='cameras')
		pm.hide('cameras')

		cameras = ('side', 'front', 'top', 'persp', 'back', 'bottom', 'left', 'alignToPoly')

		for c in cameras:
			try:
				pm.parent(c, 'cameras')
			except Exception as error:
				pass


	@staticmethod
	def toggleSafeFrames():
		'''Toggle display of the film gate for the current camera.
		'''
		camera = Cameras.getCurrentCam()

		state = pm.camera(camera, query=1, displayResolution=1)
		if state:
			pm.camera(camera, edit=1, displayFilmGate=False, displayResolution=False, overscan=1.0)
		else:
			pm.camera(camera, edit=1, displayFilmGate=False, displayResolution=True, overscan=1.3)


	@staticmethod
	def getCurrentCam():
		'''Get the currently active camera.
		'''
		import maya.OpenMaya as OpenMaya
		import maya.OpenMayaUI as OpenMayaUI

		view = OpenMayaUI.M3dView.active3dView()
		cam = OpenMaya.MDagPath()
		view.getCamera(cam)
		camPath = cam.fullPathName()
		return camPath


	@staticmethod
	def createCameraFromView():
		'''Create a new camera base on the current view.
		'''
		from maya.cmds import getPanel #pymel getPanel is broken in ver: 2022.
		curPanel = getPanel(withFocus=True)
		if getPanel(typeOf=curPanel) == "modelPanel":
			camera = pm.modelPanel(curPanel, q=1, cam=1)
			newCamera = pm.duplicate(camera)[0]
			pm.showHidden(newCamera)
			# pm.mel.lookThroughModelPanel(newCamera, curPanel)
			newCamera_ = pm.rename(newCamera, 'Camera')
			print (newCamera_)
			return newCamera_









#module name
print (__name__)
# -----------------------------------------------
# Notes
# -----------------------------------------------




#deprecated -------------------------------------


# def tree000(self, wItem=None, column=None):
# 		'''

# 		'''
# 		tree = self.cameras_ui.tree000

# 		if not any([wItem, column]):
# 			if not tree.refresh: #static list items -----------
# 				tree.expandOnHover = True
# 				tree.convert(tree.getTopLevelItems(), 'QLabel') #construct the tree using the existing contents.

# 				l = []
# 				[tree.add('QLabel', 'Editors', setText=s) for s in l]
	

# 			#refreshed list items -----------------------------
# 			try:
# 				cameras = pm.ls(type=('camera'), l=True) #Get all cameras
# 				startup_cameras = [camera for camera in cameras if pm.camera(camera.parent(0), startupCamera=True, q=True)] #filter all startup / default cameras
# 				non_startup_cameras_pynodes = list(set(cameras) - set(startup_cameras)) #get non-default cameras. these are all PyNodes
# 				non_startup_cameras_transform_pynodes = map(lambda x: x.parent(0), non_startup_cameras_pynodes) #get respective transform names
# 				non_startup_cameras = map(str, non_startup_cameras_pynodes) #non-PyNode, regular string name list
# 				non_startup_cameras_transforms = map(str, non_startup_cameras_transform_pynodes)
# 			except AttributeError: non_startup_cameras=[]
# 			[tree.add('QLabel', 'Cameras', refresh=True, setText=s) for s in non_startup_cameras]

# 			l = ['Camera Sequencer', 'Camera Set Editor']
# 			[tree.add('QLabel', 'Editors', setText=s) for s in l]
# 			return

# 		widget = tree.getWidget(wItem, column)
# 		text = tree.getWidgetText(wItem, column)
# 		header = tree.getHeaderFromColumn(column)
# 		print(header, text, column)

# 		if header=='Create':
# 			if text=='Custom Camera':
# 				mel.eval('camera -centerOfInterest 5 -focalLength 35 -lensSqueezeRatio 1 -cameraScale 1 -horizontalFilmAperture 1.41732 -horizontalFilmOffset 0 -verticalFilmAperture 0.94488 -verticalFilmOffset 0 -filmFit Fill -overscan 1 -motionBlur 0 -shutterAngle 144 -nearClipPlane 0.1 -farClipPlane 10000 -orthographic 0 -orthographicWidth 30 -panZoomEnabled 0 -horizontalPan 0 -verticalPan 0 -zoom 1; objectMoveCommand; cameraMakeNode 1 "";')
# 			if text=='Set Custom Camera':
# 				mel.eval('string $homeName = `cameraView -camera persp`;') #cameraView -edit -camera persp -setCamera $homeName;
# 			if text=='Camera From View':
# 				print('No Maya Version')

# 		if header=='Cameras':
# 			pm.select(text)
# 			pm.lookThru(text)

# 		if header=='Editors':
# 			if text=='Camera Sequencer':
# 				mel.eval('SequenceEditor;')
# 			if text=='Camera Set Editor':
# 				mel.eval('cameraSetEditor;')

# 		if header=='Options':
# 			if text=='Group Cameras':
# 				self.groupCameras()
# 			if text=='Adjust Clipping':
# 				self.clippingMenu.show()
# 			if text=='Toggle Safe Frames': #Viewport Safeframes Toggle
# 				self.toggleSafeFrames()



	# def cmb000(self, index=-1):
	# 	'''
	# 	Camera Editors

	# 	'''
	# 	cmb = self.cameras_ui.draggable_header.contextMenu.cmb000
		
	# 	list_ = ['Camera Sequencer', 'Camera Set Editor']
	# 	contents = cmb.addItems_(list_, '')

	# 	if not index:
	# 		index = cmb.currentIndex()
	# 	if index!=0:
	# 		if index==1:
	# 			mel.eval('SequenceEditor;')
	# 		if index==2:
	# 			mel.eval('cameraSetEditor;')
	# 		cmb.setCurrentIndex(0)


	# def cmb001(self, index=-1):
	# 	'''
	# 	Additional Cameras

	# 	'''
	# 	# Get all cameras first
	# 	cameras = pm.ls(type=('camera'), l=True)
	# 	# Let's filter all startup / default cameras
	# 	startup_cameras = [camera for camera in cameras if pm.camera(camera.parent(0), startupCamera=True, q=True)]
	# 	# non-default cameras are easy to find now. Please note that these are all PyNodes
	# 	non_startup_cameras_pynodes = list(set(cameras) - set(startup_cameras))
	# 	# Let's get their respective transform names, just in-case
	# 	non_startup_cameras_transform_pynodes = map(lambda x: x.parent(0), non_startup_cameras_pynodes)
	# 	# Now we can have a non-PyNode, regular string names list of them
	# 	non_startup_cameras = map(str, non_startup_cameras_pynodes)
	# 	non_startup_cameras_transforms = map(str, non_startup_cameras_transform_pynodes)

	# 	cmb = self.cameras_ui.cmb001
		
	# 	contents = cmb.addItems_(non_startup_cameras, "Cameras")

	# 	if not index:
	# 		index = cmb.currentIndex()
	# 	if index!=0:
	# 		pm.select (contents[index])
	# 		cmb.setCurrentIndex(0)


	# def cmb002(self, index=-1):
	# 	'''
	# 	Create

	# 	'''
	# 	cmb = self.cameras_ui.cmb002
		
	# 	list_ = ['Custom Camera', 'Set Custom Camera', 'Camera From View']
	# 	contents = cmb.addItems_(list_, "Create")

	# 	if not index:
	# 		index = cmb.currentIndex()
	# 	if index!=0:
	# 		if index==1:
	# 			mel.eval('cameraView -edit -camera persp -setCamera $homeName;')
	# 		if index==2:
	# 			mel.eval('string $homeName = `cameraView -camera persp`;')
	# 		if index==3:
	# 			mel.eval('print "--no code--")
	# 		cmb.setCurrentIndex(0)


	# def cmb003(self, index=-1):
	# 	'''
	# 	Options

	# 	'''
	# 	cmb = self.cameras_ui.cmb003
		
	# 	list_ = ['Group Cameras']
	# 	contents = cmb.addItems_(list_, "Options")

	# 	if not index:
	# 		index = cmb.currentIndex()
	# 	if index!=0:
	# 		if index==1:
	# 			mel.eval('''
	# 			if (`objExists cameras`)
	# 			{
	# 			  print "Group 'cameras' already exists";
	# 			}
	# 			else
	# 			{
	# 			  group -world -name cameras side front top persp;
	# 			  hide cameras;
	# 			  // Now add non-default cameras to group
	# 			  if (`objExists back`)
	# 			  {
	# 			  	parent back cameras;
	# 			  }
	# 			  if (`objExists bottom`)
	# 			  {
	# 			  	parent bottom cameras;
	# 			  }
	# 			  if (`objExists left`)
	# 			  {
	# 			  	parent left cameras;
	# 			  }
	# 			  if (`objExists alignToPoly`)
	# 			  {
	# 			  	parent alignToPoly cameras;
	# 			  }
	# 			}
	# 			''')
	# 		cmb.setCurrentIndex(0)
