# !/usr/bin/python
# coding=utf-8
"""The Shot Sequencer panel's Qt half: its controller and one mixin per concept.

Private to :mod:`tentacle.slots.tools.shot_sequencer`; the shot engine is
pythontk's, and each host's side -- its ``ShotSequencer``, ``SegmentCollector``,
``GraphSync`` and ``SequencerHost`` -- is its library's, reached through
``Slots.tk``.
"""
