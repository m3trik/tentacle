# !/usr/bin/python
# coding=utf-8
"""UI slot bindings for the Map Compositor: several texture maps of each type
merged into one image, normal formats converted.

A standalone panel (``tentacle/tcl_standalone.py``). Slots own the UI state and
compose pythontk's :class:`MapCompositor` engine.
Engine status messages flow through ``self.engine.logger`` (a LoggingMixin
logger) which has a default ``StreamHandler`` for console output; we
attach uitk's :class:`TextEditLogHandler` alongside it so the UI message
panel auto-scrolls. Progress-bar updates use a thin callback.
"""

import logging
import os
from typing import Optional

import pythontk as ptk
from pythontk import BatchResult, MapCompositor, NormalOutputMode, TooltipFormat
from qtpy.QtWidgets import QPushButton

from tentacle import Slots

#: The panel's page. Its engine is pythontk's ``MapCompositor``: nothing here
#: needs extapps, whose docs hold the page.
_DOCS_URL = "https://github.com/m3trik/extapps/blob/main/docs/map_compositor.md"


class _CompositorSlotsInternal:
    """Tooltip/intro copy builders for :class:`CompositorSlots`.

    Kept off the public class per the encapsulation standard (helpers live on a
    ``_<Class>Internal`` base the public class inherits). They run at class-body
    evaluation time to fill the ``msg_*``/``tip_*`` attributes, so this base must
    be defined before ``CompositorSlots``.
    """

    @staticmethod
    def _build_intro() -> str:
        """One-time intro panel: minimal quickstart + link to full docs.

        The full filename-suffix table used to live here but dwarfed the
        actual instructions — readers had to scroll past ~30 rows of alias
        lists to find the basic export settings. Moved to the GitHub README;
        this panel now stays a single screen.
        """
        return (
            "<u>Quickstart</u><br>"
            "&nbsp;&nbsp;1. Set the <b>source</b> (a directory of maps, or specific "
            "image files) and the <b>destination</b> directory.<br>"
            "&nbsp;&nbsp;2. (Optional) Set a <b>map name</b> prefix.<br>"
            "&nbsp;&nbsp;3. Click <b>Combine Maps</b>.<br><br>"
            "<u>Required Substance Painter Export Settings</u><br>"
            "&nbsp;&nbsp;Output Template: <b>Document channels</b><br>"
            "&nbsp;&nbsp;Padding: <b>Dilation + transparent</b> or "
            "<b>Dilation + default background color</b><br><br>"
            f'<span style="color:#888888">'
            f"Full filename-suffix table and detailed docs: "
            f'<a href="{_DOCS_URL}" style="color:#88AACC">{_DOCS_URL}</a>'
            "</span>"
        )

    @staticmethod
    def _build_source_tooltip() -> str:
        """Rich-text tooltip for the source field's resting (empty) state.

        Built with uitk's :func:`fmt`/:func:`hl` so the colors match the rest of
        the ecosystem's tooltips. Shown while the field is empty; once a valid
        source is entered the validator swaps in :meth:`_source_valid_tooltip`.
        """
        return TooltipFormat.fmt(
            title="Source maps to combine",
            body="A folder of texture maps, or specific image files.",
            bullets=[
                f"{TooltipFormat.hl('Add files…')} — pick one or more image files.",
                f"{TooltipFormat.hl('Choose folder…')} — use every image in a folder.",
                "Or type / paste a folder path directly.",
                "Recent sources are in the option box (clock icon).",
            ],
            notes=[
                "Maps are matched by filename suffix — e.g. "
                "<i>_BaseColor</i>, <i>_Normal</i>, <i>_Roughness</i>."
            ],
        )

    @staticmethod
    def _build_dest_tooltip() -> str:
        """Rich-text tooltip for the destination-directory field."""
        return TooltipFormat.fmt(
            title="Destination directory",
            body="The folder where your combined maps are written.",
            bullets=[
                f"{TooltipFormat.hl('Choose folder…')} — pick the output folder.",
                "Or type / paste a folder path directly.",
                "Recent destinations are in the option box (clock icon).",
            ],
        )

    @staticmethod
    def _build_mapname_tooltip() -> str:
        """Rich-text tooltip for the map-name (filename prefix) field."""
        return TooltipFormat.fmt(
            title="Map name prefix",
            body="Optional filename prefix for the combined maps.",
            notes=["Leave empty to use the source folder's name."],
        )


