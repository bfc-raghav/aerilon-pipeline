"""Person/obstacle detection from the drone camera stream.

Wraps the team's YOLO approach behind an interface with a simulated
fallback, so CI and laptops never need cv2/ultralytics/torch installed.
IMPORTANT for the field: yolov8n.pt MUST already exist at model_path on
the Pi — ultralytics auto-downloads on first use and the drone LAN has
no internet. Pre-stage it (see PREP_GUIDE).
"""
import logging

log = logging.getLogger("recon.detector")


class SimulatedDetector:
    """Deterministic stand-in when cv2/YOLO/camera are unavailable."""
    real = False

    def __init__(self, scenario=None):
        # cycle: clear -> one person -> crowd -> clear ...
        self._frames = scenario or [[],
                                    [{"label": "person", "confidence": 0.9}],
                                    [{"label": "person", "confidence": 0.8},
                                     {"label": "person", "confidence": 0.7}]]
        self._i = 0

    def detections(self) -> list[dict]:
        out = self._frames[self._i % len(self._frames)]
        self._i += 1
        return out

    def close(self):
        pass


class YoloDetector:
    real = True

    def __init__(self, stream_url: str, model_path: str = "yolov8n.pt"):
        import cv2                      # lazy: only on the Pi
        from ultralytics import YOLO
        self._cv2 = cv2
        self.model = YOLO(model_path)   # must be a local file in the field
        self.cap = cv2.VideoCapture(stream_url)
        if not self.cap.isOpened():
            raise RuntimeError(f"cannot open stream {stream_url}")

    def detections(self) -> list[dict]:
        ret, frame = self.cap.read()
        if not ret:
            return []
        results = self.model(frame, verbose=False)
        out = []
        for box in results[0].boxes:
            cls = int(box.cls[0])
            out.append({"label": self.model.names[cls],
                        "confidence": float(box.conf[0])})
        return out

    def close(self):
        self.cap.release()


def make_detector(stream_url: str, model_path: str):
    """Try real hardware path; fall back to simulation. Never raises."""
    try:
        d = YoloDetector(stream_url, model_path)
        log.info("YOLO detector live on %s", stream_url)
        return d
    except Exception as e:  # ImportError, stream failure, missing model
        log.warning("falling back to simulated detector: %s", e)
        return SimulatedDetector()
