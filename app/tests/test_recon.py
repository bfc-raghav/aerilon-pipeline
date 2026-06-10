import json
import os
import socket
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from recon import safety  # noqa: E402
from recon.detector import SimulatedDetector, make_detector  # noqa: E402
from recon.telemetry import TelemetrySender  # noqa: E402
from recon.arduino_link import ArduinoLink, find_arduino_port  # noqa: E402


# --- safety scoring (SAFETY-CRITICAL: exhaustive) ---
def test_empty_scene_is_full_score():
    assert safety.compute_safety_score([]) == 100


def test_one_person_reduces_score():
    dets = [{"label": "person", "confidence": 0.9}]
    assert safety.compute_safety_score(dets) == 70


def test_low_confidence_ignored():
    dets = [{"label": "person", "confidence": 0.1}]
    assert safety.compute_safety_score(dets) == 100


def test_non_person_labels_ignored():
    dets = [{"label": "boat", "confidence": 0.99}]
    assert safety.compute_safety_score(dets) == 100


def test_score_clamped_at_zero():
    dets = [{"label": "person", "confidence": 0.9}] * 10
    assert safety.compute_safety_score(dets) == 0


def test_verdict_bands():
    assert safety.verdict(100) == "USABLE"
    assert safety.verdict(71) == "USABLE"
    assert safety.verdict(70) == "DEGRADED"
    assert safety.verdict(36) == "DEGRADED"
    assert safety.verdict(35) == "BLOCKED"
    assert safety.verdict(0) == "BLOCKED"


def test_verdict_colours_distinct():
    cols = {safety.verdict_colour(v) for v in ("USABLE", "DEGRADED", "BLOCKED")}
    assert len(cols) == 3


# --- detector ---
def test_simulated_detector_cycles():
    d = SimulatedDetector()
    frames = [d.detections() for _ in range(3)]
    assert frames[0] == [] and len(frames[2]) == 2


def test_make_detector_falls_back_in_ci():
    d = make_detector("http://nonexistent:5000/video_feed", "missing.pt")
    assert d.real is False  # no cv2/YOLO here: must simulate, never raise


# --- telemetry (real UDP round-trip on localhost) ---
def test_telemetry_round_trip():
    rx = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    rx.bind(("127.0.0.1", 0))
    rx.settimeout(2)
    port = rx.getsockname()[1]
    tx = TelemetrySender("127.0.0.1", port)
    assert tx.send_status({"verdict": "USABLE", "score": 100})
    data, _ = rx.recvfrom(4096)
    msg = json.loads(data.decode())
    assert msg["verdict"] == "USABLE"
    tx.close()
    rx.close()


# --- arduino link ---
def test_arduino_falls_back_without_hardware():
    link = ArduinoLink()
    # CI has no /dev/ttyACM* — must not raise, must still accept sends
    link.send_verdict("USABLE", 88)
    link.send_verdict("BLOCKED", 10)


def test_port_discovery_returns_none_in_ci():
    assert find_arduino_port() is None
