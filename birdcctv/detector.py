"""Object detection utilities for identifying birds in video frames."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Sequence, Tuple
import threading

import cv2

try:
    from ultralytics import YOLO
except ImportError as exc:  # pragma: no cover - handled at runtime
    raise RuntimeError(
        "The 'ultralytics' package is required for bird detection. Install it via"
        " 'pip install ultralytics'."
    ) from exc


@dataclass(slots=True)
class Detection:
    """Container for a single detection result."""

    label: str
    confidence: float
    bbox: Tuple[int, int, int, int]


class BirdDetector:
    """YOLOv8 based bird detector."""

    def __init__(
        self,
        model_path: str,
        bird_labels: Sequence[str],
        min_confidence: float = 0.4,
        frame_width: int | None = None,
    ) -> None:
        self.model = YOLO(model_path)
        self.bird_labels = {label.lower() for label in bird_labels}
        self.min_confidence = min_confidence
        self.frame_width = frame_width
        self._predict_lock = threading.Lock()

    def _prepare_frame(self, frame):
        if self.frame_width and frame.shape[1] != self.frame_width:
            ratio = self.frame_width / frame.shape[1]
            new_height = int(frame.shape[0] * ratio)
            frame = cv2.resize(frame, (self.frame_width, new_height))
        return frame

    def detect(self, frame) -> tuple:
        """Run the detection model on a frame.

        Returns a tuple containing the annotated frame and a list of detections.
        """

        frame = self._prepare_frame(frame)
        with self._predict_lock:
            results = self.model(frame, verbose=False)[0]

        detections: List[Detection] = []
        annotated = frame.copy()
        for box in results.boxes:
            cls_id = int(box.cls[0]) if box.cls is not None else -1
            label = results.names.get(cls_id, str(cls_id)) if hasattr(results, "names") else str(cls_id)
            confidence = float(box.conf[0]) if box.conf is not None else 0.0
            if label.lower() not in self.bird_labels:
                continue
            if confidence < self.min_confidence:
                continue

            x1, y1, x2, y2 = [int(v) for v in box.xyxy[0].tolist()]
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(annotated.shape[1], x2), min(annotated.shape[0], y2)
            detections.append(Detection(label=label, confidence=confidence, bbox=(x1, y1, x2, y2)))
            cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(
                annotated,
                f"{label} {confidence:.2f}",
                (x1, max(15, y1 - 10)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 255, 0),
                2,
            )

        return annotated, detections

    def warmup(self, frame) -> None:
        """Run a single detection without using the result to prepare the model."""

        self.detect(frame)
