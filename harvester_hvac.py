#!/usr/bin/env python3
"""
Apex Harvester v3 — DFW HVAC contractors WITH email addresses.
BBB directory -> business website -> email scrape. Zero cost, no API keys.
Output: dfw_hvac_leads.db (name, phone, email, website, city).
"""
import re, sys, time, sqlite3, hashlib, urllib.request, urllib.parse
from pathlib import Path

DB = Path.home() / "workspace/apex-leads-pro/dfw_hvac_leads.db"
CITIES = ["Dallas TX", "Fort Worth TX", "Arlington TX", "Plano TX", "Irving TX"]
HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}

EMAIL_RE = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')
BAD_EMAIL = re.compile(r'\.(png|jpg|jpeg|gif|css|js)$|example\.|sentry|wixpress|schema', re.I)

def fetch(url, timeout=15):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        ct = r.headers.get("Content-Type", "")
        if "html" not in ct and "text" not in ct:
            return ""
        return r.read().decode("utf-8", errors="ignore")

def scrape_bbb(city):
    loc = urllib.parse.quote(city)
    url = f"https://www.bbb.org/search?find_text=hvac&find_loc={loc}"
    try:
        html = fetch(url)
    except Exception as e:
        print(f"  BBB fail {city}: {str(e)[:60]}", flush=True)
        return []
    names = re.findall(r'"businessName":"([^"]{3,80})"', html)
    if not names:
        names = re.findall(r'class="[^"]*business-name[^"]*"[^>]*>([^<]{3,80})<', html)
    phones = re.findall(r'\(?\d{3}\)?[-.\s]\d{3}[-.\s]\d{4}', html)
    leads, seen = [], set()
    for i, name in enumerate(names):
        name = re.sub(r'<[^>]+>', '', name).strip()
        if name in seen or len(name) < 3:
            continue
        seen.add(name)
        phone = phones[i] if i < len(phones) else ""
        digits = re.sub(r"\D", "", phone)
        if len(digits) == 11 and digits.startswith("1"):
            digits = digits[1:]
        phone_fmt = f"({digits[:3]}) {digits[3:6]}-{digits[6:]}" if len(digits) == 10 else phone
        leads.append({"name": name, "phone": phone_fmt, "city": city.split()[0]})
    return leads

def find_website(name, city):
    """DuckDuckGo html search -> first plausible business site."""
    q = urllib.parse.quote(f"{name} {city} TX HVAC")
    try:
        html = fetch(f"https://html.duckduckgo.com/html/?q={q}")
    except Exception:
        return ""
    for m in re.finditer(r'uddg=([^"&]+)', html):
        url = urllib.parse.unquote(m.group(1))
        if not url.startswith("http"):
            continue
        host = urllib.parse.urlparse(url).netloc.lower()
        if any(d in host for d in ["bbb.org", "yelp.com", "facebook.com", "yellowpages",
                                    "angi.com", "homeadvisor", "thumbtack", "duckduckgo"]):
            continue
        return url.split("?")[0]
    return ""

def find_email(site_url):
    """Scrape homepage (+ contact page) for an email address."""
    for url in [site_url, site_url.rstrip("/") + "/contact"]:
        try:
            html = fetch(url)
        except Exception:
            continue
        for em in EMAIL_RE.findall(html):
            em = em.lower().strip(".")
            if BAD_EMAIL.search(em):
                continue
            return em, url
        time.sleep(1)
    return "", site_url

def dedup(email, phone, name):
    return hashlib.md5(f"{email or phone or name}".lower().encode()).hexdigest()

def main():
    conn = sqlite3.connect(DB)
    conn.execute("""CREATE TABLE IF NOT EXISTS leads
        (id INTEGER PRIMARY KEY, name TEXT, phone TEXT, email TEXT,
         website TEXT, city TEXT, dedup_hash TEXT UNIQUE, ingested_at TEXT)""")
    conn.commit()
    for city in CITIES:
        leads = scrape_bbb(city)
        print(f"{city}: {len(leads)} businesses found", flush=True)
        new = 0
        for l in leads:
            site = find_website(l["name"], l["city"])
            email, _ = find_email(site) if site else ("", "")
            if not email:
                time.sleep(1)
                continue
            cur = conn.execute(
                "INSERT OR IGNORE INTO leads (name,phone,email,website,city,dedup_hash,ingested_at) VALUES (?,?,?,?,?,?,datetime('now'))",
                (l["name"], l["phone"], email, site, l["city"],
                 dedup(email, l["phone"], l["name"])))
            new += cur.rowcount
            conn.commit()
            print(f"  + {l['name'][:35]:35} {email}", flush=True)
            time.sleep(2)
        total = conn.execute("SELECT COUNT(*) FROM leads").fetchone()[0]
        print(f"  {city}: {new} with email (db total: {total})", flush=True)
        time.sleep(2)
    conn.close()
    print("DONE", flush=True)

main()
