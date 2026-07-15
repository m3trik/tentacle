"""Maya->Blender parity triage ledger — the SSoT for every *conscious* divergence.

Consumed by ``m3trik/scripts/compare_panel_surface.py`` (and ``generate_parity_audit.py``).
Every Maya-side surface element that intentionally has no identical Blender twin gets an
entry here; anything NOT ledgered (and not mechanically matched) reports as an UN-TRIAGED
delta and fails the sweep. This file is pure data — dict literals only, no imports — so
the tools load it without executing project code.

Entry statuses
--------------
- ``na``            no Blender surface, by design (reason required).
- ``renamed``       same capability under a different objectName (``to`` = Blender name).
- ``relocated``     same capability in a different file (``to`` = "file.py:objectName").
- ``replaced``      a different control *model* covers it (``to`` = short model name).
- ``divergent``     a different Blender paradigm covers the need (legacy status migrated
                    from dcc_parity_overrides.json — semantically between na and replaced).
- ``done-elsewhere`` built under another objectName/mechanism (legacy; like renamed/relocated).
- ``pending``       a REAL gap, acknowledged and tracked as open work (does not fail the
                    sweep; listed in the report's open-work section).
- ``accepted-delta`` same-named control, intentionally different default/property value.

Keys
----
CONTROLS / HANDLERS are keyed by the *Maya* file stem the pair is resolved from
(``naming_slots``, ``selection``, ...), then by the control key / handler def name the
extractor produces. PANELS is keyed by the mayatk ``*Slots`` class name. DEFAULT_DELTAS
is keyed ``"<control>.<property>"``.
"""

