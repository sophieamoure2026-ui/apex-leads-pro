#!/usr/bin/env python3
"""
Apex Leads — DFW roofing SMS blast via Twilio.
Reads creds from .env.live in this directory (TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN).
Reads leads from dfw_roofing_leads.csv (name,phone,city).

Usage:  python3 apex_sms_blast.py
Optional: TWILIO_FROM_NUMBER env to pick the sending number; otherwise uses
the first SMS-capable number on the account.

Logs every send to sms_blast_log.csv. Safe to re-run — skips numbers already sent.
"""
import csv, os, sys, time, base64, json, urllib.request, urllib.parse
from pathlib import Path

HERE = Path(__file__).parent
CSV = HERE / "dfw_roofing_leads.csv"
LOG = HERE / "sms_blast_log.csv"

# --- creds from .env.live (never printed) ---
creds = {}
env_path = HERE / ".env.live"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            creds[k.strip()] = v.strip().strip('"').strip("'")
SID = creds.get("TWILIO_ACCOUNT_SID", "")
TOK = creds.get("TWILIO_AUTH_TOKEN", "")
if not SID or not TOK:
    sys.exit("Missing TWILIO_ACCOUNT_SID / TWILIO_AUTH_TOKEN in .env.live")

AUTH = base64.b64encode(f"{SID}:{TOK}".encode()).decode()

def twilio(method, path, data=None):
    url = f"https://api.twilio.com/2010-04-01{path}"
    body = urllib.parse.urlencode(data).encode() if data else None
    req = urllib.request.Request(url, data=body, method=method,
                                 headers={"Authorization": f"Basic {AUTH}"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read())

# --- pick from number ---
FROM = os.getenv("TWILIO_FROM_NUMBER", "")
if not FROM:
    nums = twilio("GET", f"/Accounts/{SID}/IncomingPhoneNumbers.json?PageSize=20")
    for n in nums.get("incoming_phone_numbers", []):
        if n.get("capabilities", {}).get("sms"):
            FROM = n["phone_number"]
            break
if not FROM:
    sys.exit("No SMS-capable Twilio number found. Set TWILIO_FROM_NUMBER.")
print(f"Sending from {FROM}")

# --- already-sent numbers (re-run safe) ---
sent = set()
if LOG.exists():
    with open(LOG) as f:
        sent = {row["to"] for row in csv.DictReader(f)}

TEMPLATE = ("Hi {name}, Gary with Apex Leads. We generate exclusive roofing leads "
            "in DFW — one buyer per lead, never resold. $20 trial: 1 verified homeowner "
            "lead, yours only. Worth a quick call? Reply YES for details.")

def e164(phone):
    d = "".join(c for c in phone if c.isdigit())
    if len(d) == 11 and d.startswith("1"):
        d = d[1:]
    return f"+1{d}" if len(d) == 10 else None

# --- load leads ---
with open(CSV) as f:
    leads = [r for r in csv.DictReader(f) if r["phone"]]

logf = open(LOG, "a", newline="")
logw = csv.DictWriter(logf, fieldnames=["to", "name", "city", "status", "sid"])
if not sent:
    logw.writeheader()

ok = fail = skip = 0
for l in leads:
    to = e164(l["phone"])
    if not to:
        continue
    if to in sent:
        skip += 1
        continue
    msg = TEMPLATE.format(name=l["name"].split()[0] if l["name"] else "there")
    try:
        resp = twilio("POST", f"/Accounts/{SID}/Messages.json",
                      {"From": FROM, "To": to, "Body": msg})
        logw.writerow({"to": to, "name": l["name"], "city": l["city"],
                       "status": resp.get("status"), "sid": resp.get("sid")})
        ok += 1
        print(f"  ✓ {l['name'][:30]:30} {to}")
    except Exception as e:
        logw.writerow({"to": to, "name": l["name"], "city": l["city"],
                       "status": f"ERROR {str(e)[:80]}", "sid": ""})
        fail += 1
        print(f"  ✗ {l['name'][:30]:30} {str(e)[:60]}")
    logf.flush()
    time.sleep(2)  # carrier-friendly pacing

logf.close()
print(f"\nDone: {ok} sent, {fail} failed, {skip} already sent. Log: {LOG}")
