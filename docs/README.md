###### \*A Python3/PySide2 marking menu style toolkit for Maya, 3ds Max, and Blender.

*personal project. work in progress..*

## Design:

###### 

*This is a dynamic ui toolkit with a marking menu style ui (derived from a QStackedWidget) at it's core. The switchboard module (derived from QUiLoader) provides properties and convenience methods that allow quick and easy getting/setting of relevant ui and widget data across modules.*

![alt text](https://raw.githubusercontent.com/m3trik/tentacle/master/docs/toolkit_demo.gif) \*Example re-opening the last scene, renaming a material, and selecting geometry by that material.

## 

---

## Structure:

![alt text](https://raw.githubusercontent.com/m3trik/tentacle/master/docs/dependancy_graph.jpg)


Example | Description
------- | -------
[tcl](https://github.com/m3trik/tentacle/blob/main/tentacle/tcl.py) | *handles main gui construction for the marking menu.*
[events](https://github.com/m3trik/tentacle/blob/main/tentacle/events.py) | *event handling for dynamic ui.*
[overlay](https://github.com/m3trik/tentacle/blob/main/tentacle/overlay.py) | *tracks cursor position and ui hierarchy to generate paint events that overlay the main widget.*
[switchboard](https://github.com/m3trik/tentacle/blob/main/tentacle/switchboard.py) | *loads dynamic ui with custom widgets. Contains properties and convenience methods for interacting with the ui.*
[slots](https://github.com/m3trik/tentacle/blob/main/tentacle/slots.py) | *parent class housing methods that are inherited across all app specific slot class modules.*

---

## Installation:

###### 

To install:
Add the tentacle folder to a directory on your python path, or
install via pip in a command line window using:
```
python -m pip install tentacletk
```

To launch the marking menu:
For Maya:
Add a macro to a hotkey similar to the following:
```
from tentacle import tcl_maya
tcl_maya.show(key_show='Key_F12')
```

For 3ds Max:
Add a macro to a hotkey similar to the following:
```
macroScript main_max
category: "_macros.ui"
silentErrors: false
autoUndoEnabled: false
(
	python.Execute "from tentacle import tcl_max"
	python.Execute "tcl_max.getInstance(key_show='Key_F12').show()"
)
```

See the switchboard module for a demo on how to launch a stand alone dynamic ui.
