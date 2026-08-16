#!/usr/bin/python
# coding=utf-8
"""Every f-string mel.eval(f"…") prefix's first token resolves to a known MEL identifier.

Sibling of `test_mel_references.py`, but covers `mel.eval(f"…")` calls that
the constant-string scanner deliberately skips. f-strings are common in
the slots — `mel.eval(f'texStraightenUVs "UV" {angle}')` — and a typo in
the static prefix is the same class of bug as a constant-string typo.

Strategy: take the static portion *before* the first `{expr}` placeholder,
extract its first whitespace-delimited token, and ask Maya `whatIs`.
Reuses the prime-sources / known-lazy infrastructure from the constant-
string test so the two stay in sync.
"""
import unittest

from _helpers import (
    find_mel_eval_fstrings,
    first_mel_token,
    slot_files,
)
from _host import MAYA_AVAILABLE
from test_mel_references import (  # reuse priming + allow-list
    _KNOWN_LAZY,
    _ensure_plugins_loaded,
    _prime_mel_globals,
)


@unittest.skipUnless(
    MAYA_AVAILABLE, "Requires maya.cmds + maya.mel (run via mayapy)"
)
class TestFStringMelReferences(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _ensure_plugins_loaded()
        _prime_mel_globals()

    def test_every_fstring_mel_eval_prefix_resolves(self):
        import maya.mel as mel

        unresolved = []
        skipped_lazy = []
        for f in slot_files():
            source = f.read_text(encoding="utf-8")
            for line_no, prefix in find_mel_eval_fstrings(source):
                token = first_mel_token(prefix)
                if not token:
                    continue
                try:
                    kind = mel.eval(f'whatIs "{token}"')
                except RuntimeError as exc:
                    unresolved.append(
                        (f.name, line_no, token, prefix, f"eval failed: {exc}")
                    )
                    continue
                if kind.lower().startswith("unknown"):
                    if token in _KNOWN_LAZY:
                        skipped_lazy.append((f.name, line_no, token))
                    else:
                        unresolved.append(
                            (f.name, line_no, token, prefix, kind)
                        )

        if skipped_lazy:
            print(
                f"\n[fstring-mel-refs] {len(skipped_lazy)} known-lazy procs "
                "(allow-listed):"
            )
            for fname, line, token in skipped_lazy:
                print(f"  {fname}:{line}  {token}")

        if unresolved:
            lines = [
                f"  {fname}:{line}  {token!r}  -> {kind}\n"
                f"      mel.eval(f{prefix!r}…)"
                for fname, line, token, prefix, kind in unresolved
            ]
            self.fail(
                f"Found {len(unresolved)} mel.eval f-string prefixes unknown "
                "to Maya (not in allow-list):\n" + "\n".join(lines)
            )


if __name__ == "__main__":
    unittest.main()
