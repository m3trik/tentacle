# !/usr/bin/python
# coding=utf-8
from tentacle.slots.maya import *
from tentacle.slots.cameras import Cameras


class Cameras_maya(Cameras, Slots_maya):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)

		# tree = self.sb.cameras_lower_submenu.tree000
		# l = ['Camera Sequencer', 'Camera Set Editor']
		# [tree.add('QLabel', 'Editors', setText=s) for s in l]

		# l = ['Exclusive to Camera', 'Hidden from Camera', 'Remove from Exclusive', 'Remove from Hidden', 'Remove All for Camera', 'Remove All']
		# [tree.add('QLabel', 'Per Camera Visibility', setText=s) for s in l]


	@property
	def clippingMenu(self):
		'''Menu: Camera clip plane settings.

		Return:
			(obj) menu as a property.
		'''
		if not hasattr(self, '_clippingMenu'):
			self._clippingMenu = self.sb.Menu(self.sb.cameras, position='cursorPos')
			self._clippingMenu.add('QPushButton', setText='Auto Clip', setObjectName='chk000', setCheckable=True, setToolTip='When Auto Clip is ON, geometry closer to the camera than 3 units is not displayed. Turn OFF to manually define.')
			self._clippingMenu.add('QDoubleSpinBox', setPrefix='Far Clip:  ', setObjectName='s000', setMinMax_='.01-10 step.1', setToolTip='Adjust the current cameras near clipping plane.')
			self._clippingMenu.add('QSpinBox', setPrefix='Near Clip: ', setObjectName='s001', setMinMax_='10-10000 step1', setToolTip='Adjust the current cameras far clipping plane.')

		#set widget states for the active camera
		activeCamera = mtk.Cam.getCurrentCam()
		if not activeCamera:
			self.sb.toggleWidgets(self._clippingMenu, setDisabled='s000-1,chk000')

		elif pm.viewClipPlane(activeCamera, query=1, autoClipPlane=1): #if autoClipPlane is active:
			self._clippingMenu.chk000.setChecked(True)
			self.sb.toggleWidgets(self._clippingMenu, setDisabled='s000-1')

		nearClip = pm.viewClipPlane(activeCamera, query=1, nearClipPlane=1) if activeCamera else 1.0
		farClip = pm.viewClipPlane(activeCamera, query=1, farClipPlane=1) if activeCamera else 1000.0

		self._clippingMenu.s000.setValue(nearClip)
		self._clippingMenu.s001.setValue(farClip)

		return self._clippingMenu


	def chk000(self, state=None):
		'''Camera Clipping: Auto Clip
		'''
		if self.clippingMenu.chk000.isChecked():
			self.sb.toggleWidgets(self.clippingMenu, setDisabled='s000-1')
		else:
			self.sb.toggleWidgets(self.clippingMenu, setEnabled='s000-1')

		activeCamera = mtk.Cam.getCurrentCam()
		if not activeCamera:
			self.sb.messageBox('No Active Camera.')
			return

		pm.viewClipPlane(activeCamera, autoClipPlane=True)


	def s000(self, value=None):
		'''Camera Clipping: Near Clip
		'''
		value = self.clippingMenu.s000.value()

		activeCamera = mtk.Cam.getCurrentCam()
		if not activeCamera:
			self.sb.messageBox('No Active Camera.')
			return

		pm.viewClipPlane(activeCamera, nearClipPlane=widget.value())


	def s001(self, value=None):
		'''Camera Clipping: Far Clip
		'''
		value = self.clippingMenu.s001.value()

		activeCamera = mtk.Cam.getCurrentCam()
		if not activeCamera:
			self.sb.messageBox('No Active Camera.')
			return

		pm.viewClipPlane(activeCamera, farClipPlane=widget.value())


	def tree000(self, wItem=None, column=None):
		'''
		'''
		tree = self.sb.cameras_lower_submenu.tree000

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
				pm.mel.eval('camera -centerOfInterest 5 -focalLength 35 -lensSqueezeRatio 1 -cameraScale 1 -horizontalFilmAperture 1.41732 -horizontalFilmOffset 0 -verticalFilmAperture 0.94488 -verticalFilmOffset 0 -filmFit Fill -overscan 1 -motionBlur 0 -shutterAngle 144 -nearClipPlane 0.1 -farClipPlane 10000 -orthographic 0 -orthographicWidth 30 -panZoomEnabled 0 -horizontalPan 0 -verticalPan 0 -zoom 1; objectMoveCommand; cameraMakeNode 1 "";')
			if text=='Set Custom Camera':
				pm.mel.eval('string $homeName = `cameraView -camera persp`;') #cameraView -edit -camera persp -setCamera $homeName;
			if text=='Camera From View':
				mtk.Cam.createCameraFromView()

		if header=='Cameras':
			pm.select(text)
			pm.lookThru(text)

		if header=='Editors':
			if text=='Camera Sequencer':
				pm.mel.eval('SequenceEditor;')
			if text=='Camera Set Editor':
				pm.mel.eval('cameraSetEditor;')

		if header=='Per Camera Visibility':
			if text=='Exclusive to Camera':
				pm.mel.eval('SetExclusiveToCamera;') #doPerCameraVisibility 0; Make selected objects exclusive to the selected (or current) camera.
			if text=='Hidden from Camera':
				pm.mel.eval('SetHiddenFromCamera;') #doPerCameraVisibility 1; Make selected objects hidden from the selected (or current) camera.
			if text=='Remove from Exclusive':
				pm.mel.eval('CameraRemoveFromExclusive;') #doPerCameraVisibility 2; Remove selected objects from the selected (or current) camera's exclusive list.
			if text=='Remove from Hidden':
				pm.mel.eval('CameraRemoveFromHidden;') #doPerCameraVisibility 3; Remove the selected objects from the selected (or current) camera's hidden list.
			if text=='Remove All for Camera': #Remove all hidden or exclusive objects for the selected (or current) camera.
				pm.mel.eval('CameraRemoveAll;') #doPerCameraVisibility 4; 
			if text=='Remove All':
				pm.mel.eval('CameraRemoveAllForAll;') #doPerCameraVisibility 5; Remove all hidden or exclusive objects for all cameras.

		if header=='Options':
			if text=='Group Cameras':
				mtk.Cam.groupCameras()
			if text=='Adjust Clipping':
				self.clippingMenu.show()
			if text=='Toggle Safe Frames': #Viewport Safeframes Toggle
				mtk.Cam.toggleSafeFrames()


	def v000(self):
		'''Cameras: Back View
		'''
		try: #if pm.objExists('back'):
			pm.lookThru('back')

		except Exception as error:
			cam, camShape = pm.camera() #create camera
			pm.lookThru(cam)

			pm.rename(cam, 'back')
			pm.viewSet(back=1) #initialize the camera view
			pm.hide(cam)

			grp = pm.ls('cameras', transforms=1)
			if grp and self.isGroup(grp[0]): #add the new cam to 'cameras' group (if it exists).
				pm.parent(cam, 'cameras')


	def v001(self):
		'''Cameras: Top View
		'''
		try:
			pm.lookThru('topShape')

		except Exception as error:
			pm.lookThru('|top')


	def v002(self):
		'''Cameras: Right View
		'''
		try:
			pm.lookThru('sideShape')

		except Exception as error:
			pm.lookThru('|side')


	def v003(self):
		'''Cameras: Left View
		'''
		try: #if pm.objExists('back'):
			pm.lookThru('left')

		except Exception as error:
			cam, camShape = pm.camera() #create camera
			pm.lookThru(cam)

			pm.rename(cam, 'left')
			pm.viewSet(leftSide=1) #initialize the camera view
			pm.hide(cam)

			grp = pm.ls('cameras', transforms=1)
			if grp and self.isGroup(grp[0]): #add the new cam to 'cameras' group (if it exists).
				pm.parent(cam, 'cameras')


	def v004(self):
		'''Cameras: Perspective View
		'''
		try:
			pm.lookThru('perspShape')

		except Exception as error:
			pm.lookThru('|persp')


	def v005(self):
		'''Cameras: Front View
		'''
		try:
			pm.lookThru('frontShape')

		except Exception as error:
			pm.lookThru('|front')


	def v006(self):
		'''Cameras: Bottom View
		'''
		try: #if pm.objExists('back'):
			pm.lookThru('bottom')

		except Exception as error:
			cam, camShape = pm.camera() #create camera
			pm.lookThru(cam)

			pm.rename(cam, 'bottom')
			pm.viewSet(bottom=1) #initialize the camera view
			pm.hide(cam)

			grp = pm.ls('cameras', transforms=1)
			if grp and self.isGroup(grp[0]): #add the new cam to 'cameras' group (if it exists).
				pm.parent(cam, 'cameras')


	def v007(self):
		'''Cameras: Align View
		'''
		selection = pm.ls(sl=1)
		if not selection:
			self.sb.messageBox('Nothing Selected.')
			return

		if not pm.objExists('alignToPoly'): #if no camera exists; create camera
			cam, camShape = pm.camera()
			pm.rename(cam, 'alignToPoly')
			pm.hide(cam)

			grp = pm.ls('cameras', transforms=1)
			if grp and self.isGroup(grp[0]): #add the new cam to 'cameras' group (if it exists).
				pm.parent(cam, 'cameras')

		ortho = int(pm.camera('alignToPoly', query=1, orthographic=1)) #check if camera view is orthoraphic
		if not ortho:
			pm.viewPlace('alignToPoly', ortho=1)

		pm.lookThru('alignToPoly')
		pm.AlignCameraToPolygon()
		pm.viewFit(fitFactor=5.0)

