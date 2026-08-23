# !/usr/bin/python
# coding=utf-8
"""Text the animation panel's Maya and Blender forks say identically.

Both forks drive the SAME ``ui/animation.ui``, so a control that means the same
thing in each has to be described the same way — and 30 of them were, in two
copies that nothing stopped from drifting apart. They had already started to:
Scale Keys' speed tooltip said "one shared pace" in one fork and "one pace" in
the other, and *Fit Playback Range* carried two descriptions of one command.
The copies live here instead, per the root standard's "unify over duplicate" --
its vendored-copy exception covers layers that CANNOT import each other, which
these two can.

Anything a fork does DIFFERENTLY stays in that fork. Roughly 45 controls
qualify: Blender says "Dope Sheet / Graph Editor" where Maya says "Channel
Box", ``stagger_keys`` auto-enables Group Overlapping in mayatk but not in
blendertk, and the two Optimize passes disagree about what counts as static.
Hoisting those would trade an accurate tooltip for a shorter file.

Entries are ``TooltipFormat.fmt`` **keyword specs**, not rendered strings: a
slot module may not import uitk (``test_dcc_invariants.TestSlotImportDiscipline``
— the Switchboard is the only sanctioned route), so each call site renders its
own with ``self.sb.tooltip.fmt(**self.TIP_X)``. The three one-line entries are
plain text and are used as-is. That also keeps this module dependency-free.

This mixin deliberately defines NO widget-named slots (see the DEFAULT_INCLUDE
note in ``tentacle/__init__.py``): it carries text, so mixing it in cannot
capture another panel's ``tb###``.
"""


