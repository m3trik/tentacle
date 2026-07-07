# tentacle — DCC Depth Parity (option-box & dynamic-control level)

> ⚠️ **Superseded by `PARITY_AUDIT.md` for true parity.** This reaches a high parity % by *excusing* Maya-only controls via `dcc_parity_overrides.json` rather than closing them, and it only sees option-box controls — not the missing tool-panels or the absent blendertk modules. See [`PARITY_AUDIT.md`](PARITY_AUDIT.md).

_Auto-generated. Do not edit by hand. Refresh via `m3trik/scripts/generate_dcc_parity.py`._

`DCC_COVERAGE.md` measures widget **presence** (100%/100%). This measures the layer below it: the **controls each slot builds in code** (option-box checkboxes/combos/spinboxes + dynamic header buttons). A Maya-only control is a **GAP by default** — it is only excused via a written, reasoned entry in [`dcc_parity_overrides.json`](dcc_parity_overrides.json). Nothing becomes N/A by omission.

**Depth %** = controls built in *both* DCCs ÷ (Maya controls − excused). `planned` gaps still count as open.

## Headline: 0 open gap(s) — of which **0 UNREVIEWED**, 0 planned · 120 excused (na/divergent/elsewhere)

| Domain | Maya | Blender | Shared | Open gaps | Excused | Depth |
|:---|--:|--:|--:|--:|--:|--:|
| animation | 102 | 68 | 60 | 0 | 42 | 100% |
| crease | 3 | 3 | 3 | 0 | 0 | 100% |
| duplicate | 8 | 8 | 8 | 0 | 0 | 100% |
| edit | 28 | 24 | 19 | 0 | 9 | 100% |
| materials | 21 | 19 | 18 | 0 | 3 | 100% |
| normals | 6 | 6 | 6 | 0 | 0 | 100% |
| nurbs | 19 | 8 | 7 | 0 | 12 | 100% |
| pivot | 11 | 4 | 4 | 0 | 7 | 100% |
| polygons | 22 | 23 | 20 | 0 | 2 | 100% |
| rendering | 15 | 11 | 11 | 0 | 4 | 100% |
| rigging | 19 | 16 | 16 | 0 | 3 | 100% |
| scene | 24 | 21 | 19 | 0 | 5 | 100% |
| selection | 24 | 24 | 19 | 0 | 5 | 100% |
| settings | 2 | 2 | 2 | 0 | 0 | 100% |
| subdivision | 8 | 8 | 8 | 0 | 0 | 100% |
| transform | 29 | 20 | 20 | 0 | 9 | 100% |
| uv | 43 | 30 | 24 | 0 | 19 | 100% |
| **TOTAL** | **384** | — | **264** | **0** | **120** | **100%** |

## Open gaps — Maya-only controls Blender doesn't build

_None._
## Excused (auditable — challenge any that aren't truly justified)

