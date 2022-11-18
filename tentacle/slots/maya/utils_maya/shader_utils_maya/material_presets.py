# !/usr/bin/python
# coding=utf-8
import sys, os

from PySide2 import QtCore, QtWidgets

import pymel.core as pm

from switchboard import Switchboard
from utils import Utils
from utils_maya import Utils_maya


__version__ = '0.503'


class Stingray_arnold_shader(QtCore.QObject):
	'''
	To correctly render opacity and transmission, the Opaque setting needs to be disabled on the Shape node.
	If Opaque is enabled, opacity will not work at all. Transmission will work however any shadows cast by 
	the object will always be solid and not pick up the Transparent Color or density of the shader.
	'''
	msg_intro = '''<u>To setup the material:</u>
		<br>• Use the <b>Get Texture Maps</b> button to load the images you intend to use,
		<br>and click the <b>Create Network</b> button to create the shader connections.
		<br>• The HDR map, it's visiblity, and rotation can be changed after creation.
	'''
	msg_completed = '<br><hl style="color:rgb(0, 255, 255);"><b>COMPLETED.</b></hl>'

	proj_root_dir = Utils.getFilepath(__file__)
	hdr_env_name = 'aiSkyDomeLight_'

	def __init__(self, parent=None):
		super().__init__(parent)


	@property
	def hdr_env(self) -> object:
		'''
		'''
		node = pm.ls(self.hdr_env_name, exactType='aiSkyDomeLight')
		if not node:
			return None
		return node[0]


	@hdr_env.setter
	def hdr_env(self, tex) -> None:
		'''
		'''
		node = self.hdr_env #Utils_maya.nodeExists('aiSkyDomeLight', search='exactType')
		if not node:
			node = Utils_maya.createRenderNode('aiSkyDomeLight', 'asLight', name=self.hdr_env_name, camera=0, skyRadius=0) #turn off skydome and viewport visibility.
			self.hdr_env_transform.hiddenInOutliner.set(1)
			pm.outlinerEditor('outlinerPanel1', edit=True, refresh=True)

		file_node = Utils_maya.getIncomingNodeByType(node, 'file')
		if not file_node:
			file_node = Utils_maya.createRenderNode('file', 'as2DTexture', place2dTexture=True)
			pm.connectAttr(file_node.outColor, node.color, force=True)

		file_node.fileTextureName.set(tex)


	@property
	def hdr_env_transform(self) -> object:
		'''
		'''
		node = Utils_maya.getTransformNode(self.hdr_env)
		if not node:
			return None
		return node[0]


	def setHdrMapVisibility(self, state):
		'''
		'''
		node = self.hdr_env
		if node:
			node.camera.set(state)


	@Utils_maya.undo
	def createNetwork(self, textures, name='', hdrMap='', hdrMapVisibility=False, normalMapType='OpenGL', callback=print):
		'''
		'''
		normal_map_created_from_other_type = False
		normalMapType = 'Normal_'+normalMapType.strip('Normal_') #assure normalMapType is formatted as 'Normal_OpenGL' whether given as 'OpenGL' or 'Normal_OpenGL'

		if not textures:
			callback('<br><hl style="color:rgb(255, 100, 100);"><b>Error:</b> No textures given to createNetwork.</hl>')
			return None
		try:
			pm.loadPlugin('mtoa', quiet=True) #assure arnold plugin is loaded.
			pm.loadPlugin('shaderFXPlugin', quiet=True) #assure stringray plugin is loaded.

			sr_node = Utils_maya.createRenderNode('StingrayPBS', name=name)
			ai_node = Utils_maya.createRenderNode('aiStandardSurface', name=name+'_ai' if name else '')

			opacityMap = Utils.filterImagesByType(textures, 'Opacity')
			if opacityMap:
				pm.shaderfx(sfxnode='StingrayPBS1', loadGraph=r'C:/_local/_test/shaderfx/Standard_Transparent.sfx')

			openGLMap = Utils.filterImagesByType(textures, 'Normal_OpenGL')
			directXMap = Utils.filterImagesByType(textures, 'Normal_DirectX')
			if directXMap and not openGLMap and normalMapType=='Normal_OpenGL':
				mapPath = Utils.createGLFromDX(directXMap[0])
				textures.append(mapPath)
				normal_map_created_from_other_type = True
				callback('OpenGL map created using {}.'.format(Utils.truncate(directXMap[0], 20)))
			if openGLMap and not directXMap and normalMapType=='Normal_DirectX':
				mapPath = Utils.createDXFromGL(openGLMap[0])
				textures.append(mapPath)
				normal_map_created_from_other_type = True
				callback('DirectX map created using {}.'.format(Utils.truncate(openGLMap[0], 20)))

			srSG_node = Utils_maya.getOutgoingNodeByType(sr_node, 'shadingEngine')

			aiMult_node = pm.shadingNode('aiMultiply', asShader=True)

			bump_node = pm.shadingNode('bump2d', asShader=True)
			bump_node.bumpInterp.set(1) #set bump node to 'tangent space normals'

			Utils_maya.connectMultiAttr( #set node connections.
				(ai_node.outColor, srSG_node.aiSurfaceShader),
				(aiMult_node.outColor, ai_node.baseColor),
				(bump_node.outNormal, ai_node.normalCamera),
			)

			length = len(textures)
			progress = 0
			for f in textures:
				typ = Utils.getImageType(f)

				progress+=1

				#filter normal maps for the correct type.
				if typ=='Normal' and (openGLMap or directXMap):
					continue
				elif typ=='Normal_DirectX' and normalMapType=='Normal_OpenGL':
					continue
				elif typ=='Normal_OpenGL' and normalMapType=='Normal_DirectX':
					continue

				callback('creating nodes and connections for <b>{}</b> map ..'.format(typ), [progress, length])

				if typ=='Base_Color':
					n1 = Utils_maya.createRenderNode('file', 'as2DTexture', tex=f)
					pm.connectAttr(n1.outColor, sr_node.TEX_color_map, force=True)
					sr_node.use_color_map.set(1)

					n2 = Utils_maya.createRenderNode('file', 'as2DTexture', tex=f, place2dTexture=True)
					pm.connectAttr(n2.outColor, aiMult_node.input1, force=True)

				elif typ=='Roughness':
					n1 = Utils_maya.createRenderNode('file', 'as2DTexture', tex=f)
					pm.connectAttr(n1.outColor, sr_node.TEX_roughness_map, force=True)
					sr_node.use_roughness_map.set(1)

					n2 = Utils_maya.createRenderNode('file', 'as2DTexture', tex=f, place2dTexture=True, colorSpace='Raw', alphaIsLuminance=1, ignoreColorSpaceFileRules=1)
					pm.connectAttr(n2.outAlpha, ai_node.specularRoughness, force=True)
					pm.connectAttr(n2.outAlpha, ai_node.transmissionExtraRoughness, force=True) #opacity: same roughness map used in Specular Roughness to provide additional bluriness of refraction.

				elif typ=='Metallic':
					n1 = Utils_maya.createRenderNode('file', 'as2DTexture', tex=f)
					pm.connectAttr(n1.outColor, sr_node.TEX_metallic_map, force=True)
					sr_node.use_metallic_map.set(1)

					n2 = Utils_maya.createRenderNode('file', 'as2DTexture', tex=f, place2dTexture=True, colorSpace='Raw', alphaIsLuminance=1, ignoreColorSpaceFileRules=1)
					pm.connectAttr(n2.outAlpha, ai_node.metalness, force=True)

				elif typ=='Emissive':
					n1 = Utils_maya.createRenderNode('file', 'as2DTexture', tex=f)
					pm.connectAttr(n1.outColor, sr_node.TEX_emissive_map, force=True)
					sr_node.use_emissive_map.set(1)

					n2 = Utils_maya.createRenderNode('file', 'as2DTexture', tex=f, place2dTexture=True)
					pm.connectAttr(n2.outAlpha, ai_node.emission, force=True)
					pm.connectAttr(n2.outColor, ai_node.emissionColor, force=True)

				elif 'Normal' in typ:
					n1 = Utils_maya.createRenderNode('file', 'as2DTexture', tex=f)
					pm.connectAttr(n1.outColor, sr_node.TEX_normal_map, force=True)
					sr_node.use_normal_map.set(1)

					n2 = Utils_maya.createRenderNode('file', 'as2DTexture', tex=f, place2dTexture=True, colorSpace='Raw', alphaIsLuminance=1, ignoreColorSpaceFileRules=1)
					pm.connectAttr(n2.outAlpha, bump_node.bumpValue, force=True)

				elif typ=='Ambient_Occlusion':
					n1 = Utils_maya.createRenderNode('file', 'as2DTexture', tex=f)
					pm.connectAttr(n1.outColor, sr_node.TEX_ao_map, force=True)
					sr_node.use_ao_map.set(1)

					n2 = Utils_maya.createRenderNode('file', 'as2DTexture', tex=f, place2dTexture=True)
					pm.connectAttr(n2.outColor, aiMult_node.input2, force=True)

				elif typ=='Opacity':
					n1 = Utils_maya.createRenderNode('file', 'as2DTexture', tex=f)
					pm.connectAttr(n1.outAlpha, sr_node.opacity, force=True)
					sr_node.use_opacity_map.set(1)

					n2 = Utils_maya.createRenderNode('file', 'as2DTexture', tex=f, place2dTexture=True, colorSpace='Raw', alphaIsLuminance=1, ignoreColorSpaceFileRules=1)
					pm.connectAttr(n2.outAlpha, ai_node.transmission, force=True)
					pm.connectAttr(n2.outColor, ai_node.opacity, force=True)

				else:
					if normal_map_created_from_other_type:
						continue #do not show a warning for unconnected normal maps if it resulted from being converted to a different output type.
					callback('<br><hl style="color:rgb(255, 100, 100);"><b>Map type: <b>{}</b> not connected:<br></hl>'.format(typ, Utils.truncate(f, 60)), [progress, length])
					continue

				callback('<font style="color: rgb(80,180,100)">{}..connected successfully.</font>'.format(typ))
		except Exception as error:
			callback('<br><hl style="color:rgb(255, 100, 100);"><b>Error:</b>{}.</hl>'.format(error))

		self.hdr_env = hdrMap
		self.setHdrMapVisibility(hdrMapVisibility)



