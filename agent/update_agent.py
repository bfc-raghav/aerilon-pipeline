#!/usr/bin/env python3
"""Aerilon OTA update agent — runs on the drone's Pi 5 companion computer.

Loop:
  1. Poll a release server for manifest.json
  2. If a newer accepted version exists: download artifact + signature
  3. Verify sha256 AND ed25519 signature against the pinned public key
     (the drone trusts the KEY, not the network — zero-trust delivery)
  4. Install into releases/<version>/  (A/B style; 'current' is a symlink)
  5. Run the new build's self-check
  6. Atomically flip the symlink, restart the app service
  7. Post-swap health check; on ANY failure, roll the symlink back

No third-party Python deps: signature verification shells out to openssl,
which is preinstalled on Raspberry Pi OS. Run under systemd (see
update-agent.service) so it survives reboots and restarts on failure.

Manifest format served at  http://<server>/manifest.json :
{
  "version": "1.0.42",
  "artifact": "aerilon-app-1.0.42.tar.gz",
  "sha256": "<hex>",
  "accepted_by": ["coastguard", "power", "humanitarian", "ports"]
}
Artifact + "<artifact>.sig" must sit beside the manifest.
"""
import hashlib
import json
import logging
import os
import shutil
import subprocess
import sys
import tarfile
import time
import urllib.request

# ---- configuration (env-overridable) ---------------------------------------
SERVER = os.environ.get("AERILON_SERVER", "http://192.168.1.50:8000")
HOME = os.environ.get("AERILON_HOME", "/home/bae/aerilon")
PUBKEY = os.path.join(HOME, "keys", "release-signing.pub")
RELEASES = os.path.join(HOME, "releases")
CURRENT = os.path.join(HOME, "current")          # symlink -> releases/<ver>
APP_SERVICE = os.environ.get("AERILON_APP_SERVICE", "aerilon-app.service")
MY_ORG = os.environ.get("AERILON_ORG", "coastguard")  # which org owns THIS drone
POLL_SECONDS = int(os.environ.get("AERILON_POLL", "10"))

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [update-agent] %(message)s")
log = logging.getLogger()


def http_get(path: str) -> bytes:
    with urllib.request.urlopen(f"{SERVER}/{path}", timeout=10) as r:
        return r.read()


def current_version() -> str:
    try:
        return os.path.basename(os.readlink(CURRENT)).strip()
    except OSError:
        return "none"


def verify_signature(artifact_path: str, sig_path: str) -> bool:
    res = subprocess.run(
        ["openssl", "pkeyutl", "-verify", "-pubin", "-inkey", PUBKEY,
         "-rawin", "-in", artifact_path, "-sigfile", sig_path],
        capture_output=True, text=True,
    )
    return res.returncode == 0


def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def systemctl(action: str) -> bool:
    try:
        return subprocess.run(["sudo", "systemctl", action, APP_SERVICE]).returncode == 0
    except FileNotFoundError:
        log.warning("systemctl/sudo unavailable (dev machine?) — skipping service %s", action)
        return False


def health_check(version_dir: str) -> bool:
    """Ask the build to prove it can start. Extend with real checks
    (camera reachable, serial link to Arduino up, flask answering)."""
    res = subprocess.run(
        [sys.executable, os.path.join(version_dir, "app", "main.py"), "--selfcheck"],
        capture_output=True, text=True, timeout=30,
    )
    if res.returncode != 0:
        log.error("Self-check failed: %s", res.stderr.strip())
    return res.returncode == 0


def install(manifest: dict) -> None:
    ver = manifest["version"]
    staging = os.path.join(HOME, "staging")
    shutil.rmtree(staging, ignore_errors=True)
    os.makedirs(staging, exist_ok=True)

    art = os.path.join(staging, manifest["artifact"])
    sig = art + ".sig"
    with open(art, "wb") as f:
        f.write(http_get(manifest["artifact"]))
    with open(sig, "wb") as f:
        f.write(http_get(manifest["artifact"] + ".sig"))

    # --- trust gates, in order ---
    if sha256(art) != manifest["sha256"]:
        raise RuntimeError("sha256 mismatch — corrupt or tampered download")
    if not verify_signature(art, sig):
        raise RuntimeError("SIGNATURE INVALID — refusing unsigned software")
    log.info("v%s: integrity + provenance verified", ver)

    target = os.path.join(RELEASES, ver)
    shutil.rmtree(target, ignore_errors=True)
    os.makedirs(target, exist_ok=True)
    with tarfile.open(art) as t:
        t.extractall(target)

    if not health_check(target):
        raise RuntimeError("new build failed pre-swap self-check")

    # --- atomic swap with rollback ---
    previous = os.path.realpath(CURRENT) if os.path.islink(CURRENT) else None
    tmp_link = CURRENT + ".tmp"
    if os.path.lexists(tmp_link):
        os.remove(tmp_link)
    os.symlink(target, tmp_link)
    os.replace(tmp_link, CURRENT)
    systemctl("restart")
    time.sleep(3)

    if health_check(os.path.realpath(CURRENT)):
        log.info("v%s LIVE on this drone", ver)
        return

    log.error("post-swap health check FAILED — rolling back")
    if previous:
        os.remove(CURRENT)
        os.symlink(previous, CURRENT)
        systemctl("restart")
        log.info("rolled back to %s", os.path.basename(previous))
    raise RuntimeError(f"v{ver} rolled back")


def main():
    os.makedirs(RELEASES, exist_ok=True)
    log.info("agent up | org=%s | server=%s | running=%s",
             MY_ORG, SERVER, current_version())
    while True:
        try:
            manifest = json.loads(http_get("manifest.json"))
            new, cur = manifest.get("version"), current_version()
            if new and new != cur:
                if MY_ORG in manifest.get("accepted_by", []):
                    log.info("v%s available and accepted by %s (running %s) — updating",
                             new, MY_ORG, cur)
                    install(manifest)
                else:
                    log.info("v%s available but NOT yet accepted by %s — holding",
                             new, MY_ORG)
        except Exception as e:  # noqa: BLE001 — agent must never die
            log.warning("cycle error: %s", e)
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    main()
