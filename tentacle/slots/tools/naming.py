# !/usr/bin/python
# coding=utf-8
"""Naming: batch find / rename / convert-case / strip-chars / suffix-by-location /
suffix-by-type, each with an option box (▸).

One Slots class for both hosts over the host toolkit's ``Naming`` engine
(``self.tk``). The header ``Scope`` combo governs every operation:
``Selection`` / ``Scene`` act on scene objects through the engine, ``Directory``
/ ``Files`` on files (the name operations — Find, Rename, Convert Case, Strip
Chars — run on file stems through :class:`pythontk.FileNaming`; the two
scene-only suffix operations report that they do not apply). A file scope opens
a browser on Find; the matched files become the working set the other
operations act on. ``Base Names`` (file scopes only) holds each file's
texture-map suffix and UDIM tile back so one operation carries a whole texture
set. ``Dry Run`` (under the scope) previews every operation and arms the
footer's ``Apply`` button, which commits exactly what was previewed.

Every operation reports into the output panel (``txt002``) through the engine's
logger, which this class redirects into the panel with clickable select-links.
"""

import contextlib
import os
from functools import partial
from typing import List

import pythontk as ptk

from tentacle import Slots


class NamingSlots(Slots):
    SCOPES = ("Selection", "Scene", "Directory", "Files")

    # Suffix-by-type option box: display groups of (engine keyword, field
    # objectName). uitk's NamingConventionEditor builds these rows. Both hosts'
    # engines take these keywords (their SUFFIX_BINDINGS pair each one with a
    # convention key). The objectNames are persisted user settings: never
    # renumber them.
    SUFFIX_GROUPS = (
        (
            "Transforms",
            (
                ("group_suffix", "tb003_txt000"),
                ("locator_suffix", "tb003_txt001"),
                ("joint_suffix", "tb003_txt002"),
                ("ik_handle_suffix", "tb003_txt008"),
                ("constraint_suffix", "tb003_txt014"),
            ),
        ),
        (
            "Shapes",
            (
                ("mesh_suffix", "tb003_txt003"),
                ("nurbs_curve_suffix", "tb003_txt004"),
                ("nurbs_surface_suffix", "tb003_txt009"),
                ("camera_suffix", "tb003_txt005"),
                ("light_suffix", "tb003_txt006"),
            ),
        ),
        (
            "Deformers",
            (
                ("cluster_suffix", "tb003_txt010"),
                ("lattice_suffix", "tb003_txt011"),
                ("skin_cluster_suffix", "tb003_txt012"),
                ("blend_shape_suffix", "tb003_txt013"),
            ),
        ),
        (
            "Shading",
            (
                ("material_suffix", "tb003_txt015"),
                ("shading_group_suffix", "tb003_txt016"),
                ("texture_suffix", "tb003_txt017"),
            ),
        ),
        (
            "Scene",
            (
                ("display_layer_suffix", "tb003_txt007"),
                ("set_suffix", "tb003_txt018"),
            ),
        ),
    )
    SUFFIX_FIELDS = {kw: name for _g, fields in SUFFIX_GROUPS for kw, name in fields}

    # Convention entries with no scene-node counterpart: editable here (this
    # panel is the front door to the shared convention) but never part of the
    # Suffix By Type *operation*, which renames nodes. Deliberately NOT in
    # SUFFIX_GROUPS -- that table builds the engine kwargs, and there is no
    # ``lightmap_suffix`` keyword to build. objectNames are persisted user
    # settings: never renumber them.
    CONVENTION_GROUPS = (
        (
            "Assets",
            (
                ("lightmap", "tb003_txt019"),
                ("packedTexture", "tb003_txt020"),
                ("control", "tb003_txt021"),
            ),
        ),
    )

    msg_intro = (
        "<u>Naming</u><br>• Pick a <b>Scope</b> in the header menu: the current "
        "selection, the whole scene, or files on disk.<br>• <b>Find</b> lists matches "
        "(and selects them, or browses for files); the other operations report "
        "every <code>old → new</code> change here.<br>• Tick <b>Dry Run</b> to "
        "preview any operation without changing anything, then press "
        "<b>Apply</b> in the footer to commit what you previewed."
    )

    def __init__(self, switchboard):
        super().__init__(switchboard)
        self.ui = self.sb.loaded_ui.naming
        self._files: List[str] = []  # working set for the Directory / Files scopes
        self._last_dir = ""
        self._pending = None  # the live call an armed Apply button would make

        self.ui.txt002.setText(self.msg_intro)
        self.ui.txt002.restore_state = False  # a report, not a setting

        # Route the engine's report (old → new groups, summaries, warnings) and
        # this panel's own lines into the output panel: one logger, the
        # engine's. setup_logging_redirect is what enables the clickable
        # action:// select-links on object names.
        logger = self.logger
        logger.hide_logger_name(True)
        logger.set_text_handler(self.sb.registered_widgets.TextEditLogHandler)
        logger.setup_logging_redirect(self.ui.txt002)
        if hasattr(self.ui.txt002, "anchorClicked"):
            self.ui.txt002.anchorClicked.connect(self._on_log_link_clicked)

        self._apply_btn = self._add_apply_button()

    @property
    def logger(self):
        """The host engine's logger (``Naming.logger``): what the operations
        report through, and so where this panel reports too."""
        return self.tk.Naming.logger

    def _on_log_link_clicked(self, url) -> None:
        """Dispatch clickable ``action://`` links from the output panel."""
        self.tk.UiUtils.dispatch_log_link(url, self.logger)

    # ------------------------------------------------------------------
    # Header
    # ------------------------------------------------------------------

    def header_init(self, widget):
        """Configure header menu with tool description and workflow instructions."""
        # Gesture-scoped window: pin button + auto-hide on key_show release.
        widget.config_buttons("menu", "collapse", "pin")
        widget.menu.add("Separator", setTitle="Scope")
        widget.menu.add(
            "QComboBox",
            addItems=list(self.SCOPES),
            setObjectName="cmb_scope",
            setToolTip=self.sb.tooltip.fmt(
                title="Scope",
                body="What every operation acts on.",
                bullets=[
                    "<b>Selection</b> — the current selection.",
                    "<b>Scene</b> — every renameable object in the scene (Maya "
                    "leaves out its default and read-only nodes, and shapes: a "
                    "shape follows its transform).",
                    "<b>Directory</b> — the files in a directory you pick "
                    "(not its sub-directories).",
                    "<b>Files</b> — files you pick.",
                ],
                notes=[
                    "With a file scope, <b>Find</b> opens the browser and the "
                    "matched files become the working set for Rename, Convert "
                    "Case and Strip Chars. Only the file name is changed — never "
                    "the extension. Suffix By Type / Location are scene-only.",
                ],
            ),
        )
        widget.menu.add(
            "QCheckBox",
            setText="Base Names",
            setObjectName="chk_base_names",
            setToolTip=self.sb.tooltip.fmt(
                title="Base Names",
                body="Act on each file's <b>base name</b> — its texture-map "
                "suffix (<code>_Normal</code>, <code>-basecolor</code>, "
                "<code>_ORM</code>, …) and UDIM tile are held back and "
                "re-attached, so one operation carries a whole texture set and "
                "every map keeps the token that identifies it.",
                notes=[
                    "File scopes only (a scene name has no map-type suffix); "
                    "the option is disabled in the Selection / Scene scopes.",
                    "A name with no recognized map suffix is untouched, so a "
                    "mixed directory is safe.",
                ],
            ),
        )
        widget.menu.add(
            "QCheckBox",
            setText="Dry Run",
            setObjectName="chk_dry_run",
            setToolTip=self.sb.tooltip.fmt(
                title="Dry Run",
                body="Preview every operation in the output panel without "
                "renaming anything — scene objects and files alike.",
                notes=[
                    "A preview arms <b>Apply</b> in the footer: it commits the "
                    "exact plan you are looking at, even if the fields or the "
                    "selection have moved on since.",
                ],
            ),
        )
        # Base Names is meaningless outside a file scope; keep the control's
        # state honest rather than silently ignoring a ticked box.
        widget.menu.cmb_scope.currentTextChanged.connect(self._on_scope_changed)
        self._sync_scope_options()

        widget.set_help_text(
            self.sb.tooltip.fmt(
                title="Naming",
                body="Batch find, rename, and suffix scene objects or files. Each "
                "operation button has an option box (▸) for its parameters; the "
                "output panel at the bottom lists every change.",
                sections=[
                    (
                        "Operations",
                        [
                            "<b>Find</b> — select objects by name pattern "
                            "(wildcards or regex; case-sensitivity, locators-only "
                            "and regex toggles in the option box). With a file "
                            "scope it opens the browser and lists the matches.",
                            "<b>Rename</b> — replace matched names with a new "
                            "pattern. Option box: retain a defined type suffix.",
                            "<b>Convert Case</b> — upper / lower / title / "
                            "capitalize / swapcase the names.",
                            "<b>Strip Chars</b> — remove leading or trailing "
                            "characters.",
                            "<b>Suffix By Location</b> — auto-number objects by "
                            "distance from a reference point (alphabetical or "
                            "integer). Scene only.",
                            "<b>Suffix By Type</b> — append type-based suffixes "
                            "(<code>_GEO</code>, <code>_GRP</code>, "
                            "<code>_JNT</code>, …). Suffix strings are "
                            "editable in the option box. Scene only.",
                        ],
                    ),
                    (
                        "Header menu",
                        [
                            "<b>Scope</b> — <i>Selection</i>, <i>Scene</i>, "
                            "<i>Directory</i> or <i>Files</i>. Applies to every "
                            "operation.",
                            "<b>Base Names</b> — act on the base name, holding "
                            "back each file's texture-map suffix and UDIM tile. "
                            "File scopes only.",
                            "<b>Dry Run</b> — preview any operation in the output "
                            "panel; nothing is renamed. <b>Apply</b> then appears "
                            "in the footer to commit the preview.",
                        ],
                    ),
                ],
                notes=[
                    "A scene operation is one undo step; a file rename is not "
                    "undoable.",
                    "In Blender a locator is an Empty, and the Suffix By Type "
                    "rows for Maya-only node types are greyed out.",
                ],
            )
        )

    # ------------------------------------------------------------------
    # Scope helpers
    # ------------------------------------------------------------------

    @property
    def scope(self) -> str:
        return self.ui.header.menu.cmb_scope.currentText()

    @property
    def dry_run(self) -> bool:
        return self.ui.header.menu.chk_dry_run.isChecked()

    @property
    def file_scope(self) -> bool:
        return self.scope in ("Directory", "Files")

    @property
    def base_names(self) -> bool:
        """Operate on map-suffix-free base names — file scopes only."""
        return self.file_scope and self.ui.header.menu.chk_base_names.isChecked()

    def _sync_scope_options(self) -> None:
        """Enable the file-only header options for the current scope."""
        self.ui.header.menu.chk_base_names.setEnabled(self.file_scope)

    def _on_scope_changed(self, *_args) -> None:
        """A new scope re-gates the file-only options and stales any armed preview."""
        self._sync_scope_options()
        self._disarm_apply()

    # ------------------------------------------------------------------
    # Dry run / Apply
    # ------------------------------------------------------------------

    def _add_apply_button(self):
        """The footer button that commits the last dry run; hidden until one is armed."""
        footer = getattr(self.ui, "footer", None)
        if footer is None or not hasattr(footer, "add_action_button"):
            return None
        button = footer.add_action_button(
            text="Apply",
            icon_name="check",
            tooltip="Apply the changes the last dry run previewed.",
            callback=self._apply_dry_run,
        )
        button.setVisible(False)
        return button

    def _arm_apply(self, commit) -> None:
        """Hold *commit* — the identical live call — for the Apply button."""
        self._pending = commit
        if self._apply_btn is not None:
            self._apply_btn.setVisible(True)
            self.ui.footer.setText("Dry run — Apply to commit", level="warning")

    def _disarm_apply(self) -> None:
        """Drop any armed preview and hide the Apply button.

        Gated on having been armed, not on ``isVisible()`` — a child of an
        unshown window reads as invisible however it was set, which would leave
        the footer note behind.
        """
        was_armed = self._pending is not None
        self._pending = None
        if self._apply_btn is not None and was_armed:
            self._apply_btn.setVisible(False)
            self.ui.footer.setText("")

    def _apply_dry_run(self) -> None:
        """Commit the plan the last dry run previewed."""
        commit = self._pending
        self._begin()  # the applied run is an operation of its own, reported as one
        if commit is not None:
            commit()

    def _begin(self) -> None:
        """Start a new operation: clear the report and drop any pending preview.

        One rule in one place — a new operation always supersedes the last dry
        run's plan, including when it goes on to abort with nothing in scope.
        """
        self.ui.txt002.clear()
        self._disarm_apply()

    def _run(
        self, operation, targets, *args, before=None, after=None, undo=None, **kwargs
    ):
        """Run one naming operation, arming the Apply button when it is a dry run.

        The armed call is the same closure the live branch runs, over a frozen
        copy of *targets* and the arguments as they were previewed — so Apply
        commits the report on screen even if the fields, the selection or the
        option boxes have moved on since. It is armed whenever a preview ran:
        applying a plan that turned out to change nothing is a no-op that
        reports as one.

        ``before`` / ``after`` are the scope's own hooks — logging the working
        set's directories, following the renames. They belong to the call rather
        than beside it, so an applied run reports exactly like a live one.
        ``undo`` names the undo step a live scene operation is (one per click in
        both hosts); a dry run changes nothing and records nothing, and a file
        rename is no scene change.
        """

        def run(plan, items):
            if before is not None:
                before()
            step = (
                self.tk.CoreUtils.undo_chunk(undo)
                if undo and not plan
                else contextlib.nullcontext()
            )
            with step:
                result = operation(items, *args, dry_run=plan, **kwargs)
            if after is not None and not plan:
                after(result)
            return result

        if not self.dry_run:
            return run(False, targets)
        # Arm only once the preview has actually reported: an operation that
        # raised must not leave a button offering to commit it.
        result = run(True, targets)
        self._arm_apply(partial(run, False, list(targets)))
        return result

    def _scene_targets(self) -> List:
        """Scene objects in scope, or an empty list (already reported)."""
        scene = self.scope == "Scene"
        objects = self.tk.Naming.scope_objects(scene=scene)
        if not objects:
            self.logger.warning(
                "The scene has no renameable objects."
                if scene
                else "Nothing selected. Select objects, or set Scope to 'Scene' "
                "in the header menu to operate on the whole scene."
            )
        return objects

    def _browse(self) -> List[str]:
        """Open the Directory / Files browser; returns the chosen files (expanded).

        Starts where the last browse ended, else at the host's workspace root
        (empty, the dialog's own default, when there is none)."""
        start = self._last_dir or self.tk.EnvUtils.workspace_root()
        if self.scope == "Directory":
            chosen = self.sb.dir_dialog(
                title="Naming — select a directory", start_dir=start
            )
            paths = [chosen] if chosen else []
        else:
            paths = (
                self.sb.file_dialog(title="Naming — select files", start_dir=start)
                or []
            )
        files = ptk.FileNaming.expand(paths)
        if files:
            self._last_dir = os.path.dirname(files[0])
        return files

    def _file_targets(self, browse: bool = False) -> List[str]:
        """The file working set, browsing for one when asked or when there is none."""
        if not browse:  # drop files renamed or removed outside the tool
            self._files = [f for f in self._files if os.path.isfile(f)]
        if browse or not self._files:
            self._files = self._browse()
            if not self._files:
                self.logger.warning("No files chosen.")
        return self._files

    def _log_directories(self, files: List[str]) -> None:
        """One clickable directory line per distinct directory in *files*."""
        for d in sorted({os.path.dirname(f) for f in files}):
            self.logger.info(
                f"Directory: {ptk.LoggingMixin.log_link(d, 'open', path=d)}"
            )

    def _run_on_files(self, operation, *args, **kwargs) -> bool:
        """Run a ``ptk.FileNaming`` operation on the working set when a file scope is active.

        Returns True when the file scope handled the call (even with nothing
        chosen), so the caller skips its scene branch.
        """
        if not self.file_scope:
            return False
        files = self._file_targets()
        if files:
            self._run(
                operation,
                files,
                *args,
                before=partial(self._log_directories, files),
                after=self._follow_renames,
                base_names=self.base_names,
                logger=self.logger,
                **kwargs,
            )
        return True

    def _follow_renames(self, result) -> None:
        """Point the working set at the new paths after a live rename."""
        if result:
            renamed = dict(result)
            self._files = [renamed.get(f, f) for f in self._files]

    def _scene_only(self, operation: str) -> bool:
        """True (after reporting) when a scene-only operation was run in a file scope."""
        if self.file_scope:
            self.logger.notice(
                f"{operation} applies to scene objects only — set Scope to "
                "'Selection' or 'Scene' in the header menu."
            )
            return True
        return False

    @property
    def valid_suffixes(self):
        """The current Suffix By Type strings (non-empty), from the tb003 option box."""
        try:
            m = self.ui.tb003.option_box.menu
            suffixes = [getattr(m, name).text() for name in self.SUFFIX_FIELDS.values()]
            return [s for s in suffixes if s]
        except (AttributeError, RuntimeError):
            # Fallback if widgets not initialized or accessed before tb003 exists
            return [affix for _kw, affix, _l, _k in self.tk.Naming.SUFFIX_TYPES]

    # ------------------------------------------------------------------
    # Find
    # ------------------------------------------------------------------

    def txt000_init(self, widget):
        """Initialize Find"""
        widget.setToolTip(
            self.sb.tooltip.fmt(
                title="Search by Name",
                bullets=[
                    "<code>startswith*</code> — names that start with the given characters.",
                    "<code>*endswith</code> — names that end with the given characters.",
                    "<code>*contains*</code> — names that contain the given characters.",
                    "Combine terms with <code>|</code> for multiple searches "
                    "(e.g. <code>start*|*end</code>).",
                ],
                notes=[
                    "Scene scopes search the whole scene and select the matches; "
                    "file scopes open the browser and keep the matches as the "
                    "working set (an empty pattern keeps every chosen file).",
                    "Enable <b>Regular Expression</b> in the option box for advanced "
                    "patterns. Capture groups defined here can be referenced from the "
                    "Rename field as <code>\\1</code>, <code>\\2</code> or "
                    "<code>\\g&lt;name&gt;</code>.",
                    "<b>Ignore Case</b> in the option box makes the search case-insensitive.",
                    "Each pipe-separated term supplies the text that Rename replaces, "
                    "so terms here pair positionally with the Rename field's.",
                ],
            )
        )
        widget.restore_state = False  # Don't persist the search text across sessions.
        widget.option_box.menu.setTitle("Find")
        # Add clear button to the menu option box
        widget.option_box.clear_option = True
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Ignore Case",
            setObjectName="chk000",
            setToolTip="Search case insensitive.",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Regular Expression",
            setObjectName="chk001",
            setToolTip="When checked, regular expression syntax is used instead of the default '*' and '|' wildcards.",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Locators Only",
            setObjectName="chk007",
            setToolTip="Limit the search to locators (in Blender: Empties); "
            "scene scopes only.",
        )
        widget.option_box.set_action(
            callback=widget.returnPressed.emit,
            icon="search",
            tooltip="Find matching objects (same as pressing Enter).",
        )

    @Slots.Signals("returnPressed")
    def txt000(self, widget):
        """Find: select scene objects (or browse for files) whose name matches the pattern."""
        # An asterisk denotes startswith*, *endswith, *contains*
        menu = widget.option_box.menu
        regex = menu.chk001.isChecked()
        ign_case = menu.chk000.isChecked()
        locators_only = menu.chk007.isChecked()
        text = widget.text()

        self._begin()
        if self.file_scope:
            files = self._file_targets(browse=True)
            if not files:
                return
            hits = ptk.FileNaming.find(
                files,
                text,
                regex=regex,
                ignore_case=ign_case,
                base_names=self.base_names,
            )
            self._files = hits
            self._log_directories(files)
            self._report_found(
                "Find", "file", text, [os.path.basename(f) for f in hits], len(files)
            )
            return

        if not text:
            return
        naming = self.tk.Naming
        found, searched = naming.select_by_name(
            text, regex=regex, ignore_case=ign_case, locators_only=locators_only
        )
        self._report_found(
            "Find",
            "locator" if locators_only else "object",
            text,
            [naming.select_link(o) for o in found],
            searched,
        )

    def _report_found(self, title, unit, text, items, total) -> None:
        """Report a Find result as one group + footer line."""
        plural = unit if len(items) == 1 else f"{unit}s"
        pattern = f" matching '{text}'" if text else ""
        if not items:
            self.logger.warning(f"No {plural}{pattern} (searched {total}).")
            self.ui.footer.setText(f"No {plural}{pattern}")
            return
        shown = items[: ptk.RenamePlan.MAX_REPORT_ITEMS]
        if len(items) > len(shown):
            shown.append(f"… +{len(items) - len(shown)} more")
        self.logger.log_group(
            f"{title} — {len(items)} of {total} {plural}{pattern}",
            shown,
            level="SUCCESS",
        )
        self.ui.footer.setText(f"Found {len(items)} {plural}{pattern}")

    # ------------------------------------------------------------------
    # Rename
    # ------------------------------------------------------------------

    def txt001_init(self, widget):
        """Initialize Rename"""
        widget.setToolTip(
            self.sb.tooltip.fmt(
                title="Rename",
                body="The new name pattern for the matched objects or files. The "
                "asterisk marks the part of the existing name that is <b>kept</b> — "
                "one asterisk replaces that side, a doubled one keeps the whole name "
                "and adds to it.",
                bullets=[
                    "<code>string</code> — replace the whole name.",
                    "<code>*string*</code> — replace only the part matched by Find.",
                    "<code>string*</code> — replace the prefix (drops everything through the match).",
                    "<code>*string</code> — replace the suffix (drops everything from the match on).",
                    "<code>string**</code> — add a prefix, keeping the whole name.",
                    "<code>**string</code> — add a suffix, keeping the whole name.",
                    "empty — strip the part matched by Find.",
                ],
                notes=[
                    "Pipe-separated terms pair with Find's: <code>*_L|*_R</code> in "
                    "Find with <code>*_lt|*_rt</code> here renames each side "
                    "differently. A single term applies to every Find term.",
                    "With <b>Regular Expression</b> enabled, Find's capture groups "
                    "are available here as <code>\\1</code>, <code>\\2</code> or "
                    "<code>\\g&lt;name&gt;</code>.",
                    "<b>Replace prefix</b> / <b>replace suffix</b> fall back to "
                    "adding when Find is empty or does not appear in a name.",
                ],
            )
        )
        widget.restore_state = False  # Don't persist the rename text across sessions.
        widget.option_box.menu.setTitle("Rename")
        # Add clear button to the menu option box
        widget.option_box.clear_option = True
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Retain Defined Suffix",
            setObjectName="chk002",
            setToolTip=(
                "Carry the selected object's existing type suffix over to the new "
                "name — only a suffix defined in <b>Suffix By Type</b> counts. A name "
                "with no defined suffix is left alone, and a new name that still "
                "carries the suffix is never given a second copy."
            ),
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Ignore Find",
            setObjectName="chk008",
            setToolTip="Ignore the find field and rename all matched objects.",
        )
        widget.option_box.set_action(
            callback=widget.returnPressed.emit,
            icon="edit",
            tooltip="Rename matched objects (same as pressing Enter).",
        )

    # The LineEdit text parameter is not emitted on `returnPressed`
    @Slots.Signals("returnPressed")
    def txt001(self, widget):
        """Rename: rename matched objects or files (find → replace, with regex / suffix options)."""
        # An asterisk denotes startswith*, *endswith, *contains*
        find_menu = self.ui.txt000.option_box.menu
        find = self.ui.txt000.text()
        to = widget.text()
        regex = find_menu.chk001.isChecked()
        ign_case = find_menu.chk000.isChecked()
        retain_suffix = widget.option_box.menu.chk002.isChecked()
        ignore_find = widget.option_box.menu.chk008.isChecked()

        # Get current valid suffixes from property if retain_suffix is enabled
        valid_suffixes = self.valid_suffixes if retain_suffix else None
        fltr = "" if ignore_find else find

        self._begin()
        if self._run_on_files(
            ptk.FileNaming.rename,
            to,
            fltr,
            regex=regex,
            ignore_case=ign_case,
            retain_suffix=retain_suffix,
            valid_suffixes=valid_suffixes,
        ):
            return

        objects = self._scene_targets()
        if not objects:
            return
        self._run(
            self.tk.Naming.rename,
            objects,
            to,
            fltr,
            undo="Rename",
            regex=regex,
            ignore_case=ign_case,
            retain_suffix=retain_suffix,
            valid_suffixes=valid_suffixes,
        )

    # ------------------------------------------------------------------
    # Convert Case
    # ------------------------------------------------------------------

    def tb000_init(self, widget):
        """Initialize Convert Case"""
        widget.option_box.menu.setTitle("Convert Case")
        widget.option_box.menu.add(
            "QComboBox",
            addItems=["capitalize", "upper", "lower", "swapcase", "title"],
            setObjectName="cmb001",
            setToolTip="Set desired python case operator.",
        )

    def tb000(self, widget):
        """Convert Case"""
        case = widget.option_box.menu.cmb001.currentText()

        self._begin()
        if self._run_on_files(ptk.FileNaming.set_case, case):
            return

        objects = self._scene_targets()
        if not objects:
            return
        self._run(self.tk.Naming.set_case, objects, case, undo="Convert Case")

    # ------------------------------------------------------------------
    # Suffix By Location
    # ------------------------------------------------------------------

    def tb001_init(self, widget):
        """Initialize Suffix By Location"""
        widget.option_box.menu.setTitle("Suffix By Location")
        # Reference point is a choice between two named origins, not a modifier.
        ref = widget.option_box.menu.add(
            "QComboBox",
            setObjectName="cmb_reference",
            setToolTip="Scene Origin: measure from the world origin (0,0,0).\nFirst Object: measure from the first selected object.",
        )
        ref.addItems(["Scene Origin", "First Object"])
        ref.setCurrentText("Scene Origin")  # preserve prior default (checkbox off)
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Alphabetical",
            setObjectName="chk005",
            setToolTip="Use an alphabet character as a suffix when there is less than 26 objects, else use integers.",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Strip Trailing Integers",
            setObjectName="tb001_chk002",
            setChecked=True,
            setToolTip="Strip any trailing integers. ie. '123' of 'cube123'",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Strip Defined Suffixes",
            setObjectName="chk003",
            setChecked=True,
            setToolTip="Strip any suffixes found in the 'Suffix By Type' settings (e.g. '_GRP', '_LOC').",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Independent Groups",
            setObjectName="tb001_chk007",
            setToolTip="Group objects by name type and suffix them independently.",
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Reverse",
            setObjectName="chk004",
            setToolTip="Reverse the naming order. (Farthest object first)",
        )

    def tb001(self, widget):
        """Suffix By Location: number the objects in scope by their distance from
        the reference point (the engine keeps only what has a location: in
        Maya, the transforms)."""
        menu = widget.option_box.menu
        first_obj_as_ref = menu.cmb_reference.currentText() == "First Object"
        alphabetical = menu.chk005.isChecked()
        strip_trailing_ints = menu.tb001_chk002.isChecked()
        strip_defined_suffixes = menu.chk003.isChecked()
        reverse = menu.chk004.isChecked()
        independent_groups = menu.tb001_chk007.isChecked()

        self._begin()
        if self._scene_only("Suffix By Location"):
            return
        objects = self._scene_targets()
        if not objects:
            return
        self._run(
            self.tk.Naming.append_location_based_suffix,
            objects,
            undo="Suffix By Location",
            first_obj_as_ref=first_obj_as_ref,
            alphabetical=alphabetical,
            strip_trailing_ints=strip_trailing_ints,
            strip_defined_suffixes=strip_defined_suffixes,
            valid_suffixes=self.valid_suffixes,
            reverse=reverse,
            independent_groups=independent_groups,
        )

    # ------------------------------------------------------------------
    # Strip Chars
    # ------------------------------------------------------------------

    def tb002_init(self, widget):
        """Initialize Strip Chars"""
        widget.option_box.menu.setTitle("Strip Chars")
        widget.option_box.menu.add(
            "QSpinBox",
            setPrefix="Num Chars:",
            setObjectName="s000",
            setValue=1,
            setToolTip="The number of characters to delete.",
        )
        widget.option_box.menu.add(
            "QComboBox",
            addItems=["Leading", "Trailing"],
            setCurrentText="Trailing",
            setObjectName="cmb002",
            setToolTip="Which end of the name to delete characters from.",
        )

    def tb002(self, widget):
        """Strip Chars: remove a number of leading/trailing characters from the names in scope."""
        kwargs = {
            "num_chars": widget.option_box.menu.s000.value(),
            "trailing": widget.option_box.menu.cmb002.currentText() == "Trailing",
        }
        self._begin()
        if self._run_on_files(ptk.FileNaming.strip_chars, **kwargs):
            return

        objects = self._scene_targets()
        if not objects:
            return
        self._run(self.tk.Naming.strip_chars, objects, undo="Strip Chars", **kwargs)

    # ------------------------------------------------------------------
    # Suffix By Type — convention editor
    # ------------------------------------------------------------------
    #
    # These fields are the front door to ``pythontk.NamingConvention``, the one
    # definition of "what affix marks a mesh / a material / a group" that every
    # other tool in the toolset reads. The editor is uitk's
    # ``NamingConventionEditor``; this panel supplies only its data: the rows
    # (SUFFIX_GROUPS by convention key, then CONVENTION_GROUPS), their tooltips
    # and the rows the host cannot apply (its engine's UNSUPPORTED_TYPES).

    def _convention_groups(self):
        """The editor's display groups: ``((title, ((key, objectName), ...)), ...)``.

        The node-type rows are SUFFIX_GROUPS with each engine keyword mapped to
        its convention key (the engine's ``SUFFIX_BINDINGS``); the edit-only
        rows follow.
        """
        keys = {kw: ck for kw, ck, _tk in self.tk.Naming.SUFFIX_BINDINGS}
        node_rows = tuple(
            (group, tuple((keys[kw], name) for kw, name in fields))
            for group, fields in self.SUFFIX_GROUPS
        )
        return node_rows + tuple(self.CONVENTION_GROUPS)

    @staticmethod
    def _convention_tooltip(key, label):
        """A row's tooltip: a node-type row, or an edit-only (artifact) row."""
        if key in ptk.NamingConvention.ARTIFACT_KEYS:
            return (
                f"Affix for {label.lower()}s — part of the <b>shared naming "
                "convention</b>, read by the tools that write them.<br><br>Not a "
                "scene node type, so <i>Suffix By Type</i> never renames anything "
                "with it; this row exists so the convention can be edited in one "
                "place."
            )
        return (
            f"Affix for {label.lower()}s. Leave empty to skip this type.<br><br>"
            "This is the <b>shared naming convention</b> — every tool that offers "
            "a <i>Scene</i> affix mode reads what you set here.<br>"
            "The button beside the field sets placement: Auto (a leading '_' "
            "trails, a trailing '_' leads) / Suffix / Prefix."
        )

    def tb003_init(self, widget):
        """Initialize Suffix By Type — the editor for the shared naming convention."""
        menu = widget.option_box.menu
        menu.setTitle("Suffix By Type")
        self._convention_editor = self.sb.NamingConventionEditor(
            menu,
            self._convention_groups(),
            tooltip=self._convention_tooltip,
            disabled=self.tk.Naming.UNSUPPORTED_TYPES,
            logger=self.logger,
        ).build()
        menu.add(
            "Separator",
            setTitle="Suffix Options",
        )
        menu.add(
            "QCheckBox",
            setText="Strip Trailing Padding",
            setObjectName="tb003_chk004",
            setChecked=True,
            setToolTip="Strip orphaned trailing underscores and, only when underscores were at the end, also strip exposed trailing digits. Preserves intentional '_02' numbering.",
        )
        menu.add(
            "QCheckBox",
            setText="Strip Trailing Integers",
            setObjectName="tb003_chk002",
            setChecked=False,
            setToolTip="Strip any trailing integers. ie. '123' of 'cube123'",
        )
        menu.add(
            "QCheckBox",
            setText="Strip Trailing Underscores",
            setObjectName="tb003_chk003",
            setChecked=False,
            setToolTip="Strip any trailing underscores after stripping integers (e.g. 'cube_01_' -> 'cube').",
        )

    def tb003(self, widget):
        """Suffix By Type"""
        m = widget.option_box.menu
        # Spelling AND placement: a row set to Prefix has to reach the engine as
        # a prefix, or the picker beside the field would be decorative.
        kwargs = {
            kw: getattr(m, name).text() for kw, name in self.SUFFIX_FIELDS.items()
        }
        kwargs["affix_modes"] = {
            kw: getattr(m, name).option_box.affix_mode
            for kw, name in self.SUFFIX_FIELDS.items()
        }
        kwargs.update(
            strip_trailing_ints=m.tb003_chk002.isChecked(),
            strip_trailing_underscores=m.tb003_chk003.isChecked(),
            strip_trailing_padding=m.tb003_chk004.isChecked(),
        )
        self._begin()
        if self._scene_only("Suffix By Type"):
            return
        objects = self._scene_targets()
        if not objects:
            return
        self._run(
            self.tk.Naming.suffix_by_type, objects, undo="Suffix By Type", **kwargs
        )
