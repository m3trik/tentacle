# !/usr/bin/python
# coding=utf-8
"""Shared, DCC-agnostic behavior for the ``materials`` panel.

The per-panel home for logic the Maya and Blender ``MaterialsSlots`` forks share (mixed in
ahead of their ``SlotsMaya`` / ``SlotsBlender`` base). Grow this class rather than adding a
new module per feature — see the convention in ``tentacle/CLAUDE.md``.

Currently: the prefix/suffix affix option box on the materials-combo "Rename" label.
The "Rename" label (``lbl005``) in the materials combo's (``cmb002``) right-click context
menu carries an **option box** (gear) whose dropdown — built with no apply button, so the
field's Enter key is the commit — holds two controls:

- ``cmb_rename_mode``: how the affix text joins the material name —
  **Auto** (the underscore edge picks the side: ``_lod0`` -> ``mat_lod0``,
  ``metal_`` -> ``metal_mat``), **Prefix** (prepend: ``metal`` -> ``metal_mat``),
  or **Suffix** (append: ``lod0`` -> ``mat_lod0``).
- ``txt000``: the affix text; press Enter to apply.

The option-box build, the join/validation (:meth:`_join_affix`), and the ``lbl005`` handler
are identical across DCCs. Only the rename itself forks, delegated to each slot's
``_rename_current(text)`` hook (Maya ``cmds.rename`` / Blender datablock assignment), which
must return the resulting name on success or a falsy value on failure so the field is
cleared only when the rename actually happened.

Also: the submenu's ``b003`` "Get + Select" one-shot — get the material off the current
selection, then select every object using it. It carries no options of its own; it calls
each slot's ``select_by_mat(shell, in_selection, get_first, add, unassigned)`` hook (the
parameterized primitive that also backs the main panel's option-box-driven ``tb000``) with
fixed values,
so the two entry points share one implementation without either reading — or temporarily
overwriting — the other's persisted option-box state.

And the "get the material off the selection" half of that, :meth:`_adopt_selection_mat` —
shared by "Get Material" (``b002``) and ``select_by_mat``'s ``get_first``, which differ
only in their message when the selection can't yield exactly one material. Its DCC hook is
``_selection_mats()``: the material NAMES on the selection, or ``None`` when nothing is
selected (Maya ``mtk.MatUtils.get_mats`` / Blender ``btk.get_mats``). An empty list means
"selected, but nothing assigned" — the case ``b003`` turns into an unassigned search
(``select_by_mat(unassigned=True)``, which bypasses ``cmb002``: "no material" is not a
material and must never become the current one, since ~24 call sites feed
``cmb002.currentData()`` straight to delete / assign / graph / rename).

Hooks each ``<Panel>Slots`` fork must supply: ``_rename_current(text)``,
``select_by_mat(...)``, ``_selection_mats()``.
"""
import pythontk as ptk


