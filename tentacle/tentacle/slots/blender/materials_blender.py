# !/usr/bin/python
# coding=utf-8
from slots.blender import *
from slots.materials import Materials



class Materials_blender(Materials, Slots_blender):
	def __init__(self, *args, **kwargs):
		Slots_blender.__init__(self, *args, **kwargs)
		Materials.__init__(self, *args, **kwargs)

		self.randomMat = None

		dh = self.materials_ui.draggable_header
		dh.contextMenu.add(self.tcl.wgts.ComboBox, setObjectName='cmb000', setToolTip='Material Editors')
		dh.contextMenu.add(self.tcl.wgts.Label, setText='Material Attributes', setObjectName='lbl004', setToolTip='Show the material attributes in the attribute editor.')

		cmb000 = self.materials_ui.draggable_header.contextMenu.cmb000
		items = []
		cmb000.addItems_(items, 'Material Editors')


	def cmb000(self, index=None):
		'''Editors
		'''
		cmb = self.materials_ui.draggable_header.contextMenu.cmb000

		if index>0:
			text = cmb.items[index]
			if text=='Hypershade':
				mel.eval('HypershadeWindow;')
			cmb.setCurrentIndex(0)


	def cmb002(self, index=None):
		'''Material list

		:Parameters:
			index (int) = parameter on activated, currentIndexChanged, and highlighted signals.
		'''
		cmb = self.materials_ui.cmb002
		b = self.materials_submenu_ui.b003

		mode = cmb.contextMenu.cmb001.currentText()
		if mode=='Scene Materials':
			materials = self.getSceneMaterials(exclude=['standardSurface'])

		elif mode=='ID Map Materials':
			materials = self.getSceneMaterials(startingWith=['ID_'])

		if mode=='Favorite Materials':
			fav_materials = self.getFavoriteMaterials()
			currentMats = {matName:matName for matName in sorted(list(set(fav_materials)))}
		else:
			currentMats = {mat.name():mat for mat in sorted(list(set(materials))) if hasattr(mat, 'name')} 

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

		objects = pm.ls(sl=1, objectsOnly=1) if not allObjects else None

		self.selectByMaterialID(mat, objects, shell=shell, invert=invert)


	@Slots.message
	def tb002(self, state=None):
		'''Assign Material
		'''
		tb = self.materials_ui.tb002

		selection = pm.ls(selection=1, flatten=1)
		if not selection:
			return 'Error: No renderable object is selected for assignment.'

		assignCurrent = tb.contextMenu.chk007.isChecked()
		assignRandom = tb.contextMenu.chk008.isChecked()
		assignNew = tb.contextMenu.chk009.isChecked()

		if assignCurrent: #Assign current mat
			mat = self.materials_ui.cmb002.currentData()
			if isinstance(mat, str): #new mat type as a string:
				self.assignMaterial(selection, pm.createNode(mat))
			else: #existing mat object:
				self.assignMaterial(selection, mat)

		elif assignRandom: #Assign New random mat ID
			mat = self.createRandomMaterial(prefix='ID_')
			self.assignMaterial(selection, mat)

			self.randomMat = mat

			self.cmb002() #refresh the materials list comboBox
			self.materials_ui.cmb002.setCurrentItem(mat.name()) #set the combobox index to the new mat #self.cmb002.setCurrentIndex(self.cmb002.findText(name))

		elif assignNew: #Assign New Material
			mel.eval('buildObjectMenuItemsNow "MainPane|viewPanes|modelPanel4|modelPanel4|modelPanel4|modelPanel4ObjectPop";')
			mel.eval('createAssignNewMaterialTreeLister "";')


	@Slots.message
	def lbl000(self):
		'''Open material in editor
		'''
		try:
			mat = self.materials_ui.cmb002.currentData() #get the mat obj from cmb002
			pm.select(mat)
		except:
			return 'Error: No stored material or no valid object selected.'

		pm.mel.HypershadeWindow() #open the hypershade editor


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
		mat = self.materials_ui.cmb002.currentData()
		mat = pm.delete(mat)

		index = self.materials_ui.cmb002.currentIndex()
		self.materials_ui.cmb002.setItemText(index, 'None') #self.materials_ui.cmb002.removeItem(index)


	def lbl003(self):
		'''Delete Unused Materials
		'''
		mel.eval('hyperShadePanelMenuCommand("hyperShadePanel1", "deleteUnusedNodes");')
		self.cmb002() #refresh the materials list comboBox


	def lbl004(self):
		'''Material Attributes: Show Material Attributes in the Attribute Editor.
		'''
		mat = self.materials_ui.cmb002.currentData()
		try:
			mel.eval('showSG '+mat.name())

		except Exception as error:
			print (error)


	def b000(self):
		'''Material List: Delete
		'''
		self.lbl002()


	def b001(self):
		'''Material List: Edit
		'''
		self.lbl000()


	@Slots.message
	def b002(self):
		'''Set Material: Set the Currently Selected Material as the currentMaterial.
		'''
		selection = pm.ls(selection=1)
		if not selection:
			return 'Error: Nothing selected.'

		mat = self.getMaterial()

		self.materials_ui.cmb002.contextMenu.cmb001.setCurrentIndex(0) #set the combobox to show all scene materials
		self.cmb002() #refresh the materials list comboBox
		self.materials_ui.cmb002.setCurrentItem(mat.name())


	def getColorSwatchIcon(self, mat, size=[20, 20]):
		'''Get an icon with a color fill matching the given materials RBG value.

		:Parameters:
			mat (obj)(str) = The material or the material's name.
			size (list) = Desired icon size.

		:Return:
			(obj) pixmap icon.
		'''
		try:
			matName = mat.name() if not isinstance(mat, (str)) else mat #get the string name if a mat object is given.
			r = int(pm.getAttr(matName+'.colorR')*255) #convert from 0-1 to 0-255 value and then to an integer
			g = int(pm.getAttr(matName+'.colorG')*255)
			b = int(pm.getAttr(matName+'.colorB')*255)
			pixmap = QtGui.QPixmap(size[0],size[1])
			pixmap.fill(QtGui.QColor.fromRgb(r, g, b))

			return QtGui.QIcon(pixmap)

		except AttributeError:
			pass


	def renameMaterial(self, mat, newMatName):
		'''Rename Material
		'''
		cmb = self.materials_ui.cmb002 #scene materials

		curMatName = mat.name()
		if curMatName!=newMatName:
			cmb.setItemText(cmb.currentIndex(), newMatName)
			try:
				print (curMatName, newMatName)
				pm.rename(curMatName, newMatName)

			except RuntimeError as error:
				cmb.setItemText(cmb.currentIndex(), str(error).strip('\n'))


	@Slots.message
	def selectByMaterialID(self, material=None, objects=None, shell=False, invert=False):
		'''Select By Material Id
	
		material (obj) = The material to search and select for.
		objects (list) = Faces or mesh objects as a list. If no objects are given, all geometry in the scene will be searched.
		shell (bool) = Select the entire shell.
		invert (bool) = Invert the final selection.R

		#ex call:
		selectByMaterialID(material)
		'''
		if pm.nodeType(material)=='VRayMultiSubTex': #if not a multimaterial
			return 'Error: If material is a multimaterial, select a submaterial.'

		if not material:
			if not pm.ls(sl=1):
				return 'Error: Nothing selected. Select an object face, or choose the option: current material.'
			material = self.getMaterial()

		pm.select(material)
		pm.hyperShade(objects='') #select all with material. "" defaults to currently selected materials.

		if objects:
			[pm.select(i, deselect=1) for i in pm.ls(sl=1) if i.split('.')[0] not in objects]

		faces = pm.filterExpand(selectionMask=34, expand=1)
		transforms = pm.listRelatives(faces, p=True) #[node.replace('Shape','') for node in pm.ls(sl=1, objectsOnly=1, visible=1)] #get transform node name from shape node

		if shell or invert: #deselect so that the selection can be modified.
			pm.select(faces, deselect=1)

		if shell:
			for shell in transforms:
				pm.select(shell, add=1)
		
		if invert:
			for shell in transforms:
				allFaces = [shell+".f["+str(num)+"]" for num in range(pm.polyEvaluate (shell, face=1))] #create a list of all faces per shell
				pm.select(list(set(allFaces)-set(faces)), add=1) #get inverse of previously selected faces from allFaces


	def getSceneMaterials(self, startingWith=[''], exclude=[]):
		'''Get All Materials from the current scene.

		:Parameters:
			startingWith (list) = Filters material names starting with any of the strings in the given list. ie. ['ID_']
			exclude (list) = Node types to exclude. ie. ['standardSurface']

		:Return:
			(list) materials.
		'''
		materials = [m for m in pm.ls(mat=1, flatten=1) 
						if list(filter(m.name().startswith, startingWith)) and not pm.nodeType(m) in exclude] #
		return materials


	def getFavoriteMaterials(self):
		'''Get Maya Favorite Materials List.

		:Return:
			(list) materials.
		'''
		import maya.app.general.tlfavorites as _fav, os.path

		path = os.path.expandvars(r"%USERPROFILE%/Documents/maya/2022/prefs/renderNodeTypeFavorites")
		renderNodeTypeFavorites = _fav.readFavorites(path)
		materials = [i for i in renderNodeTypeFavorites if '/' not in i]
		del _fav

		return materials


	def getMaterial(self, obj=''):
		'''Get the material from the selected face.

		:Parameters:
			(str)(obj) = The obj with the material.

		:Return:
			(list) material
		'''
		pm.hyperShade(obj, shaderNetworksSelectMaterialNodes=1) #selects the material node 
		mats = pm.ls(selection=1, materials=1) #now add the selected node to a variable

		return mats[0]


	def createRandomMaterial(self, name='', prefix=''):
		'''Creates a random material.

		:Parameters:
			name (str) = material name.
			prefix (str) = Optional string to be appended to the beginning of the name.

		:Return:
			(obj) material.
		'''
		import random
		rgb = [random.randint(0, 255) for _ in range(3)] #generate a list containing 3 values between 0-255

		name = '{}{}_{}_{}_{}'.format(prefix, name, str(rgb[0]), str(rgb[1]), str(rgb[2]))

		#create shader
		mat = pm.shadingNode('lambert', asShader=1, name=name)
		#convert RGB to 0-1 values and assign to shader
		convertedRGB = [round(float(v)/255, 3) for v in rgb]
		pm.setAttr(name+'.color', convertedRGB)
		#assign to selected geometry
		# pm.select(selection) #initial selection is lost upon node creation
		# pm.hyperShade(assign=mat)

		return mat


	@Slots.message
	@Slots_blender.undoChunk
	def assignMaterial(self, objects, mat):
		'''Assign Material

		objects (list) = Faces or mesh objects as a list.
		material (obj) = The material to search and select for.
		'''
		if not mat:
			return 'Error: Material Not Assigned. No material given.'

		try: #if the mat is a not a known type; try and create the material.
			pm.nodeType(mat)
		except:
			mat = pm.shadingNode(mat, asShader=1)

		# pm.undoInfo(openChunk=1)
		for obj in pm.ls(objects):
			pm.select(obj) #hyperShade works more reliably with an explicit selection.
			pm.hyperShade(obj, assign=mat)
		# pm.undoInfo(closeChunk=1)









