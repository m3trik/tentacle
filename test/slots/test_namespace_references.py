#!/usr/bin/python
# coding=utf-8
"""Every `mtk.X` and `ptk.X` attribute chain in the slots resolves.

Both packages use a dynamic attribute resolver
(`pythontk.core_utils.module_resolver.bootstrap_package`) — symbols are
declared in each package's `DEFAULT_INCLUDE` map and exposed lazily. A typo
like `mtk.NudeUtils` doesn't fail at import time; it only blows up when the
slot method is invoked, which is exactly the "real-world use" gap the
in-Maya structural suite is meant to plug.

We AST-walk every slot file, collect each chain rooted at `mtk` / `ptk`,
and assert that:

* the top-level attribute resolves on the package, and
* if the chain has depth ≥ 2, the second attribute resolves on the parent.

Bare imports (`import mayatk as mtk`) don't need to be present in every
file — the test is per-chain, so files that don't reference the alias
simply contribute nothing to the walk.

Skipped automatically when run outside a Maya runtime since `mayatk`
imports `maya.cmds` at the top level.
"""
import importlib
import unittest
from typing import List, Tuple

from _helpers import find_attr_chain_uses, slot_files
from _host import MAYA_AVAILABLE

# Alias → importable module name. The resolver lives on the package
# itself, so we just import and `getattr` against it.
_NAMESPACES = (
    ("mtk", "mayatk"),
    ("ptk", "pythontk"),
)


@unittest.skipUnless(MAYA_AVAILABLE, "Requires maya runtime (mayatk imports maya.cmds)")
class TestNamespaceReferences(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._packages: dict = {}
        for alias, modname in _NAMESPACES:
            try:
                cls._packages[alias] = importlib.import_module(modname)
            except ImportError as exc:
                cls._packages[alias] = exc

    def _resolve(self, alias: str, chain: List[str]) -> Tuple[bool, str]:
        """Return (ok, reason). reason is non-empty only when ok is False."""
        pkg = self._packages.get(alias)
        if isinstance(pkg, ImportError) or pkg is None:
            return False, f"{alias!r} package not importable: {pkg}"
        # chain[0] is the alias itself (e.g. "mtk")
        cur = pkg
        for idx, attr in enumerate(chain[1:], start=1):
            if not hasattr(cur, attr):
                missing = ".".join(chain[: idx + 1])
                return False, f"{missing} not on {alias} ({type(cur).__name__})"
            cur = getattr(cur, attr)
        return True, ""

    def test_every_namespace_chain_resolves(self):
        unresolved: List[Tuple[str, int, str, str]] = []
        for f in slot_files():
            try:
                source = f.read_text(encoding="utf-8")
            except UnicodeDecodeError as e:
                self.fail(f"{f.name}: encoding error: {e}")

            for alias, _ in _NAMESPACES:
                for line_no, chain in find_attr_chain_uses(source, alias):
                    ok, reason = self._resolve(alias, chain)
                    if not ok:
                        unresolved.append(
                            (f.name, line_no, ".".join(chain), reason)
                        )

        if unresolved:
            lines = [
                f"  {fname}:{line}  {chain}  <- {reason}"
                for fname, line, chain, reason in unresolved
            ]
            self.fail(
                f"Found {len(unresolved)} namespace references that do not "
                "resolve:\n" + "\n".join(lines)
            )


if __name__ == "__main__":
    unittest.main()
