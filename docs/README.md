###### \*A Python3/PySide2 marking menu style toolkit for Maya, 3ds Max, and Blender.

*personal project. work in progress..*

## Design:

###### 

*This is a dynamic ui toolkit with a marking menu style ui at it's core (derived from a QStackedWidget). The switchboard module (derived from QUiLoader) provides properties and convenience methods that allow quick and easy getting/setting of relevant ui and widget data across modules.*

![alt text](https://raw.githubusercontent.com/m3trik/tentacle/master/docs/toolkit_demo.gif) \*Example re-opening the last scene, renaming a material, and selecting geometry by that material.

## 

---

## Structure:

![alt text](https://raw.githubusercontent.com/m3trik/tentacle/master/docs/dependancy_graph.jpg)

#### tcl:

###### *handles main gui construction for the marking menu.*

#### events:

###### *event handling for dynamic ui.*

#### overlay:

###### *tracks cursor position and ui hierarchy to generate paint events that overlay the main widget.*

#### switchboard:

###### *loads dynamic ui with custom widgets. Contains properties and convenience methods for interacting with the ui.*

#### slots:

###### *parent class housing methods that are inherited across all app specific slot class modules.*

## 

---

## Installation:

###### 

To install:
Add the tentacle folder to a directory on your python path, or
install via pip in a command line window using:
```
python -m pip install tcl-toolkit
```

To launch the marking menu:
For Maya:
Add a macro to a hotkey similar to the following:
```
	def hk_tentacle_show():
		'''Display the tentacle marking menu.
		'''
		if 'tcl' not in globals():
			import tentacle
			from tentacle.tcl_maya import Tcl_maya
			global tcl
			tcl = Tcl_maya(key_show='Key_F12', profile=False)

		tcl.sendKeyPressEvent(tcl.key_show)
```

For 3ds Max:
Add a macro to a hotkey similar to the following:
```
macroScript main_max
category: "_macros.ui"
silentErrors: false
autoUndoEnabled: false
(
	python.Execute "if 'tcl' not in globals():import tentacle; from tentacle.tcl_max import Tcl_max; global tcl; tcl = Tcl_max(key_show='Key_Z')" --create an instance.
	python.Execute "tcl.sendKeyPressEvent(tcl.key_show);" --show the instance.
)
```

See the switchboard module for a demo on how to launch stand alone dynamic ui.
