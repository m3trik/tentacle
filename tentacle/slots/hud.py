# !/usr/bin/python
# coding=utf-8
"""HUD: one Slots class for both hosts.

The heads-up display composed afresh on every show: opted-in warnings first
(their icons at once, their detail lines with the rest), then what is selected
-- or, with nothing selected, the scene's status -- and the last command. The
facts come from the host toolkit as plain values
(``self.tk.EnvUtils.scene_status``, ``self.tk.NodeUtils.selection_summary``);
the wording and colours are the panel's.
"""

import pythontk as ptk

from tentacle import Slots


class HudSlots(Slots):
    """Scene and selection information, shown while the marking-menu key is held."""

    #: The warnings a user can opt into (Preferences). ``key`` is the gating
    #: checkbox's objectName in ``preferences.ui``; ``check`` and ``describe``
    #: read the :meth:`EnvUtils.scene_status` dict. Adding a warning is one entry.
    WARNING_DEFS = (
        {
            "key": "chk_warn_framerate",
            "icon": "⚠",
            "color": "Orange",
            "label": "FPS",
            "check": lambda status: status["default_fps"],
            "describe": lambda status: (
                'Frame Rate: <font style="color: Orange;">'
                f"{HudSlots._frame_rate(status)}</font> "
                "matches the default for new scenes &mdash; verify this is intentional."
            ),
        },
        {
            "key": "chk_warn_autosave_off",
            "icon": "⚠",
            "color": "Red",
            "label": "Autosave",
            "check": lambda status: not status["autosave"],
            "describe": lambda status: (
                'Autosave: <font style="color: Red;">DISABLED</font> &mdash; enable '
                "it in Preferences to avoid losing work after a crash."
            ),
        },
        {
            "key": "chk_warn_autosave_open",
            "icon": "⚠",
            "color": "Red",
            "label": "Autosave Open",
            "check": lambda status: status["autosave_scene"],
            "describe": lambda status: (
                'Open file is an <font style="color: Red;">AUTOSAVE</font> &mdash; '
                "save to your main scene before continuing or your work will be "
                "lost on the next autosave cycle."
            ),
        },
    )
    #: Preferences checkbox: no warnings while the scene was never saved (setup noise).
    SKIP_ON_UNSAVED_KEY = "chk_warn_skip_unsaved"
    #: Max characters of a slot summary shown on the "Prev Command" line.
    PREV_COMMAND_MAX_CHARS = 120
    #: Selected objects named one per line up to this many; more shows the count only.
    LIST_LIMIT = 10

    _hud_request_token: int = 0

    def __init__(self, switchboard):
        super().__init__(switchboard)
        self.ui = self.sb.loaded_ui.hud_startmenu
        self.ui.hudTextEdit.shown.connect(self.request_hud_build)
        self._active_warnings: list = []
        self._versions = ptk.PackageManager()
        self._start_version_check()

    def _start_version_check(self) -> None:
        """Ask PyPI, in the background, whether a newer tentacle exists. Run
        against the interpreter that can drive pip for this host (mayapy beside
        maya.exe, Blender's bundled python); none, no check -- the host binary
        itself would hang on it."""
        python = self.sb.OptionalPackageManager.pip_python()
        if python:
            self._versions.start_version_check(
                package_name="tentacletk", python_path=python
            )

    def hudTextEdit_init(self, widget) -> None:
        """The HUD is a display composed afresh on every show -- never persisted.

        Registration defaults every widget to ``restore_state=True``; left on,
        the hide-time ``clear()`` and each line the delayed build appends wrote
        the whole HUD to the settings store and flushed it on every gesture,
        and the last session's text was restored into it at load.
        """
        widget.restore_state = False

    # --- build ------------------------------------------------------------

    def request_hud_build(self) -> None:
        """Start a new HUD build; only the latest request's token builds."""
        self._hud_request_token += 1
        my_token = self._hud_request_token

        # Lightweight pre-build phase: evaluate the opted-in warnings now and
        # show their icons at once, so the user gets feedback even if they
        # dismiss the HUD before the delayed full build runs.
        self._active_warnings = self.evaluate_warnings()
        self.insert_warning_icons(self.ui.hudTextEdit, self._active_warnings)

        self.sb.QtCore.QTimer.singleShot(500, lambda: self._delayed_hud_build(my_token))

    def _delayed_hud_build(self, token: int) -> None:
        if token != self._hud_request_token:
            return  # an outdated request
        if not (self.ui.isVisible() and self.ui.hudTextEdit.isVisible()):
            return
        self.construct_hud()

    def construct_hud(self) -> None:
        hud = self.ui.hudTextEdit
        self.insert_warning_details(hud, self._active_warnings)

        summary = self.tk.NodeUtils.selection_summary(limit=self.LIST_LIMIT)
        if not summary:
            self.insert_scene_status(hud, self.tk.EnvUtils.scene_status())
        elif summary["mode"] == "component":
            self.insert_component_info(hud, summary)
        else:
            self.insert_selection_info(hud, summary)

        self.insert_prev_command(hud, self.sb.prev_slot)

    # --- lines ------------------------------------------------------------

    @staticmethod
    def _frame_rate(status) -> str:
        """``24 fps``, with Maya's time-unit name when the host has one (``24 fps FILM``)."""
        text = f"{round(status['fps'], 3):g} fps"
        if status.get("time_unit"):
            text += f" {str(status['time_unit']).upper()}"
        return text

    def insert_scene_status(self, hud, status) -> None:
        """The scene's state: a newer release, symmetry, the transform
        constraint, the workspace, the units and the frame rate."""
        if self._versions.new_version_available:
            hud.insertText(
                "New release available: "
                f'<font style="color: Cyan;">{self._versions.latest_ver}</font>'
            )
        if status.get("symmetry"):
            hud.insertText(
                f'Symmetry Axis: <font style="color: Yellow;">{status["symmetry"]}</font>'
            )
        if status.get("xform_constraint"):
            hud.insertText(
                "Xform Constraint: "
                f'<font style="color: Cyan;">{status["xform_constraint"]}</font>'
            )
        if status.get("workspace"):
            hud.insertText(
                f'Workspace: <font style="color: Yellow;">{status["workspace"]}</font>'
            )
        hud.insertText(f'Units: <font style="color: Yellow;">{status["units"]}</font>')
        hud.insertText(
            f'Frame Rate: <font style="color: Yellow;">{self._frame_rate(status)}</font>'
        )

    def insert_selection_info(self, hud, summary) -> None:
        """The selected objects: how many, each name and type (up to
        :attr:`LIST_LIMIT`), locked normals and instances, and the poly counts."""
        names = "".join(
            f'<font style="color: Yellow;">{name}'
            f'<font style="color: LightGray;">:{kind}<br/>'
            for name, kind in summary["objects"]
        )
        hud.insertText(
            f'Selected: <font style="color: Yellow;">{summary["count"]}<br/>{names}'
        )
        if summary.get("normals_locked"):
            hud.insertText('Normals: <font style="color: Red;">LOCKED</font>')
        if summary.get("instances", 0) > 1:
            hud.insertText(
                f'Instances: <font style="color: Yellow;">{summary["instances"]}</font>'
            )
        for label, key in (("Faces", "faces"), ("Tris", "tris"), ("UVs", "uvs")):
            if summary.get(key) is not None:
                hud.insertText(
                    f'{label}: <font style="color: Yellow;">{summary[key]:,d}'
                )

    def insert_component_info(self, hud, summary) -> None:
        """Selected / total components of the type being edited."""
        if not summary.get("component"):
            return
        hud.insertText(
            f'Selected {summary["component"]}: <font style="color: Yellow;">'
            f'{summary["selected"]} <font style="color: LightGray;">/{summary["total"]}'
        )

    # --- warnings ---------------------------------------------------------

    def _warn_is_enabled(self, key: str) -> bool:
        """True when the user opted into the warning (Preferences).

        Loads the preferences UI on first call, so its checkbox state is
        restored even before the user opens it.
        """
        try:
            prefs = self.sb.loaded_ui.preferences
        except AttributeError:
            return False
        widget = getattr(prefs, key, None)
        if widget is None:
            return False
        try:
            return bool(widget.isChecked())
        except AttributeError:
            return False

    def evaluate_warnings(self) -> list:
        """The :attr:`WARNING_DEFS` that are opted into and fire now, each with
        its ``detail`` line. None while the scene was never saved, when the
        user opted to skip those."""
        enabled = [s for s in self.WARNING_DEFS if self._warn_is_enabled(s["key"])]
        if not enabled:
            return []
        try:
            status = self.tk.EnvUtils.scene_status()
        except Exception as error:  # a status readout must never break the HUD
            self.sb.logger.warning(f"[hud] scene status failed: {error}")
            return []
        if self._warn_is_enabled(self.SKIP_ON_UNSAVED_KEY) and not status["saved"]:
            return []
        active = []
        for spec in enabled:
            try:
                if spec["check"](status):
                    active.append(dict(spec, detail=spec["describe"](status)))
            except Exception as error:  # one bad check, not the others
                self.sb.logger.warning(f"[hud] check {spec['key']} failed: {error}")
        return active

    def insert_warning_icons(self, hud, warnings) -> None:
        """One row of coloured badges, one per active warning."""
        if not warnings:
            return
        badges = "&nbsp;&nbsp;".join(
            f'<font style="color: {w["color"]};">{w["icon"]} {w["label"]}</font>'
            for w in warnings
        )
        hud.insertText(f'<span style="font-size: 150%;">{badges}</span>')

    def insert_warning_details(self, hud, warnings) -> None:
        """One detail line per active warning."""
        for w in warnings:
            if w.get("detail"):
                hud.insertText(w["detail"])

    def insert_prev_command(self, hud, method) -> None:
        """The last-used command as one length-capped line.

        Slot docstrings range from a one-line summary to a full ``Parameters:``
        block, so only the leading summary is shown, truncated at
        :attr:`PREV_COMMAND_MAX_CHARS`: an undocumented or verbose slot must
        not push the rest of the HUD off-screen.

        Parameters:
            hud (obj): The uitk TextEdit the HUD is composed into.
            method (obj): The previously run slot (``sb.prev_slot``), or None.
        """
        if not method:
            return
        doc = (getattr(method, "__doc__", None) or "").strip()
        summary = next((ln.strip() for ln in doc.splitlines() if ln.strip()), "")
        if not summary:  # an undocumented slot: its name
            summary = getattr(method, "__name__", "") or str(method)
        summary = ptk.StrUtils.truncate(summary, self.PREV_COMMAND_MAX_CHARS, "end")
        hud.insertText(f'Prev Command: <font style="color: Yellow;">{summary}</font>')
