"""
collect_trends.py
Kerää sisältömarkkinoinnin RSS-syötteet ja kirjoittaa trends.md-tiedoston.
Ajaa GitHub Actionsin kautta yöllä.
"""

import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import feedparser

# ---------------------------------------------------------------------------
# Lähteet
# ---------------------------------------------------------------------------
FEEDS = [
    # Kansainväliset
    {"name": "Content Marketing Institute", "url": "https://contentmarketinginstitute.com/feed/", "lang": "en"},
    {"name": "HubSpot Marketing Blog",      "url": "https://blog.hubspot.com/marketing/rss.xml", "lang": "en"},
    {"name": "Convince & Convert",          "url": "https://www.convinceandconvert.com/feed/", "lang": "en"},
    {"name": "Digiday",                     "url": "https://digiday.com/feed/", "lang": "en"},
    {"name": "MarketingProfs",              "url": "https://www.marketingprofs.com/rss/articles.asp", "lang": "en"},
    {"name": "MarTech",                     "url": "https://martech.org/feed/", "lang": "en"},
    # Branded entertainment & sisältömarkkinointi
    {"name": "Little Black Book",           "url": "https://lbbonline.com/feed", "lang": "en"},
    {"name": "Native Advertising Institute","url": "https://nativeadvertisinginstitute.com/feed", "lang": "en"},
    {"name": "The Drum",                    "url": "https://www.thedrum.com/rss", "lang": "en"},
    # Kotimaiset
    {"name": "Markkinointi & Mainonta",     "url": "https://www.marmai.fi/rss.xml", "lang": "fi"},
    {"name": "Digimarkkinointi.fi",         "url": "https://www.digimarkkinointi.fi/feed", "lang": "fi"},
]

MAX_ITEMS_PER_FEED = 5
OUTPUT_PATH = Path(__file__).parent.parent / "user" / "trend-tracker" / "trends.md"

STRIP_HTML = re.compile(r"<[^>]+>")
NORMALIZE_WS = re.compile(r"\s+")


def clean_text(raw: str, max_chars: int = 350) -> str:
    text = STRIP_HTML.sub(" ", raw or "")
    text = NORMALIZE_WS.sub(" ", text).strip()
    if len(text) > max_chars:
        text = text[:max_chars].rsplit(" ", 1)[0] + "…"
    return text


def fetch_feed(feed_info: dict) -> list[dict]:
    try:
        parsed = feedparser.parse(feed_info["url"])
        items = []
        for entry in parsed.entries[:MAX_ITEMS_PER_FEED]:
            published = (
                getattr(entry, "published", None)
                or getattr(entry, "updated", None)
                or ""
            )
            summary = clean_text(
                getattr(entry, "summary", "") or getattr(entry, "description", "")
            )
            items.append(
                {
                    "title": clean_text(entry.get("title", "—"), max_chars=120),
                    "link": entry.get("link", ""),
                    "published": published,
                    "summary": summary,
                    "lang": feed_info["lang"],
                }
            )
        print(f"  ✓ {feed_info['name']}: {len(items)} artikkelia")
        return items
    except Exception as exc:
        print(f"  ✗ {feed_info['name']}: {exc}", file=sys.stderr)
        return []


def build_markdown(feed_results: list[tuple[dict, list[dict]]]) -> str:
    now = datetime.now(timezone.utc)
    lines = [
        "# Sisältömarkkinoinnin trendit",
        "",
        f"_Päivitetty: {now.strftime('%Y-%m-%d %H:%M')} UTC_",
        "",
        "> Tämä tiedosto generoidaan automaattisesti joka yö GitHub Actionsin kautta.",
        "> Älä muokkaa käsin — muutokset ylikirjoitetaan.",
        "",
        "---",
        "",
    ]

    fi_section = []
    en_section = []

    for feed_info, items in feed_results:
        if not items:
            continue
        block = [f"## {feed_info['name']}", ""]
        for item in items:
            block.append(f"### {item['title']}")
            if item["published"]:
                block.append(f"_{item['published']}_")
                block.append("")
            if item["summary"]:
                block.append(item["summary"])
                block.append("")
            if item["link"]:
                block.append(f"→ [{item['link']}]({item['link']})")
            block.append("")
        block.append("---")
        block.append("")

        if feed_info["lang"] == "fi":
            fi_section.extend(block)
        else:
            en_section.extend(block)

    if fi_section:
        lines += ["# 🇫🇮 Kotimaiset lähteet", ""] + fi_section
    if en_section:
        lines += ["# 🌍 Kansainväliset lähteet", ""] + en_section

    return "\n".join(lines)


def main():
    print(f"Haetaan {len(FEEDS)} syötettä…")
    feed_results = [(fi, fetch_feed(fi)) for fi in FEEDS]

    markdown = build_markdown(feed_results)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(markdown, encoding="utf-8")

    total = sum(len(items) for _, items in feed_results)
    print(f"\nValmis — {total} artikkelia → {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
