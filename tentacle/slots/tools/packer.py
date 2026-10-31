# !/usr/bin/python
# coding=utf-8
"""Map Packer UI — slot file for ``packer.ui``: channel-pack/unpack texture maps.

A standalone panel (``tentacle/tcl_standalone.py``); what it packs it reports
through its logger, at INFO.
"""

import os
from typing import List

import pythontk as ptk
from pythontk import FileUtils, ImgUtils, MapFactory

from tentacle import Slots


class PackerSlots(Slots, ptk.LoggingMixin):
    """Switchboard slots for ``packer.ui`` — RGBA channel packing and unpacking.

    The raster work is :class:`pythontk.ImgUtils`'s (``pack_channels`` /
    ``extract_channels``), called on that class rather than inherited: the
    panel is wiring, and the image library's surface is not the panel's.
    """

    channels = ["R", "G", "B", "A"]
    grayscale_types = [
        "None",
        "Metallic",
        "Roughness",
        "Ambient_Occlusion",
        "Smoothness",
        "Opacity",
        "Height",
        "Thickness",
        "Glossiness",
        "Displacement",
        # The OpenPBR scalar lobes -- glTF packs them in pairs (clearcoat R +
        # its roughness G, iridescence R + its thickness G). Appended, never
        # inserted: a preset saved before the combos stored their TEXT holds
        # each one by INDEX.
        "Clearcoat",
        "Clearcoat_Roughness",
        "Sheen",
        "Sheen_Roughness",
        "Transmission",
        "Subsurface_Scattering",
        "Subsurface_Radius",
        "Specular_Level",
        "Anisotropy",
        "Anisotropy_Angle",
        "Thin_Film",
        "Thin_Film_Thickness",
        "Diffuse_Roughness",
    ]
    output_formats = ["PNG", "TGA", "JPG", "BMP", "TIFF", "EXR"]

    # Policy for a texture set whose requested maps aren't all resolvable --
    # the registry's rules, so the Map Packer and the material updaters share
    # one vocabulary.
    MISSING_SKIP = ptk.MapRegistry.MISSING_SKIP  # default: don't write it
    MISSING_MULTI = ptk.MapRegistry.MISSING_MULTI  # only if 2+ channels resolved
    MISSING_FORCE = ptk.MapRegistry.MISSING_FORCE  # always; missing channels fill

    #: Saved data: the folder the user's presets have always been kept in.
    PRESET_DIR = "extapps/texture_maps/packer"
    # The shipped, read-only templates: one per supported packing (ORM, MRAO,
    # MSAO, Metallic Smoothness, and the glTF lobe pairs). A user preset of the
    # same name shadows one; the panel never copies them into the user store.
    BUILTIN_PRESET_DIR = os.path.join(os.path.dirname(__file__), "_packer", "presets")

    # The copies earlier releases seeded into the USER store, by stem, with the
    # values they were written with -> the built-in that replaces each. Retired
    # once, and only while untouched: an edited copy is the user's own preset.
    _LEGACY_SEEDS = {
        "ORM _Unreal_ glTF_": (
            "ORM - Unreal glTF Godot",
            {"cmbR": 3, "cmbG": 2, "cmbB": 1, "cmbA": 0, "txtSuffix": "_ORM"},
        ),
        "MRAO _Metallic_ Roughness_ AO_": (
            "MRAO - Metallic Roughness AO",
            {"cmbR": 1, "cmbG": 2, "cmbB": 3, "cmbA": 0, "txtSuffix": "_MRAO"},
        ),
        "MSAO _HDRP Mask Map_": (
            "MSAO - Unity HDRP Mask Map",
            {"cmbR": 1, "cmbG": 3, "cmbB": 0, "cmbA": 4, "txtSuffix": "_MSAO"},
        ),
        "Metallic Smoothness _URP_": (
            "Metallic Smoothness - Unity URP",
            {
                "cmbR": 1,
                "cmbG": 0,
                "cmbB": 0,
                "cmbA": 4,
                "txtSuffix": "_MetallicSmoothness",
            },
        ),
    }

    def __init__(self, switchboard, **kwargs):
        super().__init__(switchboard)
        self.logger.setLevel("INFO")
        self.ui = self.sb.loaded_ui.packer

        self._source_dir = kwargs.get("source_dir", "")

        # The switchboard can build this slots instance mid-load — even eagerly
        # during Switchboard construction (slot_source=) — *before* the child
        # widgets are registered onto self.ui. Touching any widget here would
        # raise and leave ``ui.slots = None`` (e.g. tentacle's materials b008
        # then crashes on ``ui.slots.source_dir``). Per-widget setup lives in
        # the ``*_init`` methods; cross-widget wiring that needs the whole UI
        # (presets, label colors, mode sync) runs once the UI is registered.
        self.ui.run_when_ready(self._initialize_ui)

    def _set_channel_label_colors(self):
        """Set background color for each channel label."""
        channel_colors = {
            "R": "#ef9a9a",  # Pastel Red
            "G": "#a5d6a7",  # Pastel Green
            "B": "#90caf9",  # Pastel Blue
            "A": "#bdbdbd",  # Pastel Gray
        }
        for c in self.channels:
            lbl = getattr(self.ui, f"lbl{c}", None)
            if lbl:
                lbl.setStyleSheet(
                    f"background-color: {channel_colors[c]}; color: white; border-radius: 3px;"
                )

    def _initialize_ui(self):
        """Cross-widget wiring, deferred until the whole UI is registered.

        Runs once after ``register_children`` (via ``on_first_show``), so every
        channel combo, the preset combo, the option combos, and the action
        buttons exist. Per-combo population/restore already ran in the
        ``*_init`` methods, so this only does the wiring that spans multiple
        widgets.
        """
        self._set_channel_label_colors()
        self.ui.b001.setEnabled(False)  # the open-output-dir button starts disabled
        self._setup_presets()
        # Sync the action-button text / option enablement to the restored mode.
        self._on_mode_changed()

    def _setup_presets(self):
        """Wire the in-window preset combo to the channel/format/affix widgets.

        The window's ``PresetManager`` drives ``cmbPreset`` (the canonical
        Refresh / Save / menu toolbar comes from ``wire_combo``). It runs here,
        not in ``cmbPreset_init``: the preset combo registers before the channel
        combos it captures. The templates are the read-only built-in tier
        (``BUILTIN_PRESET_DIR``); the user store (``PRESET_DIR``) holds only
        what the user saves.
        """
        presets = self.ui.presets
        presets.preset_dir = self.PRESET_DIR
        presets.builtin_dir = self.BUILTIN_PRESET_DIR
        presets.setup(
            widgets=[
                self.ui.cmbR,
                self.ui.cmbG,
                self.ui.cmbB,
                self.ui.cmbA,
                self.ui.cmbFormat,
                self.ui.txtSuffix,
            ],
            # A preset stores the field TEXT; the placement picker beside it is a
            # separate, GLOBAL setting. Without the mode travelling with the text, a
            # session left on Prefix applied the next preset's suffix-shaped value on
            # the wrong side -- 'ORM_mat' came out '_ORMmat'. Metadata is dispatched
            # BEFORE widget values, so the picker is already right when the text lands.
            metadata_provider=lambda: {
                "affix_mode": self.ui.txtSuffix.option_box.affix_mode
            },
            on_metadata_loaded=self._apply_preset_affix_mode,
        )
        # Before wiring, so the combo lists (and restores) what remains.
        self._retire_legacy_seeds(presets)
        presets.wire_combo(self.ui.cmbPreset, placeholder="Preset…")

    def cmbPreset_init(self, widget):
        """Preset selector -- its pick persists via the store's ``.active`` pointer
        (restored by ``wire_combo``), not as a per-widget combo index."""
        widget.restore_state = False

    def _affix_option(self):
        """The placement picker beside the output-affix field, or None."""
        return self.ui.txtSuffix.option_box.find_option(self.sb.AffixOption)

    def _apply_preset_affix_mode(self, meta):
        """Restore the placement a preset was saved with.

        A preset written before the mode was stored has no key, and reads back as
        the suffix it was actually saved as -- not as "auto", which would re-derive
        the side from the text and silently disagree with the picker.
        """
        option = self._affix_option()
        if option is not None:
            option.set_mode(meta.get("affix_mode", "suffix"))

    @classmethod
    def _retire_legacy_seeds(cls, presets) -> None:
        """Delete the template copies earlier releases seeded into the user store.

        They predate the built-in tier and would list beside it as duplicates.
        A copy whose values no longer match its seed (every seed wrote PNG,
        ``cmbFormat`` 0) was edited -- it is the user's, and stays. An active
        pick on a retired copy moves to the built-in that replaces it.

        Parameters:
            presets: The panel's ``uitk.PresetManager``.
        """
        active = presets.active_preset
        for stem, (replacement, seeded) in cls._LEGACY_SEEDS.items():
            if presets.source(stem) != "user":
                continue
            if presets.read(stem) != {"cmbFormat": 0, **seeded}:
                continue
            presets.delete(stem)
            if active == stem:
                presets.active_preset = replacement

    def _init_channel_combo(self, widget):
        """Populate a channel combo with the grayscale map types.

        Runs inside the per-widget ``*_init`` (so during ``register_children``,
        before state restore) — the selection then persists across sessions.
        Persisted, and captured into presets, by TEXT: a map-type name reads
        the same in a preset file and survives the list growing.
        """
        widget.clear()
        widget.addItems(self.grayscale_types)
        widget.restore_by = "text"
        widget.restore_state = True

    def cmbR_init(self, widget):
        self._init_channel_combo(widget)

    def cmbG_init(self, widget):
        self._init_channel_combo(widget)

    def cmbB_init(self, widget):
        self._init_channel_combo(widget)

    def cmbA_init(self, widget):
        self._init_channel_combo(widget)

    def txtSuffix_init(self, widget):
        """Output-affix field — clearable back to the convention's default."""
        widget.option_box.clear_option = True
        # Fourth, custom state: take the packed-texture affix from the shared
        # naming convention rather than this one field.
        widget.option_box.set_affix(
            default="auto",
            settings_key="packer_output_affix",
            convention_key="packedTexture",
        )

    def cmbFormat_init(self, widget):
        """Populate the output-format combo and react to format changes."""
        widget.clear()
        widget.addItems(self.output_formats)
        widget.restore_by = "text"
        widget.restore_state = True
        widget.currentTextChanged.connect(self._on_format_changed)

    def _on_format_changed(self, fmt: str):
        """Disable alpha combobox for formats without alpha support.

        Only constrains alpha in *pack* mode: there the alpha combo selects a
        source map to write into the output's alpha channel, so a format
        without alpha support (e.g. JPG) must clear it. In *unpack* mode the
        alpha combo selects which channel to *extract* from the input image,
        which is independent of the output format, so it stays enabled and its
        selection is left untouched (mirrors the invariant in
        :meth:`_on_mode_changed`). This handler is wired to the format combo's
        ``currentTextChanged``, so it fires in both modes.
        """
        if self._unpack_mode():
            self.ui.cmbA.setEnabled(True)
            return
        supports_alpha = fmt.upper() in {"PNG", "TGA", "TIFF", "EXR", "BMP"}
        self.ui.cmbA.setEnabled(supports_alpha)
        if not supports_alpha:
            self.ui.cmbA.setCurrentIndex(self.ui.cmbA.findText("None"))

    def cmbMode_init(self, widget):
        """The Pack/Unpack direction -- first in the window, since it decides
        what every row below it means.

        The channel layout (R/G/B/A → map type) is direction-agnostic, so a
        single set of presets serves both packing and unpacking (see
        :meth:`_on_mode_changed`).
        """
        widget.add([("Pack", "pack"), ("Unpack", "unpack")], prefix="Mode:")
        widget.restore_by = "data"
        widget.restore_state = True
        widget.currentIndexChanged.connect(lambda *_: self._on_mode_changed())

    def cmbMissing_init(self, widget):
        """What an incomplete texture set does when packing (see :meth:`_pack_set`)."""
        widget.add(
            [
                ("Skip Set", self.MISSING_SKIP),
                ("Pack If 2+ Maps", self.MISSING_MULTI),
                ("Pack Anyway", self.MISSING_FORCE),
            ],
            prefix="Missing Maps:",
        )
        widget.restore_by = "data"
        widget.restore_state = True

    def _unpack_mode(self) -> bool:
        """True when the Mode combo is set to Unpack.

        Defaults to False (Pack) when the combo isn't registered yet, so callers
        can read it safely at any point.
        """
        try:
            return self.ui.cmbMode.currentData() == "unpack"
        except (AttributeError, RuntimeError):
            return False

    def _missing_map_rule(self) -> str:
        """The 'Missing Maps' policy for incomplete texture sets.

        Falls back to :attr:`MISSING_SKIP` when the combo isn't registered yet
        (or has no selection), so callers can read it safely at any point and
        always get the safe default.
        """
        try:
            return self.ui.cmbMissing.currentData() or self.MISSING_SKIP
        except (AttributeError, RuntimeError):
            return self.MISSING_SKIP

    def _on_mode_changed(self):
        """Reflect the Pack/Unpack mode in the UI.

        Behavior is read live from :meth:`_unpack_mode` at action time, so this
        is purely cosmetic: relabel the action button and disable options that
        don't apply to the current direction.
        """
        unpack = self._unpack_mode()
        self.ui.b000.setText("Unpack" if unpack else "Pack")
        # The Suffix names the single packed output; when unpacking, each output
        # is auto-named by its channel's map type, so the field is irrelevant.
        self.ui.txtSuffix.setEnabled(not unpack)
        # The Missing Maps policy only governs the pack direction.
        self.ui.cmbMissing.setEnabled(not unpack)
        # In pack mode the alpha channel's availability follows the output
        # format. In unpack mode the alpha combo selects what to extract from
        # the input image, so it must stay enabled regardless of format.
        if unpack:
            self.ui.cmbA.setEnabled(True)
        else:
            self._on_format_changed(self.ui.cmbFormat.currentText())

    @property
    def source_dir(self):
        return self._source_dir

    @source_dir.setter
    def source_dir(self, value):
        self._source_dir = value

    def _resolve_output_affix(self):
        """``(prefix, suffix)`` for the packed file name, from field + picker.

        The picker beside the field decides which side the affix lands on; an
        empty field falls back to the shared convention rather than a literal. An
        affix carries its OWN separator (``apply_affix`` concatenates verbatim), so
        a bare token typed without one is normalised first -- "Packed" has always
        produced "base_Packed", not "basePacked".

        An emptied convention entry is a sanctioned configuration everywhere else,
        but here it would leave the output stem EQUAL to a source stem and pack
        straight over an input map, so the shipped default stands in. (The field's
        placeholderText is not a fallback here the way it is in mayatk -- this
        panel uses it as the visible LABEL, so it would yield the affix "Suffix:".)

        Lifted out of ``b000`` so the auto/suffix/prefix/convention contract is
        testable without a Qt event loop.
        """
        affix = self.ui.txtSuffix.text().strip() or ptk.NamingConvention.affix(
            "packedTexture"
        )
        if not affix:
            affix = ptk.NamingConvention.DEFAULTS["packedTexture"].text
        prefix, suffix = self.ui.txtSuffix.option_box.resolve_affix(
            affix, default="suffix"
        )
        return (
            ptk.StrUtils.delimit_affix(prefix, "prefix"),
            ptk.StrUtils.delimit_affix(suffix, "suffix"),
        )

    def _channel_combos(self) -> List[str]:
        """The R/G/B/A map-type selections, in channel order.

        Read identically by both directions: packing treats the entry as the
        map to write *into* that channel, unpacking as the map that channel
        already holds.
        """
        return [getattr(self.ui, f"cmb{c}").currentText() for c in self.channels]

    def _require_channel_selection(self, combos) -> bool:
        """True when at least one channel names a map type; reports when not.

        With every channel on 'None' there is nothing to pack or unpack, and
        both batches would otherwise walk their whole selection to no effect —
        reporting every set as skipped, which reads like the files were at
        fault rather than the empty channel layout.
        """
        if any(c != "None" for c in combos):
            return True
        self.logger.warning("No channels assigned. Set at least one channel's map type.")
        return False

    def _select_textures(self, title):
        """Open the texture file dialog seeded from the current source dir.

        On selection, re-seed ``source_dir`` from the chosen files so the next
        dialog reopens where the user last browsed. Without this the dialog
        stays pinned to the stale seed dir even after the user changes folders
        (``_finish_batch`` only updates it, to the output dir, on success).
        Mirrors :class:`ConverterSlots`, which re-seeds after every selection.
        """
        file_paths = self.sb.file_dialog(
            file_types=[f"*.{ext}" for ext in ImgUtils.texture_file_types],
            title=title,
            start_dir=self.source_dir,
            allow_multiple=True,
        )
        if file_paths:
            self.source_dir = FileUtils.format_path(file_paths[0], "path")
        return file_paths

    def _finish_batch(self, success, file_paths):
        """Post-batch bookkeeping shared by pack/unpack: on success, point the
        source dir at the output and enable the 'open output' button; otherwise
        leave it disabled."""
        if success:
            self._last_output_dir = FileUtils.format_path(file_paths[0], "path")
            self.source_dir = self._last_output_dir
            self.ui.b001.setEnabled(True)
        else:
            self.ui.b001.setEnabled(False)

    def b000(self):
        """Run the configured channel operation: Pack (default) or Unpack."""
        if self._unpack_mode():
            self._unpack_files()
        else:
            self._pack_files()

    def _pack_files(self):
        """Batch pack up to 4 channels into RGBA maps across texture sets."""
        combos = self._channel_combos()
        if not self._require_channel_selection(combos):
            self.ui.b001.setEnabled(False)
            return

        file_paths = self._select_textures(
            "Select textures for batch packing (multiple sets allowed):"
        )
        if not file_paths:
            self.logger.warning("No files selected.")
            self.ui.b001.setEnabled(False)
            return

        texture_sets = MapFactory.group_textures_by_set(file_paths)
        prefix, suffix = self._resolve_output_affix()
        ext = self.ui.cmbFormat.currentText().lower()
        fmt = self.ui.cmbFormat.currentText().upper()
        rule = self._missing_map_rule()

        success = False
        packed = 0
        total_sets = len(texture_sets)
        with self.sb.progress(
            total=total_sets, text=f"Packing 0/{total_sets} sets"
        ) as update:
            for i, (base_name, files) in enumerate(texture_sets.items()):
                result = self._pack_set(
                    base_name=base_name,
                    files=files,
                    combos=combos,
                    suffix=suffix,
                    prefix=prefix,
                    ext=ext,
                    fmt=fmt,
                    rule=rule,
                )
                packed += bool(result)
                success = result or success
                # Skipped sets are the norm now, so the progress line has to
                # say which happened rather than claim every set was packed.
                update(
                    i + 1,
                    f"{'Packed' if result else 'Skipped'} set "
                    f"{i + 1}/{total_sets}: {base_name}",
                )

        if packed < total_sets:
            hint = (
                ""
                if rule == self.MISSING_FORCE
                else " Set 'Missing Maps' to 'Pack Anyway' to pack them regardless."
            )
            self.logger.result(
                f"Packed {packed}/{total_sets} set(s); "
                f"{total_sets - packed} skipped (incomplete).{hint}"
            )

        self._finish_batch(success, file_paths)

    def _pack_set(
        self,
        *,
        base_name,
        files,
        combos,
        suffix,
        ext,
        fmt,
        rule=MISSING_SKIP,
        prefix="",
    ) -> bool:
        """Helper for ``b000`` — pack a single texture set. Returns True
        if the set was packed and the output written.

        A set is *complete* when every channel assigned a map type (anything
        but ``None``) resolves to a source file, either directly or by
        conversion from another map that is present. An incomplete set is
        skipped by default — packing it would write a map whose missing
        channels are silently filled with a constant, which is indistinguishable
        from a legitimately flat channel downstream.

        ``rule`` is the panel's 'Missing Maps' policy, applied only when the
        set is incomplete: :attr:`MISSING_SKIP` writes nothing,
        :attr:`MISSING_MULTI` writes it if at least two channels resolved, and
        :attr:`MISSING_FORCE` always writes it. In both packing cases as many
        channels as possible are resolved and the rest store their map type's
        absent value (``ptk.MapRegistry.absent_fills``): unoccluded, matte,
        dielectric, opaque -- the rule every packing follows.
        """
        assigned = {c: None for c in self.channels}
        requested = dict(zip(self.channels, combos))
        # Resolve each file's map type once: the per-channel search below would
        # otherwise re-derive every file's type for all four channels. The set
        # reads as one batch, so a set named for a lobe (``Hero_Coat``) packs
        # its ``Hero_Coat_Roughness`` as Roughness.
        types = MapFactory.resolve_map_types(files)
        file_types = [(f, types[f]) for f in files]
        available_map_types = {t: f for f, t in file_types}
        used_files = set()
        missing = []

        for channel in self.channels:
            map_type = requested[channel]
            if map_type == "None":
                continue
            file = next(
                (f for f, t in file_types if t == map_type and f not in used_files),
                None,
            )
            if file:
                assigned[channel] = file
                used_files.add(file)
                continue
            # Try conversion if not found
            converted = MapFactory.get_converted_map(map_type, available_map_types)
            if converted is not None:
                assigned[channel] = converted
                continue
            missing.append(f"{channel}:{map_type}")

        resolved = [c for c in self.channels if assigned[c]]

        if missing:
            # How many channels a packing rule needs before it will write an
            # incomplete set. MISSING_SKIP (0) needs them all, i.e. never packs.
            minimum = ptk.MapRegistry.MISSING_MAP_MINIMUMS.get(rule, 0)
            if not minimum or len(resolved) < minimum:
                self.logger.warning(
                    f"Skipped '{base_name}': required map(s) "
                    f"{', '.join(missing)} not found and cannot be converted."
                )
                return False
            self.logger.warning(
                f"'{base_name}' is missing {', '.join(missing)}. "
                "Packing with those channels at their absent values."
            )
        elif not resolved:  # every channel set to 'None' — nothing was asked for
            return False

        # Channel count follows the layout the user CONFIGURED, not just what
        # resolved: a force-packed set whose alpha map is missing still writes
        # RGBA (alpha filled), so one batch can't emit a mix of RGB and RGBA
        # files under a single suffix. A layout with A on 'None' stays RGB —
        # that is what makes ORM/MRAO 3-channel, and it is the whole point of
        # those formats (no alpha means BC1 rather than BC3/BC7).
        out_mode = "RGBA" if requested["A"] != "None" else "RGB"
        output_dir = FileUtils.format_path(files[0], "path")
        stem = ptk.StrUtils.apply_affix(base_name, prefix=prefix, suffix=suffix)
        output_path = f"{output_dir}/{stem}.{ext}"
        # Never write over one of our own source maps. Two ways in: an affix that
        # resolves to nothing on both sides, and one the user deliberately types
        # that collides -- including a re-pack over a previous output.
        def _key(path):
            return os.path.normcase(os.path.abspath(path))

        if _key(output_path) in {_key(f) for f in files}:
            self.logger.warning(
                f"Skipped {base_name} -- the output name {stem}.{ext} "
                "is one of its own source maps. Set an affix that distinguishes it."
            )
            return False
        ImgUtils.pack_channels(
            channel_files=assigned,
            output_path=output_path,
            out_mode=out_mode,
            output_format=fmt,
            fill_values=ptk.MapRegistry.absent_fills(requested),
        )
        self.logger.result(f"Packed map saved: {output_path}")
        return True

    def _unpack_files(self):
        """Batch unpack packed textures into per-channel maps.

        The same R/G/B/A → map-type assignment used for packing now describes
        what each channel of the *input* holds; each assigned channel is
        extracted to ``<base>_<MapType>.<ext>`` beside the source.
        """
        combos = self._channel_combos()
        if not self._require_channel_selection(combos):
            self.ui.b001.setEnabled(False)
            return

        file_paths = self._select_textures(
            "Select packed textures to unpack into per-channel maps:"
        )
        if not file_paths:
            self.logger.warning("No files selected.")
            self.ui.b001.setEnabled(False)
            return

        ext = self.ui.cmbFormat.currentText().lower()
        fmt = self.ui.cmbFormat.currentText().upper()

        success = False
        total = len(file_paths)
        with self.sb.progress(total=total, text=f"Unpacking 0/{total}") as update:
            for i, file in enumerate(file_paths):
                success = (
                    self._unpack_one(file=file, combos=combos, ext=ext, fmt=fmt)
                    or success
                )
                update(
                    i + 1,
                    f"Unpacked {i + 1}/{total}: {FileUtils.format_path(file, 'name')}",
                )

        self._finish_batch(success, file_paths)

    def _unpack_one(self, *, file, combos, ext, fmt) -> bool:
        """Helper for ``_unpack_files`` — split one packed texture. Returns True
        if at least one channel was extracted and written.

        Channels set to ``None`` are skipped; channels absent from the source
        image (e.g. ``A`` on an RGB input) are skipped by ``extract_channels``.
        """
        channel_config = {
            channel: {"suffix": f"_{map_type}"}
            for channel, map_type in zip(self.channels, combos)
            if map_type != "None"
        }
        if not channel_config:
            return False

        output_dir = FileUtils.format_path(file, "path")
        results = ImgUtils.extract_channels(
            file,
            channel_config,
            output_dir=output_dir,
            save=True,
            output_format=fmt,
            ext=ext,
        )
        written = [p for p in results.values() if p]
        for path in written:
            self.logger.result(f"Extracted map saved: {path}")
        return bool(written)

    def b001(self):
        """Open the last output directory in the system file explorer."""
        output_dir = getattr(self, "_last_output_dir", None)
        if not output_dir or not os.path.isdir(output_dir):
            self.logger.warning("No output directory available.")
            return
        # Delegate to the canonical, non-shell launcher. It passes the path as
        # a single argv entry (os.startfile / subprocess.Popen(["xdg-open", ...])),
        # so shell metacharacters in the directory name are inert — this avoids
        # the os.system shell-injection the interpolated command strings had.
        if not FileUtils.open_explorer(output_dir):
            self.logger.error("Unable to open output directory.")