# --------------------------------------------------------------------------- co-located panels
CONTROLS = {
    "arnold_bridge": {
        "config_buttons:menu": {"status": "na", "reason": "the panel is permanently inert (no Arnold-for-Blender integration at all); ArnoldBridgeSlots.header_init deliberately defines no menu actions -- see the file's own module docstring"},
        "config_buttons:collapse": {"status": "na", "reason": "same as config_buttons:menu"},
        "config_buttons:hide": {"status": "na", "reason": "same as config_buttons:menu"},
        "select_bridged": {"status": "na", "reason": "Cycles/EEVEE read one Principled BSDF graph -- there is no parallel Arnold-preview material to select back to (see _NOT_AVAILABLE in blendertk's arnold_bridge.py)"},
    },
    # mayatk file stem is scene_exporter/_scene_exporter.py. Ported 2026-07-04 -- cmb000 (FBX
    # export-option preset combo) and its option-box b003/b004/b007/b008 are real, built 1:1 by
    # objectName against a pythontk.PresetStore-backed named-JSON-dict preset engine (see
    # blendertk/blendertk/env_utils/scene_exporter/_scene_exporter.py's module docstring for why
    # that design was chosen over Blender's native bl_options={'PRESET'} operator-preset system).
    # No entry needed here anymore -- nothing to ledger.
    # rizom_bridge_slots: fully 1:1 as of 2026-07-15 — the round-trip pipeline is now ported
    # (blendertk RizomUVBridge.process_with_rizomuv: export __RZTMP copies -> headless RizomUV -> re-
    # import -> transfer UVs back). cmb000 is now a real preset picker listing the same five
    # scripts/*.lua stems mayatk does (optimize/pack/send/unwrap_hard/unwrap_organic, matched by the
    # sweep's combo-item-list check), backed by the same parameters.PARAMS + version-gating. The
    # header-menu buttons (btn_open_scripts / btn_refresh_scripts / btn_clear_log / btn_open_uv_editor)
    # match by objectName. Nothing to ledger — no entry needed here anymore. (Prior to this the entry
    # marked cmb000 `na` for the thin send-only bridge; that gap is closed.)
    # mayatk file stem is audio_utils/audio_clips/audio_clips_slots.py. Ported 2026-07-03 --
    # see blendertk/blendertk/audio_utils/_audio_utils.py + audio_clips.py's module docstrings
    # for the full "why" (Maya's single-slot Time-Slider + WAV-only playback forced the
    # composite-WAV/DG-node/two-phase-register-then-key machinery below; the VSE plays any
    # number of simultaneous strips natively and decodes MP3/OGG/FLAC/etc. on its own, so none
    # of it has a Blender counterpart). cmb000/tb001 + the Rename/Replace/Remove-All menu
    # buttons are reused 1:1 by objectName (real Blender builds, not stubs).
    "audio_clips_slots": {
        "chk_auto_convert": {"status": "na", "reason": "Maya's Time Slider only plays WAV/AIFF, so mayatk ffmpeg-converts MP3/OGG/M4A/FLAC on import; the VSE's own media backend decodes all of those natively -- there is no conversion step to gate."},
        "cmb_export_mode": {"status": "na", "reason": "Composite/Keyed-Tracks/All-Tracks export exists only to get audio OUT of Maya's single-slot composite-WAV workaround; a VSE strip already IS a real audio asset in the .blend (and on disk, at its original path) with nothing to bake or export."},
        "btn_export": {"status": "na", "reason": "same composite-export gap as cmb_export_mode -- no composite exists to export."},
        "chk_trim_silence": {"status": "na", "reason": "a Composite-WAV export postprocess; no composite export step exists on the Blender side (see cmb_export_mode)."},
        "chk_suffix_time_range": {"status": "na", "reason": "a Keyed-Tracks export filename convenience; no per-clip export step exists on the Blender side (see cmb_export_mode)."},
        "btn_channels": {"status": "na", "reason": "opens the Channels UI pinned to Maya's data_internal carrier node's hidden per-track attrs; a VSE strip has no carrier node or hidden attrs to pin -- its properties already show directly in the Sequencer's own N-panel."},
        "chk_auto_end_none": {"status": "na", "reason": "auto-keys an OFF value at a track's natural end so Maya's keyed-enum model has an explicit end marker; a VSE strip's end is already an intrinsic property (duration/right_handle) with no separate end-key to author."},
        "chk_snap_frames": {"status": "na", "reason": "rounds keyed audio-event times to whole frames; a VSE strip's frame_start/handles are integer frame properties by construction -- there is no sub-frame state to snap away."},
        "chk_next_event": {"status": "na", "reason": "auto-advances the combo to the next unkeyed track after keying one -- an artifact of Maya's manual one-track-at-a-time keying workflow; add_clip already both registers and places a clip in one step, so there is no unplaced-track queue to advance through."},
        "chk_key_all": {"status": "na", "reason": "queues every loaded track to be keyed sequentially end-to-end -- exists only to work around Maya's single-slot Time Slider needing one composite; the VSE already plays any number of simultaneous strips, so there is no slot-contention problem this solves. Revisit as a genuine 'auto-lay-out clips end to end' convenience if ever requested -- would be portable (compose with move_clip/AudioUtils.list_clips), just out of this port's add/remove/trim/query/sync scope."},
        "spn_stagger": {"status": "na", "reason": "the extra-frames spacing knob for chk_key_all's queue -- no Blender counterpart for the same reason (see chk_key_all)."},
        "btn_cleanup_unused": {"status": "na", "reason": "deletes tracks that were registered (a file_map entry) but never keyed -- Maya's two-phase register-then-key workflow allows that unplaced state. A VSE strip is always both registered and placed the moment add_clip creates it, so there is no unused/unkeyed state to clean up."},
    },
    # mayatk file stem is anim_utils/smart_bake/smart_bake_slots.py. Ported 2026-07-04 -- see
    # blendertk/blendertk/anim_utils/smart_bake/_smart_bake.py + smart_bake_slots.py's module
    # docstrings for the full "why" (Blender's nla.bake always writes a brand-new Action, so
    # there is no separate override-layer-vs-base-layer bake target the way Maya's animLayer
    # model has one; chk_use_override/chk_delete_sources collapse mayatk's separate
    # layer/mute-driver checkboxes into a single mute-vs-delete-sources choice). cmb_scope,
    # spn_sample_by, chk_preserve_outside, chk_optimize, label, and cmb_backup are reused 1:1
    # by objectName (real Blender builds, verified against the .ui, not stubs).
    "smart_bake_slots": {
        "chk_bake_blendshapes": {
            "status": "renamed", "to": "chk_bake_blend_shapes",
            "reason": "same drive-blend-shape-weights bake capability, corrected snake_case spelling (blend_shapes, not blendshapes)",
        },
        "chk_delete_inputs": {
            "status": "renamed", "to": "chk_delete_sources",
            "reason": "same permanently-remove-drivers-after-baking capability; 'Delete Sources' matches the panel's own Mute Sources/Delete Sources wording pair (see chk_use_override)",
        },
        "cmb_bake_layer": {
            "status": "replaced", "to": "chk_use_override",
            "reason": "Override Layer / Base Layer bake-target selector (was chk_override_layer). Blender's bake always produces a brand-new Action -- there is no separate override-layer-vs-base-layer bake target to choose between, so there's no 'which layer' axis for this control to name; chk_use_override instead names the mute-vs-delete-sources choice that replaces it (see _smart_bake.py's module docstring)",
        },
        "chk_mute_drivers": {
            "status": "na",
            "reason": "only meaningful in mayatk as an alternative to use_override_layer=False base-layer bakes; blendertk has no base-layer-conversion bake mode, so chk_use_override's mute/delete choice already covers the full space",
        },
        "chk_inherited_vis": {
            "status": "na",
            "reason": "Blender's hide_viewport/hide_render are not inherited down a parent chain the way Maya's DAG visibility is, and AnimUtils.set_visibility_keys already covers direct visibility keying -- stated as a permanent scope cut in _smart_bake.py's own module docstring, matching the precedent set porting hierarchy_manager",
        },
    },
    "reference_manager": {
        "btn_convert_assembly": {"status": "na", "reason": "assemblies have no Blender analogue"},
        "btn_unlink_import_all": {
            "status": "renamed", "to": "btn_make_local_all",
            "reason": "Blender 'make local'",
        },
        "btn_unreference_all": {"status": "renamed", "to": "btn_remove_all", "reason": "remove"},
        "btn_unlink_import": {
            "status": "replaced", "to": "row_make_local",
            "reason": "row action -> 'Make Local' (make_library_local)",
        },
        "btn_toggle_reference": {
            "status": "replaced", "to": "link icon + Link/Append",
            "reason": "reference toggle -> link icon + 'Link'/'Append'",
        },
        "b001": {"status": "renamed", "to": "btn_set_current_ws", "reason": "root option box"},
        "b006": {"status": "renamed", "to": "btn_open_dir", "reason": "root option box"},
        "btn_open_scene": {"status": "renamed", "to": "row_open", "reason": "context menu"},
        "btn_rename_scene": {"status": "renamed", "to": "row_rename", "reason": "context menu"},
        "btn_delete_scene": {"status": "renamed", "to": "row_delete", "reason": "context menu"},
        "btn_open_file_location": {"status": "renamed", "to": "row_location", "reason": "context menu"},
        "chk_hide_binary": {
            "status": "na",
            "reason": ".mb is Maya-only; .blend1 backups already excluded by find_blend_files",
        },
        "chk000": {"status": "renamed", "to": "chk_recursive", "reason": "Recursive lives in the header menu"},
        "chk003": {
            "status": "na",
            "reason": "ignore-empty-workspaces is moot; find_workspaces never returns empty dirs",
        },
        "txt_subfolder_structure": {"status": "renamed", "to": "txt_subfolder", "reason": "shorter name"},
    },
    "channels_slots": {
        # add_action (txt000 filter ON/OFF toggle) ported 2026-07-03 — mirrors mayatk
        # channels_slots.py:144-164 verbatim (option_box.clear_option + 2-state add_action +
        # _filter_enabled gate in _refresh_table). No longer a divergence.
        # cmb_attr_type (Create-Attribute type combo) is a QComboBox, so its item-list difference is
        # a report-only "combo item deltas (review)" line, not a gate -- disposition documented in
        # DEFAULT_DELTAS['channels_slots']['cmb_attr_type.items'] (Maya's 'enum' is na; 'double3' was
        # BUILT 2026-07-08 as Blender's native 'vector' 3-float array type). No CONTROLS entry: the
        # combo control itself is present on both sides, and item-level keys can't be a 'renamed'
        # CONTROL (the .ui-lint requires a renamed target to be a real control objectName).
        "chk_keyable": {
            "status": "na",
            "reason": "every Blender custom prop is keyable; no per-attr keyable flag",
        },
        "le_enum_names": {
            "status": "na",
            "reason": "Blender custom props have no Maya-style enum type on arbitrary objects",
        },
        "Names:": {"status": "na", "reason": "label for the enum-names field (see le_enum_names)"},
        "hdr_channel_control": {
            "status": "na",
            "reason": "Maya Channel Control editor; Blender -> Properties/Drivers/Graph editors",
        },
        "hdr_connection_editor": {"status": "na", "reason": "Maya Connection Editor; no Blender analogue"},
    },
    "blendshape_animator_slots": {
        "btn_recover_setup": {
            "status": "na",
            "reason": "mayatk's 'Recover Setup' rebuilds a corrupted blendShape NODE (Maya's "
            "deformer can end up in a broken position in the DAG). A Blender shape key is data "
            "on the mesh, not a separate node that can end up corrupted that way -- there is "
            "nothing analogous to rebuild. 'Recover Animation' (b005, a lost KEYFRAME range) IS "
            "ported -- see _blendshape_animator.py's module docstring.",
        },
    },
    "hdr_manager": {
        # add_value / add_hdr_btn / cmb_add_mode / clear_network / config_buttons drift
        # closed 2026-07-03 (ported to blendertk: option-box add_value on slider000, the
        # Add HDR(s)… flow, Clear Network header action, config_buttons header chrome, and
        # the slider000/spn_exposure/spn_intensity .ui promotion to uitk classes).
        "spn_diffuse": {"status": "replaced", "to": "chk_diffuse", "reason": "Arnold float aiDiffuse contribution maps to the boolean Cycles world ray-visibility Diffuse toggle (EEVEE ignores it)"},
        # spn_resolution: BUILT 2026-07-08 (was a false na). Now enabled + wired to
        # btk.set_world_importance_resolution (world.cycles.sampling_method='MANUAL' +
        # sample_map_resolution) -- the Cycles analogue of Arnold's skydome importance-sampling
        # Resolution. No divergence to ledger (control present + functional on both, .ui `enabled`
        # matches Maya's None now). spn_samples below stays na -- Cycles has no per-world sample count.
        "spn_samples": {"status": "na", "reason": "Arnold skydome light samples (aiSamples); Cycles samples globally, no per-light sample count (documented drop)"},
        "spn_specular": {"status": "replaced", "to": "chk_glossy", "reason": "Arnold float aiSpecular contribution maps to the boolean Cycles world ray-visibility Glossy toggle (EEVEE ignores it)"},
        # Triaged divergences (were documented in prose/docstrings but never machine-readable):
        "ctx_select_skydome": {"status": "na", "reason": "a Blender world isn't a selectable scene object"},
        "ctx_select_transform": {"status": "na", "reason": "a Blender world isn't a selectable scene object"},
        "ctx_select_file_node": {"status": "na", "reason": "a Blender world isn't a selectable scene object"},
        # ctx_reveal_in_explorer / open_sourceimages: stale entries removed 2026-07-03 — both
        # ship under the SAME objectName as mayatk (verified against the current file), not the
        # "btn_reveal_hdr"/"btn_open_folder" names these entries claimed; no divergence to ledger.
    },
    "naming_slots": {
        "tb003_txt007": {
            "status": "na",
            "reason": "_LYR suffix-by-type target; Maya display layers have no Blender analogue",
        },
    },
    # wheel_rig chk_world_space: stale `na` "always world-space" entry removed 2026-07-08 -- the
    # control EXISTS in Blender under the identical objectName (rig_utils/wheel_rig.py:299) as a
    # fully-wired toggle that DEFAULTS OFF (use_world_space=False -> transform_space='TRANSFORM_SPACE',
    # i.e. LOCAL, wheel_rig.py:199) exactly like Maya; the prior reason was factually wrong on every
    # clause. Only the label differs ('World Space (decomposeMatrix)' -> 'World Space (driver Transform
    # Space)', naming Blender's TRANSFORMS-driver-var mechanism for Maya's decomposeMatrix node) -- a
    # report-only setText review delta, same capability, no ledger entry needed.
    "color_id": {
        # add_presets / preset_dir: BUILT — the Blender ColorIdSlots.header_init ships the swatch-
        # palette preset combo 1:1 (color_id.py:330-334 widget.menu.add_presets=True + presets
        # .preset_dir=self._PRESET_DIR + metadata_provider/on_metadata_loaded + _ensure_default_preset),
        # a DCC-agnostic uitk feature (swatches are Qt-side) matching mayatk color_id.py:406-448. The
        # store key is Blender's own 'blendertk/color_id' (color_id.py:237), not Maya's legacy
        # 'mayatk/color_manager'. The header preset combo is not a distinct objectName the static sweep
        # tracks, so no ledger row is needed now that both sides build it.
        "chk012": {"status": "na", "reason": "Maya wireframe-override color channel (overrideEnabled/overrideRGBColors/overrideColorRGB); Blender has no per-object wireframe color — Maya's outliner+wireframe tints collapse into the single obj.color Object Color channel (documented drop)."},
    },
    "game_shader": {
        "cmb002": {"status": "na", "reason": "Output Template (workflow-preset) map-export knob; Blender flow wires existing textures into the node graph and never bakes/writes maps (documented drop)"},
        "cmb003": {"status": "na", "reason": "Ext output-format knob for the map-export step; Blender flow wires existing textures and never writes output maps (documented drop)"},
        "cmb004": {"status": "na", "reason": "Maya shader-type choice (Stingray PBS / Standard Surface / OpenPBR are Maya shader nodes); Blender builds the one Principled BSDF (documented drop)"},
        # lbl_graph_material: removed 2026-07-11 — Blender ships it 1:1 (game_shader.py:76,107 ->
        # btk.graph_materials opens the Shader Editor), matched by objectName (GameShader 0 triaged).
    },
    "image_tracer": {
        "blue_pencil_button": {
            "status": "na",
            "reason": "Maya Blue Pencil; Grease-Pencil->curve is the deferred opt-in",
        },
        "chk000": {
            "status": "na",
            "reason": "Use Blue Pencil toggle; see blue_pencil_button",
        },
    },
    "image_to_plane": {  # mayatk file stem is env_utils/image_to_plane/... ; added 2026-07-08
        "cmb_mat_type": {"status": "na", "reason": "Maya shader-node-type pick (Stingray PBS realtime/DX11 vs Standard Surface Arnold/offline); Blender builds the one unified Principled BSDF for both EEVEE and Cycles, so there is no shader-node-type choice to make -- the Blender combo is disabled by design (documented in the module docstring). Same shape as game_shader.cmb004."},
    },
    "lightmap_baker": {
        # config_buttons header chrome closed 2026-07-03 (config_buttons("menu","collapse","hide")).
        # cmb002 Packing combo (Per-Object / Atlas by Material): BUILT 2026-07-13. blendertk
        # LightmapBaker.pack_atlas now ports mayatk's atlas consolidation — per-primary-material
        # grouping (obj.material_slots / dominant material_index), area-weighted rects REUSING the
        # DCC-agnostic pythontk layout math (ptk.ImgUtils.compute_atlas_layout / inset_atlas_rects /
        # atlas_pixel_rects — all pure-Python, no cv2, the same helpers mayatk uses), one shared EXR
        # per group assembled via bpy image I/O + a numpy paste/gutter-dilate (Blender's runtime has
        # no cv2), and a per-object lightmap-UV repack into each rect (so the mesh samples the atlas
        # via UV2 — engine scaleOffset stays identity, the applied rect rides the marker's uvRect and
        # is undone by revert_lightmap). The "Atlas by Material" item is enabled (the old
        # _disable_unsupported_packing_mode removed); the slot b000 atlas branch calls pack_atlas +
        # commit_lightmap(uv_rects=…). Verified end-to-end headlessly (blendertk/test/
        # test_lightmap_baker.py: 2 objects sharing a material -> 1 shared area-weighted EXR, source
        # maps consolidated, UVs repacked into their rects, revert EXACTLY restores the 0-1 layout).
        # cmb002 is a QComboBox present+functional on both sides -> no ledger row needed.
        "open_sourceimages": {
            "status": "na",
            "reason": "no sourceimages workspace in Blender; output dir browsed explicitly",
        },
    },
    "mat_updater": {
        # chk_discover_sourceimages: removed 2026-07-11 — Blender ships it 1:1 (mat_updater.py:161,310
        # -> _mat_utils.py:1469 maps discover_sourceimages -> discover_dir = the .blend workspace dir),
        # matched by objectName against the Maya panel (mat_updater.py:785,958); MatUpdater 0 triaged.
        "cmb_transfer_mode": {
            "status": "na",
            "reason": "copy/move transfer doesn't map — Blender engine writes to output_dir, "
                      "sources stay in place",
        },
        "txt_old_files": {
            "status": "na",
            "reason": "archive-folder companion of cmb_transfer_mode (same model difference)",
        },
    },
    "_shader_templates": {  # mayatk file stem is shader_templates/_shader_templates.py
        # b002 / lbl000 / lbl001 / lbl_open_templates_dir: stale entries removed 2026-07-03 — the
        # current file is a verbatim 1:1 objectName mirror (its own module docstring: "same
        # objectNames, same header-menu layout, same method shapes"); Save/Rename/Delete/Open-
        # -templates-dir ship under the IDENTICAL names these entries claimed were renamed away
        # from. No divergence to ledger.
        # lbl002 ("Open Template File"): BUILT — the Blender twin ships it 1:1 on the cmb002
        # submenu (shader_templates.py:167-172 add_action + def lbl002:206-209 -> ptk.open_explorer
        # of self._store.path(template,"user")), matched by objectName against the Maya panel
        # (_shader_templates.py:594-599 / lbl002:646-649). Saved templates are PresetStore JSON
        # files, so open-in-editor is portable exactly as the Maya YAML entry is. No divergence.
        # lbl_graph_material: removed 2026-07-11 — Blender ships it 1:1 (shader_templates.py:107,135
        # -> btk.graph_materials opens the Shader Editor), matched by objectName against the Maya
        # panel (_shader_templates.py:529,558); ShaderTemplates 0 triaged.
    },
    "tube_rig": {
        # HYBRID panel: static s000/s001/s002/chk_stretch became AttributeSpec options
        # (num_joints/num_controls/radius/enable_stretch) built into wgt_options per mode.
        "s000": {"status": "replaced", "to": "spec:num_joints", "reason": "AttributeSpec option"},
        "s001": {"status": "replaced", "to": "spec:num_controls", "reason": "AttributeSpec option"},
        "s002": {"status": "replaced", "to": "spec:radius", "reason": "AttributeSpec option"},
        "chk_stretch": {"status": "replaced", "to": "spec:enable_stretch", "reason": "AttributeSpec option"},
        # DEFORM TOGGLES — DONE 2026-07-11 (chk_stretch/squash/volume/auto_bend above): the prior
        # "no Blender engine counterpart yet" rulings were over-scoped. Blender's Spline IK collapses
        # Maya's per-node deform graphs to native constraint options — stretch=Y FIT_CURVE,
        # squash/volume=XZ INVERSE_PRESERVE/VOLUME_PRESERVE — and auto_bend is one distance-driver on
        # the mid control. chk_twist DONE too (its entry): Spline IK ignores curve tilt, so twist is a
        # roll-control bone + per-bone Copy Rotation chain (the one non-native toggle) — TubeRig fully ported.
        #
        # The deferral's core premise — "rig correctness requires a LIVE interactive Blender; headless
        # tests can't confirm the mesh deforms right" — is REFUTED. test_tube_rig.py already verifies
        # deform numerically via the EVALUATED depsgraph (move a control -> read obj.evaluated_get(dg)
        # .to_mesh() -> assert the deformed bbox/cross-section changed). Every deform toggle above is
        # locked by such a headless test. So TubeRig is buildable + verifiable headlessly, NOT a
        # live-only item.
        #
        # GRANULAR STEP-WORKFLOW — b001/b002/b003 + chk000 DONE 2026-07-11. The engine methods already
        # existed and deform (create_joint_chain=Step1, attach_spline_rig=Step2, RigUtils.bind_armature
        # =Step3; reverse=chk000). Added the buttons to a "Manual Steps (Spline)" group in tube_rig.ui
        # + the TubeRigSlots b001/b002/b003 methods dispatching to those engine methods on the user's
        # selection (b002 resolves the chain via a mesh-less TubeRig reusing the armature's root).
        # Verified by tube_rig_slot_check.py 9/9 (incl. the moved-control deform check + chk000 reverse).
        # The b001/b002/b003 (PushButton) + chk000 (QCheckBox) class deltas vs Maya's QPushButton are
        # review-only — the same accepted cross-DCC pattern as b000. Tracked in PARITY_PORTING_PLAN.md.
        # (cmb_preset/txt000 uitk .ui promotion closed 2026-07-03.)
        #
        # b004 Add End Constraints — DONE 2026-07-11. The "needs a NEW per-vertex weight-blend algorithm
        # that doesn't exist here" ruling was the last over-scoped one. Ported as two reusable RigUtils
        # primitives — RigUtils.add_bone (single-bone graft) + RigUtils.apply_falloff_weights (the
        # per-vertex distance blend: target group = 1 - d/r, existing influences scaled by (1-w) so the
        # row REDISTRIBUTES not adds — Maya's skinPercent semantics, crease-free at the boundary) — plus
        # TubeRig.constrain_end_with_falloff (an anchor bone COPY_LOCATION-tracking the external object +
        # the falloff paint) and the TubeRigSlots.b004 slot (armature + 2 anchors selection, bound-mesh
        # lookup, proximity-based nearest-end assignment since Blender selection order is unreliable).
        # Verified headlessly: test_tube_rig.py (falloff deform + exact redistribution invariant, 33/33)
        # + tube_rig_slot_check.py (slot resolution + anchor-driven deform, 11/11). Divergence: Maya's
        # parentConstraint copies position AND orientation; the port copies translation (COPY_LOCATION)
        # to stay bind-time-stable (anchor rotation-follow would need a maintain-offset CHILD_OF inverse).
        # b004 (PushButton) class delta is review-only. With b004 + chk_twist done, the TubeRig panel is
        # FULLY PORTED — no pending items remain (only same-named PushButton/QCheckBox class deltas).
        "chk_squash": {"status": "replaced", "to": "spec:enable_squash", "reason": "AttributeSpec option (SplineIKStrategy) — native Spline IK XZ scale INVERSE_PRESERVE (squash without volume)"},
        "chk_volume": {"status": "replaced", "to": "spec:enable_volume", "reason": "AttributeSpec option (SplineIKStrategy) — native Spline IK XZ scale VOLUME_PRESERVE (squash + volume); Maya's 2 bools collapse onto the one XZ enum via _xz_scale_mode"},
        "chk_auto_bend": {"status": "replaced", "to": "spec:enable_auto_bend", "reason": "AttributeSpec option (SplineIKStrategy) — distance-driven mid-control bulge (add_distance_driver on delta_location, mirrors Maya setup_auto_bend's multiplyDivide)"},
        "chk_twist": {"status": "replaced", "to": "spec:enable_twist", "reason": "AttributeSpec option (SplineIKStrategy) — DONE 2026-07-11. Blender Spline IK ignores the driver curve's point tilt (probed), so twist is the one toggle with NO native scale-mode equivalent: TubeRig.add_twist builds a tip roll-control bone + a per-deform-bone Copy Rotation (local Y, mix ADD, CONSTANT influence 1/N) that composes AFTER the Spline IK solve — equal local increments accumulate LINEARLY down the parented chain, so rolling the control twists the tip a full turn while the start stays ~put. Verified headlessly (test_tube_rig.py: a 90deg roll -> tip cross-section 81deg vs start 19deg = progressive; + the OFF gate). The prior 'needs a custom bendy-bone, not a native toggle' ruling was right that it's not native but wrong that it wasn't portable."},
        # Note: Maya's spline default is Auto (-1 = one joint per edge loop); TubePath
        # supports -1 but the Blender spec's minimum=2 makes Auto unreachable from the UI.
    },
    # mirror / cut_on_axis / duplicate_linear: the cmb000->cmb002/cmb001/cmb003-style "renamed for
    # QSettings isolation" entries formerly here were removed 2026-07-03 — all three files now keep
    # the IDENTICAL objectName as mayatk (confirmed against current source: mirror.py/cut_on_axis.py/
    # duplicate_linear.py docstrings each state "same objectNames" / "1:1 objectName mirror" and the
    # QSettings collision is solved a different way at the Switchboard/MainWindow level instead).
    # No divergence to ledger; the item-count drop (Maya's Manip pivot has no Blender analogue)
    # still shows as a non-blocking combo-item "review" delta.
    # duplicate_radial.chk008 (Suffix) removed 2026-07-08: it is NOT dropped — the Blender
    # slot builds chk008 (identical .ui) and wires suffix=self.ui.chk008.isChecked() into
    # duplicate_radial(..., suffix=…) -> Naming.append_location_based_suffix. Fully built on
    # both sides (sweep sees no delta); the old "intentionally dropped" na was stale.
    "texture_path_editor": {
        # btn_open_source_images / delete_file_node / row_show_in_hypershade: stale `na` entries
        # removed 2026-07-08 -- all three ship in Blender under the IDENTICAL objectName (verified
        # against blendertk/mat_utils/texture_path_editor.py: open_source_images os.startfile()s the
        # resolved <blenddir>/textures folder; delete_file_node removes the image datablock via
        # bpy.data.images.remove after a confirm; row_show_in_hypershade graphs the row's material via
        # btk.open_editor("Shader Editor")). The capabilities were ported+relabeled, not dropped --
        # the label differences are report-only setText review deltas, not divergences to ledger.
        "select_file_node": {"status": "na", "reason": "no separable file node in Blender (kept as a disabled structural placeholder in the Blender panel)"},
    },
    # UV Transform tool (co-located mayatk/blendertk uv_utils/shell_xform.py). FULL parity as of
    # 2026-07-11 (Phase 1c): the Blender twin now ships every Maya shell op — move/flip/rotate/
    # straighten/mirror/distribute PLUS Align (min/avg/max + linear), Orient (shells + to-edge),
    # Gather, and Randomize. Those Align/Orient/Gather/Randomize buttons were previously ruled `na`
    # ("no bpy analogue"); that was an over-scope, corrected by the inverse audit. Realizations,
    # each probed live in headless Blender 5.1 before building:
    #   - orient_shells / orient_edges -> native bpy.ops.uv.align_rotation(AUTO|EDGE)
    #   - randomize_shells            -> native bpy.ops.uv.randomize_uv_transform (seeded)
    #   - align_u/v_min/avg/max       -> btk.align_uvs bmesh helper (avg = arithmetic mean of the
    #                                    selected UVs; the natural reading of Maya avgU, exact
    #                                    averaging method owed a live-Maya check)
    #   - linear_align                -> btk.align_uvs mode="linear" (project onto the endpoint line)
    #   - gather_shells               -> btk.gather_uv_shells bmesh helper (floor-subtract per island)
    # All 15 controls (2 groups, 2 row labels, 7 align + 4 orient buttons) now match 1:1, so their
    # ledger entries are dropped (dead — the sweep only consults `na` for a control MISSING from
    # Blender). select_back_facing / select_overlapping / select_unmapped were removed from the
    # Maya panel 2026-07-08, so there's no widget left to ledger either.
    "shell_xform": {},
}

