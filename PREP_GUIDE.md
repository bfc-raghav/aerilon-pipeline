# Aerilon Release Pipeline — Hackathon Preparation Guide

**Problem 2: push drone-software updates across four partner organisations in days, not weeks.**

**One-line pitch:** a shared CI/CD backbone that turns every code change into a *signed, verifiable release evidence pack*, consumed by four federated acceptance gates — so trust travels as an artifact, not a meeting, and the drone in the field updates itself minutes after the last org signs off.

---

## 1. The system in one diagram

```
 developer push to main
        │
        ▼
 ┌─────────────────────────────┐
 │  CORE PIPELINE (shared)     │  build · unit tests · static analysis
 │  GitHub Actions, reusable   │  (SITL scenarios — stretch goal)
 │  workflow                   │  semantic impact analysis
 └──────────────┬──────────────┘  evidence_pack.json  +  artifact
                │  ed25519-signed, SLSA provenance attached
                ▼
 ┌──────── fan-out: matrix of 4, fail-fast OFF ────────┐
 │ Coastguard │   Power   │ Humanitarian │   Ports     │
 │ OPA policy │ OPA policy│  OPA policy  │ OPA policy  │  ← versioned .rego,
 │ + reviewer │ + reviewer│  + reviewer  │ + reviewer  │    DIFFERENT per org
 └─────┬──────┴─────┬─────┴──────┬───────┴─────┬───────┘
       └─ signed acceptance attestations (one key per org) ─┘
                │
                ▼
 manifest.json {version, sha256, accepted_by:[...]}  ← laptop release server
                │
                ▼
 ┌─────────────────────────────┐      ┌──────────────────────────┐
 │ Pi 5 UPDATE AGENT (drone)   │      │ PROGRAMME-OFFICE         │
 │ poll → verify sig → A/B     │      │ DASHBOARD (read-only)    │
 │ install → health check →    │      │ observes, never approves │
 │ swap symlink │ auto-rollback│      └──────────────────────────┘
 └─────────────────────────────┘
```

Key claims, each mapped to a line of the brief:
- *"arguments about what has really changed"* → semantic impact analysis + signed change record
- *"each org has its own acceptance criteria/sign-off"* → policy-as-code per org + per-org human gate
- *"programme office needs confidence without becoming a bottleneck"* → read-only dashboard; office holds **zero** approval authority
- *"what remains uncertain"* → uncertainties are a **first-class field** in the evidence pack, auto-populated
- *"days not weeks"* → measure it live: commit timestamp → LEDs change on the drone

## 2. Repo contents (this skeleton)

```
.github/workflows/
  release.yml            orchestrator: core → 4-org matrix → dashboard
  core-pipeline.yml      build/test/evidence/sign (reusable)
  org-acceptance.yml     federated gate (reusable; org name is the only input)
policies/org-*/policy.rego   four DIFFERENT acceptance policies (OPA/conftest)
scripts/
  generate_evidence.py   builds evidence_pack.json + SUMMARY.md
  impact_analysis.py     classifies change: parameter/interface/behavioural
  sitl_scenarios.py      PX4 SITL skeleton (stretch goal)
  publish_release.sh     laptop bridge: fetch from GitHub (WAN) → serve to LAN
agent/
  update_agent.py        Pi OTA agent: verify → A/B install → health → rollback
  update-agent.service   systemd unit (agent)
  aerilon-app.service    systemd unit (app, runs ./current symlink)
app/
  main.py                LED-ring demo payload (+ --selfcheck), sim fallback
  config/params.yaml     change ONE line here for the live demo
  interfaces/serial_link.py  tagged SAFETY-CRITICAL; trips Power's policy
  tests/test_app.py      4 unit tests
dashboard/generate_dashboard.py   static HTML status matrix
keys/release-signing.pub.example  sample pubkey (generate your own!)
```

Everything was smoke-tested: evidence generation, impact analysis, dashboard, app selfcheck, and the exact `openssl pkeyutl` ed25519 sign/verify commands all run clean. The pytest suite is trivial but real (run `pytest app/tests` once you have deps installed).

## 3. Pre-event checklist (do at home, ~2 hours)

