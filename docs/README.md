# Tentacle: A Python3/PySide2 Marking Menu and UI Toolkit

Tentacle is a Python3/PySide2 marking menu and UI toolkit designed for Maya, 3ds Max, Blender, and any other DCC app that supports the PySide2 framework. It is a personal project and is currently a work in progress.

## Design

Tentacle is a dynamic UI toolkit with a marking menu style UI derived from a QStackedWidget. The switchboard module, derived from QUiLoader, provides properties and convenience methods that allow quick and easy getting/setting of relevant UI and widget data across modules.

## Example

The following example demonstrates re-opening the last scene, renaming a material, and selecting geometry by that material.

![Example](https://raw.githubusercontent.com/m3trik/tentacle/master/docs/toolkit_demo.gif)

## Structure

The structure of the project is as follows:

![Structure](https://raw.githubusercontent.com/m3trik/tentacle/master/docs/dependancy_graph.jpg)

| Module | Description |
| ------- | ----------- |
| [tcl](https://github.com/m3trik/uitk/blob/main/tentacle/tcl.py) | Handles main GUI construction for the marking menu. |
| [overlay](https://github.com/m3trik/uitk/blob/main/tentacle/overlay.py) | Tracks cursor position and UI hierarchy to generate paint events that overlay its parent widget. |
| [ui](https://github.com/m3trik/uitk/blob/main/tentacle/events.py) | Location of the dynamic UI files. |
| [slots](https://github.com/m3trik/uitk/blob/main/tentacle/slots) | Location of the various slot modules. |

## Installation

Add the `tentacle` folder to a directory on your Python path, or install via pip in a command line window using:

```bash
python -m pip install tentacletk
```
## Usage
To launch the marking menu:

For Maya, add a macro to a hotkey similar to the following:
```python
from uitk import tcl_maya
tcl_maya.show(key_show='Key_F12')
```

For 3ds Max, add a macro to a hotkey similar to the following:
```maxscript
macroScript main_max
category: "_macros.ui"
silentErrors: false
autoUndoEnabled: false
(
	python.Execute "from uitk import tcl_max"
	python.Execute "tcl_max.show(key_show='Key_F12')"
)
```
Again, please note that this is a personal project and is currently a work in progress. Contributions are welcome.