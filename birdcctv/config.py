"""Configuration helpers for the bird CCTV application."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Iterable, List, Sequence, Tuple, Union

VideoSource = Union[int, str]


def _parse_camera_driver(value: str | None) -> str:
    if not value:
        return "opencv"
    driver = value.strip().lower()
    if driver in {"opencv", "picamera2"}:
        return driver
    return "opencv"


def _parse_backend(value: str | None) -> str | None:
    if not value:
        return None
    backend = value.strip().lower()
    if backend in {"v4l2", "gstreamer"}:
        return backend
    return None


def _parse_video_source(value: str | None) -> VideoSource:
    if value is None:
        return 0
    value = value.strip()
    if not value:
        return 0
    try:
        return int(value)
    except ValueError:
        return value


def _parse_labels(value: str | None) -> List[str]:
    if not value:
        return ["bird"]
    labels = [item.strip().lower() for item in value.split(",") if item.strip()]
    return labels or ["bird"]


def _parse_float(value: str | None, default: float) -> float:
    if not value:
        return default
    try:
        return float(value)
    except ValueError:
        return default


def _parse_int(value: str | None) -> int | None:
    if not value:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _parse_model_path(value: str | None) -> str | None:
    if value is None:
        return "yolov8n.pt"
    trimmed = value.strip()
    if not trimmed:
        return "yolov8n.pt"
    if trimmed.lower() in {"none", "no", "off", "disable", "disabled"}:
        return None
    return trimmed


def _parse_resolution(value: str | None, default: Tuple[int, int]) -> Tuple[int, int]:
    if not value:
        return default
    trimmed = value.lower().replace("x", " ").replace("*", " ").replace(",", " ")
    parts = [part for part in trimmed.split() if part]
    if len(parts) != 2:
        return default
    try:
        width = int(parts[0])
        height = int(parts[1])
    except ValueError:
        return default
    if width <= 0 or height <= 0:
        return default
    return width, height


def _parse_positive_int(value: str | None, default: int) -> int:
    if not value:
        return default
    try:
        parsed = int(value)
    except ValueError:
        return default
    return parsed if parsed > 0 else default


@dataclass(slots=True)
class AppConfig:
    """Application configuration resolved from environment variables."""

    video_source: VideoSource
    camera_driver: str
    video_backend: str | None
    model_path: str | None
    bird_labels: Sequence[str]
    min_confidence: float
    frame_width: int | None
    picamera_resolution: Tuple[int, int]
    picamera_framerate: int

    @classmethod
    def from_env(cls) -> "AppConfig":
        return cls(
            video_source=_parse_video_source(os.getenv("VIDEO_SOURCE")),
            camera_driver=_parse_camera_driver(os.getenv("CAMERA_DRIVER")),
            video_backend=_parse_backend(os.getenv("VIDEO_BACKEND")),
            model_path=_parse_model_path(os.getenv("MODEL_PATH")),
            bird_labels=_parse_labels(os.getenv("BIRD_LABELS")),
            min_confidence=_parse_float(os.getenv("MIN_CONFIDENCE"), 0.4),
            frame_width=_parse_int(os.getenv("FRAME_WIDTH")),
            picamera_resolution=_parse_resolution(
                os.getenv("PICAMERA_RESOLUTION"), (1280, 720)
            ),
            picamera_framerate=_parse_positive_int(os.getenv("PICAMERA_FPS"), 30),
        )


def labels_to_display(labels: Iterable[str]) -> str:
    """Format labels for display on the dashboard."""

    return ", ".join(sorted({label.title() for label in labels}))
