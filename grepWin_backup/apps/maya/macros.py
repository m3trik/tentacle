# !/usr/bin/python
# coding=utf-8
# from __future__ import print_function, absolute_import
# from __future__ import print_function, absolute_import
from builtins import super

import pymel.core as pm
import maya.mel as mel

from maya_init import Init



class Macros(Init):
	'''Custom scripts with assigned hotkeys.
	'''
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		'''
		'''


	def setMacros(self, macros=[]):
		'''Extends setMacro to accept a list of tuples.
		'''
		if not macros:
			macros = [
				('hk_back_face_culling', '1', 'Display', 'Toggle back-face culling.'),
				('hk_smooth_preview', '2', 'Display', 'Toggle smooth mesh preview.'),
				('hk_isolate_selected', 'F2', 'Display', 'Isolate current selection.'),
				('hk_grid_and_image_planes', 'F1', 'Display', 'Toggle grid and image plane visibility.'),
				('hk_frame_selected', 'f', 'Display', 'Frame selected by a set amount.'),
				('hk_wireframe_on_shaded', '3', 'Display', 'Toggle wireframe on shaded.'),
				('hk_xray', 'F3', 'Display', 'Toggle xRay all.'),
				('hk_wireframe', '5', 'Display', 'Toggle wireframe/shaded/shaded w/texture display.'),
				('hk_shading', '6', 'Display', 'Toggle viewport shading.'),
				('hk_selection_mode', 'sht+q', 'Edit', 'Toggle between object selection & last component selection.'),
				('hk_paste_and_rename', 'ctl+v', 'Edit', 'Paste and rename removing keyword \'paste\'.'),
				('hk_multi_component', 'F5', 'Edit', 'Multi-Component Selection.'),
				('hk_toggle_component_mask', 'F4', 'Edit', 'Toggle Component Selection Mask.'),
				('hk_main_show', 'F12', 'UI', 'Display main marking menu.'),
				('hk_hotbox_full', 'sht+z', 'UI', 'Display the full version of the hotbox.'),
				('hk_toggle_panels', '9', 'UI', 'Toggle UI toolbars.'),
				('hk_toggle_UV_select_type', 'sht+t', 'Edit', 'Toggle UV / UV shell component selection.'),
				('hk_merge_vertices', 'ctl+m', 'Edit', 'Merge vertices on selection.'),
			]

		for m in macros:
			self.setMacro(*m)


	def setMacro(self, name=None, k=None, cat=None, ann=None):
		'''Sets a default runtime command with a keyboard shotcut.

		:Parameters:
			name (str) = The command name you provide must be unique. The name itself must begin with an alphabetic character or underscore followed by alphanumeric characters or underscores.
			cat (str) = catagory - Category for the command.
			ann (str) = annotation - Description of the command.
			k (str) = keyShortcut - Specify what key is being set.
						key modifier values are set by adding a '+' between chars. ie. 'sht+z'.
						modifiers:
							alt, ctl, sht
						additional valid keywords are:
							Up, Down, Right, Left,
							Home, End, Page_Up, Page_Down, Insert
							Return, Space
							F1 to F12
							Tab (Will only work when modifiers are specified)
							Delete, Backspace (Will only work when modifiers are specified)
		'''
		command = self.formatSource(name, removeTabs=2)

		#set runTimeCommand
		pm.runTimeCommand(
				name,
				annotation=ann,
				category=cat,
				command=command,
				default=True,
		)

		#set command
		nameCommand = pm.nameCommand(
				'{0}Command'.format(name),
				annotation=ann,
				command=name,
		)

		#set hotkey
		#modifiers
		ctl=False; alt=False; sht=False
		for char in k.split('+'):
			if char=='ctl':
				ctl = True
			elif char=='alt':
				alt = True
			elif char=='sht':
				sht = True
			else:
				key = char

		# print(name, char, ctl, alt, sht)
		pm.hotkey(keyShortcut=key, name=nameCommand, ctl=ctl, alt=alt, sht=sht) #set only the key press.


	def formatSource(self, cmd, removeTabs=0):
		'''Return the text of the source code for an object.
		The source code is returned as a single string.
		Removes lines containing '@' or 'def ' ie. @staticmethod.

		:Parameters:
			cmd = module, class, method, function, traceback, frame, or code object.
			removeTabs (int) = remove x instances of '\t' from each line.

		:Return:
			A Multi-line string.
		'''
		from inspect import getsource
		source = getsource(getattr(Macros, cmd))

		l = [s.replace('\t', '', removeTabs) for s in source.split('\n') if s and not '@' in s and not 'def ' in s]
		return '\n'.join(l)



	# Display --------------------------------------------------------------------------------------------------------------------------------

	@staticmethod
	def setWireframeOnShadedOption(editor, state, smoothWireframe=True, activeOnly=False):
		'''Set Wireframe On Shaded.

		:Parameters:
			editor (str) = The panel name.
			state (bool) = The desired on or off state.
		'''
		modeIsShaded = pm.modelEditor(editor, query=True, displayAppearance=True) #True if "smoothShaded", "flatShaded".

		if state and not modeIsShaded:
			pm.modelEditor(editor, edit=True, displayAppearance=True, activeOnly=activeOnly, wireframeOnShaded=1, smoothWireframe=smoothWireframe) #displayAppearance: Possible values: "wireframe", "points", "boundingBox", "smoothShaded", "flatShaded"
		else:
			pm.modelEditor(editor, edit=True, wireframeOnShaded=0)


	@staticmethod
	def hk_back_face_culling():
		'''hk_back_face_culling
		Toggle Back-Face Culling.
		'''
		sel = pm.ls(selection=True)
		if sel:
			currentPanel = pm.getPanel(withFocus=True)
			state = pm.polyOptions(sel, query=True, wireBackCulling=True)[0]

			if not state:
				pm.polyOptions(sel, gl=True, wireBackCulling=True)
				Macros.setWireframeOnShadedOption(currentPanel, 0)
				pm.inViewMessage(statusMessage="Back-Face Culling is now <hl>OFF</hl>.>", pos='topCenter', fade=True)
			else:
				pm.polyOptions(sel, gl=True, backCulling=True)
				Macros.setWireframeOnShadedOption(currentPanel, 1)
				pm.inViewMessage(statusMessage="Back-Face Culling is now <hl>ON</hl>.", pos='topCenter', fade=True)
		else:
			print(" Warning: Nothing selected. ")


	@staticmethod
	def hk_smooth_preview():
		'''hk_smooth_preview
		Toggle smooth mesh preview.

		#smooth mesh attributes:
		setAttr ($nodeName + ".displaySmoothMesh") $smoothMesh;
		setAttr ($nodeName + ".smoothMeshSelectionMode") $selMode;
		setAttr ($nodeName + ".smoothLevel") $newLevel;
		setAttr ($nodeName + ".displaySubdComps") $subDivs;
		setAttr ($nodeName + ".continuity") $newCont;
		setAttr ($nodeName + ".smoothUVs") $smoothUVs;
		setAttr ($nodeName + ".propagateEdgeHardness") $propEdgeHardness;
		setAttr ($nodeName + ".keepMapBorders") $newMapBorders;
		setAttr ($nodeName + ".keepBorder") $keepBorder;
		setAttr ($nodeName + ".keepHardEdge") $keepHardEdge;
		'''
		selection=pm.ls(selection=1)
		scene=pm.ls(geometry=1)

		#if no object selected smooth all geometry
		if len(selection)==0:
			state = Macros.cycle([0,1,2], 'hk_smooth_preview')

			for obj in scene:
				obj = obj.split('.')[0] #get u'pSphereShape1' from u'pSphereShape1.vtx[105]' if in component mode.

				if state is 0: #if pm.getAttr(str(obj) + ".displaySmoothMesh") != 2:
					pm.setAttr((str(obj) + ".displaySmoothMesh"), 2) #smooth preview on
					pm.displayPref(wireframeOnShadedActive="none") #selection wireframe off
					pm.inViewMessage(position='topCenter', fade=1, statusMessage="S-Div Preview <hl>ON</hl>.<br>Wireframe <hl>Off</hl>.")

				elif state is 1:
					pm.setAttr((str(obj) + ".displaySmoothMesh"), 2) #smooth preview on
					pm.displayPref(wireframeOnShadedActive="full") #selection wireframe off
					pm.inViewMessage(position='topCenter', fade=1, statusMessage="S-Div Preview <hl>ON</hl>.<br>Wireframe <hl>Full</hl>.")

				else:
					pm.setAttr((str(obj) + ".displaySmoothMesh"), 0) #smooth preview off
					pm.displayPref(wireframeOnShadedActive="full") #selection wireframe on
					pm.inViewMessage(position='topCenter', fade=1, statusMessage="S-Div Preview <hl>OFF</hl>.<br>Wireframe <hl>Full</hl>.")

				if pm.getAttr(str(obj) + ".smoothLevel") != 1:
					pm.setAttr((str(obj) + ".smoothLevel"), 1)

		#smooth selection only
		for obj in selection:
			obj = obj.split('.')[0] #get u'pSphereShape1' from u'pSphereShape1.vtx[105]' if in component mode.

			if pm.getAttr(str(obj) + ".displaySmoothMesh") != 2:
				pm.setAttr((str(obj) + ".displaySmoothMesh"), 2) #smooth preview on
				pm.displayPref(wireframeOnShadedActive="none") #selection wireframe off
				pm.inViewMessage(position='topCenter', fade=1, statusMessage="S-Div Preview <hl>ON</hl>.<br>Wireframe <hl>Off</hl>.")

			elif pm.getAttr(str(obj) + ".displaySmoothMesh") == 2 and pm.displayPref(query=1, wireframeOnShadedActive=1)=='none':
				pm.setAttr((str(obj) + ".displaySmoothMesh"), 2) #smooth preview on
				pm.displayPref(wireframeOnShadedActive="full") #selection wireframe full
				shapes = pm.listRelatives(selection, children=1, shapes=1) #get shape node from transform: returns list ie. [nt.Mesh('pConeShape1')]
				[pm.setAttr(s.displaySubdComps, 1) for s in shapes] #turn on display subdivisions for wireframe during smooth preview.
				pm.inViewMessage(position='topCenter', fade=1, statusMessage="S-Div Preview <hl>ON</hl>.<br>Wireframe <hl>Full</hl>.")

			else:
				pm.setAttr((str(obj) + ".displaySmoothMesh"), 0) #smooth preview off
				pm.displayPref(wireframeOnShadedActive="full") #selection wireframe full
				pm.inViewMessage(position='topCenter', fade=1, statusMessage="S-Div Preview <hl>OFF</hl>.<br>Wireframe <hl>Full</hl>.")

			if pm.getAttr(str(obj) + ".smoothLevel") != 1:
				pm.setAttr((str(obj) + ".smoothLevel"), 1)


	@staticmethod
	def hk_isolate_selected():
		'''hk_isolate_selected
		Isolate the current selection.
		'''
		currentPanel = pm.getPanel(withFocus=1)
		state = pm.isolateSelect(currentPanel, query=1, state=1)
		if state:
			pm.isolateSelect(currentPanel, state=0)
			pm.isolateSelect(currentPanel, removeSelected=1)
		else:
			pm.isolateSelect(currentPanel, state=1)
			pm.isolateSelect(currentPanel, addSelected=1)


	@staticmethod
	def hk_grid_and_image_planes():
		'''hk_grid_and_image_planes
		Toggle grid and image plane visibility.
		'''
		image_plane = pm.ls(exactType='imagePlane')

		for obj in image_plane:
			attr = obj+'.displayMode'
			if not pm.getAttr(attr)==2:
				pm.setAttr(attr, 2)
				pm.grid(toggle=1)
				pm.inViewMessage(statusMessage="Grid is now <hl>ON</hl>.", pos='topCenter', fade=True)
			else:
				pm.setAttr(attr, 0)
				pm.grid(toggle=0)
				pm.inViewMessage(statusMessage="Grid is now <hl>OFF</hl>.", pos='topCenter', fade=True)


	@staticmethod
	def hk_frame_selected():
		'''hk_frame_selected
		Frame selected by a set amount.
		'''
		pm.melGlobals.initVar('int', 'toggleFrame_')
		selection = pm.ls(selection=1)
		mode = pm.selectMode(query=1, component=1)
		maskVertex = pm.selectType(query=1, vertex=1)
		maskEdge = pm.selectType(query=1, edge=1)
		maskFacet = pm.selectType(facet=1, query=1)
		if len(selection) == 0:
			pm.viewFit(allObjects=1)
			
		if mode == 1 and maskVertex == 1 and len(selection) != 0:
			if len(selection)>1:
				if not pm.melGlobals['toggleFrame_'] == 1:
					pm.viewFit(fitFactor=.65)
					pm.melGlobals['toggleFrame_']=1
					print("frame vertices " + str(pm.melGlobals['toggleFrame_']) + "\n")

				else:
					pm.viewFit(fitFactor=.10)
					#viewSet -previousView;
					pm.melGlobals['toggleFrame_']=0
					print("frame vertices " + str(pm.melGlobals['toggleFrame_']) + "\n")
			
			elif not pm.melGlobals['toggleFrame_'] == 1:
				pm.viewFit(fitFactor=.15)
				pm.melGlobals['toggleFrame_']=1
				print("frame vertex " + str(pm.melGlobals['toggleFrame_']) + "\n")
			
			else:
				pm.viewFit(fitFactor=.01)
				#viewSet -previousView;
				pm.melGlobals['toggleFrame_']=0
				print("frame vertex " + str(pm.melGlobals['toggleFrame_']) + "\n")
			
		if mode == 1 and maskEdge == 1 and len(selection) != 0:
			if not pm.melGlobals['toggleFrame_'] == 1:
				pm.viewFit(fitFactor=.3)
				pm.melGlobals['toggleFrame_']=1
				print("frame edge " + str(pm.melGlobals['toggleFrame_']) + "\n")
			
			else:
				pm.viewFit(fitFactor=.9)
				#viewSet -previousView;
				pm.melGlobals['toggleFrame_']=0
				print("frame edge " + str(pm.melGlobals['toggleFrame_']) + "\n")
			
		if mode == 1 and maskFacet == 1:
			if not pm.melGlobals['toggleFrame_'] == 1:
				pm.viewFit(fitFactor=.9)
				pm.melGlobals['toggleFrame_']=1
				print("frame facet " + str(pm.melGlobals['toggleFrame_']) + "\n")
			
			else:
				pm.viewFit(fitFactor=.45)
				#viewSet -previousView;
				pm.melGlobals['toggleFrame_']=0
				print("frame facet " + str(pm.melGlobals['toggleFrame_']) + "\n")

		elif mode == 0 and len(selection) != 0:
			if not pm.melGlobals['toggleFrame_'] == 1:
				pm.viewFit(fitFactor=.99)
				pm.melGlobals['toggleFrame_']=1
				print("frame object " + str(pm.melGlobals['toggleFrame_']) + "\n")
			
			else:
				pm.viewFit(fitFactor=.65)
				#viewSet -previousView;
				pm.melGlobals['toggleFrame_']=0
				print("frame object " + str(pm.melGlobals['toggleFrame_']) + "\n")


	@staticmethod
	def hk_wireframe_on_shaded():
		'''hk_wireframe_on_shaded
		Toggle wireframe on shaded.
		'''
		currentPanel = pm.getPanel(withFocus=True)
		state = Macros.cycle([0,1,2], 'hk_wireframe_on_shaded')

		if state is 0:
			# Macros.setWireframeOnShadedOption(currentPanel, 1, 1)
			pm.displayPref(wireframeOnShadedActive="full") #selection wireframe full
			pm.inViewMessage(position='topCenter', fade=1, statusMessage="Wireframe <hl>Full</hl>.")

		if state is 1:
			# Macros.setWireframeOnShadedOption(currentPanel, 1, 0)
			pm.displayPref(wireframeOnShadedActive="reduced") #selection wireframe reduced
			pm.inViewMessage(position='topCenter', fade=1, statusMessage="Wireframe <hl>Reduced</hl>.")

		if state is 2:
			# Macros.setWireframeOnShadedOption(currentPanel, 0, 0)
			pm.displayPref(wireframeOnShadedActive="none") #selection wireframe off
			pm.inViewMessage(position='topCenter', fade=1, statusMessage="Wireframe <hl>Off</hl>.")


	@staticmethod
	def hk_xray():
		'''hk_xray
		Toggle xRay all except selected.
		'''
		#xray all except selected
		scene = pm.ls(visible=1, dag=1, noIntermediate=1, flatten=1, type='surfaceShape')
		selection = pm.ls(shapes=1, selection=1, dagObjects=1)
		for obj in scene:
			if not obj in selection:
				state = pm.displaySurface(obj, xRay=1, query=1)
				pm.displaySurface(obj, xRay=(not state[0]))


	@staticmethod
	def hk_wireframe():
		'''hk_wireframe
		Toggle wireframe/shaded/shaded w/texture display.
		'''
		currentPanel = pm.getPanel(withFocus=1)
		state = pm.modelEditor(currentPanel, query=1, displayAppearance=1)
		displayTextures = pm.modelEditor(currentPanel, query=1, displayTextures=1)

		if pm.modelEditor(currentPanel, exists=True):
			if not state=="wireframe" and displayTextures==False:
				pm.modelEditor(currentPanel, edit=1, displayAppearance='smoothShaded', activeOnly=False, displayTextures=True)
				pm.inViewMessage(statusMessage="modelEditor smoothShaded <hl>True</hl> displayTextures <hl>True</hl>.", pos='topCenter', fade=True)

			if state=="wireframe" and displayTextures==True:
				pm.modelEditor(currentPanel, edit=1, displayAppearance='smoothShaded', activeOnly=False, displayTextures=False)
				pm.inViewMessage(statusMessage="modelEditor smoothShaded <hl>True</hl> displayTextures <hl>False</hl>.>", pos='topCenter', fade=True)

			if not state=="wireframe" and displayTextures==True:
				pm.modelEditor(currentPanel, edit=1, displayAppearance='wireframe', activeOnly=False)
				pm.inViewMessage(statusMessage="modelEditor Wireframe <hl>True</hl>.", pos='topCenter', fade=True)


	@staticmethod
	def hk_shading():
		'''hk_shading
		Toggle viewport shading.
		'''
		currentPanel = pm.getPanel (withFocus=1)
		displayAppearance = pm.modelEditor (currentPanel, query=1, displayAppearance=1)
		displayTextures = pm.modelEditor (currentPanel, query=1, displayTextures=1)
		displayLights = pm.modelEditor (currentPanel, query=1, displayLights=1)

		#print(displayAppearance, displayTextures, displayLights)
		if pm.modelEditor (currentPanel, exists=1):
			if all ([displayAppearance=="wireframe", displayTextures==False, displayLights=="default"]):
				pm.modelEditor (currentPanel, edit=1, displayAppearance="smoothShaded", displayTextures=False, displayLights="default") #textures off
				pm.inViewMessage (statusMessage="modelEditor -smoothShaded <hl>true</hl> -displayTextures <hl>false</hl>.", fade=True, position="topCenter")
			elif all ([displayAppearance=="smoothShaded", displayTextures==False, displayLights=="default"]):
				pm.modelEditor (currentPanel, edit=1, displayAppearance="smoothShaded", displayTextures=True, displayLights="default") #textures on
				pm.inViewMessage (statusMessage="modelEditor -smoothShaded <hl>true</hl> -displayTextures <hl>true</hl>.", fade=True, position="topCenter")	
			elif all ([displayAppearance=="smoothShaded", displayTextures==True, displayLights=="default"]):
				pm.modelEditor (currentPanel, edit=1, displayAppearance="smoothShaded", displayTextures=True, displayLights="active") #lighting on
				pm.inViewMessage (statusMessage="modelEditor -smoothShaded <hl>true</hl> -displayLights <hl>true</hl>.", fade=True, position="topCenter")	
			else: #use else for starting condition in case settings are changed elsewhere and none of the conditions are met:
				pm.modelEditor (currentPanel, edit=1, displayAppearance="wireframe", displayTextures=False, displayLights="default") #wireframe
				pm.inViewMessage (statusMessage="modelEditor -wireframe <hl>true</hl>.", fade=True, position="topCenter")



	# Edit -----------------------------------------------------------------------------------------------------------------------------------

	@staticmethod
	def hk_selection_mode():
		'''hk_selection_mode
		Toggle between object selection & last component selection.
		'''
		objectMode = pm.selectMode(query=True, object=True)
		if objectMode:
			pm.selectMode(component=True)
		else:
			pm.selectMode(object=True)


	@staticmethod
	def hk_toggle_UV_select_type():
		'''hk_toggle_UV_select_type
		Toggle between UV & UV shell component selection.
		'''
		meshUVShell = pm.selectType(q=1, meshUVShell=1)
		# polymeshUV = pm.selectType(q=1, polymeshUV=1)
		pm.selectMode(component=1)

		if meshUVShell:
			#select all uv shells if in object mode and objects are selected.
			objects = pm.ls(sl=1, objectsOnly=1)
			objectMode = pm.selectMode(query=1, object=1)
			if objects and objectMode:
				for obj in objects:
					pm.selectMode(component=1)
					pm.selectType(meshUVShell=1)
					faces = Init.getComponents('f', obj, flatten=False)
					pm.select(faces, add=True)

			pm.selectType(polymeshUV=1)
			pm.inViewMessage(statusMessage='Select Type: <hl>Polymesh UV</hl>', fade=True, position="topCenter")
		else:
			pm.selectType(meshUVShell=1)
			pm.inViewMessage(statusMessage='Select Type: <hl>UV Shell</hl>', fade=True, position="topCenter")


	@staticmethod
	def hk_paste_and_rename():
		'''hk_paste_and_rename
		Paste and rename removing keyword 'paste'.
		'''
		pm.mel.cutCopyPaste("paste")
		#paste and then re-name object removing keyword 'pasted'
		pasted=pm.ls("pasted__*")
		obj = ""
		for obj in pasted:
			elements = []
			# The values returned by ls may be full or partial dag
			# paths - when renaming we only want the actual
			# object name so strip off the leading dag path.
			#
			elements=obj.split("|")
			stripped=elements[- 1]
			# Remove the 'pasted__' suffix from the name
			#
			stripped=stripped.replace("pasted__","")
			# When renaming a transform its shape will automatically be
			# be renamed as well. Use catchQuiet here to ignore errors
			# when trying to rename the child shape a second time.
			# 
			pm.catch(lambda: pm.evalEcho("rename " + str(obj) + " " + stripped))


	@staticmethod
	def hk_multi_component():
		'''hk_multi_component
		Multi-Component Selection.
		'''
		pm.SelectMultiComponentMask()
		pm.inViewMessage(statusMessage="<hl>Multi-Component Selection Mode</hl><br>Mask is now <hl>ON</hl>.", fade=True, position="topCenter")


	@staticmethod
	def hk_toggle_component_mask():
		'''hk_toggle_component_mask
		Toggle Component Selection Mask.
		'''
		mode=pm.selectMode(query=1, component=1)
		if mode == 0:
			pm.mel.changeSelectMode('-component')
			
		maskVertex=pm.selectType(query=1, vertex=1)
		maskEdge=pm.selectType(query=1, edge=1)
		maskFacet=pm.selectType(facet=1, query=1)
		if maskEdge == 0 and maskFacet == 1:
			pm.selectType(vertex=True)
			pm.inViewMessage(position='topCenter', fade=1, statusMessage="<hl>Vertex</hl> Mask is now <hl>ON</hl>.")
			
		if maskVertex == 1 and maskFacet == 0:
			pm.selectType(edge=True)
			pm.inViewMessage(position='topCenter', fade=1, statusMessage="<hl>Edge</hl> Mask is now <hl>ON</hl>.")
			
		if maskVertex == 0 and maskEdge == 1:
			pm.selectType(facet=True)
			pm.inViewMessage(position='topCenter', fade=1, statusMessage="<hl>Facet</hl> Mask is now <hl>ON</hl>.")


	@staticmethod
	def hk_merge_vertices():
		'''hk_merge_vertices
		Merge Vertices.
		'''
		tolerance = 0.001
		selection = pm.ls(selection=1, objectsOnly=1)

		if not selection:
			pm.inViewMessage(statusMessage="Warning: <hl>Nothing selected</hl>.<br>Must select an object or component.", pos='topCenter', fade=True)

		else:
			for obj in selection:

				if pm.selectMode(query=1, component=1): #merge selected components.
					if pm.filterExpand(selectionMask=31): #selectionMask=vertices
						pm.polyMergeVertex(distance=tolerance, alwaysMergeTwoVertices=True, constructionHistory=True)
					else: #if selection type =edges or facets:
						mel.eval("MergeToCenter;")

				else: #if object mode. merge all vertices on the selected object.
					for n, obj in enumerate(selection):

						# get number of vertices
						count = pm.polyEvaluate(obj, vertex=1)
						vertices = str(obj) + ".vtx [0:" + str(count) + "]" # mel expression: select -r geometry.vtx[0:1135];
						pm.polyMergeVertex(vertices, distance=tolerance, alwaysMergeTwoVertices=False, constructionHistory=False)

					#return to original state
					pm.select(clear=1)

					for obj in selection:
						pm.select(obj, add=1)


	# Selection ------------------------------------------------------------------------------------------------------------------------------

	@staticmethod
	def hk_invert_component_selection():
		'''hk_invert_component_selection
		Invert the component selection on the currently selected objects.
		'''
		if not pm.selectMode(query=1, component=1): #component select mode
			return 'Error: Selection must be at the component level.'

		objects = pm.ls(sl=1, objectsOnly=1)
		selection = pm.ls(sl=1)

		invert=[]
		for obj in objects:
			if pm.selectType(query=1, vertex=1): #vertex
				selectedVertices = pm.filterExpand(selection, selectionMask=31, expand=1)
				allVertices = pm.filterExpand(obj+'.v[*]', sm=31)
				invert += {v for v in allVertices if v not in selectedVertices}

			elif pm.selectType(query=1, edge=1): #edge
				edges = pm.filterExpand(selection, selectionMask=32, expand=1)
				allEdges = pm.filterExpand(obj+'.e[*]', sm=32)
				invert += {e for e in allEdges if e not in selectedEdges}

			elif pm.selectType(query=1, facet=1): #face
				selectedFaces = pm.filterExpand(selection, selectionMask=34, expand=1)
				allFaces = pm.filterExpand(obj+'.f[*]', sm=34)
				invert += {f for f in allFaces if f not in selectedFaces}

		pm.select(invert, replace=1)



	# UI -------------------------------------------------------------------------------------------------------------------------------------

	@staticmethod
	def hk_main_show():
		'''hk_main_show
		Display main marking menu.

		profile: Prints the total running time, times each function separately, and tells you how many times each function was called.
		'''
		if 'radial' not in locals() and 'radial' not in globals():
			from main_maya import Instance
			radial = Instance(key_show='key_F12')

		radial.show('init')
		# import cProfile
		# cProfile.run('main.show_()')


	@staticmethod
	def hk_hotbox_full():
		'''hk_hotbox_full
		Display the full version of the hotbox.
		'''
		pm.hotBox(polygonsOnlyMenus=1, displayHotbox=1)
		pm.hotBox()


	@staticmethod
	def hk_toggle_panels():
		'''hk_toggle_panels
		Toggle UI toolbars.
		'''
		if pm.menu('MayaWindow|HotBoxControlsMenu', q=1, ni=1) == 0:
			pm.setParent('MayaWindow|HotBoxControlsMenu', m=1)
			# added this expression to fix 'toggleMainMenubar function not found' error
			pm.mel.source('HotboxControlsMenu')

		#toggle panel menus
		panels=pm.getPanel(allPanels=1)
		state=int(pm.panel(panels[0], menuBarVisible=1, query=1))
		for panel in panels:
			pm.panel(panel, edit=1, menuBarVisible=(not state))
			# int $state = `panel -query -menuBarVisible $panel`;
			
		pm.mel.toggleMainMenubar(not state)
		#toggle main menubar
		#toggle titlebar
		pm.window(gMainWindow, edit=1, titleBar=(not state))

		# //toggle fullscreen mode //working but issues with windows resizing on toggle
		# inFullScreenMode=int(pm.optionVar(q="workspacesInFullScreenUIMode"))
		# inZoomInMode=int(pm.optionVar(q="workspacesInZoomInUIMode"))
		# # enter full screen mode only if the zoom-in mode is not active.
		# if not inZoomInMode:
		# 	panelWithFocus=str(pm.getPanel(withFocus=1))
		# 	parentControl=str(pm.workspaceLayoutManager(parentWorkspaceControl=panelWithFocus))
		# 	isFloatingPanel=int(pm.workspaceControl(parentControl, q=1, floating=1))
		# 	if not isFloatingPanel:
		# 		if inFullScreenMode:
		# 			pm.workspaceLayoutManager(restoreMainWindowControls=1)
		# 			#come out of fullscreen mode
					
				
		# 		else:
		# 			pm.workspaceLayoutManager(collapseMainWindowControls=(parentControl, True))
		# 			# enter fullscreen mode
					
		# 		pm.optionVar(iv=("workspacesInFullScreenUIMode", (not inFullScreenMode)))
				






