import os
import re
import json
import requests
from datetime import datetime, timezone

BASE = "https://www.amdgaming.com"
SEEN_FILE = "seen_amd.json"
WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK")

AMD_ICON = "https://www.amdgaming.com/uploads/default/original/1X/9f86b0f0a4d4c8f3c4e6b4c9e6e6a6f6.png"

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json, text/plain, */*",
}


def load_seen():
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f))
    return set()


def save_seen(seen):
    with open(SEEN_FILE, "w", encoding="utf-8") as f:
        json.dump(sorted(seen), f, indent=2)


def clean(text):
    return re.sub(r"\s+", " ", text or "").strip()


def get_json(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
        print(url, r.status_code)
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        print("JSON fetch failed:", url, e)
    return None


def absolute_url(url):
    if not url:
        return None
    if url.startswith("http"):
        return url
    return BASE + url


def fetch_promotions():
    promos = []

    endpoints = [
        f"{BASE}/latest.json",
        f"{BASE}/search.json?q=giveaway",
        f"{BASE}/search.json?q=promotion",
    ]

    for endpoint in endpoints:
        data = get_json(endpoint)
        if not data:
            continue

        topics = []

        if "topic_list" in data:
            topics.extend(data["topic_list"].get("topics", []))

        if "topics" in data:
            topics.extend(data.get("topics", []))

        for topic in topics:
            title = clean(topic.get("title"))
            if not title:
                continue

            lower = title.lower()

            if "giveaway" not in lower and "promotion" not in lower and "reward" not in lower:
                continue

            slug = topic.get("slug")
            topic_id = topic.get("id")

            if not slug or not topic_id:
                continue

            link = f"{BASE}/t/{slug}/{topic_id}"

            image = None
            if topic.get("image_url"):
                image = absolute_url(topic["image_url"])
            elif topic.get("thumbnails"):
                thumbs = topic.get("thumbnails") or []
                if thumbs:
                    image = absolute_url(thumbs[-1].get("url"))

            created_at = topic.get("created_at")
            unix_time = None
            if created_at:
                try:
                    dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                    unix_time = int(dt.timestamp())
                except Exception:
                    pass

            promos.append({
                "id": str(topic_id),
                "title": title,
                "link": link,
                "image": image,
                "created_unix": unix_time,
            })

    unique = {}
    for p in promos:
        unique[p["id"]] = p

    return list(unique.values())


def send_discord(promo):
    if not WEBHOOK_URL:
        print("DISCORD_WEBHOOK missing")
        return

    published = "Unknown"
    if promo["created_unix"]:
        published = f"<t:{promo['created_unix']}:F>"

    embed = {
        "author": {
            "name": "AMD Gaming Giveaway",
        },
        "title": promo["title"],
        "url": promo["link"],
        "color": 0x00D8FF,
        "fields": [
            {
                "name": "Status",
                "value": "🟢 AVAILABLE / NEW",
                "inline": True
            },
            {
                "name": "Published",
                "value": published,
                "inline": True
            }
        ],
        "footer": {
            "text": "AMD Gaming Notifier"
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    if promo["image"]:
        embed["image"] = {"url": promo["image"]}

    r = requests.post(WEBHOOK_URL, json={"embeds": [embed]}, timeout=30)
    print("Discord:", r.status_code, r.text[:200])


def main():
    seen = load_seen()
    promos = fetch_promotions()

    print(f"Found {len(promos)} AMD giveaway/promotion posts")

    new_seen = set(seen)

    for promo in promos:
        print("-", promo["title"])

        if promo["id"] in seen:
            continue

        send_discord(promo)
        new_seen.add(promo["id"])

    save_seen(new_seen)


if __name__ == "__main__":
    main()
