# !/usr/bin/python
# coding=utf-8
"""Tunable parameters surfaced in the WebXR Preview panel.

An ``AttributeSpec`` registry read by :class:`uitk.bridge.BridgeSlotsBase`,
which builds one row per entry, groups them by ``section`` and shows only the
keys the active source declares (:meth:`WebXrPreviewSlots._relevant_param_keys`).

The split that matters here is *export* versus *delivery*. An export param
travels in the bridge's param bag and only means something when a host is
producing the FBX, so it is hidden for a file source, which exports nothing.
A delivery param is answered by the deliverer for every source alike. Keeping
the distinction in the registry rather than in panel branches is what lets one
panel serve a DCC selection and a file on disk without a conditional.

The **Textures** rows are not this panel's own: they are the Scene Exporter's
rows that decide a GLB deliverable (:attr:`pythontk.ExportProfile.GLB_ROWS`) --
its images -- built from the same tables with the same labels and defaults, and
the push resolves them with the methods the exporters call. Set them the same in
both panels and the GLB texture pass is the same in both. The flow is one way:
nothing here is read by an export. They are shown only where the pass reads
them: for a push that re-encodes images (a scope with Include Textures on, or an
FBX -- never a GLB, published as authored), and KTX2 RDO with a KTX2 container
as the exporter shows it. The lighting recipe has no row: both publish the
recipe's own.
"""

from __future__ import annotations

from typing import Dict

import pythontk as ptk

from tentacle import Slots

AttributeSpec, ParamRegistry = Slots.AttributeSpec, Slots.ParamRegistry


#: Source carriers the preview can build from. ``.fbx`` runs the full
#: conversion; ``.glb`` publishes as authored. Mirrors
#: ``pythontk.FilePreviewBridge.SOURCE_EXTENSIONS`` -- the bridge refuses
#: anything else, and this keeps the refusal out of the file dialog.
SOURCE_FILE_TYPES = ["*.fbx", "*.glb"]

#: The carrier published as authored (``GlbPipeline.build``'s identity build):
#: no pass runs on it, so no texture row applies to a source made only of it.
AUTHORED_EXTENSION = ".glb"


#: Export params: meaningful only when a host is producing the export. Hidden
#: for the file source, whose "export" already happened -- Include Textures
#: too: a file's FBX already chose what it embeds.
EXPORT_KEYS = frozenset({"INCLUDE_ANIMATION", "EMBED_TEXTURES"})

#: Params the file source owns and no host scope has.
FILE_KEYS = frozenset({"SOURCE_FILE"})

#: This panel's key for each Scene Exporter GLB row -> the row's own key
#: (the one ``push(glb_options=...)`` takes). Upper-cased, the convention of
#: this registry; derived, so a row added upstream arrives by itself.
GLB_KEYS: Dict[str, str] = {row.upper(): row for row in ptk.ExportProfile.GLB_ROWS}

#: The texture rows: read by the texture pass, which re-encodes the images a
#: push carries -- a scope's with Include Textures on, an FBX file's -- and
#: never a GLB published as authored.
TEXTURE_KEYS = frozenset(
    key for key, row in GLB_KEYS.items() if row in ptk.ExportProfile.GLB_TEXTURE_ROWS
)

#: Texture rows only a KTX2 container reads (ETC1S / UASTC are its encodes),
#: shown with it as the Scene Exporter shows them.
KTX2_KEYS = frozenset({"UASTC_RDO"})