# -----------------------------------------------
# Notes
# -----------------------------------------------

'''
#create wrapper
mel.createMelWrapper(method)

#set command
pm.nameCommand('name', annotation='', command=<>)
pm.hotkey(key='1', altModifier=True, name='name')


#clear keyboard shortcut
pm.hotkey(keyShortcut=key, name='', releaseName='', ctl=ctl, alt=alt, sht=sht) #unset the key press name and releaseName.


#query runTimeCommand
if pm.runTimeCommand('name', exists=True):


#delete runTimeCommand
pm.runTimeCommand('name', edit=True, delete=True)


#set runTimeCommand
pm.runTimeCommand(
			'name',
			annotation=string,
			category=string,
			categoryArray,
			command=script,
			commandArray,
			commandLanguage=string,
			default=boolean,
			defaultCommandArray,
			delete,
			exists,
			hotkeyCtx=string,
			image=string,
			keywords=string,
			annotation=string,
			longAnnotation=string,
			numberOfCommands,
			numberOfDefaultCommands,
			numberOfUserCommands,
			plugin=string,
			save,
			showInHotkeyEditor=boolean,
			tags=string,
			userCommandArray,
)

-annotation(-ann) string createqueryedit 
		Description of the command.

-category(-cat) string createqueryedit	
		Category for the command.

-categoryArray(-caa) query			
		Return all the run time command categories.

-command(-c) script createqueryedit		
		Command to be executed when runTimeCommand is invoked.

-commandArray(-ca) query				
		Returns an string array containing the names of all the run time commands.

-commandLanguage(-cl) string createqueryedit
		In edit or create mode, this flag allows the caller to choose a scripting language for a command passed to the "-command" flag. If this flag is not specified, then the callback will be assumed to be in the language from which the runTimeCommand command was called. In query mode, the language for this runTimeCommand is returned. The possible values are "mel" or "python".

-default(-d) boolean createquery 		
		Indicate that this run time command is a default command. Default run time commands will not be saved to preferences.

-defaultCommandArray(-dca) query				
		Returns an string array containing the names of all the default run time commands.

-delete(-del) edit 				
		Delete the specified user run time command.

-exists(-ex) create 				
		Returns true|false depending upon whether the specified object exists. Other flags are ignored.

-hotkeyCtx(-hc)	string createqueryedit 	
		hotkey Context for the command.

-image(-i) string createqueryedit 	
		Image filename for the command.

-keywords(-k) string createqueryedit		
		Keywords for the command. Used for searching for commands in Type To Find. When multiple keywords, use ; as a separator. (Example: "keyword1;keyword2")

-annotation(-annotation) string createqueryedit		
		Label for the command.

-longAnnotation(-la) string createqueryedit	
		Extensive, multi-line description of the command. This will show up in Type To Finds more info page in addition to the annotation.

-numberOfCommands(-nc) query			
		Return the number of run time commands.

-numberOfDefaultCommands(-ndc) query			
		Return the number of default run time commands.

-numberOfUserCommands(-nuc)	query			
		Return the number of user run time commands.

-plugin(-p)	string createqueryedit			
		Name of the plugin this command requires to be loaded. This flag wraps the script provided into a safety check and automatically loads the plugin referenced on execution if it hasn't been loaded. If the plugin fails to load, the command won't be executed.

-save(-s) edit 							
		Save all the user run time commands.

-showInHotkeyEditor(-she) boolean createqueryedit		
		Indicate that this run time command should be shown in the Hotkey Editor. Default value is true.

-tags(-t) string createqueryedit	
		Tags for the command. Used for grouping commands in Type To Find. When more than one tag, use ; as a separator. (Example: "tag1;tag2")

-userCommandArray(-uca)	query			
		Returns an string array containing the names of all the user run time commands.
'''



