#!/usr/bin/env python3
"""Send v2 template emails. Usage: send_batch.py <db> <trade_label>"""
import subprocess, sqlite3, time, sys
DB, TRADE = sys.argv[1], sys.argv[2]
conn = sqlite3.connect(DB, timeout=30)
conn.execute("CREATE TABLE IF NOT EXISTS sent_log (email TEXT PRIMARY KEY, sent_at TEXT)")
has_trade = conn.execute("PRAGMA table_info(leads)").fetchall()
cols = [c[1] for c in has_trade]
if 'trade' in cols:
    leads = conn.execute("""SELECT name, email, city, trade FROM leads WHERE email != ''
                            AND email NOT IN (SELECT email FROM sent_log) ORDER BY trade, city""").fetchall()
    get = lambda r: (r[0], r[1], r[2], r[3])
else:
    leads = conn.execute("""SELECT name, email, city FROM leads WHERE email != ''
                            AND email NOT IN (SELECT email FROM sent_log) ORDER BY city""").fetchall()
    get = lambda r: (r[0], r[1], r[2], TRADE)
print(f"{DB}: {len(leads)} to send", flush=True)
sent = 0
for r in leads:
    name, email, city, trade = get(r)
    subject = f"Exclusive {city} {trade} leads — $20 trial"
    body = (f"Hi {name} — quick one. I'm Gary with Apex Leads.\n"
            f"We generate exclusive {trade} leads in {city}: one buyer per lead, never resold, never shared.\n\n"
            f"$20 trial — 1 verified homeowner lead, exclusive to you:\n"
            f"https://buy.stripe.com/fZudRba635ae22vgGFd7q0p\n\n"
            f"If it converts, we talk volume. Details: https://apexleads.biz\n\n"
            f"Gary\nApex Leads")
    try:
        p = subprocess.run(["hatch_gws_cli", "gmail", "+send", "--to", email,
                            "--subject", subject, "--body", body],
                           capture_output=True, text=True, timeout=60)
        if p.returncode == 0:
            sent += 1
            conn.execute("INSERT OR IGNORE INTO sent_log VALUES (?, datetime('now'))", (email,))
            conn.commit()
        else:
            print(f"FAIL {email}: {p.stderr[:80]}", flush=True)
    except Exception as e:
        print(f"ERR {email}: {str(e)[:80]}", flush=True)
    time.sleep(3)
print(f"{DB} DONE sent={sent}", flush=True)
