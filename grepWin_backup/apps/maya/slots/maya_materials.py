# !/usr/bin/python
# coding=utf-8
# from __future__ import print_function, absolute_import
from builtins import super
import os.path

from maya_init import *



class Materials(Init):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)

		self.currentMats=None
		self.randomMat=None

		self.materials_submenu_ui.b003.setVisible(False)


	@property
	def currentMat(self):
		'''Get the current material using the current index of the materials combobox.
		'''
		text = self.materials_ui.cmb002.currentText()

		try:
			result = self.currentMats[text]
		except:
			result = None

		return result


	def draggable_header(self, state=None):
		'''Context menu
		'''
		dh = self.materials_ui.draggable_header

		if state is 'setMenu':
			dh.contextMenu.add(wgts.ComboBox, setObjectName='cmb001', setToolTip='Maya Material Editors')
			dh.contextMenu.add(wgts.Label, setText='Material Attributes', setObjectName='lbl004', setToolTip='Show the material attributes in the attribute editor.')
			return


	def chk007(self, state=None):
		'''Assign Material: Current
		'''
		self.materials_ui.tb002.setText('Assign Current')


	def chk008(self, state=None):
		'''Assign Material: Random
		'''
		self.materials_ui.tb002.setText('Assign Random')


	def chk009(self, state=None):
		'''Assign Material: New
		'''
		self.materials_ui.tb002.setText('Assign New')


	def cmb001(self, index=-1):
		'''Editors
		'''
		cmb = self.materials_ui.cmb001

		if index is 'setMenu':
			files = ['Hypershade']
			cmb.addItems_(files, 'Maya Material Editors')
			return

		if index>0:
			text = cmb.items[index]
			if text=='Hypershade':
				mel.eval('HypershadeWindow;')
			cmb.setCurrentIndex(0)


	def cmb002(self, index=-1):
		'''Material list

		:Parameters:
			index (int) = parameter on activated, currentIndexChanged, and highlighted signals.
		'''
		cmb = self.materials_ui.cmb002
		tb = self.materials_ui.tb001
		b = self.materials_submenu_ui.b003

		if index is 'setMenu':
			cmb.contextMenu.add(wgts.Label, setText='Open in Editor', setObjectName='lbl000', setToolTip='Open material in editor.')
			cmb.contextMenu.add(wgts.Label, setText='Rename', setObjectName='lbl001', setToolTip='Rename the current material.')
			cmb.contextMenu.add(wgts.Label, setText='Delete', setObjectName='lbl002', setToolTip='Delete the current material.')
			cmb.contextMenu.add(wgts.Label, setText='Delete All Unused Materials', setObjectName='lbl003', setToolTip='Delete All unused materials.')
			cmb.beforePopupShown.connect(self.cmb002) #refresh comboBox contents before showing it's popup.
			cmb.returnPressed.connect(lambda: self.lbl001(setEditable=False))
			return

		try:
			sceneMaterials = tb.menu_.chk000.isChecked()
			idMapMaterials = tb.menu_.chk001.isChecked()
			favoriteMaterials = tb.menu_.chk002.isChecked()
		except: #if the toolbox hasn't been constructed yet: default to sceneMaterials
			sceneMaterials = True

		if sceneMaterials:
			materials = self.getSceneMaterials()

		elif idMapMaterials:
			materials = self.getSceneMaterials(startingWith=['ID_'])

		elif favoriteMaterials:
			materials = self.getFavoriteMaterials()
			self.currentMats = {matName:lambda: pm.createNode(matName) for matName in sorted(list(set(materials)))}


		self.currentMats = {mat.name():mat for mat in sorted(list(set(materials))) if hasattr(mat,'name')} if not favoriteMaterials else self.currentMats
		cmb.addItems_(list(self.currentMats.keys()), clear=True)

		#create and set icons with color swatch
		for i, mat in enumerate(self.currentMats.keys()):
			icon = Materials.getColorSwatchIcon(mat)
			cmb.setItemIcon(i, icon) if icon else None

		#set submenu assign material button attributes
		b.setText('Assign '+cmb.currentText())
		icon = Materials.getColorSwatchIcon(cmb.currentText(), [15, 15])
		b.setIcon(icon) if icon else None
		b.setMinimumWidth(b.minimumSizeHint().width()+25)
		b.setVisible(True if cmb.currentText() else False)


	@Slots.message
	def tb000(self, state=None):
		'''Select By Material Id
		'''
		tb = self.current_ui.tb000
		if state is 'setMenu':
			tb.menu_.add('QCheckBox', setText='Current Material', setObjectName='chk010', setChecked=True, setToolTip='Use the current material, <br>else use the current viewport selection to get a material.')
			tb.menu_.add('QCheckBox', setText='All Objects', setObjectName='chk003', setToolTip='Search all scene objects, or only those currently selected.')
			tb.menu_.add('QCheckBox', setText='Shell', setObjectName='chk005', setToolTip='Select entire shell.')
			tb.menu_.add('QCheckBox', setText='Invert', setObjectName='chk006', setToolTip='Invert Selection.')
			return

		if not self.currentMat:
			return 'Error: No Material Selection.'

		shell = tb.menu_.chk005.isChecked() #Select by material: shell
		invert = tb.menu_.chk006.isChecked() #Select by material: invert
		allObjects = tb.menu_.chk003.isChecked() #Search all scene objects
		currentMaterial = tb.menu_.chk010.isChecked() #Use the current material instead of the material of the current viewport selection.

		objects = pm.ls(sl=1, objectsOnly=1) if not allObjects else None
		material = self.currentMat if currentMaterial else None


		self.selectByMaterialID(material, objects, shell=shell, invert=invert)


	def tb001(self, state=None):
		'''Stored Material Options
		'''
		tb = self.materials_ui.tb001
		if state is 'setMenu':
			tb.menu_.add('QRadioButton', setText='All Scene Materials', setObjectName='chk000', setChecked=True, setToolTip='List all scene materials.') #Material mode: Scene Materials
			tb.menu_.add('QRadioButton', setText='ID Map Materials', setObjectName='chk001', setToolTip='List ID map materials.') #Material mode: ID Map Materials
			tb.menu_.add('QRadioButton', setText='Favorite Materials', setObjectName='chk002', setToolTip='List Favorite materials.') #Material mode: Favorite Materials

			self.connect_([tb.menu_.chk000, tb.menu_.chk001], 'toggled', [self.cmb002, self.tb001])
			return

		#set the groupbox title to reflect the current mode.
		if tb.menu_.chk000.isChecked():
			self.materials_ui.group000.setTitle(tb.menu_.chk000.text())
		elif tb.menu_.chk001.isChecked():
			self.materials_ui.group000.setTitle(tb.menu_.chk001.text())
		elif tb.menu_.chk002.isChecked():
			self.materials_ui.group000.setTitle(tb.menu_.chk002.text())


	@Slots.message
	def tb002(self, state=None):
		'''Assign Material
		'''
		tb = self.materials_ui.tb002
		if state is 'setMenu':
			tb.menu_.add('QRadioButton', setText='Current Material', setObjectName='chk007', setChecked=True, setToolTip='Re-Assign the current stored material.')
			tb.menu_.add('QRadioButton', setText='New Material', setObjectName='chk009', setToolTip='Assign a new material.')
			tb.menu_.add('QRadioButton', setText='New Random Material', setObjectName='chk008', setToolTip='Assign a new random ID material.')
			return

		selection = pm.ls(selection=1, flatten=1)
		if not selection:
			return 'Error: No renderable object is selected for assignment.'

		assignCurrent = tb.menu_.chk007.isChecked()
		assignRandom = tb.menu_.chk008.isChecked()
		assignNew = tb.menu_.chk009.isChecked()

		if assignCurrent: #Assign current mat
			self.assignMaterial(selection, self.currentMat)

		elif assignRandom: #Assign New random mat ID
			mat = self.createRandomMaterial(prefix='ID_')
			self.assignMaterial(selection, mat)

			#delete previous shader
			# if self.randomMat:
			# 	pm.delete(self.randomMat)

			self.randomMat = mat

			if self.materials_ui.tb001.menu_.chk001.isChecked(): #ID map material mode
				self.cmb002() #refresh the combobox
			else:
				self.materials_ui.tb001.menu_.chk001.setChecked(True) #set combobox to ID map mode. toggling the checkbox refreshes the combobox.
			self.materials_ui.cmb002.setCurrentItem(mat.name()) #set the combobox index to the new mat #self.cmb002.setCurrentIndex(self.cmb002.findText(name))

		elif assignNew: #Assign New Material
			mel.eval('buildObjectMenuItemsNow "MainPane|viewPanes|modelPanel4|modelPanel4|modelPanel4|modelPanel4ObjectPop";')
			mel.eval('createAssignNewMaterialTreeLister "";')


	@Slots.message
	def lbl000(self):
		'''Open material in editor
		'''
		if self.materials_ui.tb001.menu_.chk001.isChecked(): #ID map mode
			try:
				mat = self.currentMats[self.materials_ui.cmb002.currentText()] #get object from string key
			except:
				return '# Error: No stored material or no valid object selected.'
		else: #Stored material mode
			if not self.currentMat: #get material from selected scene object
				if pm.ls(sl=1, objectsOnly=1):
					self.currentMat = self.getMaterial()
				else:
					return '# Error: No stored material or no valid object selected.'
			mat = self.currentMat

		#open the hypershade editor
		mel.eval("HypershadeWindow;")


	def lbl001(self, setEditable=True):
		'''Rename Material: Set cmb002 as editable and disable wgts.
		'''
		cmb = self.materials_ui.cmb002

		if setEditable:
			self._mat = self.currentMat
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
		mat = self.currentMat
		mat = pm.delete(mat)

		index = self.materials_ui.cmb002.currentIndex()
		self.materials_ui.cmb002.setItemText(index, 'None') #self.materials_ui.cmb002.removeItem(index)


	def lbl003(self):
		'''Delete Unused Materials
		'''
		mel.eval('hyperShadePanelMenuCommand("hyperShadePanel1", "deleteUnusedNodes");')
		self.cmb002() #refresh the combobox


	def lbl004(self):
		'''Material Attributes: Show Material Attributes in the Attribute Editor.
		'''
		if self.currentMat and hasattr(self.currentMat, 'name'):
			mel.eval('showSG '+self.currentMat.name())


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
		'''Store Material
		'''
		selection = pm.ls(selection=1)
		if not selection:
			return 'Error: Nothing selected.'

		mat = self.getMaterial()

		self.materials_ui.tb001.menu_.chk000.setChecked(True) #set the combobox to show all scene materials
		cmb = self.materials_ui.cmb002
		self.cmb002() #refresh the combobox
		cmb.setCurrentIndex(cmb.items.index(mat.name()))


	def b003(self):
		'''Assign: Assign Current
		'''
		self.materials_ui.tb002.menu_.chk007.setChecked(True)
		self.materials_ui.tb002.setText('Assign Current')
		self.tb002()


	def b004(self):
		'''Assign: Assign Random
		'''
		self.materials_ui.tb002.menu_.chk008.setChecked(True)
		self.materials_ui.tb002.setText('Assign Random')
		self.tb002()


	def b005(self):
		'''Assign: Assign New
		'''
		self.materials_ui.tb002.menu_.chk009.setChecked(True)
		self.materials_ui.tb002.setText('Assign New')
		self.tb002()


	@staticmethod
	def getColorSwatchIcon(mat, size=[20, 20]):
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
				pm.rename(curMatName, newMatName)

			except RuntimeError as error:
				cmb.setItemText(cmb.currentIndex(), str(error.strip('\n')))


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


	@staticmethod
	def getSceneMaterials(startingWith=[''], exclude=['standardSurface']):
		'''Get All Materials from the current scene.

		:Parameters:
			startingWith (list) = Filters material names starting with any of the strings in the given list. ie. ['ID_']
			exclude (list) = Node types to exclude.

		:Return:
			(list) materials.
		'''
		materials = [m for m in pm.ls(mat=1, flatten=1) if filter(str(m.name()).startswith, startingWith) and not pm.nodeType(m) in exclude]

		return materials


	@staticmethod
	def getFavoriteMaterials():
		'''Get Maya Favorite Materials List.

		:Return:
			(list) materials.
		'''
		import maya.app.general.tlfavorites as _fav

		path = os.path.expandvars(r"%USERPROFILE%/Documents/maya/2020/prefs/renderNodeTypeFavorites")
		renderNodeTypeFavorites = _fav.readFavorites(path)
		materials = [i for i in renderNodeTypeFavorites if '/' not in i]
		del _fav

		return materials


	@staticmethod
	def getMaterial(obj=''):
		'''Get the material from the selected face.

		:Parameters:
			(str)(obj) = The obj with the material.

		:Return:
			(list) material
		'''
		pm.hyperShade(obj, shaderNetworksSelectMaterialNodes=1) #selects the material node 
		mats = pm.ls(selection=1, materials=1) #now add the selected node to a variable

		return mats[0]


	@staticmethod
	def createRandomMaterial(name=None, prefix=''):
		'''Creates a random material.

		:Parameters:
			name (str) = material name.
			prefix (str) = Optional string to be appended to the beginning of the name.

		:Return:
			(obj) material
		'''
		import random
		rgb = [random.randint(0, 255) for _ in range(3)] #generate a list containing 3 values between 0-255

		if name is None: #create name from rgb values
			name = '_'.join([prefix, str(rgb[0]), str(rgb[1]), str(rgb[2])])

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
	@Init.undoChunk
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
		for obj in objects:
			pm.select(obj) #hyperShade works more reliably with an explicit selection.
			pm.hyperShade(obj, assign=mat)
		# pm.undoInfo(closeChunk=1)









#module name
print(os.path.splitext(os.path.basename(__file__))[0])
# -----------------------------------------------
# Notes
# -----------------------------------------------

#depricated

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

# def cmb000(self, index=-1):
	# 	'''
	# 	Existing Materials

	# 	'''
	# 	cmb = self.materials_ui.cmb000

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