### animation
- `b000` — Slot Sequencer · **divergent**: Maya's Shot Sequencer is a standalone shot-node / scene-per-shot ripple editor. Blender's sequencing model (the Video Sequencer, linked scenes, and timeline-marker cameras) is structurally different, so a faithful port is a separate Blender-native tool, not a parity control; the b000 slot points the user at the VSE + camera markers.
- `b004` — Shot Manifest · **divergent**: Maya's Shot Manifest is a CSV-driven scene-assembly window built on Maya shot nodes. Blender assembles shots via linked Scenes/Collections (a different paradigm), so there is no faithful mirror; the b004 slot points the user at that native workflow.
- `chk001` — Update · **divergent**: Blender's Go To Frame is a direct frame_set (tb000/s000) that always refreshes; Maya's auto-update playback toggle has no frame-nav analogue.
- `chk002` — Relative · **divergent**: Tied to Maya's inverted-copy time placement — N/A to Blender's in-place key mirror.
- `chk003` — Preserve Keys · **divergent**: Maya's Adjust Spacing can insert/preserve a key exactly at the shift frame via its keyframe-insert API; Blender's gap-insert is a pure shift of keyframe_points at/after the frame — nothing to insert-and-preserve.
- `chk004` — Relative · **divergent**: Blender's Adjust Spacing always shifts keys at/after the frame by a relative amount; there is no absolute-frame repositioning variant of a gap insert.
- `chk005` — Delete Original · **divergent**: Maya inverts to a copy then optionally deletes the original; Blender inverts the keys in place (no copy).
- `chk006` — Relative · **divergent**: Blender Transfer assigns each target an independent copy of the source action (action.copy()); Maya's relative value-offset transfer (add the source delta to the target's current value) has no analogue in the action-copy model.
- `chk007` — Tangents · **divergent**: Blender Transfer copies the whole action, so handles/tangents always come with it — there is no separate tangent-only toggle to expose.
- `chk010` — Toggle Single frame · **divergent**: Maya Go-To-Frame single-frame playback toggle — not part of Blender's direct frame_set nav idiom.
- `chk011` — Invert · **divergent**: A Maya UI convenience that negates the frame spinbox; redundant in Blender where Go To Frame offers an explicit Absolute/Relative mode (cmb000) for negative/relative navigation.
- `chk016` — Group Overlapping · **divergent**: Blender keys visibility per object at the chosen When frame (cmb002); Maya's combined-range group visibility keying is the stagger-style grouping machinery, kept to Stagger Keys (tb003 chk014).
- `chk020` — Channel Box Only · **divergent**: Blender has no Channel Box — key ops act on all animated channels; there's no channel-box-scoped subset to restrict to.
- `chk022` — Untie Keyframes · **done-elsewhere**: Blender exposes untie as the chk_untie toggle on tb011 (tie_keyframes(untie=True)); the Maya objectName isn't reused.
- `chk024` — Channel Box Attrs Only · **divergent**: Blender has no Channel Box (no channel-box-scoped subset).
- `chk033` — Channel Box Only · **divergent**: Blender has no Channel Box (no channel-box-scoped subset).
- `chk034` — Channel Box Only · **divergent**: Blender has no Channel Box (no channel-box-scoped subset).
- `chk_absolute` — Absolute Mode · **divergent**: Blender Scale Keys uses a plain time multiplier; Maya's Absolute mode reinterprets the factor as a target duration/speed, part of its dual uniform/speed-retime model that Blender doesn't share.
- `chk_channel_box` — Channel Box Attrs Only · **divergent**: Blender has no Channel Box (no channel-box-scoped subset).
- `chk_delete_inputs` — Delete Inputs · **na**: Blender has no construction-history input nodes to delete after baking.
- `chk_ignore_holds` — Ignore Holds · **divergent**: Blender's animation info reports each object's raw keyed extent (min/max); it does no static-hold segment analysis, so there are no leading/trailing holds to exclude.
- `chk_inherited_vis` — Bake Inherited Visibility · **divergent**: Blender visibility (hide_viewport/hide_render) isn't inherited through the hierarchy the Maya way, so there's nothing to flatten on bake.
- `chk_merge_touching` — Group Touching · **divergent**: Tied to Maya Scale Keys' overlap-group machinery; Blender Scale Keys scales each action about its own pivot (no cross-object grouping). Stagger Keys carries the touching/overlap grouping (tb003 chk029).
- `chk_mute_drivers` — Mute Drivers · **divergent**: Maya mutes driver nodes after bake to keep them recoverable alongside its override-layer workflow; Blender's nla.bake replaces the action and Blender has no override animation layer, so there are no drivers left to mute.
- `chk_override_layer` — Use Override Layer · **divergent**: Blender has no animation layers (NLA differs structurally); bake targets the active action.
- `chk_preserve_outside` — Preserve Outside Keys · **divergent**: bpy.ops.nla.bake replaces the action across the baked range with no preserve-outside-range option; preserving keys outside the range isn't exposed by the native bake.
- `chk_split_static` — Split Static Segments · **divergent**: Maya Scale Keys can split animation into clips separated by static holds and scale each independently; Blender Scale Keys scales each action's keyframe_points as one block — the segment machinery isn't part of the Blender model.
- `cmb001` — Snap the resulting frame number. · **divergent**: Maya snaps the resulting frame to 'clean' numbers (preferred/aggressive) via set_current_frame; Blender frames are integers and Go To Frame is a direct frame_set, so there's no fractional result to snap.
- `cmb003` — Rounding method:
• Nearest: Round to nearest whole number
• … · **divergent**: Blender Snap Keys rounds to the nearest whole frame; Maya's floor/ceil/preferred/aggressive 'clean-number' rounding is its snap-mode machinery with no native Blender analogue.
- `cmb004` — Time range for keyframe deletion:
• All Keyframes: Delete al… · **divergent**: Blender Delete Keys clears all animation via animation_data_clear; windowed deletion (before/after/current) is done by selecting keys (tb013) and deleting them in the editor, not a delete-keys mode.
- `cmb014` — Scaling mode:
• Uniform: Traditional time scaling around piv… · **divergent**: Speed modes retime by sampling world-space motion (units/frame) — a motion-analysis retimer specific to Maya ScaleKeys. Blender Scale Keys is a pure time multiplier.
- `cmb033` — (no label) · **divergent**: Cross-object pivot grouping (single/per-object/overlap) is Maya ScaleKeys machinery; Blender Scale Keys scales each action about its own pivot.
- `cmb034` — Keyframe snapping after scaling (both modes):

