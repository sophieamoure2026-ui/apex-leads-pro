#!/usr/bin/env python3
"""
Apex Harvester v4 — DEEP DFW roofing harvest.
More cities + BBB pagination + email extraction. Roofing only.
Output: dfw_roofing_leads.db (adds email + website columns).
"""
import re, time, sqlite3, hashlib, urllib.request, urllib.parse
from pathlib import Path

DB = Path.home() / "workspace/apex-leads-pro/dfw_roofing_leads.db"
CITIES = ["Dallas TX", "Fort Worth TX", "Arlington TX", "Plano TX", "Irving TX",
          "Garland TX", "Frisco TX", "McKinney TX", "Mesquite TX", "Richardson TX",
          "Carrollton TX", "Lewisville TX", "Denton TX", "Grand Prairie TX",
          "Allen TX", "Flower Mound TX", "Rowlett TX", "Euless TX"]
PAGES = 3
HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
EMAIL_RE = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')
BAD = re.compile(r'\.(png|jpg|jpeg|gif|css|js)$|example\.|sentry|wixpress|schema|godaddy|domain\.com$|user@domain', re.I)

def fetch(url, timeout=15):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", errors="ignore")

def scrape_bbb(city, page):
    loc = urllib.parse.quote(city)
    url = f"https://www.bbb.org/search?find_text=roofing&find_loc={loc}&page={page}"
    try:
        html = fetch(url)
    except Exception as e:
        print(f"  BBB fail {city} p{page}: {str(e)[:50]}", flush=True)
        return []
    names = re.findall(r'"businessName":"([^"]{3,80})"', html)
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

def find_email(name, city):
    """Search business website via BBB detail link is unreliable; use name+city search on bing html."""
    q = urllib.parse.quote(f'"{name}" {city} TX roofing')
    try:
        html = fetch(f"https://www.bing.com/search?q={q}&format=rss")
    except Exception:
        return "", ""
    urls = re.findall(r'<link>(https?://[^<]+)</link>', html)
    for url in urls:
        host = urllib.parse.urlparse(url).netloc.lower()
        if any(d in host for d in ["bbb.org", "yelp", "facebook", "yellowpages", "angi", "homeadvisor",
                                    "thumbtack", "bing.com", "microsoft"]):
            continue
        site = url.split("?")[0]
        for page_url in [site, site.rstrip("/") + "/contact"]:
            try:
                h = fetch(page_url)
            except Exception:
                continue
            for em in EMAIL_RE.findall(h):
                em = em.lower().strip(".")
                if not BAD.search(em):
                    return em, site
            time.sleep(1)
        break
    return "", ""

def main():
    conn = sqlite3.connect(DB)
    try:
        conn.execute("ALTER TABLE leads ADD COLUMN email TEXT DEFAULT ''")
    except sqlite3.OperationalError:
        pass
    try:
        conn.execute("ALTER TABLE leads ADD COLUMN website TEXT DEFAULT ''")
    except sqlite3.OperationalError:
        pass
    conn.commit()
    total_new = 0
    for city in CITIES:
        for page in range(1, PAGES + 1):
            leads = scrape_bbb(city, page)
            if not leads:
                break
            new = 0
            for l in leads:
                dh = hashlib.md5(f"{l['phone'] or l['name']}|{l['city']}".lower().encode()).hexdigest()
                cur = conn.execute(
                    "INSERT OR IGNORE INTO leads (name,phone,address,city,dedup_hash,ingested_at) VALUES (?,?,?,?,?,datetime('now'))",
                    (l["name"], l["phone"], "", l["city"], dh))
                if cur.rowcount:
                    new += 1
                    # enrich new leads with email
                    email, site = find_email(l["name"], l["city"])
                    if email:
                        conn.execute("UPDATE leads SET email=?, website=? WHERE dedup_hash=?", (email, site, dh))
                        print(f"  + {l['name'][:32]:32} {email}", flush=True)
                conn.commit()
            total = conn.execute("SELECT COUNT(*) FROM leads").fetchone()[0]
            emailed = conn.execute("SELECT COUNT(*) FROM leads WHERE email != ''").fetchone()[0]
            print(f"  {city} p{page}: {new} new (total: {total}, with email: {emailed})", flush=True)
            total_new += new
            time.sleep(2)
    conn.close()
    print(f"DONE new={total_new}", flush=True)

main()
