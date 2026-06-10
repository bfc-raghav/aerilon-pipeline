#!/usr/bin/env bash
# Run on the LAPTOP (Git Bash on Windows works). Bridges the two event networks:
#   WAN (Vodafone hub, internet)  -> where GitHub lives
#   LAN (MERCUSYS_FB42_5G)        -> where the drones live
# Usage:
#   ./scripts/publish_release.sh fetch    # on WAN: pull latest completed run
#   ./scripts/publish_release.sh serve    # on LAN: serve it to the drones
set -euo pipefail
MODE="${1:-serve}"
RELEASE_DIR="${RELEASE_DIR:-$HOME/aerilon-releases}"
REPO="${REPO:-yourteam/aerilon-pipeline}"   # <-- set me or export REPO=...

PY=python3; command -v python3 >/dev/null 2>&1 || PY=python

if [ "$MODE" = "fetch" ]; then
  rm -rf "$RELEASE_DIR"; mkdir -p "$RELEASE_DIR/_dl"
  RUN_ID=$(gh run list --repo "$REPO" --workflow release.yml \
            --status completed --limit 1 --json databaseId \
            --jq '.[0].databaseId')
  [ -n "$RUN_ID" ] || { echo "no completed release runs found"; exit 1; }
  echo ">> Downloading ALL artifacts from run $RUN_ID"
  gh run download "$RUN_ID" --repo "$REPO" --dir "$RELEASE_DIR/_dl"
  # gh creates one subfolder per artifact:
  #   _dl/release-candidate/{dist/...,evidence_pack.json,...}
  #   _dl/acceptance-<org>/acceptance-<org>.json
  cp "$RELEASE_DIR"/_dl/release-candidate/dist/aerilon-app-*.tar.gz* "$RELEASE_DIR/"
  cp "$RELEASE_DIR"/_dl/release-candidate/evidence_pack.json "$RELEASE_DIR/" 2>/dev/null || true

  ACCEPTED=""
  for d in "$RELEASE_DIR"/_dl/acceptance-*; do
    [ -d "$d" ] || continue
    org="${d##*/acceptance-}"
    ACCEPTED="$ACCEPTED\"$org\","
  done
  ACCEPTED="[${ACCEPTED%,}]"

  ART=$(basename "$(ls "$RELEASE_DIR"/aerilon-app-*.tar.gz)")
  VERSION=$(echo "$ART" | sed 's/aerilon-app-//; s/.tar.gz//')
  SHA=$("$PY" -c "import hashlib,sys;print(hashlib.sha256(open(sys.argv[1],'rb').read()).hexdigest())" "$RELEASE_DIR/$ART")
  cat > "$RELEASE_DIR/manifest.json" <<JSON
{ "version": "$VERSION",
  "artifact": "$ART",
  "sha256": "$SHA",
  "accepted_by": $ACCEPTED }
JSON
  echo ">> Staged v$VERSION, accepted_by=$ACCEPTED"
  echo ">> Now switch wifi to MERCUSYS_FB42_5G and run: $0 serve"

elif [ "$MODE" = "serve" ]; then
  echo ">> Serving $RELEASE_DIR on :8000 — drones poll http://<this-laptop-ip>:8000"
  cd "$RELEASE_DIR" && "$PY" -m http.server 8000
fi
