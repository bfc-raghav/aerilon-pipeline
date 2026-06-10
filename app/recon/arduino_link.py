"""Serial link to the Arduino MEGA (was SafetyCalculation.py's I/O half).
Uses the contract constants from app/interfaces/serial_link.py — changing
that contract trips the Power org's interface policy, by design.
Lazy connection + console fallback: import-safe everywhere."""
import glob
import logging
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from interfaces import serial_link  # noqa: E402  (contract: BAUD, message format)

log = logging.getLogger("recon.arduino")


def find_arduino_port():
    ports = glob.glob("/dev/ttyACM*") + glob.glob("/dev/ttyUSB*")
    return ports[0] if ports else None


class ArduinoLink:
    def __init__(self):
        self.ser = None
        port = find_arduino_port()
        if port is None:
            log.warning("no Arduino found — console fallback")
            return
        try:
            import serial  # lazy: pyserial only needed on the Pi
            import time
            self.ser = serial.Serial(port, serial_link.BAUD, timeout=1)
            time.sleep(2)  # allow Arduino reset
            log.info("Arduino on %s @ %d", port, serial_link.BAUD)
        except Exception as e:  # noqa: BLE001
            log.warning("Arduino unavailable (%s) — console fallback", e)

    def send(self, line: str) -> None:
        msg = (line.strip() + "\n").encode()
        if self.ser:
            self.ser.write(msg)
        else:
            log.info("[sim-arduino] %s", line.strip())

    def send_verdict(self, verdict: str, score: int) -> None:
        self.send("SAFE" if verdict == "USABLE" else "UNSAFE")
        self.send(f"SCORE:{score}")
