# !/usr/bin/python
# coding=utf-8
from tentacle.slots import Slots



class Create(Slots):
	'''
	'''
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		'''
		'''
		dh = self.sb.create.draggableHeader
		dh.ctxMenu.add(self.sb.ComboBox, setObjectName='cmb000', setToolTip='')

		cmb000 = self.sb.create.draggableHeader.ctxMenu.cmb000
		items = ['']
		cmb000.addItems_(items, '')

		cmb001 = self.sb.create.cmb001
		items = ['Polygon', 'NURBS', 'Light']
		cmb001.addItems_(items)

		cmb002 = self.sb.create.cmb002
		items = ["Cube", "Sphere", "Cylinder", "Plane", "Circle", "Cone", "Pyramid", "Torus", "Tube", "GeoSphere", "Platonic Solids", "Text"]
		cmb002.addItems_(items)

		tb000 = self.sb.create.tb000
		tb000.ctxMenu.add('QCheckBox', setText='Translate', setObjectName='chk000', setChecked=True, setToolTip='Move the created object to the center point of any selected object(s).')
		tb000.ctxMenu.add('QCheckBox', setText='Scale', setObjectName='chk001', setChecked=True, setToolTip='Uniformly scale the created object to match the averaged scale of any selected object(s).')


	def draggableHeader(self, state=None):
		'''Context menu
		'''
		dh = self.sb.create.draggableHeader


	def createPrimitive(self, catagory1, catagory2):
		'''Create a primitive object.

		Parameters:
			catagory1 (str): type
			catagory2 (str): type
		Return:
			(obj) node

		Example: createPrimitive('Polygons', 'Cube')
		'''
		cmb001 = self.sb.create.cmb001
		cmb002 = self.sb.create.cmb002

		cmb001.setCurrentIndex(cmb001.findText(catagory1))
		cmb002.setCurrentIndex(cmb002.findText(catagory2))
		return self.tb000()


	def b001(self):
		'''Create poly cube
		'''
		self.createPrimitive('Polygon', 'Cube')


	def b002(self):
		'''Create poly sphere
		'''
		self.createPrimitive('Polygon', 'Sphere')


	def b003(self):
		'''Create poly cylinder
		'''
		self.createPrimitive('Polygon', 'Cylinder')


	def b004(self):
		'''Create poly plane
		'''
		self.createPrimitive('Polygon', 'Plane')
	