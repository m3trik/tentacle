#!/usr/bin/python
# coding=utf-8
"""Shared helpers for slot validation tests.

Centralized so each test module doesn't re-derive the slot file list and
AST extraction logic.
"""
from __future__ import annotations

import ast
from pathlib import Path
from typing import Iterator, List, Tuple

ROOT = Path(__file__).resolve().parent.parent.parent
PKG = ROOT / "tentacle"
SLOTS_DIR = PKG / "slots" / "maya"

# Files that aren't concrete slots (base class, package marker)
_SKIP = {"__init__.py", "_slots_maya.py"}


def slot_files() -> List[Path]:
    """Every concrete slot module under tentacle/slots/maya/."""
    return sorted(
        f
        for f in SLOTS_DIR.glob("*.py")
        if f.name not in _SKIP and not f.name.startswith("__")
    )


def maya_available() -> bool:
    """True when maya.cmds is importable in the current interpreter."""
    try:
        import maya.cmds  # noqa: F401

        return True
    except ImportError:
        return False


def qt_widgets_available() -> bool:
    """True iff QWidget construction is supported in the current process.

    QWidget construction silently aborts (exit 127, no Python traceback) in
    mayapy.standalone — even after a QApplication has been promoted by other
    imports — because Maya's batch/standalone Qt is a stub that can't host
    real widgets. A ``try/except`` around actually instantiating one cannot
    catch this: it's a native abort, not a Python exception. ``cmds.about(
    batch=True)`` is the safe, Qt-free discriminator (mirrors
    ``test_overlay_safety.py``'s ``_can_create_widgets``, the other place
    this same crash class is guarded against):

    - Plain Python:      no maya.cmds  -> True (regular Qt context)
    - Interactive Maya:   batch=False  -> True (full GUI Qt)
    - mayapy.standalone:  batch=True   -> False (widgets abort the process)
    """
    if not maya_available():
        return True
    import maya.cmds as cmds

    try:
        return not bool(cmds.about(batch=True))
    except Exception:
        return False


