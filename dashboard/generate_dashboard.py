#!/usr/bin/env python3
"""Programme-office dashboard: confidence WITHOUT becoming a bottleneck.

Reads evidence_pack.json + any acceptance-<org>.json files in the working
directory and renders a single static HTML status matrix. The programme
office observes; it never approves. Open dashboard.html full-screen as the
closing visual of the demo.
"""
import argparse
import glob
import json
import os
from datetime import datetime, timezone

ORGS = ["coastguard", "power", "humanitarian", "ports"]

CSS = """
body{font-family:system-ui,sans-serif;background:#10141c;color:#e8eaf0;
     margin:40px}
h1{font-weight:600} .sub{color:#8a93a6;margin-bottom:28px}
table{border-collapse:collapse;width:100%;font-size:15px}
th,td{padding:12px 16px;text-align:left;border-bottom:1px solid #232a38}
th{color:#8a93a6;font-weight:500}
.ok{color:#3ddc84;font-weight:600}.wait{color:#f5c33b}.no{color:#ff6b6b}
.badge{background:#1b2230;border-radius:6px;padding:2px 8px;font-size:13px}
.unc{background:#1b2230;border-left:3px solid #f5c33b;padding:12px 16px;
     margin-top:24px;border-radius:0 6px 6px 0}
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", required=True)
    ap.add_argument("--out", default="dashboard.html")
    args = ap.parse_args()

    evidence = {}
    if os.path.exists("evidence_pack.json"):
        evidence = json.load(open("evidence_pack.json"))

    accepted = {}
    for f in glob.glob("acceptance*.json"):
        try:
            a = json.load(open(f))
            accepted[a["org"]] = a
        except (json.JSONDecodeError, KeyError):
            continue

    rows = []
    for org in ORGS:
        if org in accepted:
            a = accepted[org]
            status = f'<span class="ok">ACCEPTED</span>'
            detail = f'{a.get("approver","?")} · {a.get("timestamp","")[:16]}'
        else:
            status = '<span class="wait">AWAITING SIGN-OFF</span>'
            detail = "policy passed · human gate open"
        rows.append(f"<tr><td>Aerilon {org.title()}</td><td>{status}</td>"
                    f"<td class='badge'>{detail}</td></tr>")

    t = evidence.get("tests", {})
    unc = evidence.get("uncertainties", [])
    html = f"""<!doctype html><meta charset="utf-8">
<title>Aerilon Release Status</title><style>{CSS}</style>
<h1>Release v{args.version}</h1>
<p class="sub">Generated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}
 · change: {evidence.get('change',{}).get('message','—')}
 · tests {t.get('total',0)-t.get('failed',0)}/{t.get('total',0)}
 · coverage {evidence.get('coverage',{}).get('percent','—')}%</p>
<table><tr><th>Organisation</th><th>Status</th><th>Detail</th></tr>
{''.join(rows)}</table>
<div class="unc"><b>Declared uncertainties ({len(unc)})</b><br>
{'<br>'.join('• ' + u for u in unc) or 'none'}</div>
"""
    with open(args.out, "w") as f:
        f.write(html)
    print(f"dashboard written: {args.out}")


if __name__ == "__main__":
    main()