# Depricated: -------------------------------------------------------------------------------------------------------




		# string $image_plane[] = `ls -exactType imagePlane`;
		# for ($object in $image_plane){
		# 	if (`getAttr ($object+".displayMode")` != 2){
		# 		setAttr ($object+".displayMode") 2;
		# 		grid -toggle 1;
		# 		inViewMessage -statusMessage "Grid is now <hl>ON</hl>.\\n<hl>F1</hl>"  -fade -position topCenter;
		# 	}else{
		# 		setAttr ($object+".displayMode") 0;
		# 		grid -toggle 0;
		# 		inViewMessage -statusMessage "Grid is now <hl>OFF</hl>.\\n<hl>F1</hl>"  -fade -position topCenter;
		# 	}
		# }


# 		global int $toggleFrame_;

# 		string $selection[] = `ls -selection`;

# 		$mode = `selectMode -query -component`;
# 		$maskVertex = `selectType -query -vertex`;
# 		$maskEdge = `selectType -query -edge`;
# 		$maskFacet = `selectType -query -facet`;

# 		if (size($selection)==0)
# 			{
# 			viewFit -allObjects;
# 			}
			
# 		if ($mode==1 && $maskVertex==1 && size($selection)!=0)
# 			{
# 			if (size($selection)>1)
# 				{
# 				if ($toggleFrame_ == !1)
# 					{
# 					viewFit -fitFactor .65;
# 					$toggleFrame_ = 1;
# 					print ("frame vertices "+$toggleFrame_+"\\n");
# 					}
# 				else
# 					{
# 					viewFit -fitFactor .10;
# 					//viewSet -previousView;
# 					$toggleFrame_ = 0;
# 					print ("frame vertices "+$toggleFrame_+"\\n");
# 					}
# 				}
# 			else
# 				{
# 				if ($toggleFrame_ == !1)
# 					{
# 					viewFit -fitFactor .15;
# 					$toggleFrame_ = 1;
# 					print ("frame vertex "+$toggleFrame_+"\\n");
# 					}
# 				else
# 					{
# 					viewFit -fitFactor .01;
# 					//viewSet -previousView;
# 					$toggleFrame_ = 0;
# 					print ("frame vertex "+$toggleFrame_+"\\n");
# 					}
# 				}
# 			}
# 		if ($mode==1 && $maskEdge==1 && size($selection)!=0)
# 			{
# 			if ($toggleFrame_ == !1)
# 				{
# 				viewFit -fitFactor .3;
# 				$toggleFrame_ = 1;
# 				print ("frame edge "+$toggleFrame_+"\\n");
# 				}
# 			else
# 				{
# 				viewFit -fitFactor .9;
# 				//viewSet -previousView;
# 				$toggleFrame_ = 0;
# 				print ("frame edge "+$toggleFrame_+"\\n");
# 				}
# 			}
# 		if ($mode==1 && $maskFacet==1)
# 			{
# 			if ($toggleFrame_ == !1)
# 				{
# 				viewFit -fitFactor .9;
# 				$toggleFrame_ = 1;
# 				print ("frame facet "+$toggleFrame_+"\\n");
# 				}
# 			else
# 				{
# 				viewFit -fitFactor .45;
# 				//viewSet -previousView;
# 				$toggleFrame_ = 0;
# 				print ("frame facet "+$toggleFrame_+"\\n");
# 				}
# 			}
# 		else if ($mode==0  && size($selection)!=0)
# 			{
# 			if ($toggleFrame_ == !1)
# 				{
# 				viewFit -fitFactor .99;
# 				$toggleFrame_ = 1;
# 				print ("frame object "+$toggleFrame_+"\\n");
# 				}
# 			else
# 				{
# 				viewFit -fitFactor .65;
# 				//viewSet -previousView;
# 				$toggleFrame_ = 0;
# 				print ("frame object "+$toggleFrame_+"\\n");
# 				}
# 			}




		# string $currentPanel = `getPanel -withFocus`;
		# $mode = `displayPref -query -wireframeOnShadedActive`;

		# if ($mode=="none")
		# 	{
		# 	displayPref -wireframeOnShadedActive "reduced";
		# 	setWireframeOnShadedOption 1 $currentPanel;
		# 	inViewMessage -statusMessage "<hl>Wireframe-on-selection</hl> is now <hl>Full</hl>.\\n<hl>3</hl>"  -fade -position topCenter;
		# 	}
		# if ($mode=="reduced")
		# 	{
		# 	displayPref -wireframeOnShadedActive "full";
		# 	setWireframeOnShadedOption 0 $currentPanel;
		# 	inViewMessage -statusMessage "<hl>Wireframe-on-selection</hl> is now <hl>Reduced</hl>.\\n<hl>3</hl>"  -fade -position topCenter;
		# 	}
		# if ($mode=="full")
		# 	{
		# 	displayPref -wireframeOnShadedActive "none";
		# 	setWireframeOnShadedOption 0 $currentPanel;
		# 	inViewMessage -statusMessage "<hl>Wireframe-on-selection</hl> is now <hl>OFF</hl>.\\n<hl>3</hl>" -fade -position topCenter;
		# 	}


	# //xray all except selected
	# string $scene[] = `ls -visible -flatten -dag -noIntermediate -type surfaceShape`;
	# string $selection[] = `ls -selection -dagObjects -shapes`;
	# for ($object in $scene)
	# 	{
	# 	if (!stringArrayContains ($object, $selection))
	# 		{
	# 		int $state[] = `displaySurface -query -xRay $object`;
	# 		displaySurface -xRay ( !$state[0] ) $object;
	# 		}
	# 	}


		# mel.eval('''
		# string $currentPanel = `getPanel -withFocus`;
		# string $state = `modelEditor -query -displayAppearance $currentPanel`;
		# string $displayTextures = `modelEditor -query -displayTextures $currentPanel`;
		# if(`modelEditor -exists $currentPanel`)
		#   {
		# 	if($state != "wireframe" && $displayTextures == false)
		# 	  {
		# 		modelEditor -edit -displayAppearance smoothShaded -activeOnly false -displayTextures true $currentPanel;
		# 		inViewMessage -statusMessage "modelEditor -smoothShaded <hl>true</hl> -displayTextures <hl>true</hl>.\\n<hl>5</hl>"  -fade -position topCenter;
		# 		}
		# 	if($state == "wireframe" && $displayTextures == true)
		# 	  {
		# 		modelEditor -edit -displayAppearance smoothShaded -activeOnly false -displayTextures false $currentPanel;
		# 		inViewMessage -statusMessage "modelEditor -smoothShaded <hl>true</hl> -displayTextures <hl>false</hl>.\\n<hl>5</hl>"  -fade -position topCenter;
		# 		}
		# 	if($state != "wireframe" && $displayTextures == true)
		# 	  {
		# 		modelEditor -edit -displayAppearance wireframe -activeOnly false $currentPanel;
		# 		inViewMessage -statusMessage "modelEditor -wireframe <hl>true</hl>.\\n<hl>5</hl>"  -fade -position topCenter;
		# 		}
		# 	}
		# ''')


