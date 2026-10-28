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
    "nurbs": {
        "b016": {"status": "na", "reason": "[Create Curve from Edges] widget removed from nurbs.ui 2026-05-20 (9f534ba3) but the handler is pinned by test_nurbs.py (create_curve_from_edges fallback) - retarget the test at mtk directly, then delete the handler"},
        # list000 "Nurbs actions" leaves -- code-built control keys sourced from
        # NurbsSlots._LIST000_COMMANDS (tentacle/tentacle/slots/blender/nurbs.py), the Blender-idiom
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
        # list000 Bend / Curl / Curvature / Straighten / Rebuild / Extend BUILT 2026-07-28 —
        # the rolled btk.NurbsUtils CV-deformation family (pure control-point math on
        # POLY/NURBS splines; arc-length-exact bend maps the chord onto a true circle,
        # refuting-for-good the SIMPLE_DEFORM route's fixed-axis no-op trap probed
        # 2026-07-11). Verified headless: test_nurbs_utils.py 16/16. Bezier splines are
        # skipped by design (handle model needs its own authoring pass; slot reports it).
        # No delta.
        "list000:Insert Isoparm": {"status": "na", "reason": "Isoparms are a parametric NURBS-surface-only concept; Blender's Screw/loft-bridge surfaces are meshes with no isoparm to insert."},
        "list000:Insert Knot": {"status": "na", "reason": "Knot insertion is parametric NURBS-curve re-parameterization; a Blender POLY/NURBS spline's control points have no knot vector exposed to Python to insert into."},
        "list000:Extend (Options)": {"status": "na", "reason": "Tolerance-based parametric curve extension (extend by a distance/tolerance along the curve's own parameterization) with its dedicated option box; the rolled btk.NurbsUtils.extend_curve covers the plain linear Extend leaf, but the parametric options surface has no CV-level equivalent."},
        "list000:Extend on Surface": {"status": "na", "reason": "Extending a curve constrained to a NURBS surface has no Blender analogue (no parametric surface-constrained curve concept) -- see Extend (Options); the plain Extend leaf is covered by the rolled btk.NurbsUtils.extend_curve."},
    },
    "selection": {
        "chk000": {"status": "na", "reason": "QRadioButton siblings are auto-exclusive; Maya's manual "
                                             "uncheck handlers are redundant on Blender"},
        "chk001": {"status": "na", "reason": "see chk000"},
        "chk002": {"status": "na", "reason": "see chk000"},
        # list001 "Convert To" (the cmb003 combo until 2026-08-16; now an ExpandableList on the
        # panel AND the submenu, both forks via SelectionMixin) -- ported 2026-07-06 from 7 to 15
        # of Maya's 20 items (Vertex
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
        "list001:Vertex Faces": {"status": "na", "reason": "Maya's vtxFace (PolySelectConvert 5) is its own per-corner sub-component type (like a split-normal/face-corner element, cmds type 70) -- a hybrid vertex-belonging-to-one-face component with no Blender selection-mode analogue (Blender's VERT/EDGE/FACE modes have no fourth 'corner' mode); Blender's nearest concept (custom split normals per-loop) lives in a completely different workflow (Mesh > Normals), not a selectable component."},
        "list001:UV's": {"status": "na", "reason": "Maya's UV component (PolySelectConvert 4, cmds .map[]) is a persistent 3D-viewport component type; Blender has no such thing -- UV coordinates are only selectable from within the UV Editor's own uv_select_mode, not the 3D viewport's VERT/EDGE/FACE modes. UV Shell/UV Shell Border/UV Perimeter/UV Edge Loop are the UV-domain items with viewport-reachable bmesh analogues and ARE built (2026-07-13)."},
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
        # The blanket "snap increments are grid-driven" reason was wrong for ROTATE — corrected
        # 2026-07-28 after enumerating ToolSettings' RNA live (Blender 5.1). Triage per widget:
        # s021=Move, s022=Scale, s023=Rotate (Maya's manipMove/Scale/RotateContext snapValue).
        "s021": {"status": "na", "reason": "Move snap increment (manipMoveContext snapValue). Blender has no scene-level numeric move increment to drive: absolute grid snapping (use_snap_grid_absolute) steps by the viewport grid, i.e. per-3D-view View3DOverlay.grid_scale/grid_subdivisions, not a value a single spinbox can own -- grid-driven, as the Blender slot docstring says."},
        "s022": {"status": "na", "reason": "Scale snap increment (manipScaleContext snapValue). Verified live (Blender 5.1, full ToolSettings RNA enumeration): the only scale-snap property is the BOOLEAN use_snap_scale -- there is no numeric scale increment anywhere in ToolSettings, so there is no value to bind."},
        # s023 (Rotate increment) BUILT 2026-07-28: bound degrees->radians onto
        # ToolSettings.snap_angle_increment_3d in the tb004 option box, enable-gated by chk023
        # (Maya's chk023 -> s023.setEnabled pattern). No delta.
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
    "polygons": {},
    "rigging": {},
    "subdivision": {},
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
    "materials": {
        "b007": {"status": "renamed", "to": "b_shader_editor", "reason": "Hypershade Editor -> 'Shader Editor' header button (btk.open_editor, Blender's Hypershade analogue)"},
        "tb002": {"status": "pending", "reason": "Enable Viewport Opacity — wires each material's opacity map (in-network, or found beside its other textures on disk) into the slot its shader type honors, so transparency shows in the viewport. Maya's engine side is mtk.MatUtils.enable_viewport_opacity / get_mats_by_scope / find_opacity_source. The Blender twin is buildable on the same shape: find the image texture whose path resolves to an Opacity map, connect its Alpha into the Principled BSDF Alpha socket, and switch the material to blended surface rendering (4.2+ surface_render_method='BLENDED'; blend_method='BLEND' before that) — needs a live Blender pass to pin the version-dependent property, so it is tracked as open work rather than guessed."},
        "cmb_opacity_scope": {"status": "pending", "reason": "tb002 scope combo (Selected Objects / Visible Objects / All Scene Materials) — rides the tb002 port; maps onto a btk.MatUtils.get_mats_by_scope twin (selection, visible objects, bpy.data.materials). Named cmb_opacity_scope, not cmb_scope: tb001's option box already owns that objectName, and the objectName is the StateManager key, so two scope combos under one name overwrite each other's persisted choice."},
        "chk_depth_peeling": {"status": "na", "reason": "tb002 option switching Viewport 2.0 to depth-peeled transparency (hardwareRenderingGlobals.transparencyAlgorithm). EEVEE has no depth-peeling mode — its transparency sorting is per-material (render method / sort order), not a viewport-wide algorithm — so there is no toggle to mirror."},
        "chk_exclude_defaults": {"status": "na", "reason": "Blender has no auto-created default materials to filter from the report; drop documented in tb001_init"},
        "chk_hide_defaults": {"status": "na", "reason": "Material-list filter (the filter field's option box, Maya's _list_filters hook): Blender has no auto-created default materials (lambert1 etc.) to hide, so its hook returns none and the field shows no option box"},
        "chk_hide_arnold": {"status": "na", "reason": "Hides Arnold shaders (classification rendernode/arnold*) from the material list (the filter field's option box), for scenes where every game material carries a parallel aiStandardSurface preview shader. Blender has no Arnold integration and no parallel-preview-shader convention — Cycles/EEVEE share one node-tree material — so there is nothing to filter."},
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
    "polygons": {
        "chk016": {"status": "na", "reason": "Snap-Closest-Verts Freeze Transforms toggle: Maya-only cmds world-query workaround (btk.snap_closest_verts computes exact world-space math under any transform — its docstring says so). The Blender port initially carried it, where freeze(store=False) permanently zeroed both objects' channels for zero benefit; removed in the 2026-07 slot-audit fix sweep."},
        "chk008": {"status": "replaced", "to": "tb007 Cuts model (s009:number_cuts)", "reason": "Maya polySubdivideFacet U-split toggle; Blender tb007 uses native mesh.subdivide(number_cuts) which has no U/V direction"},
        "chk009": {"status": "replaced", "to": "tb007 Cuts model (s009:number_cuts)", "reason": "Maya polySubdivideFacet V-split toggle; Blender tb007 uses native mesh.subdivide(number_cuts) which has no U/V direction"},
        # chk023 (Uninstance-before-Combine) + chk024 (Uninstance-before-Separate) BUILT
        # 2026-07-28: both hazards verified REAL in headless Blender 5.1 (join builds into the
        # active object's shared datablock -> a linked sibling mutates into the combined
        # geometry, refuting the 'may not exist' hypothesis; mesh.separate deletes the
        # separated faces from every sibling). btk.combine_objects/separate_objects gained
        # uninstance=True (default, mirroring mtk) via the existing NodeUtils.uninstance;
        # slot checkboxes mirror Maya's names/defaults. No delta.
    },
    "rendering": {
        "chk001": {"status": "na", "reason": "IPR launches a Maya Render View interactive session via renderer-registered MEL procs (RenderUtils.start_ipr); Blender's interactive render is the rendered-viewport shading state, not a render-op option — drop documented in Blender tb001 docstring. Added to Maya 2026-06-21 (9cc22169)."},
        "chk002": {"status": "na", "reason": "Smart Redo wraps Maya Render View MEL redoPreviousRender (RenderUtils.redo_previous_render); Blender's render op has no redo-previous concept (Render Result slots are native) — drop documented in Blender tb001 docstring. Added to Maya 2026-06-21 (9cc22169)."},
        "s020": {"status": "pending", "reason": "Render resolution width (scene-backed field + render presets via mtk.RenderUtils); Blender twin = scene.render.resolution_x, needs a btk render-settings surface"},
        "s021": {"status": "pending", "reason": "Render resolution height; see s020 (scene.render.resolution_y)"},
        "add_presets": {"status": "pending", "reason": "tb001's native preset selector over mtk.RenderUtils.render_preset_store (semantic {setting: value} presets); the Blender twin arrives with s020's render-settings surface"},
        "preset_dir": {"status": "pending", "reason": "see add_presets (the selector's user tier)"},
        "s022": {"status": "na", "reason": "Arnold sampling (mtk.RenderUtils.RENDER_SETTINGS, defaultArnoldRenderOptions); Blender has no Arnold -- Cycles/EEVEE sampling is a different model (samples + adaptive threshold, not camera x per-ray-type samples)"},
        "s023": {"status": "na", "reason": "Arnold sampling (mtk.RenderUtils.RENDER_SETTINGS, defaultArnoldRenderOptions); Blender has no Arnold -- Cycles/EEVEE sampling is a different model (samples + adaptive threshold, not camera x per-ray-type samples)"},
        "s024": {"status": "na", "reason": "Arnold sampling (mtk.RenderUtils.RENDER_SETTINGS, defaultArnoldRenderOptions); Blender has no Arnold -- Cycles/EEVEE sampling is a different model (samples + adaptive threshold, not camera x per-ray-type samples)"},
        "s025": {"status": "na", "reason": "Arnold sampling (mtk.RenderUtils.RENDER_SETTINGS, defaultArnoldRenderOptions); Blender has no Arnold -- Cycles/EEVEE sampling is a different model (samples + adaptive threshold, not camera x per-ray-type samples)"},
        "s026": {"status": "na", "reason": "Arnold sampling (mtk.RenderUtils.RENDER_SETTINGS, defaultArnoldRenderOptions); Blender has no Arnold -- Cycles/EEVEE sampling is a different model (samples + adaptive threshold, not camera x per-ray-type samples)"},
        "s027": {"status": "na", "reason": "Arnold sampling (mtk.RenderUtils.RENDER_SETTINGS, defaultArnoldRenderOptions); Blender has no Arnold -- Cycles/EEVEE sampling is a different model (samples + adaptive threshold, not camera x per-ray-type samples)"},
        "s028": {"status": "na", "reason": "Arnold sampling (mtk.RenderUtils.RENDER_SETTINGS, defaultArnoldRenderOptions); Blender has no Arnold -- Cycles/EEVEE sampling is a different model (samples + adaptive threshold, not camera x per-ray-type samples)"},
        "chk056": {"status": "na", "reason": "Maya playblast offScreen capture-mode flag (avoid viewport-redraw issues); bpy.ops.render.opengl always renders to an offscreen buffer and exposes no such parameter, so the toggle has no Blender surface. Maya control predates the port (2025-11-15 f7547ffe; Blender port 2026-06-12 c6b601c9 carried a documented subset)."},
        # chk059 (Clear Cache) + t001 (scene-name regex): removed from the Maya panel in the
        # 2026-07-18 PlayblastExporter overhaul (clearCache became an internal always-on detail;
        # the regex stage was dropped — type the name in t000 instead), so their na/replaced
        # entries no longer match any Maya-only control.
        # chk060 (Include Audio) BUILT 2026-07-28: tb000 sets scene.render.ffmpeg.audio_codec
        # (AAC when checked / NONE when not) for movie formats before render.opengl, snapshotted
        # + restored with the other borrowed render settings (audio_codec enum verified live:
        # NONE/AAC/AC3/FLAC/MP2/MP3). Live-GUI playblast-with-audio pass owed. No delta.
    },
    "rigging": {
        "chk001": {"status": "na", "reason": "IK radio drives Maya's global ikHandleDisplayScale; Blender has no global IK-handle display-scale — excused in the Blender slot"},
        "chk002": {"status": "na", "reason": "IK\\FK radio drives Maya's jointDisplayScale(ikfk=1); no Blender global IKFK display-scale — excused in the Blender slot"},
        "s000": {"status": "na", "reason": "Global joint/IK/IKFK display-scale spinbox (jointDisplayScale/ikHandleDisplayScale); no Blender scene-global display-scale — excused in the Blender slot"},
        "tb005": {"status": "pending", "reason": "Add to Skin (2026-10-14): mtk.SkinUtils.add_to_skin merges/binds new meshes into an existing skinCluster, un-posed through its bind so they land where modeled at any pose. blendertk has no SkinUtils; the port needs the Armature-modifier equivalent (vertex-group weights sampled from the closest surface point + rest-pose un-posing). tb005_init hides the button in Blender until then."},
        "cmb_skin_mode": {"status": "pending", "reason": "Add to Skin option box (merge vs separate bind) -- rides the tb005 port."},
        "chk_skin_rigid": {"status": "pending", "reason": "Add to Skin option box (rigid insert) -- rides the tb005 port."},
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
    "selection": {
        "cmb002": {"status": "pending", "reason": "Rig Picking Mode (2026-10-14): mtk.Selection.set_rig_selection_mode lifts the display lock Maya rigs put on skinned meshes (shape overrideEnabled under a rig-driven overrideDisplayType) and, for Meshes Only, masks curves/joints via selectType. blendertk rigs lock no mesh today; a port would map Meshes Only to hide_select on armatures/curves. cmb002_init hides it in Blender."},
        "chk003": {"status": "replaced", "to": "_ISLAND_DELIMIT model",
                   "reason": "Maya Lock-Values+normal-range island model -> native select_linked delimiters"},
        "s002": {"status": "replaced", "to": "_ISLAND_DELIMIT model", "reason": "see chk003"},
        "s004": {"status": "replaced", "to": "_ISLAND_DELIMIT model", "reason": "see chk003"},
        "s005": {"status": "replaced", "to": "_ISLAND_DELIMIT model", "reason": "see chk003"},
        # chk009 (Reverse Order) BUILT 2026-07-28 with the cmb001 Reorder Selection port: the
        # rolled btk.SelectionOrder tracker gives Blender an object selection order to reorder
        # (depsgraph-diff click recording + explicit set_order), and btk.reorder_objects mirrors
        # mtk's sort methods (creation_time -> session_uid, documented divergence). The old
        # "no ordered selection" na is retired — that was the missing primitive, now rolled.
        # No delta.
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
        "s021": {"status": "na", "reason": "Move increment -- grid-driven (see HANDLERS['transform']['s021'])"},
        "s022": {"status": "na", "reason": "Scale increment -- no numeric scale-snap value exists in Blender (see HANDLERS['transform']['s022'])"},
        # s023 BUILT 2026-07-28 (see HANDLERS['transform'] note). No delta.
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
    "materials": {
        "chk_include_optimization.setChecked": "Environment-driven default (documented in-file: builder comment + tooltip + docstring). Same ptk.MapOptimizer toggle, but Blender's bundled Python lacks Pillow, so the map-analysis report degrades to per-texture 'unavailable'; opt-in avoids a noise-filled default report. Maya's tooltip assumes PIL present.",
    },
    "normals": {
        "cmb000.setCurrentIndex": "Deliberately different item list: Blender cmb000 = native ops (Flip / Recalculate Outside / Recalculate Inside via btk.flip_normals/recalculate_normals); Maya = polyNormal normalMode enum (Reverse/Propagate/Conform/…). Maya's index 3 ('Reverse and Extract') has no Blender counterpart, so copying it would default to a semantically unrelated op; default 0 ('Flip') is the correct reverse counterpart.",
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
        "cmb002.items": "Blender adds Rigify presets ['Human Meta-Rig','Basic Human Meta-Rig','Generate Rig'] on top of Maya's procedural items -- Blender-only ENHANCEMENT (Rigify is Blender's native meta-rig system, no Maya counterpart), not a drop; Maya's 'Quick Rig' / 'HumanIK' are its own built-in character auto-riggers, the role Rigify fills here. The procedural items match, 'Articulated Rig' included (blendertk ArticulatedRig, 2026-10-17).",
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