class CompositorSlots(Slots, _CompositorSlotsInternal):
    """UI slot handler. Composes a :class:`MapCompositor` via ``self.engine``."""

    msg_intro = _CompositorSlotsInternal._build_intro()
    tip_source = _CompositorSlotsInternal._build_source_tooltip()
    tip_dest = _CompositorSlotsInternal._build_dest_tooltip()
    tip_mapname = _CompositorSlotsInternal._build_mapname_tooltip()

    # (display label, NormalOutputMode) — order shown in the header combo.
    NORMAL_MODE_CHOICES = (
        ("Both (auto-convert)", NormalOutputMode.BOTH),
        ("OpenGL only", NormalOutputMode.OPENGL_ONLY),
        ("DirectX only", NormalOutputMode.DIRECTX_ONLY),
        ("No conversion", NormalOutputMode.NONE),
    )

    # "None" disables the post-composite workflow pass; the remaining entries
    # are populated from pythontk's MapRegistry at runtime so the menu stays
    # in sync with the registry's WF.* workflow keys.
    _NO_TEMPLATE_LABEL = "None (composite only)"

    def __init__(self, switchboard) -> None:
        super().__init__(switchboard)
        self.ui = self.sb.loaded_ui.compositor

        # The engine is widget-free and the *_init hooks read it during
        # registration, so it must exist now.
        self.engine = MapCompositor(progress_callback=self._on_progress)

        # The switchboard can build this slots instance before the child
        # widgets are registered onto self.ui — even eagerly during Switchboard
        # construction (slot_source=). Touching widgets here would raise and
        # leave ``ui.slots = None``. Defer the widget wiring (log pane, intro,
        # footer button) until the UI is registered.
        self.ui.run_when_ready(self._initialize_ui)

    def _initialize_ui(self) -> None:
        """Wire the widgets that span the whole UI, once it is registered."""
        logger = self.engine.logger
        # Class-level logger — sweep stale widget handlers from prior sessions.
        for h in list(logger.handlers):
            if hasattr(h, "widget"):
                logger.removeHandler(h)
        # Attach directly; ``_set_text_handler`` would force this handler
        # process-wide. monospace=False keeps the intro's rich-text font;
        # log records still render monospace via TextEditLogHandler's <span>.
        logger.setLevel(logging.INFO)
        handler = self.sb.TextEditLogHandler(self.ui.txt003, monospace=False)
        handler.setLevel(logging.INFO)
        handler.setFormatter(ptk.LevelAwareFormatter(logger=logger, strip_html=False))
        logger.addHandler(handler)

        # txt003 is a QTextBrowser; TextEditLogHandler already routed its
        # links (no internal navigation; web anchors -- the intro's docs link
        # -- open in the browser), so anchorClicked here only needs to serve
        # the completion message's action://open output-dir link.
        if hasattr(self.ui.txt003, "anchorClicked"):
            self.ui.txt003.anchorClicked.connect(self._on_log_link_clicked)

        self.ui.txt003.setText(self.msg_intro)
        self.ui.footer.setDefaultStatusText("Ready.")

        # The primary action ("Combine Maps") lives in the footer with a
        # styled background so it stands out from the status text. It is wired
        # explicitly to b002 and carries no objectName, so Switchboard's
        # name-based auto-wiring (which DOES process add_widget footer widgets)
        # resolves no slot for it and leaves it untouched.
        self.combine_btn = QPushButton("Combine Maps")
        self.combine_btn.setToolTip("Start the compositing process.")
        self.combine_btn.clicked.connect(self.b002)
        self.ui.footer.add_widget(
            self.combine_btn, side="right", background=True, rounded=False
        )

    # --- output/name text-field properties ---
    # (the source field is read via _resolve_source, not a property)
    @property
    def output_dir(self) -> str:
        return self.ui.txt001.text()

    @property
    def map_name(self) -> str:
        return self.ui.txt002.text()

    # --- shared helpers ---
    def _bind_recent_values(
        self,
        widget,
        settings_key: str,
        legacy_key: str,
        *,
        auto_record: bool = False,
    ):
        """Attach a RecentValuesOption and seed it from legacy QSettings."""
        opt = self.sb.RecentValuesOption(
            wrapped_widget=widget,
            settings_key=settings_key,
            max_recent=10,
            auto_record=auto_record,
        )
        widget.option_box.add_option(opt)
        if not opt.recent_values:
            for v in self.ui.settings.value(legacy_key, []):
                if v != "/":
                    opt.add_recent_value(v)
        return opt

    def _bind_dir_actions(
        self,
        widget,
        *,
        recent_attr: str,
        folder_title: str,
        folder_tooltip: str,
        files_title: Optional[str] = None,
    ):
        """Build the field's option-box dropdown menu of path actions.

        Groups the field's path actions under a single option-box dropdown:

        * **Choose folder…** (both fields) — a directory dialog. The chosen
          folder becomes the field value (plain directory mode).
        * **Add files…** (source field only, when *files_title* is given) —
          a multi-select image-file dialog, so the source can be a whole
          folder *or* a hand-picked set of files. A folder path typed,
          pasted, or recalled is also accepted (the validator and
          :meth:`_resolve_source` both understand a bare directory).
        * **Open this location** — reveal the field's directory in the OS
          file explorer. Kept **last** so the two "set the value" actions
          read first and the reveal sits at the bottom.

        *recent_attr* names the ``RecentValuesOption`` attribute the folder
        dialog records into. Returns the *Open this location* button so the
        caller can toggle its enabled state from the text-change handler.
        """
        # One-shot action menu — suppress the settings-form chrome (apply /
        # restore-defaults footer, title header) so it reads as a plain
        # action list rather than an options panel.
        widget.option_box.enable_menu(
            add_apply_button=False,
            add_defaults_button=False,
            add_header=False,
        )
        menu = widget.option_box.menu

        if files_title:
            add_btn = menu.add(
                "QPushButton",
                setText="Add files…",
                setToolTip="Browse for specific source image files.",
            )
            add_btn.clicked.connect(
                lambda: self._browse_source_files(widget, files_title)
            )

        folder_btn = menu.add(
            "QPushButton",
            setText="Choose folder…",
            setToolTip=folder_tooltip,
        )
        folder_btn.clicked.connect(
            lambda: self._browse_directory(
                widget, folder_title, recent_attr=recent_attr
            )
        )

        open_btn = menu.add(
            "QPushButton",
            setText="Open this location",
            setToolTip="Open this location in the file explorer.",
        )
        open_btn.clicked.connect(
            lambda: self._open_dir(self._field_dir(widget.value()))
        )

        return open_btn

    def _browse_source_files(self, widget, title: str) -> None:
        """Open a multi-select image dialog and store the joined paths.

        The field carries the full ``os.pathsep``-joined paths as its *data*
        (the representation :meth:`_resolve_source` and the source validator
        understand) while *displaying* a compact one-name-per-texture-set
        label (see :meth:`_source_display`). The data-aware recent-values
        history keeps both, so a restored entry shows the friendly label and
        still resolves to the real files.
        """
        file_types = [f"*.{ext}" for ext in ptk.ImgUtils.readable]
        paths = self.sb.file_dialog(
            file_types=file_types,
            title=title,
            start_dir=self._field_dir(widget.value()) or os.path.expanduser("~"),
            filter_description="Images",
            allow_multiple=True,
        )
        if not paths:
            return
        if isinstance(paths, str):
            paths = [paths]
        widget.set_value(os.pathsep.join(paths), display=self._source_display(paths))
        recent = getattr(self, "_recent_input_dirs", None)
        if recent is not None:
            recent.record()  # data-aware: captures the display + the real paths

    @staticmethod
    def _source_display(paths) -> str:
        """A compact label for a multi-file source: one name per texture set.

        Groups the selected files into texture sets by base name (stripping
        map-type suffixes) and joins the set names, so a 12-file, 3-set
        selection reads ``brick, metal, wood`` rather than a wall of paths.
        Falls back to deduped file stems if set grouping yields nothing.
        """
        paths = list(paths)
        try:
            names = [n for n in ptk.MapFactory.group_textures_by_set(paths) if n]
        except Exception:
            names = []
        if not names:
            names = sorted(
                {os.path.splitext(os.path.basename(p))[0] for p in paths if p}
            )
        return ", ".join(names)

    def _browse_directory(self, widget, title: str, *, recent_attr: str) -> None:
        """Open a directory dialog and store the chosen folder as the value.

        Writes the folder via ``set_value`` (no display), which clears any
        prior file-selection payload so the field drops back to plain
        directory mode, then records it to the *recent_attr* history
        (programmatic edits don't trip the ``auto_record`` commit hook).
        """
        from qtpy.QtWidgets import QFileDialog

        start = self._field_dir(widget.value()) or os.path.expanduser("~")
        path = QFileDialog.getExistingDirectory(widget.window(), title, start)
        if not path:
            return
        widget.set_value(path)
        recent = getattr(self, recent_attr, None)
        if recent is not None:
            recent.record()

    @staticmethod
    def _source_parts(text: str) -> list:
        """Tokenize a source field into its ``os.pathsep``-joined components.

        Single source of truth for how the field is split — the file-selection
        join scheme lives here so the helpers below stay in sync.
        """
        return [p for p in (text or "").split(os.pathsep) if p.strip()]

    @classmethod
    def _split_source(cls, text: str) -> list:
        """Split a source field into its image-file parts.

        Returns the list of file paths when the field holds an
        ``os.pathsep``-joined file selection (or a single file). Returns an
        empty list when the field holds a single existing directory — the
        caller then treats it as directory mode.
        """
        parts = cls._source_parts(text)
        if len(parts) == 1 and os.path.isdir(parts[0]):
            return []
        return parts

    @classmethod
    def _field_dir(cls, text: str) -> str:
        """Resolve a path field's text to a directory.

        Accepts a directory, a single file, or an ``os.pathsep``-joined list
        of files; returns the directory to reveal/browse-from. Empty when it
        can't be resolved.
        """
        parts = cls._source_parts(text)
        if not parts:
            return ""
        first = parts[0]
        if os.path.isdir(first):
            return first
        parent = os.path.dirname(first)
        return parent if os.path.isdir(parent) else ""

    @classmethod
    def _validate_source(cls, text: str) -> bool:
        """Validate the source field: a directory OR image file(s)."""
        parts = cls._source_parts(text)
        if not parts:
            return False
        if len(parts) == 1 and ptk.is_valid(parts[0], "dir"):
            return True
        return all(ptk.is_valid(p, "file") for p in parts)

    @classmethod
    def _source_valid_tooltip(cls, text: str) -> str:
        """Readable rich-text tooltip for a *valid* source field.

        Directory mode shows the folder path as-is. An explicit image-file
        selection renders as a header (file + texture-set counts) followed by
        one indented line per texture set — its name, member count and the map
        basenames — rather than the raw ``os.pathsep``-joined paths the field
        actually stores. Qt auto-detects the rich text and word-wraps it.
        """
        files = cls._split_source(text)
        if not files:  # directory mode
            return text

        try:
            sets = ptk.MapFactory.group_textures_by_set(files)
        except Exception:
            sets = {}
        if not sets:  # ungroupable — flat basename list
            sets = {"": files}

        n_files, n_sets = len(files), len(sets)
        f_plural = "" if n_files == 1 else "s"
        s_plural = "" if n_sets == 1 else "s"
        muted = "color:#9a9a9a"
        lines = [
            f"{TooltipFormat.hl(f'{n_files} image file{f_plural}')} "
            f'<span style="{muted}">in {n_sets} texture set{s_plural}</span>'
        ]
        for set_name, members in sets.items():
            basenames = ", ".join(os.path.basename(f) for f in members)
            label = f"<b>{set_name}</b> " if set_name else ""
            lines.append(
                f"&nbsp;&nbsp;{label}"
                f'<span style="{muted}">({len(members)})</span>&nbsp; {basenames}'
            )
        return "<br>".join(lines)

    def _resolve_source(self):
        """Resolve the source field into ``(images, source_dir)``.

        The field holds either a single directory or an ``os.pathsep``-joined
        list of image files. Returns the ``{path: image}`` mapping the engine
        expects plus a representative directory used for naming/validation.
        """
        # The field carries the real paths as its data payload (set by
        # _browse_source_files); value() returns that, or the typed text.
        text = self.ui.txt000.value()
        if not text:
            return {}, ""
        files = self._split_source(text)
        if files:  # explicit image-file selection
            files = [f for f in files if os.path.isfile(f)]
            images = {f: ptk.ImgUtils.load_image(f) for f in files}
            source_dir = os.path.dirname(files[0]) if files else ""
            return images, source_dir
        # Directory mode (existing behaviour).
        return ptk.get_images(text), text

    @staticmethod
    def _open_dir(path: Optional[str]) -> None:
        """Reveal a directory in the OS file explorer (cross-platform).

        Delegates to the canonical, non-shell launcher (packer.b001 uses the
        same one), which dispatches os.startfile / open / xdg-open by platform
        and no-ops safely on an empty or nonexistent path. Using it here fixes
        the AttributeError crash that a bare ``os.startfile`` raised off-Windows.
        """
        ptk.FileUtils.open_explorer(path)

    def _on_log_link_clicked(self, url) -> None:
        """Route ``action://`` links in the log panel.

        ``action://open?path=…`` reveals a file/folder in the OS file
        explorer (used by the completion message's output-dir link). The
        intro's ``http(s)`` docs link is opened by
        :meth:`TextEditLogHandler.route_links` off the same signal, so it is
        deliberately not handled here (that would open it twice).
        """
        try:
            if url.scheme() == "action" and url.host() == "open":
                from urllib.parse import parse_qs

                path = parse_qs(url.query()).get("path", [""])[0]
                if path:
                    self._open_dir(path)
        except Exception:  # pragma: no cover - defensive
            pass

    def _on_dir_validated(self, ok: bool, text: str, open_btn):
        """Enable the menu's *Open this location* item only for a valid path."""
        open_btn.setEnabled(bool(text and ok))

    def _on_progress(self, percent: float) -> None:
        """Engine→UI progress bar bridge (routes through the footer).

        Goes through ``Footer.update_progress`` rather than poking
        ``progress_bar.setValue`` directly — the bar is created with
        ``auto_hide=True`` and only becomes visible after the matching
        ``start_progress`` call in ``process()``. ``ProgressBar.update_progress``
        already pumps the event loop, so no extra ``processEvents`` here.
        """
        self.ui.footer.update_progress(int(percent))

    # --- widget init handlers ---
    def header_init(self, widget):
        """Populate the header menu with global options."""
        widget.menu.add(
            "QCheckBox",
            setText="Optimize output",
            setObjectName="chk_optimize",
            setChecked=self.engine.optimize_output,
            setToolTip=(
                "Run MapOptimizer.optimize_map on each saved map "
                "(enforces map-type bit depth and mode)."
            ),
            stateChanged=self._on_optimize_toggled,
        )
        widget.menu.add(
            "QComboBox",
            setObjectName="cmb_normal_mode",
            setToolTip=(
                "Choose which DirectX/OpenGL normal map variant(s) to output. "
                "Note: when an output template is selected, the template's "
                "required normal format may add a sibling file alongside the "
                "compositor's output."
            ),
            addItems=[label for label, _mode in self.NORMAL_MODE_CHOICES],
        )
        # Sync the combo to the engine's current value before connecting the
        # signal, so the initial setCurrentIndex doesn't re-trigger the slot.
        modes = [m for _label, m in self.NORMAL_MODE_CHOICES]
        widget.menu.cmb_normal_mode.setCurrentIndex(
            modes.index(self.engine.normal_output_mode)
        )
        widget.menu.cmb_normal_mode.currentIndexChanged.connect(
            self._on_normal_mode_changed
        )

        # Output template — names sourced from pythontk's MapRegistry so the
        # menu mirrors the registry's WF.* workflow keys. None = composite
        # only (no post-pass). When set, after compositing finishes the
        # engine runs MapFactory.prepare_maps with the matching workflow
        # preset to pack/rename files for the target engine.
        profiles = ptk.OutputTemplates.profile_choices()
        self._template_choices = (
            self._NO_TEMPLATE_LABEL,
            *(name for name, _ in profiles),
        )
        widget.menu.add(
            "QComboBox",
            setObjectName="cmb_output_template",
            setToolTip=(
                "Post-process composited output for a target workflow. "
                "Packs/renames the files for the chosen engine (e.g. Unity "
                "HDRP packs Metallic/AO/Smoothness into an MSAO MaskMap). "
                "glTF 2.0 is also the WebXR delivery profile. "
                "Original composited files stay on disk alongside the "
                "workflow output."
            ),
            addItems=list(self._template_choices),
        )
        # Pre-select to match the engine field (default: None).
        current = self.engine.output_template or self._NO_TEMPLATE_LABEL
        try:
            widget.menu.cmb_output_template.setCurrentIndex(
                self._template_choices.index(current)
            )
        except ValueError:
            widget.menu.cmb_output_template.setCurrentIndex(0)
        widget.menu.cmb_output_template.currentIndexChanged.connect(
            self._on_output_template_changed
        )

    def _on_optimize_toggled(self, state) -> None:
        # Qt.Checked is 2 in PySide6, 2 in PySide2 — robust check via bool.
        self.engine.optimize_output = bool(state)

    def _on_normal_mode_changed(self, index: int) -> None:
        _label, mode = self.NORMAL_MODE_CHOICES[index]
        self.engine.normal_output_mode = mode

    def _on_output_template_changed(self, index: int) -> None:
        choice = self._template_choices[index]
        self.engine.output_template = (
            None if choice == self._NO_TEMPLATE_LABEL else choice
        )

    def txt000_init(self, widget):
        """Init Source — a directory of maps, or specific image files."""
        # Install the formatted resting-state tooltip (overrides the plain
        # .ui fallback), then capture it for the validator's empty state.
        widget.setToolTip(self.tip_source)
        self.default_toolTip_txt000 = widget.toolTip()
        self._recent_input_dirs = self._bind_recent_values(
            widget,
            "compositor_input_dirs",
            "prev_input_dirs",
            auto_record=True,
        )
        self._open_input_dir = self._bind_dir_actions(
            widget,
            recent_attr="_recent_input_dirs",
            folder_title="Select a source folder of texture maps.",
            folder_tooltip="Browse for a source folder of texture maps.",
            files_title="Select source image files.",
        )
        widget.set_validator(
            self._validate_source,
            invalid_tooltip="Not a valid directory or image-file selection",
            valid_tooltip=self._source_valid_tooltip,
            empty_tooltip=self.default_toolTip_txt000,
        )
        widget.validated.connect(
            lambda ok, text: self._on_dir_validated(ok, text, self._open_input_dir)
        )

    def txt001_init(self, widget):
        """Init Destination Directory"""
        # Install the formatted resting tooltip before capturing it as the
        # validator's empty-state tooltip (overrides the plain .ui fallback).
        widget.setToolTip(self.tip_dest)
        self.default_toolTip_txt001 = widget.toolTip()
        self._recent_output_dirs = self._bind_recent_values(
            widget,
            "compositor_output_dirs",
            "prev_output_dirs",
            auto_record=True,
        )
        self._open_output_dir = self._bind_dir_actions(
            widget,
            recent_attr="_recent_output_dirs",
            folder_title="Select an output folder.",
            folder_tooltip="Browse for an output folder.",
        )
        widget.set_validator(
            "dir",
            invalid_tooltip="Invalid directory",
            empty_tooltip=self.default_toolTip_txt001,
        )
        widget.validated.connect(
            lambda ok, text: self._on_dir_validated(ok, text, self._open_output_dir)
        )

    def txt002_init(self, widget):
        """Init Map Name"""
        widget.setToolTip(self.tip_mapname)
        widget.option_box.clear_option = True
        # Disable holds the typed prefix aside and empties the field, so one run
        # falls back to the source folder's name without losing (or having to
        # retype) the prefix. Clear throws the value away; this parks it.
        widget.option_box.set_disable(
            settings_key="compositor_map_name",
            tooltip_on=(
                "Prefix applied. Click to disable — the combined maps take the "
                "source folder's name (your prefix is held until you re-enable)."
            ),
            tooltip_off=(
                "Prefix disabled — the combined maps take the source folder's "
                "name. Click to re-apply."
            ),
        )
        self._recent_map_names = self._bind_recent_values(
            widget,
            "compositor_map_names",
            "prev_map_names",
            auto_record=True,
        )

    # --- button handlers ---
    def b002(self):
        """Combine Maps"""
        self.ui.txt003.clear()
        self.ui.footer.setStatusText("Loading maps …")
        self.engine.logger.info("Loading maps ..", preset="italic")
        self.sb.app.processEvents()
        images, source_dir = self._resolve_source()
        self.process(images, source_dir, self.output_dir, self.map_name)

    # --- orchestration ---
    def process(self, images, source_dir, output_dir, map_name=None):
        """Validate dirs, prepare sorted-image groups, and drive the engine.

        *source_dir* is the directory the maps came from — either the
        directory the user selected, or the parent of an explicit image-file
        selection. It is used for output validation and the default map name.
        """
        if not (source_dir and output_dir):
            self.engine.logger.error(
                "You must specify a source and destination directory."
            )
            self.ui.footer.setStatusText("Source and destination directories required.")
            return

        invalid_dir = next(
            (d for d in (source_dir, output_dir) if not ptk.is_valid(d, "dir")),
            None,
        )
        if invalid_dir:
            self.engine.logger.error(f"Directory is invalid: <b>{invalid_dir}</b>.")
            self.ui.footer.setStatusText(f"Invalid directory: {invalid_dir}")
            return

        if not map_name:
            map_name = ptk.format_path(source_dir, "dir")

        sorted_images = ptk.MapFactory.sort_images_by_type(images)
        # NB: contains_map_types is an *any* test — true when the batch carries
        # either normal format, which is what the generic-Normal drop below
        # keys off. (The complement estimate is computed further down, once
        # the mode pre-filter has settled the final map set.)
        has_any_normal = ptk.MapFactory.contains_map_types(
            sorted_images, ["Normal_DirectX", "Normal_OpenGL"]
        )

        if self.engine.remove_normal_map and has_any_normal:
            normal = next(
                (
                    k
                    for k in sorted_images
                    if ptk.MapFactory.resolve_map_type(k) == "Normal"
                ),
                None,
            )
            if normal:
                del sorted_images[normal]

        # When the user has both DX *and* GL sources but only wants one
        # format, drop the redundant one — otherwise the engine would
        # process each independently and the iteration order would decide
        # which content survives (the second-processed format overwrites
        # the first via the auto-invert path).
        mode = self.engine.normal_output_mode
        if (
            mode is NormalOutputMode.OPENGL_ONLY
            and "Normal_OpenGL" in sorted_images
            and "Normal_DirectX" in sorted_images
        ):
            del sorted_images["Normal_DirectX"]
        elif (
            mode is NormalOutputMode.DIRECTX_ONLY
            and "Normal_OpenGL" in sorted_images
            and "Normal_DirectX" in sorted_images
        ):
            del sorted_images["Normal_OpenGL"]

        # Drop maps superseded by present packed maps (e.g. ORM → drops
        # Metallic/Roughness/AO; MSAO → drops more). In-place mutation.
        # NB: pythontk's sort_images_by_type already aliases legacy variants
        # like Mixed_AO into Ambient_Occlusion, so no manual rename is needed.
        ptk.MapFactory.filter_redundant_maps(sorted_images)

        # +1 for the auto-generated complementary normal map. BOTH emits the
        # missing counterpart, which it can only do when the batch carries
        # exactly one of the two formats — with both present neither is
        # regenerated, and the *_ONLY modes convert in place (src is deleted),
        # so the map count is unchanged in every other case.
        total_maps_extra = (
            1
            if mode is NormalOutputMode.BOTH
            and ("Normal_DirectX" in sorted_images)
            != ("Normal_OpenGL" in sorted_images)
            else 0
        )

        total_layers = sum(len(v) for v in sorted_images.values())
        total_maps = len(sorted_images) + total_maps_extra

        self.engine.logger.info(
            f"Sorting <b>{total_layers}</b> images, into <b>{total_maps}</b> maps ..",
            preset="italic",
        )
        # Reveal the footer's slim progress bar; engine ticks flow into
        # update_progress via _on_progress. finish_progress() in every
        # exit path auto-hides the bar after a short delay.
        self.ui.footer.start_progress(
            total=100,
            text=f"Compositing {total_maps} maps from {total_layers} layers …",
        )

        try:
            result = self.engine.process_batch(sorted_images, output_dir, map_name)
        except Exception as e:
            self.engine.logger.error(
                f"Operation encountered the following error:<br>{e}"
            )
            self.ui.footer.finish_progress(f"Failed: {e}")
            raise

        if result is BatchResult.MASK_FAILURE:
            self.engine.logger.error(
                "Unable to create masks from the source images.<br>"
                "At least one map type needs a transparent or single-colour "
                "background so the islands can be told apart —<br>"
                "re-export with padding/dilation off (or a transparent "
                "background) instead of edge-to-edge."
            )
            self.ui.footer.finish_progress(
                "Mask creation failed — see message panel for details."
            )
        else:
            # Clickable link (LoggingMixin.log_link) so the user can jump
            # straight to the results; routed to the explorer by
            # _on_log_link_clicked. Truncate the *label*, not the href —
            # TextLayout.wrap_text never hard-wraps a word containing a tag, so an
            # untruncated path would force the box wider than the panel.
            link = self.engine.logger.log_link(
                ptk.truncate(output_dir, 60), "open", path=output_dir
            )
            # Report what the engine actually wrote, not the pre-flight
            # estimate — total_maps counts an auto-generated normal complement
            # the engine skips when the batch already carries that format, so
            # it over-reports. written_paths is the post-run ground truth.
            written = len(self.engine.written_paths)
            # ONE closing record: "COMPLETED." plus a separate "Wrote N…" line
            # rendered as two paragraphs saying one thing.
            self.engine.logger.log_box(
                "COMPLETED",
                [
                    f"Maps written : {written}",
                    f"Layers       : {total_layers}",
                    f"Output       : {link}",
                ],
                level="SUCCESS",
            )
            self.ui.footer.finish_progress(f"Wrote {written} map(s) to {output_dir}")
