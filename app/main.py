#!/usr/bin/env python3
"""Aerilon companion app — the deliberately tiny payload we update OTA.

Demo trick: the LED ring pattern/colour is driven by app/config/params.yaml.
Change ONE line in config, push to main, watch the drone's LEDs change after
the pipeline + acceptances complete. Code-to-field, visible from the back row.

Falls back to console output when Pi5Neo / SPI hardware isn't present, so the
same app runs on a laptop for development and judging dry-runs.
"""
import argparse
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))


def load_params() -> dict:
    """Minimal YAML-ish loader (key: value lines) — zero dependencies."""
    params = {"led_colour": "0,80,255", "led_pattern": "spin", "led_count": "24",
              "video_url": "http://hack01:5000/video_feed",
              "model_path": "/home/bae/models/yolov8n.pt",
              "telemetry_ip": "192.168.1.108", "telemetry_port": "5005",
              "safety_threshold": "70", "person_penalty": "30",
              "loop_seconds": "0.5"}
    path = os.path.join(HERE, "config", "params.yaml")
    if os.path.exists(path):
        with open(path) as f:
            for line in f:
                line = line.split("#")[0].strip()
                if ":" in line:
                    k, v = line.split(":", 1)
                    params[k.strip()] = v.strip()
    return params


def version() -> str:
    path = os.path.join(HERE, "VERSION")
    return open(path).read().strip() if os.path.exists(path) else "dev"


def get_ring(count: int):
    try:
        from pi5neo import Pi5Neo  # available inside devenv on the Pi
        return Pi5Neo("/dev/spidev0.0", count, 800)
    except Exception:
        return None  # laptop / no hardware


def show_colour(ring, count: int, rgb: tuple) -> None:
    r, g, b = rgb
    if ring:
        ring.fill_strip(r, g, b)
        ring.update_strip()
    else:
        sys.stdout.write(f"\r[sim] LED ring <- ({r},{g},{b})   ")
        sys.stdout.flush()


def run(params: dict) -> None:
    """Recon loop: camera -> safety score -> LED verdict + Arduino + telemetry."""
    sys.path.insert(0, HERE)
    from recon import safety
    from recon.detector import make_detector
    from recon.telemetry import TelemetrySender
    from recon.arduino_link import ArduinoLink

    count = int(params["led_count"])
    ring = get_ring(count)
    det = make_detector(params["video_url"], params["model_path"])
    tel = TelemetrySender(params["telemetry_ip"], params["telemetry_port"])
    ard = ArduinoLink()
    threshold = int(params["safety_threshold"])
    print(f"aerilon-app v{version()} | detector={'real' if det.real else 'sim'} "
          f"| ring={'yes' if ring else 'sim'} | threshold={threshold}")
    while True:
        detections = det.detections()
        score = safety.compute_safety_score(
            detections, person_penalty=int(params["person_penalty"]))
        v = safety.verdict(score, threshold)
        show_colour(ring, count, safety.verdict_colour(v))
        ard.send_verdict(v, score)
        tel.send_status({"version": version(), "score": score,
                         "verdict": v, "detections": len(detections)})
        time.sleep(float(params["loop_seconds"]))


def selfcheck(params: dict) -> int:
    """Health check used by the OTA agent before/after the symlink swap."""
    try:
        assert int(params["led_count"]) > 0
        assert len(params["led_colour"].split(",")) == 3
        # recon stack: importable, scoring sane, config complete
        sys.path.insert(0, HERE)
        from recon import safety
        from recon import detector, telemetry, arduino_link  # noqa: F401
        assert safety.verdict(100) == "USABLE"
        assert safety.verdict(0) == "BLOCKED"
        for key in ("video_url", "model_path", "telemetry_ip", "telemetry_port",
                    "safety_threshold", "person_penalty", "loop_seconds"):
            assert key in params, f"missing config: {key}"
        print(f"selfcheck OK (v{version()})")
        return 0
    except Exception as e:  # noqa: BLE001
        print(f"selfcheck FAILED: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--selfcheck", action="store_true")
    args = ap.parse_args()
    p = load_params()
    sys.exit(selfcheck(p)) if args.selfcheck else run(p)
