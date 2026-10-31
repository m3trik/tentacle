# !/usr/bin/python
# coding=utf-8
"""The Unity panels' shared Qt half: :class:`_unity_panel.UnityPanelMixin`.

Private to :mod:`tentacle.slots.tools.unity_bridge` (the Unity Bridge, whose engine
is each host library's ``UnityBridge``). extapps' standalone Unity Workflow keeps
a byte-identical copy of the mixin (``extapps/unity_workflow/_unity_panel.py``)
until the Unity Bridge panel's own move; ``extapps/test/test_vendor_sync.py``
holds the two together.
"""
