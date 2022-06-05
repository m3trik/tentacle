# !/usr/bin/python
# coding=utf-8
import sys, os.path

import importlib
import inspect



sys.path.append(os.path.dirname(os.path.abspath(__file__))) #append this dir to the system path.
globals()['__package__'] = 'widgets'


for module in os.listdir(os.path.dirname(__file__)):

	mod_name = module[:-3]
	mod_ext = module[-3:]

	if module == '__init__.py' or mod_ext != '.py':
		continue

	mod = importlib.import_module(mod_name)

	cls_members = inspect.getmembers(sys.modules[mod_name], inspect.isclass)

	for cls_name, cls_mem in cls_members:
		globals()[cls_name] = cls_mem

del module


widgets = [w for w in globals().values() if type(w).__name__=='ObjectType'] #get all imported widget classes as a dict.









# -----------------------------------------------
# Notes
# -----------------------------------------------

'''
EXAMPLE USE CASE:
import ui.widgets as wgts

wgts.PushButton #get a specific widget.
wgts.widgets #get a list of all widgets.
'''

# -----------------------------------------------
# deprecated:
# -----------------------------------------------


#explicit imports:
# from .menu import Menu
# from .label import Label
# from .comboBox import ComboBox
# from .checkBox import CheckBox
# from .pushButton import PushButton
# from .pushButton_optionBox import PushButton_optionBox
# # from .toolButton import ToolButton
# from .textEdit import TextEdit
# from .lineEdit import LineEdit
# from .progressBar import ProgressBar
# from .messageBox import MessageBox
# from .pushButtonDraggable import PushButtonDraggable
# from .treeWidgetExpandableList import TreeWidgetExpandableList
# # from .widgetMultiWidget import WidgetMultiWidget as MultiWidget
# # from .widgetGifPlayer import WidgetGifPlayer as GifPlayer
# # from .widgetLoadingIndicator import WidgetLoadingIndicator as LoadingIndicator

# # print ('tentacle.ui.widgets:', __name__, __package__, __file__)



# import sys, os
# this_module_dir = os.path.abspath(os.path.dirname(__file__))
# sys.path.append(this_module_dir)
# import sys; for p in sys.path: print (p)