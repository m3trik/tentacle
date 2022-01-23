# !/usr/bin/python
# coding=utf-8



class Transform_ui():
	'''
	'''
	def __init__(self, *args, **kwargs):
		'''
		:Parameters: 
			**kwargs (passed in via the switchboard module's 'getClassInstanceFromUiName' method.)
				properties:
					tcl (class instance) = The tentacle stacked widget instance. ie. self.tcl
					<name>_ui (ui object) = The ui of <name> ie. self.polygons for the ui of filename polygons. ie. self.polygons_ui
				functions:
					current_ui (lambda function) = Returns the current ui if it is either the parent or a child ui for the class; else, return the parent ui. ie. self.current_ui()
					'<name>' (lambda function) = Returns the class instance of that name.  ie. self.polygons()
		'''
		ctx = self.transform_ui.draggable_header.contextMenu
		if not ctx.containsMenuItems:
			ctx.add(self.tcl.wgts.ComboBox, setObjectName='cmb000', setToolTip='')


		cmb = self.transform_ui.draggable_header.contextMenu.cmb000
		files = ['']
		cmb.addItems_(files, '')


		cmb = self.transform_ui.cmb003
		cmb.popupStyle = 'qmenu'
		cmb.menu_.setTitle('Snap')
		if not cmb.menu_.containsMenuItems:
			values = [('chk021', 'Move: <b>Off</b>'), ('s021', 'increment:', 1, '1.00-1000 step2.8125'), 
					('chk022', 'Scale: <b>Off</b>'), ('s022', 'increment:', 1, '1.00-1000 step2.8125'), 
					('chk023', 'Rotate: <b>Off</b>'), ('s023', 'degrees:', 11.25, '1.00-360 step2.8125')]

			widgets = [cmb.menu_.add(self.tcl.wgts.CheckBox, setObjectName=i[0], setText=i[1], setTristate=1) if len(i)==2 
					else cmb.menu_.add('QDoubleSpinBox', setObjectName=i[0], setPrefix=i[1], setValue=i[2], setMinMax_=i[3], setDisabled=1) for i in values]


		ctx = self.transform_ui.tb000.contextMenu #drop to grid.
		if not ctx.containsMenuItems:
			ctx.add('QComboBox', addItems=['Min','Mid','Max'], setObjectName='cmb004', setToolTip='Choose which point of the bounding box to align to.')
			ctx.add('QCheckBox', setText='Move to Origin', setObjectName='chk014', setChecked=True, setToolTip='Move to origin (xyz 0,0,0).')
			ctx.add('QCheckBox', setText='Center Pivot', setObjectName='chk016', setChecked=True, setToolTip='Center pivot on objects bounding box.')
			ctx.add('QCheckBox', setText='Freeze Transforms', setObjectName='chk017', setChecked=True, setToolTip='Reset the selected transform and all of its children down to the shape level.')


		ctx = self.transform_ui.tb001.contextMenu
		if not ctx.containsMenuItems:
			ctx.add('QCheckBox', setText='X Axis', setObjectName='chk029', setDisabled=True, setToolTip='Align X axis')
			ctx.add('QCheckBox', setText='Y Axis', setObjectName='chk030', setDisabled=True, setToolTip='Align Y axis')
			ctx.add('QCheckBox', setText='Z Axis', setObjectName='chk031', setDisabled=True, setToolTip='Align Z axis')
			ctx.add('QCheckBox', setText='Between Two Components', setObjectName='chk013', setToolTip='Align the path along an edge loop between two selected vertices or edges.')
			ctx.add('QCheckBox', setText='Align Loop', setObjectName='chk007', setToolTip='Align entire edge loop from selected edge(s).')
			ctx.add('QCheckBox', setText='Average', setObjectName='chk006', setToolTip='Align to last selected object or average.')
			ctx.add('QCheckBox', setText='Auto Align', setObjectName='chk010', setChecked=True, setToolTip='')
			ctx.add('QCheckBox', setText='Auto Align: Two Axes', setObjectName='chk011', setToolTip='')

		