• Nearest: Ro… · **done-elsewhere**: Snapping keys to whole frames after scaling is the Snap Keys op (tb009 / snap_keys); run it after Scale Keys rather than as a scale sub-option.
- `cmb037` — Which keys to step. · **divergent**: Blender Set Tangents applies the interpolation type to all keys of the selected objects; per-key scope (current-time/selected) is graph-editor key-selection nuance not surfaced on this op.
- `cmb038` — Which attributes/keys to copy. · **divergent**: Blender Copy Keys copies the active object's whole action (the paste buffer); Maya's per-attribute/per-frame/channel-box copy modes don't map to the action-copy model.
- `cmb039` — Where to paste the copied key values. · **divergent**: Blender Paste links an independent copy of the action, preserving its own key timing (= Maya's 'at copy frame'); there is no value-at-playhead attribute paste in the action-copy model.
- `cmb040` — Which tangent(s) to set stepped. · **divergent**: Blender interpolation is per-key (CONSTANT/LINEAR/BEZIER), not split into in/out tangent sides like Maya's stepped tangents, so there's no in/out/both choice.
- `cmb_traversal` — Expand the selected set by traversing the dependency graph. … · **divergent**: Maya can expand the reported set by walking the dependency graph (up/downstream); Blender has no comparable per-object animation dependency graph to traverse.
- `lbl020` — Set To Current Frame · **divergent**: Maya UI button to load the current time into the frame field; redundant in Blender where the timeline already exposes the live current frame.
- `s001` — Time:  · **divergent**: Blender inverts keys in place; Maya's start-time placement of the inverted copy doesn't apply to an in-place mirror.
- `s007` — Percent:  · **divergent**: Blender adds intermediate keys by sampling on a frame step (every N frames); Maya's percent-of-key density is a different sampling model.
- `s014` — Samples:  · **divergent**: Motion-sampling resolution for Maya's speed-retime mode only; Blender Scale Keys has no motion-sampling speed mode.

### edit
- `chk012` — Holed · **na**: A Blender face is a simple polygon and cannot contain an interior hole, so there are no holed faces to detect.
- `chk016` — Shared UV's · **na**: Blender UVs are per-loop (face-corner), never shared across a vertex the Maya way — there is nothing to un-share.
- `chk018` — Lamina · **na**: A lamina face (two faces on the same vertex set) cannot exist in a bmesh — Blender rejects creating a duplicate-vertex-set face — so it can never occur (overlapping faces on DISTINCT vert sets are handled by chk025 / get_overlapping_faces).
- `chk019` — Delete Unused Nodes · **done-elsewhere**: Purging unused/orphan datablocks is the scene module's Cleanup (btk.cleanup_scene / scene b_cleanup); Blender has no construction-history node graph on this Delete-History op.
- `chk020` — Delete Deformers · **divergent**: Blender has no construction/deformation history to delete; deformers are non-destructive modifiers removed individually, not via a Delete-History op.
- `chk026` — Delete History · **na**: Blender has no construction history (already messaged on edit's Delete History button).
- `chk027` — Toggle Lock/UnLock · **na**: Node locking has no Blender analogue — datablocks aren't lockable the Maya way (already messaged on edit's Node Locking button).
- `chk030` — Optimize Scene · **done-elsewhere**: Removing unused scene data is the scene module's Cleanup (orphan purge); there is no separate Optimize-Scene step in Blender.
- `chk031` — For All Objects · **divergent**: Scope toggle for Maya's Delete-History op, which has no Blender analogue (no construction history to delete on all vs selected).

### materials
- `b007` — Hypershade Editor · **done-elsewhere**: Blender's node-based Shader Editor is the Hypershade analogue; the header exposes it as b_shader_editor 'Shader Editor' (btk.open_editor). The Maya objectName isn't reused because a stateless button carries no shared QSettings state and the label differs (Hypershade vs Shader Editor).
- `chk_exclude_defaults` — Exclude Default Materials · **na**: Blender has no auto-created built-in default materials (no lambert1/standardSurface1 equivalent — a new object starts with no material), so there is nothing to exclude from the report.
- `chk_hide_defaults` — Hide Default Materials · **na**: Blender has no auto-created built-in default materials to hide from the cmb002 material list (see materials:chk_exclude_defaults).

### nurbs
- `chk000` — Uniform · **divergent**: Uniform vs chord-length NURBS parameterization in the loft direction. btk.loft builds a polygon mesh by arc-length resampling (always uniform spacing), so there is no parameterization mode to pick.
- `chk002` — Auto Reverse · **divergent**: Maya auto-computes per-curve direction for the NURBS loft. btk.loft bridges the profiles in selection order using each profile's own point order; there is no NURBS direction-reversal solve to automate.
- `chk003` — Range · **divergent**: NURBS-curve range flag for the loft input (see nurbs:chk006); no analogue for the mesh loft.
- `chk004` — Polygon · **na**: Maya can output the loft as a NURBS surface or polygon; btk.loft always builds a polygon mesh, so 'Polygon' is implicitly always on.
- `chk006` — Range · **divergent**: Maya's 'force a curve range on the input curve' is a NURBS-curve parameterization flag; the Screw-mesh revolve has no curve-range concept.
- `chk007` — Polygon · **na**: Maya can output the revolve as a NURBS surface or a polygon; Blender's Screw modifier always produces a polygon mesh, so 'Polygon' is implicitly always on — there is nothing to toggle.
- `chk009` — Use Tolerance · **divergent**: NURBS build-to-tolerance vs section-count switch. The Screw mesh is driven purely by step count (Sections), so there is no tolerance build mode.
- `chk010` — Angle Loft Between Two Curves · **divergent**: Maya's specialized two-curve angle-loft (extracts polygon edges as curves and lofts an angled surface between them) is a NURBS-surfacing feature with no Blender mesh-loft analogue.
- `s000` — Degree: · **divergent**: Loft NURBS surface degree. btk.loft produces a polygon mesh (linear bridge between profiles), not a parametric surface, so there is no degree.
- `s002` — Degree: · **divergent**: NURBS surface degree. Blender's Revolve is a Screw MODIFIER producing a polygon mesh, not a parametric NURBS surface, so there is no surface degree to set.
- `s006` — Tolerance: · **divergent**: NURBS surface build tolerance (used only when Use Tolerance is on). No analogue for the step-count-driven Screw mesh (see nurbs:chk009).
- `s007` — Angle Loft: Spans: · **divergent**: Span count for Maya's two-curve angle loft (see nurbs:chk010) — no analogue in Blender.

### pivot
- `chk001` — Reset Pivot Orientation · **na**: Blender origins have no orientation independent of the object's rotation — there is no separate pivot orientation to reset.
- `chk005` — Translate · **done-elsewhere**: Transfer-translate is already what pivot tb002 (transfer_pivot) does; Blender's origin is translate-only so the per-channel checkbox is unconditional.
- `chk006` — Rotate · **na**: Blender's origin is a single point — there is no rotate pivot channel to transfer.
- `chk007` — Scale · **na**: Blender's origin is a single point — there is no scale pivot channel to transfer.
- `chk008` — Bake · **na**: Blender origins are always baked into the object; there is no separate bake-pivot step (already messaged on pivot's Bake Pivot button).
- `chk009` — World Space · **divergent**: Part of the World-Aligned manipulator-pivot option (tb003); Blender has no manipulator pivot distinct from the origin, so the world/local distinction does not apply.
- `chk010` — Manip Pivot · **na**: Blender has no manipulator pivot separate from the object origin — the transform gizmo pivots about the origin/median/cursor, not a stored manip pivot.

### polygons
- `chk008` — U · **divergent**: Maya divides a facet directionally (divisionsU). Blender's bpy.ops.mesh.subdivide is uniform (number_cuts in both parametric directions at once) with no per-face U-only / V-only operator; the Cuts spinbox (s009) is the Blender equivalent control.
- `chk009` — V · **divergent**: Maya divides a facet directionally (divisionsV). Blender's bpy.ops.mesh.subdivide is uniform with no per-face V-only operator; the Cuts spinbox (s009) is the Blender equivalent control (see polygons:chk008).

### rendering
- `chk056` — Offscreen Capture · **na**: Maya toggles offscreen playblast to dodge viewport-redraw artifacts; Blender's render.opengl always renders to an offscreen buffer (the 'Active Viewport' camera option in cmb041 chooses view_context), so there is no on/off equivalent.
- `chk057` — Show Ornaments · **divergent**: Maya burns viewport HUD/ornaments into the capture; Blender's OpenGL render shows overlays only when capturing the viewport (cmb041='Active Viewport' -> view_context), and HUD burn-in is the separate metadata-stamp system, not a capture toggle.
- `chk059` — Clear Cache · **na**: Maya clears temporary playblast files before export; Blender's OpenGL render writes straight to the output path with no playblast temp-file cache to clear.
- `t001` — Optional regex applied to the scene name before building out… · **divergent**: Maya's PlayblastExporter applies a regex to the scene name to build multi-variation output filenames; Blender's OpenGL render writes a single output path, set directly via t000 (Output base path). The regex batch-naming belongs to multi-file export, which the single render doesn't do.

### rigging
- `chk001` — IK · **divergent**: Maya's tb000 radios pick whether the display-scale applies to joints / IK handles / IK-FK. Blender has no IK-handle display object (IK is a bone constraint, not a separate displayable handle with its own size), so there is no IK axis-display to scale. Bone local axes are toggled via tb000 chk000 (Joints -> armature.show_axes).
- `chk002` — IK\FK · **divergent**: No Blender analogue for a separate IK/FK display-scale (see rigging:chk001) — IK/FK is a constraint/driver setup, not a displayable handle.
- `s000` — Tolerance:  · **divergent**: Maya's global joint/IK display-scale (jointDisplayScale). Blender has no global bone-axis display scale — bone display is per-armature display_type (octahedral/stick/...) and per-bone length, not a single scalar — so there is no equivalent value to set.

### scene
- `b006` — Cleanup Unknown · **done-elsewhere**: Maya removes 'unknown nodes' (a Maya plugin-loss artifact with no Blender analogue). The Blender cleanup equivalent - purging orphan datablocks - is the header's Scene Cleanup (b_cleanup / btk.cleanup_scene).
- `b009` — Fix OCIO · **na**: Maya 'Fix OCIO' repairs a broken/missing OCIO config on scene load; Blender bundles its OCIO config (Filmic/AgX) natively and has no missing/broken-config failure mode to repair.
- `b012` — Toggle Command Ports · **na**: Maya opens commandPort servers for remote control; Blender has no commandPort-server analogue (the same reason ScriptJobManager has no add_om_callback).
- `b013` — Mesh Converter · **done-elsewhere**: Maya's standalone FBX->GLB Mesh Converter window; the Scene Exporter's 'Also Export GLB' (chk_glb, native glTF 2.0) covers GLB output for the live scene. Standalone batch-directory conversion is not part of the menu.
- `b014` — Save to Original Scene · **na**: Maya saves an open autosave back to its resolved original file; Blender autosave recovery (File > Recover Auto Save) tracks no 'original scene' relationship - an autosave opens as a normal file you then Save As.

### selection
- `chk003` — Lock Values · **divergent**: UI helper syncing Maya's per-axis Normal X/Y/Z island ranges; Blender's island-by-normal (tb002 chk_island_normal → select_linked delimit=NORMAL) uses a single normal-angle boundary, so there are no per-axis values to lock.
- `chk009` — Reverse Order · **na**: Blender operators receive an unordered object set; there is no object selection order to reverse (see the closed Reorder Selection / cmb001 N/A).
- `s002` — x:  · **divergent**: Maya grows the face island within a per-axis normal range; Blender's tb002 island uses select_linked delimiters (chk_island_normal stops growth at normal discontinuities by a single angle), not a per-XYZ normal range.
- `s004` — y:  · **divergent**: Per-axis normal range for Maya's island growth; Blender's select_linked NORMAL delimiter has no per-XYZ range (see s002).
- `s005` — z:  · **divergent**: Per-axis normal range for Maya's island growth; Blender's select_linked NORMAL delimiter has no per-XYZ range (see s002).

### transform
- `chk023` — Snap Rotate · **done-elsewhere**: Handled by the standalone chk023 slot (static widget in transform#submenu.ui, live toggle -> use_snap_rotate), not re-built in tb004_init like Maya - re-building would duplicate the chk023 objectName (its siblings chk021/chk022 are tb004 option-box-only). Same rotate-snap behavior, no objectName collision.
- `chk026` — Make Live · **na**: Maya's Make Live turns a surface into a live construction grid (new geometry snaps onto it); Blender has no live-surface mode. Surface-snapping during transform is chk025 (Constrain: Surface -> FACE snap).
- `chk038` — Delete History · **na**: Blender has no construction/deformation history to delete (already messaged on edit's Delete History).
- `chk040` — From Channel Box · **na**: Maya freezes the channel-box-selected attributes; Blender has no channel box. The freeze targets are the explicit Translate/Rotate/Scale checkboxes (chk032-34).
- `chk_restore_rig_anchors` — Restore Rig Anchors · **na**: Restores mayatk's GRP>LOC>GEO rig hierarchy (create_locator_at_object convention) after freeze; Blender rigging is Armature + vertex-group based with no such locator-anchor convention to restore.
- `cmb_connection_strategy` — {Preserve Connections (Warn and Skip) / Disconnect Incoming Connections / Delete Connection Nodes} · **divergent**: Maya DG: how to handle freezing T/R/S that are driven by node connections (preserve/disconnect/delete). Blender has no DG connection model - transform_apply bakes current values; driven channels are drivers/constraints, not disconnected or deleted by a freeze.
- `s021` — Increment: · **divergent**: Numeric move-snap increment; Blender's increment snap uses the viewport grid, not a per-transform numeric value. The on/off is chk021 (Snap Move).
- `s022` — Increment: · **divergent**: Numeric scale-snap increment; Blender's increment snap is grid-driven with no per-transform numeric value. The on/off is chk022 (Snap Scale).
- `s023` — Degrees: · **divergent**: Numeric rotation-snap angle; Blender's increment rotation snap is fixed/grid-driven with no exposed angle setting. The on/off is chk023 (Snap Rotate).

### uv
- `chk000` — Smart Fit · **na**: Maya smartFit best-fits the planar/cylindrical/spherical projection manipulator; Blender's Cube/Cylinder/Sphere projections (tb001 cmb011) auto-fit the object bounds with no smart-fit toggle.
- `chk016` — Skip Instances · **divergent**: bpy.ops.uv.pack_islands has no instance-aware packing flag; the slot packs each selected mesh's UVs.
- `chk020` — Straighten Shell · **divergent**: Whole-shell straighten; btk.straighten_uvs (tb005) is edge-based (selected UV edges within an angle band). Blender has no native straighten-entire-shell op.
- `chk022` — Stack Similar · **divergent**: Blender stacks ALL targeted shells (b030 / stack_uv_shells); there is no per-shell similarity/tolerance grouping (Maya texStackShells-specific).
- `chk026` — Include Auto Seams · **divergent**: Maya u3dAutoSeam auto-detects + cuts new seams without layout; Blender has no auto-seam-only op (smart_project generates seams as part of a full unwrap; existing island borders are chk025 Include UV Borders -> Seams From Islands).
- `chk033` — Per Shell · **divergent**: Mirror each shell about its own center; btk mirror (transform_uvs / tb008) flips the whole map about the shared UV bbox - there is no per-island in-place flip.
- `chk034` — Preserve Footprint · **divergent**: Keep mirrored UVs in the original footprint; Blender's whole-map mirror about the shared UV bbox center already preserves the footprint - the per-shell footprint option is specific to per-shell mirror (chk033).
- `chk040` — Invert Seam · **divergent**: Maya's unwrap_cylinder cuts an explicit lengthwise seam column and can flip it to the opposite side. Blender's Smart UV Project (the tb009 unwrap path) places the lengthwise cut automatically by connectivity/angle, with no exposed control over which side it lands on, so there is no Invert-Seam toggle to mirror.
- `cmb009` — Maya u3dLayout -preScaleMode (only two distinct behaviors).
… · **divergent**: pack_islands exposes only a boolean `scale`, not Maya's Preserve-UV vs Preserve-3D pre-scale modes.
- `cmb010` — Maya u3dLayout -preRotateMode. One-shot pre-orient before pa… · **divergent**: Maya u3dLayout -preRotateMode is a 6-mode one-shot pre-orient using the 3D mesh orientation (incl. axis-to-V); Blender pack_islands rotation is the chk_pack_rotate boolean (rotate_method), not a 3D-orientation pre-orient.
- `cmb012` — Maya polyAutoProjection -scaleMode (Standard only).
None: ke… · **divergent**: Maya polyAutoProjection -scaleMode (None/Uniform/Stretch); Blender smart_project exposes a scale_to_bounds boolean + correct_aspect, not the three-mode scale.
- `cmb013` — What to do when non-manifold geometry blocks Unfold:
Warn + … · **na**: Blender's bpy.ops.uv.unwrap doesn't reject non-manifold geometry, so Maya u3dUnfold's Warn+Select / Repair+Retry strategy has no analogue.
- `s000` — Tolerance:  · **divergent**: Only drives Stack Similar (chk022) — Blender's shell stacking has no tolerance/similarity grouping to tune.
- `s004` — UDIM:  · **divergent**: Target UDIM tile 1001-1200; Blender pack_islands packs into the [0,1]/active tile, not a numbered UDIM - UDIM targeting is a post-pack tile offset, not a pack_islands parameter.
- `s011` — Rotate Step:  · **divergent**: pack_islands rotates by rotate_method (axis-aligned/cardinal/any), exposed as tb000 chk_pack_rotate — there is no min/max/step rotation search range (RizomUV-specific).
- `s012` — Rotate Min:  · **divergent**: pack_islands has no rotation search range; rotation is the rotate/rotate_method toggle on tb000 (chk_pack_rotate).
- `s013` — Rotate Max:  · **divergent**: pack_islands has no rotation search range; rotation is the rotate/rotate_method toggle on tb000 (chk_pack_rotate).
- `s014` — Mutations:  · **na**: bpy.ops.uv.pack_islands has no optimization-passes/mutations parameter — that is a RizomUV/u3dLayout-specific search knob with no Blender pack analogue.
- `uv_editor` — Open UV Editor · **done-elsewhere**: Blender wires Open UV Editor on b031 (btk.open_editor('UV Editor')); the Maya header button name isn't reused.

## Override hygiene

- 🗑️ `scene:lbl004` — stale: matches no current Maya-only control (remove it).
- 🗑️ `scene:lbl005` — stale: matches no current Maya-only control (remove it).
