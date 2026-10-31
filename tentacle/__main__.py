# !/usr/bin/python
# coding=utf-8
"""Run tentacle's standalone panels as a program: ``python -m tentacle [panel]``,
or the ``tentacle`` command.

No argument opens a browser listing every panel; a panel's name (an entry-point
name in ``pyproject.toml``: ``compositor``, ``metashape_workflow``, ...) opens
that panel alone (``tcl_standalone.py``); ``--shortcut desktop`` / ``--shortcut
start_menu`` writes a launcher. The program is uitk's :class:`ExternalAppHub`:
this module only declares tentacle's name, icon, distribution and taskbar identity. As
``HUB`` it is also how a host's UI Browser (Maya, Blender) finds tentacle to
offer a desktop shortcut on each standalone panel's row.
"""

import os

from uitk import ExternalAppHub

from tentacle.tcl import Tcl

HUB = ExternalAppHub(
    "tentacle",
    title="tentacle",
    icon=os.path.join(os.path.dirname(os.path.abspath(__file__)), "tentacle.svg"),
    app_id="m3trik.tentacle",
    # Installed as ``tentacletk``: a source checkout's pyproject.toml carries
    # that name, and a missing provider installs it.
    dist=Tcl.DIST,
)

if __name__ == "__main__":
    raise SystemExit(HUB.run())
