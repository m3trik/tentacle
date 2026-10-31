# !/usr/bin/python
# coding=utf-8
"""The photogrammetry panels' shared Qt half: the Metashape, RealityCapture and
Brush Splat workflows (``slots/tools/<engine>_workflow.py``).

* :mod:`.panel_slots` -- :class:`PhotogrammetryPanelSlots`, the panels' one base,
  and :class:`FramesSourceMixin`, the frames/video Source row of the image-in two.
* :mod:`.shared_parameters` -- the input pre-processing specs both image-in
  registries lead with (:class:`SharedParams`).
* ``<engine>_parameters.py`` -- each panel's parameter registry.

Private to those three panels. The engines, runners, profile and presets are
extapps' (``extapps.Profile``, ``extapps.MetashapeRunner``, ...).
"""
