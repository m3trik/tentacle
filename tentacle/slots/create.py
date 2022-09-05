# !/usr/bin/python
# coding=utf-8
from slots import Slots



class Create(Slots):
	'''
	'''
	def __init__(self, *args, **kwargs):
		'''
		'''
		dh = self.sb.create.draggable_header
		dh.contextMenu.add(self.sb.ComboBox, setObjectName='cmb000', setToolTip='')

		cmb000 = self.sb.create.draggable_header.contextMenu.cmb000
		list_ = ['']
		cmb000.addItems_(list_, '')

		cmb001 = self.sb.create.cmb001
		list_ = ['Polygon', 'NURBS', 'Light']
		cmb001.addItems_(list_)

		cmb002 = self.sb.create.cmb002
		list_ = ["Cube", "Sphere", "Cylinder", "Plane", "Circle", "Cone", "Pyramid", "Torus", "Tube", "GeoSphere", "Platonic Solids", "Text"]
		cmb002.addItems_(list_)

		tb000 = self.sb.create.tb000
		tb000.contextMenu.add('QCheckBox', setText='Translate', setObjectName='chk000', setChecked=True, setToolTip='Move the created object to the center point of any selected object(s).')
		tb000.contextMenu.add('QCheckBox', setText='Scale', setObjectName='chk001', setChecked=True, setToolTip='Uniformly scale the created object to match the averaged scale of any selected object(s).')


	def draggable_header(self, state=None):
		'''Context menu
		'''
		dh = self.sb.create.draggable_header


	def createPrimitive(self, catagory1, catagory2):
		'''ie. createPrimitive('Polygons', 'Cube')
		:Parameters:
			catagory1 (str) = type
			catagory2 (str) = type
		'''
		cmb001 = self.sb.create.cmb001
		cmb002 = self.sb.create.cmb002

		cmb001.setCurrentIndex(cmb001.findText(catagory1))
		cmb002.setCurrentIndex(cmb002.findText(catagory2))
		self.tb000()


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
	