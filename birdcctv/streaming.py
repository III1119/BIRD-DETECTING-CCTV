"""Video streaming utilities for the bird detecting CCTV."""

from __future__ import annotations

import logging
import time
from collections import Counter
from typing import Callable, Generator, Iterable, List
import threading

import cv2

from .camera import CaptureProtocol
from .detector import BirdDetector, Detection


LOGGER = logging.getLogger(__name__)


class VideoStreamer:
    """Capture frames, run detection, and expose MJPEG-compatible streams."""

    def __init__(
        self,
        capture_factory: Callable[[], CaptureProtocol],
        detector: BirdDetector | None = None,
    ) -> None:
        self.detector = detector
        self._capture_factory = capture_factory
        self.capture = self._open_capture()
        if self.capture is None or not self._is_open(self.capture):
            raise RuntimeError("Unable to open video source")
        self._detections: List[Detection] = []
        self._lock = threading.Lock()
        self._last_timestamp: float | None = None
        self._failure_count: int = 0

    def _open_capture(self) -> CaptureProtocol | None:
        try:
            capture = self._capture_factory()
        except Exception:  # pragma: no cover - runtime safety
            LOGGER.exception("Failed to create capture instance")
            return None
        return capture

    @staticmethod
    def _is_open(capture: CaptureProtocol) -> bool:
        try:
            return bool(capture.isOpened())
        except AttributeError:
            # Picamera2 based capture objects do not expose isOpened, assume True
            return True

    def _update_detections(self, detections: Iterable[Detection]) -> None:
        with self._lock:
            self._detections = list(detections)
            self._last_timestamp = time.time()

    def _encode_frame(self, frame) -> bytes | None:
        success, buffer = cv2.imencode(".jpg", frame)
        if not success:
            return None
        return buffer.tobytes()

    def read(self):
        """Read a single frame from the capture device."""

        if self.capture is None:
            self.capture = self._open_capture()
            if self.capture is None or not self._is_open(self.capture):
                return None, []
        ok, frame = self.capture.read()
        if not ok:
            self._failure_count += 1
            if self._failure_count > 5:
                return None, []
            # Attempt to recover by reopening the capture device once.
            self.release()
            time.sleep(1)
            self.capture = self._open_capture()
            if self.capture is None or not self._is_open(self.capture):
                return None, []
            ok, frame = self.capture.read()
            if not ok:
                return None, []
        else:
            self._failure_count = 0
        detections: List[Detection] = []
        annotated = frame
        if self.detector is not None:
            try:
                annotated, detections = self.detector.detect(frame)
            except Exception:  # pragma: no cover - runtime safety
                LOGGER.exception("Detection failed; continuing with raw frame")
                annotated = frame
                detections = []
        self._update_detections(detections)
        return annotated, detections

    def frames(self) -> Generator[bytes, None, None]:
        """Generate JPEG-encoded frames for MJPEG streaming."""

        while True:
            frame, _ = self.read()
            if frame is None:
                break
            payload = self._encode_frame(frame)
            if payload is None:
                continue
            yield payload

    def mjpeg_stream(self) -> Generator[bytes, None, None]:
        """Yield multipart JPEG payloads for Flask streaming responses."""

        boundary = b"--frame"
        for payload in self.frames():
            yield boundary + b"\r\nContent-Type: image/jpeg\r\n\r\n" + payload + b"\r\n"

    def detection_summary(self) -> dict:
        with self._lock:
            counter = Counter(det.label for det in self._detections)
            return {
                "count": len(self._detections),
                "labels": dict(counter),
                "detections": [
                    {
                        "label": det.label,
                        "confidence": det.confidence,
                        "bbox": det.bbox,
                    }
                    for det in self._detections
                ],
                "last_updated": self._last_timestamp,
            }

    def release(self) -> None:
        if self.capture is not None:
            try:
                opened = self._is_open(self.capture)
            except Exception:  # pragma: no cover - runtime safety
                opened = True
            if opened:
                try:
                    self.capture.release()
                except Exception:  # pragma: no cover - runtime safety
                    LOGGER.exception("Failed to release capture cleanly")
        self.capture = None

    def __del__(self) -> None:  # pragma: no cover - best effort cleanup
        self.release()