#: What each GLB row does, in the preview's words. The rows themselves --
#: labels, choices, order, defaults -- come from the Scene Exporter's tables;
#: only this prose is the panel's own.
_ROW_TOOLTIPS: Dict[str, str] = {
    "texture_file_type": "The Scene Exporter's Texture File Type row, for the "
    "GLB: the container every embedded image is re-encoded to.\n\n"
    f"Original takes the web default ({ptk.MeshConvert.WEB_DELIVERY_FORMAT}), "
    "exactly as an exported GLB does.\n\n"
    "WebP is small on the wire but decodes to plain RGBA on the GPU: a "
    "measured 9.5 MB delivery became roughly 740 MB of video memory with "
    "mipmaps, and on a headset that -- not the download -- caps how large a "
    "scene can be previewed. KTX2 stays block-compressed on the GPU (ASTC on "
    "a standalone headset, BC7 on desktop); it costs encode time and needs "
    "KTX-Software's toktx, which this panel offers to install when it is "
    "missing -- a push never quietly ships WebP instead. KTX2 + PNG/JPEG adds "
    "a standard copy of every map so the GLB also opens in Blender, Unreal or "
    "stock Unity.\n\n"
    "Only the containers a GLB can carry are offered: a scene-side type "
    "(TGA, EXR ...) means the web default inside a GLB anyway.",
    "optimize_textures": "The Scene Exporter's Optimize Textures row, for the "
    "GLB: the longest edge its embedded images keep. Maps smaller than the "
    "ceiling are never grown.\n\n"
    "OFF sets no ceiling: every map keeps its own resolution, as in an "
    "exported GLB, unless Secondary Map Size caps the data maps. A plain "
    "Optimize names no ceiling, so it takes the web "
    f"delivery ceiling ({ptk.MeshConvert.WEB_DELIVERY_MAX_SIZE} px); "
    "Optimize + Max N caps at N.\n\n"
    "Template Budget is not offered: its ceiling comes from the export's "
    "Texture Template row, whose material conversion this push does not run. "
    "Pick that template's ceiling here instead.",
    "secondary_max_size": "The Scene Exporter's Secondary Map Size row: a lower "
    "ceiling for the packed data maps (metallic-roughness and occlusion), "
    "under the one Optimize Textures sets -- and applied with Optimize "
    "Textures OFF too, as a choice of its own. Colour and normal maps keep "
    "the primary ceiling.",
    "uastc_rdo": "The Scene Exporter's KTX2 RDO row: rate-distortion "
    "optimisation for the UASTC encodes (normal and data maps), trading a "
    "controlled quality cost for smaller files at 3-4x the encode time. Only "
    "with a KTX2 texture file type.",
}


#: What each way of sharing means for whoever picks it, in the panel's words.
#: The entries themselves come from pythontk's registry
#: (``ShareTunnel.PROVIDERS``), so a provider added there arrives by itself,
#: under its own label.
_PROVIDER_TOOLTIPS: Dict[str, str] = {
    "cloudflared": "A Cloudflare quick tunnel: no account, and a fresh random "
    "link on every share. Cloudflare's edge terminates the HTTPS, so it sees "
    "the traffic. The panel offers to download cloudflared when it is missing; "
    "a machine that denies outbound connections by default must allow it once.",
    "tailscale_funnel": "Tailscale Funnel: a STABLE public link on your "
    "machine's tailnet name -- bookmark it once in a headset -- with the HTTPS "
    "ending on this machine. Funnel must be enabled for the tailnet once; the "
    "first share offers to open the page that does it, and the link comes up "
    "by itself once it is enabled. Relayed, so a large push loads slower.\n\n"
    "Each share's name takes minutes to reach public DNS -- measured 5.5, and "
    "over 25 -- and leaves it when the share ends: until then no one else can "
    "open the link. "
    "The panel says so in red and tells you when it opens. Guests need no "
    "Tailscale of their own. Three scenes at most share at once (ports 443, "
    "8443 and 10000).",
    "tailscale_serve": "Tailscale, reachable only by devices on your tailnet: "
    "nothing public. A standalone headset needs the Tailscale app to open it.",
}


def _share_choices() -> list:
    """Off, Auto, then every provider pythontk can drive."""
    off = ("Off", "off", "Not shared: the preview stays on this machine.")
    auto = (
        "Auto",
        "auto",
        "Whatever this machine has: Cloudflare when it is installed, else "
        "Tailscale Funnel when Tailscale is. With neither, the panel offers "
        "to download Cloudflare's client.",
    )
    return [off, auto] + [
        (spec["label"], name, _PROVIDER_TOOLTIPS.get(name, ""))
        for name, spec in ptk.ShareTunnel.PROVIDERS.items()
    ]


def _glb_rows(rows: Dict[str, str], section: str) -> "dict[str, AttributeSpec]":
    """One choice row per Scene Exporter GLB row in *rows*, from its own table.

    Each starts where the Scene Exporter starts it
    (:meth:`pythontk.ExportProfile.glb_defaults`), so an untouched panel runs
    the texture pass an untouched export runs.
    """
    options = ptk.ExportProfile.glb_options()
    defaults = ptk.ExportProfile.glb_defaults()
    return {
        key: AttributeSpec(
            key=key,
            label=ptk.ExportProfile.GLB_ROWS[row],
            kind="choice",
            default=defaults[row],
            choices=list(options[row].items()),
            section=section,
            tooltip=_ROW_TOOLTIPS[row],
        )
        for key, row in GLB_KEYS.items()
        if row in rows
    }