#module name
print (__name__)
# -----------------------------------------------
# Notes
# -----------------------------------------------

#depricated


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

# elif storedMaterial:
# 	mat = self.currentMat
# 	if not mat:
# 		cmb.addItems_(['Stored Material: None'])
# 		return

# 	matName = mat.name()

# 	if pm.nodeType(mat)=='VRayMultiSubTex':
# 		subMaterials = pm.hyperShade(mat, listUpstreamShaderNodes=1) #get any connected submaterials
# 		subMatNames = [s.name() for s in subMaterials if s is not None]
# 	else:
# 		subMatNames=[]

# 	contents = cmb.addItems_(subMatNames, matName)

# 	if index is None:
# 		index = cmb.currentIndex()
# 	if index!=0:
# 		self.currentMat = subMaterials[index-1]
# 	else:
# 		self.currentMat = mat

# def cmb000(self, index=None):
	# 	'''
	# 	Existing Materials

	# 	'''
	# 	cmb = self.materials_ui.draggable_header.contextMenu.cmb000

	# 	mats = [m for m in pm.ls(materials=1)]
	# 	matNames = [m.name() for m in mats]

	# 	contents = cmb.addItems_(matNames, "Scene Materials")

	# 	if index is None:
	# 		index = cmb.currentIndex()
	# 	if index!=0:
	# 		print contents[index]
			
	# 		self.currentMat = mats[index-1] #store material
	# 		self.cmb002() #refresh combobox

	# 		cmb.setCurrentIndex(0)


	



