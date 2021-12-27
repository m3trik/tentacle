###### *A Python3/PySide2 marking menu style toolkit for Maya, 3ds Max, and Blender.
*personal project. work in progress..*

## Design:
######
*This is a dynamic and modular marking menu style ui, with a QStackedWidget at it's core.  The switchboard module provides convenience methods that allow quick and easy lookups when getting/setting ui and widget data across modules.*

![alt text](https://raw.githubusercontent.com/m3trik/tentacle/master/docs/toolkit_demo.gif)
*Example re-opening the last scene, renaming a material, and selecting geometry by that material.


##
-----------------------------------------------
 Structure:
-----------------------------------------------

![alt text](https://raw.githubusercontent.com/m3trik/tentacle/master/docs/dependancy_graph.jpg)


#### tcl:
###### *handles main gui construction.*

#### childEvents:
###### *event handling for child widgets.*

#### overlay:
###### *tracks cursor position and ui hierarchy to generate paint events that overlay the main widget.*

#### switchboard:
###### *contains a master dictionary for widget related info as well as convienience classes for interacting with the dict.*

#### slots:
###### *parent class holding methods that are inherited across all parent app specific slot class modules.*



##
-----------------------------------------------
 Installation:
-----------------------------------------------
######
For Maya:
add these lines to a startup script:
```
sys.path.append('your path to /tentacle') --append the dir containing 'append_to_path.py' to the python path.
import append_to_path as ap
ap.appendPaths('maya', verbose=0)
```
and to launch the menu, add a macro to a hotkey like the following:
```
	def hk_tentacle_show():
		'''Display the tentacle marking menu.
		'''
		if 'tcl' not in globals():
			from tcl_maya import Tcl_maya
			global tcl
			tcl = Tcl_maya(key_show='Key_F12', profile=False)

		tcl.sendKeyPressEvent(tcl.key_show)
```

For 3ds Max:
add these lines to a startup script:
```
python.Init() --initalize python
python.Execute("import sys; sys.path.append('your path to /tentacle')") --append the dir containing 'append_to_path.py' to the python path.
python.Execute("import append_to_path as ap; ap.appendPaths('max', verbose=0)")
```
and to launch the menu, add a macro to a hotkey like the following:
```
macroScript main_max
category: "_macros.ui"
silentErrors: false
autoUndoEnabled: false
(
	python.Execute "if 'tcl' not in globals(): from tcl_max import Tcl_max; global tcl; tcl = Tcl_max(key_show='Key_Z')" --create an instance.
	python.Execute "tcl.sendKeyPressEvent(tcl.key_show);" --show the instance.
)
```