# Display order is iteration order over this dict.
PARAMS: "dict[str, AttributeSpec]" = {
    "SOURCE_FILE": AttributeSpec(
        key="SOURCE_FILE",
        label="Source Files",
        kind="files",
        default=[],
        choices=SOURCE_FILE_TYPES,
        section="Source",
        # An empty field is the ordinary first state, and it is not idle:
        # pushing from it asks. Saying so on the row is what makes the empty
        # panel usable without reading a tooltip to find that out.
        placeholder="Leave empty and Push will ask for files",
        tooltip="The file to preview -- or several, separated by ; (Browse "
        "picks as many as you select).\n\n"
        "Several files are the PARTS of one scene -- a room, the props in it, "
        "a character, each exported on its own: the page shows them together, "
        "each at its authored place, so they line up as they do in the scene. "
        "View lists each part, to hide it; Export saves each under its own "
        "name.\n\n"
        "An FBX runs the full build -- conversion, lightmaps, texture pass -- "
        "so what you see is what a target platform would receive.\n\n"
        "A GLB is published exactly as authored: no re-encode, no sidecar, no "
        "lightmap rewiring. Those passes exist to repair what an FBX "
        "translation loses, and a finished GLB has already answered them. "
        "That makes this a plain viewer too -- open a vendor's asset, or "
        "re-open the GLB an exporter just wrote, on the same page and port a "
        "scene push uses.\n\n"
        "A lightmap manifest's maps are resolved against the files' own "
        "folders, so a bake that travelled with its asset needs nothing else.\n\n"
        "The + beside the field adds another SCENE: its own files, page and "
        "server -- and, while Sharing is on, its own link -- live beside this "
        "one. Push publishes every scene.",
    ),
    "INCLUDE_ANIMATION": AttributeSpec(
        key="INCLUDE_ANIMATION",
        label="Include Animation",
        kind="bool",
        default=False,
        section="Delivery",
        tooltip="Bake the scene's animation into the pushed GLB so the preview "
        "can play it. The page grows a clip picker and transport, an Export "
        "menu Playblast item that records the selected clip -- or the whole "
        "shot sequence -- to a movie beside the deliverable, and, when the "
        "shots carry descriptions, View menu Clip descriptions to caption "
        "each as it plays.\n\n"
        "Off by default because baking samples every frame of the scene range, "
        "which costs push time and file size on a scene you are previewing for "
        "its look. A scene with shots declared ships its takes either way.",
    ),
    "EMBED_TEXTURES": AttributeSpec(
        key="EMBED_TEXTURES",
        label="Include Textures",
        kind="bool",
        default=True,
        section="Textures",
        tooltip="Embed the scene's textures in the export the preview builds "
        "from, at the container and size the rows below set -- off, those "
        "rows hide, with no image for them to set. A scene push only: a "
        "file's FBX already chose what it embeds.\n\n"
        "Unchecked is much smaller over the wire and skips the texture passes, "
        "but the preview shows flat materials -- and it is not much faster: "
        "the conversion's cost is the animation it bakes over every node, not "
        "the images. Measured on a production assembly, a 12 MB textureless "
        "export converted in the same minutes as the 366 MB one.",
    ),
    **_glb_rows(ptk.ExportProfile.GLB_TEXTURE_ROWS, "Textures"),
    "LOCOMOTION": AttributeSpec(
        key="LOCOMOTION",
        label="Locomotion",
        kind="bool",
        default=True,
        section="Viewer",
        tooltip="Getting around in a headset on the thumbsticks: walk where you "
        "look, snap-turn, and aim a teleport.\n\n"
        "Off, a session stays where it starts -- under the scene's start "
        "camera (a camera named user_pos) when it has one: free to look round "
        "and step about the room, but not to go anywhere.\n\n"
        "Applies at once, without a push: a headset already in a session, a "
        "share's guests included, follows within a second.",
    ),
    "VIEWER_SCRIPTS": AttributeSpec(
        key="VIEWER_SCRIPTS",
        label="Viewer Scripts",
        kind="check_list",
        default=[],
        # A registry rather than a branch: a script added to pythontk's
        # ``PreviewServer.SCRIPTS`` becomes a row here by ONE entry, tooltip
        # included, so an addition cannot forget a second table.
        choices=[
            (
                "Turntable",
                "turntable",
                "Rotate the model hands-free in the page. Lives on the pivot, "
                "so it survives a push -- the model swaps underneath it and "
                "keeps turning.",
            ),
            (
                "Inspect",
                "inspect",
                "A profiler in the page (Inspect menu, Performance -- or press "
                "i): frame time "
                "against the display's budget -- the headset's own rate in a "
                "session -- CPU and GPU time, draw calls, estimated GPU memory, "
                "what the file's bytes are, and how long it took to download, "
                "parse and first draw. In a headset it shows beside the view "
                "(B or Y).\n\n"
                "GPU memory is the number a GLB's file size does not tell you, "
                "and the one that decides whether this scene needs a KTX2 "
                "texture file type.",
            ),
            (
                "Export Image",
                "snapshot",
                "An Image item in the page's Export menu: saves the current view -- "
                "the camera where you left it, the pose on screen -- as a PNG, "
                "at the view's own size or rendered at 1080p / 1440p / 4K. The "
                "page's overlays are not in it.\n\n"
                "Lands beside the source file when there is one on disk, as "
                "<file>_view_001.png and up; a scene push has none, so the "
                "page downloads it instead.",
            ),
        ],
        section="Viewer",
        tooltip="ES modules the page imports on demand. These change the page "
        "looking at the asset, not the asset itself, so they apply to every "
        "source alike.\n\n"
        "The panel is authoritative: unticking a box turns that script off on "
        "the next push.",
    ),
    "SHARE_VIA": AttributeSpec(
        key="SHARE_VIA",
        label="Sharing",
        kind="choice",
        default="off",
        choices=_share_choices(),
        section="Sharing",
        tooltip="Share the preview at a link, through the provider picked here.\n\n"
        "Picking one brings the link up at once, copies it, and checks it "
        "opens from outside, the way a guest's browser reaches it -- a link "
        "no one else can open is said in red, and checked again until it "
        "opens. Each scene the Source Files row's + adds is shared at a link "
        "of its own. It then stays up "
        "across pushes, and every push logs it -- a guest's page picks each push "
        "up by itself, so the link is the same one each time. Off takes it down. "
        "The row's option box has Share Now (also a retry), Copy Link, Test "
        "Link, Copy Scene Link, Stop Sharing and Remember Sharing. It starts "
        "Off each session -- a link is a door to this machine, and it opens "
        "only when asked -- unless Remember Sharing keeps it: then it comes "
        "back as left and the link opens with the first push, never with the "
        "panel. A preset never carries it, and Reset to Defaults leaves it as "
        "it is.\n\n"
        "A share is a link anyone can open in a browser -- desktop, phone, or "
        "a standalone headset, which gets its VR button because the link is "
        "HTTPS. It is VIEW-ONLY and LIVE: every push reaches it, and nothing a "
        "guest does writes to this machine. Each guest downloads the model and "
        "renders it on their own device; this machine only serves files.",
        # A switch, not a setting: a preset loaded with it on would open a
        # public link unasked, and one saved with it on reopens it on every load.
        preset=False,
    ),
    "SHARE_PRIVATE": AttributeSpec(
        key="SHARE_PRIVATE",
        label="Private Link",
        kind="bool",
        default=False,
        section="Sharing",
        tooltip="Give every share a fresh random link: the provider's address "
        "plus a secret path (https://<name>/<16 random characters>/), and "
        "nothing outside that path opens.\n\n"
        "The link is good for one share: the next has another, and the last "
        "one opens nothing -- send a link for one review and it stops working "
        "when you share again. Cloudflare's address is random each share "
        "already; Tailscale's is your machine's name for good, and this is "
        "what makes its link disposable.\n\n"
        "Changing it while sharing re-shares at once, with a new link. A "
        "private share keeps no stable alias (PYTHONTK_PREVIEW_ALIAS): a "
        "redirect that never changes would be a lasting door to every link.",
    ),
}


class Parameters(ParamRegistry):
    """The WebXR Preview panel's registry, declared as data (:class:`uitk.bridge.ParamRegistry`).

    Handed to the slot as its ``params_module``: :data:`PARAMS` plus
    ``defaults`` (the panel gates its rows by source, not by a template).
    """

    PARAMS = PARAMS
