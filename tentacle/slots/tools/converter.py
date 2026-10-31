# !/usr/bin/python
# coding=utf-8
"""Map Converter UI — slot file for ``converter.ui``.

Bundles texture-map conversion, channel packing, PBR-workflow prep, and bulk
optimization into a single Switchboard panel. The heavy lifting lives in
``MapFactory`` / ``ImgUtils`` (in pythontk), and the converter's own batch rules
(destination / archive resolution, rename-mode naming, output collisions, the
dry-run report) in extapps' Qt-free :class:`extapps.MapConverter`, which the
slots class HOLDS as ``self.engine`` -- this module is the UI wiring only. What a
tool reports goes through the panel's logger, at INFO.

This module exposes :class:`ConverterSlots` — the Switchboard slot class.
Method names map to widget ``objectName`` in the .ui file: ``tb*`` =
toolbutton (has an options menu populated by the matching ``*_init`` hook),
``b*`` = plain button. Host integrations can inject a ``texture_provider``
callable to read the DCC selection.

A standalone panel: :class:`ConverterUI` in ``tentacle/tcl_standalone.py``.
"""
import os
from typing import Callable, Dict, Iterable, List, Optional, Tuple

import pythontk as ptk
from extapps import MapConverter
from pythontk import (
    ExportProfile,
    FileUtils,
    ImgUtils,
    MapFactory,
    MapRegistry,
    OutputTemplates,
)
from qtpy import QtCore

from tentacle import Slots


