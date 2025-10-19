"""Camera adapters for different capture backends."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Protocol, Tuple

import cv2

LOGGER = logging.getLogger(__name__)

try:  # pragma: no cover - optional dependency
    from picamera2 import Picamera2  # type: ignore
except ImportError:  # pragma: no cover - optional dependency
    Picamera2 = None  # type: ignore[assignment]


class CaptureProtocol(Protocol):
    """Minimal protocol required by :class:`birdcctv.streaming.VideoStreamer`."""

    def read(self) -> tuple[bool, object]:
        ...

    def release(self) -> None:
        ...

    def isOpened(self) -> bool:
        ...


@dataclass
class OpenCVCapture:
    """Wrapper around ``cv2.VideoCapture`` with an optional backend flag."""

    source: int | str
    backend: str | None = None

    def __post_init__(self) -> None:
        if self.backend == "v4l2":
            self._capture = cv2.VideoCapture(self.source, cv2.CAP_V4L2)
        elif self.backend == "gstreamer":
            self._capture = cv2.VideoCapture(self.source, cv2.CAP_GSTREAMER)
        else:
            self._capture = cv2.VideoCapture(self.source)

    def read(self) -> tuple[bool, object]:
        return self._capture.read()

    def release(self) -> None:
        if self._capture.isOpened():
            self._capture.release()

    def isOpened(self) -> bool:
        return self._capture.isOpened()


class PiCameraCapture:
    """Capture frames using the Raspberry Pi "Picamera2" library."""

    def __init__(
        self,
        resolution: Tuple[int, int] = (1280, 720),
        framerate: int = 30,
    ) -> None:
        if Picamera2 is None:
            raise RuntimeError(
                "Picamera2 library is not installed. Install it with "
                "'sudo apt install -y python3-picamera2' on Raspberry Pi OS."
            )
        self._resolution = resolution
        self._framerate = framerate
        self._opened = False
        self._camera = Picamera2()
        config = self._camera.create_video_configuration(
            main={"size": resolution, "format": "RGB888"}
        )
        self._camera.configure(config)
        try:
            self._camera.set_controls({"FrameRate": framerate})
        except Exception:  # pragma: no cover - depends on driver support
            LOGGER.debug("Picamera2 framerate control not supported; continuing")
        self._camera.start()
        self._opened = True

    def read(self) -> tuple[bool, object]:
        if not self._opened:
            return False, None
        try:
            frame = self._camera.capture_array()
        except Exception:  # pragma: no cover - runtime safety
            LOGGER.exception("Failed to capture frame from Picamera2")
            return False, None
        if frame is None:
            return False, None
        # Picamera2 returns RGB frames; convert to OpenCV's BGR for consistency.
        bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        return True, bgr

    def release(self) -> None:
        if self._opened:
            try:
                self._camera.stop()
            except Exception:  # pragma: no cover - runtime safety
                LOGGER.exception("Failed to stop Picamera2 cleanly")
            self._opened = False

    def isOpened(self) -> bool:
        return self._opened


def create_capture(
    driver: str,
    source: int | str,
    backend: str | None,
    resolution: Tuple[int, int],
    framerate: int,
) -> CaptureProtocol:
    """Factory that instantiates the appropriate capture backend."""

    driver = driver.lower()
    if driver == "picamera2":
        LOGGER.info(
            "Using Picamera2 driver with resolution %sx%s @ %sfps",
            resolution[0],
            resolution[1],
            framerate,
        )
        return PiCameraCapture(resolution=resolution, framerate=framerate)
    if driver != "opencv":
        LOGGER.warning("Unknown camera driver '%s', falling back to OpenCV", driver)
    return OpenCVCapture(source=source, backend=backend)
