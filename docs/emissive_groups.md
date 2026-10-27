# Emissive groups — runtime-toggleable emissive regions in the FBX → Unity flow

One all-on emissive map; named face groups the engine gates independently at
runtime with `emission * dot(mask, weights)`. This doc is the cross-package
SSoT for the feature: concept, encodings, scene-data contract, wire schema,
and what each package owns.

The tool is tentacle's: its panel
([`ui/panels/emissive_groups/`](../tentacle/ui/panels/emissive_groups/), one Slots
class for both hosts) drives
[`tools/emissive_groups/`](../tentacle/tools/emissive_groups/), whose host-free
model runs over a Maya half and a Blender half (`maya.py` / `blender.py`); the
libraries' FBX exporters and record stores reach it through tentacle's
`m3trik.scene_records` entry points. The shared registry model is
pythontk's region-mask engine
(`pythontk/core_utils/engines/textures/region_masks.py`); the Unity side is the
`EmissiveGroupController.cs` / `EmissiveGroups.hlsl` / `EmissiveGroupsLit.shader`
templates in `unitytk/templates/`.

## Panel

**Materials ▸ Tools ▸ Materials (scene) ▸ Emissive Groups** in tentacle (both
DCCs; `marking_menu.show("emissive_groups")`). Layout: name field + **Add**,
a group table (Group / Slot / Weight / Faces) whose **Weight** column
scrub- and click-edits like a Maya channel-box field, **Remove / Select /
Validate**, and **Bake** — one button whose option box picks the encoding and
its settings (resolution, padding, force-over-foreign-color-set). The header
menu holds *Compact Retired Slots* and *Republish Export Data*; the table's
context menu repeats select/remove and adds *All On* / *All Off* plus the
keyable-weights actions (*Make Weights Keyable* / *Key Weights @ Current
Frame* / *Remove Keyable Weights*).

## Concept

An *emissive group* is a named set of faces ("headlights", "panel_leds") whose
emissive texels toggle or dim as one unit. Each group owns a **slot** — a mask
channel index (0=R … 3=A). Slots are a *contract*: assigned once, persisted,
never reshuffled, because engine scenes and animations key against them.
Removing a group **retires** its slot; `compact_slots()` is the explicit,
binding-breaking reclaim.

## Encodings

| Encoding | Membership transport | When |
|:---|:---|:---|
| `vertex-color` (default) | `emissiveGroups` RGBA color set, written **per-face-vertex/corner** (hard group boundaries), rides the FBX | Face-aligned groups. Zero textures, no UV coupling. **Claims the mesh's single Unity color stream**; caps at 4 groups |
| `channels` | `<name>_EMask` RGBA texture (one group per channel) + manifest sidecar, rasterized by `ptk.RegionMaskPacker` (AA supersampling + edge padding) | Emissive detail painted sub-face, or the color stream is taken. Mask resolution is decoupled from the emissive map (512 default). Mirrored/stacked UV shells share texels → such groups toggle together |
| `id` | reserved (per-pixel index + control LUT) | >4 groups (past the shared 4-slot ceiling); not implemented |

## Scene data (kept minimal — nothing exists until the tool is used)

- **Membership** — Maya: one bare `objectSet` per group (`emissiveGroup_<name>`);
  Blender: per-group boolean FACE attributes (same name), so overlap stays
  expressible like Maya sets.
