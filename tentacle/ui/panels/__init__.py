# !/usr/bin/python
# coding=utf-8
"""Tool panels: one folder per panel, holding its ``.ui`` and its one Slots class, shared by
every host. Registered by :meth:`tentacle.tcl.Tcl.register_shared`; a panel reaches its host
only through a tool's API or ``self.tk``."""