# --------------------------------------------------------------------------- tentacle shared slots
# Keyed by slot file stem; entries cover both handler defs and code-built control keys.
HANDLERS = {
    # duplicate: tb002 Auto Instance (+ its option box chk004-011/s000/s001) ported
    # 2026-07-08 — blendertk core_utils/auto_instancer (btk.auto_instance), with the
    # matching math and assembly clustering extracted to pythontk
    # (PointCloud.match_clouds / AssemblySorter) and mayatk refactored onto the same
    # shared implementation. Verified: blendertk test_auto_instancer.py headless +
    # mayatk auto_instancer/instancer_ground_truth suites green.
    "cameras": {
        # PARITY_SURFACE.md "combo item deltas (review)": `list000` 11->5 items; missing=
        # ['Exclusive to Camera', 'Hidden from Camera', 'Remove from Exclusive',
        # 'Remove from Hidden', 'Remove All for Camera', 'Remove All']. Audited 2026-07-04.
        "list000": {
            "status": "na",
            "reason": "Maya's 4th list000 group ('Visibility Settings', the 6 items above) drives "
                      "the per-camera 'camera sets' isolate-visibility MEL commands "
                      "(SetExclusiveToCamera/SetHiddenFromCamera/CameraRemoveFromExclusive/"
                      "CameraRemoveFromHidden/CameraRemoveAll/CameraRemoveAllForAll) — objects are "
                      "shown/hidden conditionally on which camera is currently being looked "
                      "through. Blender has no per-camera-object visibility primitive to match: "
                      "object visibility is either global (hide_viewport/hide_render, or Cycles "
                      "ray-visibility flags like visible_camera — hides an object from ALL cameras, "
                      "not one) or Scene/View-Layer/Collection-scoped (excluding a Collection from a "
                      "View Layer is a per-Scene/View-Layer setting, not a live per-camera toggle "
                      "flippable while orbiting). A faithful port would mean inventing a new "
                      "subsystem (custom properties per camera + a depsgraph/render handler "
                      "continuously re-deriving hide_render from scene.camera) with no native "
                      "Blender feature to anchor it to — out of scope for a capability port (see "
                      "CLAUDE.md YAGNI/OCP: don't build speculative infrastructure). Workflow "
                      "substitute: give each camera its own Scene (or View Layer) and use Collection "
                      "exclusion to control what's visible when rendering/looking through that "
                      "camera, or Object > Visibility > Ray Visibility > Camera (Cycles) to hide an "
                      "object from all camera rays at once. Checked blendertk/API_INDEX.md and "
                      "cam_utils/_cam_utils.py — no existing helper covers this; none added.",
        },
    },
    "nurbs": {
        "b016": {"status": "na", "reason": "[Create Curve from Edges] widget removed from nurbs.ui 2026-05-20 (9f534ba3) but the handler is pinned by test_nurbs.py (create_curve_from_edges fallback) - retarget the test at mtk directly, then delete the handler"},
        # list000 "Nurbs actions" leaves -- code-built control keys sourced from
        # Nurbs._LIST000_COMMANDS (tentacle/tentacle/slots/blender/nurbs.py), the Blender-idiom
        # mirror of Maya's _LIST000_COMMANDS (tentacle/tentacle/slots/maya/nurbs.py). Ported
        # 2026-07-04: root->category->leaf tree structure now matches Maya 1:1
        # (Create/Modify/Surfaces/Edit), and 12 of Maya's 24 leaves are real bpy ops/props
        # (Project, Extract, Duplicate, Smooth, Planar, Edit Curve Tool, Attach, Detach, Cut,
        # Open/Close, Add Points Tool, Reverse). Audit previously found the WHOLE widget
        # hidden (widget.setVisible(False), "no Blender analogue") despite most leaves having a
        # genuine 1:1 bpy op; these entries are only the leaves that are true parametric-NURBS
        # concepts with no Blender/mesh-curve equivalent, intentionally not built rather than
        # silently dropped -- see the module's own _LIST000_COMMANDS comment for the full
        # per-leaf reasoning.
        "list000:Lock": {"status": "na", "reason": "Lock Curve Length constrains a NURBS curve to a fixed arc length under deformation; a Blender curve/mesh control point has no such constraint to toggle."},
        "list000:Unlock": {"status": "na", "reason": "see Lock"},
        "list000:Bend": {"status": "na", "reason": "Maya drives Bend from its own option-box magnitude/weight; Blender's nearest analogue (Simple Deform modifier) is a persistent modifier needing that same kind of dedicated option UI as this file's own tb000/tb001 tools, not a parameterless one-click list action -- reviewer's call, same as flagged by the parity audit. VERIFIED 2026-07-11 (headless Blender 5.1): a SIMPLE_DEFORM/BEND modifier applied to a curve DOES bake into the bezier control points, but ONLY when deform_axis is perpendicular to the curve's plane (deform_axis='Z' bends an X/Y-planar curve; 'X'/'Y' are silent no-ops) -- so a fixed-axis parameterless Bend no-ops for common orientations. A faithful Bend needs an option box (deform_axis + angle) = the dedicated option UI above; buildable later as a tb-style tool, stays na as a list-leaf action. (The 2026-07 divergence re-audit's 'trivial SIMPLE_DEFORM+apply' overturn is refuted by this probe.)"},
        "list000:Curl": {"status": "na", "reason": "see Bend"},
        "list000:Curvature": {"status": "na", "reason": "see Bend"},
        "list000:Straighten": {"status": "na", "reason": "see Bend -- Maya's StraightenCurves interpolates CVs toward a line by a magnitude/weight parameter; no parameterless Blender op matches."},
        "list000:Insert Isoparm": {"status": "na", "reason": "Isoparms are a parametric NURBS-surface-only concept; Blender's Screw/loft-bridge surfaces are meshes with no isoparm to insert."},
        "list000:Insert Knot": {"status": "na", "reason": "Knot insertion is parametric NURBS-curve re-parameterization; a Blender POLY/NURBS spline's control points have no knot vector exposed to Python to insert into."},
        "list000:Rebuild": {"status": "na", "reason": "RebuildCurveOptions re-parameterizes a NURBS curve's knot/span structure; no Blender op rebuilds a spline's parameterization this way."},
        "list000:Extend (Options)": {"status": "na", "reason": "Tolerance-based parametric curve extension (extend by a distance/tolerance along the curve's own parameterization); no Blender op extends a curve this way."},
        "list000:Extend": {"status": "na", "reason": "see Extend (Options)"},
        "list000:Extend on Surface": {"status": "na", "reason": "see Extend (Options) -- extending a curve constrained to a NURBS surface has no Blender analogue (no parametric surface-constrained curve concept)."},
    },
    "selection": {
        "chk000": {"status": "na", "reason": "QRadioButton siblings are auto-exclusive; Maya's manual "
                                             "uncheck handlers are redundant on Blender"},
        "chk001": {"status": "na", "reason": "see chk000"},
        "chk002": {"status": "na", "reason": "see chk000"},
        # cmb003 "Convert To" -- ported 2026-07-06 from 7 to 15 of Maya's 20 items (Vertex
        # Perimeter, Contained Edges, Edge Perimeter, Contained Faces, Face Path, Face
        # Perimeter, UV Shell, Shell Border added; touching-vs-contained on plain Faces/Edges
        # fixed to match Maya -- see btk.Selection.convert_to's docstring). UV Shell Border / UV
        # Perimeter / UV Edge Loop were BUILT 2026-07-13 (bmesh UV-graph helpers on btk.Selection --
        # select_uv_shell_border / select_uv_perimeter / select_uv_edge_loop, keyed off a single
        # UV-boundary test: a mesh-open edge OR a UV discontinuity where an edge's two faces assign
        # different UVs to a shared vert, i.e. a seam that splits a manifold surface in UV space).
        # Verified headlessly (blendertk/test/test_selection.py) against the two extremes that expose
        # a wrong boundary test -- a smart-projected cube (6 one-face islands => every edge a seam)
        # and a seamless grid (one island => no internal seams) -- incl. UV Edge Loop truncating a
        # cross-loop at a real re-unwrapped seam (uv=3 < native=6). The 2 below stay genuinely NOT
        # built (no Blender component analogue), not silently dropped:
        "cmb003:Vertex Faces": {"status": "na", "reason": "Maya's vtxFace (PolySelectConvert 5) is its own per-corner sub-component type (like a split-normal/face-corner element, cmds type 70) -- a hybrid vertex-belonging-to-one-face component with no Blender selection-mode analogue (Blender's VERT/EDGE/FACE modes have no fourth 'corner' mode); Blender's nearest concept (custom split normals per-loop) lives in a completely different workflow (Mesh > Normals), not a selectable component."},
        "cmb003:UV's": {"status": "na", "reason": "Maya's UV component (PolySelectConvert 4, cmds .map[]) is a persistent 3D-viewport component type; Blender has no such thing -- UV coordinates are only selectable from within the UV Editor's own uv_select_mode, not the 3D viewport's VERT/EDGE/FACE modes. UV Shell/UV Shell Border/UV Perimeter/UV Edge Loop are the UV-domain items with viewport-reachable bmesh analogues and ARE built (2026-07-13)."},
        # list000 "Select by Type" leaves -- code-built control keys sourced from
        # btk.Selection._SELECTION_CONFIG (blendertk/blendertk/edit_utils/selection.py), the
        # mirror of mayatk's Selection._SELECTION_CONFIG. Ported 2026-07-04: the category
        # breadth now matches mayatk 1:1 (Animation/Dynamics/Geometry/Hierarchy/Scene/UV, same
        # leaf labels); these entries are the leaves that genuinely have no Blender Object-level
        # analogue (sub-object / bone / brush-datablock concepts) and were intentionally NOT
        # built, rather than silently dropped -- see the module's own docstring for the full
        # per-leaf reasoning.
        "list000:Clusters": {"status": "done-elsewhere", "to": "list000 Clusters (Hook-modifier carriers)", "reason": "BUILT 2026-07-11: the Blender Selection config now ships a 'Clusters' leaf in the same Animation category as Maya, selecting meshes that carry a Hook modifier (btk.Selection._select_by_modifier(objs,'HOOK')) -- Blender's control-object-driven per-vertex deformer, the direct analogue of Maya's cluster deformer, delivered via the same modifier-carrier idiom as the nCloths->CLOTH / Fluids->FLUID leaves. (The static sweep does not track list000 leaves, so this entry is documentation of the mapping decision.)"},
        "list000:IK Handles": {"status": "na", "reason": "Maya IK handles are their own DAG transform; Blender IK is a bone-level Constraint living inside an Armature's data, not a separate selectable Object."},
        "list000:Joints": {"status": "na", "reason": "Maya joints are DAG transforms; Blender bones live inside Armature data (pose bones), not as separate selectable Objects -- only the Armature Object itself is selectable."},
        "list000:Brushes": {"status": "na", "reason": "Maya paint-effects brush nodes; Blender sculpt/paint brushes are tool datablocks (bpy.data.brushes), not selectable scene Objects."},
        "list000:Dynamic Constraints": {"status": "na", "reason": "Maya's Nucleus dynamicConstraint (point/slide pin constraints for nCloth/nParticle) has no Blender analogue -- cloth pinning uses vertex groups, not constraint Objects. (Rigid Constraints, the OTHER Maya constraint leaf, DOES have a real analogue -- obj.rigid_body_constraint on an Empty -- and IS built; only the Nucleus dynamic-constraint concept is absent.)"},
        "list000:Sculpts": {"status": "na", "reason": "Maya's implicitSphere/sculpt deformer nodes; Blender Sculpt Mode is a mesh edit mode, not a selectable Object type or deformer node."},
        "list000:Wires": {"status": "done-elsewhere", "to": "list000 Wires (Curve-modifier carriers)", "reason": "BUILT 2026-07-11: the Blender Selection config now ships a 'Wires' leaf in the same Dynamics category as Maya, selecting meshes that carry a Curve modifier (btk.Selection._select_by_modifier(objs,'CURVE')) -- Blender's curve-driven mesh-deform (bpy.types.CurveModifier), the analogue of Maya's wire deformer, via the same modifier-carrier idiom. (list000 leaves are not tracked by the static sweep; documentation of the mapping.)"},
        "list000:Templated Geometry": {"status": "na", "reason": "Maya's legacy 'template' display mode (dashed wireframe, non-selectable/non-renderable) has no Blender display-mode counterpart; Non-Selectable Geometry (hide_select) and Hidden Geometry (hide_get) already cover the adjacent non-selectable/hidden capabilities."},
        # list000:Back-Facing / Front-Facing: BUILT 2026-07-13. The blendertk Selection config's UV
        # category now ships both leaves (edit_utils/selection.py _SELECTION_CONFIG["UV"]) via
        # _select_uv_face_orientation -- a bmesh signed-UV-area (shoelace over face.loops[].uv) pass:
        # negative area = flipped/mirrored winding (Back-Facing), positive = normal (Front-Facing).
        # Object-level granularity (selects objects CONTAINING such a face), matching the sibling UV
        # leaves (Texture Borders / Unmapped). This is the UV-space winding filter, NOT the camera-
        # depth backface pref (that's the separate, already-handled chk004). Verified headlessly
        # (test_selection.py: a CCW-UV quad -> Front-Facing, a CW-UV quad -> Back-Facing). list000
        # leaves are not tracked by the static sweep, so this is documentation of the built mapping.
        "list000:nParticles": {"status": "replaced", "to": "list000 Particles", "reason": "Blender has one unified particle system (no separate classic-vs-Nucleus split like Maya's legacy Particles vs nParticles); EMITTER-type particle systems cover both roles under the single 'Particles' leaf."},
    },
    "transform": {
        "chk021": {"status": "replaced", "to": "apply-model tb004",
                   "reason": "widget exists on both; Maya applies live on toggle, Blender reads at apply"},
        "chk022": {"status": "replaced", "to": "apply-model tb004", "reason": "see chk021"},
        # chk026 (Make Live) removed 2026-07-08: BUILT — the Blender chk026 handler maps
        # makeLive onto face-projection snapping (_set_project_snap -> snap_elements_individual
        # ={FACE_NEAREST}). Handler present on both sides; no delta.
        "s021": {"status": "na", "reason": "snap increments are grid-driven in Blender (slot docstring)"},
        "s022": {"status": "na", "reason": "see s021"},
        "s023": {"status": "na", "reason": "see s021"},
    },
    "scene": {
        "b006": {"status": "renamed", "to": "b_cleanup",
                 "reason": "Cleanup Unknown -> Scene Cleanup (different cleanup semantics)"},
        # Reason labels corrected 2026-07-11 (b013/b014) + 2026-07-12 (b009/b012) — all four had
        # drifted onto the wrong widgets. The live Maya scene slot: b009 = "Fix OCIO" (def b009),
        # b012 = "Toggle Command Ports" (def b012), b013 = "Mesh Converter" (scene.py:43),
        # b014 = "Save to Original Scene" (scene.py:81). Statuses were already right (all
        # genuinely Maya-only / pending); only the human-readable labels were swapped.
        "b009": {"status": "na", "reason": "Fix OCIO — repairs Maya Color Management / OCIO config preferences; Maya-only header entry"},
        "b012": {"status": "na", "reason": "Toggle Command Ports — Maya commandPort concept (MEL :7001 / Python :7002) with no Blender analogue; Maya-only header entry"},
        # b013 Mesh Converter (FBX->GLB): BUILT 2026-07-13 — the Blender scene header now ships it
        # (slots/blender/scene.py header_init + def b013) launching the DCC-agnostic extapps/
        # mesh_convert tool via self.sb.handlers.external_app.launch("mesh_convert"), the SAME
        # handler the Blender materials bridges use, defaulting source_dir to the .blend's folder.
        # Divergence (internal, not a widget the sweep sees): Maya's 'From FBX references' provider
        # is not wired -- Blender links .blend libraries, not FBX, and an imported FBX leaves no live
        # reference to trace, so there is no selected-FBX set to feed; the converter's own file
        # picker chooses inputs instead. Matched by objectName on both sides -> no ledger row needed.
        "b014": {"status": "na", "reason": "Save to Original Scene -- writes an open Maya autosave back over its original scene file (enabled only when an autosave is open and the original is locatable). Blender's recovery model differs (File > Recover Auto Save reopens the .blend; there is no 'save the autosave back to the original' action), so no 1:1 header entry."},
        "b014_init": {"status": "na", "reason": "see b014 (Save to Original Scene enable-state init)"},
        # b016 Unity Bridge: BUILT on both sides 2026-07-14 — the Blender scene header now ships it
        # (slots/blender/scene.py header_init + def b016) via marking_menu.show("unity_bridge"),
        # 1:1 with Maya's scene.py b016. It previously lived in the Blender materials menu (b026);
        # moved here so Marmoset/Substance (materials External) and Unity (Scene) group exactly as
        # Maya does. Matched by objectName + label on both sides -> no ledger row needed.
    },
    # display.py list000 (ExpandableList) — PARITY_SURFACE.md "combo item deltas (review)" for
    # this file. Audited 2026-07-04: Component ID / Mat Override / Soft Edge Display / UV
    # Distortion were genuine gaps (real Blender per-viewport analogues exist — verified live in
    # Blender 5.1) and are now ported (_component_id/_mat_override/_soft_edge_display/
    # _uv_distortion in _LIST000_ITEMS's View/Normals/UV categories) — no longer divergences, so
    # not ledgered below (matches this file's own convention: fixed drift is closed via a comment,
    # not a status entry — see e.g. the hdr_manager/channels_slots blocks above). The prior class
    # docstring's "viewport/editor state has no per-object Blender analogue" rationale for these
    # four was incorrect: Maya's own controls are themselves viewport/editor state (not
    # per-object) too. Remaining entries below are permanent divergences (a different control
    # model, or a verified-live absence of any Blender surface). Keys mirror the sweep's own
    # `_LIST000_ITEMS[Category]` naming, qualified with the item label.
    "display": {
        # list000[Normals] "Display Normals": the visible item-delta is only a label rename (Maya
        # "Display Normal" -> Blender "Display Normals", cosmetic/report-only, no entry needed).
        # Behind the item, Maya's mtk DisplayMacros.m_normals_display cycles Off/Face/Vertex/Tangent.
        # BUILT 2026-07-08: the Blender item now cycles Off -> Face -> Vertex -> Off
        # (View3DOverlay.show_face_normals / show_vertex_normals), matching Maya minus the na Tangent
        # state (no show_tangent RNA in Blender 5.1 -- verified live). Kept as a comment (not
        # fabricated leaf keys) since Maya cycles ONE item, not separate leaves.
        "list000[View].Show Selected": {
            "status": "replaced", "to": "Show All",
            "reason": "Maya's 'reveal only the current selection' has no faithful Blender translation: "
                      "confirmed live (Blender 5.1.2) that obj.hide_set(True)/hide_viewport=True both "
                      "clear obj.select_get(), and a subsequent obj.select_set(True) on a hidden object "
                      "silently no-ops (select_get() stays False) — there is no selection to scope an "
                      "unhide to. Only an unhide-everything model (Show All) is possible.",
        },
        "list000[View].Show Geometry": {
            "status": "replaced", "to": "Show All",
            "reason": "Maya's unconditional 'make all geometry visible' (mtk.set_visibility('mesh', True)) "
                      "folds into the same Show All control — Blender has no separate per-type "
                      "(geometry-only vs everything) visibility action to mirror it as a distinct item.",
        },
        # list000[Wireframe].Template Selected: BUILT 2026-07-08 (was a false 'replaced->Shaded
        # Selected' na). The Blender display slot now ships a real "Template Selected" item under the
        # identical label -- obj.display_type='WIRE' + hide_render=True + hide_select=True (the Maya
        # cmds.toggle(template=1) analogue, matching blendertk.reference_manager's own 'template'
        # mode). Re-click with nothing selected releases every templated object (hide_select DESELECTS
        # in Blender -- verified live -- so a plain toggle-on-selection would be one-way). No
        # divergence to ledger. 'Shaded Selected' is KEPT as a Blender-only extra item -> a
        # report-only "extra" combo delta, documented in DEFAULT_DELTAS['display'].
        "list000[UV].Display UV Border": {
            "status": "na",
            "reason": "Same underlying capability as list000[UV].Borders (Maya routes both through "
                      "cmds.polyOptions displayMapBorder — see mayatk macros.py m_toggle_uv_border_edges "
                      "vs display.py's own _list_uv_borders call — one object-scoped, one global-with-"
                      "width). Verified live (Blender 5.1) that no View3DOverlay/SpaceUVEditor property "
                      "highlights open/UV-map-border edges: show_edge_seams is user-marked UV seams (not "
                      "an auto-detected boundary) and SpaceUVEditor.edge_display_type only restyles ALL UV "
                      "edges (Outline/Dash/Black/White), not border edges specifically. No reasonable "
                      "mapping exists.",
        },
        "list000[UV].Checkered": {
            "status": "na",
            "reason": "Verified live (Blender 5.1) by enumerating the full bpy.types RNA surface for "
                      "'check*' properties: no UV/Image editor checker-background overlay boolean exists "
                      "(only unrelated theme/brush/ImageTexture checker properties). A faithful port would "
                      "mean generating and swapping in a UV_GRID checker image datablock as the editor's "
                      "background image — a builder action, not a property toggle — a different capability "
                      "shape than every other list000 item; out of scope for this port.",
        },
        "list000[UV].Borders": {
            "status": "na",
            "reason": "See list000[UV].Display UV Border — same Maya cmds.polyOptions displayMapBorder "
                      "capability (this item additionally sets sizeBorder width) and the same verified-live "
                      "absence of any Blender border-edge-highlight overlay.",
        },
    },
    "animation": {},
    "edit": {
        "tb001_init": {"status": "na", "reason": "Blender defines tb001 as a documented not-applicable message-box stub (no construction history), so the button is handled (not inert) and its Maya option box (chk019/20/30/31) is intentionally not built — no _init needed."},
        "tb004_init": {"status": "na", "reason": "Blender defines tb004 as a documented not-applicable message-box stub (Maya node locking has no Blender analogue), so the button is handled and the chk027 option box is intentionally not built — no _init needed."},
    },
    "pivot": {
        "tb002_init": {"status": "replaced", "to": "tb002 (option-less always-translate transfer)", "reason": "Maya's Transfer Pivot option box (chk005-009 channel/space/bake toggles) is replaced on Blender by an option-less tb002 that always transfers the single origin (translate) — the button itself IS handled (def tb002 exists), only the option-box builder is deliberately absent; tool's 'visible but inert' applies to the empty option box, not the button."},
        "tb003_init": {"status": "na", "reason": "tb003_init only builds the Manip Pivot option (chk010) for Maya's world-aligned manipulator pivot; Blender tb003 is an explicit not-applicable stub (no separate manip pivot, origin is a point), so no option box should exist — button remains handled by def tb003."},
    },
    "polygons": {},
    "preferences": {},
    "rigging": {},
    "settings": {
    },
    "subdivision": {},
    "uv": {
    },
}

