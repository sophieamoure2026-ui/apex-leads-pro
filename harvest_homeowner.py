#!/usr/bin/env python3
"""
Apex homeowner intent harvester — Phase 1 lead database.
Scrapes Reddit city/insurance subs for "looking for" posts (homeowner intent).
Free, real, thin. Profiles build over time.
Output: homeowner_leads.db
"""
import re, time, urllib.request, urllib.parse, json, sqlite3, hashlib
from pathlib import Path

DB = Path.home() / "workspace/apex-leads-pro/homeowner_leads.db"
HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}

# subreddit -> (city, trades to look for)
TARGETS = [
    ("Dallas", ["roofing", "roofer", "hvac", "ac repair", "plumber", "plumbing", "electrician", "insurance"]),
    ("Houston", ["roofing", "roofer", "hvac", "ac repair", "plumber", "plumbing", "electrician", "insurance"]),
    ("FortWorth", ["roofing", "roofer", "hvac", "plumber", "electrician"]),
    ("insurance", ["auto insurance", "home insurance", "life insurance", "quote"]),
]

def fetch(url, timeout=15):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", errors="ignore")

def search_reddit(sub, query):
    q = urllib.parse.quote(query)
    url = f"https://www.reddit.com/r/{sub}/search.json?q={q}&restrict_sr=1&sort=new&limit=25"
    try:
        data = json.loads(fetch(url))
        return data.get("data", {}).get("children", [])
    except Exception as e:
        print(f"  reddit fail r/{sub} '{query}': {str(e)[:60]}", flush=True)
        return []

def main():
    conn = sqlite3.connect(DB)
    conn.execute('''CREATE TABLE IF NOT EXISTS leads (
        id INTEGER PRIMARY KEY, source TEXT, source_url TEXT,
        title TEXT, body TEXT, city TEXT, trade TEXT,
        posted_utc INTEGER, author TEXT,
        dedup_hash TEXT UNIQUE, ingested_at TEXT)''')
    conn.commit()
    total_new = 0
    for sub, queries in TARGETS:
        for q in queries:
            posts = search_reddit(sub, q)
            new = 0
            for p in posts:
                d = p.get("data", {})
                title = d.get("title", "")
                body = d.get("selftext", "")[:2000]
                # filter: must look like a request, not an ad
                text = (title + " " + body).lower()
                if not any(w in text for w in ["looking for", "need", "recommend", "anyone know",
                                               "seeking", "in need of", "quote"]):
                    continue
                url = "https://www.reddit.com" + d.get("permalink", "")
                dh = hashlib.md5(url.encode()).hexdigest()
                # guess trade from query
                trade = q
                for t in ["roofing", "roofer", "hvac", "ac", "plumb", "electric", "insurance"]:
                    if t in q.lower():
                        trade = {"roofer": "roofing", "ac": "hvac", "plumb": "plumbing",
                                 "electric": "electrician"}.get(t, t)
                        break
                city = sub if sub in ("Dallas", "Houston", "FortWorth") else ""
                cur = conn.execute(
                    """INSERT OR IGNORE INTO leads
                       (source, source_url, title, body, city, trade, posted_utc, author, dedup_hash, ingested_at)
                       VALUES (?,?,?,?,?,?,?,?,?,datetime('now'))""",
                    ("reddit", url, title, body, city, trade,
                     int(d.get("created_utc", 0)), d.get("author", ""), dh))
                if cur.rowcount:
                    new += 1
                    print(f"  + [{trade}] {title[:60]}", flush=True)
            conn.commit()
            total_new += new
            time.sleep(2)
    t = conn.execute("SELECT COUNT(*) FROM leads").fetchone()[0]
    print(f"DONE new={total_new} total={t}", flush=True)
    conn.close()

main()
