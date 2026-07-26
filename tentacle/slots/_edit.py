# !/usr/bin/python
# coding=utf-8
"""Shared, DCC-agnostic behavior for the ``edit`` panel.

The per-panel home for logic the Maya and Blender ``Edit`` forks share (mixed in ahead of
their ``SlotsMaya`` / ``SlotsBlender`` base). Grow this class rather than adding a new module
per feature — see the convention in ``tentacle/CLAUDE.md``.

Currently: the two user-feedback channels for the Mesh Cleanup tool (``edit.tb000``) — a
detailed console breakdown and a minimal HTML popup — so the tool reads identically across
DCCs. The tool's cross-engine parity extends to its messaging, not just its controls, so the
format lives here once rather than being duplicated (and drifting) in each engine's slot.
"""


class EditMixin:
    """DCC-agnostic ``edit`` slot behavior (Mesh Cleanup user-feedback formatting)."""

    @staticmethod
    def cleanup_popup_html(header, rows):
        """Minimal HTML for the Mesh Cleanup popup (``sb.message_box``) — glanceable, one fact per line.

        Parameters:
            header (str): a short, already-marked-up lead line
                (e.g. ``"<hl>Mesh Cleanup — Repair</hl>"``).
            rows (iterable): ``(count, label)`` pairs. Zero / falsey-count rows are dropped so the
                popup only shows what actually happened; with no surviving rows the body reads
                "nothing found".

        Returns:
            str: ``header`` followed by one ``<hl>count</hl> label`` line per non-zero row.
        """
        body = "<br>".join(f"<hl>{count}</hl> {label}" for count, label in rows if count)
        return f"{header}<br>{body}" if body else f"{header}<br>nothing found"

    @staticmethod
    def cleanup_console_report(title, lines):
        """Detailed Mesh Cleanup report to stdout (Maya Script Editor / Blender system console).

        Emits a ``# Mesh Cleanup — <title>`` header then one indented ``#   <line>`` per fact. Kept
        on ``print`` (not a logger) so it always surfaces in the DCC console, matching the other
        edit-slot diagnostics (Transfer, Bake Partial History) that already report that way.

        Parameters:
            title (str): the run's headline (mode + optional sub-operation).
            lines (iterable[str]): the detail facts, in display order.
        """
        print(f"# Mesh Cleanup — {title}")
        for line in lines:
            print(f"#   {line}")

    def report_cleanup_failure(self, scope, mode_label, exc):
        """Report a Mesh Cleanup failure through both channels — a detailed console line and a
        minimal popup — via the slot's own ``sb.message_box``, so the Maya and Blender edit slots
        surface the exact same wording (rather than each copying it and drifting).
        """
        self.cleanup_console_report(f"{mode_label} — FAILED", [f"scope: {scope}", str(exc)])
        self.sb.message_box(f"<hl>Mesh Cleanup failed</hl><br>{exc}")
