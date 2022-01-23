# !/usr/bin/python
# coding=utf-8
from slots.max import *



class Init(Slots_max):
	'''
	'''
	def __init__(self, *args, **kwargs):
		Slots_max.__init__(self, *args, **kwargs)

		try:
			self.init_ui.hud.shown.connect(self.construct_hud)

		except AttributeError: #(an inherited class)
			pass


	def construct_hud(self):
		'''Add current scene attributes to a lineEdit.
		Only those with relevant values will be displayed.
		'''
		hud = self.init_ui.hud

		try:
			selection = rt.selection
		except AttributeError:
			selection = None

		if selection:
			if len(selection) is 1:
				obj = selection[0]
				symmetry = obj.modifiers[rt.Symmetry]
				if symmetry:
					int_ = symmetry.axis
					axis = {0:'x', 1:'y', 2:'z'}
					hud.insertText('Symmetry Axis: <font style="color: Yellow;">{}'.format(axis[int_].upper())) #symmetry axis

				level = rt.subObjectLevel if rt.subObjectLevel else 0
				if level==0: #object level
					numberOfSelected = len(selection)
					if numberOfSelected<11:
						name_and_type = ['<font style="color: Yellow;">{0}<font style="color: LightGray;">:{1}'.format(obj.name, rt.classOf(obj.baseObject)) for obj in selection]
						name_and_type_str = str(name_and_type).translate(str.maketrans('', '', ',[]\'')) #format as single string. remove brackets, single quotes, and commas.
					else:
						name_and_type_str = '' #if more than 10 objects selected, don't list each object.
					hud.insertText('Selected: <font style="color: Yellow;">{0}<br/>{1}'.format(numberOfSelected, name_and_type_str)) #currently selected objects by name and type.

				elif level>0: #component level
					obj = selection[0]
					objType = rt.classOf(obj.baseObject)

					if objType==rt.Editable_Poly or objType==rt.Edit_Poly:
						if level==1: #get vertex info
							type_ = 'Verts'
							components = Slots_max.bitArrayToArray(rt.polyop.getVertSelection(obj))
							total_num = rt.polyop.getNumVerts(obj)

						elif level==2: #get edge info
							type_ = 'Edges'
							components = Slots_max.bitArrayToArray(rt.polyop.getEdgeSelection(obj))
							total_num = rt.polyop.getNumEdges(obj)

						elif level==3: #get border info
							type_ = 'Borders'
							# rt.polyop.SetSelection #Edge ((polyOp.getOpenEdges $) as bitarray)
							components = Slots_max.bitArrayToArray(rt.polyop.getBorderSelection(obj))
							total_num = rt.polyop.getNumBorders(obj)

						elif level==4: #get face info
							type_ = 'Faces'
							components = Slots_max.bitArrayToArray(rt.polyop.getFaceSelection(obj))
							total_num = rt.polyop.getNumFaces(obj)

						elif level==5: #get element info
							type_ = 'Elements'
							components = Slots_max.bitArrayToArray(rt.polyop.getElementSelection(obj))
							total_num = rt.polyop.getNumElements(obj)

						try:
							hud.insertText('Selected {}: <font style="color: Yellow;">{} <font style="color: LightGray;">/{}'.format(type_, len(components), total_num)) #selected components
						except NameError:
							pass

		prevCommand = self.tcl.sb.prevCommand(docString=True)
		if prevCommand:
			hud.insertText('Prev Command: <font style="color: Yellow;">{}'.format(prevCommand))  #get button text from last used command

		# prevUi = self.tcl.sb.prevUiName(omitLevel=[0,1,2])
		# hud.insertText('Prev UI: {}'.format(prevUi.replace('_', '').title())) #get the last level 3 ui name string.

		# prevCamera = self.tcl.sb.prevCamera(docString=True)
		# hud.insertText('Prev Camera: {}'.format(prevCamera)) #get the previously used camera.









#module name
print (__name__)
# -----------------------------------------------
# Notes
# -----------------------------------------------




