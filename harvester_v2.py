#!/usr/bin/env python3
"""
Apex Harvester v2 — DFW roofing contractor leads, no API key required.
Scrapes public business directories (Yellow Pages) for roofing contractors
in the Dallas-Fort Worth metro. Zero cost, no Google API dependency.

Output: SQLite DB with name, phone, address, city — ready for outreach.
"""
import re, sys, time, json, sqlite3, hashlib, urllib.request, urllib.parse
from pathlib import Path

DB = Path.home() / "workspace/apex-leads-pro/dfw_roofing_leads.db"
CITIES = ["Dallas TX", "Fort Worth TX", "Arlington TX", "Plano TX",
          "Irving TX", "Garland TX", "Frisco TX", "McKinney TX"]
QUERY = "roofing contractor"

HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}

def dedup(phone, name, city):
    return hashlib.md5(f"{phone or name}|{city}".lower().encode()).hexdigest()

def fetch(url, timeout=20):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", errors="ignore")

def scrape_yp(city):
    """BBB.org search: roofing contractors in city. (YP blocks datacenter IPs.)"""
    loc = urllib.parse.quote(city)
    url = f"https://www.bbb.org/search?find_text=roofing&find_loc={loc}"
    leads = []
    try:
        html = fetch(url)
    except Exception as e:
        print(f"  BBB fetch failed for {city}: {str(e)[:80]}", flush=True)
        return leads
    # BBB business cards: name in <a> + phone patterns
    names = re.findall(r'"businessName":"([^"]{3,80})"', html)
    if not names:
        names = re.findall(r'class="[^"]*business-name[^"]*"[^>]*>([^<]{3,80})<', html)
    phones = re.findall(r'\(?\d{3}\)?[-.\s]\d{3}[-.\s]\d{4}', html)
    seen = set()
    for i, name in enumerate(names):
        name = name.strip()
        if name in seen or len(name) < 3:
            continue
        seen.add(name)
        phone = phones[i] if i < len(phones) else ""
        digits = re.sub(r"\D", "", phone)
        if len(digits) == 11 and digits.startswith("1"):
            digits = digits[1:]
        phone_fmt = f"({digits[:3]}) {digits[3:6]}-{digits[6:]}" if len(digits) == 10 else phone
        leads.append({"name": name, "phone": phone_fmt,
                      "address": "", "city": city.split()[0]})
    return leads

def main():
    conn = sqlite3.connect(DB)
    conn.execute("""CREATE TABLE IF NOT EXISTS leads
        (id INTEGER PRIMARY KEY, name TEXT, phone TEXT, address TEXT,
         rating REAL DEFAULT 0, city TEXT, dedup_hash TEXT UNIQUE, ingested_at TEXT)""")
    conn.commit()
    total_new = 0
    for city in CITIES:
        leads = scrape_yp(city)
        new = 0
        for l in leads:
            if not l["name"]:
                continue
            cur = conn.execute(
                "INSERT OR IGNORE INTO leads (name,phone,address,city,dedup_hash,ingested_at) VALUES (?,?,?,?,?,datetime('now'))",
                (l["name"], l["phone"], l["address"], l["city"],
                 dedup(l["phone"], l["name"], l["city"])))
            new += cur.rowcount
        conn.commit()
        total = conn.execute("SELECT COUNT(*) FROM leads").fetchone()[0]
        print(f"  {city}: {len(leads)} scraped, {new} new (db total: {total})", flush=True)
        total_new += new
        time.sleep(2)
    conn.close()
    print(f"DONE new={total_new} db={DB}", flush=True)

main()
