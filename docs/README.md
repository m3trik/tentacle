## Tentacle

\*\*personal project. work in progress ..\*\*


##### 
---
<!-- short_description_start -->
*Tentacle is a marking menu style ui and toolkit derived from a QStackedWidget and constructed using the uitk backend.*
<!-- short_description_end -->

![alt text](https://raw.githubusercontent.com/m3trik/tentacle/master/docs/toolkit_demo.gif) \*Example re-opening the last scene, renaming a material, and selecting geometry by that material.

##


## Design:

![alt text](https://raw.githubusercontent.com/m3trik/tentacle/master/docs/dependancy_graph.jpg)


Module | Description
------- | -------
[tcl](https://github.com/m3trik/tentacle/blob/main/tentacle/tcl.py) | *A Custom QStackedWidget that handles UI hierarchy navigation.*
[overlay](https://github.com/m3trik/tentacle/blob/main/tentacle/overlay.py) | *Tracks cursor position and UI hierarchy to generate paint events that overlay the parent widget.*
[slots](https://github.com/m3trik/tentacle/blob/main/tentacle/slots) | *The source directory for the various slot connection modules.*
[ui](https://github.com/m3trik/tentacle/blob/main/tentacle/slots) | *The source directory for dynamic UI files.*

---

## Installation:

#####

To install:
install via pip in a command line window using:
```
python -m pip install tentacletk
```

To launch the marking menu:
For Maya:
Add a macro to a hotkey similar to the following:
```python
from tentacle import tcl_maya
tcl_maya.show(key_show='Key_F12')
```

For 3ds Max:
Add a macro to a hotkey similar to the following:
```python
macroScript main_max
category: "_macros.ui"
silentErrors: false
autoUndoEnabled: false
(
	python.Execute "from tentacle import tcl_max"
	python.Execute "tcl_max.show(key_show='Key_F12')"
)
```