CONTROLS_SLOTS = {
    # ---- migrated 2026-07-02 from the retired dcc_parity_overrides.json (its statuses
    # kept: "divergent" = different Blender paradigm covers it, "done-elsewhere" = built
    # under another objectName/mechanism — both count as triaged-OK, like "na").
    "animation": {
        "Repair Visibility Tangents": {"status": "na", "reason": "Maya-only visibility-curve tangent repair (mtk.Diagnostics.repair_visibility_tangents); Blender keys boolean props CONSTANT natively and the Blender header docstring explicitly documents omitting the tool rather than showing a dead entry."},
        # b000 / b004: removed 2026-07-12 — BUILT. The Shots trio shipped in blendertk 2026-07-11
        # (anim_utils/shots/shot_sequencer + shot_manifest, sweep: 0 element deltas each), so the
        # Blender animation slot's b000/b004 now launch those panels via
        # sb.handlers.marking_menu.show("shot_sequencer"/"shot_manifest") — the exact mirror of
        # slots/maya/animation.py. The old `divergent` rulings ("VSE / linked Scenes cover it")
        # described the pre-port message-box stubs, which are gone.
        "chk001": {"status": "divergent", "reason": "[Update] Blender's Go To Frame is a direct frame_set that always refreshes; Maya's auto-update playback toggle has no frame-nav analogue."},
        "chk007": {"status": "replaced", "to": "tb004 action-copy", "reason": "Blender tb004 transfers by duplicating the whole action, so fcurve handles/tangents always transfer — a tangents on/off toggle is inapplicable to that model."},
        "chk020": {"status": "na", "reason": "Delete Keys 'Channel Box Only' scopes to Maya Channel Box attribute selection; Blender has no Channel Box — channel scoping is covered by Dope Sheet/Graph Editor selection instead."},
        # chk022 (Untie) -> cmb_tie on BOTH DCCs now (Tie/Untie combobox); name-matched, so no ledger entry needed.
        "chk024": {"status": "na", "reason": "Stagger Keys 'Channel Box Attrs Only' scopes to Maya Channel Box attribute selection; Blender has no Channel Box UI."},
        "chk033": {"status": "na", "reason": "Move Keys 'Channel Box Only' scopes to Maya Channel Box attribute selection; Blender has no Channel Box UI."},
        "chk034": {"status": "na", "reason": "Select Keys 'Channel Box Only' scopes to Maya Channel Box attribute selection; Blender has no Channel Box UI."},
        "chk_channel_box": {"status": "na", "reason": "Scale Keys 'Channel Box Attrs Only' scopes to Maya Channel Box attribute selection; Blender has no Channel Box UI."},
        # chk_delete_inputs / chk_mute_drivers / chk_override_layer / chk_preserve_outside: removed
        # 2026-07-11 — these bake-option widgets are NOT built in tentacle's Maya animation slot nor
        # the shared animation .ui; they live on the co-located SmartBake panel (ledgered under
        # CONTROLS['smart_bake_slots'], where the Blender engine ships them as chk_use_override /
        # chk_delete_sources). The entries here named non-existent slot widgets and were never
        # consulted by the sweep (dead config).
        "chk_inherited_vis": {"status": "divergent", "reason": "[Bake Inherited Visibility] Blender visibility isn't inherited through the hierarchy the Maya way; nothing to flatten on bake."},
        "cmb037": {"status": "replaced", "to": "cmb_interp", "reason": "tb017 redesigned on Blender as an interpolation-type picker applied to all keys on the selection; code comment documents cmb_interp replacing cmb037/cmb040 (Maya's key-scope narrowing auto/current-time/selected dropped by design)."},
        "cmb040": {"status": "replaced", "to": "cmb_interp", "reason": "Maya in/out/both tangent selector has no direct Blender analogue (fcurve interpolation is per-segment, not split in/out); code comment documents cmb_interp replacing cmb037/cmb040."},
        "cmb_traversal": {"status": "divergent", "reason": "[Dependency traversal (info)] no comparable per-object animation dependency graph to traverse."},
    },
    "edit": {
        "chk012": {"status": "na", "reason": "Maya polyCleanup 'holed polys' checks faces containing holes; Blender BMesh faces cannot hold holes (no holed-face data model) and blender/edit.py documents Holed as not mirrored (no bmesh primitive)."},
        "chk016": {"status": "na", "reason": "Maya-only data model: Maya stores per-vertex-shareable UVs that cleanup can 'unshare'; Blender UVs are always per-loop so shared-across-vertices UVs cannot exist; blender/edit.py documents Shared-UV as not mirrored."},
        "chk018": {"status": "na", "reason": "Maya lamina faces (faces sharing all edges) are structurally impossible in BMesh (duplicate faces over one vert set are rejected); blender/edit.py documents Lamina as not mirrored; near-coincident doubles are covered by chk025 Overlapping Faces."},
        "chk019": {"status": "na", "reason": "Option of Maya tb001 Delete History (MLdeleteUnused + empty-group purge); Blender tb001 is a documented not-applicable stub (no construction history), so its option box is intentionally not built; a Blender purge-orphans surface would be a separate control if ever wanted."},
        "chk020": {"status": "na", "reason": "'Delete Deformers' toggles deleting full vs non-deformer construction history (cmds.delete ch=True vs bakePartialHistory); construction history does not exist in Blender (modifier stack is non-destructive) per the documented tb001 stub."},
        "chk026": {"status": "na", "reason": "tb000 pre-cleanup option 'Delete History' bakes non-deformer construction history (bakePartialHistory) before polyCleanup; Blender has no construction history so the pre-pass is meaningless, per the documented drop in blender/edit.py."},
        "cmb_lock": {"status": "na", "reason": "Lock/Unlock selector of tb004 Node Locking (cmds.lockNode; was chk027); Blender tb004 is a documented not-applicable stub — Maya node locking (prevent delete/rename of DG nodes) has no Blender analogue."},
        "chk030": {"status": "na", "reason": "Runs MEL 'OptimizeScene' (Maya scene optimizer) as a tb001 Delete History option; host tool is a documented not-applicable stub on Blender; nearest Blender analogue (outliner.orphans_purge) would be a separate surface if ever surfaced."},
        "chk031": {"status": "na", "reason": "'For All Objects' scope toggle for tb001 Delete History; rides on the construction-history capability that the Blender slot documents as not applicable, so no Blender surface should exist."},
    },
    "materials": {
        "b007": {"status": "renamed", "to": "b_shader_editor", "reason": "Hypershade Editor -> 'Shader Editor' header button (btk.open_editor, Blender's Hypershade analogue)"},
        "chk_exclude_defaults": {"status": "na", "reason": "Blender has no auto-created default materials to filter from the report; drop documented in tb001_init"},
        "chk_hide_defaults": {"status": "na", "reason": "Blender has no auto-created default materials (lambert1 etc.) to hide; drop documented in the Blender slot"},
    },
    "nurbs": {
        "chk000": {"status": "na", "reason": "Loft 'Uniform' = NURBS uniform-vs-chord-length parameterization; Blender loft (btk.loft bmesh bridge) outputs a mesh with no parametric direction — explicitly excused in the blender slot's tb001 comment."},
        "chk002": {"status": "na", "reason": "Loft 'Auto Reverse' = cmds.loft autoReverse NURBS curve-direction flag; explicitly excused (blender loft is a mesh bridge, winding handled by chk005 Reverse Surface Normals)."},
        "chk003": {"status": "na", "reason": "Loft 'Range' = force NURBS curve range on complete input curve; parametric-curve concept with no mesh analogue — explicitly excused in the blender slot's tb001 comment."},
        "chk004": {"status": "na", "reason": "Loft 'Polygon' = NURBS-vs-polygon output toggle; Blender loft output is always a mesh so the toggle is meaningless — explicitly excused in the blender slot's tb001 comment."},
        "chk006": {"status": "na", "reason": "Revolve 'Range' = force NURBS curve range; parametric concept absent from the Screw-modifier model — explicitly excused in the blender slot's tb000 comment."},
        "chk007": {"status": "na", "reason": "Revolve 'Polygon' = NURBS-vs-polygon output toggle; Screw modifier output is always a mesh — explicitly excused in the blender slot's tb000 comment."},
        "chk009": {"status": "na", "reason": "Revolve 'Use Tolerance' = cmds.revolve NURBS build-tolerance switch; no tolerance concept on a Screw mesh — explicitly excused in the blender slot's tb000 comment."},
        "chk010": {"status": "na", "reason": "Loft 'Angle Loft Between Two Curves' = mtk.loft angle-loft mode; excused as no-mesh-analogue in the blender module docstring and tb001 comment (btk.loft has no angle-loft path)."},
        "s000": {"status": "na", "reason": "Loft 'Degree' = NURBS surface degree; a bmesh-bridge mesh has no degree — explicitly excused in the blender slot's tb001 comment."},
        "s002": {"status": "na", "reason": "Revolve 'Degree' = NURBS surface degree; the Screw-modifier mesh has no degree — explicitly excused in the blender slot's tb000 comment."},
        "s006": {"status": "na", "reason": "Revolve 'Tolerance' value pairs with chk009's use-tolerance NURBS build flag; excused together in the blender slot's tb000 comment."},
        "s007": {"status": "na", "reason": "Loft 'Angle Loft: Spans' pairs with chk010's angle-loft mode; excused together with angle-loft in the blender slot's documented drops."},
    },
    "pivot": {
        "chk001": {"status": "na", "reason": "Reset Pivot Orientation drives Maya manipPivotReset's orientation channel; Blender's object origin is a point with no manipulator-pivot orientation — Blender tb000_init deliberately ships only chk000 and the module docstring documents the single-baked-origin model."},
        "chk005": {"status": "replaced", "to": "tb002 always-on translate (btk.transfer_pivot)", "reason": "Translate is Blender's only pivot channel, so the toggle is meaningless; the capability runs unconditionally via btk.transfer_pivot(translate=True) in the option-less Blender tb002."},
        "chk006": {"status": "na", "reason": "Rotate-pivot transfer has no Blender analogue — btk.transfer_pivot accepts rotate= only for signature parity and no-ops (Blender has no separate rotate pivot)."},
        "chk007": {"status": "na", "reason": "Scale-pivot transfer has no Blender analogue — btk.transfer_pivot accepts scale= only for signature parity and no-ops (Blender has no separate scale pivot)."},
        "chk008": {"status": "na", "reason": "Bake toggle bakes Maya pivot values into the transform node; Blender origins are always baked into the transform (the b004 Bake stub explicitly messages not-applicable)."},
        "chk009": {"status": "na", "reason": "World Space toggle is meaningless in Blender's transfer model — btk.transfer_pivot documents world_space as implicit (origin read via matrix_world; 3D-cursor snap is world-space by construction)."},
        "chk010": {"status": "na", "reason": "Manip Pivot chooses Maya's temporary manipulator pivot vs permanent object pivot; Blender has no separate manipulator pivot — the Blender tb003 stub explicitly messages World-Aligned Pivot not-applicable."},
    },
    "polygons": {
        "chk008": {"status": "replaced", "to": "tb007 Cuts model (s009:number_cuts)", "reason": "Maya polySubdivideFacet U-split toggle; Blender tb007 uses native mesh.subdivide(number_cuts) which has no U/V direction"},
        "chk009": {"status": "replaced", "to": "tb007 Cuts model (s009:number_cuts)", "reason": "Maya polySubdivideFacet V-split toggle; Blender tb007 uses native mesh.subdivide(number_cuts) which has no U/V direction"},
    },
    "rendering": {
        "chk000": {"status": "na", "reason": "Arnold preview-network attach (mtk.ArnoldBridge / aiStandardSurface) is Arnold/Maya-only; Blender tb001 docstring documents the drop. Added to Maya 2026-06-21 (9cc22169), same commit as the Blender tb001 port."},
        "chk001": {"status": "na", "reason": "IPR launches a Maya Render View interactive session via renderer-registered MEL procs (RenderUtils.start_ipr); Blender's interactive render is the rendered-viewport shading state, not a render-op option — drop documented in Blender tb001 docstring. Added to Maya 2026-06-21 (9cc22169)."},
        "chk002": {"status": "na", "reason": "Smart Redo wraps Maya Render View MEL redoPreviousRender (RenderUtils.redo_previous_render); Blender's render op has no redo-previous concept (Render Result slots are native) — drop documented in Blender tb001 docstring. Added to Maya 2026-06-21 (9cc22169)."},
        "chk056": {"status": "na", "reason": "Maya playblast offScreen capture-mode flag (avoid viewport-redraw issues); bpy.ops.render.opengl always renders to an offscreen buffer and exposes no such parameter, so the toggle has no Blender surface. Maya control predates the port (2025-11-15 f7547ffe; Blender port 2026-06-12 c6b601c9 carried a documented subset)."},
        "chk059": {"status": "na", "reason": "clearCache clears Maya's temporary playblast movie-cache files (cmds.playblast clearCache flag); Blender's OpenGL render writes directly to the output filepath with no playblast cache to clear."},
        "t001": {"status": "replaced", "to": "t000 direct-filepath model", "reason": "Maya's regex only transforms the scene-derived output name used when the base path is a directory; the Blender port takes an explicit base path (t000 defaults to scene.render.filepath) with '#' frame padding via _playblast_path, so filename control needs no scene-name regex stage."},
    },
    "rigging": {
        "chk001": {"status": "na", "reason": "IK radio drives Maya's global ikHandleDisplayScale; Blender has no global IK-handle display-scale — excused in the Blender slot"},
        "chk002": {"status": "na", "reason": "IK\FK radio drives Maya's jointDisplayScale(ikfk=1); no Blender global IKFK display-scale — excused in the Blender slot"},
        "s000": {"status": "na", "reason": "Global joint/IK/IKFK display-scale spinbox (jointDisplayScale/ikHandleDisplayScale); no Blender scene-global display-scale — excused in the Blender slot"},
    },
    "uv": {
        "chk000": {"status": "replaced", "to": "cube/cylinder/sphere_project (bounds-fit)", "reason": "Maya polyProjection -smartFit best-fits the projection manipulator; Blender's cube/cylinder/sphere_project ops fit from the object bounds natively and the slot documents 'no per-mode options, like Maya gates'."},
        "chk016": {"status": "na", "reason": "Instance dedupe is inherent in Blender: linked duplicates share one mesh datablock/UV map and multi-object edit via _uv_op operates on each unique datablock once, so a Skip-Instances pack toggle is moot (Maya side exists only to pre-filter duplicate instance transforms for u3dLayout)."},
        "chk040": {"status": "na", "reason": "Blender Cut Cylinder rides smart_project auto-seaming which places the lengthwise cut itself; the slot explicitly documents 'chk040 (Invert Seam) has no Blender analogue'."},
        # cmb009 (Pre-Scale Mode): removed 2026-07-11 — BUILT. The Blender Pack UVs option box now
        # ships cmb009 with Maya's exact labels ("Pre-Scale: Preserve UV" / "Preserve 3D", default
        # Preserve 3D): Preserve 3D runs a native `bpy.ops.uv.average_islands_scale()` pass (equal
        # texel density) before `pack_islands`; Preserve UV skips it. Matched by objectName + items
        # against the Maya panel (uv.py 12 -> 11 triaged, no combo delta).
        "cmb010": {"status": "replaced", "to": "chk_pack_rotate (pack_islands rotate)", "reason": "Packing-time shell orientation is covered by pack_islands' rotate toggle (chk_pack_rotate); u3dLayout's one-shot axis pre-rotate modes (X/Y/Z to V, 3D-orientation-based) have no counterpart in that model."},
        "cmb012": {"status": "replaced", "to": "smart_project (s_smart_angle/s_smart_margin)", "reason": "Maya's Standard-projection Scale Mode is a polyAutoProjection flag; Blender's Smart UV Project normalizes to the unit square by default (= Maya's Uniform default) and its option box exposes the native operator params (angle limit / island margin) instead."},
        "cmb013": {"status": "na", "reason": "Non-Manifold strategy exists solely to handle Maya u3dUnfold's non-manifold RuntimeError (Warn+Select / Repair+Retry); Blender's uv.unwrap does not reject non-manifold meshes, so there is no failure mode to strategize and tb004 needs no error path."},
        "s011": {"status": "replaced", "to": "chk_pack_rotate (pack_islands rotate)", "reason": "u3dLayout rotation-search step; Blender pack_islands exposes packing rotation as a single rotate toggle (chk_pack_rotate) with no step/range search granularity."},
        "s012": {"status": "replaced", "to": "chk_pack_rotate (pack_islands rotate)", "reason": "u3dLayout rotation-search minimum; covered by pack_islands' boolean rotate model (chk_pack_rotate) which has no min/max range."},
        "s013": {"status": "replaced", "to": "chk_pack_rotate (pack_islands rotate)", "reason": "u3dLayout rotation-search maximum (opt-in gate for the search); covered by pack_islands' boolean rotate model (chk_pack_rotate) which has no min/max range."},
        "s014": {"status": "na", "reason": "u3dLayout -mutations is an Unfold3D-engine optimization-pass count; pack_islands has no iteration parameter, and the module docstring documents u3dLayout packing params as deferred Maya-only depth with no Blender analogue."},
        "uv_editor": {"status": "renamed", "to": "b031", "reason": "Maya's header button is a convenience duplicate that just calls b031; Blender header_init documents 'Open UV Editor is already on b031' (shared uv#submenu.ui button, btk.open_editor) and drops the duplicate."},
    },
    "selection": {
        "chk003": {"status": "replaced", "to": "_ISLAND_DELIMIT model",
                   "reason": "Maya Lock-Values+normal-range island model -> native select_linked delimiters"},
        "s002": {"status": "replaced", "to": "_ISLAND_DELIMIT model", "reason": "see chk003"},
        "s004": {"status": "replaced", "to": "_ISLAND_DELIMIT model", "reason": "see chk003"},
        "s005": {"status": "replaced", "to": "_ISLAND_DELIMIT model", "reason": "see chk003"},
        "chk009": {"status": "na",
                   "reason": "option of cmb001 Reorder Selection, hidden on Blender (no ordered selection)"},
    },
    "scene": {
        "b006": {"status": "renamed", "to": "b_cleanup", "reason": "see HANDLERS['scene']['b006']"},
        "b009": {"status": "na", "reason": "see HANDLERS['scene']"},
        "b012": {"status": "na", "reason": "see HANDLERS['scene']"},
        # b013 Mesh Converter: BUILT 2026-07-13 — see HANDLERS['scene'] b013 note (present on both sides).
        "b014": {"status": "na", "reason": "see HANDLERS['scene'] (Save to Original Scene)"},
        # b016 Unity Bridge: present on both sides now (Scene menu) — see HANDLERS['scene'] b016 note.
        # lbl004/lbl005 ("Open Workspace Root"/"Auto Set Workspace") removed 2026-07-04: stale
        # entries matching no current Maya-only control (already flagged for removal in the
        # archived BLENDER_FEATURE_GAPS.md audit) — and doubly wrong now that main.py's
        # list000 ships exactly an Auto Set Workspace action (btk.find_workspaces-backed
        # up-the-tree detection) plus a Current-Workspace row that opens the workspace root.
    },
    "transform": {
        "chk023": {"status": "done-elsewhere", "to": "chk023 (static)",
                   "reason": "[Snap Rotate] handled by the standalone chk023 slot (static widget in "
                             "transform#submenu.ui, live toggle -> use_snap_rotate); re-building it in "
                             "tb004_init like Maya would duplicate the objectName."},
        # chk026 (Make Live) removed 2026-07-08: BUILT as a tb003 option-box checkbox mapping
        # onto face-projection snapping (FACE_NEAREST); single-live-surface vs all-surfaces is
        # an accepted delta documented in the slot's tb003 comment. No delta.
        "s021": {"status": "na", "reason": "grid-driven increments (see HANDLERS)"},
        "s022": {"status": "na", "reason": "grid-driven increments (see HANDLERS)"},
        "s023": {"status": "na", "reason": "grid-driven increments (see HANDLERS)"},
        "chk038": {"status": "na", "reason": "Freeze rig extras are Maya-rig-specific (slot comment)"},
        "chk040": {"status": "na", "reason": "Freeze rig extras are Maya-rig-specific (slot comment)"},
        "chk_restore_rig_anchors": {"status": "na", "reason": "Maya-rig-specific (slot comment)"},
        "cmb_connection_strategy": {"status": "na", "reason": "Maya-rig-specific (slot comment)"},
    },
}

