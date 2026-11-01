# !/usr/bin/python
# coding=utf-8
"""The Reference Manager's scene files: open / close / save / rename / delete, the
Naming conventions Save and Rename apply (and the previews of both), and the
conversions a foreign row runs -- asked up front, run in the footer progress.

Private to :mod:`tentacle.slots.tools.reference_manager`; a collaborator of the
panel's controller (:mod:`.controller`). The host's side is its engine's
(``open_scene``, ``save_scene``, ``rename_scene_file``, ``remove_scene_file``,
``bake_scene``, ``import_scene``).
"""

import contextlib
import html
import os
from typing import Optional, Sequence

import pythontk as ptk
from qtpy import QtCore


class SceneFiles:
    """The scene-file actions (see the module docstring)."""

    #: Max file names listed verbatim in a delete confirmation (the rest fold into
    #: an "...and N more" line).
    DELETE_PROMPT_MAX_NAMES = 10

    def __init__(self, controller):
        self.c = controller
        self._warned_scene_placeholder_typo = False

    def normalize_structure_pattern(self, pattern: str) -> str:
        """The folder-structure pattern as Save reads it
        (``ptk.SceneListing.normalize_structure_pattern``: trimmed, the common
        ``{scene}`` typo read as ``{scenes}``), the typo warned once."""
        if "{scene}" in (pattern or "") and not self._warned_scene_placeholder_typo:
            self._warned_scene_placeholder_typo = True
            self.c.logger.warning(
                "Folder Structure: '{scene}' is not a supported placeholder. "
                "Did you mean '{scenes}'? Auto-correcting for this operation."
            )
        return ptk.SceneListing.normalize_structure_pattern(pattern)

    def default_save_name(self, case_style: str, suffix: str) -> str:
        """The name Save would prepopulate for the open scene
        (``ptk.SceneListing.default_save_name``); '' with no scene."""
        return ptk.SceneListing.default_save_name(
            self.c.engine.current_scene(), case_style, suffix
        )

    def resolve_save_target(self, name, case_style, suffix, pattern) -> str:
        """The absolute path Save To Workspace writes for *name* under the browsed
        workspace (``ptk.SceneListing.save_target``, in the host's scene format) --
        shared by Save and its button's live tooltip, so the preview cannot drift
        from the save.

        Raises:
            ValueError: No valid workspace, or an invalid placeholder pattern.
        """
        return ptk.SceneListing.save_target(
            self.c.workspaces.workspace_dir(),
            name,
            case_style,
            suffix,
            pattern,
            self.c.engine.SCENE_SAVE_EXTENSION,
        )

    def save_scene_preview(self) -> str:
        """Live tooltip for the footer's Save button: the exact path Save would write."""
        case_style, suffix, structure = self.c.naming_options()
        notes = []
        if "{scene}" in structure:
            notes.append("<b>{scene}</b> is not valid — did you mean <b>{scenes}</b>?")
        pattern = structure.replace("{scene}", "{scenes}")
        name = self.default_save_name(case_style, suffix) or "<scene name>"
        try:
            path = self.resolve_save_target(name, case_style, suffix, pattern)
        except ValueError as e:
            path = None
            notes.append(html.escape(str(e), quote=False))
        return self.c.sb.tooltip.fmt(
            title="Save To Workspace",
            body="Save the current scene into the workspace using the header "
            "menu's Naming options: case / suffix / folder structure.",
            rows=[("saves →", f"<b>{html.escape(path, quote=False)}</b>")]
            if path
            else None,
            notes=notes or None,
        )

    def folder_structure_preview(self) -> str:
        """Live tooltip for the Folder Structure field: its placeholders resolved
        against the browsed workspace and the open scene, plus the real save folder.
        Side-effect free: the ``{scene}`` typo is noted, not warned."""
        case_style, suffix, pattern = self.c.naming_options()
        workspace = self.c.workspaces.workspace_dir() or ""
        workspace_name = (
            os.path.basename(os.path.normpath(workspace))
            if workspace
            else "<workspace>"
        )
        notes = ["e.g. {scenes} · {scenes}/{name} · {scenes}/{name}/versions"]
        if "{scene}" in pattern:
            notes.append("<b>{scene}</b> is not valid — did you mean <b>{scenes}</b>?")
        resolve_pattern = ptk.SceneListing.normalize_structure_pattern(pattern)
        context = {
            "scenes": ptk.SceneListing.scenes_folder(workspace),
            "name": self.default_save_name(case_style, suffix) or "<scene name>",
            "workspace": workspace_name,
            "suffix": suffix,
        }
        # The folder Save writes, from Save's own target, so the two cannot
        # drift; where Save would refuse, the reason instead.
        try:
            final = os.path.dirname(
                self.resolve_save_target(
                    context["name"], case_style, suffix, resolve_pattern
                )
            )
        except ValueError as e:
            final = None
            notes.append(html.escape(str(e), quote=False))
        return self.c.sb.tooltip.placeholder_preview(
            resolve_pattern,
            context,
            title="Folder Structure",
            body="Where scenes live, panel-wide: <b>Save To Workspace</b> writes "
            "here, <b>Filter by Folder Structure</b> matches against it, and with "
            "<b>{name}</b> Rename and Delete keep each scene's own folder in step.",
            descriptions={
                "scenes": "workspace scenes folder (its scene file rule)",
                "name": "scene name — excludes the suffix",
                "workspace": "workspace folder name",
                "suffix": "the Suffix field above",
            },
            final=final,
            final_label="save dir →",
            notes=notes,
        )

    def wire_structure_tooltip(self, menu) -> None:
        """Bind the live folder-structure preview once the field's ``.tooltip`` proxy
        is stamped: menu registration is deferred (a coalesced next-tick drain), so
        bind on the following tick, with a small bounded retry."""

        def _bind(attempts_left=5):
            txt = getattr(menu, "txt_subfolder_structure", None)
            proxy = getattr(txt, "tooltip", None) if txt is not None else None
            if proxy is not None:
                proxy.bind(self.folder_structure_preview)
            elif attempts_left > 0:
                QtCore.QTimer.singleShot(0, lambda: _bind(attempts_left - 1))

        QtCore.QTimer.singleShot(0, _bind)

    def open_scene_at_row(self, row, col=None):
        """Open the row's scene -- or close it (a new empty scene) when it already is
        the open one: the Open icon toggles like the reference icon."""
        path = self.c.row_path(row)
        if not path:
            return
        if self.c.engine.is_current(path):
            if self.close_scene():
                self.c.logger.info("Closed the scene (new empty scene).")
                self.c.refresh_file_list()
        else:
            self.open_path(path)

    def confirm_discard_unsaved(self) -> bool:
        """True if it is OK to replace the open scene: nothing unsaved, the user saved,
        or chose to discard. False -- Cancel, or a Save that did not complete --
        cancels the caller's operation."""
        if not self.c.engine.scene_modified():
            return True
        choice = self.c.message(
            "The current scene has changes, do you want to save?",
            "Save",
            "Discard",
            "Cancel",
        )
        if choice == "Save":
            return self.save_current_scene()
        return choice == "Discard"

    def save_current_scene(self) -> bool:
        """Save the open scene in place -- or, when it cannot be written where it came
        from (never saved, or a format the host only reads), through Save To
        Workspace. True once the scene is clean on disk."""
        try:
            saved = self.c.engine.save_open_scene()
        except Exception as e:  # noqa: BLE001 - reported
            self.c.message(
                f"Failed to save the open scene:<br>{html.escape(str(e), quote=False)}"
            )
            return False
        if saved is not None:
            return bool(saved)
        self.save_to_workspace()
        # Save has several bail-outs: the modified flag is the authoritative answer.
        return not self.c.engine.scene_modified()

    def open_path(self, path) -> bool:
        """Open *path*, offering to save the open scene's changes first -- the single
        guarded entry every Open goes through. False when the user backed out or it
        did not open (reported)."""
        if not self.confirm_discard_unsaved():
            return False
        name = os.path.basename(path)
        try:
            opened = self.c.engine.open_scene(path)
        except (OSError, RuntimeError) as e:
            self.c.error_box("Can't open", name, e)
            return False
        if opened and self.c.engine.is_foreign(path):
            self.c.footer_status(
                f"Opened {name} as a new scene, baked from its source: save it into "
                "the workspace to keep it.",
                level="success",
            )
        return bool(opened)

    def close_scene(self) -> bool:
        """Close the open scene (a new empty one), guarding unsaved changes. True if
        it was closed."""
        if not self.confirm_discard_unsaved():
            return False
        if not self.c.engine.new_scene():
            self.c.message("Failed to close the scene.")
            return False
        return True

    def save_to_workspace(self):
        """Save the open scene into the workspace under the Naming conventions,
        prompting for a name (the target is :meth:`resolve_save_target`, what the
        button's tooltip previews)."""
        case_style, suffix, structure = self.c.naming_options()
        default_name = self.default_save_name(case_style, suffix)
        name = self.c.sb.input_dialog(
            "Save Scene", "Enter name for scene:", default_name
        )
        # The conventions append the suffix; one typed into the name would double.
        name = ptk.StrUtils.strip_suffix(name or "", [suffix])
        if not name:
            return
        pattern = self.normalize_structure_pattern(structure)
        try:
            new_path = self.resolve_save_target(name, case_style, suffix, pattern)
        except ValueError as e:
            self.c.message(html.escape(str(e), quote=False))
            return
        target_dir = os.path.dirname(new_path)
        try:
            os.makedirs(target_dir, exist_ok=True)
        except OSError as e:
            self.c.message(
                f"Failed to create directory: {html.escape(str(e), quote=False)}"
            )
            return
        if os.path.exists(new_path) and (
            self.c.message(
                f"File exists:<br>{html.escape(new_path, quote=False)}<br>Overwrite?",
                "Yes",
                "No",
            )
            != "Yes"
        ):
            return
        try:
            self.c.engine.save_scene(new_path)
        except Exception as e:  # noqa: BLE001 - reported
            self.c.message(f"Failed to save scene: {html.escape(str(e), quote=False)}")
            return
        self.c.refresh_file_list(invalidate=True)

    def rename_path(self, old_path, new_path, folder=None, item=None) -> Optional[str]:
        """Rename *old_path* to *new_path* through the engine (the open scene saved and
        reopened; *folder*, the per-scene folder's new name), carry its note, refresh.
        The final path, or None (an *item* being edited gets its label back)."""
        try:
            final = self.c.engine.rename_scene_file(old_path, new_path, folder=folder)
        except Exception as e:  # noqa: BLE001 - reported
            self.c.logger.error(f"Rename failed: {e}")
            self.c.message(f"Rename failed:<br>{html.escape(str(e), quote=False)}")
            final = None
        if not final:
            if item is not None:
                self.c.restore_item_display(item)
            return None
        # The note is keyed by the scene's project-relative path: it follows.
        try:
            self.c.scene_notes.move(old_path, final)
        except Exception as e:  # noqa: BLE001 - the rename stands
            self.c.logger.warning(f"The note of {old_path} did not follow: {e}")
        self.c.refresh_file_list(invalidate=True)
        return final

    def rename_scene(self):
        """Rename the right-clicked row's scene, prompting for the new name under the
        Naming conventions (case + suffix; a ``{name}`` structure moves the scene's
        own folder along)."""
        path = self.c.row_path(self.c.context_row())
        if not path:
            self.c.message("No scene selected.")
            return
        if not os.path.exists(path):
            self.c.message("File not found.")
            return
        old_name = os.path.basename(path)
        old_base, ext = os.path.splitext(old_name)
        case_style, suffix, structure = self.c.naming_options()
        # The conventions append the suffix: neither the prefill nor the answer has it.
        prefill = ptk.StrUtils.strip_suffix(old_base, [suffix])
        answer = self.c.sb.input_dialog("Rename Scene", "Enter new name:", prefill)
        # "Unchanged" is what was TYPED: "hero_v01" for an unsuffixed "hero.ma"
        # strips back to the prefill, yet asks for the suffix.
        if not answer or answer == prefill:
            return
        new_base = ptk.StrUtils.strip_suffix(answer, [suffix])
        if not new_base:
            return
        new_name = ptk.SceneListing.format_name(new_base, case_style, suffix) + ext
        if new_name == old_name:
            return  # the conventions give back the name it already has
        new_path = os.path.join(os.path.dirname(path), new_name)
        if os.path.exists(new_path) and not ptk.FileUtils.is_same_file(new_path, path):
            self.c.message(f"Target file exists: {html.escape(new_path, quote=False)}")
            return
        folder = (
            ptk.SceneListing.format_name(new_base, case_style)
            if "{name}" in structure
            else None
        )
        self.rename_path(path, new_path, folder)

    @classmethod
    def delete_prompt(cls, paths: Sequence[str], permanent: Sequence[str] = ()) -> str:
        """Confirmation text for deleting *paths*.

        Names each file in full: the row label can hide the suffix/extension, so a
        count alone gives no way to confirm WHICH file is about to be removed. And
        it says where each goes: the platform's trash (``ptk.FileUtils.trash_name``),
        or, for *permanent* -- the ones no trash would take (a network share, a
        removable drive) -- gone for good, which it says cannot be undone.
        """
        trash = ptk.FileUtils.trash_name()
        gone = {os.path.normcase(os.path.abspath(p)) for p in permanent}
        marks = [os.path.normcase(os.path.abspath(p)) in gone for p in paths]
        names = [os.path.basename(p) for p in paths]
        if len(names) == 1:
            if marks[0]:
                return (
                    f"Delete <hl>{names[0]}</hl> permanently?<br>The {trash} "
                    "will not take it, so this cannot be undone."
                )
            return f"Move <hl>{names[0]}</hl> to the {trash}?"
        mixed = any(marks) and not all(marks)
        shown = list(zip(names, marks))[: cls.DELETE_PROMPT_MAX_NAMES]
        listed = "<br>".join(
            f"&bull; {n}" + (f" (permanently: no {trash})" if mark and mixed else "")
            for n, mark in shown
        )
        if len(names) > len(shown):
            listed += f"<br>&bull; ...and {len(names) - len(shown)} more"
        if all(marks):
            return (
                f"Delete {len(names)} file(s) permanently?<br>{listed}<br>The "
                f"{trash} will not take them, so this cannot be undone."
            )
        if mixed:
            return (
                f"Delete {len(names)} file(s)?<br>{listed}<br>The rest go to the "
                f"{trash}; the marked ones cannot be undone."
            )
        return f"Move {len(names)} file(s) to the {trash}?<br>{listed}"

    def delete_scene(self):
        """Delete the right-clicked row's scene: to the trash, or -- a drive with none,
        confirmed as permanent -- for good. A trash that refuses it after all asks
        again, as permanent, before anything is lost."""
        path = self.c.row_path(self.c.context_row())
        if not path:
            self.c.message("No scene selected.")
            return
        if not os.path.exists(path):
            return
        permanent = [path] if not ptk.FileUtils.can_trash(path) else []
        if self.c.message(self.delete_prompt([path], permanent), "Yes", "No") != "Yes":
            return
        # {name} in the folder structure: per-scene folders, removed with their last scene.
        use_folder = "{name}" in self.c.naming_options()[2]
        result = self.c.engine.remove_scene_file(
            path, permanent=bool(permanent), use_folder=use_folder
        )
        if result is None and (
            self.c.message(self.delete_prompt([path], [path]), "Yes", "No") == "Yes"
        ):
            result = self.c.engine.remove_scene_file(
                path, permanent=True, use_folder=use_folder
            )
        if result:
            try:
                self.c.scene_notes.remove(path)
            except Exception as e:  # noqa: BLE001 - the delete stands
                self.c.logger.warning(f"The note of {path} was kept: {e}")
        elif result is False:
            self.c.message(
                f"Could not delete <hl>{html.escape(os.path.basename(path), quote=False)}</hl>."
            )
        self.c.refresh_file_list()

    def open_file_location(self):
        """Reveal the right-clicked row's file in the file manager."""
        path = self.c.row_path(self.c.context_row())
        if not path:
            self.c.message("No scene file selected.")
            return
        try:
            ptk.FileUtils.reveal_in_file_manager(path)
        except FileNotFoundError:
            parent = os.path.dirname(os.path.normpath(path))
            self.c.message(
                f"Directory not found:<br>{html.escape(parent, quote=False)}"
            )

    def copy_path(self):
        """Copy the right-clicked row's full path to the clipboard."""
        path = self.c.row_path(self.c.context_row())
        if not path:
            self.c.message("No scene selected.")
            return
        path = os.path.normpath(path)
        self.c.sb.QtWidgets.QApplication.clipboard().setText(path)
        self.c.workspaces.flash_footer(f"Copied: {path}")

    def resolve_rig_mode(self, path):
        """How a foreign scene's rig logic travels: asked only when it has some. The
        ``rig_mode`` for the engine -- one of its ``RIG_MODES``, ``"auto"`` (nothing
        to ask) -- or None when the user cancelled. ``message_box`` takes standard Qt
        button names only, so the outcomes ride Yes / No / Ignore."""
        if not self.c.engine.scene_has_complex_animation(path):
            return "auto"
        modes = self.c.engine.RIG_MODES
        text = (
            f"<hl>{html.escape(os.path.basename(path), quote=False)}</hl> has rig logic (constraints, "
            "IK, drivers or set-driven keys).<br><br><b>Yes</b> = Transfer the rig as "
            "editable relationships where they can be rebuilt here, baking the rest.<br>"
            "<b>No</b> = Bake everything to keyframes."
        )
        buttons = ["Yes", "No"]
        if "raw" in modes:
            text += "<br><b>Ignore</b> = Convert raw (the rig logic is lost)."
            buttons.append("Ignore")
        choice = self.c.message(text, *buttons, "Cancel")
        return {"Yes": "rig", "No": "bake", "Ignore": "raw"}.get(choice)

    def resolve_conversion(self, path):
        """The route + rig mode ``bake_scene`` / ``import_scene`` take for *path*, or
        None when the user cancelled."""
        rig_mode = self.resolve_rig_mode(path)
        if rig_mode is None:
            return None
        return {"via": self.c.foreign_route(), "rig_mode": rig_mode}

    @contextlib.contextmanager
    def conversion_progress(self, text):
        """Footer progress for one conversion; yields the engine's
        ``progress(current, total, message)`` callback. Every tick pumps the UI, and
        an Esc-hold on the bar stops the running child
        (``pythontk.OperationCancelled``)."""
        with self.c.sb.busy_cursor():
            with self.c.sb.progress(
                ui=self.c.ui, total=100, text=text, busy=True
            ) as update:
                yield self.c.sb.progress_adapter(update)

    def bake_foreign_path(self, path, project=None):
        """Bake *path* to the host's cached native scene and return it, or None.

        Asks how a rig travels first (before the progress starts, so the prompt shows
        a normal cursor), then runs the engine's ``bake_scene`` in the footer
        progress: a stop is not a failure, an error is shown. *project* is the project
        whose bake cache keeps it (the engine's default: the open scene's). The
        engine's ``bake_for_reference`` collaborator too.
        """
        conv = self.resolve_conversion(path)
        if conv is None:
            return None
        name = os.path.basename(path)
        try:
            with self.conversion_progress(f"Converting {name}") as progress:
                return self.c.engine.bake_scene(
                    path, progress=progress, project=project, **conv
                )
        except ptk.OperationCancelled:
            self.c.footer_status(f"Stopped converting {name}.")
        except FileNotFoundError as e:
            # The error names what is missing -- the other DCC, or the scene itself.
            self.c.error_box("Can't reference", name, e)
        except Exception as e:  # noqa: BLE001 - surfaced to the user
            self.c.logger.warning(f"Foreign scene bake failed for {path}: {e}")
            self.c.error_box("Reference failed for", name, e)
        return None

    def import_paths(self, paths):
        """Import each row in *paths* as local data with no reference behind it.

        Every question comes up front (a cancelled scene drops out of the batch) so
        none waits between minutes-long conversions; a row that converts nothing (an
        FBX / USD row) asks nothing. A missing converter stops the batch; a missing
        file skips its row only.
        """
        paths = [p for p in (paths or []) if self.c.is_importable(p)]
        if not paths:
            self.c.message("Select a foreign scene or USD row to import.")
            return
        plan = []
        for path in paths:
            if not self.c.engine.needs_conversion(path):
                plan.append((path, {}))
                continue
            conv = self.resolve_conversion(path)
            if conv is not None:
                plan.append((path, conv))
        if not plan:
            return
        total, done = 0, 0
        for path, conv in plan:
            name = os.path.basename(path)
            try:
                with self.conversion_progress(f"Importing {name}") as progress:
                    total += len(
                        self.c.engine.import_scene(path, progress=progress, **conv)
                        or []
                    )
                done += 1
            except ptk.OperationCancelled:
                self.c.footer_status(f"Stopped importing {name}.")
                break
            except FileNotFoundError as e:
                self.c.error_box("Can't import", name, e)
                if not self.c.engine.needs_conversion(path):
                    continue
                return
            except Exception as e:  # noqa: BLE001 - surfaced to the user
                self.c.logger.warning(f"Scene import failed for {path}: {e}")
                self.c.error_box("Import failed for", name, e)
        self.c.logger.info(f"Imported {total} object(s) from {done} scene(s).")
        self.c.refresh_file_list(invalidate=False)
