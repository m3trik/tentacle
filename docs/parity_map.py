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
    # The Transfer tool left tentacle's uv b000 option box for the Texture Combine panels'
    # Transfer mode (2026-10-17); its vocabulary deltas moved with it.
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
