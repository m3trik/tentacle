# !/usr/bin/python
# coding=utf-8
"""The app-bridge panels' shared base: :class:`host_bridge.HostBridge`.

Private to tentacle's app-bridge tools (Unity, Marmoset, Substance, RizomUV and
DCC bridges). Each tool's
engine and host behavior are its library's (``self.tk.<X>Bridge``,
``self.tk.BridgeHost``, ``self.tk.BakeSourceSet``).
"""
