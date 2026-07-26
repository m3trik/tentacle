# !/usr/bin/python
# coding=utf-8
"""Prefix/suffix affix option box on the materials-combo "Rename" label (DCC-agnostic).

The "Rename" label (``lbl005``) in the materials combo's (``cmb002``) right-click
context menu carries an **option box** (gear) whose dropdown — built with no apply
button, so the field's Enter key is the commit — holds two controls:

- ``cmb_rename_mode``: how the affix text joins the material name —
  **Auto** (the underscore edge picks the side: ``_lod0`` -> ``mat_lod0``,
  ``metal_`` -> ``metal_mat``), **Prefix** (prepend: ``metal`` -> ``metal_mat``),
  or **Suffix** (append: ``lod0`` -> ``mat_lod0``).
- ``txt000``: the affix text; press Enter to apply.

Shared by every DCC's Materials slot — the option-box build, the join/validation
(:meth:`_join_affix`), and the ``lbl005`` handler are identical. Only the rename
itself forks, delegated to each slot's ``_rename_current(text)`` hook (Maya
``cmds.rename`` / Blender datablock assignment), which must return the resulting
name on success or a falsy value on failure so the field is cleared only when the
rename actually happened.
"""


class MaterialsRenameAffixMixin:
    """``cmb002`` "Rename" label (``lbl005``) + its prefix/suffix affix option box."""

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
        """Join *affix* onto *name* per *mode*.

        Returns the new name, or ``None`` when the input can't yield one:
        an Auto affix with an underscore on both edges or neither (no side to
        infer), or a Prefix/Suffix affix that is only underscores.

        - **Prefix** / **Suffix**: the text's edge underscores are stripped and a
          single underscore separator is inserted (``metal`` and ``metal_`` both
          give ``metal_<name>``).
        - **Auto**: the underscore edge is the separator and encodes the side —
          leading ``_`` appends (suffix), trailing ``_`` prepends (prefix).
        """
        if mode in ("Prefix", "Suffix"):
            token = affix.strip("_")
            if not token:
                return None
            return f"{token}_{name}" if mode == "Prefix" else f"{name}_{token}"

        # Auto: the underscore edge picks the side.
        leading = affix.startswith("_")
        trailing = affix.endswith("_")
        if leading == trailing:  # both edges or neither → can't infer a side
            return None
        return name + affix if leading else affix + name

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