**GitHub (needs internet) — order matters; secrets/environments BEFORE first push so run #1 succeeds:**
1. Create a **public** repo (public = free Actions minutes + provenance attestation works). Do NOT push yet.
2. Generate keys locally (Git Bash has openssl): `openssl genpkey -algorithm ed25519 -out release-signing.pem` then `openssl pkey -in release-signing.pem -pubout -out keys/release-signing.pub`. Repeat for four org keys. The repo ships a `.gitignore` blocking `*.pem` — only `.pub` files may ever be committed. If a `.pem` ever lands in history on a public repo, treat the key as burned and rotate.
3. Repo → Settings → Secrets → Actions: add `SIGNING_KEY` = full contents of `release-signing.pem`.
4. Repo → Settings → Environments: create `org-coastguard`, `org-power`, `org-humanitarian`, `org-ports` (exact names). On each: Required Reviewer = a different teammate (invite as collaborators first), plus environment secret `ORG_KEY` = that org's private PEM.
5. Now push the skeleton (`git init && git add -A && git commit -m "skeleton (#1)" && git push`). Note the `(#1)` — the Ports policy rejects commits with no issue reference, so keep `(#N)` in commit messages or you'll demo a rejection unintentionally (which is itself a nice demo, but on purpose only).
6. Watch run #1 in the Actions tab; approve all four gates once; download the artifacts and open SUMMARY.md + dashboard.html so you know what judges will see. Then push a trivial second commit — impact analysis diffs against the previous commit, so behaviour is only representative from run #2 onward.
7. Install the `gh` CLI on the laptop, `gh auth login`, and set `REPO=<you>/<repo>` inside `scripts/publish_release.sh` (or export it). Run `./scripts/publish_release.sh fetch` once on WAN to confirm it stages a manifest with the right `accepted_by` list.
8. Known soft spot: the workflow pins conftest v0.56.0 by URL. If that step 404s, swap the version number for the latest on conftest's GitHub releases page — the policies import `rego.v1` so they run on both old and new OPA.

**Pi prep (mirror at home if you have a Pi; otherwise first hour of the event):**
1. `mkdir -p /home/bae/aerilon/{keys,releases,agent}`; copy `agent/update_agent.py` and `keys/release-signing.pub` over (FileZilla, per the guide).
2. Install both systemd units (templates in `agent/`), set `AERILON_SERVER` to your laptop's LAN IP, `AERILON_ORG` to whichever org "owns" your drone. The agent restarts the app via `sudo systemctl`; if the `bae` user lacks passwordless sudo, add: `echo 'bae ALL=(ALL) NOPASSWD: /usr/bin/systemctl' | sudo tee /etc/sudoers.d/bae-systemctl`.
3. Manually drop a v1.0.1 into `releases/`, symlink `current`, start both services. Confirm LEDs run (devenv venv has Pi5Neo).

**Event-day network plan (important — read twice):**
- The drone LAN (`MERCUSYS_FB42_5G`) has **no internet**; GitHub is only reachable on the Vodafone WAN. The laptop bridges them: `./scripts/publish_release.sh fetch` on WAN → switch wifi to LAN → `./scripts/publish_release.sh serve`. Practise the wifi flip; it's 30 seconds but feels like minutes on stage.
- Better: one teammate's laptop lives on WAN (pipeline + approvals), yours lives on LAN (release server + SSH to Pi). Transfer the fetched bundle by USB stick or phone hotspot. Decide this before the demo.
- Full fallback if GitHub/WAN dies: pre-stage a signed v1.0.X bundle on the laptop and run only the LAN half live. The agent's verify/swap/rollback still demos perfectly.

## 4. Demo runbook (~4 minutes, rehearse twice)

