#!/usr/bin/python
# coding=utf-8
"""Regression tests for tentacle.slots.maya.lighting.

Lighting is a small slot. The only behavioral unit is b000 (HDR Manager)
which drives marking_menu.show("hdr_manager"). Pin the key name —
drift would silently break the HDR Manager launch button.
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


if __name__ == "__main__":
    unittest.main()