# Accepted same-named default/property divergences: {"pair": {"control.prop": reason}}.
# Populated 2026-07-03 from the default-flip triage: every same-named-control property delta
# was either FIXED in the Blender slot (matched to Maya — the majority) or accepted here with
# evidence. Accept only when the Blender value is genuinely correct because the underlying
# operator differs in units/range/semantics, the combo holds a deliberately different item
# list, the control is a counterpart (named after its target), or the value is actually set
# post-population (static tool can't see it). Pure drift is fixed, never accepted.
DEFAULT_DELTAS = {
    "blendshape_animator_slots": {
        "group_name.setText": "Maya's default '_morphInbetweens_GRP' names a real transform node; the Blender counterpart is a plain Empty used purely as a parent, so the '_GRP' Maya-suffix convention is dropped -- default is '_morphInbetweens' (Targets.GROUP_NAME).",
    },
    "channels_slots": {
        "cmb_attr_type.items": "Create-Attribute type combo: Maya offers bool/int/float/string/enum/double3; Blender offers bool/int/float/string/vector. 'enum' is dropped (na -- Blender ID custom props have no Maya-style enum type on arbitrary objects). 'double3' is BUILT 2026-07-08 as 'vector' (Blender's native term): create_attribute makes a 3-float XYZ array custom prop (obj[name]=(d,d,d) + id_properties_ui subtype='XYZ'), parse_value round-trips the '(x, y, z)' cell on edit, and the table already displayed/keyed vectors (_value_type='vector'). The 'double3'->'vector' label difference is the combo item rename.",
    },
    "materials": {
        "chk_include_optimization.setChecked": "Environment-driven default (documented in-file: builder comment + tooltip + docstring). Same ptk.MapOptimizer toggle, but Blender's bundled Python lacks Pillow, so the map-analysis report degrades to per-texture 'unavailable'; opt-in avoids a noise-filled default report. Maya's tooltip assumes PIL present.",
    },
    "normals": {
        "cmb000.setCurrentIndex": "Deliberately different item list: Blender cmb000 = native ops (Flip / Recalculate Outside / Recalculate Inside via btk.flip_normals/recalculate_normals); Maya = polyNormal normalMode enum (Reverse/Propagate/Conform/…). Maya's index 3 ('Reverse and Extract') has no Blender counterpart, so copying it would default to a semantically unrelated op; default 0 ('Flip') is the correct reverse counterpart.",
    },
    "display": {
        "list000[Wireframe].items": "Blender's Wireframe category carries a 'Shaded Selected' item (display_type='TEXTURED', the inverse of Wireframe Selected) that Maya lacks -- a Blender-only ENHANCEMENT kept when 'Template Selected' was built 2026-07-08, so the sweep shows it as a report-only extra. Every Maya item now has its twin.",
    },
    "edit": {
        "cmb000.items": "Deliberately different item list (Transfer menu): Blender's Data-Transfer operator works one data-layer at a time, so Maya's single 'Attribute Values' dialog (UVs/vertex colors/weights/normals together) is broken out into its natural granular items (UVs / Vertex Colors / Vertex Group Weights / Custom Normals); 'Shading Sets' is renamed to Blender's own term 'Material Slots'. Maya's 'Maps' (Cycles-scale bake setup) and 'Vertex Order' (interactive click-to-match reindex, no bpy primitive) are intentionally dropped rather than added as inert entries — see the _TRANSFER_OPS comment in blender/edit.py.",
    },
    "subdivision": {
        "cmb000.items": "Decimate 'Reduce' item names its output metric by each host's native algorithm: Maya = Quadric Error % ('Reduce (Quadric Error %)', data 'qem', cmds.polyReduce QEM), Blender = Collapse % ('Reduce (Collapse %)', data 'collapse', Decimate modifier collapse mode). Same Reduce slot/operation; only the metric name in the item text (and its data token) differs to match each DCC's native reduction.",
    },
    "nurbs": {
        "s003.setValue": "Blender's Screw modifier takes ONE sweep angle computed as end-start (tb000: math.radians(s004-s003)); start=0 is the neutral origin. Matching Maya's 3 alongside its 3 end sweep would give a 0-degree (degenerate) revolve. Maya's 3/3 is itself drift from cmds.revolve defaults (ssw=0, esw=360).",
        "s004.setValue": "Screw has no independent end angle, only total sweep (end-start). 360 with start=0 = full revolution, matching cmds.revolve's documented esw default and Screw's native 360; matching Maya's 3 would make sweep 3-3=0 degrees (no geometry).",
        "s005.set_limits": "Value assigned directly to ScrewModifier.steps, whose RNA range is [2, 10000]; Maya's [0] minimum would allow 0/1 steps that Blender's property rejects/clamps. [1, 256] reflects Blender's supported revolution-step range.",
    },
    "polygons": {
        "s001.setValue": "Blender s001 drives mesh.inset(thickness) in scene METERS; Maya's polyExtrudeFacet(offset) is cm-scale. 0.1 m is the meter-scale equivalent of a sensible default; Maya's 2.0 would be an absurd inset in Blender units.",
        "s001.set_limits": "Same [0,100] range but Blender adds step=0.01/decimals=3 needed to edit a meter-scale inset thickness; Maya's coarse step is unusable at that scale.",
        "s002.setValue": "0.0001 is mesh.remove_doubles' native threshold default (meters) and the b005 reset path resets to exactly that; Maya's 0.0005 is polyMergeVertex tolerance in cm — different units, and forcing it would desync b005's documented reset.",
        "s002.set_limits": "Range/precision tuned to remove_doubles' meter-unit threshold (max 10, 4 decimals); Maya's [0,1000,…,5] is cm-scale merge tolerance — different operator units, not drift.",
        "s004.setValue": "Different operator parameter: Maya s004 = int Divisions for polyExtrudeFacet(divisions); Blender s004 = signed distance for transform.shrink_fatten(value), whose no-op default is 0.0 (handler skips shrink_fatten when 0).",
        "s004.set_limits": "Blender s004 is a signed float offset for shrink_fatten, so [-100,100,0.01,3] (negative = inward) is required; Maya's [0] is a min-only bound for an integer division count — different semantics.",
        "s004.setPrefix": "'Offset: ' correctly labels the Blender control (shrink_fatten normal offset after extrude — Blender extrude has no divisions param); 'Divisions: ' would be false.",
    },
    "rendering": {
        "cmb016.setCurrentIndex": "Not a real delta: items are populated after add() via cmb016.addItem(label, data) (per-item quality data), then cmb016.setCurrentIndex(5) is called immediately — matching Maya's index 5. A setCurrentIndex kwarg inside add() would run on an empty combo (no-op); the static tool can't see the post-population call.",
        "cmb040.setCurrentIndex": "Not a real delta: resolution items populated post-add via addItem(label, data), then cmb040.setCurrentIndex(2) (1920x1080) — matching Maya's index 2. Static tool can't see the post-population call.",
        "cmb041.setCurrentIndex": "Not a real delta: camera items populated post-add via addItem(name, cam), then cmb041.setCurrentIndex(0) (Active Viewport) at rendering.py:124 — matching Maya's index 0. Static tool can't see the post-population call.",
        "cmb050.setCurrentIndex": "Deliberately different item list: Blender _FORMATS = 9 ffmpeg/native presets (MP4/MOV/AVI, PNG/JPEG/TIFF/TARGA/EXR via configure_render_output) vs Maya's 15 Maya-codec presets (qt/avi/iff/Arnold); indices are not interchangeable and Qt defaults the populated combo to index 0.",
    },
    "rigging": {
        "chk000.setChecked": "Not a same-meaning toggle: Maya chk000 is a QRadioButton 'Joints' (checked as the default of a 3-way Joints/IK/IK-FK group driving display scales); Blender chk000 is a standalone QCheckBox opting into armature bone-axes (show_axes) — a mode Maya lacks. Defaulting True would make tb000 error ('No armatures selected') on non-armature selections. Documented in the Blender file's name-reuse comment.",
        "cmb010.items": "Deliberately different item list: Maya's Attrs scope ['Attrs: Auto','Attrs: Channel Box'] names Channel-Box-driven attribute scoping; Blender has no Channel Box, so the scope is re-expressed as the concrete transform channels ['Attrs: Translate','Attrs: Rotate','Attrs: Scale']. Documented only in the Blender slot comment previously; recorded here 2026-07-08.",
        "cmb002.items": "Blender adds Rigify presets ['Human Meta-Rig','Basic Human Meta-Rig','Generate Rig'] on top of Maya's 4 items -- Blender-only ENHANCEMENT (Rigify is Blender's native meta-rig system, no Maya counterpart), not a drop.",
    },
    "animation": {
        "cmb038.items": "Blender drops Maya's 'Mode: Channel Box' copy-scope item -- Blender has no Channel Box UI; channel scoping is covered by Dope Sheet/Graph Editor selection instead (same rationale as the chk020/024/033/034/chk_channel_box na family). Resolves the 'see parity_map.py cmb038' reference in slots/blender/animation.py.",
    },
    # uv.cmb002 (the 17->3 Transform submenu) was relocated 2026-07-08 into the dedicated UV
    # Transform tool (co-located mayatk/blendertk uv_utils/shell_xform.py). The Maya-only ops
    # (Align/Orient/Gather/Randomize/select filters) are now ledgered under CONTROLS["shell_xform"]
    # as `na`; Flip/Rotate (+ the move pad and Straighten/Mirror/Distribute) ship in the Blender
    # twin. No cmb002 remains in the uv slot, so the former cmb002.items pending note is retired
    # (no "uv" entry needed here while the panel has no other triaged deltas).
    "scene": {
        "b010.setText": "Counterpart control: the cross-DCC bridge button is named after its TARGET app — Maya's says 'Blender Bridge' (sends to Blender), Blender's says 'Maya Bridge' (sends to Maya). Same cross-DCC send-pair rule as BlenderBridgeSlots <-> MayaBridgeSlots.",
    },
    "lightmap_baker": {
        "spn_samples.maximum": "Different renderer sample ceilings: Maya spn_samples = Arnold AA samples (max 256, sensible for Arnold); Blender spn_samples = Cycles bake samples (max 4096 — Cycles routinely uses far higher sample counts than Arnold AA). Same 'render sample count' concept, renderer-appropriate range.",
    },
}

