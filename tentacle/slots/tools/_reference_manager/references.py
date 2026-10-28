# !/usr/bin/python
# coding=utf-8
"""The Reference Manager's reference actions: a row's reference and display
toggles, and unlink / remove / convert across the scene's references.

Private to :mod:`tentacle.slots.tools.reference_manager`; a collaborator of the
panel's controller (:mod:`.controller`). What a reference is is the engine's
(Maya: a file reference under a namespace; Blender: a linked library).
"""

import html
import os


class ReferenceActions:
    """The row and bulk reference actions (see the module docstring)."""

    #: Display-mode click cycle: Normal -> Reference -> Template -> Normal.
    DISPLAY_MODE_CYCLE = {
        "off": "reference",
        "reference": "template",
        "template": "off",
    }

    #: The namespace button beside Unlink and Import All, per engine namespace mode:
    #: its glyph and tooltip. uitk persists the state by INDEX, so the engine's
    #: ``NAMESPACE_MODES`` order is append-only; index 0 (remove) is the default.
    UNLINK_NAMESPACE_STATES = {
        "remove": (
            "merge",
            "Namespace: Remove — merged into the scene; every node loses the prefix.",
        ),
        "keep": ("tag", "Namespace: Keep — every imported node stays prefixed."),
        "root": (
            "branch",
            "Namespace: Keep On Root — only the asset's top-level node(s) keep the "
            "prefix; everything below is merged into the scene.",
        ),
    }

    #: Named in the confirm prompt, so the choice is never a hidden setting.
    UNLINK_MODE_LABELS = {
        "remove": "namespaces are <b>removed</b> — every node loses its prefix",
        "keep": "namespaces are <b>kept</b> on every imported node",
        "root": "namespaces are kept on the <b>top-level node(s) only</b>",
    }

    def __init__(self, controller):
        self.c = controller

    def toggle_reference_at_row(self, row, col=None):
        """Reference the row's file, or remove the references it stands for.

        A file is either open or referenced, never both: referencing the open scene
        closes it first (guarded). A foreign row bakes its source and references the
        bake; a second click removes it again -- the bake's record maps it back.
        """
        table = self.c.ui.tbl000
        item = table.item(row, self.c.COL_NAME)
        path = item.data(self.c.role(self.c.ROLE_PATH)) if item else None
        if not path:
            return
        refs = self.c.row_references(path)
        if refs:
            self.c.engine.remove_references([ref.namespace for ref in refs])
            table.actions.set(row, self.c.COL_REF, "unreferenced")
            table.actions.set(row, self.c.COL_DISPLAY, "unavailable")
            self.c.select_item_silently(item, False)
            self.c.sync_reference_icons()
            return
        closed_current = self.c.engine.is_current(path)
        if closed_current and not self.c.files.close_scene():
            return  # unsaved changes kept
        namespace, ref_path = item.text(), path
        if self.c.engine.is_foreign(path):
            # The bake's name is a cache hash and the label may be shortened: the
            # source's own stem names the namespace.
            namespace = os.path.splitext(os.path.basename(path))[0]
            ref_path = self.c.files.bake_foreign_path(
                path, project=self.c.engine.bake_project_root()
            )
            if not ref_path:
                return
        try:
            ok = self.c.engine.add_reference(namespace, ref_path)
        except (RuntimeError, OSError) as e:
            self.c.error_box("Reference failed for", os.path.basename(path), e)
            return
        if not ok:
            return
        table.actions.set(row, self.c.COL_REF, "referenced")
        modes = [
            self.c.engine.get_reference_display_mode(r)
            for r in self.c.row_references(path)
        ]
        table.actions.set(
            row, self.c.COL_DISPLAY, next((m for m in modes if m != "off"), "off")
        )
        if not self.c.engine.is_foreign(path):
            # Silently: when this row was the just-closed scene its cell is still
            # non-selectable, and an unblocked select would read as a deselect that
            # removes the reference just made (the two-click bug).
            self.c.select_item_silently(item, True)
        if closed_current:
            self.c.refresh_file_list()  # the row is no longer the current scene
        else:
            self.c.sync_reference_icons()

    def cycle_display_mode_at_row(self, row, col=None):
        """Cycle the row's references' display: Normal -> Reference -> Template."""
        table = self.c.ui.tbl000
        refs = self.c.row_references(self.c.row_path(row) or "")
        if not refs:
            # Removed elsewhere between the sync and this click: show the truth.
            table.actions.set(row, self.c.COL_DISPLAY, "unavailable")
            return
        modes = [self.c.engine.get_reference_display_mode(r) for r in refs]
        current = next((m for m in modes if m != "off"), "off")
        new_mode = self.DISPLAY_MODE_CYCLE.get(current, "off")
        if not any(
            [self.c.engine.set_reference_display_mode(r, new_mode) for r in refs]
        ):
            self.c.message(
                "Display override had no effect — the reference has no objects to update."
            )
            return
        table.actions.set(row, self.c.COL_DISPLAY, new_mode)

    def add_unlink_namespace_action(self, button):
        """Give *button* the cycling namespace-mode action (applies to every unlink);
        none on a host with a single mode (Blender has no namespaces)."""
        modes = tuple(self.c.engine.NAMESPACE_MODES)
        if len(modes) < 2:
            return
        button.option_box.set_action(
            tooltip="Namespace handling on unlink",
            states=[
                {
                    "icon": self.UNLINK_NAMESPACE_STATES[mode][0],
                    "tooltip": f"{self.UNLINK_NAMESPACE_STATES[mode][1]}\n"
                    "Applies to every unlink. Click to cycle.",
                }
                for mode in modes
            ],
        )

    def unlink_namespace_mode(self) -> str:
        """The namespace handling picked beside Unlink and Import All: the engine's
        first mode until the menu is built (an early call)."""
        modes = tuple(self.c.engine.NAMESPACE_MODES)
        if len(modes) < 2:
            return modes[0]
        menu = self.c.header_menu()
        button = (
            getattr(menu, "btn_unlink_import_all", None) if menu is not None else None
        )
        action = (
            button.option_box.find_option(self.c.sb.ActionOption) if button else None
        )
        index = action.current_state if action is not None else 0
        return modes[index % len(modes)]

    def _unlink_mode_sentence(self, mode) -> str:
        """The confirm prompt's word on namespaces (none where there are none)."""
        if len(tuple(self.c.engine.NAMESPACE_MODES)) < 2:
            return ""
        return f"On import, {self.UNLINK_MODE_LABELS.get(mode, mode)}.<br>"

    def ask_scene_data(self, summary, namespace):
        """The unlink question for a reference bringing scene data of its own: merge
        it, drop it, or leave it referenced (the engine asks only when a merge would
        keep something)."""
        lines = "".join(
            f"<br>&nbsp;&nbsp;&bull; {html.escape(str(line), quote=False)}"
            for line in summary
        )
        answer = self.c.message(
            f"<hl>{html.escape(str(namespace), quote=False)}</hl> brings scene data of its own:{lines}<br><br>"
            "<b>Yes</b> merges it into this scene's -- nothing is lost, and anything "
            "renamed or re-slotted on the way is logged.<br>"
            "<b>No</b> drops it with the reference's data nodes.<br>"
            "<b>Cancel</b> leaves this reference linked.",
            "Yes",
            "No",
            "Cancel",
        )
        return {"Yes": "merge", "No": "discard"}.get(answer)

    def unlink_references(self, namespaces):
        """Unlink and import the references named *namespaces* (confirmed)."""
        if not namespaces:
            return
        mode = self.unlink_namespace_mode()
        prompt = f"Unlink {len(namespaces)} reference(s)?<br>{self._unlink_mode_sentence(mode)}"
        if self.c.message(prompt, "Yes", "No") != "Yes":
            return
        with self.c.table_signals_blocked():
            self.c.engine.import_references(
                namespaces=list(namespaces),
                namespace_mode=mode,
                scene_data=self.ask_scene_data,
            )
        self.c.refresh_file_list()

    def unlink_import_row(self):
        """Unlink and Import at the right-clicked row: a referenced row's data made
        local; a foreign or USD row with no reference imported fresh."""
        row = self.c.context_row()
        if row is None:
            self.c.message("No scene selected.")
            return
        path = self.c.row_path(row)
        refs = self.c.row_references(path or "")
        if refs:
            self.unlink_references([ref.namespace for ref in refs])
            return
        if not (path and self.c.is_importable(path)):
            self.c.message(
                "Select a referenced row (to make it local), or a foreign or USD row "
                "(to import it)."
            )
            return
        self.c.files.import_paths([path])

    def unlink_all(self):
        """Unlink and import every reference (confirmed: an unlink is not undoable)."""
        if not self.c.engine.current_references:
            self.c.message("No references to unlink.")
            return
        mode = self.unlink_namespace_mode()
        if (
            self.c.message(
                "<b>Warning:</b> The unlink operation is not undoable.<br>"
                f"{self._unlink_mode_sentence(mode)}Do you want to proceed?",
                "Yes",
                "No",
            )
            != "Yes"
        ):
            return
        with self.c.table_signals_blocked():
            self.c.engine.import_references(
                namespace_mode=mode, scene_data=self.ask_scene_data
            )
        self.c.refresh_file_list()

    def unreference_all(self):
        """Remove every reference from the scene (confirmed). A reference the host
        refuses to drop is named, never left to read as "did nothing"."""
        refs = self.c.engine.current_references
        if not refs:
            self.c.message("No references to remove.")
            return
        if (
            self.c.message(
                f"Remove all {len(refs)} reference(s) from the scene?", "Yes", "No"
            )
            != "Yes"
        ):
            return
        with self.c.table_signals_blocked():
            failed = self.c.engine.remove_references()
        self.c.refresh_file_list()
        if failed:
            names = "<br>".join(
                sorted(html.escape(str(ref.label), quote=False) for ref in failed)
            )
            self.c.message(
                f"{len(failed)} reference(s) could not be removed:<br>{names}"
            )

    def convert_to_assembly(self):
        """Replace every reference with an assembly (confirmed; Maya's scene
        assemblies -- a host without them builds no button)."""
        assemblies = getattr(self.c.tk, "AssemblyManager", None)
        if assemblies is None:
            return
        if (
            self.c.message(
                "<b>Warning:</b> The convert to assembly operation is not undoable."
                "<br>Do you want to proceed?",
                "Yes",
                "No",
            )
            != "Yes"
        ):
            return
        with self.c.table_signals_blocked():
            assemblies.convert_references_to_assemblies()
        self.c.refresh_file_list()
