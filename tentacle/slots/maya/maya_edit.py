# !/usr/bin/python
# coding=utf-8
import os.path

from maya_init import *



class Edit(Init):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)


	def draggable_header(self, state=None):
		'''Context menu
		'''
		dh = self.edit_ui.draggable_header

		if state=='setMenu':
			dh.contextMenu.add(self.tcl.wgts.ComboBox, setObjectName='cmb000', setToolTip='Maya Editors')
			return


	def cmb000(self, index=-1):
		'''Editors
		'''
		cmb = self.edit_ui.draggable_header.contextMenu.cmb000

		if index=='setMenu':
			list_ = ['Cleanup', 'Transfer: Attribute Values', 'Transfer: Shading Sets']
			cmb.addItems_(list_, 'Maya Editors')
			return

		if index>0:
			text = cmb.items[index]
			if text=='Cleanup':
				pm.mel.CleanupPolygonOptions()
			elif text=='Transfer: Attribute Values':
				pm.mel.TransferAttributeValuesOptions()
				# mel.eval('performTransferAttributes 1;') #Transfer Attributes Options
			elif text=='Transfer: Shading Sets':
				pm.mel.performTransferShadingSets(1)
			cmb.setCurrentIndex(0)


	@Init.attr
	def cmb001(self, index=-1):
		'''Object History Attributes
		'''
		cmb = self.edit_ui.cmb001

		if index=='setMenu':
			cmb.beforePopupShown.connect(self.cmb001) #refresh comboBox contents before showing it's popup.
			return

		try:
			list_ = list(set([n.name() for n in pm.listHistory(pm.ls(sl=1, objectsOnly=1), pruneDagObjects=1)])) #levels=1, interestLevel=2, 
		except RuntimeError as error:
			list_ = ['No selection.']
		cmb.addItems_(list_, 'History')

		cmb.setCurrentIndex(0)
		if index>0:
			if cmb.items[index]!='No selection.':
				return pm.ls(cmb.items[index])


	def chk006_9(self):
		'''Set the toolbutton's text according to the checkstates.
		'''
		tb = self.current_ui.tb003
		axis = self.getAxisFromCheckBoxes('chk006-9', tb.contextMenu)
		tb.setText('Delete '+axis)


	def tb000(self, state=None):
		'''Mesh Cleanup
		'''
		tb = self.current_ui.tb000
		if state=='setMenu':
			tb.contextMenu.add('QCheckBox', setText='All Geometry', setObjectName='chk005', setToolTip='Clean All scene geometry.')
			tb.contextMenu.add('QCheckBox', setText='Repair', setObjectName='chk004', setToolTip='Repair matching geometry. Else, select only.') #tb.contextMenu.add(self.tcl.wgts.CheckBox, setText='Select Only', setObjectName='chk004', setTristate=True, setCheckState_=2, setToolTip='Select and/or Repair matching geometry. <br>0: Repair Only<br>1: Repair and Select<br>2: Select Only')
			tb.contextMenu.add('QCheckBox', setText='N-Gons', setObjectName='chk002', setChecked=True, setToolTip='Find N-gons.')
			tb.contextMenu.add('QCheckBox', setText='Non-Manifold Geometry', setObjectName='chk017', setChecked=True, setToolTip='Check for nonmanifold polys.')
			tb.contextMenu.add('QCheckBox', setText='Non-Manifold Vertex', setObjectName='chk021', setToolTip='A connected vertex of non-manifold geometry where the faces share a single vertex.')
			tb.contextMenu.add('QCheckBox', setText='Quads', setObjectName='chk010', setToolTip='Check for quad sided polys.')
			tb.contextMenu.add('QCheckBox', setText='Concave', setObjectName='chk011', setToolTip='Check for concave polys.')
			tb.contextMenu.add('QCheckBox', setText='Non-Planar', setObjectName='chk003', setToolTip='Check for non-planar polys.')
			tb.contextMenu.add('QCheckBox', setText='Holed', setObjectName='chk012', setToolTip='Check for holed polys.')
			tb.contextMenu.add('QCheckBox', setText='Lamina', setObjectName='chk018', setToolTip='Check for lamina polys.')
			tb.contextMenu.add('QCheckBox', setText='Shared UV\'s', setObjectName='chk016', setToolTip='Unshare uvs that are shared across vertices.')
			# tb.contextMenu.add('QCheckBox', setText='Invalid Components', setObjectName='chk019', setToolTip='Check for invalid components.')
			tb.contextMenu.add('QCheckBox', setText='Zero Face Area', setObjectName='chk013', setToolTip='Check for 0 area faces.')
			tb.contextMenu.add('QDoubleSpinBox', setPrefix='Face Area Tolerance:   ', setObjectName='s006', setDisabled=True, setMinMax_='0.0-10 step.001', setValue=0.001, setToolTip='Tolerance for face areas.')
			tb.contextMenu.add('QCheckBox', setText='Zero Length Edges', setObjectName='chk014', setToolTip='Check for 0 length edges.')
			tb.contextMenu.add('QDoubleSpinBox', setPrefix='Edge Length Tolerance: ', setObjectName='s007', setDisabled=True, setMinMax_='0.0-10 step.001', setValue=0.001, setToolTip='Tolerance for edge length.')
			tb.contextMenu.add('QCheckBox', setText='Zero UV Face Area', setObjectName='chk015', setToolTip='Check for 0 uv face area.')
			tb.contextMenu.add('QDoubleSpinBox', setPrefix='UV Face Area Tolerance:', setObjectName='s008', setDisabled=True, setMinMax_='0.0-10 step.001', setValue=0.001, setToolTip='Tolerance for uv face areas.')
			tb.contextMenu.add('QCheckBox', setText='Overlapping Duplicate Objects', setObjectName='chk022', setToolTip='Find any duplicate overlapping geometry at the object level.')
			tb.contextMenu.add('QCheckBox', setText='Omit Selected Objects', setObjectName='chk023', setDisabled=True, setToolTip='Overlapping Duplicate Objects: Search for duplicates of any selected objects while omitting the initially selected objects.')

			tb.contextMenu.chk022.stateChanged.connect(lambda state: self.toggleWidgets(tb.contextMenu, setDisabled='chk002-3,chk005,chk010-21,s006-8', setEnabled='chk023') if state 
															else self.toggleWidgets(tb.contextMenu, setEnabled='chk002-3,chk005,chk010-21,s006-8', setDisabled='chk023')) #disable non-relevant options.
			tb.contextMenu.chk013.toggled.connect(lambda state: tb.contextMenu.s006.setEnabled(True if state else False))
			tb.contextMenu.chk014.toggled.connect(lambda state: tb.contextMenu.s007.setEnabled(True if state else False))
			tb.contextMenu.chk015.toggled.connect(lambda state: tb.contextMenu.s008.setEnabled(True if state else False))
			return

		allMeshes = int(tb.contextMenu.chk005.isChecked()) #[0] All selectable meshes
		repair = tb.contextMenu.chk004.isChecked() #repair or select only
		historyOn = 1 #[2] keep construction history
		quads = int(tb.contextMenu.chk010.isChecked()) #[3] check for quads polys
		nsided = int(tb.contextMenu.chk002.isChecked()) #[4] check for n-sided polys
		concave = int(tb.contextMenu.chk011.isChecked()) #[5] check for concave polys
		holed = int(tb.contextMenu.chk012.isChecked()) #[6] check for holed polys
		nonplanar = int(tb.contextMenu.chk003.isChecked()) #[7] check for non-planar polys
		zeroGeom = int(tb.contextMenu.chk013.isChecked()) #[8] check for 0 area faces
		zeroGeomTol = tb.contextMenu.s006.value() #[9] tolerance for face areas
		zeroEdge = int(tb.contextMenu.chk014.isChecked()) #[10] check for 0 length edges
		zeroEdgeTol = tb.contextMenu.s007.value() #[11] tolerance for edge length
		zeroMap = int(tb.contextMenu.chk015.isChecked()) #[12] check for 0 uv face area
		zeroMapTol = tb.contextMenu.s008.value() #[13] tolerance for uv face areas
		sharedUVs = int(tb.contextMenu.chk016.isChecked()) #[14] Unshare uvs that are shared across vertices
		nonmanifold = int(tb.contextMenu.chk017.isChecked()) #[15] check for nonmanifold polys
		lamina = -int(tb.contextMenu.chk018.isChecked()) #[16] check for lamina polys [default -1]
		splitNonManifoldVertex = tb.contextMenu.chk021.isChecked()
		invalidComponents = 0 #int(tb.contextMenu.chk019.isChecked()) #[17] a guess what this arg does. not checked. default is 0.
		overlappingDuplicateObjects = tb.contextMenu.chk022.isChecked() #find overlapping geometry at object level.
		omitSelectedObjects = tb.contextMenu.chk023.isChecked() #Search for duplicates of any selected objects while omitting the initially selected objects.

		# if tb.contextMenu.chk005.isChecked(): #All Geometry. Select components for cleanup from all visible geometry in the scene
		# 	scene = pm.ls(visible=1, geometry=1)
		# 	[pm.select (geometry, add=1) for geometry in scene]

		objects = pm.ls(sl=1, transforms=1)

		if overlappingDuplicateObjects:
			duplicates = Init.getOverlappingDuplicateObjects(omitInitialObjects=omitSelectedObjects, select=True, verbose=True)
			if repair: #repair
				pm.delete(duplicates)
			return

		if any((quads,nsided,concave,holed,nonplanar,zeroGeom,zeroEdge,zeroMap,sharedUVs,nonmanifold,invalidComponents)):
			arg_list = '"{0}","{1}","{2}","{3}","{4}","{5}","{6}","{7}","{8}","{9}","{10}","{11}","{12}","{13}","{14}","{15}","{16}","{17}"'.format(
					allMeshes, 1 if repair else 2, historyOn, quads, nsided, concave, holed, nonplanar, zeroGeom, zeroGeomTol, 
					zeroEdge, zeroEdgeTol, zeroMap, zeroMapTol, sharedUVs, nonmanifold, lamina, invalidComponents)
			command = 'polyCleanupArgList 4 {'+arg_list+'}' # command = 'polyCleanup '+arg_list #(not used because of arg count error, also the quotes in the arg list would need to be removed). 
			print (command)
			mel.eval(command)

		if splitNonManifoldVertex: #Split Non-Manifold Vertex
			if not repair: #select only
				Init.findNonManifoldVertex(objects)
			else:
				nonManifoldVerts = Init.getComponents(objects, 'vtx', selection=1) #user selection
				if not nonManifoldVerts:
					nonManifoldVerts = Init.findNonManifoldVertex(objects, select=2) #Select: 0=off, 1=on, 2=on while keeping any existing vertex selections. (default: 1)
				for vertex in nonManifoldVerts:
					Init.splitNonManifoldVertex(vertex, select=True) #select(bool): Select the vertex after the operation. (default: True)


	def tb001(self, state=None):
		'''Delete History
		'''
		tb = self.current_ui.tb001
		if state=='setMenu':
			tb.contextMenu.add('QCheckBox', setText='For All Objects', setObjectName='chk018', setChecked=True, setToolTip='Delete history on All objects or just those selected.')
			tb.contextMenu.add('QCheckBox', setText='Delete Unused Nodes', setObjectName='chk019', setChecked=True, setToolTip='Delete unused nodes.')
			tb.contextMenu.add('QCheckBox', setText='Delete Deformers', setObjectName='chk020', setToolTip='Delete deformers.')
			return

		all_ = tb.contextMenu.chk018.isChecked()
		unusedNodes = tb.contextMenu.chk019.isChecked()
		deformers = tb.contextMenu.chk020.isChecked()
		objects = pm.ls(selection=1, objectsOnly=1) if not all_ else pm.ls(typ="mesh")

		try: #delete history
			if all_:
				pm.delete(objects, constructionHistory=1)
			else:
				pm.bakePartialHistory(objects, prePostDeformers=1)
		except:
			pass
		if unusedNodes:
			pm.mel.MLdeleteUnused() #pm.mel.hyperShadePanelMenuCommand('hyperShadePanel1', 'deleteUnusedNodes')

		#display viewPort messages
		if all_:
			if deformers:
				self.viewPortMessage("delete <hl>all</hl> history.")
			else:
				self.viewPortMessage("delete <hl>all non-deformer</hl> history.")
		else:
			if deformers:
				self.viewPortMessage("delete history on "+str(objects))
			else:
				self.viewPortMessage("delete <hl>non-deformer</hl> history on "+str(objects))


	def tb002(self, state=None):
		'''Delete
		'''
		tb = self.current_ui.tb002
		if state=='setMenu':
			tb.contextMenu.add('QCheckBox', setText='Delete Edge Loop', setObjectName='chk001', setToolTip='Delete the edge loops of any edges selected.')
			tb.contextMenu.add('QCheckBox', setText='Delete Edge Ring', setObjectName='chk000', setToolTip='Delete the edge rings of any edges selected.')
			return

		deleteRing = tb.contextMenu.chk000.isChecked()
		deleteLoop = tb.contextMenu.chk001.isChecked()

		# selectionMask = pm.selectMode (query=True, component=True)
		maskVertex = pm.selectType (query=True, vertex=True)
		maskEdge = pm.selectType (query=True, edge=True)
		maskFacet = pm.selectType (query=True, facet=True)

		objects = pm.ls(sl=1, objectsOnly=1)
		for obj in objects:
			if pm.objectType(obj, isType='joint'):
				pm.removeJoint(obj) #remove joints

			elif pm.objectType(obj, isType='mesh'): 
				if maskEdge:
					edges = pm.ls(obj, sl=1, flatten=1)
					if deleteRing:
						[edges.append(i) for i in Init.getEdgeRing(edges)] # pm.polySelect(edges, edgeRing=True) #select the edge ring.
					if deleteLoop:
						[edges.append(i) for i in Init.getEdgeLoop(edges)] # pm.polySelect(edges, edgeLoop=True) #select the edge loop.
					pm.polyDelEdge(edges, cleanVertices=True) #delete edges

				elif maskVertex:
					pm.polyDelVertex() #try delete vertices
					if pm.ls(sl=1)==objects: #if nothing was deleted:
						mel.eval('polySelectSp -loop;') #convert selection to edge loop
						pm.polyDelEdge(cleanVertices=True) #delete edges

				else: #all([selectionMask==1, maskFacet==1]):
					pm.delete(obj) #delete faces\mesh objects


	def tb003(self, state=None):
		'''Delete Along Axis
		'''
		tb = self.current_ui.tb003
		if state=='setMenu':
			tb.contextMenu.add('QCheckBox', setText='-', setObjectName='chk006', setChecked=True, setToolTip='Perform delete along negative axis.')
			tb.contextMenu.add('QRadioButton', setText='X', setObjectName='chk007', setChecked=True, setToolTip='Perform delete along X axis.')
			tb.contextMenu.add('QRadioButton', setText='Y', setObjectName='chk008', setToolTip='Perform delete along Y axis.')
			tb.contextMenu.add('QRadioButton', setText='Z', setObjectName='chk009', setToolTip='Perform delete along Z axis.')

			self.connect_('chk006-9', 'toggled', self.chk006_9, tb.contextMenu)
			return

		axis = self.getAxisFromCheckBoxes('chk006-9', tb.contextMenu)

		pm.undoInfo(openChunk=1)
		objects = pm.ls(sl=1, objectsOnly=1)

		for obj in objects:
			self.deleteAlongAxis(obj, axis)
		pm.undoInfo(closeChunk=1)


	@Slots.message
	@Slots.hideMain
	def b001(self):
		'''Object History Attributes: get most recent node
		'''
		cmb = self.edit_ui.cmb001
		self.cmb001() #refresh the contents of the combobox.

		items = pm.ls(cmb.items[-1])
		if items:
			self.setAttributeWindow(items, checkableLabel=True)
		else:
			return 'Error: Found no items to list the history for.'


	def b021(self):
		'''Tranfer Maps
		'''
		pm.mel.performSurfaceSampling(1)


	def b022(self):
		'''Transfer Vertex Order
		'''
		pm.mel.TransferVertexOrder()


	def b023(self):
		'''Transfer Attribute Values
		'''
		pm.mel.TransferAttributeValues()


	def b027(self):
		'''Shading Sets
		'''
		pm.mel.performTransferShadingSets(0)









#module name
print(os.path.splitext(os.path.basename(__file__))[0])
# -----------------------------------------------
# Notes
# -----------------------------------------------
	# b008, b009, b011
