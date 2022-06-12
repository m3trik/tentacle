# !/usr/bin/python
# coding=utf-8
from slots import Slots



class Create(Slots):
	'''
	'''
	def __init__(self, *args, **kwargs):
		'''
		:Parameters: 
			**kwargs (inherited from this class's respective slot child class, and originating from switchboard.setClassInstanceFromUiName)
				properties:
					sb (class instance) = The switchboard instance.  Allows access to ui and slot objects across modules.
					<name>_ui (ui object) = The ui object of <name>. ie. self.polygons_ui
					<widget> (registered widget) = Any widget previously registered in the switchboard module. ie. self.PushButton
				functions:
					current_ui (lambda function) = Returns the current ui if it is either the parent or a child ui for the class; else, return the parent ui. ie. self.current_ui()
					<name> (lambda function) = Returns the slot class instance of that name.  ie. self.polygons()
		'''
		ctx = self.create_ui.draggable_header.contextMenu
		if not ctx.containsMenuItems:
			ctx.add(self.ComboBox, setObjectName='cmb000', setToolTip='')

		cmb = self.create_ui.draggable_header.contextMenu.cmb000
		list_ = ['']
		cmb.addItems_(list_, '')

		cmb = self.create_ui.cmb001
		list_ = ['Polygon', 'NURBS', 'Light']
		cmb.addItems_(list_)

		cmb = self.create_ui.cmb002
		list_ = ["Cube", "Sphere", "Cylinder", "Plane", "Circle", "Cone", "Pyramid", "Torus", "Tube", "GeoSphere", "Platonic Solids", "Text"]
		cmb.addItems_(list_)

		ctx = self.create_ui.tb000.contextMenu
		if not ctx.containsMenuItems:
			ctx.add('QCheckBox', setText='Translate', setObjectName='chk000', setChecked=True, setToolTip='Move the created object to the center point of any selected object(s).')
			ctx.add('QCheckBox', setText='Scale', setObjectName='chk001', setChecked=True, setToolTip='Uniformly scale the created object to match the averaged scale of any selected object(s).')


	def draggable_header(self, state=None):
		'''Context menu
		'''
		dh = self.create_ui.draggable_header


	def createPrimitive(self, catagory1, catagory2):
		'''ie. createPrimitive('Polygons', 'Cube')
		:Parameters:
			catagory1 (str) = type
			catagory2 (str) = type
		'''
		cmb001 = self.create_ui.cmb001
		cmb002 = self.create_ui.cmb002

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
	