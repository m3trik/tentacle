# !/usr/bin/python
# coding=utf-8
"""HDR Manager: light the scene from an HDR environment map, spin it and adjust
its levels.

One Slots class for both hosts over the host toolkit's ``HdrManager``
(``self.tk``): Maya's is an Arnold ``aiSkyDomeLight`` + ``file`` texture
network, Blender's the world shader's Environment Texture. The dropdown lists
the environment maps in the project's texture folder (``sourceimages``) and is
a live mirror of the scene: it shows the map that lights it, or **None**. Each
control drives one of the manager's knobs, live; a knob the host's environment
lacks (``HdrManager.KNOBS``) leaves its control disabled. Picking a map, adding
one and Clear Network are one undo step each (the manager's).
"""

import os
import shutil
from typing import Optional

import pythontk as ptk

from tentacle import Slots


class HdrManagerSlots(Slots, ptk.LoggingMixin):
    # File-dialog filter for Add HDR(s)…
    HDR_FILTER: str = "HDR Images (*.exr *.hdr);;All Files (*.*)"
    # Glob patterns every texture-folder / folder scan lists.
    HDR_PATTERNS = ["*.exr", "*.hdr"]

    # Sentinel userData for the dropdown's explicit "None" entry: selecting it
    # removes the scene's HDR environment. Distinct from "nothing picked yet"
    # (an unset combo, which carries no userData) so the slot can tell an
    # intentional clear from an empty selection.
    NONE_TOKEN: str = "<none>"
    NONE_LABEL: str = "None"

    # Add-HDR mode picker: index -> (label, token). The index is the source of
    # truth (the combo saves it), so reordering the labels can't silently
    # rename the dispatch token.
    _ADD_MODES: tuple = (
        ("Copy to sourceimages", "copy"),
        ("Move to sourceimages", "move"),
        ("Link to original location", "link"),
    )

    # Filesystem op per import mode.
    _IO_OPS = {"copy": shutil.copy2, "move": shutil.move}

    #: Spin box -> the ``HdrManager`` knob it drives. The rotation slider drives
    #: ``rotation``; its option box's two toggles ``preview`` and ``visibility``.
    _SPINBOX_KNOBS = {
        "spn_intensity": "intensity",
        "spn_exposure": "exposure",
        "spn_resolution": "resolution",
        "spn_samples": "samples",
        "spn_diffuse": "diffuse",
        "spn_specular": "specular",
    }

    #: The tooltip of a control whose knob the host's environment lacks.
    _UNAVAILABLE = (
        "Not available here: this application's HDR environment has no such setting."
    )

    #: Right-click "Select ..." items: (label, objectName, tooltip).
    _SELECT_ITEMS = (
        (
            "Select Skydome",
            "ctx_select_skydome",
            "Select the skydome light in the scene.",
        ),
        (
            "Select Transform",
            "ctx_select_transform",
            "Select the skydome's transform parent.",
        ),
        (
            "Select File Node",
            "ctx_select_file_node",
            "Select the file texture node driving the skydome color.",
        ),
    )

    #: What a Select item reports when the scene has no such node.
    _SELECT_ABSENT = {
        "skydome": "No skydome in scene.",
        "transform": "No skydome transform in scene.",
        "file_node": "No file node connected to the skydome.",
    }

    def __init__(self, switchboard):
        super().__init__(switchboard)
        self.logger.setLevel("WARNING")
        self.logger.set_log_prefix("[HDR Manager] ")
        self.ui = self.sb.loaded_ui.hdr_manager
        self.manager = self.tk.HdrManager()

        # Option-box plugins on the rotation slider, built in
        # _setup_rotation_slider (deferred): an inline degrees value plus two
        # view toggles. Held so _sync_ui_to_scene can push scene state into them.
        self._rotation_value = None
        self._viewport_toggle = None
        self._render_toggle = None

        # Keep the dropdown a live mirror of the scene's HDR environment. Scene
        # open / new / import swap the whole environment AND the texture folder
        # the list is drawn from -> re-scan disk + re-sync. Undo / Redo only flip
        # which network is live -> re-sync, without a disk re-scan on every undo.
        # Each subscribe is guarded: an event a host lacks (Blender has no
        # "SceneImported") must not block the panel open.
        jobs = self.tk.ScriptJobManager.instance()
        for events, handler in (
            (
                ("SceneOpened", "NewSceneOpened", "SceneImported"),
                self._on_scene_changed,
            ),
            (("Undo", "Redo"), self._sync_ui_to_scene),
        ):
            for event in events:
                try:
                    jobs.subscribe(event, handler, owner=self)
                except Exception as e:
                    self.logger.debug("event %r unavailable (%s)", event, e)
        jobs.connect_cleanup(self.ui, owner=self)

        # Deferred to the next event-loop tick: the switchboard builds this
        # slots instance mid-load, and the child widgets (footer, spin boxes,
        # slider) aren't wired onto self.ui until register_children runs.
        self.sb.QtCore.QTimer.singleShot(0, self._initialize_ui)

    def _initialize_ui(self) -> None:
        """Gate the controls on the host's knobs, populate the dropdown and
        sync the controls from the scene (deferred from ``__init__``)."""
        knobs = self.manager.KNOBS
        absent = [
            getattr(self.ui, name)
            for name, knob in self._SPINBOX_KNOBS.items()
            if knob not in knobs
        ]
        for widget in absent:
            widget.setEnabled(False)
            widget.setToolTip(self._UNAVAILABLE)
        # Per-field reset buttons (click: reset to default; Alt/Ctrl+click:
        # bypass) on every live spin box -- a disabled one's would be dead
        # chrome. Before the reads below: wrapping reparents the widgets.
        self.sb.add_reset_buttons(self.ui, skip=tuple(absent))
        self._setup_rotation_slider()

        self._refresh_combo()
        self._sync_ui_to_scene()

        # Maya only: the skydome is Arnold's light, and mtoa loads on the first
        # edit rather than with the panel (it boots the whole renderer).
        # Blender's world shader needs no plugin, so its manager has no check.
        arnold_loaded = getattr(self.manager, "arnold_loaded", None)
        if arnold_loaded is not None and not arnold_loaded():
            self.ui.footer.setText("Arnold (mtoa) not loaded — loads on first use.")

    def _setup_rotation_slider(self) -> None:
        """Wire the rotation slider's option box: the exact angle plus two view
        toggles -- **viewport visibility** (``preview``: the HDR as a viewport
        backdrop) and **render visibility** (``visibility``: the HDR as the
        render's backdrop).

        Deferred (not a ``slider000_init`` hook) because wrapping a widget in its
        option box reparents it. Both toggles are non-persistent
        (``settings_key=False``): they mirror scene state, never a stored pref.
        Built directly rather than via ``add_toggle`` so both instances are
        held (``find_option`` returns only the first of a type). A host without
        a ``preview`` knob keeps the toggle, disabled.
        """
        ob = self.ui.slider000.option_box
        # ValueOption sorts ahead of the buttons, so the exact-angle field sits
        # flush against the slider; the viewport toggle, added first, is left.
        ob.add_value(width=46, suffix="°")
        preview = "preview" in self.manager.KNOBS
        self._viewport_toggle = self.sb.ToggleOption(
            wrapped_widget=self.ui.slider000,
            icon="screen",
            tooltip_on=(
                "HDR shown as a backdrop in the viewport. Click to hide."
                if preview
                else self._UNAVAILABLE
            ),
            tooltip_off=(
                "HDR hidden in the viewport. Click to show."
                if preview
                else self._UNAVAILABLE
            ),
            initial=False,
            settings_key=False,
        )
        self._viewport_toggle.toggled.connect(self._on_viewport_visible)
        self._render_toggle = self.sb.ToggleOption(
            wrapped_widget=self.ui.slider000,
            icon="camera",
            tooltip_on="HDR visible as the render's backdrop. Click to hide.",
            tooltip_off="HDR hidden from the render (lighting only). Click to show.",
            initial=False,
            settings_key=False,
        )
        self._render_toggle.toggled.connect(self._on_render_visible)
        ob.add_option(self._viewport_toggle)
        ob.add_option(self._render_toggle)
        _ = ob.container  # force the lazy wrap so the field + toggles show
        if not preview:
            self._viewport_toggle.widget.setEnabled(False)
        self._rotation_value = ob.find_option(self.sb.ValueOption)

    # ------------------------------------------------------------------
    # Feedback
    # ------------------------------------------------------------------

    def _notify(
        self,
        message: str,
        *,
        level: str = "info",
        detail: Optional[str] = None,
        dialog: bool = False,
        dialog_text: Optional[str] = None,
    ) -> None:
        """Surface feedback in the footer (short, coloured by *level*), the
        console (*detail*, else *message*) and -- with *dialog* -- a modal
        message box showing *dialog_text* (else *message*), never the long
        console detail."""
        self.ui.footer.setText(message, level=level)
        {
            "error": self.logger.error,
            "warning": self.logger.warning,
        }.get(level, self.logger.info)(detail or message)
        if dialog:
            prefix = {
                "error": "Error:",
                "warning": "Warning:",
                "success": "Result:",
            }.get(level, "Note:")
            # The message box colours these prefixes; "Ok" makes it modal.
            self.sb.message_box(f"{prefix} {dialog_text or message}", "Ok")

    # ------------------------------------------------------------------
    # Header
    # ------------------------------------------------------------------

    def header_init(self, widget) -> None:
        """Configure the header menu, the refresh button and the help text."""
        widget.config_buttons("refresh", "menu", "collapse", "hide")
        widget.refresh_requested.connect(self._refresh_and_sync_combo)
        widget.menu.add("Separator", setTitle="Sourceimages")
        widget.menu.add(
            "QPushButton",
            setText="Open Sourceimages Folder",
            setObjectName="open_sourceimages",
            setToolTip="Open the project's texture folder (sourceimages) in the file manager.",
        )
        widget.menu.add("Separator", setTitle="Network")
        widget.menu.add(
            "QPushButton",
            setText="Clear Network",
            setObjectName="clear_network",
            setToolTip="Remove the HDR environment from the scene.",
        )
        widget.set_help_text(
            self.sb.tooltip.fmt(
                title="HDR Manager",
                body="Light the scene with an HDR environment map (Maya: an "
                "Arnold aiSkyDomeLight + file texture network; Blender: the "
                "world shader's Environment Texture).",
                steps=[
                    "Pick an HDR / EXR from the dropdown to light the scene (it "
                    "lists the environment maps in the project's "
                    "<i>sourceimages</i> folder); pick <b>None</b> to remove "
                    "the HDR environment.",
                    "Open the dropdown's option menu (▸) → <b>Add HDR(s)…</b> to "
                    "add images: one dialog picks loose files and/or a whole "
                    "folder; the import mode is set just below it.",
                    "Adjust <b>Intensity</b> (linear), <b>Exposure</b> (stops) "
                    "and <b>Resolution</b> (the HDR's importance-sampling map).",
                    "Drag the rotation slider to spin the environment around "
                    "the up axis. Its option box (▸) holds the exact angle plus "
                    "two view toggles: <b>viewport visibility</b> (the HDR as a "
                    "viewport backdrop; Maya) and <b>render visibility</b> (the "
                    "HDR as the render's backdrop; it lights the scene either "
                    "way).",
                ],
                sections=[
                    (
                        "Advanced Options (collapsible)",
                        [
                            "<b>Samples</b>: light samples; raise to clean up "
                            "soft-IBL noise (Maya; Cycles samples the world "
                            "with the scene).",
                            "<b>Diffuse</b> / <b>Specular</b>: the "
                            "environment's contribution to diffuse vs specular "
                            "light (Blender: on above 0, off at 0; Cycles only).",
                        ],
                    ),
                    (
                        "Add HDR(s)… (option-box menu ▸)",
                        [
                            "One dialog picks <b>loose files and/or a whole "
                            "folder</b>; folders are expanded to the environment "
                            "maps they hold (per the <b>List</b> toggles). "
                            "Incomplete/corrupt files are skipped.",
                            "Files already inside <i>sourceimages</i> (any "
                            "subfolder) are used in place, never duplicated.",
                            "<b>Copy</b>: duplicate an <i>external</i> file into "
                            "sourceimages (default; keeps the project portable).",
                            "<b>Move</b>: relocate an external file into "
                            "sourceimages.",
                            "<b>Link</b>: wire each in at its original path.",
                        ],
                    ),
                    (
                        "List (option-box menu ▸)",
                        [
                            "<b>Latlong Only (2:1)</b>: list only images shaped "
                            "like a latlong environment, the projection the "
                            "environment maps; hides square lightmaps and "
                            "textures.",
                            "<b>Hide Lightmaps</b>: hide files named with the "
                            "Lightmap affix of the shared naming convention "
                            "(<i>Naming ▸ Suffix By Type</i>).",
                        ],
                    ),
                    (
                        "Dropdown right-click",
                        [
                            "Select the skydome / its transform / its file "
                            "node (Maya).",
                            "Reveal the texture in the file manager.",
                        ],
                    ),
                    (
                        "Header menu",
                        [
                            "<b>Open Sourceimages Folder</b>: open it in the "
                            "file manager.",
                            "<b>Clear Network</b>: remove the HDR environment "
                            "(Maya: the skydome and its file / place2d nodes; "
                            "Blender: the world's environment nodes).",
                        ],
                    ),
                ],
                notes=[
                    "Maya: applying an HDR makes <b>Arnold</b> the active "
                    "renderer (an aiSkyDomeLight renders in no other); the "
                    "footer says when mtoa is not loaded yet.",
                    "Blender: the world renders in EEVEE and Cycles alike; "
                    "Cycles sizes the importance map from the image until "
                    "<b>Resolution</b> sets one.",
                ],
            )
        )

    def cmb000_init(self, widget) -> None:
        """Wire the HDR dropdown: option-box plugins, context menu, auto-refresh."""
        # Re-scan disk AND re-point at the live HDR every time the dropdown
        # opens, so new HDRs appear and the active map is highlighted.
        widget.before_popup_shown.connect(self._refresh_and_sync_combo)

        # The dropdown mirrors the LIVE scene, never a persisted value: a
        # restored index would fire cmb000 and load a stale HDR into a fresh
        # scene. ComboBox.add() resets restore_state on every populate, so
        # _refresh_combo re-asserts it; this covers the pre-refresh window.
        widget.restore_state = False

        # Right-click context menu (a separate Menu from the option box's).
        # Selecting the environment's nodes is Maya's: a Blender world is not a
        # selectable scene object, so its manager has no ``select`` and the
        # items stay, disabled.
        selectable = getattr(self.manager, "select", None) is not None
        widget.configure_menu(trigger_button="right")
        for text, name, tip in self._SELECT_ITEMS:
            item = widget.menu.add(
                "QPushButton",
                setText=text,
                setObjectName=name,
                setToolTip=tip
                if selectable
                else "Not available here: this application's HDR environment "
                "is not a selectable scene object.",
            )
            if not selectable:
                item.setEnabled(False)
        widget.menu.add("Separator")
        widget.menu.add(
            "QPushButton",
            setText="Reveal in Explorer",
            setObjectName="ctx_reveal_in_explorer",
            setToolTip="Open the HDR file's containing folder in the file manager.",
        )

        # Option-box menu (▸): the panel's add affordance. "Add HDR(s)…" sits
        # above the import-mode combo. (A non-slot objectName + an explicit
        # connect: no double-fire from auto-wiring by objectName.)
        widget.option_box.menu.setTitle("Add HDR")
        add_btn = widget.option_box.menu.add(
            "QPushButton",
            setText="Add HDR(s)…",
            setObjectName="add_hdr_btn",
            setToolTip=(
                "Add HDR/EXR images: one dialog picks loose files and/or a "
                "whole folder.\nEach is imported using the mode below. "
                "Incomplete/corrupt files are skipped."
            ),
        )
        add_btn.clicked.connect(self.add_hdr)
        widget.option_box.menu.add("Separator")
        widget.option_box.menu.add(
            "QComboBox",
            setObjectName="cmb_add_mode",
            setToolTip=(
                "What 'Add HDR(s)…' does with the picked file(s):\n"
                "  • Copy: duplicate into sourceimages (default, the project "
                "stays portable).\n"
                "  • Move: relocate into sourceimages (originals are removed).\n"
                "  • Link: leave in place and wire the original path directly\n"
                "    (won't appear in the dropdown afterward)."
            ),
            addItems=[label for label, _token in self._ADD_MODES],
        )
        # What the dropdown (and a folder add) takes from disk; both re-list on
        # toggle. See ptk.ImgUtils.is_environment_map.
        widget.option_box.menu.add("Separator", setTitle="List")
        for name, text, tip in (
            (
                "chk_latlong_only",
                "Latlong Only (2:1)",
                "List only images shaped like a latlong environment (2:1), the "
                "projection the environment maps. Hides lightmaps and other "
                "square textures by their size.\nOnline-only cloud files are "
                "listed unread (reading one would download it).",
            ),
            (
                "chk_hide_lightmaps",
                "Hide Lightmaps",
                "Hide files named with the Lightmap affix of the shared naming "
                "convention (Naming ▸ Suffix By Type ▸ Lightmap; '_Lightmap' by "
                "default), including tiles and light groups such as "
                "'room_Lightmap_3' or 'desk_Lightmap.LIGHT_A'.",
            ),
        ):
            check = widget.option_box.menu.add(
                "QCheckBox",
                setText=text,
                setObjectName=name,
                setChecked=True,
                setToolTip=tip,
            )
            check.toggled.connect(lambda *_: self._refresh_and_sync_combo())

    def _list_filter(self) -> dict:
        """``ptk.ImgUtils.is_environment_map`` keywords from the List toggles;
        both on before the option box exists."""
        try:
            menu = self.ui.cmb000.option_box.menu
            return {
                "latlong_only": menu.chk_latlong_only.isChecked(),
                "skip_lightmaps": menu.chk_hide_lightmaps.isChecked(),
            }
        except AttributeError:
            return {"latlong_only": True, "skip_lightmaps": True}

    def _folder_hdrs(self, directory: str) -> list:
        """The environment maps directly in *directory*, per the List toggles.

        A folder add takes what the dropdown would list: adding sourceimages
        itself in Link mode otherwise wired whichever file came last, often a
        baked lightmap. Loose files the user picks are taken as-is.
        """
        flags = self._list_filter()
        return [
            path
            for path in ptk.get_dir_contents(
                directory, "filepath", inc_files=self.HDR_PATTERNS
            )
            or []
            if ptk.ImgUtils.is_environment_map(path, **flags)
        ]

    def _texture_dir(self) -> str:
        """The project's texture folder (``sourceimages``), or ``""`` without
        a project."""
        return self.tk.EnvUtils.source_images_dir() or ""

    # ------------------------------------------------------------------
    # Scene -> UI sync
    # ------------------------------------------------------------------

    def _on_scene_changed(self) -> None:
        self._refresh_combo()
        self._sync_ui_to_scene()

    def _refresh_combo(self) -> None:
        """Repopulate the dropdown from the texture folder, keeping the pick
        (by data, not index) across rebuilds."""
        combo = self.ui.cmb000
        previous_data = combo.currentData()
        src = self._texture_dir()

        if not src or not os.path.isdir(src):
            # Signals blocked: the rebuild must not fire cmb000.
            combo.blockSignals(True)
            try:
                combo.add([], clear=True)
                combo.restore_state = False  # add() reset it
                self._prepend_none_item()
            finally:
                combo.blockSignals(False)
            # Fires on every dropdown open: colour the footer, but skip
            # _notify so the console isn't spammed.
            self.ui.footer.setText(
                "No sourceimages folder: set a project first.", level="warning"
            )
            return

        # Recursive, so HDRs kept in a subfolder (sourceimages/hdr/) list too;
        # they're in the project already, so the add flow leaves them in place.
        hdr_info = ptk.get_dir_contents(
            src,
            ["filename", "filepath"],
            recursive=True,
            inc_files=self.HDR_PATTERNS,
            group_by_type=True,
        )
        # sourceimages also holds baked lightmaps and other EXR textures; list
        # only what can light the scene.
        flags = self._list_filter()
        listed = [
            (name, path)
            for name, path in zip(hdr_info["filename"], hdr_info["filepath"])
            if ptk.ImgUtils.is_environment_map(path, **flags)
        ]
        names = [name for name, _path in listed]
        paths = [path for _name, path in listed]
        count, hidden = len(paths), len(hdr_info["filepath"]) - len(paths)
        message = f"{count} HDR{'s' if count != 1 else ''} in sourceimages"
        if hidden:
            message += f" ({hidden} other image{'s' if hidden != 1 else ''} hidden)"
        self.ui.footer.setText(message + ".")

        # An unchanged listing skips the destructive repopulate: rebuilding the
        # model right before the popup shows can desync the popup's selection
        # so the first click is dropped.
        if self._listed_paths_match(paths):
            return

        combo.blockSignals(True)
        try:
            # No header: a header paints a fixed label at index -1 and snaps the
            # selection back to it after every pick, hiding the active map and
            # zeroing currentData() so the apply silently no-ops.
            combo.add(zip(names, paths), ascending=False, clear=True)
            combo.restore_state = False  # add() reset it
            self._prepend_none_item()
            if previous_data:
                idx = combo.findData(previous_data)
                if idx >= 0:
                    combo.setCurrentIndex(idx)
        finally:
            combo.blockSignals(False)

    def _listed_paths_match(self, new_paths) -> bool:
        """True if the dropdown already lists exactly *new_paths*
        (order-independent, slash/case-normalized, the None entry skipped)."""
        combo = self.ui.cmb000
        current = set()
        for i in range(combo.count()):
            data = combo.itemData(i)
            if data and data != self.NONE_TOKEN:
                current.add(self._norm_path(data))
        return current == {self._norm_path(p) for p in new_paths}

    def _prepend_none_item(self) -> None:
        """Insert the explicit None entry at the top (callers block signals)."""
        self.ui.cmb000.insertItem(0, self.NONE_LABEL, self.NONE_TOKEN)

    def _select_combo_path(self, path: str) -> bool:
        """Select the entry whose file is *path*, compared slash/case-normalized
        (the combo's raw listing can mix slash styles, a caller's normpath
        not). True on a hit (selected, signals blocked)."""
        target = self._norm_path(path)
        combo = self.ui.cmb000
        for i in range(combo.count()):
            data = combo.itemData(i)
            if data and self._norm_path(data) == target:
                combo.blockSignals(True)
                try:
                    combo.setCurrentIndex(i)
                finally:
                    combo.blockSignals(False)
                return True
        return False

    def _read(self, knob: str):
        """The manager's reading of *knob*; None when the host's environment
        lacks it."""
        return getattr(self.manager, knob) if knob in self.manager.KNOBS else None

    def _write(self, knob: str, value) -> None:
        """Set *knob* on the scene's environment, live; a knob the host's
        environment lacks is ignored."""
        if knob in self.manager.KNOBS:
            setattr(self.manager, knob, value)

    def _sync_ui_to_scene(self) -> None:
        """Pull the scene's environment into the controls.

        Each control shows its knob's reading (with no environment, the
        manager's defaults). A knob the host lacks, or one reading None -- a
        value the host picks itself (Blender: Cycles' automatic importance-map
        size) -- leaves its control as it is.
        """
        widgets = [(self.ui.slider000, "setSliderPosition", "rotation")]
        widgets += [
            (getattr(self.ui, name), "setValue", knob)
            for name, knob in self._SPINBOX_KNOBS.items()
        ]
        for widget, setter, knob in widgets:
            value = self._read(knob)
            if value is None:
                continue
            if knob == "rotation":
                value = int(round(value)) % 360
            widget.blockSignals(True)
            try:
                getattr(widget, setter)(value)
            finally:
                widget.blockSignals(False)

        # The toggles and the degrees field live in the slider's option box,
        # not the .ui. Toggles set silently (no scene write); the field is
        # refreshed since the blocked slider set didn't fire its mirror.
        for toggle, knob in (
            (self._viewport_toggle, "preview"),
            (self._render_toggle, "visibility"),
        ):
            value = self._read(knob)
            if toggle is not None and value is not None:
                toggle.set_on(bool(value), emit=False)
        if self._rotation_value is not None:
            self._rotation_value.refresh()

        self._select_active_in_combo()

    def _select_active_in_combo(self) -> None:
        """Point the dropdown at the scene's active HDR, or None.

        A listed map selects its row; an unlisted one (a Link-mode HDR outside
        sourceimages) is surfaced as a transient row, so the combo shows the
        real map rather than a misleading None; no environment selects the
        None entry. Signals stay blocked, so this never fires cmb000.
        """
        current_path = self.manager.hdr_file_path
        if current_path and self._select_combo_path(current_path):
            return
        combo = self.ui.cmb000
        combo.blockSignals(True)
        try:
            if current_path:
                combo.addItem(os.path.basename(current_path), current_path)
                combo.setCurrentIndex(combo.count() - 1)
            else:
                idx = combo.findData(self.NONE_TOKEN)
                combo.setCurrentIndex(idx if idx >= 0 else -1)
        finally:
            combo.blockSignals(False)

    def _refresh_and_sync_combo(self) -> None:
        """Re-list from disk, then re-point at the active HDR (the dropdown's
        pre-popup signal and the header Refresh). Only the combo: a mid-edit
        level isn't clobbered by opening the dropdown."""
        self._refresh_combo()
        self._select_active_in_combo()

    # ------------------------------------------------------------------
    # Read-only convenience
    # ------------------------------------------------------------------

    @property
    def hdr_map(self) -> Optional[str]:
        """The dropdown's picked HDR path (or the None token)."""
        return self.ui.cmb000.currentData()

    @property
    def hdr_map_visibility(self) -> bool:
        """The render-visibility toggle; before it exists, the scene's own."""
        if self._render_toggle is not None:
            return bool(self._render_toggle.is_on)
        return bool(self._read("visibility"))

    @property
    def hdr_map_preview(self) -> bool:
        """The viewport-visibility toggle; False before it exists."""
        return bool(self._viewport_toggle.is_on) if self._viewport_toggle else False

    # ------------------------------------------------------------------
    # Slot handlers
    # ------------------------------------------------------------------

    def cmb000(self, index, widget) -> None:
        """HDR map pick: the panel's apply, handed to the manager's
        ``defer_apply``.

        A pick mutates the scene (swap the map, build a network, or remove it
        for None). Maya runs that on its idle queue, off the combo signal: the
        popup's teardown is a re-entrant Qt loop, and a live Arnold IPR
        re-translating the skydome inside it leaves the render stuck black.
        Blender's world edit has no such hazard and runs at once.
        """
        path = widget.currentData()
        if not path:  # nothing picked
            return
        if path == self.NONE_TOKEN:
            self.ui.footer.setText("Removing HDR…", level="info")
        else:
            self.ui.footer.setText(f"Applying {os.path.basename(path)}…", level="info")
        self.manager.defer_apply(self._apply_selection)

    def _on_viewport_visible(self, state) -> None:
        """Viewport visibility (the slider's first toggle): the HDR as a
        viewport backdrop, live. Lighting is unaffected."""
        self._write("preview", bool(state))

    def _on_render_visible(self, state) -> None:
        """Render visibility (the slider's second toggle): the HDR as the
        render's backdrop, live and synchronous like the other controls -- a
        deferred write was starved by a running Arnold IPR."""
        self._write("visibility", bool(state))

    def slider000(self, value, widget) -> None:
        """Rotate the environment around the up axis."""
        self._write("rotation", value)

    def spn_intensity(self, value) -> None:
        """The environment's linear intensity."""
        self._write("intensity", value)

    def spn_exposure(self, value) -> None:
        """The environment's exposure, in stops."""
        self._write("exposure", value)

    def spn_resolution(self, value) -> None:
        """The HDR's importance-sampling resolution."""
        self._write("resolution", value)

    def spn_samples(self, value) -> None:
        """The environment's light samples."""
        self._write("samples", value)

    def spn_diffuse(self, value) -> None:
        """The environment's diffuse contribution."""
        self._write("diffuse", value)

    def spn_specular(self, value) -> None:
        """The environment's specular contribution."""
        self._write("specular", value)

    def _validate_or_warn(self, path: str, *, dialog: bool = True) -> bool:
        """True if *path* is safe to light the scene with.

        A missing file is allowed through (Maya shows a checker); an existing
        but incomplete image -- a partly synced cloud HDR -- is refused: Maya's
        Viewport 2.0 crashes loading it for the light's IBL, Blender's loader
        chokes on it. The refusal goes to the footer and the console, and a
        modal when *dialog* is True.
        """
        if not os.path.isfile(path):
            return True
        ok, reason = ptk.ImgUtils.validate_image_integrity(path)
        if ok:
            return True
        name = os.path.basename(path)
        self._notify(
            f"{name} is incomplete on disk ({reason})",
            level="error",
            detail=(
                f"HDR not loaded — only part of the file is on disk ({reason}):\n"
                f"{path}\n\n"
                "Common causes: it's a cloud-synced file still downloading, a "
                "download or export that was interrupted, or the disk filled up "
                "mid-write. If it's a cloud file, make sure your sync client is "
                "running and let it finish downloading (right-click -> 'Make "
                "available offline' / 'Always keep on this device'); otherwise "
                "free up disk space and re-export or re-download it. Then retry."
            ),
            dialog=dialog,
            # The popup stays digestible: name + the fix, no raw path.
            dialog_text=(
                f"{name} is incomplete on disk ({reason}).\n\n"
                "Common causes: a cloud-synced file still downloading, an "
                "interrupted download or export, or a full disk. If it's a cloud "
                "file, make sure your sync client is running and it finishes "
                "downloading; otherwise free up space and re-export or "
                "re-download it, then retry.\n\n(Full path in the console.)"
            ),
        )
        return False

    def _clear_environment(self, absent_msg: str, *, absent_level: str = "info") -> bool:
        """Remove the environment, resync and report; with none, report
        *absent_msg* and return False. The one clear path (the None pick and
        Clear Network)."""
        if self.manager.hdr_env is None:
            self._notify(absent_msg, level=absent_level)
            return False
        self.manager.clear()
        self._sync_ui_to_scene()
        self._notify("HDR environment cleared.", level="success")
        return True

    def _apply_path(self, path: str) -> bool:
        """Light the scene from *path*: swap the live environment's map in
        place (its levels kept), else build one from the controls. False when
        none was built (Maya: Arnold unavailable)."""
        if self.manager.hdr_env is not None:
            self.manager.hdr_env = path
            return True
        built = self.manager.create_network(
            hdrMap=path,
            hdrMapVisibility=self.hdr_map_visibility,
            intensity=self.ui.spn_intensity.value(),
            exposure=self.ui.spn_exposure.value(),
            rotation=self.ui.slider000.sliderPosition(),
            resolution=self.ui.spn_resolution.value(),
            samples=self.ui.spn_samples.value(),
            diffuse=self.ui.spn_diffuse.value(),
            specular=self.ui.spn_specular.value(),
            preview=self.hdr_map_preview,
        )
        return built is not None

    def _apply_selection(self) -> None:
        """Apply the dropdown's pick: None removes the environment, a map
        swaps or builds it (:meth:`_apply_path`). Re-reads the dropdown, so the
        latest pick wins. A pick that can't apply re-points the dropdown at the
        live map, so it never shows a map that isn't lighting the scene."""
        path = self.hdr_map
        if path == self.NONE_TOKEN:
            self._clear_environment("HDR is set to None — no environment to clear.")
            return
        if not path:
            self._notify("Pick or browse for an HDR first.", level="warning")
            self._select_active_in_combo()
            return
        # A casual pick: a bad file goes to the footer and console, no modal.
        if not self._validate_or_warn(path, dialog=False):
            self._select_active_in_combo()
            return
        if not self._apply_path(path):
            self._notify(
                "HDR environment not built (details in the console).",
                level="warning",
            )
            self._select_active_in_combo()
            return
        self._sync_ui_to_scene()
        self._notify(f"HDR: {os.path.basename(path)}", level="success")

    def add_hdr(self) -> None:
        """Add HDR(s): one dialog picks loose files and/or folders (expanded
        to their environment maps), imported per the mode. A single loose file
        gets the careful UX (modal on a bad file, overwrite prompt); a folder
        or several files is a bulk add (skip + count)."""
        selected = self._pick_hdr_paths(self._texture_dir())
        if not selected:
            return

        dirs = [p for p in selected if os.path.isdir(p)]
        files = [p for p in selected if os.path.isfile(p)]
        paths = list(files)
        for d in dirs:
            paths.extend(self._folder_hdrs(d))

        careful = len(files) == 1 and not dirs
        if dirs and not files:
            where = os.path.basename(dirs[0].rstrip("/\\")) or dirs[0]
        else:
            where = "selection"
        self._add_hdrs(paths, where=where, careful=careful)

    def _pick_hdr_paths(self, start: str) -> list:
        """One dialog selecting HDR/EXR files and/or folders (Qt has no native
        "files or directories" mode: a non-native dialog with its views in
        extended selection). ``[]`` on cancel."""
        QtW = self.sb.QtWidgets
        dialog = QtW.QFileDialog(self.ui, "Add HDR(s) — pick files and/or a folder", start)
        dialog.setFileMode(QtW.QFileDialog.ExistingFiles)
        dialog.setOption(QtW.QFileDialog.DontUseNativeDialog, True)
        dialog.setNameFilters(self.HDR_FILTER.split(";;"))
        # findChildren with a tuple of types isn't portable across bindings.
        views = dialog.findChildren(QtW.QListView) + dialog.findChildren(QtW.QTreeView)
        for view in views:
            view.setSelectionMode(QtW.QAbstractItemView.ExtendedSelection)
        if dialog.exec_():
            return dialog.selectedFiles() or []
        return []

    def _add_hdrs(self, paths: list, *, where: str, careful: bool) -> None:
        """Import HDR/EXR *paths* per the mode, then light the scene from the
        last good one.

        *careful* (one explicit file): a bad file raises the modal, a same-named
        file in sourceimages prompts before overwrite. Otherwise (a bulk add):
        incomplete files are skipped into a count and an existing usable file
        is reused, never clobbered. Copy / Move bring each into sourceimages
        (so it lists); a file already anywhere under it is used in place; Link
        wires it where it is. *where* labels the summary.
        """
        if not paths:
            self._notify(f"No HDR environment maps in {where}.", level="warning")
            return

        mode = self._add_mode()
        src = self._texture_dir() if mode != "link" else None
        if mode != "link" and (not src or not os.path.isdir(src)):
            self._notify(
                "No sourceimages folder: set a project first.",
                level="error",
                dialog=True,
            )
            return

        added, skipped, last, did_io = 0, 0, None, False
        for path in paths:
            if careful:
                if not self._validate_or_warn(path):
                    return
            elif not ptk.ImgUtils.validate_image_integrity(path)[0]:
                skipped += 1
                continue

            if mode == "link":
                last, added = path, added + 1
                continue

            if self._is_under_dir(path, src):
                last, added = os.path.normpath(path), added + 1
                continue

            final = os.path.normpath(os.path.join(src, os.path.basename(path)))
            if os.path.exists(final):
                if careful:
                    if not self._confirm_overwrite(final):
                        self._notify(f"{mode.capitalize()} cancelled.", level="info")
                        return
                elif ptk.ImgUtils.validate_image_integrity(final)[0]:
                    last, added = final, added + 1  # reuse a usable existing file
                    continue
                else:
                    skipped += 1  # the existing one is corrupt: never clobber in bulk
                    continue
            try:
                self._IO_OPS[mode](path, final)
            except OSError as e:
                self.logger.error("Add — %s of %s failed: %s", mode, path, e)
                if careful:
                    self._notify(
                        f"{mode.capitalize()} failed: {e}",
                        level="error",
                        detail=f"{mode} of {path} → {final} failed: {e}",
                        dialog=True,
                    )
                    return
                skipped += 1
                continue
            last, added, did_io = final, added + 1, True

        self._refresh_combo()
        if last:
            self._select_combo_path(last)
            if not self._apply_path(last):
                self._notify(
                    "HDR environment not built (details in the console).",
                    level="warning",
                )
                self._select_active_in_combo()
                return
            self._sync_ui_to_scene()

        self._notify_add_result(
            added, skipped, last, where=where, careful=careful, mode=mode, did_io=did_io
        )

    def _notify_add_result(self, added, skipped, last, *, where, careful, mode, did_io) -> None:
        """The footer summary of an add: one rich line, or a bulk count."""
        if careful and added:
            name = os.path.basename(last)
            if mode == "link":
                verb = "Linked"
            elif did_io:
                verb = {"copy": "Copied & set", "move": "Moved & set"}[mode]
            else:
                verb = "Set"  # reused an existing sourceimages copy
            self._notify(f"{verb}: {name}", level="success")
        elif added:
            msg = f"Added {added} HDR{'s' if added != 1 else ''} from {where}"
            if skipped:
                msg += f" ({skipped} skipped — incomplete/corrupt)"
            self._notify(msg, level="success")
        else:
            self._notify(
                f"No usable HDRs in {where} ({skipped} incomplete/corrupt).",
                level="warning",
            )

    # ------------------------------------------------------------------
    # Header-menu actions
    # ------------------------------------------------------------------

    def open_sourceimages(self) -> None:
        """Open the project's texture folder in the file manager."""
        src = self._texture_dir()
        if not src or not os.path.isdir(src):
            self._notify("No sourceimages folder: set a project first.", level="warning")
            return
        ptk.FileUtils.open_explorer(src, logger=self.logger)

    def clear_network(self) -> None:
        """Remove the HDR environment and reset the controls to defaults."""
        self._clear_environment("No HDR network in scene.")

    # ------------------------------------------------------------------
    # Context-menu actions (right-click on cmb000)
    # ------------------------------------------------------------------

    def _select_part(self, part: str) -> None:
        """Select the environment's *part* through the manager (Maya)."""
        select = getattr(self.manager, "select", None)
        if select is None:  # the items are disabled (Blender)
            return
        node = select(part)
        if not node:
            self._notify(self._SELECT_ABSENT[part], level="warning")
            return
        self._notify(f"Selected: {node}", level="success")

    def ctx_select_skydome(self) -> None:
        """Select the skydome light."""
        self._select_part("skydome")

    def ctx_select_transform(self) -> None:
        """Select the skydome's transform."""
        self._select_part("transform")

    def ctx_select_file_node(self) -> None:
        """Select the file node feeding the skydome's HDR texture."""
        self._select_part("file_node")

    def ctx_reveal_in_explorer(self) -> None:
        """Reveal the environment's HDR file in the file manager; without one
        on disk, open the texture folder instead."""
        path = self.manager.hdr_file_path
        try:
            if path and os.path.exists(path):
                ptk.FileUtils.reveal_in_file_manager(path)
                return
            src = self._texture_dir()
            if src and os.path.isdir(src):
                ptk.FileUtils.open_explorer(src, logger=self.logger)
                return
        except OSError as e:  # FileNotFoundError included
            self._notify(str(e), level="error")
            return
        self._notify("HDR file not found and no sourceimages folder.", level="warning")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _norm_path(path) -> str:
        """Case-folded, separator-normalized *path*, for comparison: the combo
        holds raw listings that can mix slash styles."""
        return os.path.normcase(os.path.normpath(str(path)))

    @staticmethod
    def _is_under_dir(path: str, directory: str) -> bool:
        """True if *path* lies inside *directory*, at any depth
        (``ptk.FileUtils.is_under`` over :meth:`_norm_path`)."""
        return ptk.FileUtils.is_under(
            HdrManagerSlots._norm_path(path), HdrManagerSlots._norm_path(directory)
        )

    def _add_mode(self) -> str:
        """The Add-HDR mode token (``copy`` / ``move`` / ``link``); ``copy``
        before the option box exists."""
        try:
            idx = self.ui.cmb000.option_box.menu.cmb_add_mode.currentIndex()
        except AttributeError:
            return "copy"
        if 0 <= idx < len(self._ADD_MODES):
            return self._ADD_MODES[idx][1]
        return "copy"

    def _confirm_overwrite(self, target_path: str) -> bool:
        """Ask before overwriting an existing file in sourceimages."""
        return (
            self.sb.message_box(
                f"{os.path.basename(target_path)} already exists in sourceimages.\n"
                "Overwrite it?",
                "Yes",
                "No",
            )
            == "Yes"
        )
