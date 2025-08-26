# Policy Ingestion MVP (YouTube)

This is a minimal, non-brittle ingestion flow for YouTube policies using **sitemaps + deterministic parsing + diffing**.

## Components
- `sitemap_crawler.py`: discovers official URLs from:
  - https://www.youtube.com/howyoutubeworks/sitemap.xml
  - https://support.google.com/youtube/sitemap?hl=en
- `policy_parser.py`: fetches an URL and normalizes it into a Rules JSON document.
- `diff_watcher.py`: compares text snapshots to detect meaningful updates.

## Install
```bash
pip install httpx selectolax
```

## Quickstart
```bash
python sitemap_crawler.py
python -c "from policy_parser import to_rule_doc; import json; print(json.dumps(to_rule_doc('https://support.google.com/youtube/answer/9288567?hl=en'), indent=2))"
```

## Notes
- This is a starting point. In production, persist URLs with `lastmod`, add clause extractors per policy family, and store docs in Postgres JSONB.
