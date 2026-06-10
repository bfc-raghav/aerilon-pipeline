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
    params = {"led_colour": "0,80,255", "led_pattern": "spin", "led_count": "24"}
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


def run(params: dict) -> None:
    count = int(params["led_count"])
    r, g, b = (int(x) for x in params["led_colour"].split(","))
    ring = get_ring(count)
    print(f"aerilon-app v{version()} | pattern={params['led_pattern']} "
          f"colour=({r},{g},{b}) | hardware={'yes' if ring else 'simulated'}")
    i = 0
    while True:
        if ring:
            ring.clear_strip()
            if params["led_pattern"] == "spin":
                ring.set_led_color(i % count, r, g, b)
            else:  # 'solid'
                ring.fill_strip(r, g, b)
            ring.update_strip()
        else:
            sys.stdout.write(f"\r[sim] LED {i % count:02d} <- ({r},{g},{b})  ")
            sys.stdout.flush()
        i += 1
        time.sleep(0.05)


def selfcheck(params: dict) -> int:
    """Health check used by the OTA agent before/after the symlink swap."""
    try:
        assert int(params["led_count"]) > 0
        assert len(params["led_colour"].split(",")) == 3
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