# SelectMultiComponentMask;
# inViewMessage -statusMessage "<hl>Multi-Component Selection Mode</hl>\\n Mask is now <hl>ON</hl>.\\n<hl>F4</hl>"  -fade -position topCenter;



		# //paste and then re-name object removing keyword 'pasted'
		# cutCopyPaste "paste";
		# {
		# string $pasted[] = `ls "pasted__*"`;
		# string $object;
		# for ( $object in $pasted )
		# {
		# string $elements[];
		# // The values returned by ls may be full or partial dag
		# // paths - when renaming we only want the actual
		# // object name so strip off the leading dag path.
		# //
		# tokenize( $object, "|", $elements );
		# string $stripped = $elements[ `size $elements` - 1 ];
		# // Remove the 'pasted__' suffix from the name
		# //
		# $stripped = `substitute "pasted__" $stripped ""`;
		# // When renaming a transform its shape will automatically be
		# // be renamed as well. Use catchQuiet here to ignore errors
		# // when trying to rename the child shape a second time.
		# // 
		# catchQuiet(`evalEcho("rename " + $object + " " + $stripped)`);
		# }
		# };
		# //alternative: edit the cutCopyPaste.mel
		# //REMOVE the line "-renameAll" so the sub-nodes won't get renamed at all
		# //REMOVE the -renamingPrefix "paste_" line
		# //and instead write the line -defaultNamespace


