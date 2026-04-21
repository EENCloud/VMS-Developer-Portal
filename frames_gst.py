"""
RTSP frame decoder using GStreamer.
Connects to the camera's live stream and yields frames as numpy arrays.

cv2 is used only for display (imshow) and saving (imwrite).
All stream decoding goes through GStreamer pipelines.
"""
from __future__ import annotations

import time
from collections.abc import Generator
from dataclasses import dataclass
from typing import Callable

import gi
gi.require_version("Gst", "1.0")
from gi.repository import Gst

import cv2
import numpy as np

Gst.init(None)

_NS = Gst.SECOND  # nanoseconds per second (1_000_000_000)


# ---------------------------------------------------------------------------
# Timing dataclass
# ---------------------------------------------------------------------------

@dataclass
class FrameTiming:
    """Timing information for a single decoded frame."""
    stream_pos_ms: float    # PTS from the stream — ms since the pipeline started
    received_at: float      # wall-clock time (time.time()) when frame was pulled
    stream_opened_at: float # wall-clock time when the pipeline started playing

    @property
    def estimated_capture_time(self) -> float:
        """Best-effort wall-clock time the frame was generated at the camera."""
        return self.stream_opened_at + self.stream_pos_ms / 1000.0

    @property
    def latency_ms(self) -> float:
        """Milliseconds between estimated frame capture and local receipt."""
        return (self.received_at - self.estimated_capture_time) * 1000.0


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _build_pipeline(rtsp_url: str, ntp_sync: bool = False) -> Gst.Pipeline:
    ntp_opts = "ntp-sync=true" if ntp_sync else ""
    desc = (
        f'rtspsrc location="{rtsp_url}" protocols=tcp latency=0 {ntp_opts} '
        f'! decodebin '
        f'! videoconvert '
        f'! video/x-raw,format=BGR '
        f'! appsink name=sink emit-signals=false sync=false'
    )
    return Gst.parse_launch(desc)


def _pull_bgr(
    sink: Gst.Element, dims: list
) -> tuple[np.ndarray | None, int]:
    """
    Pull one sample from an appsink element.

    Returns (frame, pts_ns). (None, CLOCK_TIME_NONE) = end-of-stream.
    (None, pts_ns) with pts_ns != CLOCK_TIME_NONE = transient failure, skip.
    """
    sample = sink.emit("pull-sample")
    if sample is None:
        return None, Gst.CLOCK_TIME_NONE

    buf = sample.get_buffer()
    pts_ns = buf.pts

    if dims[0] is None:
        s = sample.get_caps().get_structure(0)
        dims[0] = s.get_value("width")
        dims[1] = s.get_value("height")

    try:
        ok, mi = buf.map(Gst.MapFlags.READ)
    except (ValueError, TypeError):
        return None, pts_ns
    if not ok:
        return None, pts_ns
    try:
        frame = np.frombuffer(mi.data, np.uint8).reshape((dims[1], dims[0], 3)).copy()
    except (ValueError, TypeError):
        frame = None
    finally:
        buf.unmap(mi)

    if frame is None:
        return None, pts_ns
    return frame, pts_ns


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def iter_frames(
    rtsp_url: str,
    on_frame: Callable[[np.ndarray, int], bool] | None = None,
) -> Generator[np.ndarray, None, None]:
    """
    Connect to an RTSP stream and yield decoded frames as BGR numpy arrays.

    Args:
        rtsp_url: Full RTSP URL (including access_token param).
        on_frame: Optional callback(frame, frame_number) -> bool.
                  Return False from the callback to stop iteration.

    Yields:
        numpy.ndarray: BGR image frames, shape (H, W, 3).
    """
    pipeline = _build_pipeline(rtsp_url)
    pipeline.set_state(Gst.State.PLAYING)
    sink = pipeline.get_by_name("sink")
    dims: list = [None, None]
    frame_number = 0

    try:
        while True:
            frame, pts_ns = _pull_bgr(sink, dims)
            if frame is None:
                if pts_ns == Gst.CLOCK_TIME_NONE:
                    break
                continue
            frame_number += 1
            if on_frame is not None and on_frame(frame, frame_number) is False:
                break
            yield frame
    finally:
        pipeline.set_state(Gst.State.NULL)


def iter_frames_timed(
    rtsp_url: str,
) -> Generator[tuple[np.ndarray, FrameTiming], None, None]:
    """
    Like iter_frames, but yields (frame, FrameTiming) pairs.

    Yields:
        (numpy.ndarray, FrameTiming): BGR frame and its timing metadata.
    """
    pipeline = _build_pipeline(rtsp_url)
    pipeline.set_state(Gst.State.PLAYING)
    sink = pipeline.get_by_name("sink")
    dims: list = [None, None]
    stream_opened_at = time.time()

    try:
        while True:
            frame, pts_ns = _pull_bgr(sink, dims)
            received_at = time.time()
            if frame is None:
                if pts_ns == Gst.CLOCK_TIME_NONE:
                    break
                continue
            timing = FrameTiming(
                stream_pos_ms=pts_ns / 1e6 if pts_ns != Gst.CLOCK_TIME_NONE else 0.0,
                received_at=received_at,
                stream_opened_at=stream_opened_at,
            )
            yield frame, timing
    finally:
        pipeline.set_state(Gst.State.NULL)


