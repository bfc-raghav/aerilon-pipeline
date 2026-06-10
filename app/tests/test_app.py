import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import main  # noqa: E402


def test_params_load():
    p = main.load_params()
    assert "led_colour" in p and "led_pattern" in p


def test_colour_is_rgb_triple():
    p = main.load_params()
    parts = p["led_colour"].split(",")
    assert len(parts) == 3
    assert all(0 <= int(x) <= 255 for x in parts)


def test_led_count_positive():
    assert int(main.load_params()["led_count"]) > 0


def test_selfcheck_passes():
    assert main.selfcheck(main.load_params()) == 0


def test_version_returns_string():
    assert isinstance(main.version(), str) and len(main.version()) > 0


def test_get_ring_falls_back_without_hardware():
    # No SPI hardware / pi5neo in CI: must return None, never raise
    assert main.get_ring(24) is None
