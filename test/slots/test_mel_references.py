#!/usr/bin/python
# coding=utf-8
"""Every mel.eval("Y …") string literal in the slots resolves to a known
MEL identifier (proc, runTimeCommand, command, or script).

We extract the first whitespace-delimited token from each `mel.eval(...)`
literal and ask Maya `whatIs` about it. `whatIs` is reliable for things
Maya has already discovered at startup (built-in commands, RTCs, sourced
MEL scripts), but Maya defers loading large parts of its MEL library
until first use — so we have to nudge it before the walk.

Two-stage strategy:
1. **Prime** by sourcing the MEL files we know contain procs the slots
   call. Wrapped in Python try/except so missing files don't fail the test.
2. **Allow-list** procs we've validated by hand to live behind plugins or
   to be loaded lazily by Maya's UI startup, which we can't trigger from
   maya.standalone. These get reported as "skipped" rather than failures.

Caveats:
- f-strings and runtime-built MEL strings are skipped — we can only
  validate static literals.
- This test asserts *resolvability*, not behavior. A proc can resolve
  and still error at runtime if its arguments are wrong.
"""
import unittest

from _helpers import (
    find_mel_eval_strings,
    first_mel_token,
    slot_files,
)
from _host import MAYA_AVAILABLE


# MEL files we explicitly source up-front so the procs they define become
# visible to `whatIs`. Located by grepping `global proc <name>\b` under
# Maya's scripts/ tree. Quietly skipped if a file isn't on Maya's MEL path.
_PRIME_SOURCES = (
    # performAlignUV, performLinearAlignUV
    "uvTkBuildAlignSnapOptions.mel",
    # hyperShadePanelMenuCommand
    "hyperShadePanel.mel",
    # redoPreviousRender
    "renderWindowPanel.mel",
    # createAssignNewMaterialTreeLister
    "buildShaderMenus.mel",
)

# Plugins to ensure are loaded before MEL resolution. mayapy.standalone
# auto-loads more plugins than fresh interactive Maya does — fbxmaya
# in particular registers FBXUICallBack only when explicitly loaded.
_REQUIRED_PLUGINS = ("fbxmaya",)

# Procs we've manually verified to be real Maya identifiers but which can't
# be reliably primed in a standalone session — they live behind plugins
# (modelingToolkit's `dR_*` family) or runTimeCommands defined late in
# the GUI startup chain (`Send*Selection`).
_KNOWN_LAZY = frozenset(
    {
        # Modeling Toolkit (dR_*) — sourced by modelingToolkit plugin.
        "dR_multiCutTool",
        "dR_connectTool",
        "dR_quadDrawTool",
        "dR_selConstraintAngle",
        "dR_selConstraintBorder",
        "dR_selConstraintEdgeLoop",
        "dR_selConstraintEdgeRing",
        "dR_selConstraintElement",
        "dR_selConstraintUVEdgeLoop",
        "dR_selConstraintOff",
        # runTimeCommands registered by Maya's preview/menu init scripts.
        "SendToUnrealSelection",
        "SendToUnitySelection",
    }
)


def _prime_mel_globals():
    """Source MEL files in _PRIME_SOURCES; tolerate missing files."""
    import maya.mel as mel

    for source_file in _PRIME_SOURCES:
        try:
            mel.eval(f'source "{source_file}";')
        except RuntimeError:
            # File not on Maya's MEL path — fine, will fall through to
            # the allow-list or a hard failure for genuinely missing procs.
            pass


def _ensure_plugins_loaded():
    """Load plugins that register MEL procs the slots reference."""
    import maya.cmds as cmds

    for plugin in _REQUIRED_PLUGINS:
        try:
            if not cmds.pluginInfo(plugin, query=True, loaded=True):
                cmds.loadPlugin(plugin, quiet=True)
        except RuntimeError:
            # Plugin missing on this Maya install — fall through; the
            # affected procs will surface as failures (real signal).
            pass


@unittest.skipUnless(MAYA_AVAILABLE, "Requires maya.cmds + maya.mel (run via mayapy)")
class TestMelReferences(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _ensure_plugins_loaded()
        _prime_mel_globals()

    def test_every_mel_eval_first_token_resolves(self):
        import maya.mel as mel

        unresolved = []  # genuine failures
        skipped_lazy = []  # tracked but tolerated
        for f in slot_files():
            source = f.read_text(encoding="utf-8")
            for line_no, mel_str in find_mel_eval_strings(source):
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
                    if token in _KNOWN_LAZY:
                        skipped_lazy.append((f.name, line_no, token))
                    else:
                        unresolved.append((f.name, line_no, token, mel_str, kind))

        if skipped_lazy:
            print(
                f"\n[mel-refs] {len(skipped_lazy)} known-lazy procs (allow-listed):"
            )
            for fname, line, token in skipped_lazy:
                print(f"  {fname}:{line}  {token}")

        if unresolved:
            lines = [
                f"  {fname}:{line}  {token!r}  → {kind}\n      mel.eval({mel_str!r})"
                for fname, line, token, mel_str, kind in unresolved
            ]
            self.fail(
                f"Found {len(unresolved)} mel.eval first tokens unknown to Maya "
                "(not in allow-list):\n" + "\n".join(lines)
            )


if __name__ == "__main__":
    unittest.main()
