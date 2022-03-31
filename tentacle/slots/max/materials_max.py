# !/usr/bin/python
# coding=utf-8
from slots.max import *
from slots.materials import Materials



class Materials_max(Materials, Slots_max):
	def __init__(self, *args, **kwargs):
		Slots_max.__init__(self, *args, **kwargs)
		Materials.__init__(self, *args, **kwargs)

		self.randomMat=None

		dh = self.materials_ui.draggable_header
		dh.contextMenu.add(self.tcl.wgts.ComboBox, setObjectName='cmb000', setToolTip='Maya Material Editors')
		dh.contextMenu.add(self.tcl.wgts.PushButton, setText='Relink Scene Bitmaps', setObjectName='tb003', setToolTip='Repair broken bitmap file links for any scene materials. If no materials are selected, all scene materials will be used.')
		dh.contextMenu.add(self.tcl.wgts.PushButton, setText='Relink Library Bitmaps', setObjectName='tb004', setToolTip='Repair broken bitmap file links for all libraries in a given directory.')

		cmb000 = self.materials_ui.draggable_header.contextMenu.cmb000
		items = ['Material Editor']
		cmb000.addItems_(items, 'Material Editors')


	def cmb000(self, index=-1):
		'''Editors
		'''
		cmb = self.materials_ui.draggable_header.contextMenu.cmb000

		if index>0:
			text = cmb.items[index]
			if text=='Material Editor':
				maxEval('max mtledit')
			cmb.setCurrentIndex(0)


	def cmb002(self, index=-1):
		'''Material list

		:Parameters:
			index (int) = parameter on activated, currentIndexChanged, and highlighted signals.
		'''
		cmb = self.materials_ui.cmb002
		b = self.materials_submenu_ui.b003

		mode = cmb.contextMenu.cmb001.currentText()
		if mode=='Scene Materials':
			materials = self.getSceneMaterials()

		elif mode=='ID Map Materials':
			materials = self.getSceneMaterials(startingWith=['ID_'])

		if mode=='Favorite Materials':
			currentMats = {m:m for m in ['standardMaterial']}
		else:
			currentMats = {mat.name:mat for mat in sorted(list(set(materials))) if hasattr(mat, 'name')}

		cmb.addItems_(currentMats, clear=True)

		#create and set icons with color swatch
		for i, mat in enumerate(cmb.items):
			icon = self.getColorSwatchIcon(mat)
			cmb.setItemIcon(i, icon) if icon else None

		#set submenu assign material button attributes
		b.setText('Assign '+cmb.currentText())
		icon = self.getColorSwatchIcon(cmb.currentText(), [15, 15])
		b.setIcon(icon) if icon else None
		b.setMinimumWidth(b.minimumSizeHint().width()+25)
		b.setVisible(True if cmb.currentText() else False)


	@Slots.message
	def tb000(self, state=None):
		'''Select By Material Id
		'''
		tb = self.materials_ui.tb000

		mat = self.materials_ui.cmb002.currentData()
		if not mat:
			return 'Error: No Material Selection.'

		shell = tb.contextMenu.chk005.isChecked() #Select by material: shell
		invert = tb.contextMenu.chk006.isChecked() #Select by material: invert
		allObjects = tb.contextMenu.chk003.isChecked() #Search all scene objects

		objects = rt.selection if not allObjects else None
		
		self.selectByMaterialID(mat, objects, shell=shell, invert=invert)


	@Slots.message
	def tb002(self, state=None):
		'''Assign Material
		'''
		tb = self.materials_ui.tb002

		selection = rt.selection

		assignCurrent = tb.contextMenu.chk007.isChecked()
		assignRandom = tb.contextMenu.chk008.isChecked()
		assignNew = tb.contextMenu.chk009.isChecked()

		if assignRandom: #Assign New random mat ID
			if selection:
				mat = self.createRandomMaterial(prefix='ID_')
				self.assignMaterial(selection, mat)

				#delete previous shader
				if self.randomMat:
					self.randomMat = None #replace with standard material

				self.randomMat = mat

				if self.materials_ui.tb001.menu_.chk001.isChecked(): #ID map materials mode.
					self.cmb002() #refresh the combobox
				else:
					self.materials_ui.tb001.menu_.chk001.setChecked(True) #set comboBox to ID map mode. toggling the checkbox refreshes the combobox.
				self.materials_ui.cmb002.setCurrentItem(mat.name) #set the comboBox index to the new mat #self.cmb002.setCurrentIndex(self.cmb002.findText(name))
			else:
				return 'Error: No valid object/s selected.'

		elif assignCurrent: #Assign current mat
			if isinstance(mat, str): #new mat type as a string:
				self.assignMaterial(selection, rt.Standard(name=mat))
			else: #existing mat object:
				self.assignMaterial(selection, mat)

		elif assignNew: #Assign New Material
			pass

		rt.redrawViews()


	def tb003(self, state=None):
		'''Relink Scene Bitmaps
		'''
		tb = self.materials_ui.draggable_header.contextMenu.tb003
		if state=='setMenu':
			tb.contextMenu.add('QLineEdit', setPlaceholderText='Set Bitmaps Directory:', setText=r'\\m3trik-Server\NAS\Graphics\_materials', setObjectName='l000', setToolTip='Location to search for missing bitmaps.') #
			return

		mat_dir = tb.contextMenu.l000.text()
		mats = self.getNodesSME(selected=True) #find bitmaps for any currently selected nodes in the slate material editor, else relink all scene nodes.
		if not mats:
			mats = None

		self.relinkSceneBitmaps(mat_dir, mats=mats, replaceTxWithTif=True)


	def tb004(self, state=None):
		'''Relink Material Library Bitmaps
		'''
		tb = self.materials_ui.draggable_header.contextMenu.tb004
		if state=='setMenu':
			tb.contextMenu.add('QLineEdit', setPlaceholderText='Set Bitmaps Directory:', setText=r'\\m3trik-Server\NAS\Graphics\_materials', setObjectName='l001', setToolTip='Location to search for missing bitmaps.') #
			tb.contextMenu.add('QLineEdit', setPlaceholderText='Set Material Library Directory:', setText=r'\\m3trik-Server\NAS\Graphics\_materials\libraries', setObjectName='l002', setToolTip='Location of material libraries.') #
			return

		library_dir = tb.contextMenu.l001.text()
		mat_dir = tb.contextMenu.l002.text()

		self.relinkMatLibBitmaps(library_dir, mat_dir, replaceTxWithTif=True)


	@Slots.message
	def lbl000(self):
		'''Open material in editor
		'''
		try:
			mat = self.materials_ui.cmb002.currentData() #get the mat obj from cmb002
			rt.select(mat)
		except Exception as error:
			return 'Error: No stored material or no valid object selected.'

		#open the slate material editor
		if not rt.SME.isOpen():
			rt.SME.open()

		#create a temp view in the material editor
		if rt.SME.GetViewByName('temp'):
			rt.SME.DeleteView(rt.SME.GetViewByName('temp'), False)
		index = rt.SME.CreateView('temp')
		view = rt.SME.GetView(index)

		#show node and corresponding parameter rollout
		node = view.CreateNode(mat, rt.point2(0, 0))
		rt.SME.SetMtlInParamEditor(mat)

		rt.redrawViews()


	def lbl001(self, setEditable=True):
		'''Rename Material: Set cmb002 as editable and disable wgts.
		'''
		cmb = self.materials_ui.cmb002

		if setEditable:
			self._mat = self.materials_ui.cmb002.currentData()
			cmb.setEditable(True)
			self.toggleWidgets(self.materials_ui, setDisabled='b002,lbl000,tb000,tb002')
		else:
			mat = self._mat
			newMatName = cmb.currentText()
			self.renameMaterial(mat, newMatName)
			cmb.setEditable(False)
			self.toggleWidgets(self.materials_ui, setEnabled='b002,lbl000,tb000,tb002')


	def lbl002(self):
		'''Delete Material
		'''
		cmb = self.materials_ui.cmb002

		mat = self.materials_ui.cmb002.currentData()
		default_mat = rt.Standard(mat, name="Default Material") #replace with standard material

		index = cmb.currentIndex()
		cmb.setItemText(index, default_mat.name) #self.materials_ui.cmb002.removeItem(index)


	def lbl003(self):
		'''Delete Unused Materials
		'''
		defaultMaterial = rt.Standard(name='Default Material')
		
		for mat in rt.sceneMaterials:
			nodes = rt.refs().dependentnodes(mat) 
			if nodes.count==0:
				rt.replaceinstances(mat, defaultMaterial)
				
			rt.gc()
			rt.freeSceneBitmaps()


	@Slots.message
	def b002(self):
		'''Set Material: Set the Currently Selected Material as the currentMaterial.
		'''
		try: 
			obj = rt.selection[0]
		except IndexError:
			return 'Error: Nothing selected.'

		mat = self.getMaterial()

		self.materials_ui.cmb001.setCurrentIndex(0) #set the combobox to show all scene materials
		self.cmb002() #refresh the materials list comboBox
		self.materials_ui.cmb002.setCurrentIndex(self.materials_ui.cmb002.items.index(mat.name()))


	def getColorSwatchIcon(self, mat, size=[20, 20]):
		'''Get an icon with a color fill matching the given materials RBG value.

		:Parameters:
			mat (obj)(str) = The material or the material's name.
			size (list) = Desired icon size. [width, height]

		:Return:
			(obj) pixmap icon.
		'''
		try:
			mat = next(m for m in self.getSceneMaterials() if m.name==mat) if isinstance(mat, (str)) else mat #get the mat object if a string name is given.
			r = int(mat.diffuse.r) #convert from float value
			g = int(mat.diffuse.g)
			b = int(mat.diffuse.b)
			pixmap = QtGui.QPixmap(size[0],size[1])
			pixmap.fill(QtGui.QColor.fromRgb(r, g, b))

			return QtGui.QIcon(pixmap)

		except (StopIteration, AttributeError):
			pass


	def renameMaterial(self, mat, newMatName):
		'''Rename Material
		'''
		cmb = self.materials_ui.cmb002 #scene materials

		curMatName = mat.name
		if curMatName!=newMatName:
			cmb.setItemText(cmb.currentIndex(), newMatName)
			try:
				curMatName = newMatName
			except RuntimeError as error:
				cmb.setItemText(cmb.currentIndex(), str(error.strip('\n')))


	@Slots.message
	def selectByMaterialID(self, material=None, objects=None, shell=False, invert=False):
		'''Select By Material Id
	
		material (obj) = The material to search and select for.
		objects (list) = Faces or mesh objects as a list. If no objects are given, all geometry in the scene will be searched.
		shell (bool) = Select the entire shell.
		invert (bool) = Invert the final selection.

		#ex call:
		selectByMaterialID(material)
		'''
		if rt.getNumSubMtls(material): #if not a multimaterial
			return 'Error: No valid stored material. If material is a multimaterial, select a submaterial.'

		if not material:
			material = self.getMaterial()

		if not objects: #if not selection; use all scene geometry
			objects = rt.geometry

		for obj in objects:
			if not any([rt.isKindOf(obj, rt.Editable_Poly), rt.isKindOf(obj, rt.Editable_mesh)]):
				print('Error: '+str(obj.name)+' skipped. Operation requires an Editable_Poly or Editable_mesh.')
			else:
				if shell: #set to base object level
					rt.modPanel.setCurrentObject(obj.baseObject)
				else: #set object level to face
					Slots_max.setSubObjectLevel(4)
				m = obj.material
				multimaterial = rt.getNumSubMtls(m)

				same=[] #list of faces with the same material
				other=[] #list of all other faces

				faces = list(range(1, obj.faces.count))
				for f in faces:
					if multimaterial:
						try: #get material from face
							index = rt.GetFaceId_(obj, f) #Returns the material ID of the specified face.
						except RuntimeError: #try procedure for polygon object
							index = rt.polyop.GetFaceId_(obj, f) #Returns the material ID of the specified face.
						m = obj.material[index-1] #m = rt.getSubMtl(m, id) #get the material using the ID_ index (account for maxscript arrays starting at index 1)

					if m==material: #single material
						if shell: #append obj to same and break loop
							same.append(obj)
							break
						else: #append face ID to same
							same.append(f)
					else:
						if shell: #append obj to other and break loop
							other.append(obj)
							break
						else: #append face ID to other
							other.append(f)

				if shell:
					if invert:
						(rt.select(i) for i in other)
					else:
						(rt.select(i) for i in same)
				else:
					if invert:
						try:
							rt.setFaceSelection(obj, other) #select inverse of the faces for editable mesh.
						except RuntimeError:
							rt.polyop.setFaceSelection(obj, other) #select inverse of the faces for polygon object.
					else:
						try:
							rt.setFaceSelection(obj, same) #select the faces for editable mesh.
						except RuntimeError:
							rt.polyop.setFaceSelection(obj, same) #select the faces for polygon object.
				# print same
				# print other


	def getSceneMaterials(self.startingWith=['']):
		'''Get All Materials from the current scene.

		:Parameters:
			startingWith (list) = Filters material names starting with any of the strings in the given list. ie. ['ID_']
		:Return:
			(list) materials.
		'''
		materials=[] #get any scene material that does not start with 'Material'
		for mat in rt.sceneMaterials:
			if rt.getNumSubMtls(mat): #if material is a submaterial; search submaterials
				for i in range(1, rt.getNumSubMtls(mat)+1):
					subMat = rt.getSubMtl(mat, i)
					if subMat and filter(subMat.name.startswith, startingWith):
						materials.append(subMat)
			elif filter(mat.name.startswith, startingWith):
				materials.append(mat)

		return materials


	@Slots.message
	def getMaterial(self, obj=None, face=None):
		'''Get the material from the given object or face components.

		:Parameters:
			obj (obj) = Mesh object.
			face (int) = Face number.
		:Return:
			(obj) material
		'''
		if not obj:
			selection = rt.selection
			if not selection:
				return 'Error: Nothing selected. Select an object face, or choose the option: current material.'
			obj = selection[0]

		mat = obj.material #get material from selection

		if rt.subObjectLevel==4: #if face selection check for multimaterial
			if rt.getNumSubMtls(mat): #if multimaterial; use selected face to get material ID
				if face is None:
					face = self.bitArrayToArray(rt.getFaceSelection(obj))[0] #get selected face

				if rt.classOf(obj)==rt.Editable_Poly:
					ID_ = rt.polyop.GetFaceId_(obj, face) #Returns the material ID of the specified face.
				else:
					try:
						ID_ = rt.GetFaceId_(obj, face) #Returns the material ID of the specified face.
					except RuntimeError:
						return 'Error: Object must be of type Editable_Poly or Editable_mesh.'

				mat = rt.getSubMtl(mat, ID_) #get material from mat ID

		return mat


	def createRandomMaterial(self, name='', prefix=''):
		'''Creates a random material.

		:Parameters:
			name (str) = material name.
			prefix (str) = Optional string to be appended to the beginning of the name.

		:Return:
			(obj) material
		'''
		import random
		rgb = [random.randint(0, 255) for _ in range(3)] #generate a list containing 3 values between 0-255

		name = '{}{}_{}_{}_{}'.format(prefix, name, str(rgb[0]), str(rgb[1]), str(rgb[2]))

		#create shader
		mat = rt.StandardMaterial()
		mat.name = name
		mat.diffuse = rt.color(rgb[0], rgb[1], rgb[2])

		return mat


	@Slots.message
	def assignMaterial(self, objects, mat):
		'''Assign Material

		objects (list) = Faces or mesh objects as a list.
		material (obj) = The material to search and select for.
		'''
		if not mat:
			return 'Error: Material Not Assigned. No material given.'

		for obj in objects:
			if rt.getNumSubMtls(mat): #if multimaterial
				mat.materialList.count = mat.numsubs+1 #add slot to multimaterial
				mat.materialList[-1] = material #assign new material to slot
			else:
				obj.material = mat

		rt.redrawViews()


	def getMaterialBitmaps(self, mats=None, missing=False, processChildren=True):
		'''Get any bitmaps from a given material(s), or from all scene materials.

		:Parameters:
			mats (obj)(list) = Mat object or list of mat objects. If None is given, all bitmap textures in the scene are used.
			missing (bool) = Return only filenames from missing bitmaps.
			processChildren (bool) = Child scene nodes are also searched as part of the Animatable or Reference hierarchy.

		:Return:
			(list) material bitmaps.
		'''
		if mats is None:
			result = list(rt.getClassInstances(rt.BitmapTexture, processChildren=False))
		else:
			result=[]
			for mat in list(mats):
				result+=list(rt.getClassInstances(rt.BitmapTexture, target=mat, processChildren=processChildren))

		if missing: #get only the names from bitmaps that are missing.
			result = {bitmap:bitmap.filename.rsplit('\\')[-1]
			for bitmap in bitmaps
				if not rt.doesFileExist(bitmap.filename)}

		return result


	def getBitmapFilenames(self, bitmaps=None, missing=False, returnType=list):
		'''Get the file paths for the given bitmaps. If no bitmaps are given all bitmaps in the scene will be used.

		:Parameters:
			bitmaps (list) = A list of bitmaps. If no bitmaps are given all bitmaps in the scene will be used.
			missing (bool) = Return only filenames from missing bitmaps.
			returnType (type) = Valid (list (default), dict).

		:Return:
			dependant on returnType flag.
			(dict) {bitmap object:filepath}
			(list) [filepath]
		'''
		import fnmatch

		if not bitmaps: #if no bitmaps are given, use all scene bitmaps.
			bitmaps = self.getMaterialBitmaps(missing=missing)

		result = {bitmap:bitmap.filename.rsplit('\\')[-1] for bitmap in bitmaps}

		if returnType is list:
			result = result.values()

		return result


	def setBitmapFilenames(self, dict_, reload=False):
		'''Set the file paths for the given bitmaps. Bitmaps are given as a dict of bitmaps as keys, and filenames as values.

		:Parameters:
			dict_ (dict) = A dict of bitmaps as keys, and filenames as values.
			reload (bool) = Refresh the bitmap node after updating the path.
		'''
		for bitmap,name in dict_.items():
			bitmap.filename = name
			if reload:
				bitmap.reload()


	def relinkBitmaps(self, dir_, bitmaps=None, replaceTxWithTif=False):
		'''Find the first valid path in the given dir for each bitmap in a given dict. If no bitmaps are given all bitmaps in the scene will be used.

		:Parameters:
			dir_ (str) = The parent dir to recursively search for files in.
			bitmaps (dict) = A dict of bitmaps as keys, and filenames as values. If no bitmaps are given all bitmaps in the scene will be used.
			replaceTxWithTif (bool) = Look instead for a .tif file of the same name, to replace a previoud .tx format.

		:Return:
			(dict) Any bitmaps that are not found. {bitmap object:filename}
		'''
		import fnmatch, os

		bitmaps = self.getBitmapFilenames(bitmaps, missing=True, returnType=dict)

		if replaceTxWithTif:
			for bitmap,filename in bitmaps.items():
				if filename.endswith('.tx'):
					bitmaps[bitmap] = filename.replace('.tx', '.tif')

		print('Relinking bitmaps in {} ..'.format(dir_))
		result={}
		for root, dirnames, filenames in os.walk(dir_):

			for bitmap, pattern in bitmaps.items():
				for filename in fnmatch.filter(filenames, pattern):
					path = os.path.join(root, filename)
					result[bitmap] = path
					bitmaps.pop(bitmap, None)
					print ('# Result: {}: {}: {} #'.format(filename, bitmap.name, path))

		self.setBitmapFilenames(result, reload=True)

		if bitmaps:
			for bitmap,filename in bitmaps.items():
				print ('# Error: {}: {} #'.format(bitmap.name, filename))


	def relinkMatLibBitmaps(self, library_dir, mat_dir, replaceTxWithTif=False):
		'''Repair broken bitmap file links for all libraries in a given directory.

		:Parameters:
			library_dir (str) = A path to a directory containing the library files.
			mat_dir (str) = A path to a directory containing the material dependancies.
		'''
		import os

		bitmaps=[]; tempLibs={}
		for root, dirnames, filenames in os.walk(library_dir):
			for filename in filenames:
				if filename.endswith('.mat'):
					try:
						path = os.path.join(root, filename)
						tempLib = rt.loadTempMaterialLibrary(path)

						for bitmap in self.getMaterialBitmaps(tempLib):
							bitmaps.append(bitmap)

						tempLibs[tempLib] = path
					except Exception as e:
						print ('# Error: {}: {} #'.format(filename, e))

		if bitmaps:
			self.relinkBitmaps(mat_dir, bitmaps, replaceTxWithTif=replaceTxWithTif)
			{rt.saveTempMaterialLibrary(lib, name) for lib,name in tempLibs.items()}


	def relinkSceneBitmaps(self, mat_dir, mats=None, replaceTxWithTif=False):
		'''Repair broken bitmap file links.  If no mats are given, all scene bitmaps will be used.

		:Parameters:
			mats (obj)(list) = Specify material(s) to get bitmaps for. If none are given, all scene materials will be used.
			replaceTxWithTif (bool) = Look instead for a .tif file of the same name, to replace a previoud .tx format.
		'''
		bitmaps = self.getMaterialBitmaps(mats)

		if bitmaps:
			self.relinkBitmaps(mat_dir, bitmaps, replaceTxWithTif=True)


	def getNodesSME(self, nodeType=None, selected=False):
		'''Get any nodes in the slate material editor that are currently selected.

		:Parameters:
			nodeType (obj)(str) = The type of node to filter the results for. If 'query' is given, the node type will be returned. ie. rt.VRayMtl()
			selected (bool) = When True, only currently selected nodes will be returned.
		:Return:
			(list) nodes or node types.
		'''
		view = rt.SME.getView(rt.SME.activeView)

		result=[]
		for i in range(1, view.GetNumNodes()):
			node = view.getNode(i)
			if all((nodeType, rt.isKindOf(node, nodeType), selected, node.selected)): #get selected of type.
				result.append(node)

			elif all((nodeType, nodeType=='query', selected, node.selected)): #query type of selected.
				result.append(rt.classOf(node))

			elif selected and node.selected: #get selected.
				result.append(node)

			elif all((nodeType, nodeType!='query', rt.isKindOf(node, nodeType))): #get node of type.
				result.append(node)

			elif nodeType and nodeType=='query': #query type.
				result.append(rt.classOf(node))

			else: #get all SME nodes.
				result.append(node)

		return result


	def compareMats(self, obj1, obj2):
		'''Compare material names. unlike other properties, this is a simple true/false comparison, it doesn't find 'similar' names.

		:Parameters:
			obj1 (obj) = 
			obj2 (obj) = 
		'''
		maxEval('''
			m1 = obj1.material
			m2 = obj2.material
			
			if m1 != undefined and m2 != undefined then --verify both objects have a material assigned
			(
				if m1.name == m2.name then 
				(
					dbgSelSim ("  Material match on object: '" + obj1.name + "' with '" + obj2.name + "'")
					true	--check if material names are the same, if they are, return a true value
				)
				else false --uh oh. material names aren't the same. return false.
			)
			else false	--one or both objects do not have a material assigned. returning false.
			''')









#module name
print (__name__)
# -----------------------------------------------
# Notes
# -----------------------------------------------


# deprecated: -----------------------------------


	# @property
	# def currentMat(self):
	# 	'''Get the current material using the current index of the materials combobox.
	# 	'''
	# 	text = self.materials_ui.cmb002.currentText()

	# 	try:
	# 		result = self.currentMats[text]
	# 	except:
	# 		result = None

	# 	return result


	# def chk007(self, state=None):
	# 	'''Assign Material: Current
	# 	'''
	# 	self.materials_ui.tb002.setText('Assign Current')


	# def chk008(self, state=None):
	# 	'''Assign Material: Random
	# 	'''
	# 	self.materials_ui.tb002.setText('Assign Random')


	# def chk009(self, state=None):
	# 	'''Assign Material: New
	# 	'''
	# 	self.materials_ui.tb002.setText('Assign New')