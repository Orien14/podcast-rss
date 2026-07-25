#!/usr/bin/env python3
import html
import sys
from pathlib import Path
from xml.etree import ElementTree as ET

import requests

SOURCE_URLS = [
    "https://rss.lizhi.fm/rss/3528895.xml",
    "http://rss.lizhi.fm/rss/3528895.xml",
]
OUT = Path("heishaguihua.xml")
SELF_URL = "https://raw.githubusercontent.com/Orien14/podcast-rss/main/heishaguihua.xml"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 Version/18.0 Mobile/15E148 Safari/604.1",
    "Accept": "application/rss+xml, application/xml, text/xml, */*",
}

ITUNES = "http://www.itunes.com/dtds/podcast-1.0.dtd"
ATOM = "http://www.w3.org/2005/Atom"
ET.register_namespace("itunes", ITUNES)
ET.register_namespace("atom", ATOM)


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


def text_of(node, tag, default=""):
    child = node.find(tag)
    return (child.text or "").strip() if child is not None and child.text else default


def build_minimal_feed(xml_text: str) -> bytes:
    src = ET.fromstring(xml_text)
    src_channel = src.find("channel")
    if src_channel is None:
        raise RuntimeError("Source RSS has no channel")

    rss = ET.Element("rss", {"version": "2.0"})
    channel = ET.SubElement(rss, "channel")

    title = text_of(src_channel, "title", "黑鲨诡话")
    description = text_of(src_channel, "description", "黑鲨诡话播客")

    ET.SubElement(channel, "title").text = title
    ET.SubElement(channel, "link").text = "https://www.lizhi.fm/"
    ET.SubElement(channel, "language").text = "zh-CN"
    ET.SubElement(channel, "description").text = description
    ET.SubElement(channel, f"{{{ITUNES}}}author").text = title
    ET.SubElement(channel, f"{{{ITUNES}}}summary").text = description
    ET.SubElement(channel, f"{{{ITUNES}}}explicit").text = "yes"
    ET.SubElement(channel, f"{{{ITUNES}}}category", {"text": "Society & Culture"})
    ET.SubElement(channel, f"{{{ATOM}}}link", {
        "href": SELF_URL,
        "rel": "self",
        "type": "application/rss+xml",
    })

    image = src_channel.find(f"{{{ITUNES}}}image")
    if image is not None and image.attrib.get("href"):
        ET.SubElement(channel, f"{{{ITUNES}}}image", {"href": image.attrib["href"].replace("http://", "https://")})

    for src_item in src_channel.findall("item"):
        enclosure = src_item.find("enclosure")
        if enclosure is None or not enclosure.attrib.get("url"):
            continue

        item = ET.SubElement(channel, "item")
        item_title = text_of(src_item, "title", "黑鲨诡话")
        ET.SubElement(item, "title").text = item_title

        link = text_of(src_item, "link")
        if link:
            ET.SubElement(item, "link").text = link.replace("http://", "https://")

        ET.SubElement(item, "description").text = item_title
        ET.SubElement(item, f"{{{ITUNES}}}author").text = title
        ET.SubElement(item, f"{{{ITUNES}}}explicit").text = "yes"

        audio_url = enclosure.attrib["url"].replace("http://", "https://")
        length = enclosure.attrib.get("length", "0")
        mime = enclosure.attrib.get("type", "audio/mpeg") or "audio/mpeg"
        ET.SubElement(item, "enclosure", {
            "url": audio_url,
            "length": length,
            "type": mime,
        })
        guid = ET.SubElement(item, "guid", {"isPermaLink": "false"})
        guid.text = audio_url

        pubdate = text_of(src_item, "pubDate")
        if pubdate:
            ET.SubElement(item, "pubDate").text = pubdate

        duration = text_of(src_item, f"{{{ITUNES}}}duration")
        if duration:
            ET.SubElement(item, f"{{{ITUNES}}}duration").text = duration

        ep_image = src_item.find(f"{{{ITUNES}}}image")
        if ep_image is not None and ep_image.attrib.get("href"):
            ET.SubElement(item, f"{{{ITUNES}}}image", {"href": ep_image.attrib["href"].replace("http://", "https://")})

    tree = ET.ElementTree(rss)
    ET.indent(tree, space="  ")
    return ET.tostring(rss, encoding="utf-8", xml_declaration=True)


def main() -> int:
    raw = fetch_source()
    fixed = build_minimal_feed(raw)
    OUT.write_bytes(fixed)
    print(f"Wrote {OUT} ({len(fixed)} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
