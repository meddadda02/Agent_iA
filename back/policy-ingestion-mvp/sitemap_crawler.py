import httpx
import xml.etree.ElementTree as ET
from typing import List, Dict

HOWYT_SITEMAP = "https://www.youtube.com/howyoutubeworks/sitemap.xml"
YT_HELP_SITEMAP = "https://support.google.com/youtube/sitemap?hl=en"

def fetch_xml(url: str) -> ET.Element:
    r = httpx.get(url, timeout=30)
    r.raise_for_status()
    return ET.fromstring(r.text)

def parse_sitemap(root: ET.Element) -> List[Dict]:
    ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    out = []
    for url in root.findall("sm:url", ns):
        loc = url.find("sm:loc", ns)
        lastmod = url.find("sm:lastmod", ns)
        out.append({
            "loc": loc.text if loc is not None else "",
            "lastmod": lastmod.text if lastmod is not None else None,
        })
    if not out:
        for url in root.findall("url"):
            loc = url.find("loc")
            lastmod = url.find("lastmod")
            out.append({
                "loc": loc.text if loc is not None else "",
                "lastmod": lastmod.text if lastmod is not None else None,
            })
    return out

def get_catalog() -> List[Dict]:
    cat = []
    for u in [HOWYT_SITEMAP, YT_HELP_SITEMAP]:
        try:
            root = fetch_xml(u)
            cat.extend(parse_sitemap(root))
        except Exception as e:
            print(f"[warn] sitemap failed: {u} -> {e}")

    keep = []
    for row in cat:
        loc = row["loc"]
        if not loc:
            continue
        # Skip language variations
        if "/intl/" in loc:
            continue
        # Keep all policy-related pages
        if (
            "howyoutubeworks" in loc
            or "community-guidelines" in loc
            or "answer/" in loc
            or "policy" in loc
            or "guidelines" in loc
        ):
            keep.append(row)
    return keep

if __name__ == "__main__":
    catalog = get_catalog()
    print(f"discovered: {len(catalog)} relevant urls")
    for r in catalog[:20]:
        print(r)