- **Registry** (slots / defaults / encoding / last-bake info) — one JSON channel
  `emissive_registry` on `data_internal` (see [Scene data nodes](https://github.com/m3trik/mayatk/blob/main/docs/data_nodes.md)).
  Cleared when the last group and retired slot are gone. The bookkeeping model
  is `ptk.RegionGroupRegistry`; both DCCs only bind it to their carrier.
- **Export manifest** — regenerated onto `data_export.emissive_groups` before
  every FBX export (tentacle's registered producer for
  `ptk.SceneRecords.EMISSIVE_GROUPS`, `EmissiveGroups.export_record`; the
  authoring-time republish is `EmissiveGroups.refresh_export_metadata`); rides
  the FBX as a user property,
  read by unitytk's `EmissiveGroupImporter`. Cleared when no groups exist.
  **Authoring alone never creates it** — adding, weighting, or removing groups
  only refreshes a manifest that already exists, so a scene that has never
  been baked or exported carries no `data_export` node from this tool.

## Manifest wire schema (v2)

```json
{
  "version": 2,
  "encoding": "vertex-color",
  "color_set": "emissiveGroups",
  "groups": [
    {"name": "headlights", "slot": 0, "default": 1.0},
    {"name": "panel_leds", "slot": 1, "default": 0.0}
  ]
}
```

`channels` encoding replaces `color_set` with `mask` (texture filename),
`uv_channel`, and `resolution`. A group made keyable additionally carries
`"attr": "emissiveGroup_<name>"` — the carrier attribute whose animation
curve drives its weight (absent otherwise). Model + (de)serialization:
`ptk.RegionMaskManifest`, its `version` the record's
(`ptk.SceneRecords.EMISSIVE_GROUPS.version`); consumers warn-and-best-effort
on a newer `version`.

## Keyable weights (opt-in)

`EmissiveGroups.make_weights_keyable(names=None)` adds one keyable 0-1 float
per group on the `data_export` carrier (`emissiveGroup_<name>`, seeded from
the group default) and publishes the manifest — the RenderOpacity
attribute-mode idiom, but model-global rather than per-object. This is the
one authoring action allowed to *create* the carrier: keyable is inherently
export-facing. Key in the channel box / graph editor, or
`key_weight(name, value=None, frame=None)` (None = current value / time;
auto-makes the group keyable). `remove_keyable_weights()` strips the attrs
*and their animation*, leaving groups intact; `remove_group` also removes its
attr. `set_default` follows through to an **un-keyed** attr only — once
keyed, the animation owns the value and the default stays the import seed.

Transport per DCC:

- **Maya** — the FBX exporter ships keyed custom-attr curves natively as
  animated custom properties (proven by the RenderOpacity e2e). Unity
  flattens them onto the root Animator; because every group's attr name is
  unique (unlike RenderOpacity's shared `opacity`), `EmissiveGroupImporter`'s
  `OnPostprocessAnimation` rebinds each curve to
  `groups.Array.data[i].weight` on the root controller (slot-order index,
  the same order the importer writes the list) and drops the Animator
  orphan. No visibility dual-key workaround is needed.
- **Blender** — full authoring parity (keyable carrier custom properties +
  fcurves). Blender's FBX exporter has no custom-property *animation* path
  (verified in the 5.1 `io_scene_fbx` source: only transform / shape-key /
  camera channels bake), so the Scene Exporter ships the curves on a channel
  it DOES bake: at export time, `export_data_node` stages one **transient
  curve proxy** per keyed group
  (`BlenderEmissiveGroups.create_export_curve_proxies`, tentacle's registered
  `emissive_groups` export stager) — an Empty under
  `data_export`, named exactly the group's `attr`, whose `scale.x` carries
  the weight curve (scale because it is unitless; translation would pick up
  unit conversion). The proxy rides the FBX write and is deleted right after
  (`perform_export`'s finally → the task manager's transient-cleanup seam),
  so a saved scene never carries one; `validate()` flags leftovers from an
  interrupted export. Two exporter settings are load-bearing for this and
  are pinned in `_DEFAULT_FBX_OPTIONS`: `bake_anim_use_nla_strips` and
  `bake_anim_use_all_actions` are **False**, because with either on Blender
  writes one take *per action*, each rebased to frame 1 and with no
  scene-range take at all — the weight curve would then arrive in its own
  clip, time-misaligned with the model's animation. `export_data_node` also
  widens the scene frame range to cover the staged curves (`_cover_frame_range`),
  since the range is what the bake samples and the proxies are staged after
  the (optional) `set_bake_animation_range` task. Unity-side, the importer matches the proxy by its node
  name == manifest `attr`, rebinds its `m_LocalScale.x` curve to
  `groups.Array.data[i].weight`, strips the remaining baked transform
  curves, and deletes the proxy node from the prefab — so both DCCs' keyed
  weights arrive identically bound.

## Unity side

- `EmissiveGroupImporter` (in `EmissiveGroupController.cs`) parses the FBX user
  property, attaches a populated `EmissiveGroupController` to the prefab root,
  and enforces mask-texture import settings (`*_EMask*`: linear, HQ
  compression). Runtime: weights pack into `_GroupWeights` (Vector4) applied
  per-renderer via MaterialPropertyBlock — note an MPB opts that renderer out
  of SRP batching; at high instance counts prefer material instances.
- `_GroupWeights` **defaults to (1,1,1,1)** — a material without a controller
  matches the all-on bake; a disabled controller reverts to it.
- **Texels in no group always glow as baked.** The gate is
  `saturate(dot(mask, weights) + (1 - saturate(dot(mask, 1))))`: the second
  term restores exactly the texels no group claims, so grouping the
  headlights doesn't black out the dashboard. You only need to group what you
  intend to control. `RegionMaskPacker.preview` implements the same formula,
  so a DCC preview matches the engine.
- `EmissiveGroups.hlsl` is the pipeline-agnostic gate (Custom Function node
  compatible); `EmissiveGroupsLit.shader` is the ready-made URP material
  (vertex-color or texture mask source via a toggle).
- API: `controller.SetWeight("headlights", 0.5f)` / `SetAll(0)`;
  `groups[i].weight` fields are animatable (Timeline/Animator), and
  DCC-keyed weight curves arrive pre-bound to them via the keyable-weights
  import path above.

## Constraints (also in the panel help)

- Baked-GI bounce light ignores runtime toggles — pair a real `Light` with a
  group when it must light the scene.
- Face membership tracks indices; topology edits shift it — `validate()` after
  modeling changes (it also flags overlaps, orphan sets, foreign color sets).
- Mask `padding_px` must be ≥ the emissive bake's padding (dark-halo guard).
- Blender: the channels bake needs Pillow importable in Blender's Python
  (vertex-color encoding does not — the engine's imaging deps are optional).

## Verified / owed

Verified: pythontk engine tests (37); the tool's model (tentacle's
`test_emissive_groups_model.py`, 18, plain Python); its Maya half
(`test_emissive_groups.py`, 40, fresh Maya: Maya→FBX→Maya round-trips of the
color-set values, the user property and the **keyed weight curves**); its
Blender half (`test/blender/emissive_groups_check.py`, 62 checks, headless,
the curve-proxy FBX round trip included); panel wiring (tentacle's `test_emissive_groups_panel.py`, 21, in a
fresh GUI Maya — the uitk `TableWidget` hard-crashes mayapy in batch); the
panel loads and shows in a fresh GUI Blender (tentacle's
`test/blender/menus_load_check.py`); the full Scene Exporter pipeline (`test_scene_exporter.py`:
`perform_export` ships the animated proxy + manifest join key, leaves the
scene proxy-free, keeps weights keyed *past* `scene.frame_end` un-flattened,
and pins the single scene-range take that keeps them time-aligned with the
model's animation); full suites green after the fix — blendertk 2517 checks /
85 suites, mayatk 4136 tests; C# templates compile against Unity editor assemblies
(2022.3.40f1, and 6000.3.10f1 for the keyable-weights revisions); panel
parity sweep 0 deltas.

**Owed live**: the Blender panel's button flows — headless Blender ships no Qt
binding, so they are exercised only through the one Slots class both hosts
share (its Maya test drives every button). Unity in-editor import + shader compile is blocked by a license wall
on this machine (every batch launch, both 2022.3 and 6000, exits 198 /
"Machine bindings don't match" — needs a Hub sign-in), as is the real-project
bloom check and the in-editor half of the keyable-weights path (the curve
rebinding in `OnPostprocessAnimation` — the DCC-side transport is FBX
round-trip-proven, the Unity-side compile-proven only).
