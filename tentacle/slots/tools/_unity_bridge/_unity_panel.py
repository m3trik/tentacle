# !/usr/bin/python
# coding=utf-8
"""What every Unity panel shares: the 'Unity Project' row, the Editor combo, script management.

:class:`UnityPanelMixin` is mixed into each Unity panel's Slots class, listed
FIRST among its bases so its hooks override :class:`uitk.bridge.BridgeSlotsBase`'s
defaults: the selection-driven ``UnityBridgeSlots`` (one class for Maya and
Blender) and the standalone, model-file-driven ``UnityWorkflowSlots``. The panels differ
only in what they send (the engine from ``make_bridge``, the parameter registry,
the ``b000`` send action, the help text); the two combo modes, the project
actions, the Editor-version combo and the Manage Unity Scripts flow are this one
implementation.

``unitytk`` is optional in every host (installed on demand), so it is imported
inside the methods that use it; so is ``qtpy``, which only the New Unity Project
dialogs need.
"""

import os
from pathlib import Path


_PKG_DIR = Path(__file__).resolve().parent


class UnityPanelMixin:
    """Unity-panel behavior shared by both Unity Slots classes.

    Per-host hooks the panel class provides: ``params_module``, ``make_bridge``,
    ``b000`` (calling :meth:`_run_manage_mode` first) and, where the install
    prompt should name the panel differently, :attr:`UNITY_FEATURE`. The panel's
    ``__init__`` calls :meth:`_populate_unity_rows` once the base has built the
    parameter widgets.
    """

    # Manage Unity Scripts needs TemplateDeployer.components() / .run_action(), which
    # landed in unitytk 0.0.8, and 0.1.0 moved the templates into one folder per
    # component: an older deployer knows only the flat names, so its Install / Update
    # writes flat copies beside the moved ones (every class twice; the package's
    # assembly stops compiling). The floor rides on the requirement string so the
    # probe, the prompt and pip all read one value; `pyproject.toml`'s [unity] extra
    # only constrains a FRESH install, so a session carrying the older release would
    # otherwise keep using it.
    UNITYTK_REQ = "unitytk>=0.1.0"

    #: The feature named by the install prompt (Manage Unity Scripts -> Install).
    UNITY_FEATURE = "Unity Bridge"

    # The required path row IS the Unity project (folder with Assets/).
    REQUIRE_OUTPUT_DIR = True
    OUTPUT_DIR_LABEL = "Unity Project:"
    OUTPUT_DIR_PLACEHOLDER = "(folder containing Assets/)"

    # The combo picks a MODE, not a template file, and ``template_dir`` is the
    # package's own directory -- so the template-management rows would offer to
    # re-scan nothing and to reveal source code.
    TEMPLATE_MENU = False

    # Two combo entries: the delivery (copy into Assets/), and the unitytk script
    # management flow (status / install-update / uninstall of the embedded
    # com.m3trik.unitytk package) -- panel-native, driven by its own
    # SCRIPTS_ACTION parameter rather than a buried menu button.
    MODE_COPY = "copy_to_assets"
    MODE_MANAGE = "manage_scripts"
    MODE_LABELS = {
        MODE_COPY: "Copy to Project",
        MODE_MANAGE: "Manage Unity Scripts",
    }

    #: Params owned by the Manage Unity Scripts template (hidden in copy mode).
    SCRIPT_PARAM_KEYS = frozenset({"SCRIPTS", "SCRIPTS_ACTION"})

    # The project actions (Set / Open / New) live on the Unity Project field's
    # option menu (see _configure_output_dir_options), co-located with the field
    # they act on; the header keeps just Clear Log.
    HEADER_MENU_ITEMS = (
        ("Clear Log", "btn_clear_log", "Clear the log panel below.", "clear_log"),
    )

    # ------------------------------------------------------------------ base-class hooks
    @property
    def template_dir(self) -> Path:
        # No script templates (copy-to-assets renders nothing); the package dir is
        # a harmless stand-in for the (no-op) per-template description lookup.
        return _PKG_DIR

    def list_template_modes(self):
        return [(self.MODE_COPY, ""), (self.MODE_MANAGE, "")]

    def _format_combo_label(self, template, mode):
        # Friendly label over the internal stem.
        return self.MODE_LABELS.get(template, template)

    def default_output_dir(self) -> str:
        # No scene/workspace fallback -- a DCC scene dir isn't a Unity project.
        return ""

    def _file_bridge(self):
        """unitytk's file-input engine (``FileToUnityBridge``), or ``None`` while
        unitytk is absent -- a reportable state, not an import error the panel
        can't survive. SILENT, for a ``make_bridge`` that runs from ``__init__``
        (a modal raised from a constructor strands itself); installing is the
        explicit Manage Unity Scripts > Install. Here beside the mixin's other
        unitytk reads, so the optional package is imported in one module.
        """
        if not self.optional_package_available("unitytk"):
            return None

        from unitytk import FileToUnityBridge

        return FileToUnityBridge()

    def _selected_template(self) -> str:
        """The combo's mode stem; :attr:`MODE_COPY` before the combo populates."""
        pair = self._selected_template_mode()
        return pair[0] if pair else self.MODE_COPY

    def _relevant_param_keys(self):
        # Copy-to-assets shows every delivery param; Manage Unity Scripts shows
        # its script checklist + action combo. Explicit (not file-driven) so
        # visibility never silently depends on the absence of a template file
        # in the package dir.
        if self._selected_template() == self.MODE_MANAGE:
            return set(self.SCRIPT_PARAM_KEYS)
        return set(self.params_module.PARAMS) - self.SCRIPT_PARAM_KEYS

    def _configure_output_dir_options(self, edit) -> None:
        """Unity Project field: recent-history button + an option menu of project
        actions (Set Project / Open / New), co-located with the field they act on.
        Overrides the base browse-button default.
        """
        self._add_recent_output_dir_option(edit)
        menu = edit.option_box.menu  # the option-menu (▾) button + its Menu
        for label, name, tooltip, handler in (
            (
                "Set Project…",
                "btn_set_project",
                "Browse for the Unity project folder (the one containing 'Assets/').",
                self._pick_output_dir,
            ),
            (
                "Open Unity Project",
                "btn_open_project",
                "Reveal the configured Unity project folder in Explorer.",
                self._open_project_folder,
            ),
            (
                "New Unity Project…",
                "btn_new_project",
                "Create a new Unity project (pick a version + location) and load it\n"
                "into the field above. Uses the selected Unity Version.",
                self._new_unity_project,
            ),
        ):
            menu.add(
                "QPushButton", setText=label, setObjectName=name, setToolTip=tooltip
            )
            getattr(menu, name).clicked.connect(handler)

    # ------------------------------------------------------------------ Unity helpers
    def _populate_unity_rows(self) -> None:
        """Fill the rows discovered at runtime from the installed unitytk release:
        the UNITY_VERSION combo and the SCRIPTS checklist. Call once from the
        panel's ``__init__``, after the base has built the parameter widgets.
        """
        # Components of the deployable C# set, discovered from the installed
        # unitytk release; empty when it is absent (see _populate_script_components).
        self._script_components = []
        self._populate_unity_versions()
        self._populate_script_components()

    def _populate_unity_versions(self) -> None:
        """Fill the UNITY_VERSION combo from the installed Editors (newest first).

        The 'Auto (newest)' entry (data "") is the registry default; discovered
        versions are appended so the user can pin which Editor creates/launches.
        """
        widget = self._param_widgets.get("UNITY_VERSION")
        if widget is None:
            return
        try:
            from unitytk import UnityFinder

            editors = UnityFinder.find_editors()
            # Numeric, not string, order: '2022.3.9f1' > '2022.3.10f1' as text.
            # Inside the try so an import failure keeps the empty-combo fallback.
            ranked = sorted(editors, key=UnityFinder.version_sort_key, reverse=True)
        except Exception:  # noqa: BLE001
            ranked = []
        for ver in ranked:
            widget.addItem(ver, ver)

    def _open_project_folder(self) -> None:
        """Reveal the configured Unity project folder."""
        self.reveal_folder(self.resolved_output_dir())

    def _populate_script_components(self) -> None:
        """Fill the SCRIPTS checklist from unitytk's deployable components.

        Dynamic like the version combo: one checkable row per import channel,
        read from the installed unitytk release — a controller added to the
        C# bundle appears here with no panel edit. Everything starts checked
        (the historical full-set deploy). The shared core files aren't listed:
        they ride along with every install and leave with the last script.

        Silent when unitytk is absent — the row stays empty and the actions
        fall back to the full set (see :meth:`_script_selection`).
        """
        widget = self._param_widgets.get("SCRIPTS")
        if widget is None:
            return
        try:
            from unitytk import TemplateDeployer

            components = [c for c in TemplateDeployer.components() if not c.required]
        except Exception:  # noqa: BLE001
            components = []
        if not components:
            return
        self._script_components = components
        self._set_param_choices(
            "SCRIPTS", [(c.label, c.key, c.summary) for c in components]
        )
        self._write_param("SCRIPTS", [c.key for c in components])

    def _script_selection(self):
        """The checked component keys, or ``None`` when the checklist never
        populated (unitytk absent at panel build) — ``None`` means the full
        set, so the action still does the obvious thing."""
        if not self._script_components:
            return None
        return list(self._read_param("SCRIPTS"))

    def _run_manage_mode(self) -> bool:
        """Run the Manage Unity Scripts action when that mode is selected.

        Returns:
            True when it ran (the panel's ``b000`` is then done), False in the
            copy mode, where the panel's own send runs.
        """
        if self._selected_template() != self.MODE_MANAGE:
            return False
        action = self.collect_param_values().get("SCRIPTS_ACTION", "status")
        self._manage_unity_scripts(action)
        return True

    def _manage_unity_scripts(self, action: str) -> None:
        """Run the Manage Unity Scripts template's chosen *action* over the
        scripts checked in the panel.

        Status / install-update / uninstall of the embedded
        ``Packages/com.m3trik.unitytk`` UPM package in the configured project.
        The work and its reporting live in
        :meth:`unitytk.TemplateDeployer.run_action` (one implementation for
        every Unity panel); this owns the panel-side preconditions and logs
        via :meth:`panel_log` — every branch here must be able to report while
        the optional engine is missing.
        """
        project = self.resolved_output_dir()
        if not project:
            self.panel_log(
                "Set the Unity Project folder first (the one containing 'Assets/').",
                "error",
            )
            if self._output_dir_edit is not None:
                self._output_dir_edit.setFocus()
            return

        if action == "install":
            # Explicit action — prompting to install the DCC-side unitytk
            # package is appropriate here (and only here).
            if not self.ensure_optional_package(
                self.UNITYTK_REQ, feature=self.UNITY_FEATURE
            ):
                return
            # Engine just arrived: fill the checklist that built empty, so the
            # run below deploys the real set. Guarded — a re-populate would
            # re-check every row and throw away the user's selection.
            if not self._script_components:
                self._populate_script_components()
        elif not self.optional_package_available(self.UNITYTK_REQ):
            self.panel_log(
                f"This panel needs {self.UNITYTK_REQ} — it is not installed in this "
                "session, or is older than that. Run the 'Install / Update' "
                "action first.",
                "error",
            )
            return
        from unitytk import TemplateDeployer

        for level, message in TemplateDeployer.run_action(
            project, action, self._script_selection()
        ):
            self.panel_log(message, level)

    def _new_unity_project(self) -> None:
        """Create a new Unity project (version + location) and load it into the field."""
        from qtpy import QtCore, QtWidgets
        from unitytk import UnityLauncher

        version = (
            self._read_param("UNITY_VERSION")
            if "UNITY_VERSION" in self._param_widgets
            else ""
        ) or None
        launcher = UnityLauncher(executable_path=version)
        if not launcher.executable_path:
            self.bridge.logger.error(
                "No Unity Editor found to create a project. Install one via Unity Hub."
            )
            return

        parent = QtWidgets.QFileDialog.getExistingDirectory(
            self.ui, "Choose where to create the new project", str(Path.home())
        )
        if not parent:
            return
        name, ok = QtWidgets.QInputDialog.getText(
            self.ui, "New Unity Project", "Project name:"
        )
        name = (name or "").strip()
        if not ok or not name:
            return
        target = os.path.join(parent, name)
        if os.path.exists(target):
            self.bridge.logger.error(f"Target already exists: {target}")
            return

        self.bridge.logger.info(
            f"Creating Unity project at {target} (batch mode; this can take a minute)…"
        )
        QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
        try:
            created = launcher.create_project(target)
        except Exception as e:  # noqa: BLE001
            self.bridge.logger.error(f"Project creation failed: {e}")
            return
        finally:
            QtWidgets.QApplication.restoreOverrideCursor()

        if created and self._output_dir_edit is not None:
            self._output_dir_edit.setText(target)
            self._record_output_dir(target)
            self.bridge.logger.info(f"Created project at {target}")
        elif not created:
            self.bridge.logger.error(f"Project creation did not complete at {target}.")
