#!/bin/bash
set -e

cd "$(dirname "$0")"

# Initialize git repo if not exists
if [ ! -d .git ]; then
  git init
  git commit --allow-empty -m "init"
fi

# 105 days back from today (2026-03-05)
DAYS=105

for i in $(seq $DAYS -1 0); do
  # Calculate date
  DATE=$(date -v-${i}d +%Y-%m-%d)

  # Calculate timestamps for the day
  START_TS=$(date -j -f "%Y-%m-%d %H:%M:%S" "${DATE} 00:00:00" +%s)
  END_TS=$(date -j -f "%Y-%m-%d %H:%M:%S" "${DATE} 23:59:59" +%s)

  echo "Fetching ${DATE} (day $((DAYS - i + 1))/${DAYS})..."

  # Fetch front page stories for that day, sorted by points
  # Use pagination to get more results
  ALL_HITS="[]"
  PAGE=0
  while true; do
    RESPONSE=$(curl -s "https://hn.algolia.com/api/v1/search?tags=front_page&numericFilters=created_at_i%3E${START_TS}%2Ccreated_at_i%3C${END_TS}&hitsPerPage=50&page=${PAGE}")

    HITS=$(echo "$RESPONSE" | python3 -c "
import json, sys
data = json.load(sys.stdin)
hits = data.get('hits', [])
print(json.dumps(hits))
")

    HIT_COUNT=$(echo "$HITS" | python3 -c "import json,sys; print(len(json.load(sys.stdin)))")

    if [ "$HIT_COUNT" -eq 0 ]; then
      break
    fi

    # Merge hits
    ALL_HITS=$(python3 -c "
import json, sys
a = json.loads('$ALL_HITS' if '$ALL_HITS' != '[]' else '[]')
b = json.loads(sys.stdin.read())
a.extend(b)
print(json.dumps(a))
" <<< "$HITS")

    NB_PAGES=$(echo "$RESPONSE" | python3 -c "import json,sys; print(json.load(sys.stdin).get('nbPages', 0))")
    PAGE=$((PAGE + 1))
    if [ "$PAGE" -ge "$NB_PAGES" ]; then
      break
    fi
  done

  # Extract and save clean data, sorted by points descending
  python3 -c "
import json, sys

hits = json.loads(sys.stdin.read())

stories = []
for h in hits:
    stories.append({
        'id': h.get('objectID'),
        'title': h.get('title'),
        'url': h.get('url'),
        'author': h.get('author'),
        'points': h.get('points', 0),
        'num_comments': h.get('num_comments', 0),
        'created_at': h.get('created_at'),
    })

stories.sort(key=lambda x: x.get('points', 0) or 0, reverse=True)

print(json.dumps(stories, indent=2, ensure_ascii=False))
" <<< "$ALL_HITS" > "${DATE}.json"

  STORY_COUNT=$(python3 -c "import json; print(len(json.load(open('${DATE}.json'))))")

  # Commit with that day's date
  git add "${DATE}.json"
  GIT_AUTHOR_DATE="${DATE}T12:00:00" GIT_COMMITTER_DATE="${DATE}T12:00:00" \
    git commit -m "$(cat <<EOF
${DATE} Hacker News front page (${STORY_COUNT} stories)
EOF
)"

  echo "  -> ${STORY_COUNT} stories committed."

  # Small delay to be nice to the API
  sleep 0.5
done

echo "Done! Fetched $((DAYS + 1)) days of HN data."