class Stingray_arnold_shader_slots(Stingray_arnold_shader):

	def __init__(self, **kwargs):
		'''
		'''
		self.ui = self.sb.currentUi

		self.imageFiles = None

		#set json file location.
		path = '{}/{}.json'.format(self.sb.defaultDir, 'stingray_arnold_shader')
		Utils.setJsonFile(path) #set json file name

		#add filenames|filepaths to the comboBox.
		hdr_path = '{}/resources/hdr'.format(self.proj_root_dir)
		hdr_filenames = Utils.getDirectoryContents(hdr_path, 'files', include='*.exr', stripExtension=True)
		hdr_fullpaths = Utils.getDirectoryContents(hdr_path, 'filepaths', include='*.exr')
		self.ui.cmb000.addItems_(dict(zip(hdr_filenames, hdr_fullpaths)), ascending=False)

		#initialize widgets with any saved values.
		self.ui.txt000.setText(Utils.getJson('mat_name'))
		self.ui.txt001.setText(self.msg_intro)
		hdr_map_visibility = Utils.getJson('hdr_map_visibility')
		if hdr_map_visibility:
			self.ui.chk000.setChecked(hdr_map_visibility)
		hdr_map = Utils.getJson('hdr_map')
		if hdr_map:
			self.ui.cmb000.setCurrentItem(hdr_map)
		normal_map_type = Utils.getJson('normal_map_type')
		if normal_map_type:
			self.ui.cmb001.setCurrentItem(normal_map_type)
		node = self.hdr_env_transform
		if node:
			rotation = node.rotateY.get()
			self.ui.slider000.setSliderPosition(rotation)


	@property
	def mat_name(self) -> str:
		'''Get the mat name from the user input text field.

		:Return:
			(str)
		'''
		text = self.ui.txt000.text()
		return text


	@property
	def hdr_map(self) -> str:
		'''Get the hdr map filepath from the comboBoxes current text.

		:Return:
			(str) data as string.
		'''
		data = self.ui.cmb000.currentData()
		return data


	@property
	def hdr_map_visibility(self) -> bool:
		'''Get the hdr map visibility state from the checkBoxes current state.

		:Return:
			(bool)
		'''
		state = self.ui.chk000.isChecked()
		return state


	@property
	def normal_map_type(self) -> str:
		'''Get the normal map type from the comboBoxes current text.

		:Return:
			(str)
		'''
		text = self.ui.cmb001.currentText()
		return text


	def cmb000(self, index):
		'''HDR map selection.
		'''
		cmb = self.ui.cmb000
		text = cmb.currentText()
		data = cmb.currentData()

		self.hdr_env = data #set the HDR map.
		Utils.setJson('hdr_map', text)


	def chk000(self, state):
		'''
		'''
		chk = self.ui.chk000

		self.setHdrMapVisibility(state) #set the HDR map visibility.
		Utils.setJson('hdr_map_visibility', state)


	def cmb001(self, index):
		'''Normal map output selection.
		'''
		cmb = self.ui.cmb001
		text = cmb.currentText()
		Utils.setJson('normal_map_type', text)


	def txt000(self, text=None):
		'''Material name.
		'''
		txt = self.ui.txt000
		text = txt.text()
		Utils.setJson('mat_name', text)


	def slider000(self, value):
		'''Rotate the HDR map.
		'''
		if self.hdr_env:
			transform = Utils_maya.getTransformNode(self.hdr_env)
			pm.rotate(transform, value, rotateY=True, forceOrderXYZ=True, objectSpace=True, absolute=True)


	def b000(self):
		'''Create network.
		'''
		if self.imageFiles:
			# pm.mel.HypershadeWindow() #open the hypershade window.

			self.ui.txt001.clear()
			self.callback('Creating network ..<br>')

			self.createNetwork(self.imageFiles, self.mat_name, hdrMap=self.hdr_map,
				hdrMapVisibility=self.hdr_map_visibility, normalMapType=self.normal_map_type, 
				callback=self.callback)

			self.callback(self.msg_completed)
			# pm.mel.hyperShadePanelGraphCommand('hyperShadePanel1', 'rearrangeGraph')


	def b001(self):
		'''Get texture maps.
		'''
		imageFiles = Utils.getImageFiles()
		if imageFiles:
			self.imageFiles = imageFiles
			self.ui.txt001.clear()

			msg_mat_selection = self.imageFiles
			for i in msg_mat_selection: #format msg_intro using the mapTypes in imtools.
				self.callback(Utils.truncate(i, 60))

			self.ui.b000.setDisabled(False)
		elif not self.imageFiles:
			self.ui.b000.setDisabled(True)


	def callback(self, string, progress=None, clear=False):
		'''
		:Parameters:
			string (str) = The text to output to a textEdit widget.
			progress (int)(list) = The progress amount to register with the progressBar.
				Can be given as an int or a tuple as: (progress, total_len) 
		'''
		if clear:
			self.ui.txt003.clear()

		if isinstance(progress, (list, tuple, set)):
			p, l = progress
			progress = (p/l) *100

		self.ui.txt001.append(string)

		if progress is not None:
			self.ui.progressBar.setValue(progress)
			QtWidgets.QApplication.processEvents()



class Stingray_arnold_shader_main(Stingray_arnold_shader):
	'''
	'''
	app = QtWidgets.QApplication.instance()
	if not app:
		app = QtWidgets.QApplication(sys.argv)

	def __init__(self, parent=None):
		super().__init__(parent)

		if not parent:
			self.setParent(Utils_maya.getMainWindow())

		self.sb = Switchboard(self, widgetLoc='ui/widgets', slotLoc=Stingray_arnold_shader_slots)

		self.ui = self.sb.stingray_arnold_shader
		self.sb.setStyle(self.ui.widgets)
		self.ui.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
		self.ui.show()









if __name__ == "__main__":

	main = Stingray_arnold_shader_main()

	# app = QtWidgets.QApplication.instance()
	# sys.exit(app.exec_()) # run app, show window, wait for input, then terminate program with a status code returned from app.


# --------------------------------
# Notes
# --------------------------------



# Deprecated ---------------------