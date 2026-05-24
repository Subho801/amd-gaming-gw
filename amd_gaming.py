import os
import re
import json
import requests
from datetime import datetime
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

URL = "https://www.amdgaming.com/promotions"
SEEN_FILE = "seen_amd.json"
WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK")

AMD_LOGO = "https://upload.wikimedia.org/wikipedia/commons/7/7c/AMD_Logo.svg"


def load_seen():
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f))
    return set()


def save_seen(seen):
    with open(SEEN_FILE, "w", encoding="utf-8") as f:
        json.dump(sorted(list(seen)), f, indent=2)


def clean_text(text):
    return re.sub(r"\s+", " ", text or "").strip()


def fetch_page():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(
            viewport={"width": 1600, "height": 1200},
            user_agent="Mozilla/5.0"
        )

        page.goto(URL, wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(4000)

        html = page.content()
        browser.close()
        return html


def extract_promotions(html):
    soup = BeautifulSoup(html, "html.parser")
    promos = []

    text_blocks = soup.find_all(["tr", "li", "div", "article"])

    for block in text_blocks:
        text = clean_text(block.get_text(" "))

        if not text:
            continue

        if "Giveaway" not in text:
            continue

        title_match = re.search(r"(.+?Giveaway)", text, re.I)
        if not title_match:
            continue

        title = clean_text(title_match.group(1))

        if len(title) < 5:
            continue

        status = "UNKNOWN"
        if "Ended!" in text or "Ended" in text:
            status = "ENDED"
        else:
            status = "AVAILABLE"

        published = "Unknown"
        date_match = re.search(r"\b\d{2}\.\d{2}\.\d{4}\b", text)
        if date_match:
            published = date_match.group(0)

        img = None
        image_tag = block.find("img")
        if image_tag:
            img = image_tag.get("src") or image_tag.get("data-src")

        if img and img.startswith("/"):
            img = "https://www.amdgaming.com" + img

        link = URL
        a = block.find("a", href=True)
        if a:
            href = a["href"]
            if href.startswith("/"):
                link = "https://www.amdgaming.com" + href
            elif href.startswith("http"):
                link = href

        promo_id = re.sub(r"[^a-zA-Z0-9]+", "-", title.lower()).strip("-")

        promos.append({
            "id": promo_id,
            "title": title,
            "status": status,
            "published": published,
            "image": img,
            "link": link
        })

    unique = {}
    for promo in promos:
        unique[promo["id"]] = promo

    return list(unique.values())


def send_discord(promo):
    if not WEBHOOK_URL:
        print("DISCORD_WEBHOOK not set")
        return

    color = 0x00c8ff if promo["status"] == "AVAILABLE" else 0x777777

    embed = {
        "author": {
            "name": "AMD Gaming Giveaway",
            "icon_url": AMD_LOGO
        },
        "title": promo["title"],
        "url": promo["link"],
        "color": color,
        "fields": [
            {
                "name": "Status",
                "value": "🟢 AVAILABLE" if promo["status"] == "AVAILABLE" else "🔴 ENDED",
                "inline": True
            },
            {
                "name": "Published",
                "value": promo["published"],
                "inline": True
            }
        ],
        "footer": {
            "text": "AMD Gaming Notifier"
        },
        "timestamp": datetime.utcnow().isoformat()
    }

    if promo["image"]:
        embed["image"] = {"url": promo["image"]}

    payload = {"embeds": [embed]}

    r = requests.post(WEBHOOK_URL, json=payload, timeout=20)
    print("Discord:", r.status_code, r.text[:200])


def main():
    seen = load_seen()

    print("Fetching AMD Gaming promotions...")
    html = fetch_page()

    promos = extract_promotions(html)
    print(f"Found {len(promos)} giveaways")

    new_seen = set(seen)

    for promo in promos:
        print(promo["title"], "-", promo["status"])

        if promo["status"] == "ENDED":
            continue

        if promo["id"] in seen:
            continue

        send_discord(promo)
        new_seen.add(promo["id"])

    save_seen(new_seen)


if __name__ == "__main__":
    main()
