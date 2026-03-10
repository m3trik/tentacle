"""Performance test: tb004 Lock/Unlock Attributes.

Compares the old PyMEL set_lock_state approach vs direct cmds.setAttr.
"""
import sys
import time
import unittest

import maya.cmds as cmds
import maya.standalone

maya.standalone.initialize()

sys.path.insert(0, r"o:\Cloud\Code\_scripts\mayatk")
sys.path.insert(0, r"o:\Cloud\Code\_scripts\pythontk")
import pymel.core as pm
import mayatk as mtk


ALL_ATTRS = ("tx", "ty", "tz", "rx", "ry", "rz", "sx", "sy", "sz")
NUM_OBJECTS = 200
ITERATIONS = 5


def _create_scene():
    cmds.file(new=True, force=True)
    nodes = []
    for i in range(NUM_OBJECTS):
        nodes.append(cmds.polyCube(name=f"cube_{i}")[0])
    cmds.select(nodes)
    return nodes


def _old_approach(nodes, lock):
    """Old: PyMEL set_lock_state with translate/rotate/scale kwargs."""
    pm_nodes = pm.ls(nodes)
    mtk.Attributes.set_lock_state(pm_nodes, translate=lock, rotate=lock, scale=lock)


def _new_approach(nodes, lock):
    """New: Direct cmds.setAttr loop."""
    for node in nodes:
        for attr in ALL_ATTRS:
            try:
                cmds.setAttr(f"{node}.{attr}", lock=lock)
            except Exception:
                pass


class TestTb004Performance(unittest.TestCase):
    def test_correctness(self):
        """Verify both approaches produce identical results."""
        nodes = _create_scene()

        # Lock with new approach
        _new_approach(nodes, True)
        for node in nodes:
            for attr in ALL_ATTRS:
                self.assertTrue(
                    cmds.getAttr(f"{node}.{attr}", lock=True),
                    f"{node}.{attr} should be locked",
                )

        # Unlock with new approach
        _new_approach(nodes, False)
        for node in nodes:
            for attr in ALL_ATTRS:
                self.assertFalse(
                    cmds.getAttr(f"{node}.{attr}", lock=True),
                    f"{node}.{attr} should be unlocked",
                )

        # Lock with old approach
        _old_approach(nodes, True)
        for node in nodes:
            for attr in ALL_ATTRS:
                self.assertTrue(
                    cmds.getAttr(f"{node}.{attr}", lock=True),
                    f"{node}.{attr} should be locked (old)",
                )

        # Unlock with old approach
        _old_approach(nodes, False)
        for node in nodes:
            for attr in ALL_ATTRS:
                self.assertFalse(
                    cmds.getAttr(f"{node}.{attr}", lock=True),
                    f"{node}.{attr} should be unlocked (old)",
                )

    def test_timing(self):
        """Benchmark old vs new approach."""
        nodes = _create_scene()

        # Warm up
        _old_approach(nodes, True)
        _new_approach(nodes, False)

        # Time old approach
        old_times = []
        for _ in range(ITERATIONS):
            start = time.perf_counter()
            _old_approach(nodes, True)
            _old_approach(nodes, False)
            old_times.append(time.perf_counter() - start)

        # Time new approach
        new_times = []
        for _ in range(ITERATIONS):
            start = time.perf_counter()
            _new_approach(nodes, True)
            _new_approach(nodes, False)
            new_times.append(time.perf_counter() - start)

        old_avg = sum(old_times) / len(old_times)
        new_avg = sum(new_times) / len(new_times)
        speedup = old_avg / new_avg if new_avg > 0 else float("inf")

        print(f"\n{'='*60}")
        print(f"  Lock/Unlock {NUM_OBJECTS} objects x {len(ALL_ATTRS)} attrs")
        print(f"  {ITERATIONS} iterations each (lock+unlock per iter)")
        print(f"{'='*60}")
        print(f"  Old (set_lock_state): {old_avg:.4f}s avg")
        print(f"  New (cmds.setAttr):   {new_avg:.4f}s avg")
        print(f"  Speedup:              {speedup:.2f}x")
        print(f"{'='*60}")

        self.assertGreater(speedup, 1.0, "New approach should be faster")


if __name__ == "__main__":
    unittest.main(verbosity=2)
