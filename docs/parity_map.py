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
        "b018": {"status": "pending", "reason": "Fix Mangled Names (2026-08-04) — mtk.Diagnostics.repair_mangled_names: strips __uninst_tmp/__RZTMP/FBXASC###/underscore-run name damage, then conforms shapes. FBXASC escapes and __uninst tokens are Maya-side artifacts, but Blender's Rizom bridge round-trips the SAME __RZTMP suffixes, so a Blender twin (scoped to __RZTMP + underscore runs) is real open work rather than na."},
        # b016 Unity Bridge: BUILT on both sides 2026-07-14 — the Blender scene header now ships it
        # (slots/blender/scene.py header_init + def b016) via marking_menu.show("unity_bridge"),
        # 1:1 with Maya's scene.py b016. It previously lived in the Blender materials menu (b026);
        # moved here so Marmoset/Substance (materials External) and Unity (Scene) group exactly as
        # Maya does. Matched by objectName + label on both sides -> no ledger row needed.
        # list001 "Import Maya Scene": Blender-side ADDITION 2026-07-16 (no Maya twin to triage —
        # Maya opens its own .ma/.mb natively via its list001 "Import File"). The item calls
        # btk.import_maya_scene (env_utils/maya_bridge/_scene_import.py): a headless
        # mayapy converts the scene to FBX (pythontk.run_script_to_artifact) and the FBX is
        # imported + cleaned up. Item-delta is report-only (Blender addition, no Maya-side key).
        # list001 "Import Blender Scene": Maya-side ADDITION 2026-07-16 (later) — the SYMMETRIC
        # pull import: mtk.import_blender_scene (env_utils/blender_bridge/_scene_import.py), a
        # headless `blender --background --factory-startup` FBX round-trip whose manifest sidecar
        # is rebuilt through the GameShader engine (packed Metallic_Smoothness/MSAO/ORM maps
        # included; verified live in scene_import_live_e2e.py). The two items intentionally differ
        # by label — each names the OTHER DCC — so neither side's item-delta pairs; both stay
        # report-only additions.
        # 2026-07-16: the Import/Export combos (cmb003/cmb004, scene.ui) became the submenu's
        # Import/Export ExpandableLists (list001/list002, scene#submenu.ui) on BOTH sides — same
        # items, same dispatch tables; the submenu's b007 Import button and tb003 Export PushButton
        # folded into them (tb003 is now list002's first entry, created dynamically with its
        # option box). 2026-08-01: the header's plain "Export Scene" launcher (b018) was dropped
        # on BOTH sides — redundant with that list entry, which carries the option box.
    },
    # display.py list000 (ExpandableList) — PARITY_SURFACE.md "combo item deltas (review)" for
    # this file. Audited 2026-07-04: Component ID / Mat Override / Soft Edge Display / UV
    # Distortion were genuine gaps (real Blender per-viewport analogues exist — verified live in
    # Blender 5.1) and are now ported (_component_id/_mat_override/_soft_edge_display/
    # _uv_distortion in _LIST000_ITEMS's View/Normals/UV categories) — no longer divergences, so
    # not ledgered below (matches this file's own convention: fixed drift is closed via a comment,
    # not a status entry). The prior class
    # docstring's "viewport/editor state has no per-object Blender analogue" rationale for these
    # four was incorrect: Maya's own controls are themselves viewport/editor state (not
    # per-object) too. Remaining entries below are permanent divergences (a different control
    # model, or a verified-live absence of any Blender surface). Keys mirror the sweep's own
    # `_LIST000_ITEMS[Category]` naming, qualified with the item label.
    "animation": {},
    # b000 is the Texture Combine launcher in both forks (2026-10-17: blendertk's twin panel
    # took the Transfer tool UvMixin's option box was).
    "uv": {},
}

