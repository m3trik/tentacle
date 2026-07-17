# !/usr/bin/python
# coding=utf-8
"""Shared user-feedback formatting for the Mesh Cleanup tool (``edit.tb000``).

Used by BOTH the Maya and Blender ``Edit`` slots so the tool's two feedback channels — a detailed
console breakdown and a minimal HTML popup — read identically across DCCs. The tool's cross-engine
parity extends to its messaging, not just its controls, so the format lives here once rather than
being duplicated (and drifting) in each engine's slot.
"""


def cleanup_popup_html(header, rows):
    """Minimal HTML for the Mesh Cleanup popup (``sb.message_box``) — glanceable, one fact per line.

    Parameters:
        header (str): a short, already-marked-up lead line
            (e.g. ``"<hl>Mesh Cleanup — Repair</hl>"``).
        rows (iterable): ``(count, label)`` pairs. Zero / falsey-count rows are dropped so the popup
            only shows what actually happened; with no surviving rows the body reads "nothing found".

    Returns:
        str: ``header`` followed by one ``<hl>count</hl> label`` line per non-zero row.
    """
    body = "<br>".join(f"<hl>{count}</hl> {label}" for count, label in rows if count)
    return f"{header}<br>{body}" if body else f"{header}<br>nothing found"


def cleanup_console_report(title, lines):
    """Detailed Mesh Cleanup report to stdout (Maya Script Editor / Blender system console).

    Emits a ``# Mesh Cleanup — <title>`` header then one indented ``#   <line>`` per fact. Kept on
    ``print`` (not a logger) so it always surfaces in the DCC console, matching the other edit-slot
    diagnostics (Transfer, Bake Partial History) that already report that way.

    Parameters:
        title (str): the run's headline (mode + optional sub-operation).
        lines (iterable[str]): the detail facts, in display order.
    """
    print(f"# Mesh Cleanup — {title}")
    for line in lines:
        print(f"#   {line}")


def report_cleanup_failure(message_box, scope, mode_label, exc):
    """Report a Mesh Cleanup failure through both channels — a detailed console line and a minimal
    popup. ``message_box`` is the slot's ``sb.message_box`` callable, kept engine-agnostic so the
    Maya and Blender edit slots surface the exact same wording (rather than each copying it and
    drifting).
    """
    cleanup_console_report(f"{mode_label} — FAILED", [f"scope: {scope}", str(exc)])
    message_box(f"<hl>Mesh Cleanup failed</hl><br>{exc}")