class AnimationMixin:
    """Shared tooltip text for ``slots/{maya,blender}/animation.py``."""

    TIP_GOTO_FRAME = {
        "title": "Frame",
        "body": "The frame to move the playhead to — read as an absolute "
        "frame number or as an offset, per <b>Mode</b> below.",
        "notes": ["Ignored while a Snap mode other than None is selected."],
    }

    TIP_GOTO_MODE = {
        "title": "Mode",
        "body": "How the <b>Frame</b> value above is interpreted.",
        "bullets": [
            "<b>Absolute</b> — jump to that frame number.",
            "<b>Relative</b> — offset from the current frame "
            "(the default, so <code>1</code> steps forward one frame).",
        ],
    }

    TIP_GOTO_SINGLE_FRAME = {
        "title": "Toggle Single Frame",
        "body": "Park <b>Frame</b> at a one-frame nudge "
        "(<code>+1</code>/<code>-1</code>, sign following its current "
        "value) and restore the previous value when unchecked.",
    }

    TIP_GOTO_INVERT = {
        "title": "Invert",
        "body": "Reverse the direction of the move.",
        "bullets": [
            "<b>Snap: None</b> — flips the sign of <b>Frame</b>, "
            "turning a <code>+N</code> nudge into <code>-N</code>. "
            "The box also tracks the sign, so typing a negative "
            "Frame ticks it on.",
            "<b>Snap: Floor / Ceil</b> — swaps the two, so a "
            "round-down snap rounds up instead.",
        ],
        "notes": [
            "No effect under Preferred, Aggressive or Nearest — "
            "those modes have no direction to reverse."
        ],
    }

    TIP_INVERT_MODE = {
        "title": "Mode",
        "body": "Which axis of the curve gets mirrored.",
        "bullets": [
            "<b>X</b> — mirror key <i>times</i>: the animation plays backwards.",
            "<b>Y</b> — mirror key <i>values</i> about <b>Pivot</b>: "
            "the motion flips, the timing is untouched.",
            "<b>X &amp; Y</b> — both.",
        ],
        "notes": ["The Time controls apply to X; Pivot applies to Y."],
    }

    TIP_INVERT_PIVOT = {
        "title": "Pivot",
        "body": "The value each key is mirrored about in <b>Y</b> mode: a "
        "key at <code>pivot + n</code> lands at <code>pivot - n</code>.",
        "notes": ["Unused in X mode — there are no values to flip there."],
    }

    TIP_INVERT_RELATIVE = {
        "title": "Relative",
        "bullets": [
            "<b>On</b> (default) — <b>Time</b> is an offset from the "
            "last key, so the copy lands just past the source.",
            "<b>Off</b> — <b>Time</b> is an absolute frame number.",
        ],
        "notes": ["Ignored while Time is Auto — nothing is copied there."],
    }

    TIP_STAGGER_GROUP_OVERLAPPING = {
        "title": "Group Overlapping",
        "body": "Objects whose key ranges overlap are re-timed together as "
        "one block, so their relative timing survives the stagger.",
        "notes": [
            "Without this, every object is staggered on its own and "
            "objects animated in sync come apart."
        ],
    }

    TIP_STAGGER_INVERT = {
        "title": "Invert",
        "body": "Reverse the order the objects are laid out in, so the last "
        "one goes first.",
    }

    TIP_TRANSFER_RELATIVE = {
        "title": "Relative",
        "bullets": [
            "<b>On</b> (default) — the source's motion is offset onto "
            "each target's own current values, so a target keeps the "
            "pose it is standing in and inherits the movement.",
            "<b>Off</b> — targets are keyed to the source's literal "
            "values and snap onto it.",
        ],
    }

    TIP_REMOVE_INTERMEDIATE = {
        "title": "Remove Intermediate Keys",
        "body": "Flip the button from adding keys to stripping them.",
        "bullets": [
            "<b>Off</b> (default) — sample new keys across the window "
            "at <b>Percent</b> density.",
            "<b>On</b> — cut every key strictly inside the window, "
            "leaving only its two end keys.",
        ],
        "notes": ["<b>Percent</b> greys out — it only drives the add pass."],
    }

    TIP_VISIBILITY_OFFSET = {
        "title": "Offset",
        "body": "Nudge the chosen frame(s) — positive moves the key later, "
        "negative earlier.",
        "notes": [
            "Stacks with <b>Before Start</b> / <b>After End</b>, which "
            "already step one frame out on their own."
        ],
    }

    TIP_VISIBILITY_GROUP_OVERLAPPING = {
        "title": "Group Overlapping",
        "body": "Objects whose key ranges overlap are keyed against the "
        "group's combined range instead of each object's own.",
        "notes": [
            "Use it when several objects make up one prop, so the whole "
            "prop appears and disappears together."
        ],
    }

    TIP_SNAP_METHOD = {
        "title": "Method",
        "body": "How a fractional key time is rounded.",
        "sections": [
            (
                "Plain rounding",
                [
                    "<b>Nearest</b> — to the closest whole frame.",
                    "<b>Floor</b> / <b>Ceil</b> — always down / always up.",
                    "<b>Half Up</b> — .5 always rounds up.",
                ],
            ),
            (
                "Clean-number snapping",
                [
                    "<b>Preferred</b> — snap to a round number only "
                    "when very close (24 &#8594; 25, 99 &#8594; 100).",
                    "<b>Aggressive Preferred</b> — snap from farther "
                    "out (48 &#8594; 50, 73 &#8594; 75).",
                ],
            ),
        ],
        "notes": [
            "The clean-number modes move keys that were already on "
            "whole frames — reach for them to tidy timing, not just to "
            "de-fraction it."
        ],
    }

    TIP_DELETE_TIME_RANGE = {
        "title": "Time Range",
        "body": "Which keys, relative to the playhead, are deleted.",
        "rows": [
            ("All Keyframes", "every key on the selection"),
            ("Current Frame", "only keys sitting on the playhead"),
            ("Before Current", "everything earlier, playhead kept"),
            ("Before &amp; Current", "everything earlier, playhead too"),
            ("After Current", "everything later, playhead kept"),
            ("Current &amp; After", "everything later, playhead too"),
        ],
    }

    TIP_SELECT_TIME_RANGE = {
        "title": "Time Range",
        "body": "Which keys, relative to the playhead, get selected.",
        "rows": [
            ("All", "every key on the selection"),
            ("Current", "only keys sitting on the playhead"),
            ("Before / After", "everything earlier / later, playhead kept"),
            ("Before|Current", "everything earlier, playhead too"),
            ("After|Current", "everything later, playhead too"),
            ("Range", "the explicit Start/End frames below"),
        ],
    }

    TIP_SCALE_GROUPING = {
        "title": "Grouping",
        "body": "What shares one pivot and one time range.",
        "bullets": [
            "<b>Single Group</b> — the whole selection scales about one "
            "pivot, so the objects keep their offsets from each other.",
            "<b>Per Object Pivots</b> — each object (or, with Split Static "
            "Segments, each segment) scales about its own start.",
            "<b>Group Overlaps</b> — objects whose key ranges overlap share "
            "a group pivot; unrelated objects scale independently.",
        ],
    }

    TIP_SCALE_RELATIVE_ABSOLUTE = {
        "title": "Relative / Absolute",
        "body": "Whether <b>Factor</b> is a change or a destination.",
        "rows": [
            (
                "Uniform · Relative",
                "a multiplier &mdash; 2.0 is twice as long",
            ),
            (
                "Uniform · Absolute",
                "a target duration in frames",
            ),
            (
                "Speed · Relative",
                "a speed multiplier &mdash; 2.0 is twice as fast",
            ),
            (
                "Speed · Absolute",
                "a target speed in units per frame",
            ),
        ],
        "notes": [
            "Switching Mode resets this to that mode's usual choice "
            "&mdash; Relative for Uniform, Absolute for Speed."
        ],
    }

    TIP_SCALE_SAMPLES = {
        "title": "Samples",
        "body": "How many points along each block are evaluated to measure "
        "the distance it travels.",
        "bullets": [
            "<b>Higher</b> — truer distance on a curving or "
            "stop-and-start path, but slower.",
            "<b>Lower</b> — faster, at the cost of cutting corners.",
        ],
        "notes": [
            "64 is a good balance; 32-128 covers most work.",
            "Speed modes only — greyed out under Uniform, which needs "
            "no motion measurement.",
        ],
    }

    TIP_SCALE_GROUP_TOUCHING = {
        "title": "Group Touching",
        "body": "Widen grouping to blocks that merely <i>touch</i> — one "
        "ending on the exact frame the next begins — not just blocks "
        "that overlap.",
        "bullets": [
            "<b>Off</b> (default) — touching blocks scale separately.",
            "<b>On</b> — they are merged and scale about one pivot.",
        ],
        "notes": [
            "Only bites under <b>Group Overlaps</b>; the other two "
            "grouping modes already decide their own blocks."
        ],
    }

    TIP_REPAIR_TIME_THRESHOLD = {
        "title": "Time Threshold",
        "body": "The largest frame number treated as plausible. A key "
        "beyond it, in either direction, counts as corrupted.",
        "notes": ["Raise it if a legitimately long scene trips the check."],
    }

    TIP_REPAIR_VALUE_THRESHOLD = {
        "title": "Value Threshold",
        "body": "The largest key value treated as plausible. Anything "
        "beyond it counts as corrupted.",
        "notes": [
            "Scene-scale dependent — a rig working in millimetres "
            "needs a higher ceiling than one working in metres."
        ],
    }

    TIP_INFO_SORT_BY_TIME = {
        "title": "Sort by Time",
        "body": "Order the report by each entry's start frame instead of "
        "alphabetically by object name — reads as a running order "
        "rather than an index.",
    }

    TIP_INFO_IGNORE_HOLDS = {
        "title": "Ignore Holds",
        "body": "Whether a static hold at either end counts as part of an "
        "object's animation.",
        "bullets": [
            "<b>On</b> (default) — ranges report where the object is "
            "actually <i>moving</i>.",
            "<b>Off</b> — leading and trailing holds are folded into "
            "the range, matching the raw key extents.",
        ],
    }

    TIP_OPTIMIZE_REMOVE_FLAT_KEYS = {
        "title": "Remove Flat Keys",
        "body": "Thin out runs of keys that all hold the same value, "
        "keeping the two that bound the hold.",
        "notes": [
            "The timing is unchanged — the hold still starts and ends "
            "where it did, with fewer keys spelling it out."
        ],
    }

    TIP_SCALE_FACTOR_UNIFORM = {
        "title": "Factor (Uniform mode)",
        "body": "How the block is stretched in time — read per "
        "<b>Relative / Absolute</b> below.",
        "sections": [
            (
                "Relative — a multiplier",
                [
                    "<b>1.0</b> — no change.",
                    "<b>0.5</b> — half as long, so it plays twice as fast.",
                    "<b>2.0</b> — twice as long, so it plays half as fast.",
                ],
            ),
            (
                "Absolute — a target duration",
                [
                    "The block is scaled to span exactly this many frames, "
                    "whatever it spanned before.",
                ],
            ),
        ],
    }

    TIP_SCALE_FACTOR_SPEED = {
        "title": "Speed (Speed mode)",
        "body": "The block is retimed until its sampled world-space motion "
        "hits this speed; the new duration is distance &#247; speed.",
        "sections": [
            (
                "Absolute — a target speed",
                [
                    "In units per frame. <b>5.0</b> retimes every block to "
                    "travel 5 units each frame, so objects that move "
                    "different distances end up moving at one shared pace.",
                ],
            ),
            (
                "Relative — a speed multiplier",
                [
                    "<b>2.0</b> makes each block twice as fast as it "
                    "already was, keeping their relative pacing.",
                ],
            ),
        ],
    }

    TIP_GOTO_SET_TO_CURRENT = "Write the current frame into the Frame field above."

    TIP_SELECT_RANGE_START = "First frame of the window, in Range mode."

    TIP_SELECT_RANGE_END = "Last frame of the window, in Range mode."
