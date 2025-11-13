"""Flask application that exposes the smart CCTV endpoints."""

from __future__ import annotations

import atexit
from datetime import datetime
from flask import Flask, Response, jsonify, render_template

from .camera import create_capture
from .config import AppConfig, labels_to_display
from .detector import BirdDetector
from .streaming import VideoStreamer


def create_app() -> Flask:
    """Create and configure the Flask application."""

    config = AppConfig.from_env()
    app = Flask(__name__)

    detector = None
    if config.model_path is not None:
        detector = BirdDetector(
            model_path=config.model_path,
            bird_labels=config.bird_labels,
            min_confidence=config.min_confidence,
            frame_width=config.frame_width,
        )
    streamer = VideoStreamer(
        lambda: create_capture(
            driver=config.camera_driver,
            source=config.video_source,
            backend=config.video_backend,
            resolution=config.picamera_resolution,
            framerate=config.picamera_framerate,
        ),
        detector,
    )

    atexit.register(streamer.release)

    @app.before_first_request
    def _log_configuration():
        app.logger.info("Video source: %s", config.video_source)
        app.logger.info("Tracking labels: %s", labels_to_display(config.bird_labels))
        if detector is None:
            app.logger.info("Model: disabled (stream only mode)")
        else:
            app.logger.info("Model: %s", config.model_path)

    def _format_timestamp(timestamp: float | None) -> str:
        if not timestamp:
            return "N/A"
        return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")

    @app.route("/")
    def index():
        summary = streamer.detection_summary()
        return render_template(
            "index.html",
            summary=summary,
            label_names=labels_to_display(config.bird_labels),
            last_updated_text=_format_timestamp(summary.get("last_updated")),
            detection_enabled=detector is not None,
        )

    @app.route("/video_feed")
    def video_feed():
        response = Response(
            streamer.mjpeg_stream(),
            mimetype="multipart/x-mixed-replace; boundary=frame",
        )
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response

    @app.route("/api/detections")
    def api_detections():
        summary = streamer.detection_summary()
        return jsonify(summary)

    @app.route("/healthz")
    def healthz():
        summary = streamer.detection_summary()
        return jsonify({
            "status": "ok",
            "camera_active": summary["last_updated"] is not None,
            "labels": labels_to_display(config.bird_labels),
            "detection_enabled": detector is not None,
        })

    return app
