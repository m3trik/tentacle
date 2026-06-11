# !/usr/bin/python
# coding=utf-8
"""One-time migration: promote the legacy ``i``-prefixed navigation QPushButtons
in tentacle's marking-menu .ui files to the ``MenuButton`` custom widget.

For each ``<widget class="QPushButton" name="i###">`` it:
  1. promotes the class to ``MenuButton`` (resolved by name via the uitk widget
     registry; the ``<header>`` is cosmetic — both loaders repair it),
  2. converts the overloaded ``accessibleName`` into the de-overloaded
     ``target`` (clean menu name) + ``filterTags`` (the non-structural tags),
  3. ensures a ``<customwidgets>`` promotion entry for ``MenuButton`` exists.

``accessibleName`` is exclusive to the ``i`` buttons in these files, so the
conversion is safe to apply file-wide. The script is idempotent and EOL- and
indent-preserving. Slot buttons (``b###`` / ``tb###``) are left untouched.

Usage:
    python migrate_nav_buttons.py <file_or_glob> ...        # dry-run (default)
    python migrate_nav_buttons.py --write <file_or_glob> ...
    python migrate_nav_buttons.py --write --all             # whole ui/ tree
"""
import re
import sys
import glob
from pathlib import Path

UI_ROOT = Path(__file__).parent / "tentacle" / "ui"
KNOWN_TAGS = {"submenu", "startmenu"}

PROMOTE_RE = re.compile(r'(<widget class=")QPushButton(" name="i\d+">)')
# Leaf nav-button block (no nested <widget>), scoped *after* promotion so the
# accessibleName conversion can only touch a promoted button — never a
# container or the UI's own QMainWindow (which may carry its own accessibleName).
BUTTON_BLOCK_RE = re.compile(r'<widget class="MenuButton" name="i\d+">.*?</widget>', re.DOTALL)
ACCESSIBLE_RE = re.compile(
    r'(?P<indent>[ \t]*)<property name="accessibleName">[ \t]*\r?\n'
    r'[ \t]*<string>(?P<val>[^<]*)</string>[ \t]*\r?\n'
    r'[ \t]*</property>'
)


def _split_target(accessible: str):
    """Return (clean_target, filter_tags) from a legacy accessibleName spec."""
    parts = accessible.split("#")
    base, tags = parts[0], parts[1:]
    known = [t for t in tags if t in KNOWN_TAGS]
    unknown = [t for t in tags if t not in KNOWN_TAGS]
    return "#".join([base] + known), " ".join(unknown)


def _convert_accessible(text: str, eol: str):
    converted = [0]
    tagged = [0]

    def prop_repl(m):
        converted[0] += 1
        indent = m.group("indent")
        target, tags = _split_target(m.group("val"))
        out = [
            f'{indent}<property name="target">',
            f'{indent} <string>{target}</string>',
            f'{indent}</property>',
        ]
        if tags:
            tagged[0] += 1
            out += [
                f'{indent}<property name="filterTags">',
                f'{indent} <string>{tags}</string>',
                f'{indent}</property>',
            ]
        return eol.join(out)

    # Convert only within promoted button blocks — never elsewhere in the file.
    text = BUTTON_BLOCK_RE.sub(lambda bm: ACCESSIBLE_RE.sub(prop_repl, bm.group(0)), text)
    return text, converted[0], tagged[0]


def _ensure_customwidget(text: str, eol: str) -> str:
    if "<class>MenuButton</class>" in text:
        return text  # idempotent

    entry = eol.join(
        [
            "  <customwidget>",
            "   <class>MenuButton</class>",
            "   <extends>QPushButton</extends>",
            "   <header>widgets.menubutton.h</header>",
            "  </customwidget>",
        ]
    )

    if "<customwidgets>" in text:  # add to the existing block
        return text.replace("<customwidgets>", "<customwidgets>" + eol + entry, 1)

    block = eol.join([" <customwidgets>", entry, " </customwidgets>"]) + eol
    for anchor in (" <resources", " <connections", "</ui>"):
        idx = text.find(anchor)
        if idx != -1:
            return text[:idx] + block + text[idx:]
    return text


def migrate(path: Path, write: bool) -> dict:
    # newline="" preserves the file's original EOLs (no universal-newline
    # translation), so the detected eol is faithful and nothing is reflowed.
    raw = path.read_text(encoding="utf-8", newline="")
    eol = "\r\n" if "\r\n" in raw else "\n"

    promoted = len(PROMOTE_RE.findall(raw))
    if not promoted:
        return {"promoted": 0, "converted": 0, "tagged": 0, "changed": False}

    text = PROMOTE_RE.sub(r"\1MenuButton\2", raw)
    text, converted, tagged = _convert_accessible(text, eol)
    text = _ensure_customwidget(text, eol)

    changed = text != raw
    if write and changed:
        path.write_text(text, encoding="utf-8", newline="")
    return {"promoted": promoted, "converted": converted, "tagged": tagged, "changed": changed}


def main(argv):
    write = "--write" in argv
    args = [a for a in argv if not a.startswith("--")]
    if "--all" in argv:
        files = list(UI_ROOT.glob("*.ui")) + list(UI_ROOT.glob("maya_menus/*.ui"))
    else:
        files = [Path(p) for a in args for p in glob.glob(a)]

    total = {"files": 0, "promoted": 0, "converted": 0, "tagged": 0}
    for f in files:
        r = migrate(f, write)
        if r["promoted"]:
            total["files"] += 1
            total["promoted"] += r["promoted"]
            total["converted"] += r["converted"]
            total["tagged"] += r["tagged"]
            flag = "WROTE" if (write and r["changed"]) else "would change"
            print(
                f"  [{flag}] {f.name}: {r['promoted']} promoted, "
                f"{r['converted']} targets ({r['tagged']} w/ filterTags)"
            )
            if r["promoted"] != r["converted"]:
                print(f"    WARNING: {f.name} promoted {r['promoted']} but converted "
                      f"{r['converted']} accessibleName props (expected equal)")

    mode = "WROTE" if write else "DRY-RUN (use --write to apply)"
    print(
        f"\n{mode}: {total['promoted']} nav buttons across {total['files']} files "
        f"({total['converted']} targets, {total['tagged']} w/ filterTags)"
    )


if __name__ == "__main__":
    main(sys.argv[1:])
