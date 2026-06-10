"""UDP status reporting to the coordinator laptop (was PIReading.py).
One socket for the process lifetime; structured JSON instead of a hello
string, so the coordinator can actually act on it."""
import json
import logging
import socket

log = logging.getLogger("recon.telemetry")


class TelemetrySender:
    def __init__(self, target_ip: str, target_port: int):
        self.addr = (target_ip, int(target_port))
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def send_status(self, status: dict) -> bool:
        try:
            self.sock.sendto(json.dumps(status).encode(), self.addr)
            return True
        except OSError as e:
            log.warning("telemetry send failed: %s", e)
            return False

    def close(self):
        self.sock.close()
