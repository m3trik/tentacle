## Tentacle is a Python3/PySide2 marking menu and ui toolkit for Maya, 3ds Max, and Blender.

\*\*personal project. work in progress ..\*\*

## Design:

##### 

*This is a dynamic ui toolkit with a marking menu style ui derived from a QStackedWidget. The switchboard module (derived from QUiLoader) provides properties and convenience methods that allow quick and easy getting/setting of relevant ui and widget data across modules.*


## Example:

![alt text](https://raw.githubusercontent.com/m3trik/uitk/master/docs/toolkit_demo.gif) \*Example re-opening the last scene, renaming a material, and selecting geometry by that material.


## Structure:

![alt text](https://raw.githubusercontent.com/m3trik/uitk/master/docs/dependancy_graph.jpg)


Example | Description
------- | -------
[tcl](https://github.com/m3trik/uitk/blob/main/uitk/tcl.py) | *Handles main gui construction for the marking menu.*
[events](https://github.com/m3trik/uitk/blob/main/uitk/events.py) | *Event handling for dynamic ui.*
[overlay](https://github.com/m3trik/uitk/blob/main/uitk/overlay.py) | *Tracks cursor position and ui hierarchy to generate paint events that overlay it's parent widget.*
[slots](https://github.com/m3trik/uitk/blob/main/uitk/slots) | *Modules for the various slot connections.*

---


## Installation:

#####
Add the `tentacle` folder to a directory on your python path, or
install via pip in a command line window using:
```
python -m pip install tentacletk
```

To launch the marking menu:
For Maya:
Add a macro to a hotkey similar to the following:
```
from uitk import tcl_maya
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
	python.Execute "from uitk import tcl_max"
	python.Execute "tcl_max.show(key_show='Key_F12')"
)
```