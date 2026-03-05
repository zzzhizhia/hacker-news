#!/usr/bin/env python3
"""Fetch today's Hacker News front page stories and save to JSON."""

import json
import os
import time
import urllib.request
import urllib.parse
from datetime import datetime, timedelta, timezone

BASE_URL = "https://hn.algolia.com/api/v1/search"

os.chdir(os.path.dirname(os.path.abspath(__file__)))

today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
date_str = today.strftime("%Y-%m-%d")
start_ts = int(today.timestamp())
end_ts = int((today + timedelta(days=1)).timestamp()) - 1

print(f"Fetching {date_str}...")

all_hits = []
page = 0
while True:
    params = urllib.parse.urlencode({
        "tags": "front_page",
        "numericFilters": f"created_at_i>{start_ts},created_at_i<{end_ts}",
        "hitsPerPage": 50,
        "page": page,
    })
    url = f"{BASE_URL}?{params}"

    data = {"hits": [], "nbPages": 0}
    for attempt in range(3):
        try:
            with urllib.request.urlopen(url, timeout=30) as resp:
                data = json.loads(resp.read())
            break
        except Exception as e:
            print(f"  Attempt {attempt + 1} failed: {e}")
            if attempt < 2:
                time.sleep(2)

    hits = data.get("hits", [])
    if not hits:
        break

    all_hits.extend(hits)
    page += 1
    if page >= data.get("nbPages", 0):
        break
    time.sleep(0.3)

stories = []
for h in all_hits:
    stories.append({
        "id": h.get("objectID"),
        "title": h.get("title"),
        "url": h.get("url"),
        "author": h.get("author"),
        "points": h.get("points", 0),
        "num_comments": h.get("num_comments", 0),
        "created_at": h.get("created_at"),
    })
stories.sort(key=lambda x: x.get("points") or 0, reverse=True)

filename = f"{date_str}.json"
with open(filename, "w", encoding="utf-8") as f:
    json.dump(stories, f, indent=2, ensure_ascii=False)

print(f"Done! {len(stories)} stories saved to {filename}")