CONTROLS_SLOTS = {
    # ---- migrated 2026-07-02 from the retired dcc_parity_overrides.json (its statuses
    # kept: "divergent" = different Blender paradigm covers it, "done-elsewhere" = built
    # under another objectName/mechanism — both count as triaged-OK, like "na").
    "animation": {
        "Repair Visibility Tangents": {"status": "na", "reason": "Maya-only visibility-curve tangent repair (mtk.Diagnostics.repair_visibility_tangents); Blender keys boolean props CONSTANT natively and the Blender header docstring explicitly documents omitting the tool rather than showing a dead entry."},
        # b000 / b004: removed 2026-07-12 — BUILT. The Shots trio is tentacle's shared tools
        # (slots/tools/shot_sequencer + shot_manifest, one panel for both hosts since 2026-10-28),
        # so both forks' b000/b004 launch them via
        # sb.handlers.marking_menu.show("shot_sequencer"/"shot_manifest"). The old `divergent`
        # rulings ("VSE / linked Scenes cover it") described the pre-port message-box stubs.
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
        "cmb037": {"status": "replaced", "to": "cmb_interp", "reason": "tb017 redesigned on Blender as an interpolation-type picker applied to all keys on the selection; code comment documents cmb_interp replacing cmb037/cmb040 (Maya's key-scope narrowing auto/current-time/selected dropped by design)."},
        "cmb040": {"status": "replaced", "to": "cmb_interp", "reason": "Maya in/out/both tangent selector has no direct Blender analogue (fcurve interpolation is per-segment, not split in/out); code comment documents cmb_interp replacing cmb037/cmb040."},
        "cmb_traversal": {"status": "divergent", "reason": "[Dependency traversal (info)] no comparable per-object animation dependency graph to traverse."},
    },
    "uv": {
        "chk016": {"status": "na", "reason": "Instance dedupe is inherent in Blender: linked duplicates share one mesh datablock/UV map and multi-object edit via _uv_op operates on each unique datablock once, so a Skip-Instances pack toggle is moot (Maya side exists only to pre-filter duplicate instance transforms for u3dLayout)."},
        "chk040": {"status": "na", "reason": "Blender Cut Cylinder rides smart_project auto-seaming which places the lengthwise cut itself; the slot explicitly documents 'chk040 (Invert Seam) has no Blender analogue'."},
        "chk045": {"status": "na", "reason": "Hide Seam From View: Maya's band-based seamer (mtk.UvUtils.get_auto_seam_edges) lands the lengthwise seam on the side facing away from the active viewport camera; Blender Cut Cylinder rides smart_project which places seams itself (same rationale as chk040). A blendertk twin of the band seamer would carry both -- see .claude/BACKLOG.md."},
        "chk046": {"status": "na", "reason": "Keep Existing Seams (unwrap_cylinder sew=False): the Maya band seamer sews stale UV borders shut before cutting; Blender's smart_project re-seams from scratch and has no equivalent pre-sew, so there is no toggle to mirror. Rides the same blendertk twin as chk040 / chk045."},
        "s021": {"status": "na", "reason": "Taper Angle (band seamer taper tolerance): a parameter of mtk.UvUtils.get_auto_seam_edges' profile reading, which Blender's smart_project auto-seaming does not have. Rides the blendertk twin (see .claude/BACKLOG.md)."},
        "s022": {"status": "na", "reason": "Flat Angle (band seamer rings-vs-sectors threshold): same rationale as s021."},
        "s023": {"status": "na", "reason": "Fillet Size (band seamer trim ratio, % of radius): same rationale as s021."},
        # cmb011 (Auto Unwrap mode) 2026-07-28: trimmed on BOTH DCCs to three
        # byte-identical items -- "Standard" (each DCC's own auto projection:
        # polyAutoProjection / smart_project), "Hard Surface (Ministry of Flat)"
        # and "Organic (BFF)". The two engine modes call UvUtils.auto_unwrap,
        # mirrored in mayatk and blendertk. No delta.
        # chk000 (Smart Fit), cmb017 (Cut Algorithm) and the seam / planar /
        # cylindrical / spherical / normal modes: REMOVED from the Maya panel
        # 2026-07-28 with that trim, so their na rows are retired.
        # cmb016 (Cut Cylinder Algorithm): REMOVED 2026-07-28 -- one band-based
        # seamer (mtk.UvUtils.get_auto_seam_edges, 2026-08-15) reads straight,
        # turned and bent tubes alike, so there is nothing to select on either
        # DCC.
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
        "cmb018": {"status": "na", "reason": "Post-pack scale-to-fit is u3dLayout -layoutScaleMode (Fill uniform / Off keep-density / Stretch non-uniform). Blender's pack_islands has no post-pack fit mode: it always fits the islands into the target region, so only the Fill behavior exists and there is nothing to select. Keep-density is instead reached on the Blender side by leaving Pre-Scale on Preserve UV (skipping average_islands_scale) -- same u3dLayout-params-are-Maya-only rationale as s011/s012/s013/s014."},
        "cmb019": {"status": "pending", "reason": "Pack Method combo (Standard / xatlas). The xatlas engine itself is portable -- ptk.UvPack is array-in/array-out with no DCC imports, and the package pip-installs into Blender's Python the same way -- so the Blender Pack option box can gain the same method combo dispatching to a blendertk pack_uvs twin (uv arrays via bmesh/foreach_get, per-island transform write-back; honor mirrored charts like mayatk's _uv_pack does). Until built, Blender packs via its native pack_islands only."},
        "chk043": {"status": "pending", "reason": "Brute Force (xatlas-only quality toggle) -- rides the cmb019 port; maps 1:1 onto ptk.UvPack.pack_islands(brute_force=)."},
        "chk044": {"status": "pending", "reason": "Rotate Shells (xatlas) -- rides the cmb019 port; maps 1:1 onto ptk.UvPack.pack_islands(rotate=). Distinct from chk_pack_rotate, which drives the native pack_islands rotate."},
        "s019": {"status": "na", "reason": "u3dLayout -tileU multi-tile distribution (pack across an N-wide grid of UDIM tiles anchored at the target UDIM). bpy.ops.uv.pack_islands packs into a single region with no tile-grid parameter, so there is no native counterpart to drive -- same u3dLayout-params-are-Maya-only rationale as s011/s012/s013/s014."},
        "s020": {"status": "na", "reason": "u3dLayout -tileV multi-tile distribution (the vertical half of the s019 tile grid); same absent pack_islands capability."},
        "s014": {"status": "na", "reason": "u3dLayout -mutations is an Unfold3D-engine optimization-pass count; pack_islands has no iteration parameter, and the module docstring documents u3dLayout packing params as deferred Maya-only depth with no Blender analogue."},
        "uv_editor": {"status": "renamed", "to": "b031", "reason": "Maya's header button is a convenience duplicate that just calls b031; Blender header_init documents 'Open UV Editor is already on b031' (shared uv#submenu.ui button, btk.open_editor) and drops the duplicate."},
        # cmb014 (Transfer UVs Scope) BUILT 2026-07-28 with the b000 option box (see
        # HANDLERS['uv']). No delta.
        # d000 (similarity threshold) BUILT 2026-07-28 with the b000 option box (see
        # HANDLERS['uv']). No delta.
        # cmb015 (Pack UVs Tile Coverage) BUILT 2026-07-28: post-pack whole-map scale about the
        # target tile's bottom-left corner via the new btk.scale_uvs primitive (pack_islands has
        # no packBox analogue), after tb000's existing tile-delta move. Same items/default as
        # Maya. No delta.
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
}

# Accepted same-named default/property divergences: {"pair": {"control.prop": reason}}.
# Populated 2026-07-03 from the default-flip triage: every same-named-control property delta
# was either FIXED in the Blender slot (matched to Maya — the majority) or accepted here with
# evidence. Accept only when the Blender value is genuinely correct because the underlying
# operator differs in units/range/semantics, the combo holds a deliberately different item
# list, the control is a counterpart (named after its target), or the value is actually set
# post-population (static tool can't see it). Pure drift is fixed, never accepted.
DEFAULT_DELTAS = {
    "normals": {
        "cmb000.setCurrentIndex": "Deliberately different item list: Blender cmb000 = native ops (Flip / Recalculate Outside / Recalculate Inside via btk.flip_normals/recalculate_normals); Maya = polyNormal normalMode enum (Reverse/Propagate/Conform/…). Maya's index 3 ('Reverse and Extract') has no Blender counterpart, so copying it would default to a semantically unrelated op; default 0 ('Flip') is the correct reverse counterpart.",
    },
    "animation": {
        "cmb038.items": "Blender drops Maya's 'Mode: Channel Box' copy-scope item -- Blender has no Channel Box UI; channel scoping is covered by Dope Sheet/Graph Editor selection instead (same rationale as the chk020/024/033/034/chk_channel_box na family). Resolves the 'see parity_map.py cmb038' reference in slots/blender/animation.py.",
    },
    # uv.cmb002 (the 17->3 Transform submenu) was relocated 2026-07-08 into the UV Transform
    # tool, now tentacle's shared Shell Xform panel (one surface, no deltas). No cmb002 remains
    # in the uv slot, so no "uv" entry is needed here.
    # The Transfer tool left tentacle's uv b000 option box for the Texture Combine panels'
    # Transfer mode (2026-10-17); its vocabulary deltas moved with it.
    "scene": {
        "b010.setText": "Counterpart control: the cross-DCC bridge button is named after its TARGET app — Maya's says 'Blender Bridge' (sends to Blender), Blender's says 'Maya Bridge' (sends to Maya). Same cross-DCC send-pair rule as BlenderBridgeSlots <-> MayaBridgeSlots.",
    },
}

# --------------------------------------------------------------------------- Maya-only panels
# mayatk *Slots classes with no blendertk twin: how to treat the gap.
PANELS = {
    # SHOTS TRIO — SHIPPED 2026-07-11 (user directive: full 1:1 workflow parity so a Maya user moves to
    # Blender with the SAME tentacle tools). All three panels ported 1:1; Shot Manifest and Shots are
    # tentacle's shared tools now (2026-10-28), the Sequencer still co-located in
    # blendertk/anim_utils/shots/ until it moves. The DCC-agnostic core — shot model,
    # planner, detection math, and the whole manifest (CSV/mapping/behaviors[JSON]/range) — extracted to
    # pythontk.core_utils.engines.shots so mayatk + blendertk share ONE implementation. The divergence is
    # in the ENGINE, not the UX: Blender realises shots on native primitives (fcurve key-motion,
    # RenderOpacity fades, VSE audio). 2026-08-22 BEHAVIOR-PARITY PASS closed every deferred item:
    # sequencer audio tracks (AudioSegment over VSE strips), Move-to-Shot sequence grouping, motion/hold
    # segmentation (btk.SegmentKeys), Show Internal Holds, gap-hold stepping (CONSTANT), extend/fit,
    # detect-next, transport/play controller, ShotEditDialog + combo context menu, native undo/redo,
    # Graph-Editor key-selection sync; manifest behaviors/ + range_resolver facades; store save_pre
    # flush / fps-change rescale / Detection class. The only Maya-only names left are Maya MECHANISMS
    # (tangent snapshot/restore, DAG-path reconciliation, DG audio node binding, OpenMaya callbacks).
    # The slot-class entries are dropped by the sweep now that the classes exist — no ledger rows needed.
}

# --------------------------------------------------------------------------- file counterpart sets
# Whole-file groups where the Blender counterpart is a different-shaped equivalent, not a
# same-name mirror. Native-menu stubs are ALSO derived mechanically from
# mayatk MayaNativeMenus.MENU_MAPPING — entries here add the explanation + any extras.
FILE_COUNTERPARTS = {
    "maya_native_menus": {
        "detect": "MENU_MAPPING",  # auto: maya-only slot stems that are MENU_MAPPING keys
        "blender_counterpart": "blender.py (blender#startmenu -> BlenderNativeMenus.get_menu)",
        "reason": "Maya-native-menu Qt clones (QAction harvest); Blender menus are Python "
                  "classes, so blendertk harvests each menu's draw() into an equivalent QMenu "
                  "(menu_harvest) hosted in the same wrapped MainWindow — full pin-header / "
                  "hide-on-key_show parity (shipped 2026-07-16; superseded the wm.call_menu "
                  "popup wrap from 2026-06-12)",
    },
}
