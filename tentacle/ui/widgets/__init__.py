# !/usr/bin/python
# coding=utf-8
import sys, os.path

sys.path.append(os.path.dirname(os.path.abspath(__file__))) #append this dir to the system path.

if __name__=='__main__':
	import tentacle.ui.widgets
	globals()['__package__'] = 'tentacle.ui.widgets'


from .menu import Menu
from .label import Label
from .comboBox import ComboBox
from .checkBox import CheckBox
from .pushButton import PushButton
from .toolButton import ToolButton
from .textEdit import TextEdit
from .lineEdit import LineEdit
from .progressBar import ProgressBar
from .messageBox import MessageBox
from .pushButtonDraggable import PushButtonDraggable
from .treeWidgetExpandableList import TreeWidgetExpandableList
from .widgetMultiWidget import WidgetMultiWidget as MultiWidget
from .widgetGifPlayer import WidgetGifPlayer as GifPlayer
from .widgetLoadingIndicator import WidgetLoadingIndicator as LoadingIndicator

# print ('tentacle.ui.widgets:', __name__, __package__, __file__)






# -----------------------------------------------
# Notes
# -----------------------------------------------


# -----------------------------------------------
# deprecated:
# -----------------------------------------------


# import sys, os
# this_module_dir = os.path.abspath(os.path.dirname(__file__))
# sys.path.append(this_module_dir)
# import sys; for p in sys.path: print (p)