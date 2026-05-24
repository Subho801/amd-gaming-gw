import os
import json
import requests
from datetime import datetime, timezone

API_URL = "https://www.amdgaming.com/api/promotions"

WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK")
SEEN_FILE = "seen_amd.json"

AMD_LOGO = "https://upload.wikimedia.org/wikipedia/commons/7/7c/AMD_Logo.svg"


def load_seen():
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f))
    return set()


def save_seen(seen):
    with open(SEEN_FILE, "w", encoding="utf-8") as f:
        json.dump(sorted(list(seen)), f, indent=2)


def discord_timestamp(unix_time):
    return f"<t:{unix_time}:F>"


def get_promotions():
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json"
    }

    r = requests.get(API_URL, headers=headers, timeout=30)
    print("API:", r.status_code)

    if r.status_code != 200:
        return []

    data = r.json()

    return data.get("items", [])


def send_discord(item):
    title = item.get("title", "Unknown Giveaway")
    slug = item.get("slug", "")
    image = item.get("thumbnailImageUrl")
    status = item.get("status", "unknown").lower()
    platform = item.get("platform", "Unknown")
    keys = item.get("keysAvailable", 0)
    created = item.get("createdAt", 0)

    url = f"https://www.amdgaming.com/promotions/{slug}"

    if status == "active":
        status_text = "🟢 AVAILABLE"
        color = 0x00ff99
    else:
        status_text = "🔴 ENDED"
        color = 0xff4444

    embed = {
        "author": {
            "name": "AMD Gaming Giveaway",
            "icon_url": AMD_LOGO
        },
        "title": title,
        "url": url,
        "color": color,
        "fields": [
            {
                "name": "Status",
                "value": status_text,
                "inline": True
            },
            {
                "name": "Platform",
                "value": platform,
                "inline": True
            },
            {
                "name": "Keys Left",
                "value": str(keys),
                "inline": True
            },
            {
                "name": "Published",
                "value": discord_timestamp(created),
                "inline": False
            }
        ],
        "footer": {
            "text": "AMD Gaming Notifier",
            "icon_url": AMD_LOGO
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    if image:
        embed["image"] = {"url": image}

    payload = {
        "embeds": [embed]
    }

    r = requests.post(WEBHOOK_URL, json=payload)
    print("Discord:", r.status_code)


def main():
    seen = load_seen()

    items = get_promotions()

    print(f"Found {len(items)} promotions")

    new_seen = set(seen)

    for item in items:
        promo_id = item.get("id")

        if not promo_id:
            continue

        title = item.get("title", "Unknown")

        print(title)

        if promo_id in seen:
            continue

        send_discord(item)

        new_seen.add(promo_id)

    save_seen(new_seen)


if __name__ == "__main__":
    main()