# --------------------------------------------------------------------------------------------









# --------------------------------------------------------------------------------------------

#module name
print (__name__)

# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------




#deprecated -------------------------------------


# def tree000(self, wItem=None, column=None):
# 		'''

# 		'''
# 		tree = self.sb.cameras.tree000

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
# 				pm.mel.eval('camera -centerOfInterest 5 -focalLength 35 -lensSqueezeRatio 1 -cameraScale 1 -horizontalFilmAperture 1.41732 -horizontalFilmOffset 0 -verticalFilmAperture 0.94488 -verticalFilmOffset 0 -filmFit Fill -overscan 1 -motionBlur 0 -shutterAngle 144 -nearClipPlane 0.1 -farClipPlane 10000 -orthographic 0 -orthographicWidth 30 -panZoomEnabled 0 -horizontalPan 0 -verticalPan 0 -zoom 1; objectMoveCommand; cameraMakeNode 1 "";')
# 			if text=='Set Custom Camera':
# 				pm.mel.eval('string $homeName = `cameraView -camera persp`;') #cameraView -edit -camera persp -setCamera $homeName;
# 			if text=='Camera From View':
# 				print('No Maya Version')

# 		if header=='Cameras':
# 			pm.select(text)
# 			pm.lookThru(text)

# 		if header=='Editors':
# 			if text=='Camera Sequencer':
# 				pm.mel.eval('SequenceEditor;')
# 			if text=='Camera Set Editor':
# 				pm.mel.eval('cameraSetEditor;')