def iter_calls(tree: ast.AST) -> Iterator[ast.Call]:
    """Yield every ast.Call node in a tree."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            yield node


def attr_chain(node: ast.AST) -> List[str]:
    """Return the dotted name parts of an ast.Attribute / ast.Name chain.

    `cmds.foo` -> ["cmds", "foo"]
    `mel.eval` -> ["mel", "eval"]
    `self.x.y` -> ["self", "x", "y"]
    Returns empty list if the chain isn't a pure name/attribute walk.
    """
    parts: List[str] = []
    cur: ast.AST = node
    while isinstance(cur, ast.Attribute):
        parts.append(cur.attr)
        cur = cur.value
    if isinstance(cur, ast.Name):
        parts.append(cur.id)
        parts.reverse()
        return parts
    return []


def find_cmds_calls(source: str) -> List[Tuple[int, str]]:
    """Return list of (line_number, cmds_function_name) for every cmds.X(...)
    call site in `source`.
    """
    tree = ast.parse(source)
    found: List[Tuple[int, str]] = []
    for call in iter_calls(tree):
        chain = attr_chain(call.func)
        if len(chain) >= 2 and chain[0] == "cmds":
            # Only direct cmds.X — ignore cmds.X.Y indirection (no such Maya pattern)
            found.append((call.lineno, chain[1]))
    return found


def find_mel_eval_strings(source: str) -> List[Tuple[int, str]]:
    """Return list of (line_number, mel_string_literal) for every
    mel.eval("…") call where the argument is a string literal.

    f-strings and runtime-built strings are skipped (we can't statically
    resolve them).
    """
    tree = ast.parse(source)
    found: List[Tuple[int, str]] = []
    for call in iter_calls(tree):
        chain = attr_chain(call.func)
        if chain == ["mel", "eval"] and call.args:
            arg = call.args[0]
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                found.append((call.lineno, arg.value))
    return found


def first_mel_token(mel_string: str) -> str:
    """Return the first token of a MEL string — typically the proc name."""
    stripped = mel_string.lstrip().rstrip(";").strip()
    if not stripped:
        return ""
    # First whitespace-delimited token, also splits on `(` for proc-call form.
    head = stripped.split(None, 1)[0]
    head = head.split("(", 1)[0]
    return head.rstrip(";")


def find_mel_eval_fstrings(source: str) -> List[Tuple[int, str]]:
    """Return list of (line_number, static_prefix) for every mel.eval(f"…")
    call where the f-string starts with a static literal portion.

    The static prefix is what appears before the first `{expr}` placeholder,
    so its first whitespace-delimited token is reliably the MEL proc name
    (e.g. ``mel.eval(f'texStraightenUVs "UV" {angle}')`` → ``texStraightenUVs``).

    Skips f-strings that begin with an interpolation (no static prefix to
    validate) and runtime-built strings (Name / BinOp).
    """
    tree = ast.parse(source)
    found: List[Tuple[int, str]] = []
    for call in iter_calls(tree):
        chain = attr_chain(call.func)
        if chain != ["mel", "eval"] or not call.args:
            continue
        arg = call.args[0]
        if not isinstance(arg, ast.JoinedStr) or not arg.values:
            continue
        head = arg.values[0]
        if isinstance(head, ast.Constant) and isinstance(head.value, str):
            prefix = head.value.lstrip()
            if prefix:
                found.append((call.lineno, prefix))
    return found


def find_attr_chain_uses(
    source: str, root_name: str, max_depth: int = 3
) -> List[Tuple[int, List[str]]]:
    """Return every attribute chain rooted at ``root_name`` in the source.

    For ``root_name="mtk"`` and code containing ``mtk.NodeUtils.get_parent(x)``
    this returns ``(line_no, ["mtk", "NodeUtils", "get_parent"])``. Captures
    both call expressions and bare attribute accesses (e.g. decorator
    ``@mtk.undoable`` and constant lookups ``mtk.EnvUtils.SCENE_UNIT_VALUES``).

    Chains longer than ``max_depth`` are truncated to ``max_depth`` parts.
    Duplicates are kept so call sites can be reported individually.
    """
    tree = ast.parse(source)
    found: List[Tuple[int, List[str]]] = []
    seen_top_attr_ids = set()  # Avoid double-recording inner Attributes
    for node in ast.walk(tree):
        if not isinstance(node, ast.Attribute):
            continue
        # Walk to the leaf and skip if a parent Attribute will report this.
        chain = attr_chain(node)
        if not chain or chain[0] != root_name:
            continue
        # Only emit at the *outermost* attribute of a chain. We approximate
        # this by recording each unique (lineno, chain) and letting the
        # caller dedupe, but skip strict subchains of one we'll see later
        # by deferring to the longest-on-the-line.
        key = (node.lineno, tuple(chain))
        if key in seen_top_attr_ids:
            continue
        seen_top_attr_ids.add(key)
        found.append((node.lineno, chain[: max(2, max_depth)]))
    # Suppress proper prefixes of longer chains on the same line.
    by_line: dict[int, List[List[str]]] = {}
    for line, chain in found:
        by_line.setdefault(line, []).append(chain)
    pruned: List[Tuple[int, List[str]]] = []
    for line, chains in by_line.items():
        chains_sorted = sorted(chains, key=len, reverse=True)
        kept: List[List[str]] = []
        for c in chains_sorted:
            if not any(
                len(c) < len(longer) and longer[: len(c)] == c for longer in kept
            ):
                kept.append(c)
        for c in kept:
            pruned.append((line, c))
    pruned.sort(key=lambda x: (x[0], x[1]))
    return pruned


def find_mel_string_constants(source: str) -> List[Tuple[int, str]]:
    """Return MEL-shaped string literals that live inside dict/list values
    at module or class scope.

    Catches the ``_CONVERT_COMMANDS`` pattern: a constant table of MEL
    snippets later passed to ``mel.eval(cmd)`` where ``cmd`` is a runtime
    lookup the AST scanner cannot follow.

    Heuristic: a constant string is treated as MEL when it ends with ``;``
    or its first whitespace-delimited token is a plausible MEL identifier
    AND the literal sits inside an ``ast.Dict`` / ``ast.List`` / ``ast.Tuple``
    that is the value of a module- or class-level assignment whose name is
    UPPER_SNAKE or starts with an underscore (project convention for
    constant tables).
    """
    tree = ast.parse(source)
    found: List[Tuple[int, str]] = []

    def _looks_mel(s: str) -> bool:
        # Require a trailing semicolon: this is the strong signal that
        # distinguishes a MEL statement from incidental string data
        # (dict keys, labels, descriptions). False negatives are fine —
        # the constant-string mel.eval scanner already covers literals
        # at the call site.
        s = s.rstrip()
        if not s.endswith(";"):
            return False
        head = s.lstrip().split(None, 1)[0].split("(", 1)[0].rstrip(";")
        return bool(head) and head[0].isalpha() and head.isidentifier()

    def _walk_value(value: ast.AST):
        # Only inspect VALUES of a Dict (not its keys), and ELEMENTS of
        # List / Tuple / Set. This avoids treating natural-language dict
        # keys ('NURBS to Polygons') as MEL.
        if isinstance(value, ast.Dict):
            children = list(value.values)
        elif isinstance(value, (ast.List, ast.Tuple, ast.Set)):
            children = list(value.elts)
        else:
            children = [value]
        for child in children:
            if isinstance(child, ast.Constant) and isinstance(child.value, str):
                if _looks_mel(child.value):
                    found.append((child.lineno, child.value))
            elif isinstance(child, (ast.Dict, ast.List, ast.Tuple, ast.Set)):
                _walk_value(child)

    def _scan_assign_targets(node: ast.AST):
        # Module-level or ClassDef-level assignments only
        for stmt in node.body:
            targets: List[ast.AST] = []
            value: ast.AST | None = None
            if isinstance(stmt, ast.Assign):
                targets = stmt.targets
                value = stmt.value
            elif isinstance(stmt, ast.AnnAssign) and stmt.value is not None:
                targets = [stmt.target]
                value = stmt.value
            else:
                continue
            if not isinstance(value, (ast.Dict, ast.List, ast.Tuple, ast.Set)):
                continue
            for tgt in targets:
                name = tgt.id if isinstance(tgt, ast.Name) else None
                if not name:
                    continue
                # UPPER_SNAKE or leading underscore (e.g. _CONVERT_COMMANDS)
                stripped = name.lstrip("_")
                if not stripped or not stripped.isupper():
                    continue
                _walk_value(value)

    if isinstance(tree, ast.Module):
        _scan_assign_targets(tree)
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                _scan_assign_targets(node)
    return found