def _ntp_capture_unix(
    buf: Gst.Buffer,
    pts_ns: int,
    pipeline: Gst.Pipeline,
    ntp_caps: "Gst.Caps",
    ntp_unix_delta: int,
) -> float | None:
    """Return Unix capture timestamp from NTP metadata, or None if not yet available."""
    try:
        meta = buf.get_reference_timestamp_meta(ntp_caps)
        if meta is not None:
            return meta.timestamp / _NS - ntp_unix_delta
    except Exception:
        pass
    if pts_ns not in (0, Gst.CLOCK_TIME_NONE):
        base_time = pipeline.get_base_time()
        if base_time not in (0, Gst.CLOCK_TIME_NONE):
            candidate = (pts_ns + base_time) / _NS
            if candidate > 946_684_800:
                return candidate
    return None


def iter_frames_ntp(
    rtsp_url: str,
) -> Generator[tuple[np.ndarray, float | None, float], None, None]:
    """
    Yield (frame, capture_unix, received_at) using true NTP wall-clock time.

    Sets ntp-sync=True and add-reference-timestamp-meta=True on the internal
    rtpbin via the rtspsrc new-manager signal.

    capture_unix is derived from GstReferenceTimestampMeta on the buffer when
    available (most reliable), or falls back to (pts_ns + base_time) / 1e9
    once GStreamer has NTP-calibrated the pipeline clock.

    capture_unix is None until the first RTCP SR arrives.

    Yields:
        (frame, capture_unix, received_at)
        - frame:        BGR numpy array (H, W, 3)
        - capture_unix: Unix timestamp of camera capture, or None if no SR yet.
        - received_at:  time.time() when the frame was decoded locally.
    """
    _NTP_UNIX_DELTA = 2_208_988_800  # seconds: NTP epoch (1900) → Unix epoch (1970)

    desc = (
        f'rtspsrc name=src location="{rtsp_url}" protocols=tcp latency=0 '
        f'! decodebin ! videoconvert ! video/x-raw,format=BGR '
        f'! appsink name=sink emit-signals=false sync=false'
    )
    pipeline = Gst.parse_launch(desc)
    src = pipeline.get_by_name("src")
    _ntp_caps = Gst.Caps.from_string("timestamp/x-ntp")

    def _on_new_manager(rtspsrc, manager):
        for prop in ("ntp-sync", "add-reference-timestamp-meta"):
            try:
                manager.set_property(prop, True)
            except Exception:
                pass

    src.connect("new-manager", _on_new_manager)
    pipeline.set_state(Gst.State.PLAYING)
    sink = pipeline.get_by_name("sink")
    dims: list = [None, None]

    try:
        while True:
            sample = sink.emit("pull-sample")
            if sample is None:
                break

            buf = sample.get_buffer()
            pts_ns = buf.pts
            received_at = time.time()

            if dims[0] is None:
                s = sample.get_caps().get_structure(0)
                dims[0] = s.get_value("width")
                dims[1] = s.get_value("height")

            try:
                ok, mi = buf.map(Gst.MapFlags.READ)
            except (ValueError, TypeError):
                continue
            if not ok:
                continue
            try:
                frame = np.frombuffer(mi.data, np.uint8).reshape((dims[1], dims[0], 3)).copy()
            except (ValueError, TypeError):
                frame = None
            finally:
                buf.unmap(mi)

            if frame is None:
                continue

            yield frame, _ntp_capture_unix(buf, pts_ns, pipeline, _ntp_caps, _NTP_UNIX_DELTA), received_at
    finally:
        pipeline.set_state(Gst.State.NULL)


def display(rtsp_url: str, window_title: str = "EEN Live Stream") -> None:
    """
    Open an OpenCV window and display the live stream until 'q' is pressed.

    Args:
        rtsp_url:     Full RTSP URL (including access_token param).
        window_title: Title of the display window.
    """
    print("Press 'q' in the window to quit.")
    for frame in iter_frames(rtsp_url):
        cv2.imshow(window_title, frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break
    cv2.destroyAllWindows()


def save_snapshot(rtsp_url: str, output_path: str = "snapshot.jpg") -> str:
    """
    Grab a single frame from the stream and save it as an image file.

    Args:
        rtsp_url:    Full RTSP URL (including access_token param).
        output_path: File path to write (JPEG, PNG, etc. — inferred from extension).

    Returns:
        The output_path that was written.
    """
    for frame in iter_frames(rtsp_url):
        cv2.imwrite(output_path, frame)
        print(f"Snapshot saved to {output_path}")
        return output_path
    raise RuntimeError("No frame received from stream.")
