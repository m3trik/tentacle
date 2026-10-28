# !/usr/bin/python
# coding=utf-8
"""The app-bridge panels' shared base: :class:`host_bridge.HostBridge`.

Private to tentacle's bridge tools (``slots/tools/unity_bridge.py`` first; the
Marmoset, Substance, RizomUV, Blender and Maya bridges as they move). Each tool's
engine and host behavior are its library's (``self.tk.<X>Bridge``,
``self.tk.BridgeHost``, ``self.tk.BakeSourceSet``).
"""