1. **Set the scene (20s):** drone on desk, LED ring spinning **blue**. Dashboard on screen: v1.0.6 accepted by all four orgs.
2. **The change (30s):** field operators report blue is invisible in smoke — they need amber. Edit one line of `app/config/params.yaml` (`led_colour: 255,40,0`... adjust to taste), commit with message `amber visibility fix (#17)`, push.
3. **The pipeline (60s, talk over it):** show the Actions graph fan-out. Point at the evidence pack SUMMARY.md: what changed, tests 4/4, coverage, *and the declared uncertainties* — "the system is honest about what it doesn't know."
4. **Federated sign-off (45s):** each teammate approves their org **from their phone** (GitHub mobile app). Show one org's policy file on screen: "Coastguard demands SITL evidence for parameter changes; Humanitarian doesn't — same pipeline, different sovereignty."
5. **Delivery (60s):** run `publish_release.sh fetch`, flip wifi, `serve`. SSH window on the Pi shows the agent log: *signature verified → self-check OK → swap → LIVE*. **The ring turns amber.** Pause. Let it land.
6. **The kicker (20s):** "Commit was at 14:02. The drone changed at 14:09. That chain — change, evidence, four independent sign-offs, cryptographically verified delivery — used to take three weeks of email."
7. **Optional showstopper:** push a deliberately broken build (make `--selfcheck` fail, e.g. `led_count: 0` — note this passes unit tests only if you also skip them, so instead break selfcheck via a bad colour string). Agent installs, health check fails, **auto-rollback**, LEDs stay amber. "Fast *and* safe."

## 5. Presentation structure (8–10 slides)

1. **Title** — team, "Trust as an artifact, not a meeting."
2. **Problem reframed** — quote the brief's four questions (changed / tested / uncertain / ready). State the insight: this is an *evidence federation* problem; CI/CD alone rebuilds the bottleneck digitally.
3. **Architecture** — the diagram above. One slide, big.
4. **Evidence pack** — show real JSON + SUMMARY.md side by side. Highlight `uncertainties` in a callout.
5. **Federation** — two .rego files side by side (Coastguard vs Humanitarian). "Sovereignty preserved: we automated the evidence flow, never the decision."
6. **Zero-trust delivery** — sign at build, verify on the drone, A/B + rollback. The drone trusts a key, not a network.
7. **Demo** (live) — runbook above.
8. **Metrics & exploitation** — DORA lead time weeks→minutes; scales to N orgs by adding one folder + one environment; lineage from certification lifecycle data (DO-178C-style accountability at hackathon weight); judging-criteria mapping (Collaboration = federation model, Innovation = uncertainty-as-evidence + policy-as-code, Closeness to brief = slide 2, Technology = Actions/OPA/ed25519/SLSA/systemd, Exploitation = real multi-org programmes).
9. **Honest limits** — SITL ≠ flight test (and link to Problem 1: our evidence packs are exactly the shared baseline that would fix test drift); key management hand-waved (production: HSM/Sigstore + key rotation); Pixhawk/PX4 firmware deliberately out of scope — companion-computer software only, matching the "don't touch the flight controller" rule and the reality that flight-critical code needs heavier gates.

## 6. Anticipated judge questions

- **"Isn't this just CI/CD?"** — CI/CD answers "does it build and pass?". Ours answers "can four organisations that don't share tooling each make an *independent, accountable* accept decision in minutes?" The pipeline is commodity; the signed evidence pack + federated policy gates are the contribution.
- **"What if one org rejects?"** — `fail-fast: false`: the other three accept and deploy; the manifest's `accepted_by` list means each org's drones only take builds *their* org accepted. Partial rollout is a feature, not a failure.
- **"What about the flight controller?"** — Out of scope by design; we update mission/payload/companion software. Safety-critical flight code needs DO-178C-grade verification; our evidence-pack pattern is the on-ramp to that, not a replacement.
- **"Security of the update path?"** — Artifact is signed at build with a key only the pipeline holds; the drone pins the public key and refuses anything unverified — demoed live if asked (serve a tampered tarball, watch the agent reject it). Production hardening: TLS, Sigstore transparency log, per-org delivery keys, TUF-style metadata.
- **"How does a fifth org join?"** — `mkdir policies/org-newpartner`, write their .rego, create one GitHub Environment, name an approver. Ten minutes. That's the exploitation story.
- **"Connection drops mid-update?"** — Download to staging first; the swap is an atomic symlink replace; rollback restores the previous tree. The drone is never left in a half-updated state.

## 7. Where to spend hackathon hours (priority order)

1. Get the full chain working with real hardware LEDs (½ day).
2. Rehearse the demo + wifi flip until boring.
3. Stretch A: real PX4 SITL scenario in CI (pymavlink takeoff-hold-land) — huge wow if it lands, but time-box it.
4. Stretch B: dashboard auto-published to GitHub Pages.
5. Stretch C: tamper demo (reject a modified artifact live).