# -----------------------------------------------
# deprecated:
# -----------------------------------------------

	# def selectFaceLoop(tolerance, includeOpenEdges=False):
	# 	'''
	# 	:Parameters:
	# 		tolerance (float) = Face normal tolerance.
	# 		includeOpenEdges (bool) = 
	# 	'''
	# 	maxEval('''
	# 	selEdges = #{}
	# 	theObj = $

	# 	eCount = polyOp.getNumEdges theObj
	# 	for e = 1 to eCount do
	# 	(
	# 		theFaces = (polyOp.getEdgeFaces theObj e) as array
	# 		if theFaces.count == 2 then
	# 		(
	# 		 theAngle = acos(dot (polyOp.getFaceNormal theObj theFaces[1]) (polyOp.getFaceNormal theObj theFaces[2])) 
	# 			if theAngle >= tolerance do selEdges[e] = true
	# 		)	
	# 		else 
	# 			if includeOpenEdges do selEdges[e] = true
	# 	)
	# 	case classof (modPanel.getCurrentObject()) of
	# 	(
	# 		Editable_Poly: polyOp.setEdgeSelection theObj selEdges 
	# 		Edit_Poly: (modPanel.getCurrentObject()).SetSelection #Edge &selEdges 
	# 	)	
	# 	redrawViews()
	# 	''')


	# @staticmethod
	# def getVertices(obj):
	# 	'''Get the vertices of a given object whether it is an editable mesh or polygon.

	# 	:Parameters:
	# 		obj (obj) = polygon or mesh object.

	# 	:Return:
	# 		(list) vertex list.		
	# 	'''
	# 	try:
	# 		vertices = Slots_max.bitArrayToArray(rt.polyop.getVertSelection(obj)) #polygon
	# 	except:
	# 		vertices = Slots_max.bitArrayToArray(rt.getVertSelection(obj)) #mesh

	# 	return vertices


	# @staticmethod
	# def getSelectedVertices(obj):
	# 	'''Get the selected vertices of a given object whether it is an editable mesh or polygon.

	# 	:Parameters:
	# 		obj (obj) = polygon or mesh object.

	# 	:Return:
	# 		(list) vertex list.		
	# 	'''
	# 	try:
	# 		vertices = list(range(1, rt.polyop.getNumVerts(obj)))
	# 	except:
	# 		vertices = list(range(1, rt.getNumVerts(obj)))

	# 	return vertices


	# @staticmethod
	# def getEdges(obj):
	# 	'''Get the edges of a given object whether it is an editable mesh or polygon.

	# 	:Parameters:
	# 		obj (obj) = polygon or mesh object.

	# 	:Return:
	# 		(list) edge list.		
	# 	'''
	# 	try:
	# 		edges = list(range(1, rt.polyop.getNumEdges(obj)))
	# 	except:
	# 		edges = list(range(1, obj.edges.count))

	# 	return edges


	# @staticmethod
	# def getSelectedEdges(obj):
	# 	'''Get the selected edges of a given object whether it is an editable mesh or polygon.

	# 	:Parameters:
	# 		obj (obj) = polygon or mesh object.

	# 	:Return:
	# 		(list) edge list.		
	# 	'''
	# 	try:
	# 		edges = Slots_max.bitArrayToArray(rt.polyop.getEdgeSelection(obj)) #polygon
	# 	except:
	# 		edges = Slots_max.bitArrayToArray(rt.getEdgeSelection(obj)) #mesh

	# 	return edges


	# @staticmethod
	# def getFaces(obj):
	# 	'''Get the faces of a given object whether it is an editable mesh or polygon.

	# 	:Parameters:
	# 		obj (obj) = polygon or mesh object.

	# 	:Return:
	# 		(list) facet list.		
	# 	'''
	# 	try:
	# 		faces = list(range(1, rt.polyop.getNumFaces(obj)))
	# 	except:
	# 		faces = list(range(1, obj.faces.count))

	# 	return faces


	# @staticmethod
	# def getSelectedFaces(obj):
	# 	'''Get the selected faces of a given object whether it is an editable mesh or polygon.

	# 	:Parameters:
	# 		obj (obj) = polygon or mesh object.

	# 	:Return:
	# 		(list) facet list.		
	# 	'''
	# 	try:
	# 		faces = Slots_max.bitArrayToArray(rt.polyop.getFaceSelection(obj)) #polygon
	# 	except:
	# 		faces = Slots_max.bitArrayToArray(rt.getFaceSelection(obj)) #mesh

	# 	return faces




	# @staticmethod
	# def splitNonManifoldVertex(obj, vertex):
	# 	'''
	# 	Separate a connected vertex of non-manifold geometry where the faces share a single vertex.

	# 	:Parameters:
	# 		obj (obj) = A polygon object.
	# 		vertex (int) = A single vertex number of the given polygon object.
	# 	'''
	# 	connected_faces = rt.polyop.getFacesUsingVert(obj, vertex)

	# 	rt.polyop.breakVerts(obj, vertex)

	# 	#get a list for the vertices of each face that is connected to the original vertex.
	# 	verts_sorted_by_face=[]
	# 	for face in Slots_max.bitArrayToArray(connected_faces):
	# 		connected_verts = rt.polyop.getVertsUsingFace(obj, face)
	# 		verts_sorted_by_face.append(Slots_max.bitArrayToArray(connected_verts))


	# 	out=[] #1) take first set A from list. 2) for each other set B in the list do if B has common element(s) with A join B into A; remove B from list. 3) repeat 2. until no more overlap with A. 4) put A into outpup. 5) repeat 1. with rest of list.
	# 	while len(verts_sorted_by_face)>0:
	# 		first, rest = verts_sorted_by_face[0], verts_sorted_by_face[1:] #first, *rest = edges
	# 		first = set(first)

	# 		lf = -1
	# 		while len(first)>lf:
	# 			lf = len(first)

	# 			rest2=[]
	# 			for r in rest:
	# 				if len(first.intersection(set(r)))>0:
	# 					first |= set(r)
	# 				else:
	# 					rest2.append(r)     
	# 			rest = rest2

	# 		out.append(first)
	# 		verts_sorted_by_face = rest


	# 	for vertex_set in out:
	# 		obj.weldThreshold = 0.001
	# 		rt.polyop.weldVertsByThreshold(obj, list(vertex_set))


	# 	rt.polyop.setVertSelection(obj, vertex)



	# def setComboBox(self, comboBox, index):
	# 	'''
	# 	Set the given comboBox's index using a text string.
	# 	:Parameters:
	# 		comboBox (str) = comboBox name (will also be used as the methods name).
	# 		index = int or 'string' - text of the index to switch to.
	# 	'''
	# 	cmb = getattr(self.init_ui, comboBox)
	# 	method = getattr(self, comboBox)
	# 	cmb.currentIndexChanged.connect(method)
	# 	if not type(index)==int:
	# 		index = cmb.findText(index)
	# 	cmb.setCurrentIndex(index)