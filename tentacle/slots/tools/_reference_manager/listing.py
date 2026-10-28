# !/usr/bin/python
# coding=utf-8
"""The Reference Manager's listing rules: how a scene file reads as a row and
which rows a filter keeps -- pure, host-free.

Private to :mod:`tentacle.slots.tools.reference_manager`; the controller
(:mod:`.controller`) applies them to the table.
"""

import os
from fnmatch import fnmatchcase
from typing import Iterable, List, Sequence

import pythontk as ptk


class SceneListing:
    """Row labels, filter matches and the naming conventions' path rules."""

    #: Max file names listed verbatim in a delete confirmation (the rest fold into
    #: an "...and N more" line).
    DELETE_PROMPT_MAX_NAMES = 10
    #: The delimiters a filter (and a note) splits on.
    DELIMITERS = (",", ";")

    @staticmethod
    def display_name(path: str, hide_extension: bool, hide_suffix: str) -> str:
        """The table label for *path* -- its basename, less the extension and/or a
        TRAILING *hide_suffix*.

        End-anchored on the stem, never a substring pass: the suffix field holds a
        naming token (``_LOC``), and removing it wherever it appears rewrites the
        middle of a name -- ``ITA_LOCKHANDLE.ma`` listed as ``ITAKHANDLE``. The
        extension is split off first so the token is still at the end when the
        column is showing it, and ``endswith`` matches the suffix filter, so a row
        shown for its suffix hides that same one.
        """
        stem, ext = os.path.splitext(os.path.basename(path))
        if hide_suffix and stem.endswith(hide_suffix):
            stem = stem[: -len(hide_suffix)]
        return stem if hide_extension else f"{stem}{ext}"

    @classmethod
    def split_patterns(cls, text: str) -> List[str]:
        """*text* split on every :attr:`DELIMITERS` entry, each part trimmed."""
        parts = [text or ""]
        for delim in cls.DELIMITERS:
            expanded = []
            for part in parts:
                expanded.extend(s.strip() for s in part.split(delim) if s.strip())
            parts = expanded
        return parts

    @staticmethod
    def text_matches_filter(
        text: str, filter_patterns: Sequence[str], ignore_case: bool = True
    ) -> bool:
        """True if *text* (a file name) matches ANY of the already-split glob
        *filter_patterns*."""
        if not text or not filter_patterns:
            return False
        t = text.lower() if ignore_case else text
        for pattern in filter_patterns:
            p = pattern.lower() if ignore_case else pattern
            if fnmatchcase(t, p):
                return True
        return False

    @classmethod
    def matches_notes_filter(
        cls, notes_text: str, filter_text: str, ignore_case: bool = True
    ) -> bool:
        """True if the note *notes_text* matches the filter.

        Notes are often comma or semicolon-delimited ("Layout, Speedrun"), so each
        filter pattern is checked against the whole note as well as each segment.
        """
        if not notes_text or not filter_text:
            return False
        candidates = [notes_text] + cls.split_patterns(notes_text)
        for pattern in cls.split_patterns(filter_text):
            p = pattern.lower() if ignore_case else pattern
            for candidate in candidates:
                c = candidate.lower() if ignore_case else candidate
                if fnmatchcase(c, p):
                    return True
        return False

    @staticmethod
    def scenes_folder(workspace: str) -> str:
        """The ``{scenes}`` placeholder for *workspace*: its ``scene`` file rule when
        that is a relative folder, else the literal ``"scenes"`` -- the folder Save
        writes under, the folder-structure filter matches and both previews show."""
        try:
            rule = (
                ptk.Workspace.load(workspace).rules.get("scene") if workspace else None
            )
        except Exception:  # noqa: BLE001 - an unreadable workspace.mel
            rule = None
        return rule if rule and not os.path.isabs(rule) else "scenes"

    @staticmethod
    def format_name(name: str, case_style: str = "None", suffix: str = "") -> str:
        """*name* in the *case_style* convention (``ptk.StrUtils.set_case``;
        ``"None"`` leaves it), with *suffix* appended -- excluded from the case."""
        if case_style and case_style.startswith("Case: "):
            case_style = case_style[len("Case: ") :]
        if case_style and case_style != "None":
            try:
                name = ptk.StrUtils.set_case(name, case_style)
            except Exception:  # noqa: BLE001 - an unknown style leaves the name
                pass
        return name + suffix if suffix else name

    @staticmethod
    def strip_all_suffixes(base: str, suffix: str) -> str:
        """*base* less EVERY trailing *suffix*: a prefill still ending in one (a
        ``_v01_v01`` an old rename doubled) would save under another name than the
        one both previews show."""
        stripped = ptk.StrUtils.strip_suffix(base, [suffix])
        while stripped != base:
            base, stripped = stripped, ptk.StrUtils.strip_suffix(stripped, [suffix])
        return base

    @staticmethod
    def filter_by_folder_structure(
        files: Iterable[str],
        workspace: str,
        pattern: str,
        suffix: str,
        scenes: str,
    ) -> List[str]:
        """The *files* whose folder ends with *pattern* resolved for each
        (``{scenes}`` / ``{name}`` -- the stem less *suffix* -- / ``{workspace}`` /
        ``{suffix}``); a file may sit deeper than the structure. A file on another
        drive, or a malformed pattern, is left out."""
        workspace_name = os.path.basename(os.path.normpath(workspace))
        kept = []
        for f in files:
            try:
                rel_dir = os.path.relpath(os.path.dirname(f), workspace)
            except ValueError:  # another drive (Windows)
                continue
            base = os.path.splitext(os.path.basename(f))[0]
            name = base[: -len(suffix)] if suffix and base.endswith(suffix) else base
            try:
                expected = ptk.StrUtils.replace_placeholders(
                    pattern,
                    scenes=scenes,
                    name=name,
                    workspace=workspace_name,
                    suffix=suffix,
                )
            except ValueError:  # an unbalanced brace: no file can match it
                continue
            rel_parts = os.path.normcase(os.path.normpath(rel_dir)).split(os.sep)
            exp_parts = os.path.normcase(os.path.normpath(expected)).split(os.sep)
            if (
                len(rel_parts) >= len(exp_parts)
                and rel_parts[-len(exp_parts) :] == exp_parts
            ):
                kept.append(f)
        return kept

    @classmethod
    def delete_prompt(cls, paths: Sequence[str], permanent: Sequence[str] = ()) -> str:
        """Confirmation text for deleting *paths*.

        Names each file in full: the row label can hide the suffix/extension, so a
        count alone gives no way to confirm WHICH file is about to be removed. And
        it says where each goes: the platform's trash (``ptk.FileUtils.trash_name``),
        or, for *permanent* -- the ones no trash would take (a network share, a
        removable drive) -- gone for good, which it says cannot be undone.
        """
        trash = ptk.FileUtils.trash_name()
        gone = {os.path.normcase(os.path.abspath(p)) for p in permanent}
        marks = [os.path.normcase(os.path.abspath(p)) in gone for p in paths]
        names = [os.path.basename(p) for p in paths]
        if len(names) == 1:
            if marks[0]:
                return (
                    f"Delete <hl>{names[0]}</hl> permanently?<br>The {trash} "
                    "will not take it, so this cannot be undone."
                )
            return f"Move <hl>{names[0]}</hl> to the {trash}?"
        mixed = any(marks) and not all(marks)
        shown = list(zip(names, marks))[: cls.DELETE_PROMPT_MAX_NAMES]
        listed = "<br>".join(
            f"&bull; {n}" + (f" (permanently: no {trash})" if mark and mixed else "")
            for n, mark in shown
        )
        if len(names) > len(shown):
            listed += f"<br>&bull; ...and {len(names) - len(shown)} more"
        if all(marks):
            return (
                f"Delete {len(names)} file(s) permanently?<br>{listed}<br>The "
                f"{trash} will not take them, so this cannot be undone."
            )
        if mixed:
            return (
                f"Delete {len(names)} file(s)?<br>{listed}<br>The rest go to the "
                f"{trash}; the marked ones cannot be undone."
            )
        return f"Move {len(names)} file(s) to the {trash}?<br>{listed}"
