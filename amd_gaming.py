import os
import json
import requests
from datetime import datetime, timezone

API_URL = "https://www.amdgaming.com/promotions"

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
    try:
        return f"<t:{int(unix_time)}:F>"
    except:
        return "Unknown"


def get_promotions():
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "X-Requested-With": "XMLHttpRequest"
    }

    r = requests.get(API_URL, headers=headers, timeout=30)

    print("API:", r.status_code)

    if r.status_code != 200:
        print(r.text[:500])
        return []

    try:
        data = r.json()
    except Exception as e:
        print("JSON parse failed:", e)
        print(r.text[:500])
        return []

    return data.get("items", [])


def get_status(item):
    status = str(item.get("status", "")).lower()
    keys = item.get("keysAvailable", 0)

    if status == "active" and keys > 0:
        return "🟢 AVAILABLE", 0x00ff99

    if status == "active" and keys == 0:
        return "🟠 OUT OF KEYS", 0xffaa00

    return "🔴 ENDED", 0xff4444


def send_discord(item):
    title = item.get("title", "Unknown Giveaway")
    slug = item.get("slug", "")
    image = item.get("thumbnailImageUrl")
    platform = item.get("platform", "Unknown")
    developer = item.get("developer", "Unknown")
    keys = item.get("keysAvailable", 0)
    created = item.get("createdAt", 0)
    updated = item.get("updatedAt", 0)
    tags = item.get("tags", "")

    url = f"https://www.amdgaming.com/promotions/{slug}"

    status_text, color = get_status(item)

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
                "name": "Developer",
                "value": developer,
                "inline": True
            },
            {
                "name": "Published",
                "value": discord_timestamp(created),
                "inline": True
            },
            {
                "name": "Updated",
                "value": discord_timestamp(updated),
                "inline": True
            }
        ],
        "footer": {
            "text": "AMD Gaming Notifier",
            "icon_url": AMD_LOGO
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    if image:
        embed["image"] = {
            "url": image
        }

    if tags:
        embed["description"] = f"🏷️ `{tags}`"

    payload = {
        "embeds": [embed]
    }

    r = requests.post(WEBHOOK_URL, json=payload, timeout=30)

    print("Discord:", r.status_code)

    if r.text:
        print(r.text[:300])


def main():
    if not WEBHOOK_URL:
        print("DISCORD_WEBHOOK missing")
        return

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