#assign random
	# mel.eval('''
# 		string $selection[] = `ls -selection`;

# 		int $d = 2; //decimal places to round to
# 		$r = rand (0,1);
# 		$r = trunc($r*`pow 10 $d`+0.5)/`pow 10 $d`;
# 		$g = rand (0,1);
# 		$g = trunc($g*`pow 10 $d`+0.5)/`pow 10 $d`;
# 		$b = rand (0,1);
# 		$b = trunc($b*`pow 10 $d`+0.5)/`pow 10 $d`;

# 		string $rgb = ("_"+$r+"_"+$g+"_"+$b);
# 		$rgb = substituteAllString($rgb, "0.", "");

# 		$name = ("ID_"+$rgb);

# 		string $ID_ = `shadingNode -asShader lambert -name $name`;
# 		setAttr ($name + ".colorR") $r;
# 		setAttr ($name + ".colorG") $g;
# 		setAttr ($name + ".colorB") $b;

# 		for ($object in $selection)
# 			{
# 			select $object;
# 			hyperShade -assign $ID_;
# 			}
# 		 ''')

#re-assign random
	# mel.eval('''
		# string $objList[] = `ls -selection -flatten`;
		# $material = `hyperShade -shaderNetworksSelectMaterialNodes ""`;
		# string $matList[] = `ls -selection -flatten`;

		# hyperShade -objects $material;
		# string $selection[] = `ls -selection`;
		# //delete the old material and shader group nodes
		# for($i=0; $i<size($matList); $i++)
		# 	{
		# 	string $matSGplug[] = `connectionInfo -dfs ($matList[$i] + ".outColor")`;
		# 	$SGList[$i] = `match "^[^\.]*" $matSGplug[0]`;
		# 	print $matList; print $SGList;
		# 	delete $matList[$i];
		# 	delete $SGList[$i];
		# 	}
		# //create new random material
		# int $d = 2; //decimal places to round to
		# $r = rand (0,1);
		# $r = trunc($r*`pow 10 $d`+0.5)/`pow 10 $d`;
		# $g = rand (0,1);
		# $g = trunc($g*`pow 10 $d`+0.5)/`pow 10 $d`;
		# $b = rand (0,1);
		# $b = trunc($b*`pow 10 $d`+0.5)/`pow 10 $d`;

		# string $rgb = ("_"+$r+"_"+$g+"_"+$b+"");
		# $rgb = substituteAllString($rgb, "0.", "");

		# $name = ("ID_"+$rgb);

		# string $ID_ = `shadingNode -asShader lambert -name $name`;
		# setAttr ($name + ".colorR") $r;
		# setAttr ($name + ".colorG") $g;
		# setAttr ($name + ".colorB") $b;

		# for ($object in $selection)
		# 	{
		# 	select $object;
		# 	hyperShade -assign $ID_;
		# 	}
		# ''')