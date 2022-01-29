# !/usr/bin/python
# coding=utf-8
from slots.maya import *
from slots.symmetry import Symmetry



class Symmetry_maya(Symmetry, Slots_maya):
	def __init__(self, *args, **kwargs):
		Slots_maya.__init__(self, *args, **kwargs)
		Symmetry.__init__(self, *args, **kwargs)

		cmb000 = self.symmetry_ui.draggable_header.contextMenu.cmb000
		items = ['']
		cmb000.addItems_(items, '')

		#set initial checked state
		state = pm.symmetricModelling(query=True, symmetry=True) #application symmetry state
		axis = pm.symmetricModelling(query=True, axis=True)
		widget = 'chk000' if axis=='x' else 'chk001' if axis=='y' else 'chk002'
		getattr(self.symmetry_ui, widget).setChecked(state)
		getattr(self.symmetry_submenu_ui, widget).setChecked(state)


	def cmb000(self, index=None):
		'''Editors
		'''
		cmb = self.symmetry_ui.draggable_header.contextMenu.cmb000

		if index>0:
			if index==cmd.items.index(''):
				pass
			cmb.setCurrentIndex(0)


	@Slots.message
	def chk005(self, state=None):
		'''Symmetry: Topo
		'''
		self.symmetry_ui.chk004.setChecked(False) #uncheck symmetry:object space
		if any ([self.symmetry_ui.chk000.isChecked(), self.symmetry_ui.chk001.isChecked(), self.symmetry_ui.chk002.isChecked()]): #(symmetry)
			pm.symmetricModelling(edit=True, symmetry=False)
			self.toggleWidgets(setUnChecked='chk000,chk001,chk002')
			return 'Note: First select a seam edge and then check the symmetry button to enable topographic symmetry'


	@Slots.message
	def setSymmetry(self, state, axis):
		space = "world" #workd space
		if self.symmetry_ui.chk004.isChecked(): #object space
			space = "object"
		elif self.symmetry_ui.chk005.isChecked(): #topological symmetry
			space = "topo"

		tolerance = 0.25
		pm.symmetricModelling(edit=True, symmetry=state, axis=axis, about=space, tolerance=tolerance)
		if state:
			self.viewPortMessage('Symmetry: <hl>{}</hl>'.format(axis.upper()))









#module name
print (__name__)
# -----------------------------------------------
# Notes
# -----------------------------------------------