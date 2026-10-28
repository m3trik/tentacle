# !/usr/bin/python
# coding=utf-8
"""The Shot Sequencer panel's Qt half: its controller, one mixin per concept,
and the shot layer it adds to uitk's timeline (``shot_layer``).

Private to :mod:`tentacle.slots.tools.shot_sequencer`; the shot engine is
pythontk's, and each host's side -- its ``ShotSequencer``, ``SegmentCollector``,
``GraphSync`` and ``SequencerHost`` -- is its library's, reached through
``Slots.tk``.
"""
