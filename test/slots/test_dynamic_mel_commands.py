#!/usr/bin/python
# coding=utf-8
"""MEL strings stored in module/class-level constant containers also resolve.

Several slots build dispatch tables of MEL snippets and pass them through
``mel.eval(cmd)`` at runtime — for example
``tentacle/slots/maya/edit.py:_CONVERT_COMMANDS``. The constant-string
``mel.eval(...)`` scanner can't see those values because the call site
takes a variable, not a literal. A typo in such a table only surfaces
when the user clicks the corresponding menu item.

Heuristic (see ``find_mel_string_constants`` in ``_helpers``):

* assignment target name is UPPER_SNAKE (with optional leading underscore)
* RHS is a Dict / List / Tuple / Set
* string values inside that look MEL-shaped (end with ``;`` or first token
  is a plausible MEL identifier)

Validates the first whitespace-delimited token via ``whatIs``, sharing
the priming + allow-list infrastructure of ``test_mel_references``.
"""
import unittest

from _helpers import (
    find_mel_string_constants,
    first_mel_token,
    slot_files,
)
from _host import MAYA_AVAILABLE
from test_mel_references import (
    _KNOWN_LAZY,
    _ensure_plugins_loaded,
    _prime_mel_globals,
)

# Procs that live behind menus / panels Maya only sources when their UI
# is built. They're real, just not visible to a fresh `whatIs` query in
# a standalone session. Verified by hand against the Maya 2025 install.
_KNOWN_LAZY_TABLE_PROCS = frozenset(
    {
        "performnurbsToPoly",
        "performSubdivCreate",
        "performSmoothMeshPreviewToPolygon",
        "performSubdivTessellate",
        "performSubdToNurbs",
        "convertTypeCapsToCurves",
        "nurbsCurveToBezier",
        "bezierCurveToNurbs",
        "performPaintEffectsToNurbs",
        "performPaintEffectsToCurve",
        "performTextureToGeom",
        "displacementToPoly",
        "setupAnimatedDisplacement",
        "fluidToPoly",
        "particleToPoly",
        "convertInstanceToObject",
        "performGeomToBBox",
    }
)


@unittest.skipUnless(
    MAYA_AVAILABLE, "Requires maya.cmds + maya.mel (run via mayapy)"
)
class TestDynamicMelCommands(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _ensure_plugins_loaded()
        _prime_mel_globals()

    def test_every_constant_table_mel_string_resolves(self):
        import maya.mel as mel

        unresolved = []
        skipped_lazy = []
        for f in slot_files():
            source = f.read_text(encoding="utf-8")
            for line_no, mel_str in find_mel_string_constants(source):
                token = first_mel_token(mel_str)
                if not token:
                    continue
                try:
                    kind = mel.eval(f'whatIs "{token}"')
                except RuntimeError as exc:
                    unresolved.append(
                        (f.name, line_no, token, mel_str, f"eval failed: {exc}")
                    )
                    continue
                if kind.lower().startswith("unknown"):
                    if token in _KNOWN_LAZY or token in _KNOWN_LAZY_TABLE_PROCS:
                        skipped_lazy.append((f.name, line_no, token))
                    else:
                        unresolved.append(
                            (f.name, line_no, token, mel_str, kind)
                        )

        if skipped_lazy:
            print(
                f"\n[dynamic-mel] {len(skipped_lazy)} known-lazy procs "
                "(allow-listed):"
            )
            for fname, line, token in skipped_lazy:
                print(f"  {fname}:{line}  {token}")

        if unresolved:
            lines = [
                f"  {fname}:{line}  {token!r}  -> {kind}\n"
                f"      literal: {mel_str!r}"
                for fname, line, token, mel_str, kind in unresolved
            ]
            self.fail(
                f"Found {len(unresolved)} MEL constant-table tokens unknown "
                "to Maya (not in allow-list):\n" + "\n".join(lines)
            )


if __name__ == "__main__":
    unittest.main()
