"""Headless suite for the Emissive Groups tool's Blender half
(``tools/emissive_groups/blender.py``) over its model: the same registry
schema, slot stability, manifest wire format and bake behaviors as the Maya
half (``test_emissive_groups.py``, in a fresh Maya), plus Blender's own
curve-proxy transport and its FBX round trip.

Run: blender --background --factory-startup --python tentacle/test/blender/emissive_groups_check.py
"""

import os
import sys
import json
import tempfile
import traceback
from pathlib import Path

MONO = Path(__file__).resolve().parents[3]
for pkg in ("pythontk", "tentacle", "blendertk"):
    p = str(MONO / pkg)
    if os.path.isdir(p) and p not in sys.path:
        sys.path.insert(0, p)

lines = []


def check(name, cond, detail=""):
    lines.append(
        f"{'OK  ' if cond else 'FAIL'} {name}{(' | ' + str(detail)) if detail else ''}"
    )


try:
    import bpy

    import pythontk as ptk
    import blendertk as btk
    from tentacle.tools.emissive_groups.blender import (
        BlenderEmissiveGroups,
        EmissiveGroups,
    )

    DataNodes = btk.DataNodes

    # Fresh scene with one cube (factory startup ships one; make it explicit).
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.mesh.primitive_cube_add()
    cube = bpy.context.active_object
    cube.name = "eg_cube"

    # --- authoring -------------------------------------------------------
    attr = EmissiveGroups.add_group("front", {"eg_cube": [0]})
    check("add_group returns attr name", attr == "emissiveGroup_front", attr)
    check(
        "boolean FACE attribute created",
        cube.data.attributes["emissiveGroup_front"].domain == "FACE",
    )
    EmissiveGroups.add_group("top", {"eg_cube": [1, 3]})
    groups = EmissiveGroups.list_groups()
    check(
        "slots 0,1", (groups["front"]["slot"], groups["top"]["slot"]) == (0, 1), groups
    )
    check("face counts", (groups["front"]["faces"], groups["top"]["faces"]) == (1, 2))

    EmissiveGroups.add_group("front", {"eg_cube": [2]})  # extend
    check("extend keeps slot", EmissiveGroups.list_groups()["front"]["slot"] == 0)
    check("extend adds faces", EmissiveGroups.list_groups()["front"]["faces"] == 2)

    # Whole-mesh entry resolves to all faces.
    EmissiveGroups.add_group("shell", {"eg_cube": []})
    check("whole-mesh membership", EmissiveGroups.list_groups()["shell"]["faces"] == 6)
    EmissiveGroups.remove_group("shell")

    # --- registry hygiene + slot stability -------------------------------
    check(
        "registry on data_internal",
        ptk.SceneRecords.EMISSIVE_REGISTRY.is_present(DataNodes),
    )
    EmissiveGroups.remove_group("front")
    EmissiveGroups.add_group("new", {"eg_cube": [4]})
    slots = EmissiveGroups.list_groups()
    check(
        "removed slot retired (shell=2 retired, front=0 retired -> new=3)",
        slots["new"]["slot"] == 3,
        slots,
    )
    reclaimed = EmissiveGroups.compact_slots()
    check("compact reclaims", sorted(reclaimed) == [0, 2], reclaimed)

    # --- validate ---------------------------------------------------------
    EmissiveGroups.add_group("overlap", {"eg_cube": [1]})  # overlaps 'top'
    warnings = EmissiveGroups.validate()
    check("overlap warned", any("overlaps" in w for w in warnings), warnings)
    EmissiveGroups.remove_group("overlap")
    EmissiveGroups.compact_slots()

    # --- context safety: no screen-context reads ---------------------------
    # The slots run from tentacle's Qt event-pump timer, where
    # `bpy.context.window` is None: `selected_objects` is then absent
    # entirely (AttributeError) and `context.scene` unreliable. Simulate it
    # by driving the selection path with the window context stripped.
    import ast
    import tentacle.tools.emissive_groups.blender as eg_mod

    def _chain(node):
        parts = []
        while isinstance(node, ast.Attribute):
            parts.append(node.attr)
            node = node.value
        if isinstance(node, ast.Name):
            parts.append(node.id)
        return ".".join(reversed(parts))

    # AST, not text: docstrings legitimately NAME these members while
    # explaining why they aren't used.
    tree = ast.parse(open(eg_mod.__file__, encoding="utf-8").read())
    screen_ctx = (
        "bpy.context.selected_objects",
        "bpy.context.scene",
        "bpy.context.active_object",
        "bpy.context.view_layer",
    )
    offenders = sorted(
        {
            c
            for c in (_chain(n) for n in ast.walk(tree) if isinstance(n, ast.Attribute))
            if c.startswith(screen_ctx)
        }
    )
    check("no screen-context reads in the Blender half", not offenders, offenders)

    for obj in bpy.data.objects:
        obj.select_set(obj.name == "eg_cube")
    check(
        "selection resolves via the view layer",
        list(EmissiveGroups.adapter.faces()) == ["eg_cube"],
        list(EmissiveGroups.adapter.faces()),
    )

    # --- scene hygiene: authoring must not create the export carrier -------
    check(
        "authoring left no data_export carrier",
        bpy.data.objects.get("data_export") is None,
        [o.name for o in bpy.data.objects if o.name.startswith("data_")],
    )
    EmissiveGroups.refresh_export_metadata()  # explicit publish
    EmissiveGroups.add_group("hygiene", {"eg_cube": [5]})
    published = ptk.SceneRecords.EMISSIVE_GROUPS.read_text(DataNodes)
    check(
        "published manifest kept current by authoring",
        published is not None and "hygiene" in published,
        published,
    )
    EmissiveGroups.remove_group("hygiene")
    EmissiveGroups.compact_slots()

    # --- keyable weights (opt-in) -----------------------------------------
    plugs = EmissiveGroups.make_weights_keyable(["top"])
    check(
        "keyable prop created",
        plugs.get("top", "").endswith('["emissiveGroup_top"]'),
        plugs,
    )
    carrier = DataNodes.get_export_node(create=False)
    check(
        "keyable prop on carrier",
        carrier is not None and "emissiveGroup_top" in carrier,
    )
    payload = ptk.SceneRecords.EMISSIVE_GROUPS.load(DataNodes)
    by_name = {g["name"]: g for g in payload["groups"]}
    check("manifest records attr", by_name["top"].get("attr") == "emissiveGroup_top")
    check("non-keyable group has no attr", "attr" not in by_name["new"], by_name)

    EmissiveGroups.key_weight("top", value=1.0, frame=1)
    EmissiveGroups.key_weight("top", value=0.0, frame=10)
    fc = BlenderEmissiveGroups._weight_fcurve("emissiveGroup_top")
    check("keyed 2 frames", fc is not None and len(fc.keyframe_points) == 2)
    check(
        "key values",
        fc is not None
        and [kp.co[1] for kp in sorted(fc.keyframe_points, key=lambda k: k.co[0])]
        == [1.0, 0.0],
    )

    EmissiveGroups.set_default("new", 0.25)
    EmissiveGroups.make_weights_keyable(["new"])
    check(
        "keyable seeds from default",
        abs(carrier["emissiveGroup_new"] - 0.25) < 1e-6,
        carrier.get("emissiveGroup_new"),
    )
    EmissiveGroups.set_default("new", 0.75)
    check(
        "unkeyed prop follows default",
        abs(carrier["emissiveGroup_new"] - 0.75) < 1e-6,
    )
    EmissiveGroups.set_default("top", 0.5)  # keyed: animation owns the value
    check(
        "keyed prop keeps its fcurve", BlenderEmissiveGroups._weight_fcurve("emissiveGroup_top") is not None
    )

    removed = EmissiveGroups.remove_keyable_weights()
    check("remove strips props", sorted(removed) == ["new", "top"], removed)
    check(
        "props gone from carrier",
        "emissiveGroup_top" not in carrier and "emissiveGroup_new" not in carrier,
    )
    check(
        "groups intact after strip",
        sorted(EmissiveGroups.list_groups()) == ["new", "top"],
    )
    payload = ptk.SceneRecords.EMISSIVE_GROUPS.load(DataNodes)
    check(
        "manifest attr records cleared",
        all("attr" not in g for g in payload["groups"]),
    )

    # Orphan carrier prop: a reimport restores keyable props, not the registry.
    carrier["emissiveGroup_ghost"] = 1.0
    warnings = EmissiveGroups.validate()
    check(
        "orphan carrier prop warned",
        any("emissiveGroup_ghost" in w and "no registry entry" in w for w in warnings),
        warnings,
    )
    del carrier["emissiveGroup_ghost"]

    # --- vertex-color bake ------------------------------------------------
    manifest = EmissiveGroups.bake_vertex_colors()
    check("bake manifest encoding", manifest["encoding"] == "vertex-color")
    check("color_set name", manifest["color_set"] == "emissiveGroups")
    cattr = cube.data.color_attributes.get("emissiveGroups")
    check("color attribute exists", cattr is not None)
    check("corner domain", cattr is not None and cattr.domain == "CORNER")
    if cattr is not None:
        # top = slot 1 -> G on faces 1,3; new = slot 3 -> A on face 4.
        poly = cube.data.polygons[1]
        cols = [tuple(cattr.data[lo].color) for lo in poly.loop_indices]
        check("top face G=1", all(abs(c[1] - 1.0) < 0.02 for c in cols), cols[0])
        check("top face R=0", all(abs(c[0]) < 0.02 for c in cols))
        poly4 = cube.data.polygons[4]
        cols4 = [tuple(cattr.data[lo].color) for lo in poly4.loop_indices]
        check("new face A=1", all(abs(c[3] - 1.0) < 0.02 for c in cols4), cols4[0])
        poly5 = cube.data.polygons[5]
        cols5 = [tuple(cattr.data[lo].color) for lo in poly5.loop_indices]
        check(
            "unmember face zeroed",
            all(all(abs(v) < 0.02 for v in c[:3]) and abs(c[3]) < 0.02 for c in cols5),
        )

    payload = ptk.SceneRecords.EMISSIVE_GROUPS.read_text(DataNodes)
    check("manifest published to data_export", payload is not None)
    if payload:
        data = json.loads(payload)
        check(
            "manifest version is the record's, no schema",
            data.get("version") == ptk.SceneRecords.EMISSIVE_GROUPS.version
            and "schema" not in data,
            data,
        )
        check(
            "manifest groups sorted by slot",
            [g["slot"] for g in data["groups"]]
            == sorted(g["slot"] for g in data["groups"]),
        )

    # Foreign color attribute guard.
    cube.data.color_attributes.new(name="paintjob", type="BYTE_COLOR", domain="CORNER")
    try:
        EmissiveGroups.bake_vertex_colors()
        check("foreign color attr refused", False)
    except ValueError:
        check("foreign color attr refused", True)
    manifest = EmissiveGroups.bake_vertex_colors(force=True)
    check("force overrides foreign guard", manifest["encoding"] == "vertex-color")

    # --- mask bake (channels) --------------------------------------------
    tmp = tempfile.mkdtemp()
    mask_path = os.path.join(tmp, "eg_EMask.png")
    manifest = EmissiveGroups.bake_mask(output_path=mask_path, resolution=64)
    check("mask written", os.path.isfile(mask_path))
    check("mask manifest encoding", manifest["encoding"] == "channels", manifest)
    check(
        "no mask manifest sidecar (published via the scene records)",
        not os.path.exists(os.path.join(tmp, "eg_EMask.json")),
    )
    payload = ptk.SceneRecords.EMISSIVE_GROUPS.load(DataNodes)
    check("export carrier switched to channels", payload["encoding"] == "channels")

    # No path: the file's project texture folder (mayatk's folder for a scene
    # in that project), never temp -- an unsaved file uses the workspace set.
    EnvUtils = btk.EnvUtils

    _prev_pin = EnvUtils.workspace_root() or None
    ws = tempfile.mkdtemp()
    EnvUtils.set_current_workspace(ws)
    try:
        EmissiveGroups.bake_mask(resolution=32)
        default_mask = os.path.join(ws, "sourceimages", "untitled_EMask.png")
        check(
            "default mask lands in the workspace's texture folder, not temp",
            os.path.isfile(default_mask),
            os.listdir(ws),
        )
        EnvUtils.set_current_workspace(None)
        try:
            EmissiveGroups.bake_mask(resolution=32)
            check("an unsaved file with no workspace refuses a default mask", False)
        except ValueError:
            check("an unsaved file with no workspace refuses a default mask", True)
    finally:
        EnvUtils.set_current_workspace(_prev_pin)

    # --- teardown hygiene -------------------------------------------------
    for name in list(EmissiveGroups.list_groups()):
        EmissiveGroups.remove_group(name)
    EmissiveGroups.compact_slots()
    check(
        "registry cleared when empty",
        ptk.SceneRecords.EMISSIVE_REGISTRY.read_text(DataNodes) is None,
    )
    check(
        "export carrier cleared when empty",
        ptk.SceneRecords.EMISSIVE_GROUPS.read_text(DataNodes) is None,
    )

    # --- keyed-weight curve transport (export proxies) ---------------------
    # Fresh scene: the FBX round-trip below imports objects, which must not
    # bleed into the sections above.
    AnimUtils = btk.AnimUtils
    FbxUtils = btk.FbxUtils

    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.mesh.primitive_cube_add()
    kcube = bpy.context.active_object
    kcube.name = "kw_cube"
    EmissiveGroups.add_group("glow", {"kw_cube": [0]})
    EmissiveGroups.make_weights_keyable(["glow"])
    EmissiveGroups.key_weight("glow", value=1.0, frame=1)
    EmissiveGroups.key_weight("glow", value=0.0, frame=10)

    proxies = BlenderEmissiveGroups.create_export_curve_proxies()
    check("one proxy per keyed group", len(proxies) == 1, [o.name for o in proxies])
    proxy = proxies[0] if proxies else None
    check(
        "proxy named the manifest attr",
        proxy is not None and proxy.name == "emissiveGroup_glow",
    )
    check(
        "proxy marked + parented under the carrier",
        proxy is not None
        and proxy.get(BlenderEmissiveGroups.PROXY_MARKER)
        and proxy.parent is DataNodes.get_export_node(create=False),
    )
    pfc = next(
        (
            f
            for f in AnimUtils.get_fcurves([proxy] if proxy else [])
            if f.data_path == "scale" and f.array_index == 0
        ),
        None,
    )
    check(
        "proxy scale.x carries the weight keys",
        pfc is not None
        and [kp.co[1] for kp in sorted(pfc.keyframe_points, key=lambda k: k.co[0])]
        == [1.0, 0.0],
        None if pfc is None else [tuple(kp.co) for kp in pfc.keyframe_points],
    )

    # Round-trip: the proxy's curve must survive a real FBX export→import —
    # the exact transport Unity's importer reads (m_LocalScale.x on the
    # proxy node). Empty-inclusive object_types + bake_anim mirror the scene
    # exporter's defaults (fbx_utils' bridge defaults pin mesh-only).
    fbx_path = os.path.join(tmp, "kw_proxy.fbx")
    FbxUtils.export_selection_fbx(
        filepath=fbx_path,
        objects=[kcube, DataNodes.get_export_node(create=False)] + proxies,
        object_types={"EMPTY", "MESH"},
        use_custom_props=True,
        bake_anim=True,
    )
    check("proxy FBX written", os.path.isfile(fbx_path))

    removed = BlenderEmissiveGroups.remove_export_curve_proxies()
    check("proxies removed after the write", removed == ["emissiveGroup_glow"], removed)
    check(
        "no proxy object survives in the scene",
        not any(o.get(BlenderEmissiveGroups.PROXY_MARKER) for o in bpy.data.objects),
    )

    # anim_offset=0: Blender's importer shifts every key +1 frame by default,
    # so the round trip is only an identity without it. Until 2026-09-19 the
    # write cancelled that shift by accident -- with no takes armed it emitted
    # one start-ZEROED take per action, and an action starting at frame 1 came
    # back at 1. An action starting anywhere else did not (the 81-frame clip
    # miss), which is why every animated write is one scene-range take now.
    imported = FbxUtils.import_fbx(fbx_path, use_custom_props=True, anim_offset=0.0)
    iproxy = next(
        (o for o in imported if o.name.startswith("emissiveGroup_glow")), None
    )
    check(
        "proxy node rides the FBX",
        iproxy is not None,
        [o.name for o in imported],
    )
    ifc = next(
        (
            f
            for f in AnimUtils.get_fcurves([iproxy] if iproxy else [])
            if f.data_path == "scale" and f.array_index == 0
        ),
        None,
    )
    check(
        "imported scale.x curve reproduces the weight animation",
        ifc is not None
        and abs(ifc.evaluate(1) - 1.0) < 0.01
        and abs(ifc.evaluate(10) - 0.0) < 0.01,
        None if ifc is None else (ifc.evaluate(1), ifc.evaluate(10)),
    )

    # Name-collision guard: an unrelated object squatting the attr name means
    # that group's animation is skipped (warned), never clobbered. Sweep the
    # imported transport artifacts first — the imported proxy still carries
    # the marker prop (user props ride the FBX), so the pre-clean would
    # otherwise delete it and hand its name to the blocker's .001 twin.
    BlenderEmissiveGroups.remove_export_curve_proxies()
    blocker = bpy.data.objects.new("emissiveGroup_glow", None)
    check("blocker owns the exact attr name", blocker.name == "emissiveGroup_glow")
    check(
        "proxy creation skips a squatted name",
        BlenderEmissiveGroups.create_export_curve_proxies() == [],
    )
    bpy.data.objects.remove(blocker)

    # Leftover sweep: a proxy outside an export is an interrupted run.
    BlenderEmissiveGroups.create_export_curve_proxies()
    check(
        "validate flags a leftover proxy",
        any("Leftover export curve proxy" in w for w in EmissiveGroups.validate()),
    )
    BlenderEmissiveGroups.remove_export_curve_proxies()

except Exception:
    traceback.print_exc()
    lines.append("FAIL unhandled exception")

print("\n".join(lines))
ok = not any(line.startswith("FAIL") for line in lines)
print(f"===RESULT: {'PASS' if ok else 'FAIL'}===")
