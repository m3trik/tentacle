#!/usr/bin/python
# coding=utf-8
"""Regression tests for tentacle.slots.maya.lighting.

Lighting launches two mayatk panels via marking_menu.show(): b000 (HDR
Manager) and b001 (Lightmap Baker). Pin the key names — drift would
silently break the launch buttons.
"""
import unittest

try:
    from tentacle.slots.maya import lighting as lighting_module

    _AVAILABLE = True
except ImportError:
    lighting_module = None
    _AVAILABLE = False


class _FakeMarkingMenu:
    def __init__(self):
        self.shown = []

    def show(self, name):
        self.shown.append(name)


class _FakeHandlers:
    def __init__(self):
        self.marking_menu = _FakeMarkingMenu()


class _FakeSb:
    def __init__(self):
        self.handlers = _FakeHandlers()


@unittest.skipUnless(_AVAILABLE, "Requires tentacle import path")
class TestB000HdrManager(unittest.TestCase):
    """b000 shows the 'hdr_manager' marking menu."""

    def test_b000_routes_to_hdr_manager(self):
        instance = lighting_module.Lighting.__new__(lighting_module.Lighting)
        instance.sb = _FakeSb()
        instance.b000()
        self.assertEqual(instance.sb.handlers.marking_menu.shown, ["hdr_manager"])

    def test_b001_routes_to_lightmap_baker(self):
        instance = lighting_module.Lighting.__new__(lighting_module.Lighting)
        instance.sb = _FakeSb()
        instance.b001()
        self.assertEqual(instance.sb.handlers.marking_menu.shown, ["lightmap_baker"])


if __name__ == "__main__":
    unittest.main()
