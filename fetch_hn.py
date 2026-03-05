#!/usr/bin/env python3
"""Fetch Hacker News front page stories for the past 105 days and commit each day."""

import json
import os
import subprocess
import time
import urllib.request
import urllib.parse
from datetime import datetime, timedelta, timezone

DAYS = 105
BASE_URL = "https://hn.algolia.com/api/v1/search"
WORKDIR = os.path.dirname(os.path.abspath(__file__))

os.chdir(WORKDIR)

# Init git repo
if not os.path.isdir(".git"):
    subprocess.run(["git", "init"], check=True)
    subprocess.run(["git", "commit", "--allow-empty", "-m", "init"], check=True)

today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

for i in range(DAYS, -1, -1):
    day = today - timedelta(days=i)
    date_str = day.strftime("%Y-%m-%d")
    start_ts = int(day.timestamp())
    end_ts = int((day + timedelta(days=1)).timestamp()) - 1

    print(f"Fetching {date_str} ({DAYS - i + 1}/{DAYS + 1})...")

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

        try:
            with urllib.request.urlopen(url, timeout=30) as resp:
                data = json.loads(resp.read())
        except Exception as e:
            print(f"  Error fetching page {page}: {e}, retrying...")
            time.sleep(2)
            try:
                with urllib.request.urlopen(url, timeout=30) as resp:
                    data = json.loads(resp.read())
            except Exception as e2:
                print(f"  Retry failed: {e2}, skipping remaining pages")
                break

        hits = data.get("hits", [])
        if not hits:
            break

        all_hits.extend(hits)
        page += 1
        if page >= data.get("nbPages", 0):
            break
        time.sleep(0.3)

    # Clean and sort by points
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

    count = len(stories)
    env = os.environ.copy()
    env["GIT_AUTHOR_DATE"] = f"{date_str}T12:00:00"
    env["GIT_COMMITTER_DATE"] = f"{date_str}T12:00:00"

    subprocess.run(["git", "add", filename], check=True)
    subprocess.run(
        ["git", "commit", "-m", f"{date_str} Hacker News front page ({count} stories)"],
        env=env, check=True,
    )
    print(f"  -> {count} stories committed.")
    time.sleep(0.5)

print(f"\nDone! Fetched {DAYS + 1} days of HN data.")