# $mode = `selectMode -query -component`;
# if ($mode==0)
#   {
# 	changeSelectMode -component;
# 	}

# $maskVertex = `selectType -query -vertex`;
# $maskEdge = `selectType -query -edge`;
# $maskFacet = `selectType -query -facet`;

# if ($maskEdge==0 && $maskFacet==1)
# 	{
# 	selectType -vertex true;
# 	inViewMessage -statusMessage "<hl>Vertex</hl> Mask is now <hl>ON</hl>.\\n<hl>F4</hl>"  -fade -position topCenter;
# 	}
# if ($maskVertex==1 && $maskFacet==0)
# 	{
# 	selectType -edge true;
# 	inViewMessage -statusMessage "<hl>Edge</hl> Mask is now <hl>ON</hl>.\\n<hl>F4</hl>"  -fade -position topCenter;
# 	}
# if ($maskVertex==0 && $maskEdge==1)
# 	{
# 	selectType -facet true;
# 	inViewMessage -statusMessage "<hl>Facet</hl> Mask is now <hl>ON</hl>.\\n<hl>F4</hl>"  -fade -position topCenter;
# 	}


		# // added this expression to fix 'toggleMainMenubar function not found' error
		# if (`menu -q -ni MayaWindow|HotBoxControlsMenu` == 0) {setParent -m MayaWindow|HotBoxControlsMenu;source HotboxControlsMenu;};

		# //toggle panel menus
		# string $panels[] = `getPanel -allPanels`;
		# int $state = `panel -query -menuBarVisible $panels[0]`;
		# for ($panel in $panels)
		# {
		# 	// int $state = `panel -query -menuBarVisible $panel`;
		# 	panel -edit -menuBarVisible (!$state) $panel;
		# }
		# //toggle main menubar
		# toggleMainMenubar (!$state);

		# //toggle titlebar
		# window -edit -titleBar (!$state) $gMainWindow;

		# // //toggle fullscreen mode //working but issues with windows resizing on toggle
		# // int $inFullScreenMode = `optionVar -q "workspacesInFullScreenUIMode"`;
		# // int $inZoomInMode = `optionVar -q "workspacesInZoomInUIMode"`;
		# // // enter full screen mode only if the zoom-in mode is not active.
		# // if(!$inZoomInMode) 
		# // {
		# // 	string $panelWithFocus = `getPanel -withFocus`;
		# // 	string $parentControl = `workspaceLayoutManager -parentWorkspaceControl $panelWithFocus`;
		# // 	int $isFloatingPanel = `workspaceControl -q -floating $parentControl`;
						
		# // 	if(!$isFloatingPanel) 
		# // 	{
		# // 		if($inFullScreenMode) 
		# // 		{
		# // 		//come out of fullscreen mode
		# // 		workspaceLayoutManager -restoreMainWindowControls;
		# // 		}
		# // 		else 
		# // 		{
		# // 			// enter fullscreen mode
		# // 			workspaceLayoutManager -collapseMainWindowControls $parentControl true;
		# // 		}
		# // 	optionVar -iv "workspacesInFullScreenUIMode" (!$inFullScreenMode);
		# // 	}
		# // }