class MaterialsMixin:
    """DCC-agnostic ``materials`` slot behavior.

    ``cmb002`` "Rename" label (``lbl005``) + its prefix/suffix affix option box,
    the submenu's ``b003`` "Get + Select" one-shot, and the shared
    adopt-the-selection's-material path behind ``b003`` / ``b002``.
    """

    #: Affix modes offered by ``cmb_rename_mode`` (index 0 is the default).
    _RENAME_MODES = ("Auto", "Prefix", "Suffix")

    def _add_rename_control(self, menu):
        """Add the "Rename" label with its affix option box to *menu*.

        The label (``lbl005``) auto-wires to the slot method of the same name; its
        option-box dropdown carries the affix field (on top) + a mode combo below.
        No apply button — the affix commits when the field's Enter is pressed or
        the "Rename" label is clicked while the field holds text (:meth:`lbl005`).
        """
        lbl005 = menu.add(
            self.sb.registered_widgets.Label,
            setText="Rename",
            setObjectName="lbl005",
            setToolTip=(
                "Rename the current material. Type an affix in the option box (gear) "
                "to prefix/suffix instead — press Enter or click Rename to apply."
            ),
        )

        # No apply / restore-defaults buttons — commit is Enter / the label click.
        lbl005.option_box.enable_menu(add_apply_button=False, add_defaults_button=False)
        obox = lbl005.option_box.menu
        obox.setTitle("Rename Affix")
        # Affix field on top (primary), the mode selector below it.
        obox.add(
            "QLineEdit",
            setObjectName="txt000",
            setPlaceholderText="affix (Enter to apply)",
            setToolTip=(
                "Type an affix and press Enter (or click Rename) to prefix/suffix the "
                "current material name. In Auto mode the underscore edge picks the side."
            ),
        )
        obox.add(
            "QComboBox",
            setObjectName="cmb_rename_mode",
            setToolTip=(
                "How the affix text joins the material name:\n"
                "  Auto   — the underscore edge picks the side "
                "(_lod0 → mat_lod0, metal_ → metal_mat)\n"
                "  Prefix — prepend the text  (metal → metal_mat)\n"
                "  Suffix — append the text   (lod0 → mat_lod0)"
            ),
        )
        obox.cmb_rename_mode.addItems(list(self._RENAME_MODES))
        # Transient input — don't persist the typed affix across sessions
        # (registration defaults new widgets to restore_state=True).
        obox.txt000.restore_state = False
        obox.txt000.returnPressed.connect(self._apply_rename_affix)

        self._rename_affix = obox.txt000
        self._rename_mode_combo = obox.cmb_rename_mode

    @staticmethod
    def _join_affix(name, affix, mode):
        """Join *affix* onto *name* per *mode*, via ``ptk.StrUtils.apply_affix``.

        Returns the new name, or ``None`` when the input can't yield one: an Auto
        affix with an underscore on both edges or neither (no side to infer), or a
        Prefix/Suffix affix that is only underscores.

        Auto resolves the side from the underscore edge (leading ``_`` → suffix,
        trailing ``_`` → prefix). The actual join — a single ``_`` separator,
        idempotent, no dangling underscores — is pythontk's ``apply_affix``
        primitive; this method is only the UI's mode + rejection policy over it
        (edge underscores are stripped from the token, so ``metal`` and ``metal_``
        both give ``metal_<name>``).
        """
        if mode == "Auto":
            leading, trailing = affix.startswith("_"), affix.endswith("_")
            if leading == trailing:  # both edges or neither → can't infer a side
                return None
            mode = "Suffix" if leading else "Prefix"
        token = affix.strip("_")
        if not token:
            return None
        if mode == "Prefix":
            return ptk.StrUtils.apply_affix(name, prefix=f"{token}_")
        return ptk.StrUtils.apply_affix(name, suffix=f"_{token}")

    def _apply_rename_affix(self):
        """Apply the affix field to the current material using the selected mode.

        Reads the mode from ``cmb_rename_mode`` and the text from ``txt000``,
        joins them via :meth:`_join_affix`, and commits through the DCC slot's
        ``_rename_current`` hook. The field is cleared only on a successful
        rename (a failed/ rejected commit keeps the typed affix).
        """
        affix = self._rename_affix.text().strip()
        if not affix:
            return
        mat = self.ui.cmb002.currentData()
        if not mat:
            return

        name = str(mat).rsplit("|", 1)[-1]
        mode = self._rename_mode_combo.currentText()
        new_name = self._join_affix(name, affix, mode)
        if new_name is None:
            if mode == "Auto":
                self.sb.message_box(
                    "<hl>Ambiguous affix</hl><br>"
                    "In Auto mode, put one underscore on the joining edge: "
                    "leading '_' for a suffix (_lod0), trailing '_' for a prefix "
                    "(metal_). Or pick Prefix / Suffix from the option box."
                )
            else:
                self.sb.message_box(
                    f"<hl>Empty affix</hl><br>Enter some text to use as the {mode.lower()}."
                )
            return

        if self._rename_current(new_name):
            self._rename_affix.clear()

    def lbl005(self):
        """Rename the current material.

        With an affix typed in the option box, apply the prefix/suffix; otherwise
        make the combo editable for a full free-form rename. Clicking the label is
        the reliable commit for the affix (reading option-box values on the main
        widget's action is the established pattern) — the field's Enter key is a
        shortcut for the same. The context menu dismisses itself via
        ``hide_on_trigger`` (the label's option-box wrap is recognized as the
        triggered item), so no explicit hide is needed.
        """
        if self._rename_affix.text().strip():
            self._apply_rename_affix()
        else:
            self.ui.cmb002.setEditable(True)

    #: Why the selection can't yield one material -> (title, body) for the message box.
    _GET_MAT_FAILURES = {
        "empty": (
            "Nothing selected",
            "Select mesh object(s) or face(s) to get the material from.",
        ),
        "none": (
            "No material found",
            "The selected object has no material assigned.",
        ),
        "multiple": (
            "Multiple materials found",
            "The selected object has multiple materials assigned, so a single "
            "current material can't be determined.",
        ),
        "filtered": (
            "Material hidden by the list filters",
            "'{mat}' isn't in the materials list — a cmb002 option-box filter "
            "(Hide Default Materials / Hide Arnold Shaders) is hiding it. Turn "
            "that filter off to make it current.",
        ),
    }

    def _adopt_selection_mat(self, on_failure=""):
        """Set ``cmb002`` to the single material assigned to the current selection.

        Shared by "Get Material" (``b002``) and ``select_by_mat``'s ``get_first``,
        which differ only in what happens when the selection can't yield exactly
        one material: b002 stops there, get_first carries on with whatever material
        is current — hence ``on_failure``, appended to the reported reason.

        Only the lookup forks, via each slot's ``_selection_mats()`` hook: the
        material NAMES on the selection, or ``None`` when nothing is selected.

        Parameters:
            on_failure (str): Text appended to the failure message (e.g. what the
                caller does next).

        Returns:
            str | None: The adopted material name, or None (a message was shown).
        """
        mats = self._selection_mats()
        found = mats[0] if mats and len(mats) == 1 else ""

        if found:
            previous = self.ui.cmb002.currentData()
            self.ui.cmb002.init_slot()  # refresh the list so the found material is in it
            self.ui.cmb002.setAsCurrent(found)
            if str(self.ui.cmb002.currentData() or "") == found:
                return found
            # A cmb002 list filter (Hide Default Materials / Hide Arnold Shaders)
            # can drop the found material from the list — and ComboBox.setAsCurrent
            # silently falls back to INDEX 0 for a missing item, which would leave
            # an unrelated material current and select by it. Put the previous
            # material back, then report it like any other adopt failure.
            if previous is not None:
                self.ui.cmb002.setAsCurrent(str(previous))
            reason = "filtered"
        else:
            reason = "empty" if mats is None else "none" if not mats else "multiple"

        # One report path, so ``on_failure`` (what the caller does next) is always
        # part of the message — a reason without it would misdescribe the outcome.
        title, body = self._GET_MAT_FAILURES[reason]
        self.sb.message_box(f"<hl>{title}</hl><br>{body.format(mat=found)}{on_failure}")
        return None

    def b003(self, widget=None):
        """Get + Select (submenu): adopt the selection's material, then select its users.

        A fixed one-shot — whole objects, whole scene, replacing the selection —
        so the submenu button does the same thing every time. The configurable
        form is the main panel's ``tb000`` with its option box; both run the same
        ``select_by_mat`` implementation.

        A selection with NO material takes the analogous branch rather than
        failing: "everything that matches this selection, material-wise" becomes
        every object that also has no material. Only a genuinely materialless
        selection routes there — an empty or multi-material selection still
        reports through the normal adopt path.

        Returns:
            list: whatever ``select_by_mat`` selected (see the DCC slot's hook).
        """
        if self._selection_mats() == []:  # selected, but nothing assigned
            self.sb.message_box(
                "<hl>No material on the selection</hl><br>"
                "Selecting the objects that have no material assigned."
            )
            return self.select_by_mat(shell=True, unassigned=True)
        return self.select_by_mat(shell=True, get_first=True)
