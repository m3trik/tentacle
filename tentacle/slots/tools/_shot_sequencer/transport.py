# !/usr/bin/python
# coding=utf-8
"""Transport: the playhead, audio scrub and the transport row.

Provides :class:`TransportMixin` -- mixed into
:class:`~.controller.ShotSequencerController`. Moving the playhead moves the
scene's time; scrubbing is made audible the host's way
(``SequencerHost.bind_timeline_audio``: Maya binds the composite audio to the
Time Slider and hands its WAV to the widget's scrub player, Blender turns on
the scene's own audio scrub); the transport row plays through the host's play
controller (``SequencerHost.play_controller``).
"""


class TransportMixin:
    """The playhead, audible scrubbing and the transport button row."""

    def on_playhead_moved(self, frame: float) -> None:
        """Move the scene's time to the widget playhead.

        Audio scrub is the host's (:meth:`_ensure_sound_on_timeline`); this
        mirrors the time value, sub-frames kept: with a fractional snap the
        playhead would otherwise sit up to half a frame off the time it shows.
        No undo entry: scrubbing is not an edit, and a recorded time change
        would bury the user's edits one Ctrl+Z per playhead move and leave the
        queue top owned by a scrub (``SequencerHost.set_current_time``).
        """
        self._syncing_playhead = True
        try:
            self._ensure_sound_on_timeline()
            self.host.set_current_time(frame)
        finally:
            self._syncing_playhead = False

    def _ensure_sound_on_timeline(self) -> None:
        """Make scrubbing and playback audible.

        The host binds its timeline audio (``SequencerHost.bind_timeline_audio``)
        and names what it bound.  When that comes with a WAV for the widget's
        own scrub player (Maya: drag-scrubbing time emits no audio there), the
        WAV is pushed into it -- once per bound source, so the two stay in
        lockstep without re-reading the path on every scrub step.
        """
        source = self.host.bind_timeline_audio(getattr(self, "_active_sound", "") or "")
        self._active_sound = source
        if not source or getattr(self, "_bound_audio_node", None) == source:
            return  # nothing to scrub, or the player already plays it
        wav_path = self.host.timeline_audio_wav(source)
        if not wav_path:
            return
        widget = self._get_sequencer_widget()
        set_audio = getattr(widget, "set_audio_source", None)
        if set_audio is None:
            return
        if set_audio(wav_path, self.host.scene_fps()):
            self._bound_audio_node = source

    # ---- Transport controls (footer) -------------------------------------

    #: Button edge of the footer transport, in pixels.  Sized so the glyphs
    #: land on the 16px icon grid the rest of uitk draws on (icons are 0.7 of
    #: the button) -- at the old 20px the transport rendered 14px glyphs, a
    #: half-step off every other icon in the panel and small for a control
    #: that gets clicked constantly.
    TRANSPORT_BUTTON_HEIGHT = 23

    def _setup_transport_controls(self) -> None:
        """Install the reusable ``TransportControls`` row on the RIGHT of the
        footer, wired to the host's play controller.

        Frame/key/go-to actions interrupt playback by default (see
        ``TransportControls.interrupt_mode``).  Playhead navigation goes
        through the sequencer widget so scrub audio fires via
        ``playhead_moved``.
        """
        footer = getattr(self.ui, "footer", None)
        if footer is None:
            return

        # Key the rebuild guard off the persistent footer, not this
        # controller's own attr: a slots re-init builds a NEW controller
        # whose _transport_controls is always None, so a per-controller guard
        # never trips and attach_to_footer (append-only) would stack a
        # duplicate row plus a second play controller on every reopen.
        existing = getattr(footer, "_shot_transport_controls", None)
        if existing is not None:
            # Re-init over a live UI: adopt the existing row and repoint its
            # playback AND its range provider at this controller — range_fn
            # is an instance method, and the constructor binding would
            # otherwise keep reading (and keep alive) the retired
            # controller's stale sequencer/mode state.
            existing.set_play_controller(
                self.host.play_controller(before_play=self._ensure_sound_on_timeline)
            )
            existing.set_range_fn(self._playback_range)
            self._transport_controls = existing
            return

        widget = self._get_sequencer_widget()
        if widget is None:
            return

        TransportControls = self.sb.TransportControls
        # The footer grows to fit a taller child (Footer.add_widget), so this
        # is a floor, not a ceiling -- never shrink to the footer's height.
        h = max(footer.height(), self.TRANSPORT_BUTTON_HEIGHT)
        transport = TransportControls(
            sequencer=widget,
            play_controller=self.host.play_controller(
                before_play=self._ensure_sound_on_timeline
            ),
            parent=footer,
            button_height=h,
            interrupt_mode=TransportControls.INTERRUPT_STOP,
            range_fn=self._playback_range,
            button_names=(
                "go_to_start",
                "prev_key",
                "play_back",
                "play_forward",
                "next_key",
                "go_to_end",
            ),
        )
        transport.attach_to_footer(footer, side="right")
        self._transport_controls = transport
        footer._shot_transport_controls = transport

        # Prime the audio binding now so the first scrub produces
        # sound — the widget's built-in audio slot runs before the
        # controller's ``on_playhead_moved``, so without this the first
        # drag fires into an unsourced player.
        try:
            self._ensure_sound_on_timeline()
        except Exception:
            self.logger.debug("audio binding failed", exc_info=True)

    def _playback_range(self) -> tuple:
        """Range the transport's go-to-start / go-to-end buttons target.

        The ACTIVE SHOT wins over the scene's playback range.  Reading the
        scene's range made the two buttons skip the current shot's own
        boundaries whenever the range covered more than that shot — which it
        does in the "adjacent" and "all" view modes, and whenever the
        playback-range mode is "off".  An empty shot has no clips to fall back
        on, so it was the case where the skip was total.

        Falls back to the scene's playback range when no shot is selected.
        """
        if self.sequencer is not None:
            sid = self.active_shot_id
            shot = self.sequencer.shot_by_id(sid) if sid is not None else None
            if shot is not None and shot.end > shot.start:
                return float(shot.start), float(shot.end)
        rng = self.host.playback_range()
        return rng if rng is not None else (1.0, 120.0)
