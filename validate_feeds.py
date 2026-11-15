"""
Run this on YOUR machine first:
  python validate_feeds.py

It will print only the feeds that pass all checks.
Then paste the output into your RSS_FEEDS dict.
"""

import requests
import feedparser
import time

FEEDS_TO_TEST = {
    "rbi_press_releases":    "https://www.rbi.org.in/rss/Rss.aspx?Id=1",
    "rbi_circulars":         "https://www.rbi.org.in/rss/Rss.aspx?Id=4",
    "rbi_notifications":     "https://www.rbi.org.in/rss/Rss.aspx?Id=7",
    "sebi_news":             "https://www.sebi.gov.in/sebirss.xml",
    "sebi_orders":           "https://www.sebi.gov.in/sebirssorders.xml",
    "bse_announcements":     "https://www.bseindia.com/xml-data/corpfiling/announcements.xml",
}

HEADERS = {"User-Agent": "Mozilla/5.0"}
TIMEOUT  = 5

passed = {}

for name, url in FEEDS_TO_TEST.items():
    try:
        t0   = time.time()
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT, allow_redirects=True)
        elapsed = round(time.time() - t0, 2)

        if resp.status_code != 200:
            print(f"FAIL [{name}] status={resp.status_code}")
            continue

        ct = resp.headers.get("Content-Type", "")
        if "xml" not in ct and "rss" not in ct and "atom" not in ct:
            # Try parsing anyway — some servers return wrong content-type
            pass

        body = resp.text
        if "<rss" not in body and "<feed" not in body and "<channel" not in body:
            print(f"FAIL [{name}] no RSS/feed tag in body")
            continue

        feed = feedparser.parse(body)
        if not feed.entries:
            print(f"FAIL [{name}] 0 entries parsed")
            continue

        print(f"PASS [{name}] {len(feed.entries)} entries, {elapsed}s")
        passed[name] = url

    except requests.exceptions.Timeout:
        print(f"FAIL [{name}] timeout after {TIMEOUT}s")
    except Exception as e:
        print(f"FAIL [{name}] {e}")

print("\n# ── Paste these into RSS_FEEDS ──")
for name, url in passed.items():
    print(f'    "{name}": {{"url": "{url}", "max_articles": 20, "timeout": 12}},')