# --------------------------------------------------------------------------- Maya-only panels
# mayatk *Slots classes with no blendertk twin: how to treat the gap.
PANELS = {
    "ArnoldBridgeSlots": {"status": "na", "reason": "no Arnold in Blender (Cycles/EEVEE)"},
    # MarmosetBridgeSlots / SubstanceBridgeSlots: stale "no twin" rows removed 2026-07-08 -- both
    # now ship real native blendertk twins (blendertk/mat_utils/{marmoset,substance}_bridge/
    # *_bridge_slots.py -- full BlenderBridgeSlotsBase panels with co-located .ui + RPC clients +
    # FBX export + Painter/Toolbag handoff), discovered by BlenderUiHandler and launched from
    # materials.py b019/b020 via marking_menu.show(), exactly like Maya. Same condition that retired
    # the five below on 2026-07-03/04; these two were missed. Track any residual gaps via panel rows.
    "BlenderBridgeSlots": {"status": "counterpart", "to": "MayaBridgeSlots",
                           "reason": "cross-DCC send pair — each package ships the bridge named "
                                     "after its TARGET app"},
    # HierarchyManagerSlots / SceneExporterSlots / UnityBridgeSlots / AudioClipsSlots /
    # SmartBakeSlots: removed 2026-07-03/04 -- all five now have real blendertk twins
    # (mechanically diffed above under their own panel rows, measured OK/GAP, not "no twin").
    # AudioClipsSlots verified via
    # `compare_panel_surface.py --panel audio_clips` (0 untriaged / 0 pending / 0 triaged-OK /
    # 0 stale-maya / 3 prop deltas [setText wording only] / 0 item deltas) after ledgering the
    # 12 controls under the new "audio_clips_slots" CONTROLS row above -- all Maya-only
    # composite-WAV/DG-node/two-phase-keying machinery with no VSE counterpart (see that row's
    # header comment). UnityBridgeSlots verified clean via
    # `compare_panel_surface.py --panel unity_bridge` (0 untriaged / 0 pending / 0 triaged-OK /
    # 0 stale-maya / 0 prop deltas / 0 item deltas): a native co-located blendertk panel (engine +
    # Slots + .ui under env_utils/unity_bridge, engine registered in blendertk/__init__.py,
    # materials.py b026 -> marking_menu.show("unity_bridge")) -- Unity's own asset pipeline ingests
    # anything dropped into Assets/ on focus, so (like Maya's) this needs no live-RPC / fresh-
    # instance-launch dance, unlike the Marmoset/Substance external-app-relay bridges. Track any
    # remaining gaps via the CONTROLS/panel-table entries instead of this "unbuilt" ledger.
    # SmartBakeSlots verified clean via `compare_panel_surface.py --panel smart_bake` (0
    # untriaged / 0 pending / 5 triaged-OK / 0 stale-maya / 2 prop deltas [b000/b001 .ui
    # widget `class` PushButton-vs-QPushButton — pre-existing uitk-promotion review delta, not
    # blocking] / 0 item deltas) after ledgering the 5 real controls under the new
    # "smart_bake_slots" CONTROLS row above -- chk_bake_blendshapes/chk_delete_inputs renamed,
    # chk_override_layer replaced by chk_use_override (Blender's nla.bake always writes a
    # brand-new Action, so there's no override-vs-base-layer axis left to name), and
    # chk_mute_drivers/chk_inherited_vis na (both fully covered by chk_use_override and by
    # AnimUtils.set_visibility_keys respectively — see that row's header comment and
    # _smart_bake.py's own module docstring).
    # BlendshapeAnimatorSlots: removed 2026-07-03 -- now a real blendertk twin (engine + Slots +
    # .ui under anim_utils/blendshape_animator, engine registered in blendertk/__init__.py).
    # scene.py's b015 -> marking_menu.show("blendshape_animator") is a NEW, Blender-only
    # marking-menu entry point, not a mirror of an existing mayatk tentacle button: mayatk's own
    # BlendshapeAnimatorSlots has no tentacle-Maya wiring at all (grep
    # tentacle/tentacle/slots/maya/*.py for "blendshape" -> zero hits; the panel is only reachable
    # via MayaUiHandler.instance().show("blendshape_animator")). The panel/engine correspondence
    # itself IS 1:1 (Maya's blendShape multi-target in-betweens are rebuilt as driver-driven
    # additive corrective shape keys -- see applicator.py's module docstring for the
    # interpolation-equivalence proof); only the tentacle-launcher wiring is Blender-only, added
    # here because a marking-menu entry point is broadly useful even without a Maya-side
    # precedent to mirror. Verified clean via `compare_panel_surface.py --panel
    # blendshape_animator` (0 untriaged / 0 pending / 1 triaged-OK / 0 stale-maya / 0 prop deltas
    # / 0 item deltas) -- the one triaged control (btn_recover_setup, "Recover Setup") is `na`:
    # no Blender analogue to a corrupted blendShape NODE. Track remaining gaps via the CONTROLS
    # table instead of this "unbuilt" ledger.
    # SHOTS TRIO — SHIPPED 2026-07-11 (user directive: full 1:1 workflow parity so a Maya user moves to
    # Blender with the SAME tentacle tools). All three panels ported 1:1 (sweep: 0 element deltas each)
    # and co-located in blendertk/anim_utils/shots/ (engine + <tool>.ui + <Tool>Slots, discovered by
    # BlenderUiHandler; tentacle carries only the nav launch button). The DCC-agnostic core — shot model,
    # planner, detection math, and the whole manifest (CSV/mapping/behaviors[JSON]/range) — extracted to
    # pythontk.core_utils.engines.shots so mayatk + blendertk share ONE implementation. The divergence is
    # in the ENGINE, not the UX: Blender realises shots on native primitives (fcurve key-motion,
    # RenderOpacity fades, VSE audio). Ledgered follow-ups (not sweep gaps): sequencer AUDIO-track display
    # + move-to-shot sequence grouping are deferred; the object-animation timeline is fully wired. The
    # slot-class entries are dropped by the sweep now that the classes exist — no ledger rows needed.
    "WorkspaceMapSlots": {"status": "na",
                          "reason": "Maya-workspace management tool; no Blender project concept — "
                                    "reframe as a .blend/asset browser only if wanted (plan ruling)"},
}

# --------------------------------------------------------------------------- file counterpart sets
# Whole-file groups where the Blender counterpart is a different-shaped equivalent, not a
# same-name mirror. Native-menu stubs are ALSO derived mechanically from
# mayatk MayaNativeMenus.MENU_MAPPING — entries here add the explanation + any extras.
FILE_COUNTERPARTS = {
    "maya_native_menus": {
        "detect": "MENU_MAPPING",  # auto: maya-only slot stems that are MENU_MAPPING keys
        "blender_counterpart": "blender.py (blender#startmenu -> btk.call_native_menu)",
        "reason": "Maya-native-menu Qt clones (QAction harvest — impossible in Blender's "
                  "OpenGL UI); Blender pops its OWN native menus at the cursor instead "
                  "(shipped 2026-06-12)",
    },
}
