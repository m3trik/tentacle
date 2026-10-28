# !/usr/bin/python
# coding=utf-8
"""Texture Path Editor: inspect and fix the scene's texture paths.

One Slots class for both hosts over the host toolkit's ``TexturePathEditor``
(``self.tk``), composed, never inherited. The engine owns the scene: the rows
(one per texture node -- Maya's file node, Blender's image datablock -- with its
material, stored path and verdict), the commands (Set Directory, Find & Copy,
Normalize Paths, Make Paths Absolute, Resolve Missing Textures), the renames with
Keep Names In Sync, selection, deletion and the lightmap dependencies the bake
markers name. This class owns the table, the header and row menus, the Find &
Copy form, and what the user is told. The host's words (Shader / File Node vs
Material / Texture) are the engine's ``LABELS``; the Exclude Arnold Nodes toggle
appears where the engine has Arnold nodes to exclude (``EXCLUDE_ARNOLD``).
"""

import contextlib
import os
import posixpath
from functools import partial

import pythontk as ptk

from tentacle import Slots


class TexturePathEditorSlots(Slots, ptk.LoggingMixin):
    #: The header menu's option-box buttons, built in ``header_init`` and filled
    #: by their ``*_init`` slots: no ``.ui`` declares them.
    RUNTIME_WIDGETS = (
        "tb_set_texture_directory",
        "tb_normalize_paths",
        "tb_resolve_missing_textures",
    )

    #: Selection payload keys -> the table's columns.
    _ROW_SELECTION_COLUMNS = {"shader": 0, "path": 1, "file_node": 2}

    #: Shader-column label of a lightmap row whose objects wear no material.
    _LIGHTMAP_ROW_LABEL = "<lightmap>"

    # Default displayed length of a texture path while "Truncate Texture Paths"
    # is on (its option box sets the length). Cut with ``mode="path"``: whole
    # middle components go, the root stays at the front and the filename at the
    # back; ``_PATH_TRUNCATE_HEAD`` caps the front to that root -- what
    # identifies a texture is the end of its path.
    _PATH_TRUNCATE_LENGTH = 96
    _PATH_TRUNCATE_HEAD = 1

    #: The fact columns -> the ``ImgUtils.texture_facts`` field each shows. Read
    #: only while the column shows.
    _INFO_COLUMNS = {3: "bytes", 4: "dimensions", 5: "mode"}
    #: Hidden until shown from the table header's menu: the node column, rarely
    #: needed beside its path, and the file facts.
    _COLUMNS_HIDDEN_BY_DEFAULT = (2, 3, 4, 5)

    # Option-box combo items (label, mode key). Order is the contract: each
    # combo is filled in this order and saves its INDEX, which reads back here.
    _RELOCATE_MODE_ITEMS = (
        ("Leave textures in place (path only)", "rewrite"),
        ("Copy textures to new directory", "copy"),
        ("Move textures to new directory", "move"),
    )
    _NORMALIZE_MODE_ITEMS = (
        ("Leave external textures untouched", "rewrite"),
        ("Copy external textures into the project", "copy"),
        ("Move external textures into the project", "move"),
    )
    _FIND_MODE_ITEMS = (("Copy", "copy"), ("Move", "move"))
    #: Resolve Missing's option-box checkboxes, by strategy.
    _RESOLVE_CHECKBOXES = {
        "stem": "chk_stem",
        "texture": "chk_texture",
        "fuzzy": "chk_fuzzy",
    }

    # Colour markers leading the Find & Copy source / destination rows and the
    # destination pickers' captions. A native picker draws its caption as plain
    # text but renders emoji in colour, so the marker carries colour without
    # giving up the shell browser. Blue/amber survives the common colour-vision
    # deficiencies, and the words carry the meaning anyway.
    _DIALOG_MARK_SOURCE = "🔵"
    _DIALOG_MARK_DEST = "🟠"

    def __init__(self, switchboard):
        super().__init__(switchboard)
        self.ui = self.sb.loaded_ui.texture_path_editor
        #: The host's engine: rows, commands and the in-session previous paths.
        self.engine = self.tk.TexturePathEditor()
        self._refresh_pending = False
        self._browse_in_progress = False  # re-entry guard
        # Per refresh: lightmap rows by their path text (the one column every
        # selection payload carries), the stored paths' verdicts, the shaders
        # reading each node, and the shaders a cell may rename.
        self._lightmap_rows = {}
        self._path_state = {}
        self._node_materials = {}
        self._editable_shaders = set()
        self._over_long_paths = set()
        # Find & Copy is a tool window that stays open while it works, so it is
        # KEPT: reopening re-seeds its rows from live scene state rather than
        # throwing away the log being read and the size it was given. The scope
        # it is pointed at is captured when it opens -- the row selection can
        # change behind a modeless window, and a button naming a count must not
        # disagree with what it relocates.
        self._find_copy_panel = None
        self._find_copy_nodes = []
        self._find_copy_mode = "copy"
        self._find_copy_scope_label = ""
        self._find_copy_lightmaps = []
        self._footer_controller = self._create_footer_controller()

    @property
    def labels(self):
        """The host's words for the node and shader columns and row actions."""
        return self.engine.LABELS

    # ------------------------------------------------------------------
    # Header menu
    # ------------------------------------------------------------------

    def header_init(self, widget):
        """The header menu: General / Naming / Path Management / Selection.

        Plain action items are QPushButtons wired via ``clicked.connect``. The
        items with option-box flyouts (Set Directory, Normalize Paths, Resolve
        Missing Textures) are uitk ``PushButton`` (``tb_*``) auto-wired by name;
        their flyouts are filled by the matching ``*_init`` slots.
        """
        labels = self.labels
        widget.config_buttons("refresh", "menu", "collapse", "hide")
        widget.refresh_requested.connect(self.refresh_texture_table)

        widget.menu.add("Separator", setTitle="General")
        btn_open = widget.menu.add(
            "QPushButton",
            setText=f"Open {labels['texture_dir']}",
            setObjectName="btn_open_source_images",
            setToolTip="Open the project's texture folder in the file explorer.",
        )
        btn_open.clicked.connect(self.open_source_images)

        btn_reload = widget.menu.add(
            "QPushButton",
            setText="Reload Scene Textures",
            setObjectName="btn_reload_scene_textures",
            setToolTip=(
                "Re-read every scene texture from disk. Useful after editing "
                "textures externally or after Find & Copy / Normalize Paths "
                "relocates them."
            ),
        )
        btn_reload.clicked.connect(self.reload_scene_textures)

        chk_truncate = widget.menu.add(
            "QCheckBox",
            setText="Truncate Texture Paths",
            setObjectName="chk_truncate_paths",
            setChecked=False,
            setToolTip=(
                "Shorten long paths in the Texture Path column by dropping "
                "whole middle folders — the drive and its first directories "
                "stay readable at the front, the filename at the back.\n"
                "Display only — the cell still holds the full path, so edits, "
                "path commands and the tooltip are unaffected.\n"
                "Option box (▸): the length to shorten to."
            ),
        )
        chk_truncate.toggled.connect(lambda *_: self._apply_path_truncation())
        chk_truncate.option_box.menu.setTitle("Truncate Texture Paths")
        spn_length = chk_truncate.option_box.menu.add(
            "QSpinBox",
            setObjectName="spn_truncate_length",
            setPrefix="Length: ",
            setSuffix=" characters",
            setMinimum=24,
            setMaximum=400,
            setValue=self._PATH_TRUNCATE_LENGTH,
            setToolTip=(
                "How many characters a truncated path shows. Whole middle "
                "folders are dropped until it fits; the filename always stays."
            ),
        )
        spn_length.valueChanged.connect(lambda *_: self._apply_path_truncation())

        chk_warn_len = widget.menu.add(
            "QCheckBox",
            setText="Warn On Over-Long Paths",
            setObjectName="chk_warn_path_length",
            setChecked=True,
            setToolTip=(
                "Flag rows whose resolved path is longer than this OS accepts "
                f"({ptk.FileUtils.path_length_limit()} characters).\n"
                "Over-long paths fail late and opaquely — a texture the FBX "
                "exporter silently cannot embed, a copy that reports success "
                "and produced nothing — and a path that fits here still breaks "
                "on a machine without long paths enabled (260 characters)."
            ),
        )
        chk_warn_len.toggled.connect(lambda *_: self.refresh_texture_table())

        # Maya only: an Arnold preview shader owns a file node per texture.
        # Blender's rows are image datablocks, shared by reference and never
        # duplicated per renderer, so there is nothing to exclude there.
        if self.engine.EXCLUDE_ARNOLD:
            chk_exc_arnold = widget.menu.add(
                "QCheckBox",
                setText="Exclude Arnold Nodes",
                setObjectName="chk_exclude_arnold",
                setChecked=False,
                setToolTip=(
                    "Hide rows whose texture is used only by an Arnold shader.\n"
                    "An Arnold preview shader (Materials ▸ Arnold Preview "
                    "Shader) owns a dedicated file node per texture, so every "
                    "bridged material contributes a duplicate row for the same "
                    "image.\nA texture shared with a non-Arnold shader is "
                    "always shown."
                ),
            )
            chk_exc_arnold.toggled.connect(lambda *_: self.refresh_texture_table())

        chk_lightmaps = widget.menu.add(
            "QCheckBox",
            setText="Show Lightmap Dependencies",
            setObjectName="chk_show_lightmaps",
            setChecked=True,
            setToolTip=(
                "List the baked lightmaps the scene's bake markers name.\n"
                "A committed lightmap is a texture dependency with no texture "
                "node: the marker records the map and the folder it was baked "
                "into, and that folder goes stale when the project is "
                "reorganised or the scene is migrated — the export then ships "
                "unlit. Rows read red when the map is nowhere on disk and "
                "amber when it was found somewhere other than the recorded "
                "folder.\n"
                "Find & Copy relocates them with the textures and rewrites "
                "the markers; Normalize Paths / Make Paths Absolute re-spell "
                "the recorded folder (relative inside the project, so a "
                "teammate's copy on another drive resolves it); Select Broken "
                "Paths, Browse for File and a typed path apply too. Set "
                "Directory and Resolve Missing are texture-node only."
            ),
        )
        chk_lightmaps.toggled.connect(lambda *_: self.refresh_texture_table())

        widget.menu.add("Separator", setTitle="Naming")
        chk_sync = widget.menu.add(
            "QCheckBox",
            setText="Keep Names In Sync",
            setObjectName="chk_sync_names",
            setChecked=False,
            setToolTip=self.sb.tooltip.fmt(
                title="Keep Names In Sync",
                body="Renaming a material, a texture or its node renames the "
                "rest of its material to match: the material, every texture "
                "file it uses (on disk) and their nodes share one base name.",
                bullets=[
                    "<b>Material</b> — the base name with the material affix "
                    "(Maya: its shading group <i>…SG</i> and an Arnold "
                    "<i>…_ai</i> beside it follow).",
                    "<b>Textures</b> — the material's own texture set, each "
                    "keeping what follows its base name (map type, UDIM token, "
                    "extension): <i>rock_Base_Color.png</i> follows <i>stone</i> "
                    "as <i>stone_Base_Color.png</i>. Every node reading a "
                    "renamed file is repointed.",
                    "<b>Lightmap</b> — the set's baked lightmap "
                    "(<i>rock_Lightmap.exr</i>) follows, its bake markers "
                    "re-stamped.",
                    f"<b>{labels['file_node']}s</b> — named after their texture, "
                    "plus the suffix (Blender: an image keeps its file name, as "
                    "Blender names a loaded image, unless a suffix is set).",
                ],
                notes=[
                    "A texture or node follows only as a new base name "
                    "(<i>rock_Normal</i> → <i>stone_Normal</i>); a new map type "
                    "or another set's map is renamed alone.",
                    "Left alone: another set's map (an environment cube), any "
                    "file outside this project — another project may read it — "
                    "and whatever a linked library brings. Each is reported.",
                    "Planned whole first: a rename that would land on another "
                    "file stops the lot before anything changes.",
                    "One undo step, files included.",
                    "Option box (▸): the material affix and the node suffix.",
                ],
            ),
        )
        flyout = chk_sync.option_box.menu
        flyout.setTitle("Keep Names In Sync")
        shader_affix = flyout.add(
            self.sb.registered_widgets.LineEdit,
            setObjectName="txt_shader_affix",
        )
        shader_affix.option_box.set_affix(
            default="convention",
            convention_key="material",
            settings_key="texture_path_editor_shader_affix",
            on_change=lambda _mode, w=shader_affix: self._apply_shader_affix_hint(w),
        )
        self._apply_shader_affix_hint(shader_affix)
        flyout.add(
            self.sb.registered_widgets.LineEdit,
            setObjectName="txt_file_node_suffix",
            setPlaceholderText=f"{labels['file_node']} Suffix",
            setToolTip=(
                "Appended to a texture's name to name its node (e.g. '_file': "
                "stone_Base_Color.png → stone_Base_Color_file).\n"
                "Empty: the node takes the texture's name as it is."
            ),
        )

        widget.menu.add("Separator", setTitle="Path Management")
        widget.menu.add(
            self.sb.registered_widgets.PushButton,
            setText="Set Directory…",
            setObjectName="tb_set_texture_directory",
            setToolTip=(
                "Repath every (selected, or all) texture so it lives under the "
                "chosen directory. Subdirectories are flattened. Paths become "
                "relative when the chosen directory is inside the project.\n"
                "Option box (▸): leave / copy / move, and Allow Missing Targets."
            ),
        )
        widget.menu.add(
            self.sb.registered_widgets.PushButton,
            setText="Find && Copy Textures…",
            setObjectName="tb_find_and_copy_textures",
            setToolTip=self.sb.tooltip.fmt(
                title="Find &amp; Copy Textures",
                body="Gather the files behind the (selected, or all) textures, "
                "relocate them into one destination, and repath. Paths become "
                "relative when the destination is inside the project.",
                bullets=[
                    "Opens a panel with both folders on screen at once — "
                    "<b>Search in</b> and <b>Copy into</b>, each labelled — so "
                    "there is no order to remember and nothing to mistake one "
                    "for the other. Copy vs Move lives there too.",
                    "A path that already resolves is its own source, so the "
                    "search folder is only used for what is unresolved — "
                    "leave it empty and only the resolving paths relocate.",
                    "The panel stays open and reports into its own log, so a "
                    "second run with one value changed is one click away.",
                ],
                notes=[
                    "Lightmap dependencies (rows the header toggle shows) ride "
                    "along: searched, copied and their bake markers repointed.",
                    "Maya: Arnold texture nodes are not supported.",
                ],
            ),
        )
        widget.menu.add(
            self.sb.registered_widgets.PushButton,
            setText="Normalize Paths",
            setObjectName="tb_normalize_paths",
            setToolTip=(
                "Rewrite (selected, or all) absolute paths inside the project "
                "to relative (Maya: relative to the project, the form Maya keeps "
                "across a reopen; Blender: // relative to the saved .blend). "
                "UDIM tokens are preserved.\n"
                "Option box (▸): textures outside the project — leave / copy / "
                "move into it."
            ),
        )
        btn_make_abs = widget.menu.add(
            "QPushButton",
            setText="Make Paths Absolute",
            setObjectName="btn_make_paths_absolute",
            setToolTip=(
                "Rewrite (selected, or all) relative paths to absolute, resolved "
                "against the project (Blender: the saved .blend). Inverse of "
                "Normalize Paths — needed e.g. for FBX Embed Media, which cannot "
                "consume relative paths."
            ),
        )
        btn_make_abs.clicked.connect(self.make_paths_absolute)
        widget.menu.add(
            self.sb.registered_widgets.PushButton,
            setText="Resolve Missing Textures",
            setObjectName="tb_resolve_missing_textures",
            setToolTip=(
                "Search the project's texture folder (recursively, all "
                "subfolders) for replacement files for missing (selected, or "
                "all) textures. Enabled strategies run in order: Stem → "
                "Texture → Fuzzy (safest first); stops at first hit."
            ),
        )

        widget.menu.add("Separator", setTitle="Selection")
        btn_sel_for_obj = widget.menu.add(
            "QPushButton",
            setText="Select Textures for Selected Objects",
            setObjectName="btn_select_textures_for_objects",
            setToolTip=(
                "Highlight the texture-path cells for textures used by the "
                "currently selected scene objects."
            ),
        )
        btn_sel_for_obj.clicked.connect(self.select_textures_for_objects)

        btn_sel_broken = widget.menu.add(
            "QPushButton",
            setText="Select Broken Paths",
            setObjectName="btn_select_broken_paths",
            setToolTip="Highlight rows whose texture file is missing.",
        )
        btn_sel_broken.clicked.connect(self.select_broken_paths)

        btn_sel_abs = widget.menu.add(
            "QPushButton",
            setText="Select Absolute Paths",
            setObjectName="btn_select_absolute_paths",
            setToolTip=(
                "Highlight rows whose path is absolute (regardless of validity). "
                "These are candidates for Normalize Paths."
            ),
        )
        btn_sel_abs.clicked.connect(self.select_absolute_paths)

        widget.set_help_text(self._help_text())

    def _help_text(self) -> str:
        """The header's ``?``: what each command does, both hosts."""
        labels = self.labels
        general = [
            f"<b>Open {labels['texture_dir']}</b> — Explorer shortcut.",
            "<b>Reload Scene Textures</b> — re-read every texture from disk "
            "(useful after relocations).",
            "<b>Truncate Texture Paths</b> — shorten the path column's display "
            "by dropping whole middle folders (drive and filename stay "
            "readable). The cell keeps the full path (edits, commands and the "
            "tooltip always use it). Option box (▸) sets the length.",
        ]
        if self.engine.EXCLUDE_ARNOLD:
            general.append(
                "<b>Exclude Arnold Nodes</b> — hide rows whose texture is used "
                "only by an Arnold shader (a preview shader owns a duplicate file "
                "node per texture). Also narrows the <i>all</i> scope, so path "
                "commands skip them too."
            )
        general.append(
            "<b>Show Lightmap Dependencies</b> — rows for the baked maps the "
            "bake markers name (no texture node). Red = nowhere on disk; amber = "
            "found outside the recorded folder. Find &amp; Copy relocates them "
            "and rewrites the markers; Normalize Paths / Make Paths Absolute "
            "re-spell the recorded folder; hiding them also keeps them out of "
            "the <i>all</i> scope."
        )
        return self.sb.tooltip.fmt(
            title="Texture Path Editor",
            body="Inspect and fix texture paths. Path commands operate on "
            "selected rows if any, otherwise on every texture in the scene.",
            sections=[
                (
                    "Path management (header menu)",
                    [
                        "<b>Set Directory…</b> — repath to a chosen folder "
                        "(subdirs flatten). Option box (▸) chooses leave / copy / "
                        "move.",
                        "<b>Find &amp; Copy Textures…</b> — gather every texture "
                        "and relocate them into one destination. Opens a panel "
                        "carrying every option: Copy / Move, the folder to "
                        "search, the folder to write into, and a dry run.",
                        "<b>Normalize Paths</b> — rewrite absolute paths inside "
                        "the project to relative (Blender: // relative to the "
                        "saved .blend). Option box (▸) controls textures outside "
                        "it: leave / copy / move into the project.",
                        "<b>Make Paths Absolute</b> — rewrite relative paths to "
                        "absolute. Inverse of Normalize Paths.",
                        "<b>Resolve Missing Textures</b> — search the project's "
                        "texture folder using the strategy cascade <i>Stem → "
                        "Texture → Fuzzy</i> (safest first; stops at first hit). "
                        "Option box (▸) enables/disables individual strategies.",
                    ],
                ),
                ("General (header menu)", general),
                (
                    "Naming (header menu)",
                    [
                        "<b>Keep Names In Sync</b> — renaming a material, or "
                        "giving a texture or its node a new base name, renames "
                        "its whole material to one base name: the material (with "
                        "its affix), every texture file of its set, on disk, and "
                        "their nodes. Option box (▸): the material affix (the "
                        "scene convention by default) and the node suffix.",
                    ],
                ),
                (
                    "Selection helpers (header menu)",
                    [
                        "<b>Select Textures for Selected Objects</b> — highlight "
                        "rows for textures used by the current scene selection.",
                        "<b>Select Broken Paths</b> — rows whose file is missing "
                        "on disk.",
                        "<b>Select Absolute Paths</b> — rows with absolute paths "
                        "(candidates for Normalize Paths).",
                    ],
                ),
            ],
            notes=[
                "Find &amp; Copy runs inside its own panel and reports there — "
                "the pane at the bottom is the whole record of what it found, "
                "relocated and repathed.",
                "<b>Right-click</b> any row for per-texture actions: Browse for "
                "File (one row) or Folder (several — each repointed to its "
                "same-named file there), Rename File (the file on disk, in "
                f"place), scene selection, {labels['select_file_node']}, "
                f"{labels['graph']}, {labels['delete']} (on a lightmap row: "
                "Revert to Source, the Lightmap Baker's Revert Selected — its "
                "objects are unbound, the map stays on disk). Editing a path "
                "that changes only the file name renames the file too, inside "
                "this project (outside it the path repoints).",
                "<b>Right-click the column headers</b> to show, hide or reorder "
                f"columns: {labels['file_node']}, File Size, Dimensions and "
                "Image Type start hidden, and a hidden column's values are never "
                "read.",
                "Collision policy on Copy / Move: same-name + same-size files "
                "rebind without overwriting; different-size hits skip with a "
                "warning (never silently rebinds to a wrong texture, never "
                "destroys the external).",
                "Blender: Normalize Paths, Make Paths Absolute and copying or "
                "moving into the project need the .blend saved.",
            ],
        )

    def tb_set_texture_directory_init(self, widget):
        """The Set Directory option box: the relocate mode and Allow Missing Targets."""
        widget.option_box.menu.setTitle("Set Directory")
        widget.option_box.menu.add(
            "QComboBox",
            setObjectName="cmb_relocate_mode",
            setToolTip=(
                "Behavior for texture files when the directory changes:\n\n"
                "• Leave in place — only rewrite the path.\n"
                "• Copy — duplicate each texture into the chosen directory.\n"
                "• Move — relocate each texture into the chosen directory.\n\n"
                "Collision policy: same-name + same-size at destination is a "
                "safe rebind (no overwrite). Different size is skipped + "
                "warned — never silently rebind to a wrong texture."
            ),
            addItems=[label for label, _key in self._RELOCATE_MODE_ITEMS],
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setObjectName="chk_allow_missing",
            setText="Allow Missing Targets",
            setChecked=False,
            setToolTip=(
                "Repath a texture even when the chosen directory holds no file "
                "of that name.\n\nOff (the default), such textures keep the "
                "path they have: rewriting them would only spell the breakage "
                "differently. Tick it to point a batch at a folder you are "
                "about to fill."
            ),
        )

    def tb_normalize_paths_init(self, widget):
        """The Normalize Paths option box: what becomes of external textures."""
        widget.option_box.menu.setTitle("Normalize Paths")
        widget.option_box.menu.add(
            "QComboBox",
            setObjectName="cmb_external_mode",
            setToolTip=(
                "Behavior for external textures (absolute paths outside the "
                "project) whose file exists on disk:\n\n"
                "• Leave untouched — only rewrite paths already inside the "
                "project.\n"
                "• Copy into the project — duplicate the file in (a UDIM set's "
                "every tile; Maya: into sourceimages), then rebind.\n"
                "• Move into the project — relocate the file in, then rebind.\n\n"
                "Collision policy: a same-named file already there is reused "
                "only when it matches; a different one is never overwritten "
                "and never silently rebound to."
            ),
            addItems=[label for label, _key in self._NORMALIZE_MODE_ITEMS],
        )

    def tb_resolve_missing_textures_init(self, widget):
        """The Resolve Missing option box: one checkbox per strategy."""
        widget.option_box.menu.setTitle("Resolve Missing Textures")
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Stem  — exact name, different extension",
            setObjectName="chk_stem",
            setChecked=True,
            setToolTip=(
                "Match files whose stem equals the missing texture's stem "
                "(extension may differ)."
            ),
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Texture  — same map type + base name (safest fuzzy)",
            setObjectName="chk_texture",
            setChecked=True,
            setToolTip=(
                "Restrict candidates to files of the same map type "
                "(AO / Normal / Roughness / …) and fuzzy-match on the "
                "map-stripped base name — an _AO file can never get repathed to "
                "a _Normal file."
            ),
        )
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Fuzzy  — similar name (loose; may mismatch)",
            setObjectName="chk_fuzzy",
            setChecked=True,
            setToolTip=(
                "Loose name matching across all candidates. May mismatch on "
                "map-type boundaries."
            ),
        )

    # ------------------------------------------------------------------
    # The table
    # ------------------------------------------------------------------

    def _headers(self):
        """The table's columns, in order: 3-5 are facts about the file."""
        labels = self.labels
        return (
            labels["shader"],
            "Texture Path",
            labels["file_node"],
            "File Size",
            "Dimensions",
            "Image Type",
        )

    def tbl000_init(self, widget):
        """Build the row menu once, then (re)populate the table."""
        if not widget.is_initialized:
            labels = self.labels
            widget.refresh_on_show = True
            widget.cellChanged.connect(self.handle_cell_edit)
            if self._footer_controller:
                widget.itemSelectionChanged.connect(self._footer_controller.update)

            # Right-click the header: show / hide / reorder the columns. The
            # optional ones start hidden and are read only once shown.
            widget.enable_column_config(
                settings_key="texture_path_editor_columns",
                locked=(1,),
                reorderable=True,
                hidden_by_default=self._COLUMNS_HIDDEN_BY_DEFAULT,
            )
            self.sb.ColumnConfig.of(widget).visibility_changed.connect(
                lambda column, hidden, w=widget: (
                    None if hidden else self._fill_info_columns(w, [column])
                )
            )
            widget.context_menu_about_to_show.connect(
                lambda w=widget: self._fit_row_menu(w)
            )

            widget.menu.add("Separator", setTitle="Path Management")
            widget.menu.add(
                "QPushButton",
                setText="Browse for File...",
                setObjectName="row_browse_for_file",
                setToolTip=(
                    "One row: pick the texture file to repath it to.\n"
                    "Several rows: pick a folder — each selected texture is "
                    "repointed to its same-named file there; one with no such "
                    "file keeps its path."
                ),
            )
            widget.menu.add(
                "QPushButton",
                setText="Rename File...",
                setObjectName="row_rename_file",
                setToolTip=(
                    "Rename this row's texture file on disk, in its cell (a UDIM "
                    "set renames every tile). Every node reading it is "
                    "repointed; with Keep Names In Sync on, a new base name "
                    "takes the material, its other textures and their nodes "
                    "along. One undo step."
                ),
            )

            widget.menu.add("Separator", setTitle="Selection")
            widget.menu.add(
                "QPushButton",
                setText="Select In Scene",
                setObjectName="select_material",
                setToolTip="Select the scene objects using this row's material(s).",
            )
            widget.menu.add(
                "QPushButton",
                setText=labels["select_file_node"],
                setObjectName="select_file_node",
                setToolTip=(
                    "Select the node(s) reading this row's texture (Blender: "
                    "every Image Texture node bound to it, node groups "
                    "included — one texture can map to none or several)."
                ),
            )
            widget.menu.add(
                "QPushButton",
                setText=labels["graph"],
                setObjectName="row_show_in_hypershade",
                setToolTip=(
                    "Graph the row's texture in the node editor (Maya: the file "
                    "node in the Hypershade; Blender: its material in the "
                    "Shader Editor)."
                ),
            )

            widget.menu.add("Separator", setTitle="Edit")
            widget.menu.add(
                "QPushButton",
                setText=labels["delete"],
                setObjectName="delete_file_node",
                setToolTip=(
                    "Delete the selected row(s)' texture node — the file on disk "
                    "is never deleted (Blender: the image leaves the .blend and "
                    "the Image Texture nodes using it are left empty). On a "
                    "lightmap row: Revert to Source."
                ),
            )

            for action, method in (
                ("row_browse_for_file", self.row_browse_for_file),
                ("row_rename_file", self.row_rename_file),
                ("select_material", self.select_material),
                ("select_file_node", self.select_file_node),
                ("row_show_in_hypershade", self.row_show_in_hypershade),
                ("delete_file_node", self.delete_file_node),
            ):
                widget.register_menu_action(
                    action,
                    lambda selection, fn=method: fn(selection),
                    columns=self._ROW_SELECTION_COLUMNS,
                )

            self._setup_scene_change_callback(widget)

        self._refresh_table_content(widget)

    def refresh_texture_table(self):
        """Re-read the scene into the table (the header's refresh button)."""
        table = getattr(self.ui, "tbl000", None)
        if table:
            table.init_slot()

    def _refresh_table_content(self, widget):
        """Repopulate the table from the engine's rows and the lightmap records."""
        with self.sb.busy_cursor():
            rows = self.engine.rows(exclude_arnold=self._exclude_arnold())
            self._lightmap_rows = {
                self._lightmap_row_path(dep): dep
                for dep in self._lightmap_dependencies()
            }
            self._path_state = {}
            self._node_materials = {}
            self._editable_shaders = set()
            for row in rows:
                self._path_state[row["path"]] = (row["exists"], row["abspath"])
                known = self._node_materials.setdefault(row["file_node"], [])
                known.extend(m for m in row["materials"] if m not in known)
                if row["shader_editable"] and row["shader_node"]:
                    self._editable_shaders.add(row["shader_node"])

            # The fact columns start empty: _fill_info_columns reads only the
            # ones showing. Node names ride in UserRole so an edit can recover
            # the old name; an EMPTY UserRole on a lightmap row's name cells
            # keeps the node commands from mistaking its label for a node, and
            # its path cell keeps the path in UserRole: an edit replaces the
            # text, and the row's identity is what reaches its record.
            facts = [""] * len(self._INFO_COLUMNS)
            formatted = [
                [
                    (row["shader"], row["shader_node"]),
                    row["path"],
                    (row["file_node"], row["file_node"]),
                    *facts,
                ]
                for row in rows
            ]
            for path, dep in self._lightmap_rows.items():
                shader_label, node_label = self._lightmap_labels(dep)
                formatted.append(
                    [(shader_label, ""), (path, path), (node_label, ""), *facts]
                )
            if not formatted:
                formatted = [["", "", ("No textures found", ""), *facts]]

            widget.setUpdatesEnabled(False)
            # A populated cell is not an edit: cellChanged runs handle_cell_edit.
            blocked = widget.blockSignals(True)
            try:
                widget.clear()
                widget.add(formatted, headers=list(self._headers()))
                self._lock_shader_cells(widget)

                header = widget.horizontalHeader()
                header.setSectionsMovable(False)
                QHeaderView = self.sb.QtWidgets.QHeaderView
                for column in range(len(self._headers())):
                    header.setSectionResizeMode(
                        column,
                        QHeaderView.Stretch if column == 1 else QHeaderView.Interactive,
                    )
                widget.setColumnWidth(0, 200)
                widget.setColumnWidth(2, 200)
                for column in self._INFO_COLUMNS:
                    widget.setColumnWidth(column, 90)
                # A rebuild resets the columns; the user's layout goes back on.
                widget.restore_column_state()

                self.setup_formatting(widget)
                widget.apply_formatting()
                self._apply_path_truncation(widget)
                self._fill_info_columns(widget)
            finally:
                widget.blockSignals(blocked)
                widget.setUpdatesEnabled(True)

        # After apply_formatting -- that pass is what fills the set.
        if self._over_long_paths:
            self.logger.warning(
                f"Texture Path Editor: {len(self._over_long_paths)} path(s) exceed "
                f"this OS's {ptk.FileUtils.path_length_limit()}-character path limit."
            )
        if self._footer_controller:
            self._footer_controller.update()

    def _lock_shader_cells(self, widget):
        """A shader cell is editable only where it names one shader the engine
        lets it rename (Blender: one local material; a lightmap row: none)."""
        Qt = self.sb.QtCore.Qt
        for row in range(widget.rowCount()):
            item = widget.item(row, 0)
            if (
                item is not None
                and item.data(Qt.UserRole) not in self._editable_shaders
            ):
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)

    def _row_state(self, path, file_node=None):
        """``(exists, absolute path)`` for a stored path: the refresh's verdict,
        or the engine's for a path typed since."""
        state = self._path_state.get(path)
        if state is None:
            state = self.engine.resolve_path(path, file_node)
            self._path_state[path] = state
        return state

    def setup_formatting(self, widget):
        """Mark the path cell red when its file is missing (amber when over-long
        or, on a lightmap row, found away from the recorded folder), and tooltip
        it with the resolved path and the path it had before this session's
        last repath."""
        warn_long = self._warn_path_length_enabled()
        length_limit = ptk.FileUtils.path_length_limit()
        # Reset per rebuild; the formatter fills it as it paints, so the caller
        # reads it only after apply_formatting.
        self._over_long_paths = set()

        def format_if_invalid(item, value, row, col, *_):
            path = str(value).strip()
            dep = self._lightmap_rows.get(path)
            if dep is not None:
                # A lightmap row carries its own verdict: the records resolved
                # it the way the export will. Red = nowhere; amber = found, but
                # not where the marker says (the export ships it, and Find &
                # Copy heals it).
                found = dep.get("path")
                stale = bool(found) and dep.get("found_by") != "hint"
                widget.format_item(
                    item,
                    key="invalid" if not found else ("warning" if stale else "reset"),
                )
                objects = dep.get("objects") or []
                if not found:
                    line = f"Missing lightmap:\n{path}"
                    if dep.get("note"):
                        line += f"\n{dep['note']}"
                elif stale:
                    line = f"Recorded folder no longer holds it; found at:\n{found}"
                else:
                    line = found
                names = ", ".join(str(o).rsplit("|", 1)[-1] for o in objects)
                item.setToolTip(
                    f"{line}\n\nBake marker on {len(objects)} object(s): {names}"
                )
                return
            node_item = widget.item(row, 2)
            node = node_item.data(self.sb.QtCore.Qt.UserRole) if node_item else None
            exists, abs_path = self._row_state(path, node or None)
            # A missing file outranks an over-long one: it is the harder
            # failure, and an over-long path is usually WHY it went missing.
            over_long = warn_long and len(abs_path or "") > length_limit
            if over_long:
                self._over_long_paths.add(path)
            widget.format_item(
                item,
                key="invalid" if not exists else ("warning" if over_long else "reset"),
            )
            tooltip_lines = [abs_path if exists else f"Missing file:\n{abs_path}"]
            if over_long:
                tooltip_lines.append(
                    f"Path is {len(abs_path)} characters — over this OS's "
                    f"{length_limit}-character limit."
                )
            previous = self.engine.previous_paths.get(node) if node else None
            if previous and previous != path:
                tooltip_lines.append(f"Previous: {previous}")
            item.setToolTip("\n\n".join(tooltip_lines))

        widget.set_column_formatter(1, format_if_invalid)

    # ------------------------------------------------------------------
    # Menu state
    # ------------------------------------------------------------------

    @staticmethod
    def _menu_flag(menu, name: str, default: bool) -> bool:
        """State of a checkbox on ``menu``; ``default`` when it isn't there.

        Every toggle here is read from a menu that may not exist yet -- a
        refresh can fire before ``header_init`` builds it, and a command can be
        driven without an option box at all.
        """
        chk = getattr(menu, name, None) if menu is not None else None
        try:
            return bool(chk.isChecked())
        except AttributeError:
            return default

    @classmethod
    def _read_option_flag(cls, button, name: str, default: bool) -> bool:
        """State of a checkbox in ``button``'s option box; ``default`` if absent."""
        return cls._menu_flag(
            getattr(getattr(button, "option_box", None), "menu", None), name, default
        )

    @staticmethod
    def _read_combo_mode(button, combo_name: str, mode_items) -> str:
        """An option-box combo's mode key, by index (the first when unbuilt or
        out of range -- the safe default)."""
        try:
            idx = getattr(button.option_box.menu, combo_name).currentIndex()
        except AttributeError:
            return mode_items[0][1]
        return mode_items[idx][1] if 0 <= idx < len(mode_items) else mode_items[0][1]

    def _read_resolve_modes(self, button):
        """The Resolve Missing strategies ticked, safest first (all when unbuilt)."""
        return [
            mode
            for mode in self.engine.RESOLVE_STRATEGY_ORDER
            if self._read_option_flag(button, self._RESOLVE_CHECKBOXES[mode], True)
        ]

    def _header_menu(self):
        """The header's menu, or None while it is still unbuilt."""
        return getattr(getattr(self.ui, "header", None), "menu", None)

    def _option_menu(self, name: str):
        """The option-box menu of header item *name*, or None while unbuilt."""
        item = getattr(self._header_menu(), name, None)
        return getattr(getattr(item, "option_box", None), "menu", None)

    def _exclude_arnold(self) -> bool:
        """The header's "Exclude Arnold Nodes" toggle (off, and absent where the
        engine has nothing to exclude)."""
        return bool(self.engine.EXCLUDE_ARNOLD) and self._menu_flag(
            self._header_menu(), "chk_exclude_arnold", False
        )

    def _warn_path_length_enabled(self) -> bool:
        """ "Warn On Over-Long Paths" -- on until the header is built: an early
        refresh should warn, not silently skip the check."""
        return self._menu_flag(self._header_menu(), "chk_warn_path_length", True)

    def _truncate_paths_enabled(self) -> bool:
        """ "Truncate Texture Paths" -- off until the header is built."""
        return self._menu_flag(self._header_menu(), "chk_truncate_paths", False)

    def _truncate_length(self) -> int:
        """The truncation length; the default until the header is built."""
        spin = getattr(
            self._option_menu("chk_truncate_paths"), "spn_truncate_length", None
        )
        return int(spin.value()) if spin is not None else self._PATH_TRUNCATE_LENGTH

    def _apply_path_truncation(self, widget=None):
        """Push the Truncate Texture Paths toggle onto the path column.

        Display-only: ``set_column_truncation`` shortens what the delegate
        paints, never the item's data -- the cell still holds (and edits back)
        the full path. Re-applied on every rebuild so a refresh can't drop it.
        """
        widget = widget if widget is not None else getattr(self.ui, "tbl000", None)
        if widget is None:  # toggled before the table exists
            return
        widget.set_column_truncation(
            1,
            length=(
                self._truncate_length() if self._truncate_paths_enabled() else None
            ),
            mode="path",
            # An ellipsis, not the primitive's default "..", which in a path
            # column reads as a parent-directory segment.
            insert="…",
            head=self._PATH_TRUNCATE_HEAD,
        )

    def _sync_names_enabled(self) -> bool:
        """The header's "Keep Names In Sync" toggle."""
        return self._menu_flag(self._header_menu(), "chk_sync_names", False)

    def _sync_affixes(self):
        """``(material (prefix, suffix), node (prefix, suffix))`` from the Keep
        Names In Sync option box -- the material's through its affix picker (the
        scene convention by default), the node's a plain suffix."""
        flyout = self._option_menu("chk_sync_names")
        field = getattr(flyout, "txt_shader_affix", None)
        shader = ("", "")
        if field is not None:
            shader = field.option_box.resolve_affix(default="suffix")
        if not any(shader):  # an empty field: the convention, not nothing
            shader = ptk.NamingConvention.affix_parts("material")
        suffix_field = getattr(flyout, "txt_file_node_suffix", None)
        suffix = suffix_field.text().strip() if suffix_field is not None else ""
        if suffix and not suffix.startswith("_"):
            suffix = f"_{suffix}"
        return tuple(shader), ("", suffix)

    def _sync(self):
        """What the engine's renames take as ``sync``: the affixes while Keep
        Names In Sync is on, ``None`` while it is off."""
        return self._sync_affixes() if self._sync_names_enabled() else None

    def _apply_shader_affix_hint(self, widget) -> None:
        """The material affix field's placeholder and tooltip, per its mode."""
        noun = self.labels["shader"]
        mode = widget.option_box.affix_mode
        hints = {
            "convention": (
                "Scene Convention",
                "The material takes the scene's naming convention for materials "
                "(edit it in the Naming panel's Suffix By Type).\nClick the "
                "button beside the field to type your own instead.",
            ),
            "prefix": (f"{noun} Prefix", "Prepended to the base name: MAT_stone."),
            "suffix": (f"{noun} Suffix", "Appended to the base name: stone_MAT."),
        }
        placeholder, tip = hints.get(
            mode,
            (
                f"{noun} Affix",
                "Placement read from the '_': '_MAT' is a suffix, 'MAT_' a prefix.",
            ),
        )
        widget.setPlaceholderText(placeholder)
        widget.setToolTip(tip)

    # ------------------------------------------------------------------
    # Scope -- the selected rows, else everything shown
    # ------------------------------------------------------------------

    @staticmethod
    def _leaf(name) -> str:
        """A node name without its DAG path and namespace (how rows compare)."""
        return str(name).split("|")[-1].split(":")[-1]

    @staticmethod
    def _selection_value(entry, key: str):
        """A selection entry's value for *key* -- a row object (``values`` dict)
        or a plain dict keyed by name or column."""
        # A row carries its cells in a ``values`` DICT; a plain dict's
        # ``values`` is the builtin method, so it is probed by shape.
        values = getattr(entry, "values", None)
        if isinstance(values, dict):
            return values.get(key)
        if isinstance(entry, dict):
            if key in entry:
                return entry.get(key)
            column = TexturePathEditorSlots._ROW_SELECTION_COLUMNS.get(key)
            return entry.get(column) if column is not None else None
        return None

    def _get_selected_contexts(self, selection=None, require_file_nodes=True):
        """What each selected row stands for.

        A texture row: ``shader_node`` (the shader its cell renames; Keep Names
        In Sync's material), ``file_node`` / ``file_nodes`` (when it still
        exists) and ``materials`` (the shaders a scene selection follows). A
        lightmap row: its ``lightmap`` record (skipped by commands that need a
        node).
        """
        table = getattr(self.ui, "tbl000", None)
        if table is None:
            return []
        if selection is None:
            selection = table.get_selection(
                columns=self._ROW_SELECTION_COLUMNS, include_current=True
            )
        contexts = []
        for entry in selection or []:
            path = str(self._selection_value(entry, "path") or "").strip()
            lightmap = self._lightmap_rows.get(path)
            if lightmap is not None:
                if not require_file_nodes:
                    contexts.append(
                        {
                            "shader_node": None,
                            "file_node": None,
                            "file_nodes": [],
                            "materials": [],
                            "lightmap": lightmap,
                        }
                    )
                continue
            node = self._selection_value(entry, "file_node")
            if isinstance(node, (list, tuple)):
                node = next((v for v in node if v), None)
            node = str(node).strip() if node else ""
            if node and not self.engine.node_exists(node):
                node = ""
            shader = str(self._selection_value(entry, "shader") or "").strip()
            context = {
                "shader_node": shader or None,
                "file_node": node or None,
                "file_nodes": [node] if node else [],
                "materials": (
                    [shader] if shader else list(self._node_materials.get(node, []))
                ),
            }
            if require_file_nodes and not node:
                continue
            contexts.append(context)
        return contexts

    def _get_scope_nodes(self):
        """``(nodes, scope label)``: the selected rows' nodes if any are selected,
        otherwise every node the table lists (Exclude Arnold Nodes honored, so a
        command never touches rows the table is hiding).

        A selection holding no live node is NOT escalated to the whole scene: it
        returns nothing, and the command says so.
        """
        contexts = self._get_selected_contexts(require_file_nodes=False)
        if contexts:
            nodes = list(dict.fromkeys(n for c in contexts for n in c["file_nodes"]))
            if nodes:
                return nodes, f"{len(nodes)} selected row(s)"
            if any(c.get("lightmap") for c in contexts):
                # A lightmap-only selection is a valid scope for the commands
                # that take one; the node commands get an empty list.
                return [], f"{len(contexts)} selected lightmap row(s)"
            return [], "selected (no valid textures)"
        nodes = list(self.engine.file_nodes(exclude_arnold=self._exclude_arnold()))
        return nodes, f"all {len(nodes)} texture(s)"

    def _get_scope_lightmaps(self):
        """The lightmap rows in scope: the selected ones when the selection holds
        any (texture rows alone take none along), otherwise every lightmap row
        shown -- so the toggle that hides them keeps them out of "all" too."""
        contexts = self._get_selected_contexts(require_file_nodes=False)
        if contexts:
            return [c["lightmap"] for c in contexts if c.get("lightmap")]
        return list(self._lightmap_rows.values())

    # ------------------------------------------------------------------
    # Lightmap rows
    # ------------------------------------------------------------------

    def _show_lightmaps_enabled(self) -> bool:
        """The header's "Show Lightmap Dependencies" toggle (default on)."""
        return self._menu_flag(self._header_menu(), "chk_show_lightmaps", True)

    def _lightmap_dependencies(self):
        """The records, ``[]`` when the toggle hides them or they cannot be
        listed (a listing must never cost the table)."""
        if not self._show_lightmaps_enabled():
            return []
        try:
            return list(self.engine.lightmap_dependencies())
        except Exception as e:  # noqa: BLE001
            self.logger.warning(f"Lightmap dependencies not listed: {e}")
            return []

    @staticmethod
    def _lightmap_row_path(dep) -> str:
        """The path a lightmap row shows: the marker's recorded folder + map --
        the STORED spelling, as texture rows show theirs."""
        folder = str(dep.get("dir") or "").replace("\\", "/").rstrip("/")
        return f"{folder}/{dep['map']}" if folder else dep["map"]

    def _lightmap_labels(self, dep):
        """``(shader, node)`` labels for a lightmap row (the engine's), never
        costing the table."""
        try:
            shader, node = self.engine.lightmap_labels(dep)
        except Exception:  # noqa: BLE001
            shader, node = "", os.path.splitext(dep["map"])[0]
        return shader or self._LIGHTMAP_ROW_LABEL, node

    # ------------------------------------------------------------------
    # Header slots -- General
    # ------------------------------------------------------------------

    def open_source_images(self):
        """Open the project's texture folder in the file explorer."""
        path = self.engine.texture_dir()
        if path and os.path.isdir(path):
            ptk.FileUtils.open_explorer(path)
        elif not path:
            self.sb.message_box("No project texture folder yet — save the scene first.")
        else:
            self.sb.message_box(f"Texture folder not found:<br><hl>{path}</hl>")

    def reload_scene_textures(self):
        """Re-read every scene texture from disk."""
        self.engine.reload_textures()
        self.sb.message_box("Reloaded scene textures from disk.")
        self.refresh_texture_table()

    # ------------------------------------------------------------------
    # Header slots -- Path Management
    # ------------------------------------------------------------------

    def tb_set_texture_directory(self, widget=None):
        """Repath the scope's textures under a chosen directory.

        The option box decides whether the files travel (copy / move) or only
        the path changes, and whether a texture the folder does not hold is
        repathed anyway (Allow Missing Targets).
        """
        nodes, scope_label = self._get_scope_nodes()
        if not nodes:
            self.sb.message_box("No textures to process.")
            return
        relocate_mode = self._read_combo_mode(
            widget, "cmb_relocate_mode", self._RELOCATE_MODE_ITEMS
        )
        allow_missing = self._read_option_flag(widget, "chk_allow_missing", False)
        # The active mode in the dialog title -- the last thing read before
        # any file op; the marker says it is a TARGET, not a folder to look in.
        mode_hint = {
            "rewrite": "path only",
            "copy": "copy files",
            "move": "move files",
        }.get(relocate_mode, relocate_mode)
        target_dir = self.sb.dir_dialog(
            title=(
                f"{self._DIALOG_MARK_DEST} DESTINATION — Set Texture Directory "
                f"({mode_hint}) for {scope_label}"
            ),
            start_dir=self.engine.texture_dir(),
        )
        if not target_dir:
            return
        count = self.engine.set_texture_directory(
            nodes, target_dir, relocate_mode=relocate_mode, allow_missing=allow_missing
        )
        message = f"Updated <hl>{count}</hl>/{len(nodes)} texture path(s)."
        if count < len(nodes) and not allow_missing:
            message += (
                "<br>The rest kept their path (already there, a collision, or "
                "not in that folder — Copy / Move brings the files along; Allow "
                "Missing Targets in the option box points them there anyway)."
            )
        self.sb.message_box(message)
        self.refresh_texture_table()

    def tb_find_and_copy_textures(self, widget=None):
        """Open the Find & Copy panel over the current scope.

        Every option lives on that panel, so there is no option box: the mode,
        the search folder and the destination are read together at the moment
        they are used, and the panel stays up while it works.
        """
        nodes, scope_label = self._get_scope_nodes()
        lightmaps = self._get_scope_lightmaps()
        if not nodes and not lightmaps:
            self.sb.message_box("No textures to process.")
            return
        if lightmaps:
            scope_label = (f"{scope_label} + " if nodes else "") + (
                f"{len(lightmaps)} lightmap(s)"
            )
        self._find_and_copy_workflow(
            nodes, scope_label=scope_label, lightmaps=lightmaps
        )

    def tb_normalize_paths(self, widget=None):
        """Rewrite the scope's paths inside the project to relative; the option
        box says what becomes of the textures outside it."""
        nodes, scope_label = self._get_scope_nodes()
        lightmaps = self._get_scope_lightmaps()
        if not nodes and not lightmaps:
            self.sb.message_box("No textures to process.")
            return
        changed = 0
        if nodes:
            external_mode = self._read_combo_mode(
                widget, "cmb_external_mode", self._NORMALIZE_MODE_ITEMS
            )
            changed = self.engine.normalize_paths(nodes, external_mode=external_mode)
        # Lightmap rows: the recorded folder takes the same portable spelling.
        # Files never move.
        respelled = self.engine.normalize_lightmaps(lightmaps, relative=True)
        self.sb.message_box(
            self._summary(changed, respelled, scope_label, "made relative")
            or "Nothing changed — the paths are already relative (or cannot be: "
            "outside the project, missing, or an unsaved file)."
        )
        self.refresh_texture_table()

    def make_paths_absolute(self):
        """Rewrite the scope's relative paths to absolute -- inverse of Normalize."""
        nodes, scope_label = self._get_scope_nodes()
        lightmaps = self._get_scope_lightmaps()
        if not nodes and not lightmaps:
            self.sb.message_box("No textures to process.")
            return
        try:
            changed = self.engine.make_paths_absolute(nodes) if nodes else 0
        except ValueError as e:  # nothing to resolve against
            self.sb.message_box(str(e))
            return
        respelled = self.engine.normalize_lightmaps(lightmaps, relative=False)
        self.sb.message_box(
            self._summary(changed, respelled, scope_label, "made absolute")
            or "Nothing changed — the paths are already absolute."
        )
        self.refresh_texture_table()

    @staticmethod
    def _summary(changed, respelled, scope_label, verb) -> str:
        """``"N path(s) made relative; M lightmap folder(s) re-spelled (scope)."``,
        ``""`` when nothing changed."""
        parts = []
        if changed:
            parts.append(f"<hl>{changed}</hl> path(s) {verb}")
        if respelled:
            parts.append(f"<hl>{respelled}</hl> lightmap folder(s) re-spelled")
        return f"{'; '.join(parts)} ({scope_label})." if parts else ""

    def tb_resolve_missing_textures(self, widget=None):
        """Rebind the scope's missing textures to files found in the project's
        texture folder; the option box picks the strategies."""
        nodes, _scope_label = self._get_scope_nodes()
        if not nodes:
            self.sb.message_box("No textures to process.")
            return
        modes = self._read_resolve_modes(widget)
        if not modes:
            self.sb.message_box(
                "No Resolve Missing strategies enabled in the option box."
            )
            return
        count = self.engine.resolve_missing_textures(modes, file_nodes=nodes)
        self.sb.message_box(f"Resolved <hl>{count}</hl> missing texture(s).")
        self.refresh_texture_table()

    # ------------------------------------------------------------------
    # Header slots -- Selection
    # ------------------------------------------------------------------

    def select_textures_for_objects(self):
        """Select the rows whose textures the scene selection's materials read."""
        nodes = self.engine.selected_file_nodes()
        if nodes is None:
            self.sb.message_box("Select object(s) first.")
            return
        targets = {self._leaf(n) for n in nodes}
        if not targets:
            self.sb.message_box("No textures found on the selected objects.")
            return
        self._select_rows_by_predicate(
            lambda path, node: bool(node) and self._leaf(node) in targets,
            "No texture of the selected objects is listed.",
            "matching textures",
        )

    def select_broken_paths(self):
        """Select the rows whose texture file is missing."""
        self._select_rows_by_predicate(
            # A lightmap row is broken when the records found its map nowhere
            # (a stale-but-found hint is amber, not broken -- it ships).
            lambda path, node: (
                not self._lightmap_rows[path].get("path")
                if path in self._lightmap_rows
                else not self._row_state(path, node)[0]
            ),
            "No broken paths found.",
            "broken paths",
        )

    def select_absolute_paths(self):
        """Select the rows whose path is stored absolute -- Normalize candidates
        (a lightmap row by its recorded folder's spelling, the same test)."""
        self._select_rows_by_predicate(
            lambda path, node: self.engine.is_absolute_path(path),
            "No absolute paths found.",
            "absolute paths",
        )

    def _select_rows_by_predicate(self, predicate, empty_message, count_message):
        """Select the path cells of the rows where ``predicate(path, node)`` holds.

        The path cell: the node column is hidden by default, and a selected cell
        nobody can see reads as nothing selected.
        """
        table = self.ui.tbl000
        UserRole = self.sb.QtCore.Qt.UserRole
        table.clearSelection()
        prior = table.selectionMode()
        table.setSelectionMode(self.sb.QtWidgets.QAbstractItemView.MultiSelection)
        selected = 0
        try:
            for row in range(table.rowCount()):
                path_item = table.item(row, 1)
                if path_item is None:
                    continue
                path = str(path_item.text()).strip()
                if not path:
                    continue
                node_item = table.item(row, 2)
                node = node_item.data(UserRole) if node_item is not None else None
                if predicate(path, node or None):
                    path_item.setSelected(True)
                    if selected == 0:
                        table.scrollToItem(path_item)
                    selected += 1
        finally:
            table.setSelectionMode(prior)
        self.sb.message_box(
            f"Selected <hl>{selected}</hl> {count_message}."
            if selected
            else empty_message
        )

    # ------------------------------------------------------------------
    # Row menu
    # ------------------------------------------------------------------

    def _fit_row_menu(self, widget) -> None:
        """Fit the row menu to the selection, just before it opens.

        Browse is a file pick for one row and a folder pick for several (its
        label says which); Rename File renames one row's file and is disabled
        otherwise; Delete on lightmap rows only is the baker's Revert Selected.
        """
        selection = (
            widget.get_selection(
                columns=self._ROW_SELECTION_COLUMNS, include_current=True
            )
            or []
        )
        rows = len(selection)
        lightmap_rows = sum(
            1
            for entry in selection
            if str(self._selection_value(entry, "path") or "").strip()
            in self._lightmap_rows
        )
        QPushButton = self.sb.QtWidgets.QPushButton
        delete = widget.menu.findChild(QPushButton, "delete_file_node")
        if delete is not None:
            delete.setText(
                "Revert to Source..."
                if rows and lightmap_rows == rows
                else self.labels["delete"]
            )
        browse = widget.menu.findChild(QPushButton, "row_browse_for_file")
        if browse is not None:
            browse.setText("Browse for Folder..." if rows > 1 else "Browse for File...")
        rename = widget.menu.findChild(QPushButton, "row_rename_file")
        if rename is not None:
            rename.setEnabled(rows == 1)

    def row_browse_for_file(self, selection=None):
        """Repath the row's texture to a picked file (several rows: a folder)."""
        if self._browse_in_progress:
            return
        self._browse_in_progress = True
        try:
            self._do_browse_for_file(selection)
        finally:
            self.sb.QtCore.QTimer.singleShot(
                250, lambda: setattr(self, "_browse_in_progress", False)
            )

    def _do_browse_for_file(self, selection):
        contexts = self._get_selected_contexts(selection, require_file_nodes=False)
        if len(contexts) > 1:
            # Several rows: one folder, each repointed to its own file there.
            self._browse_for_folder(contexts)
            return
        lightmaps = [c["lightmap"] for c in contexts if c.get("lightmap")]
        if lightmaps:
            # A lightmap row: the file picked names the folder the markers should
            # record (a different basename is a re-bake, refused).
            self._browse_for_lightmap(lightmaps[0])
            return
        nodes = [n for c in contexts for n in c["file_nodes"]]
        if not nodes:
            return
        node = nodes[0]
        start_dir = self.engine.texture_dir()
        current = self.engine.stored_path(node)
        if current:
            folder = os.path.dirname(self.engine.resolve_path(current, node)[1])
            if folder and os.path.isdir(folder):
                start_dir = folder
        chosen = self.sb.file_dialog(
            file_types=list(self.engine.FILE_TYPES),
            title=f"Select texture file for {node}",
            start_dir=start_dir,
            filter_description="Texture Files",
            allow_multiple=False,
        )
        if not chosen:
            return
        try:
            self.engine.set_texture_path(node, chosen, relative=True)
        except (ValueError, OSError, RuntimeError) as e:
            self.sb.message_box(f"Browse for File: {e}")
            return
        self.refresh_texture_table()

    def _browse_for_lightmap(self, dep) -> None:
        """Pick the file a lightmap row's markers should point at; repath them."""
        texture_dir = self.engine.texture_dir()
        start_dir = os.path.dirname(dep["path"]) if dep.get("path") else dep.get("dir")
        if not (start_dir and os.path.isdir(start_dir)):
            start_dir = texture_dir
        chosen = self.sb.file_dialog(
            file_types=["*.exr", "*.hdr", "*.png", "*.tif", "*.tiff", "*.*"],
            title=f"Select lightmap file {dep['map']}",
            start_dir=start_dir,
            filter_description="Lightmap Files",
            allow_multiple=False,
        )
        if not chosen:
            return
        if os.path.basename(chosen).lower() != dep["map"].lower():
            self.sb.message_box(
                f"Browse for File: the markers name <hl>{dep['map']}</hl>; pick "
                f"that file (chose {os.path.basename(chosen)}). A different map "
                "is a re-bake, not a repath."
            )
            return
        if self.engine.repath_lightmap(dep, os.path.dirname(chosen)):
            self.refresh_texture_table()

    def _browse_for_folder(self, contexts) -> None:
        """Several rows: repoint each to its same-named file in a folder picked.

        The textures go through Set Directory's path-only pass, which repoints
        one only when the folder actually holds it -- tiles included -- and
        leaves the rest; a lightmap row follows when its map is there.
        """
        nodes = list(dict.fromkeys(n for c in contexts for n in c["file_nodes"]))
        lightmaps = [c["lightmap"] for c in contexts if c.get("lightmap")]
        start_dir = self.engine.texture_dir()
        for node in nodes[:1]:
            current = self.engine.stored_path(node)
            folder = os.path.dirname(self.engine.resolve_path(current, node)[1])
            if folder and os.path.isdir(folder):
                start_dir = folder
        chosen = self.sb.dir_dialog(
            title=(
                f"{self._DIALOG_MARK_DEST} Browse for Folder — repoint "
                f"{len(contexts)} texture(s) to their same-named files in…"
            ),
            start_dir=start_dir,
        )
        if not chosen:
            return
        count = self.engine.set_texture_directory(nodes, chosen) if nodes else 0
        missing = []
        for dep in lightmaps:
            if os.path.isfile(os.path.join(chosen, dep["map"])):
                count += int(self.engine.repath_lightmap(dep, chosen))
            else:
                missing.append(dep["map"])
        message = (
            f"Browse for Folder: repointed <hl>{count}</hl> of {len(contexts)} row(s)."
        )
        if count < len(nodes) + len(lightmaps):
            message += (
                f"<br>The rest keep their path: {chosen} holds no file of that name"
                + (f" ({', '.join(missing)})" if missing else "")
                + "."
            )
        self.sb.message_box(message)
        self.refresh_texture_table()

    # ------------------------------------------------------------------
    # File facts -- the optional columns
    # ------------------------------------------------------------------

    def _row_texture_path(self, widget, row: int) -> str:
        """The absolute texture (or tile pattern) *row* names; ``""`` if none."""
        item = widget.item(row, 1)
        if item is None:
            return ""
        UserRole = self.sb.QtCore.Qt.UserRole
        lightmap = self._lightmap_rows.get(
            str(item.data(UserRole) or item.text()).strip()
        )
        if lightmap is not None:
            return lightmap.get("path") or ""
        stored = item.text().strip()
        if not stored:
            return ""
        node_item = widget.item(row, 2)
        node = node_item.data(UserRole) if node_item is not None else None
        return self._row_state(stored, node or None)[1]

    @staticmethod
    def _format_fact(field: str, facts: dict):
        """``(text, tooltip, sort key)`` for one fact of a row."""
        if not facts:
            return "", "No file on disk.", None
        tiles = facts.get("tiles", 1)
        of_set = f" — the first of {tiles} tiles" if tiles > 1 else ""
        if field == "bytes":
            size = facts.get("bytes")
            across = f", across {tiles} tiles" if tiles > 1 else ""
            return ptk.FileUtils.format_bytes(size), f"{size:,} bytes{across}", size
        value = facts.get(field)
        if value is None:
            why = (
                "Online-only: not downloaded to read its header."
                if facts.get("online_only")
                else "Unreadable header."
            )
            return "", why, None
        if field == "dimensions":
            width, height = value
            return (
                f"{width} x {height}",
                f"{width} x {height} pixels{of_set}",
                width * height,
            )
        tip = value
        if ";" not in value:  # a PIL mode: spell its depth too
            try:
                tip = f"{value} — {ptk.ImgUtils.format_bit_depth(value)}"
            except Exception:  # noqa: BLE001 -- the mode alone still reads
                pass
        return value, tip + of_set, value

    def _fill_info_columns(self, widget, columns=None) -> None:
        """Fill the fact columns that show (of *columns*, default all).

        A hidden column is never read: its files are not even stat'ed. Headers
        are read once per file version (``ImgUtils.texture_facts`` caches), so
        a refresh costs nothing new.
        """
        header = widget.horizontalHeader()
        wanted = {
            column: field
            for column, field in self._INFO_COLUMNS.items()
            if (columns is None or column in columns)
            and column < widget.columnCount()
            and not header.isSectionHidden(column)
        }
        if not wanted:
            return
        sorting = widget.isSortingEnabled()
        widget.setSortingEnabled(False)  # a sorted column would move rows mid-fill
        blocked = widget.blockSignals(True)  # a filled cell is not an edit
        try:
            for row in range(widget.rowCount()):
                path = self._row_texture_path(widget, row)
                facts = (
                    ptk.ImgUtils.texture_facts(path, tuple(wanted.values()))
                    if path
                    else {}
                )
                for column, field in wanted.items():
                    text, tip, key = self._format_fact(field, facts)
                    widget.set_sorted_cell(row, column, text, key).setToolTip(tip)
        finally:
            widget.blockSignals(blocked)
            widget.setSortingEnabled(sorting)

    # ------------------------------------------------------------------
    # Renaming
    # ------------------------------------------------------------------

    def row_rename_file(self, selection=None):
        """Rename one row's texture file, edited in its own cell: the path cell
        opens on just the file name (the stem selected); Enter renames the file
        on disk and repoints every node reading it."""
        selection = list(selection or [])
        contexts = self._get_selected_contexts(selection, require_file_nodes=False)
        if len(contexts) != 1 or len(selection) != 1:
            self.sb.message_box("Rename File: select a single row.")
            return
        context, row = contexts[0], selection[0].row
        dep = context.get("lightmap")
        if dep is not None:
            name = dep["map"]
        else:
            node = context.get("file_node")
            if not node:
                self.sb.message_box("Rename File: this row has no texture.")
                return
            # posixpath: a Blender-relative "//textures/x.png" is a UNC share to
            # ntpath, whose basename is empty.
            name = posixpath.basename(self.engine.stored_path(node).replace("\\", "/"))
        if not name:
            self.sb.message_box("Rename File: this row names no file.")
            return
        self.ui.tbl000.edit_cell_as(
            row,
            1,
            name,
            lambda new_name, ctx=context: self._rename_texture(ctx, new_name),
        )

    def _rename_texture(self, context, new_name: str) -> bool:
        """Rename the file *context* names (Keep Names In Sync as toggled), then
        refresh; a refused name is said, never half-applied."""
        try:
            self.engine.rename_texture(context, new_name, sync=self._sync())
        except (ValueError, OSError, RuntimeError) as e:
            self.sb.message_box(f"Rename File: {e}")
            return False
        self.sb.QtCore.QTimer.singleShot(0, self.refresh_texture_table)
        return True

    def handle_cell_edit(self, row: int, col: int):
        """An edited cell: the shader / node cells rename what they name, the
        path cell repoints its texture -- or renames the file when only its name
        changed to one nothing is at. With Keep Names In Sync on, a shader
        rename (or a node given a new base name) renames the whole material."""
        if col in self._INFO_COLUMNS:  # facts about the file, not edits
            return
        table = self.ui.tbl000
        item = table.item(row, col)
        if not item:
            return
        new_value = item.text()
        UserRole = self.sb.QtCore.Qt.UserRole

        def restore(original):
            blocked = table.blockSignals(True)
            try:
                item.setText(original)
            finally:
                table.blockSignals(blocked)

        def refresh_later():
            # Deferred: this runs inside cellChanged, and rebuilding the table
            # from within its own signal would delete the item mid-dispatch.
            self.sb.QtCore.QTimer.singleShot(0, self.refresh_texture_table)

        # A lightmap row is identified through its path cell's UserRole, which
        # still holds the row's path after the text was edited.
        path_item = table.item(row, 1)
        row_key = (
            str(path_item.data(UserRole) or path_item.text()).strip()
            if path_item is not None
            else ""
        )
        lightmap = self._lightmap_rows.get(row_key)
        if lightmap is not None:
            self._edit_lightmap_cell(lightmap, col, new_value, restore, refresh_later)
            return

        shader_item, node_item = table.item(row, 0), table.item(row, 2)
        shader = (shader_item.data(UserRole) if shader_item else None) or None
        node = (node_item.data(UserRole) if node_item else None) or None
        sync = self._sync()
        old = item.data(UserRole) or ""
        try:
            if col == 0:
                if not shader or new_value == shader:
                    return
                if sync:
                    restore(shader)  # the refresh after the sync shows what landed
                self.engine.rename_shader(shader, new_value, sync=sync)
                refresh_later()  # every row reading it shows the shader
            elif col == 2:
                if not node or new_value == node:
                    return
                if sync and shader:
                    restore(node)
                    self.engine.rename_file_node(
                        node, new_value, shader=shader, sync=sync
                    )
                    refresh_later()
                    return
                actual = self.engine.rename_file_node(node, new_value)
                item.setData(UserRole, actual)
                if actual != new_value:  # the host made it unique
                    restore(actual)
            elif col == 1:
                if not node:
                    self.sb.message_box("No texture associated with this row.")
                    return
                outcome = self.engine.apply_path_edit(
                    node, new_value, shader=shader, sync=sync
                )
                if outcome == "renamed":
                    refresh_later()
                else:
                    table.apply_formatting()
                    if self._footer_controller:
                        self._footer_controller.update()
        except (ValueError, OSError, RuntimeError) as e:
            if col == 1:
                restore(self.engine.stored_path(node) if node else "")
            else:
                restore(old)
            self.sb.message_box(str(e))

    def _edit_lightmap_cell(self, lightmap, col, new_value, restore, refresh_later):
        """A lightmap row's cell: the path cell repoints the bake markers (folder
        only -- the map is what the bake committed) or renames the map; the name
        cells are labels, not nodes."""
        if col != 1:
            self.sb.message_box("Lightmap rows carry no node to rename.")
            refresh_later()
            return
        typed = new_value.strip().replace("\\", "/")
        stored = self._lightmap_row_path(lightmap)
        if lightmap.get("path") and self.engine.is_file_rename(lightmap["path"], typed):
            # The same folder, a name nothing is at: rename the map (its markers
            # re-stamped with it).
            if not self._rename_texture(
                {"lightmap": lightmap}, os.path.basename(typed)
            ):
                restore(stored)
            return
        if typed and os.path.basename(typed).lower() != lightmap["map"].lower():
            self.sb.message_box(
                f"The bake markers name <hl>{lightmap['map']}</hl>; a path to a "
                "different map is a re-bake, not a repath."
            )
            restore(stored)
            return
        if self.engine.repath_lightmap(lightmap, os.path.dirname(typed)):
            refresh_later()
        else:
            restore(stored)

    # ------------------------------------------------------------------
    # Row slots -- selection, graph, delete
    # ------------------------------------------------------------------

    def select_material(self, selection=None):
        """Select the scene objects using the selected rows' materials (a
        lightmap row: the objects its bake markers bind)."""
        contexts = self._get_selected_contexts(selection, require_file_nodes=False)
        if not contexts:
            return
        shaders = list(dict.fromkeys(m for c in contexts for m in c["materials"]))
        lightmaps = [c["lightmap"] for c in contexts if c.get("lightmap")]
        try:
            count = self.engine.select_objects(shaders=shaders, lightmaps=lightmaps)
        except Exception as e:  # noqa: BLE001 -- said, never raised at the user
            self.sb.message_box(f"Failed to select objects: {e}")
            return
        self.sb.message_box(
            f"Selected <hl>{count}</hl> object(s)."
            if count
            else "No scene objects use the selected row(s)."
        )

    def select_file_node(self, selection=None):
        """Select the selected rows' texture nodes."""
        nodes = [
            n for c in self._get_selected_contexts(selection) for n in c["file_nodes"]
        ]
        if not nodes:
            return
        count = self.engine.select_file_nodes(nodes)
        self.sb.message_box(
            f"Selected <hl>{count}</hl> texture node(s)."
            if count
            else "No texture node uses the selected texture(s)."
        )

    def row_show_in_hypershade(self, selection=None):
        """Graph the selected rows' textures in the node editor."""
        nodes = [
            n for c in self._get_selected_contexts(selection) for n in c["file_nodes"]
        ]
        if nodes:
            self.engine.graph_file_nodes(nodes)

    def delete_file_node(self, selection=None):
        """Delete the selected rows' texture nodes, confirmed with what it would
        unwire; a lightmap row reverts its objects (:meth:`_remove_lightmaps`)."""
        everything = self._get_selected_contexts(selection, require_file_nodes=False)
        lightmaps = [c["lightmap"] for c in everything if c.get("lightmap")]
        if lightmaps:
            self._remove_lightmaps(lightmaps)
        nodes = list(dict.fromkeys(n for c in everything for n in c["file_nodes"]))
        label = self.labels["delete"]
        if not nodes:
            if not lightmaps and everything:
                self.sb.message_box(f"{label}: the selected row(s) hold no texture.")
            return
        names = [self._leaf(n) for n in nodes]
        shown = ", ".join(names[:4]) + (
            f", +{len(names) - 4} more" if len(names) > 4 else ""
        )
        message = f"<b>{label}</b> &mdash; <hl>{shown}</hl>?"
        for line in self.engine.delete_consequences(nodes):
            message += f"<br>{line}"
        if self.sb.message_box(message, "Yes", "No") != "Yes":
            return
        try:
            count = self.engine.delete_file_nodes(nodes)
        except Exception as e:  # noqa: BLE001 -- said, never raised at the user
            self.sb.message_box(f"{label} failed: {e}")
            return
        self.sb.message_box(f"{label}: <hl>{count}</hl> removed.")
        self.refresh_texture_table()

    def _remove_lightmaps(self, deps) -> int:
        """Revert the objects each lightmap in *deps* binds to source.

        The Lightmap Baker's Revert Selected, scoped to those objects and
        confirmed first: their markers are cleared and the manifest republished,
        so nothing is left bound to the map. Their materials and texture UVs
        were never changed, and the map stays on disk. The reflection probe
        binds no object, and an object a linked library brings is its
        library's: both are named, never reverted. One undo step.

        Returns:
            How many objects were cleared.
        """
        unbound = [dep["map"] for dep in deps if not dep.get("objects")]
        bound = [dep for dep in deps if dep.get("objects")]
        objects, kept = self.engine.lightmap_revert_scope(bound) if bound else ([], [])
        names = ", ".join(dep["map"] for dep in bound[:4])
        if len(bound) > 4:
            names += f", +{len(bound) - 4} more"
        if not objects:
            if kept:
                self.sb.message_box(
                    f"Revert to Source: <hl>{names}</hl> is bound by linked "
                    f"object(s) {', '.join(kept)} only; revert it in their library."
                )
            elif unbound:
                self.sb.message_box(
                    f"Revert to Source: {', '.join(unbound)} binds no object "
                    "(the reflection probe) -- re-bake without a probe to drop it."
                )
            return 0
        question = (
            f"<b>Revert to Source</b> &mdash; the {len(objects)} object(s) lit by "
            f"<hl>{names}</hl>?<br><br>Removes their lightmap wiring: each "
            "object's lightmap record and its entry in the scene's lightmap "
            "export data. Their materials and texture UVs were never changed, and "
            "the map file stays on disk. One Undo restores the wiring."
        )
        if kept:
            question += (
                f"<br>Left as they are: {', '.join(kept)} (linked -- their library's)."
            )
        if self.sb.message_box(question, "Yes", "No") != "Yes":
            return 0
        cleared = self.engine.revert_lightmaps(objects)
        self.sb.message_box(
            f"Reverted <hl>{len(cleared)}</hl> object(s) to source (unbound from "
            f"{names}; the map stays on disk)."
        )
        self.refresh_texture_table()
        return len(cleared)

    # ------------------------------------------------------------------
    # Find & Copy
    # ------------------------------------------------------------------

    def _find_and_copy_workflow(
        self, file_nodes, relocate_mode="copy", scope_label="", lightmaps=None
    ):
        """Open the Find & Copy panel over *file_nodes*, or re-seed and raise it.

        The scope is captured HERE, not re-read when Run is pressed: the row
        selection can change behind a modeless window, and a button reading
        "Copy 12 texture(s)" that relocates three is the exact mismatch this
        panel exists to remove. Re-issuing the command re-seeds it; the footer
        names the scope so which one is loaded is visible.
        """
        self._find_copy_nodes = [str(n) for n in file_nodes]
        self._find_copy_mode = relocate_mode
        self._find_copy_scope_label = scope_label
        self._find_copy_lightmaps = list(lightmaps or [])

        panel = self._find_copy_panel
        if panel is None:
            panel = self.sb.form_panel(
                self._find_and_copy_scope_fields(),
                title="Find & Copy Textures",
                parent=getattr(self, "ui", None),
                # Callable: the mode lives ON the form, so a fixed verb here
                # would contradict the combo the moment it is changed.
                ok_text=self._find_and_copy_ok_text,
                validate=self._validate_find_and_copy,
                help_text=self._find_and_copy_help_text(),
                on_run=self._run_find_and_copy,
                # A tool window sized once and reopened all week.
                settings=self._find_copy_settings(),
            )
            self._find_copy_panel = panel
        else:
            panel.set_fields(self._find_and_copy_scope_fields())

        panel.footer.setDefaultStatusText(
            f"Scope: {scope_label}" if scope_label else ""
        )
        panel.present()
        return panel

    def _find_copy_settings(self):
        """The Find & Copy panel's geometry store, or None when the switchboard
        has none (a panel that cannot remember its size is a smaller loss than a
        tool that will not open)."""
        store = getattr(self.sb, "settings", None)
        if store is None:
            return None
        return store.branch("find_and_copy_textures")

    def _find_and_copy_scope_fields(self):
        """Field specs for the scope the panel is pointed at -- re-partitioned on
        every call: a reopen after Resolve Missing must not still claim the
        textures it just fixed are unresolved."""
        return self._find_and_copy_fields(
            self._find_copy_nodes,
            self.engine.unresolved_file_nodes(self._find_copy_nodes),
            self.engine.texture_dir(),
            self._find_copy_mode,
            lightmaps=self._find_copy_lightmaps,
        )

    def _find_and_copy_fields(
        self, node_names, unresolved, texture_dir, relocate_mode="copy", lightmaps=None
    ):
        """The Find & Copy rows: operation (dry run beside it), search folder,
        destination.

        *lightmaps* count toward the search hint: a missing lightmap is as much
        "something to find" as a broken texture. They get no row of their own:
        the scope already says what this runs over.

        The source row is DISABLED, not hidden, when every path resolves: the
        reason is the answer to the question a missing row would raise.

        Pure: no Qt, no scene writes beyond reading the stored paths.

        Returns:
            list[dict]: specs for ``sb.form_panel`` -- ``mode`` (carrying
            ``dry_run`` inline), ``source_dir``, ``dest_dir``.
        """
        # Counted from the NODES: two nodes reading one texture are two to
        # relocate.
        total = len(node_names)
        resolved_count = total - len(unresolved)
        mode_labels = {key: label for label, key in self._FIND_MODE_ITEMS}
        initial_mode = mode_labels.get(relocate_mode, self._FIND_MODE_ITEMS[0][0])

        # What the search folder is FOR: the textures that do not resolve and
        # the lightmaps found nowhere -- one list, since one folder serves both.
        wanted = [
            posixpath.basename(self.engine.stored_path(n).replace("\\", "/")) or str(n)
            for n in unresolved
        ]
        wanted.extend(d["map"] for d in (lightmaps or []) if not d.get("path"))

        # Counted off ``wanted``, never off ``total``: a lightmap-only scope has
        # no texture nodes, and a count of 0 in the one line always on screen
        # makes the rest of the form untrusted.
        if wanted:
            listed = ", ".join(wanted[:3])
            if len(wanted) > 3:
                listed += f", +{len(wanted) - 3} more"
            skipped = "Leave it empty to skip them"
            if resolved_count:
                skipped += f" and relocate the {resolved_count} that already resolve"
            source_hint = (
                f"Searched recursively for {len(wanted)} unresolved "
                f"texture(s): {listed}. {skipped}. A path that already "
                "resolves is its own source and is never searched for — it "
                "is the file the scene is rendering."
            )
            source_placeholder = f"{len(wanted)} path(s) require a search dir"
        else:
            source_hint = (
                f"All {total} path(s) resolve — every texture is its own source, "
                "so nothing needs finding."
                if total
                else "Nothing in scope needs finding — every path already resolves."
            )
            source_placeholder = "No path requires a search dir"

        # Order is the reading order of the decision: what to do (and whether to
        # commit it -- dry run rides the operation row), where to look, where it
        # lands.
        return [
            {
                "name": "mode",
                "kind": "choice",
                "label": "Operation:",
                "label_align": "right",
                "items": [label for label, _key in self._FIND_MODE_ITEMS],
                "value": initial_mode,
                "hint": (
                    "Copy duplicates each texture into the destination; "
                    "Move removes the original after a successful copy."
                ),
                "inline": [
                    {
                        "name": "dry_run",
                        "kind": "check",
                        "label": "Dry run (preview only)",
                        "hint": (
                            "Report exactly what would be relocated and "
                            "repathed without touching a file or a path, then "
                            "arm <b>Apply</b> to commit the report on screen. "
                            "The preview and the commit derive every "
                            "destination through the same call, so what Apply "
                            "writes is what was previewed."
                        ),
                    }
                ],
            },
            {
                "name": "source_dir",
                "kind": "dir",
                "label": f"{self._DIALOG_MARK_SOURCE} Search in",
                "hint": source_hint,
                "placeholder": source_placeholder,
                "enabled": bool(wanted),
            },
            {
                "name": "dest_dir",
                "kind": "dir",
                "label": f"{self._DIALOG_MARK_DEST} Copy into",
                "value": texture_dir,
                "hint": (
                    f"The {total} texture(s) land HERE and are repointed at "
                    "them. Paths become relative when this folder is inside the "
                    "project."
                ),
            },
        ]

    def _find_and_copy_ok_text(self, values) -> str:
        """Accept-button text -- the verb chosen ON the form and the real count;
        a ticked Dry Run retitles it to what it will do: preview."""
        total = len(self._find_copy_nodes)
        lightmaps = len(self._find_copy_lightmaps)
        what = f"{total} texture(s)"
        if lightmaps:
            what = (
                f"{what} + {lightmaps} lightmap(s)"
                if total
                else f"{lightmaps} lightmap(s)"
            )
        if values.get("dry_run"):
            return f"Preview {what}"
        mode = values.get("mode") or self._FIND_MODE_ITEMS[0][0]
        return f"{mode} {what}"

    def _find_and_copy_help_text(self) -> str:
        """Rich text behind the Find & Copy panel's ``?``."""
        return self.sb.tooltip.fmt(
            title="Find &amp; Copy Textures",
            body="Gather the files behind the scoped textures, relocate them into "
            "one destination, and repoint the textures at them.",
            sections=[
                (
                    "The rows",
                    [
                        "<b>Operation</b> — Copy duplicates each texture; Move "
                        "removes the original after a successful copy.",
                        "<b>Search in</b> — searched recursively, and only for "
                        "paths that do not already resolve. Leave it empty to "
                        "skip those and relocate the rest.",
                        "<b>Copy into</b> — where the textures land. Created if "
                        "it does not exist; paths become relative when it is "
                        "inside the project.",
                        "<b>Dry run</b> — report what would happen without "
                        "touching anything, then press <b>Apply</b> in the "
                        "footer to commit exactly what was reported.",
                    ],
                ),
            ],
            notes=[
                "Lightmaps in the scope ride along — there is no row for them, "
                "because the selection that opened this panel already said so. "
                "No texture node references a baked map, so this is the one "
                "command that relocates them: searched and copied like the "
                "textures, then every marker is repointed at the destination "
                "and the FBX manifest republished.",
                "Source and destination may not be the same folder — nothing "
                "would move, and the run would report success.",
                "What the search did not find is named at the end of the "
                "report; those textures keep their current path.",
                "Collision policy: same-name + same-size files rebind without "
                "overwriting; different-size hits skip with a warning.",
            ],
        )

    def _run_find_and_copy(self, values):
        """The panel's Run -- over whatever scope the panel is pointed at."""
        return self._run_find_and_copy_over(
            list(self._find_copy_nodes), values, list(self._find_copy_lightmaps)
        )

    def _run_find_and_copy_over(self, node_names, values, lightmaps=None):
        """Preview or commit *node_names* (+ *lightmaps*), reporting into the panel.

        Returns the call that WOULD commit when this pass was a preview -- the
        panel's contract for arming its Apply button: this same method with the
        preview off, over the scope and answers AS THEY WERE PREVIEWED, so Apply
        commits the report on screen even if the selection or the form has moved
        on since.
        """
        panel = self._find_copy_panel
        dry_run = bool(values.get("dry_run"))
        lightmaps = list(self._find_copy_lightmaps if lightmaps is None else lightmaps)
        # The engine reports into the pane being watched for the duration.
        self.engine.active_logger = getattr(panel, "logger", None)
        try:
            planned = self.engine.find_and_copy_textures(
                node_names,
                values,
                lightmaps=lightmaps,
                dry_run=dry_run,
                progress=partial(self._progress, panel),
            )
        finally:
            self.engine.active_logger = None
        self.refresh_texture_table()
        if not (dry_run and planned):
            return None
        return partial(
            self._run_find_and_copy_over,
            node_names,
            dict(values, dry_run=False),
            lightmaps,
        )

    @contextlib.contextmanager
    def _progress(self, host, text):
        """The engine's ``progress(text)``: the footer bar of *host* (the panel
        running the command -- feedback on the window being watched) as a
        ``callback(done, total)``."""
        with self.sb.progress(host or self.ui, text=text) as update:
            yield self.sb.progress_adapter(update)

    @staticmethod
    def _validate_find_and_copy(values):
        """Refuse a form that cannot do what it says, and say why: aiming the
        destination at the folder being searched relocates nothing, reports
        success, and leaves the user believing the textures moved."""
        dest = values.get("dest_dir") or ""
        source = values.get("source_dir") or ""
        if not dest:
            return "Pick a destination — this is where the textures will land."
        if source and os.path.normcase(os.path.abspath(source)) == os.path.normcase(
            os.path.abspath(dest)
        ):
            return (
                "Search folder and destination are the same — nothing would "
                "move. The destination is where the textures LAND."
            )
        return ""

    # ------------------------------------------------------------------
    # Scene changes
    # ------------------------------------------------------------------

    def _setup_scene_change_callback(self, widget):
        """Refresh on the engine's scene events (the host's script-job manager),
        unsubscribed when the table goes."""
        manager = self.tk.ScriptJobManager.instance()
        for event, visible_only in self.engine.SCENE_EVENTS:
            manager.subscribe(
                event,
                lambda w=widget, v=visible_only: self._on_scene_change(w, v),
                owner=self,
            )
        manager.connect_cleanup(widget, owner=self)

    def _on_scene_change(self, widget, visible_only: bool = False):
        """One refresh per idle. Pending is "shown" (an undo: skips a hidden
        table) or "always" (a scene event) -- and a scene event outranks a
        waiting undo rather than being swallowed by it."""
        pending = self._refresh_pending
        self._refresh_pending = (
            "shown" if visible_only and pending in (False, "shown") else "always"
        )
        if pending:
            return

        def do_refresh():
            mode, self._refresh_pending = self._refresh_pending, False
            try:
                try:
                    visible = widget.isVisible()
                except RuntimeError:  # the widget's C++ object is gone
                    self.cleanup_scene_callbacks()
                    return
                if mode == "shown" and not visible:
                    return
                self.engine.previous_paths.clear()
                self._refresh_table_content(widget)
            except Exception as e:  # noqa: BLE001 -- a refresh must never raise
                self.logger.warning(
                    f"Error refreshing the table on a scene change: {e}"
                )

        # Deferred: the host fires these mid-load (and mid-undo).
        self.sb.QtCore.QTimer.singleShot(0, do_refresh)

    def cleanup_scene_callbacks(self):
        """Drop the scene-change subscriptions."""
        self.tk.ScriptJobManager.instance().unsubscribe_all(self)

    # ------------------------------------------------------------------
    # Footer
    # ------------------------------------------------------------------

    def _create_footer_controller(self):
        footer = getattr(self.ui, "footer", None)
        if not footer or not hasattr(footer, "status_controller"):
            return None
        return footer.status_controller(
            resolver=self._footer_status_text,
            default_text="",
            truncate_kwargs={"length": 96, "mode": "middle"},
        )

    def _footer_status_text(self) -> str:
        """Footer line: the texture folder every path command resolves against,
        labelled by the folder's own name (the project may call it anything: a
        footer reading SOURCEIMAGES over ``/textures`` would contradict itself)."""
        path = self.engine.texture_dir()
        if not path:
            return ""
        label = ptk.FileUtils.format_path(path, "dir").upper()
        return f"{label}: {path}" if label else path
