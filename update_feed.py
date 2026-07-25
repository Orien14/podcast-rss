#!/usr/bin/env python3
import html
import re
import sys
from pathlib import Path

import requests
from bs4 import BeautifulSoup

SOURCE_URLS = [
    "https://rss.lizhi.fm/rss/3528895.xml",
    "http://rss.lizhi.fm/rss/3528895.xml",
]
OUT = Path("heishaguihua.xml")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 Version/18.0 Mobile/15E148 Safari/604.1",
    "Accept": "application/rss+xml, application/xml, text/xml, */*",
}


def fetch_source() -> str:
    errors = []
    for url in SOURCE_URLS:
        try:
            r = requests.get(url, headers=HEADERS, timeout=30, allow_redirects=True)
            if r.ok and "<rss" in r.text[:5000].lower():
                return r.text
            errors.append(f"{url}: HTTP {r.status_code}")
        except Exception as exc:
            errors.append(f"{url}: {exc}")
    raise RuntimeError("Unable to fetch source RSS: " + " | ".join(errors))


def clean_description(text: str) -> str:
    # Remove Lizhi-specific markup while preserving readable text.
    soup = BeautifulSoup(text or "", "html.parser")
    return soup.get_text("\n", strip=True)


def transform(xml_text: str) -> str:
    # Normalize http media/feed URLs to https where supported.
    xml_text = xml_text.replace("http://cdn.lizhi.fm/", "https://cdn.lizhi.fm/")
    xml_text = xml_text.replace("http://imagev2.xmcdn.com/", "https://imagev2.xmcdn.com/")

    # Remove self-referential atom:link entries that point back to the problematic source server.
    xml_text = re.sub(r"\s*<atom:link\b[^>]*/>\s*", "\n", xml_text, flags=re.I)

    # Strip Lizhi custom <myfont> tags but keep their content.
    xml_text = re.sub(r"</?myfont\b[^>]*>", "", xml_text, flags=re.I)

    # Make guid non-permalink so clients do not try to resolve legacy HTTP guid URLs.
    xml_text = re.sub(
        r"<guid(?:\s+isPermaLink=['\"](?:true|false)['\"])?>(.*?)</guid>",
        lambda m: f'<guid isPermaLink="false">{html.escape(html.unescape(m.group(1)), quote=False)}</guid>',
        xml_text,
        flags=re.I | re.S,
    )

    # Normalize any remaining legacy Lizhi audio URLs.
    xml_text = xml_text.replace("http://cdn.lizhi.fm/audio/", "https://cdn.lizhi.fm/audio/")

    # Ensure UTF-8 declaration.
    xml_text = re.sub(
        r"^<\?xml[^>]*\?>",
        '<?xml version="1.0" encoding="UTF-8"?>',
        xml_text,
        count=1,
        flags=re.I,
    )
    return xml_text


def main() -> int:
    raw = fetch_source()
    fixed = transform(raw)
    OUT.write_text(fixed, encoding="utf-8")
    print(f"Wrote {OUT} ({len(fixed)} chars)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