# 		if header=='Options':
# 			if text=='Group Cameras':
# 				mtk.Cam.groupCameras()
# 			if text=='Adjust Clipping':
# 				self.clippingMenu.show()
# 			if text=='Toggle Safe Frames': #Viewport Safeframes Toggle
# 				mtk.Cam.toggleSafeFrames()



	# def cmb000(self, index=-1):
	# 	'''
	# 	Camera Editors

	# 	'''
	# 	cmb = self.sb.cameras.draggable_header.ctxMenu.cmb000
		
	# 	items = ['Camera Sequencer', 'Camera Set Editor']
	# 	contents = cmb.addItems_(items, '')

	# 	if not index:
	# 		index = cmb.currentIndex()
	# 	if index!=0:
	# 		if index==1:
	# 			pm.mel.eval('SequenceEditor;')
	# 		if index==2:
	# 			pm.mel.eval('cameraSetEditor;')
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

	# 	cmb = self.sb.cameras.cmb001
		
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
	# 	cmb = self.sb.cameras.cmb002
		
	# 	items = ['Custom Camera', 'Set Custom Camera', 'Camera From View']
	# 	contents = cmb.addItems_(items, "Create")

	# 	if not index:
	# 		index = cmb.currentIndex()
	# 	if index!=0:
	# 		if index==1:
	# 			pm.mel.eval('cameraView -edit -camera persp -setCamera $homeName;')
	# 		if index==2:
	# 			pm.mel.eval('string $homeName = `cameraView -camera persp`;')
	# 		if index==3:
	# 			pm.mel.eval('print "--no code--")
	# 		cmb.setCurrentIndex(0)


	# def cmb003(self, index=-1):
	# 	'''
	# 	Options

	# 	'''
	# 	cmb = self.sb.cameras.cmb003
		
	# 	items = ['Group Cameras']
	# 	contents = cmb.addItems_(items, "Options")

	# 	if not index:
	# 		index = cmb.currentIndex()
	# 	if index!=0:
	# 		if index==1:
	# 			pm.mel.eval('''
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
