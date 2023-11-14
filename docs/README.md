[![License: LGPL v3](https://img.shields.io/badge/License-LGPL%20v3-blue.svg)](https://www.gnu.org/licenses/lgpl-3.0.en.html)
[![Version](https://img.shields.io/badge/Version-0.9.2-blue.svg)](https://pypi.org/project/tentacletk/)


# Tentacle: A Python3/PySide2 Marking Menu and DCC Toolkit

Tentacle is a Python3/PySide2 marking menu implemented using Qt's QStackedWidget. It is designed for use with Maya, 3ds Max, Blender, and any other DCC app that supports the PySide2 framework. It allows easy management of various user interfaces (UIs) and provides functionality related to key events and mouse interactions. This is an ongoing personal project and is currently a work in progress. At the moment, I have stopped developing for Max and Blender and am solely focused on Maya, as it proved too much of an undertaking at this stage to support all three apps, especially since I am still somewhat in the experimental stage. However, this can be easily extended to work with those apps. If you have any questions or thoughts about that, feel like collaborating on something, or anything else, just drop me message.

## Design

Tentacle runs on top of the [uitk](https://github.com/m3trik/uitk.git), a dynamic UI loader and management package which supports multiple UI, custom widget, and slot locations. 

## Example

The following example demonstrates re-opening the last scene, renaming a material, and selecting geometry by that material.

![Example](https://raw.githubusercontent.com/m3trik/tentacle/master/docs/toolkit_demo.gif)

## Structure

The structure of the project is as follows:

![Structure](https://raw.githubusercontent.com/m3trik/tentacle/master/docs/UML_diagram.jpg)

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
from tentacle import tcl_maya
tcl_maya.show(key_show='Key_F12')  # Change 'Z' to match your desired hotkey.
```

For 3ds Max, add a macro to a hotkey similar to the following:
```maxscript
macroScript main_max
category: "_macros.ui"
silentErrors: false
autoUndoEnabled: false
(
	python.Execute "from tentacle import tcl_max"
	python.Execute "tcl_max.show(key_show='Key_F12')"  // Change 'Z' to match your desired hotkey.
)
```
Again, please note that this is a personal project and is currently a work in progress. Contributions are welcome.