class ConverterSlots(Slots, ptk.LoggingMixin):
    """Switchboard slots for ``converter.ui``.

    Slot methods are bound to widgets by name. The ``Scope`` combobox in the
    header menu (installed by :meth:`header_init`) decides where *every* tool
    reads its texture paths from: the built-in :attr:`BROWSE_SCOPE` opens a
    file dialog, and any host-registered scope calls that host's provider.
    Set :attr:`source_dir` to seed the initial dialog directory.
    """

    #: Built-in scope — always present, always first, never host-provided.
    #: ASCII on purpose: scope labels get interpolated into log output,
    #: and a cp1252 console raises UnicodeEncodeError on a stray "…".
    BROWSE_SCOPE = "Browse..."

    def __init__(self, switchboard, **kwargs):
        super().__init__(switchboard)
        self.logger.setLevel("INFO")
        #: The batch engine this panel drives (held, not inherited).
        self.engine = MapConverter()
        self.ui = self.sb.loaded_ui.converter

        self._source_dir = kwargs.get("source_dir", "")
        # Insertion-ordered label -> provider. Excludes BROWSE_SCOPE, whose
        # "provider" is the file dialog (a None lookup in _get_texture_paths).
        self._scopes: Dict[str, Callable[[], Iterable[str]]] = {}
        # Scope a host asked to activate before the combobox existed. Hosts
        # register right after launch(show=False) and the header menu may not
        # be built until first show, so the request has to survive the gap.
        self._pending_scope: Optional[str] = None

        provider = kwargs.get("texture_provider", None)
        if provider:
            self.texture_provider = provider

    @property
    def source_dir(self):
        """Get the starting directory for file dialogs."""
        return self._source_dir

    @source_dir.setter
    def source_dir(self, value):
        """Set the starting directory for file dialogs."""
        self._source_dir = value

    # -------------------------------------------------------------------------
    # Scopes — where tools read their texture paths from
    # -------------------------------------------------------------------------

    @property
    def scopes(self) -> Tuple[str, ...]:
        """Scope labels currently offered, in combobox order.

        Always starts with :attr:`BROWSE_SCOPE`; the rest are whatever the
        host registered via :meth:`register_scope`. This is why the panel can
        stay app-agnostic — it owns the *mechanism* (a scope picker) and the
        host owns the *policy* (what "Selected Materials" means here).
        """
        return (self.BROWSE_SCOPE, *self._scopes)

    def register_scope(
        self,
        label: str,
        provider: Callable[[], Iterable[str]],
        *,
        select: bool = False,
    ) -> None:
        """Offer *label* in the Scope combobox, resolved by calling *provider*.

        Parameters:
            label (str): Combobox entry, e.g. "Selected Objects". Re-registering
                a label replaces its provider and keeps its position.
            provider (callable): ``() -> Iterable[str]`` returning texture file
                paths. Called fresh on every tool invocation, so it always sees
                the host's *current* selection. May open its own dialog (that's
                how a "Choose Materials…" scope is built).
            select (bool): Make this the active scope once registered.

        Hosts call this right after launching the panel — see the Maya
        integration in ``tentacle.slots.materials.b016`` (both hosts).
        """
        if not callable(provider):
            raise TypeError(
                f"Scope {label!r} needs a callable provider, got {type(provider)}."
            )
        if label == self.BROWSE_SCOPE:
            # Shadowing it would leave two identically-labelled entries and
            # route the built-in one to the host, so 'Browse' would silently
            # stop opening the file dialog.
            raise ValueError(f"{label!r} is the built-in browse scope; pick another label.")
        self._scopes[label] = provider
        if select:
            self._pending_scope = label
        self._refresh_scope_combo()

    def unregister_scope(self, label: str) -> None:
        """Drop a previously registered scope (no-op if it isn't registered)."""
        if self._scopes.pop(label, None) is not None:
            self._refresh_scope_combo()

    @property
    def texture_provider(self) -> Optional[Callable[[], Iterable[str]]]:
        """Provider for the plain "Selected" scope.

        Back-compatible shorthand for hosts that only supply one selection
        source: setting it registers (or, when set to None, removes) a single
        "Selected" scope. Hosts with several selection kinds should call
        :meth:`register_scope` per kind instead.
        """
        return self._scopes.get("Selected")

    @texture_provider.setter
    def texture_provider(self, fn: Optional[Callable[[], Iterable[str]]]) -> None:
        if fn is None:
            self.unregister_scope("Selected")
        else:
            self.register_scope("Selected", fn)

    def header_init(self, widget):
        """Add the global Scope combobox to the header menu."""
        combo = widget.menu.add(
            "QComboBox",
            setObjectName="cmb_scope",
            setToolTip=(
                "Where every tool on this panel reads its texture paths from.\n"
                f"'{self.BROWSE_SCOPE}' opens a file browser; the remaining "
                "entries are provided by the host application and read its "
                "current selection when the tool runs.\n"
                "Only 'Browse' is available when running standalone."
            ),
        )
        # Populated through the just-created widget rather than a self.ui
        # lookup — during header_init the header isn't necessarily reachable
        # from the loaded ui yet.
        self._refresh_scope_combo(combo=combo)

    def _refresh_scope_combo(self, combo=None) -> None:
        """Rebuild the Scope combobox, keeping the active scope where possible.

        Called whenever the scope set changes — hosts register their scopes
        *after* the UI is built, so the combobox has to repopulate rather than
        being filled once in :meth:`header_init`.
        """
        if combo is None:
            try:
                combo = self.ui.header.menu.cmb_scope
            except (AttributeError, RuntimeError):
                return  # Header menu not built yet; header_init will populate it.

        target = self._pending_scope or self._current_scope()
        labels = self.scopes
        try:
            combo.add(
                [(label, label) for label in labels],
                prefix="Scope:",
            )
            combo.setCurrentIndex(labels.index(target) if target in labels else 0)
            # Only clear once it actually landed on a live combobox.
            self._pending_scope = None
            # Deliberately not persisted (``add`` turns restore_state back on):
            # the entries past 'Browse' come from whichever host launched the
            # panel, and combo state restores by *index* — a saved index would
            # resolve to a different scope under a different host, silently
            # retargeting which files a tool overwrites.
            combo.restore_state = False
        except (AttributeError, RuntimeError, TypeError):
            pass  # Mocked / torn-down combo — nothing to repopulate.

    def _current_scope(self) -> str:
        """Active scope label, falling back to :attr:`BROWSE_SCOPE`."""
        try:
            scope = self.ui.header.menu.cmb_scope.currentData()
        except (AttributeError, RuntimeError):
            return self.BROWSE_SCOPE
        return scope if scope in self.scopes else self.BROWSE_SCOPE

    def _get_texture_paths(self, *, title, map_type_filter=None, allow_multiple=True):
        """Resolve texture paths for the active scope.

        Parameters:
            title (str): Title shown if the file dialog is used.
            map_type_filter (Iterable[str], optional): When pulling from a host
                scope, restrict to these MapRegistry keys (e.g. ``["Normal",
                "Normal_DirectX"]``). Ignored when the file dialog is used —
                there the filter is the user's own selection.
            allow_multiple (bool): Forwarded to ``file_dialog``.

        Returns:
            List[str]: Existing absolute paths. Empty list when nothing valid.
        """
        scope = self._current_scope()
        provider = self._scopes.get(scope)

        if provider is not None:
            paths = list(provider() or [])
            if map_type_filter:
                wanted = set(map_type_filter)
                kept, dropped = [], []
                # The scope's files read as one batch: a set named for a lobe
                # (``Hero_Coat``) keeps its ``Hero_Coat_Normal`` a Normal.
                types = MapFactory.resolve_map_types(paths)
                for p in paths:
                    key = types[p]
                    (kept if key in wanted else dropped).append(p)
                if dropped:
                    self.logger.warning(
                        f"Skipping {len(dropped)} map(s) not in "
                        f"{sorted(wanted)} from '{scope}'."
                    )
                paths = kept
            if not paths:
                self.logger.warning(f"No matching textures found for scope '{scope}'.")
                return []
        else:
            paths = self.sb.file_dialog(
                file_types=[f"*.{ext}" for ext in ImgUtils.texture_file_types],
                title=title,
                start_dir=self.source_dir,
                allow_multiple=allow_multiple,
            )
            paths = list(paths or [])

        valid = [p for p in paths if p and os.path.isfile(p)]
        for missing in (p for p in paths if p not in valid):
            self.logger.warning(f"Skipping (file not found): {missing}")
        return valid

    #: Longest-side clamp offered by the Optimize menu, and the entry selected
    #: on a first run. 4K is the practical ceiling for real-time textures — a
    #: bigger source almost always ships downsampled — so it beats 'None' as
    #: the default for a tool whose whole purpose is shrinking maps.
    CLAMP_SIZES = (256, 512, 1024, 2048, 4096, 8192)
    DEFAULT_CLAMP = 4096

    #: Clamp sentinel meaning "defer to the selected target's DeliveryBudget".
    #: Negative so it stays truthy (0 already means "no clamp") and can never
    #: collide with a real pixel dimension.
    CLAMP_TARGET = -1
    CLAMP_TARGET_LABEL = "Target"

    #: Lossy-quality choices for the Optimize menu. Off is first and default —
    #: lossy is opt-in, and the safety gate still refuses it per map type.
    LOSSY_CHOICES = (("Off", 0), ("q95", 95), ("q90", 90), ("q80", 80))

    @property
    def optimize_formats(self) -> Tuple[str, ...]:
        """The containers Optimize offers: every writable one, then the
        delivery containers (``ImgUtils.DELIVERY_FORMATS`` -- KTX2).

        Appended, never interleaved: the Format combo persists its selection by
        index, so a new entry anywhere but the end would re-point every saved
        choice. KTX2 is offered whether or not its encoder is installed yet;
        choosing it offers the install (:meth:`_ktx2_ready`).
        """
        return tuple(ImgUtils.writable) + tuple(
            ext for ext in ImgUtils.DELIVERY_FORMATS if ext not in ImgUtils.writable
        )

    def _ktx2_ready(self) -> bool:
        """Settle a missing KTX2 encoder before a KTX2 run, offering the managed
        install -- the panels' rule: a missing tool is an install offer, never
        a dead end in a log.  The refusal is the fix-shaped message naming the
        manual install, so it IS the dialog."""
        return ImgUtils.settle_ktx2_encoder(
            prompt=self.sb.confirm,
            refused=self.sb.message_box,
            installed=lambda path: self.sb.message_box(
                f"Installed KTX-Software (toktx): <hl>{path}</hl>"
            ),
        )

    #: KTX2 RDO dictionary sizes for the Optimize menu (``toktx --uastc_rdo_d``),
    #: largest window first. toktx's own 4096 is the first-run default: this is
    #: a map tool, where the time is the user's to spend -- a web export runs a
    #: smaller window by policy (``MeshConvert.WEB_DELIVERY_UASTC_RDO_DICTIONARY``).
    RDO_DICTIONARIES = (16384, 4096, 1024, 256)
    DEFAULT_RDO_DICTIONARY = 4096

    def tb000_init(self, widget):
        """Populate the Optimize toolbutton's option menu.

        Grouped under titled separators — Output (what gets written), Naming
        (what it's called), Destination (where it lands), Preview — so the
        menu reads as sections rather than one flat stack of controls.
        """
        menu = widget.option_box.menu
        menu.setTitle("Optimize")

        menu.add("Separator", setTitle="Output")
        menu.add(
            "QComboBox",
            setObjectName="cmb_target",
            setToolTip=(
                "Delivery target. Drives each map's container and bit depth "
                "from the profile's output template, and lets 'Clamp: Target' "
                "use the profile's size budget.\n"
                "Also skips packed maps belonging to another engine — an MSAO "
                "mask map when targeting glTF. Loose maps are never skipped.\n"
                "'None' processes every selected map with no target rules.\n"
                "For WebXR pick 'glTF 2.0' — that is the WebXR material model."
            ),
        )
        # Profile list + tooltips come from OutputTemplates (SSoT shared with
        # game_shader / mat_updater / the compositor), so a profile added to the
        # registry appears in every panel without touching any of them.
        #
        # The prefix is baked into the label rather than passed as prefix=:
        # that kwarg re-cases each label (`.replace("_"," ").title()`), which is
        # right for the bare tokens the sibling combos carry but renders
        # "glTF 2.0" as "Gltf 2.0" and "PBR Metallic/Roughness" as "Pbr ...".
        # Profile names are proper nouns matched against the registry by string.
        profiles = OutputTemplates.profile_choices()
        menu.cmb_target.add(
            [("Target:\tNone", "")] + [(f"Target:\t{n}", n) for n, _ in profiles]
        )
        for i, (_name, description) in enumerate(profiles):
            if description:  # +1 for the leading "None" entry
                menu.cmb_target.setItemData(
                    i + 1, description, QtCore.Qt.ToolTipRole
                )

        menu.add(
            "QComboBox",
            setObjectName="cmb001",
            setToolTip=(
                "Set the output file type. 'Original' keeps each texture's "
                "existing format; with a Target selected, WEBP is the web/XR "
                "choice (lossless WebP is 10-30% under PNG at identical pixels).\n"
                "KTX2 is the GPU-delivery container (Basis: UASTC for normals and "
                "data maps, ETC1S for base color / emissive) -- it needs the toktx "
                "encoder, which is offered for install on first use."
            ),
        )
        # Falsy sentinels (empty string / 0) — the prefix-mode combobox
        # replaces explicit None data with the label string, so use values
        # that still evaluate falsy in the ``if not file_type`` / ``if not
        # max_size`` checks below. 'Original' stays at index 0: this combo's
        # selection is persisted by index (see format_choices' sentinel_first).
        menu.cmb001.add(
            OutputTemplates.format_choices(
                sentinel=OutputTemplates.ORIGINAL_LABEL,
                writable=self.optimize_formats,
                sentinel_first=True,
            ),
            prefix="Format:",
        )

        menu.add(
            "QComboBox",
            setObjectName="cmb000",
            setToolTip=(
                "Maximum dimension (longest side). 'None' disables resizing; "
                "'Target' uses the selected target's own size budget "
                "(glTF/Godot/URP 2048, HDRP/Unreal 4096)."
            ),
        )
        # 'Target' appended LAST for the same index-persistence reason as the
        # format sentinel — prepending it would re-point every saved clamp.
        menu.cmb000.add(
            [("None", 0)]
            + [(str(s), s) for s in self.CLAMP_SIZES]
            + [(self.CLAMP_TARGET_LABEL, self.CLAMP_TARGET)],
            prefix="Clamp:",
        )
        # First-run default only: state restore runs after the *_init hooks, so
        # a previously chosen clamp still wins on later sessions.
        default_clamp = menu.cmb000.findData(self.DEFAULT_CLAMP)
        if default_clamp > -1:
            menu.cmb000.setCurrentIndex(default_clamp)

        menu.add(
            "QComboBox",
            setObjectName="cmb_secondary_scale",
            setToolTip=(
                "Downscale non-critical maps (roughness, metallic, AO, masks, "
                "height, etc.) by this fraction of the clamp. Resolution-critical "
                "maps (base color, normals, emissive) always use the full clamp."
            ),
        )
        menu.cmb_secondary_scale.add(
            [("Full", 1.0), ("1/2", 0.5), ("1/4", 0.25), ("1/8", 0.125)],
            prefix="Secondary:",
        )

        menu.add(
            "QComboBox",
            setObjectName="cmb_lossy",
            setToolTip=(
                "Lossy compression for WEBP / JPG output. Applied ONLY to "
                "unpacked sRGB maps (base color, emissive) — normals, ORM/mask "
                "maps and every linear map are written lossless regardless, "
                "and each refusal is reported.\n"
                "At q95 a base color deviates by at most 9/255; a normal map "
                "deviates by 122/255, which is why the gate exists.\n"
                "Off = lossless everywhere."
            ),
        )
        menu.cmb_lossy.add(list(self.LOSSY_CHOICES), prefix="Lossy:")

        # The KTX2 pair: meaningful only with Format KTX2, and there only for
        # the maps that encode UASTC -- which is what their tooltips say, the
        # way the Lossy row names the maps it leaves alone.
        menu.add(
            "QComboBox",
            setObjectName="cmb_rdo",
            setToolTip=(
                "KTX2 only: UASTC rate-distortion optimisation for the maps "
                "that encode UASTC - normals, ORM / mask and other data maps. "
                "Smaller files at a controlled quality cost, and 3-4x the "
                "encode time.\n"
                "Normal maps are capped at lambda 0.75 (toktx's own guidance); "
                "base color and emissive encode ETC1S, which has no RDO stage.\n"
                "Off = plain UASTC."
            ),
        )
        # The exporter's own vocabulary (ExportProfile), so the two read alike.
        menu.cmb_rdo.add(ExportProfile.UASTC_RDO_OPTIONS, prefix="RDO:")
        menu.add(
            "QComboBox",
            setObjectName="cmb_rdo_dictionary",
            setToolTip=(
                "KTX2 with RDO on: the RDO dictionary size - how far back the "
                "optimiser looks for matches, and where RDO's time goes. "
                "Measured on production maps: 1024 took half the time of 4096 "
                "(toktx's own) for 2% larger files, 256 saved little more for "
                "5%. A larger window keeps more of RDO's size win and takes "
                "longer."
            ),
        )
        menu.cmb_rdo_dictionary.add(
            [
                (
                    f"{size} (toktx default)"
                    if size == self.DEFAULT_RDO_DICTIONARY
                    else str(size),
                    size,
                )
                for size in self.RDO_DICTIONARIES
            ],
            prefix="RDO Dictionary:",
        )
        # First-run default only, as with the clamp: a saved choice restores
        # after the *_init hooks.
        default_dictionary = menu.cmb_rdo_dictionary.findData(
            self.DEFAULT_RDO_DICTIONARY
        )
        if default_dictionary > -1:
            menu.cmb_rdo_dictionary.setCurrentIndex(default_dictionary)

        menu.add("Separator", setTitle="Naming")
        menu.add(
            "QLineEdit",
            setObjectName="txt_modifier",
            setPlaceholderText="e.g. LD_ or _LD",
            setToolTip=(
                "Text inserted into the base name (before the map-type suffix). "
                "Empty = keep the original name.\n"
                "The first button beside the field picks where it attaches "
                "(click to cycle Auto → Suffix → Prefix). On Auto the modifier's "
                "own underscore decides: 'LD_' prefixes, '_LD' suffixes, bare "
                "'LD' suffixes."
            ),
        )
        # Affix picker + disable, inline on the field rather than as sibling
        # combos: the mode is a property OF the modifier, and an icon button
        # keeps a one-line menu row instead of two full-width controls.
        menu.txt_modifier.option_box.set_affix(default="auto")
        # Disable = the field reads empty to every consumer (the value is held
        # aside and handed back on re-enable), so a run without the modifier is
        # one click away and cannot be half-applied.
        menu.txt_modifier.option_box.set_disable(
            settings_key="converter_optimize_modifier",
            tooltip_on=(
                "Modifier applied. Click to disable — the output keeps the "
                "original name (your text is held until you re-enable)."
            ),
            tooltip_off=(
                "Modifier disabled — the output keeps the original name. "
                "Click to re-apply."
            ),
        )

        menu.add("Separator", setTitle="Destination")
        menu.add(
            "QLineEdit",
            setObjectName="txt_new_folder",
            setPlaceholderText="e.g. new, or D:/out",
            setToolTip=(
                "Where the optimized map is written.\n"
                "A bare name is a subdirectory under each texture's own folder; "
                "an absolute path collects every map from the run into that one "
                "folder.\n"
                "Empty = write beside the original (which, with no modifier, "
                "overwrites it)."
            ),
        )
        menu.txt_new_folder.option_box.set_disable(
            settings_key="converter_optimize_new_folder",
            tooltip_on=(
                "Output folder in use. Click to disable — the map is written "
                "beside the original (your path is held until you re-enable)."
            ),
            tooltip_off=(
                "Output folder disabled — the map is written beside the "
                "original. Click to re-apply."
            ),
        )

        menu.add(
            "QLineEdit",
            setObjectName="txt_old_folder",
            setText="old",
            setPlaceholderText="e.g. old, or D:/archive",
            setToolTip=(
                "Where the original is moved to. A bare name is a subdirectory "
                "under each texture's own folder; an absolute path collects every "
                "original into that one folder.\n"
                "Empty = don't move the original."
            ),
        )
        menu.txt_old_folder.option_box.set_disable(
            settings_key="converter_optimize_old_folder",
            tooltip_on=(
                "Originals archived. Click to disable — the original is left "
                "where it is, and is overwritten when nothing else moves the "
                "output off it."
            ),
            tooltip_off=(
                "Archiving disabled — the original is left where it is. Click "
                "to re-enable."
            ),
        )

        menu.add("Separator", setTitle="Preview")
        menu.add(
            "QCheckBox",
            setText="Dry run",
            setObjectName="chk_dry_run",
            setChecked=False,
            setToolTip=(
                "Report what each texture would become — resolution, bit "
                "depth, file size before → after, and the output path — "
                "without writing, overwriting, or archiving anything.\n"
                "The projected size comes from a real encode of the planned "
                "result, so it's the size you'd actually get, not an estimate."
            ),
        )

    def _refuses_collisions(
        self, texture_paths, file_type, target_profile, new_folder, old_folder
    ) -> bool:
        """Whether two inputs would land on one output or archive path (said,
        with each claimed path): every write but the last would be lost."""
        for where, folder, forced_ext, profile in (
            ("output", new_folder, file_type, target_profile),
            ("archive", old_folder, "", None),
        ):
            clashes = self.engine.output_collisions(
                texture_paths, forced_ext, folder, profile
            )
            if clashes:
                self.logger.warning(
                    f"{len(clashes)} {where} path(s) would be claimed by more "
                    "than one map - each would overwrite the last, so only the "
                    "final result would survive. Convert them separately, or "
                    "give each source its own subdirectory."
                )
                for out_name, clashing in clashes:
                    self.logger.warning(f"  {out_name}: " + ", ".join(clashing))
                return True
        return False

    def tb000(self, widget):
        """Optimize a texture map(s)"""
        texture_paths = self._get_texture_paths(
            title="Select texture map(s) to optimize:"
        )
        if not texture_paths:
            return

        # Falsy sentinels ("", 0) → None so optimize_map preserves
        # the original format / skips clamping respectively.
        file_type = widget.option_box.menu.cmb001.currentData() or None
        max_size = widget.option_box.menu.cmb000.currentData() or None
        secondary_scale = (
            widget.option_box.menu.cmb_secondary_scale.currentData() or 1.0
        )
        target = widget.option_box.menu.cmb_target.currentData() or None
        lossy_quality = widget.option_box.menu.cmb_lossy.currentData() or None
        uastc_rdo = widget.option_box.menu.cmb_rdo.currentData() or None
        uastc_rdo_dictionary = (
            widget.option_box.menu.cmb_rdo_dictionary.currentData() or None
        )

        target_profile, file_type = OutputTemplates.resolve_selection(
            target, file_type
        )
        # A dry run encodes too (its size is a real encode), so both need it.
        if file_type == "ktx2" and not self._ktx2_ready():
            return

        # 'Clamp: Target' takes the ceiling from the profile's DeliveryBudget.
        # The number is resolved HERE rather than left to enforce_budget alone:
        # downstream, the secondary scale only engages when it has a max_size to
        # scale (`if max_size and secondary_scale != 1.0`), so deferring the
        # whole ceiling into optimize_map would silently disable that control.
        # enforce_budget stays on so the budget's POT rule still applies; an
        # explicit max_size outranks the budget's, and here they are the same.
        enforce_budget = max_size == self.CLAMP_TARGET
        if enforce_budget:
            max_size = (
                OutputTemplates.budget(target_profile).max_size
                if target_profile
                else None
            )
            if not target_profile:
                self.logger.warning(
                    "Clamp is 'Target' but no Target is selected - no size "
                    "budget to apply. Pick a Target, or choose an explicit clamp."
                )
            elif max_size is None:
                self.logger.warning(
                    f"'{target_profile}' is unbudgeted (an authoring target) - "
                    "no clamp applied. Choose an explicit clamp to resize."
                )
        # Affix mode rides on the modifier field's own option box (the icon
        # button beside it), so a disabled field reports no modifier at all
        # rather than an orphaned mode.
        modifier_field = widget.option_box.menu.txt_modifier
        mode, modifier = self.engine.resolve_affix(
            modifier_field.option_box.affix_mode, modifier_field.text()
        )
        new_folder = self.engine.folder_name(widget.option_box.menu.txt_new_folder.text())
        old_folder = self.engine.folder_name(widget.option_box.menu.txt_old_folder.text())
        dry_run = widget.option_box.menu.chk_dry_run.isChecked()

        registry = MapRegistry()

        # Target filter — drop packed maps belonging to another engine (an MSAO
        # when writing for glTF). Delegated to MapFactory.foreign_packings, the
        # pipeline's single answer to "is this source right for what I'm
        # writing?", already shared by the GLB writer, pack_orm_texture and both
        # DCCs' Scene Exporter gates. Its restrictions are the contract, not an
        # optimisation: only PACKED maps are eligible (a loose map's
        # ``workflows`` means "presets that emit it", so a general form would
        # flag ordinary AO as foreign), and an unknown workflow reports nothing
        # rather than everything.
        #
        # Deliberately NOT extended to loose maps a present pack supersedes:
        # MapFactory.filter_redundant_maps owns that question and resolves it
        # losslessly, extracting any channel the pack does not cover before
        # dropping its components. Optimize writes each file independently with
        # no extraction step, so the same rule here could drop a Roughness whose
        # data the surviving ORM never carried.
        #
        # Runs BEFORE the destination guards below: those refuse the whole batch
        # over same-stem collisions, and a map this filter drops is never
        # written, so counting it would block a run that has no real clash.
        skipped_by_target = 0
        if target_profile:
            foreign = MapFactory.foreign_packings(
                texture_paths, workflow=target_profile
            )
            if foreign:
                for path, map_type in foreign.items():
                    self.logger.warning(
                        f"Skipping ({target_profile}): {os.path.basename(path)} - "
                        f"{map_type} is another engine's packing"
                    )
                skipped_by_target = len(foreign)
                texture_paths = [p for p in texture_paths if p not in foreign]
            if not texture_paths:
                self.logger.warning(
                    f"Every selected map is another engine's packing for "
                    f"'{target_profile}' - nothing to do. Check the Target, or "
                    "set it to 'None'."
                )
                return

        # Both fields resolve against the *source* folder, so pointing them at
        # the same subdirectory drops the archived original on top of the map
        # just written there — the optimization is silently undone. Refuse once,
        # up front, rather than per texture after the first one is already gone.
        # normcase, not casefold: on Windows 'out' and 'OUT' are one directory
        # (so the clobber is real); on POSIX they are two, and refusing there
        # would block a legitimate pair.
        if new_folder and os.path.normcase(new_folder) == os.path.normcase(old_folder):
            self.logger.warning(
                f"Both destination folders are '{new_folder}' - the archived "
                "original would overwrite the optimized map. Use different names."
            )
            return

        # A full-path destination collapses every source folder into one, so two
        # maps sharing a stem resolve to the SAME output (or archive) path and
        # the later one silently destroys the earlier — both optimize_map's
        # writer and FileUtils.move_file default to overwrite=True. Per-texture
        # subdirectories cannot hit this (each source keeps its own folder), so
        # the check is scoped to the shared case, and refuses up front for the
        # same reason as the guard above.
        # One question asked of each destination: would two inputs land on the
        # SAME path? Both keyed on the resolved path rather than the bare stem,
        # which is what keeps a refusal honest -- `.tga` and `.png` sources
        # collapsed into one folder keep two names and lose nothing, and the
        # earlier shared-folder guard refused them anyway. The archive keeps
        # each source's own container, so it asks with no forced extension and
        # no profile.
        if self._refuses_collisions(
            texture_paths, file_type, target_profile, new_folder, old_folder
        ):
            return

        verb = "Assessing" if dry_run else "Optimizing"
        done = "Assessed" if dry_run else "Optimized"
        if dry_run:
            self.logger.info("Dry run - no files will be written, moved, or overwritten.")

        total = len(texture_paths)
        saved_before = saved_after = counted = 0
        failed: List[Tuple[str, str]] = []
        # The run's maps read as one batch: a set named for a lobe
        # (``Hero_Coat``) keeps its base maps -- sized and renamed as such.
        readings = MapFactory.classify_textures(texture_paths)
        with self.sb.progress(
            total=total, text=f"{verb} 0/{total}"
        ) as update:
            for i, texture_path in enumerate(texture_paths):
                # One unwritable / unreadable map must not abandon the rest of
                # the batch: a read-only source (a DCC's own preset textures
                # live under Program Files) or a locked file used to raise out
                # of the loop, leaving the run half-done with no summary.
                map_type, base_name = readings[texture_path]
                try:
                    before, after = self.engine.optimize_one(
                        texture_path,
                        map_type=map_type,
                        base_name=base_name,
                        file_type=file_type,
                        max_size=max_size,
                        secondary_scale=secondary_scale,
                        mode=mode,
                        modifier=modifier,
                        new_folder=new_folder,
                        old_folder=old_folder,
                        registry=registry,
                        dry_run=dry_run,
                        output_profile=target_profile,
                        enforce_budget=enforce_budget,
                        lossy_quality=lossy_quality,
                        uastc_rdo=uastc_rdo,
                        uastc_rdo_dictionary=uastc_rdo_dictionary,
                    )
                except Exception as e:
                    before = after = None
                    reason = f"{type(e).__name__}: {e}"
                    failed.append((texture_path, reason))
                    self.logger.error(f"Failed: {texture_path}\n  {reason}")
                if before is not None and after is not None:
                    saved_before += before
                    saved_after += after
                    counted += 1
                update(
                    i + 1,
                    f"{done} {i + 1}/{total}: {os.path.basename(texture_path)}",
                )

        if failed:
            self.logger.error(f"{len(failed)} map(s) failed:")
            for path, reason in failed:
                self.logger.error(f"  {os.path.basename(path)}: {reason}")

        if saved_before:
            # Count the maps that actually contributed a size, not the whole
            # batch — a total labelled "5 map(s)" that summed 3 of them is a
            # wrong number, and size is the number being trusted here.
            skipped = f" ({total - counted} unmeasured)" if counted < total else ""
            filtered = (
                f", {skipped_by_target} skipped for '{target_profile}'"
                if skipped_by_target
                else ""
            )
            self.logger.result(
                f"Total ({counted} map(s)){skipped}{filtered}: "
                f"{FileUtils.format_bytes_delta(saved_before, saved_after)}"
            )
        self.source_dir = FileUtils.format_path(texture_paths[0], "path")

    def tb001_init(self, widget):
        """ """
        widget.option_box.menu.setTitle("Spec Gloss to PBR")
        widget.option_box.menu.add(
            "QCheckBox",
            setText="Create MetallicSmoothness map",
            setObjectName="chk000",
            setToolTip="Also create a MetallicSmoothness map.",
        )

    def tb001(self, widget):
        """Batch converts Spec/Gloss maps to PBR Metal/Rough using MapFactory.

        User selects multiple texture sets. The function groups them per base name
        and converts them accordingly using the DRY MapFactory.

        Maps are saved as Metallic/Roughness maps in the same directory.
        """
        spec_map_paths = self._get_texture_paths(
            title="Select Specular, Gloss (optional), and Diffuse maps to convert:",
        )
        if not spec_map_paths:
            return

        create_metallic_smoothness = widget.option_box.menu.chk000.isChecked()

        # Use MapFactory for DRY conversion
        workflow_config = {
            "albedo_transparency": False,
            "metallic_smoothness": create_metallic_smoothness,
            "mask_map": False,
            "normal_type": "OpenGL",
            "output_extension": "png",
            "convert_specgloss_to_pbr": True,
        }

        self.logger.info(f"Processing {len(spec_map_paths)} files...")

        try:
            results = MapFactory.prepare_maps(
                spec_map_paths,
                **workflow_config,
            )

            if isinstance(results, dict):
                self.logger.info(f"Processed {len(results)} texture sets.")
                for base_name, maps in results.items():
                    self.logger.info(f"Set: {base_name}")
                    for m in maps:
                        self.logger.info(f"  - {m}")
            else:
                self.logger.info("Processed single set.")
                for m in results:
                    self.logger.info(f"  - {m}")

        except Exception as e:
            self.logger.error(f"Error during batch processing: {e}")
            import traceback

            traceback.print_exc()

        try:
            self.source_dir = FileUtils.format_path(spec_map_paths[0], "path")
        except Exception:
            pass

    def tb003_init(self, widget):
        """Initialize a 'Bump to Normal' toolbutton with options."""
        widget.option_box.menu.setTitle("Bump to Normal")
        widget.option_box.menu.add(
            "QComboBox",
            setObjectName="tb003_cmb_format",
            setToolTip="OpenGL: Y+ up, DirectX: Y+ down",
        )
        # Display-friendly items with data values
        cmb = widget.option_box.menu.tb003_cmb_format
        cmb.clear()
        cmb.addItem("Format: OpenGL", "opengl")
        cmb.addItem("Format: DirectX", "directx")

        widget.option_box.menu.add(
            "QDoubleSpinBox",
            setObjectName="tb003_dsb_intensity",
            setMinimum=0.1,
            setMaximum=5.0,
            setSingleStep=0.1,
            setValue=1.0,
            setDecimals=2,
            setPrefix="Intensity: ",
            setToolTip="Controls how deep the height values are interpreted",
        )

    def tb003(self, widget):
        """Bump/Height to Normal converter (single entry point with options)."""
        bump_map_paths = self._get_texture_paths(
            title="Select bump/height maps to convert:",
            map_type_filter=["Bump", "Height"],
        )
        if not bump_map_paths:
            return

        # Options
        try:
            output_format = (
                widget.option_box.menu.tb003_cmb_format.currentData() or "opengl"
            )
        except Exception:
            fmt_text = widget.option_box.menu.tb003_cmb_format.currentText().lower()
            output_format = "directx" if "directx" in fmt_text else "opengl"
        intensity = widget.option_box.menu.tb003_dsb_intensity.value()

        for bump_path in bump_map_paths:
            self.logger.info(f"Converting bump to normal ({output_format.upper()}): {bump_path}")

            try:
                normal_path = MapFactory.convert_bump_to_normal(
                    bump_path,
                    output_format=output_format,
                    intensity=intensity,
                    smooth_filter=True,
                    filter_radius=0.5,
                )
                self.logger.result(normal_path)

            except Exception as e:
                self.logger.error(f"Error converting {bump_path}: {e}")

        try:
            self.source_dir = FileUtils.format_path(bump_map_paths[0], "path")
        except Exception:
            pass

    # Output channel ← source choices for the Flip Channels tool. ``-X`` marks
    # an inverted source; ``0``/``1`` write a constant. Shared by the option-box
    # builder and (implicitly) the dispatch in :meth:`tb002`.
    _FLIP_SOURCES = [
        ("R", "R"),
        ("G", "G"),
        ("B", "B"),
        ("A", "A"),
        ("R (inv)", "-R"),
        ("G (inv)", "-G"),
        ("B (inv)", "-B"),
        ("A (inv)", "-A"),
        ("Black", "0"),
        ("White", "1"),
    ]

    def tb002_init(self, widget):
        """Populate the Flip Channels option menu (per-channel source + suffix)."""
        widget.option_box.menu.setTitle("Flip Channels")

        for idx, channel in enumerate("RGBA"):
            name = f"cmb_{channel.lower()}"
            widget.option_box.menu.add(
                "QComboBox",
                setObjectName=name,
                setToolTip=(
                    f"Source for the output {channel} channel. '(inv)' inverts "
                    "the source; Black/White write a constant. The default "
                    f"keeps the original {channel}."
                ),
            )
            combo = getattr(widget.option_box.menu, name)
            combo.add(self._FLIP_SOURCES, prefix=f"{channel} ← ")
            combo.setCurrentIndex(idx)  # identity default (R←R, G←G, …)

        widget.option_box.menu.add(
            "QLineEdit",
            setObjectName="txt_suffix",
            setPlaceholderText="empty = overwrite",
            setToolTip=(
                "Suffix appended to the base name (before the extension). "
                "Empty overwrites the source file."
            ),
        )

    def tb002(self, widget):
        """Flip/swizzle texture channels (per-channel invert, swap, or constant fill).

        Each output channel pulls from a chosen source via
        :meth:`ImgUtils.swizzle_channels`; the ``-`` (inverted) sources are
        applied afterward with :meth:`ImgUtils.invert_channels`, keeping both
        primitives pure and composable.
        """
        texture_paths = self._get_texture_paths(
            title="Select texture map(s) to flip/swizzle:",
        )
        if not texture_paths:
            return

        menu = widget.option_box.menu
        tokens = {
            channel: getattr(menu, f"cmb_{channel.lower()}").currentData()
            for channel in "RGBA"
        }
        suffix = menu.txt_suffix.text().strip()

        # Each token is a swizzle source, optionally inverted (the ``-`` prefix).
        # Only *non-identity* sources enter the swizzle map — so an untouched
        # ``A`` slot doesn't force an alpha channel onto an RGB image, and a
        # pure invert leaves the map empty (skipping the RGBA promotion below).
        # Inverts ride separately so the two pure primitives compose.
        swizzle_map = {}
        invert_dests = ""
        for dest, token in tokens.items():
            if token.startswith("-"):
                invert_dests += dest
            source = token.lstrip("-").upper()
            if source != dest:
                swizzle_map[dest] = source

        if not swizzle_map and not invert_dests and not suffix:
            self.logger.warning("Flip Channels: identity selection, nothing to do.")
            return

        total = len(texture_paths)
        with self.sb.progress(total=total, text=f"Flipping 0/{total}") as update:
            for i, path in enumerate(texture_paths):
                self.engine.flip_one(
                    path,
                    swizzle_map=swizzle_map,
                    invert_dests=invert_dests,
                    suffix=suffix,
                )
                update(
                    i + 1, f"Flipped {i + 1}/{total}: {os.path.basename(path)}"
                )

        self.source_dir = FileUtils.format_path(texture_paths[0], "path")

    def b000(self):
        """Convert DirectX to OpenGL"""
        dx_map_paths = self._get_texture_paths(
            title="Select a DirectX normal map to convert:",
            map_type_filter=["Normal", "Normal_DirectX"],
        )
        if not dx_map_paths:
            return

        for dx_map_path in dx_map_paths:
            self.logger.info(f"Converting: {dx_map_path} ..")
            gl_map_path = MapFactory.convert_normal_map_format(
                dx_map_path, target_format="opengl"
            )
            self.logger.result(gl_map_path)
        self.source_dir = FileUtils.format_path(dx_map_paths[0], "path")

    def b001(self):
        """Convert OpenGL to DirectX"""
        gl_map_paths = self._get_texture_paths(
            title="Select an OpenGL normal map to convert:",
            map_type_filter=["Normal", "Normal_OpenGL"],
        )
        if not gl_map_paths:
            return

        for gl_map_path in gl_map_paths:
            self.logger.info(f"Converting: {gl_map_path} ..")
            dx_map_path = MapFactory.convert_normal_map_format(
                gl_map_path, target_format="directx"
            )
            self.logger.result(dx_map_path)
        self.source_dir = FileUtils.format_path(gl_map_paths[0], "path")

    def b004(self):
        """Batch pack Transparency into Albedo across texture sets."""
        paths = self._get_texture_paths(
            title="Select one or more sets of Albedo/Base Color and Transparency maps:",
        )
        if not paths:
            return

        texture_sets = MapFactory.group_textures_by_set(paths)

        for base_name, files in texture_sets.items():
            sorted_maps = MapFactory.sort_images_by_type(files)

            albedo_map_path = sorted_maps.get("Albedo_Transparency", [None])[0]
            base_color_path = sorted_maps.get("Base_Color", [None])[0]
            opacity_map_path = sorted_maps.get("Opacity", [None])[0]

            if not (albedo_map_path or base_color_path):
                self.logger.warning(f"Skipping {base_name}: No Albedo or Base Color map found.")
                continue

            if not opacity_map_path:
                self.logger.warning(f"Skipping {base_name}: No Transparency (Opacity) map found.")
                continue

            rgb_map_path = albedo_map_path or base_color_path

            self.logger.info(
                f"Packing Transparency from: {opacity_map_path}\n\tinto: {rgb_map_path} .."
            )

            packed_path = MapFactory.pack_transparency_into_albedo(
                rgb_map_path,
                opacity_map_path,
                invert_alpha=False,
            )
            self.logger.result(packed_path)

        try:
            self.source_dir = FileUtils.format_path(paths[0], "path")
        except Exception:
            pass

    def b007(self):
        """Unpack Specular and Gloss maps from SpecularGloss textures."""
        specular_gloss_paths = self._get_texture_paths(
            title="Select SpecularGloss maps to unpack:",
            map_type_filter=["Specular"],
        )
        if not specular_gloss_paths:
            return

        for specular_gloss_path in specular_gloss_paths:
            self.logger.info(f"Unpacking: {specular_gloss_path} ..")

            try:
                specular_path, gloss_path = MapFactory.unpack_specular_gloss(
                    specular_gloss_path
                )
                self.logger.info(f"Specular map: {specular_path}")
                self.logger.info(f"Gloss map: {gloss_path}")

            except Exception as e:
                self.logger.error(f"Error unpacking {specular_gloss_path}: {e}")

        try:
            self.source_dir = FileUtils.format_path(specular_gloss_paths[0], "path")
        except Exception:
            pass

    def b010(self):
        """Convert Smoothness maps to Roughness maps."""
        smoothness_paths = self._get_texture_paths(
            title="Select Smoothness maps to convert to Roughness:",
            map_type_filter=["Smoothness"],
        )
        if not smoothness_paths:
            return

        for smoothness_path in smoothness_paths:
            self.logger.info(f"Converting Smoothness to Roughness: {smoothness_path} ..")

            try:
                roughness_path = MapFactory.convert_smoothness_to_roughness(
                    smoothness_path
                )
                self.logger.result(roughness_path)

            except Exception as e:
                self.logger.error(f"Error converting {smoothness_path}: {e}")

        try:
            self.source_dir = FileUtils.format_path(smoothness_paths[0], "path")
        except Exception:
            pass

    def b011(self):
        """Convert Roughness maps to Smoothness maps."""
        roughness_paths = self._get_texture_paths(
            title="Select Roughness maps to convert to Smoothness:",
            map_type_filter=["Roughness"],
        )
        if not roughness_paths:
            return

        for roughness_path in roughness_paths:
            self.logger.info(f"Converting Roughness to Smoothness: {roughness_path} ..")

            try:
                smoothness_path = MapFactory.convert_roughness_to_smoothness(
                    roughness_path
                )
                self.logger.result(smoothness_path)

            except Exception as e:
                self.logger.error(f"Error converting {roughness_path}: {e}")

        try:
            self.source_dir = FileUtils.format_path(roughness_paths[0], "path")
        except Exception:
            pass

    def b012(self):
        """Batch-prepare textures for a target PBR workflow using MapFactory.

        Workflow presets come from :class:`pythontk.MapRegistry` — the single
        source of truth the Maya "Update Materials" tool also reads — so a named
        workflow yields identical settings in both tools. (This method used to
        carry its own copy of the configs, which had drifted from the registry.)

        WebXR is not listed separately: its runtime material model is glTF 2.0,
        so "glTF 2.0" is the preset to choose for WebXR / three.js / Babylon.js
        delivery.
        """
        # Get texture paths
        texture_paths = self._get_texture_paths(
            title="Select texture maps for PBR workflow preparation:",
        )
        if not texture_paths:
            return

        # Workflow presets are owned by MapRegistry (SSoT); offer its names.
        registry = MapRegistry()
        workflow_names = list(registry.get_workflow_presets())

        from qtpy.QtWidgets import QInputDialog

        workflow, ok = QInputDialog.getItem(
            None,
            "Select PBR Workflow",
            "Choose target workflow:",
            workflow_names,
            0,
            False,
        )
        if not ok:
            return

        # Resolve to a full MapFactory config (applies aliases, derives
        # resize/convert_format). Drop the human-readable description and keep
        # the panel's long-standing default output format.
        config = registry.resolve_config(workflow)
        if not config:
            self.logger.error(f"Unknown workflow: {workflow}")
            return
        config.pop("description", None)
        config.setdefault("output_extension", "png")

        self.logger.info(f"\n{'='*60}")
        self.logger.info(f"Preparing textures for {workflow}")
        self.logger.info(f"{'='*60}\n")

        try:
            results = MapFactory.prepare_maps(
                texture_paths,
                **config,
            )

            if isinstance(results, dict):
                self.logger.info(f"Processed {len(results)} texture sets.")
                for base_name, maps in results.items():
                    self.logger.info(f"\n[ok] Set: {base_name}")
                    for m in maps:
                        self.logger.info(f"  - {FileUtils.format_path(m, 'name')}")
            else:
                self.logger.info("\n[ok] Processed single set.")
                for m in results:
                    self.logger.info(f"  - {FileUtils.format_path(m, 'name')}")

        except Exception as e:
            self.logger.error(f"Error during batch processing: {e}")

        self.logger.info(f"{'='*60}")
        self.logger.info("Workflow preparation complete!")
        self.logger.info(f"{'='*60}\n")

        try:
            self.source_dir = FileUtils.format_path(texture_paths[0], "path")
        except Exception:
            pass
