#!/usr/bin/env python3
"""Fetch-only worker: prints id|email|site lines, no DB writes. Usage: enrich_fetch.py <db> <wid> <nworkers>"""
import re, time, urllib.request, urllib.parse, sqlite3, sys
DB, WID, NW = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
HEADERS = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'}
EMAIL_RE = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')
BAD = re.compile(r'\.(png|jpg|jpeg|gif|css|js|webp)$|example\.|sentry|wixpress|schema|godaddy|domain\.com$|user@domain|@website.mlb.com|@animaljam.com|@google.com|@williams.com|@rccl.com|@userbenchmark.com|@faithlife.com|@clearme.com|@biblegateway.com|@thezeusnetwork.com|@rip.ie|@ggp.com', re.I)
SKIP = ['bbb.org','yelp','facebook','yellowpages','angi','homeadvisor','thumbtack','bing.com','porch.com']
def fetch(url, timeout=10):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode('utf-8', errors='ignore')
conn = sqlite3.connect(DB, timeout=30)
rows = conn.execute("SELECT id, name, city, trade FROM leads WHERE email='' AND id % ? = ? ORDER BY id", (NW, WID)).fetchall()
conn.close()
out = open(f"/tmp/enrich_{WID}.txt", "w")
n = 0
for lid, name, city, trade in rows:
    q = urllib.parse.quote(f'"{name}" {city} {trade}')
    try:
        rss = fetch(f'https://www.bing.com/search?q={q}&format=rss')
    except Exception:
        time.sleep(1); continue
    urls = re.findall(r'<link>(https?://[^<]+)</link>', rss)
    for url in urls[:3]:
        host = urllib.parse.urlparse(url).netloc.lower()
        if any(d in host for d in SKIP): continue
        site = url.split('?')[0]
        try: h = fetch(site)
        except Exception: continue
        for em in EMAIL_RE.findall(h):
            em = em.lower().strip('.')
            if not BAD.search(em):
                out.write(f"{lid}|{em}|{site}\n"); out.flush(); n += 1
                break
        else:
            time.sleep(0.5); continue
        break
    time.sleep(1)
out.close()
print(f"worker {WID}: {n} emails -> /tmp/enrich_{WID}.txt", flush=True)
