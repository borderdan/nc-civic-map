import asyncio
import csv
import json
import logging
import os
import sys
import time
from urllib.parse import urljoin, urlparse
from datetime import datetime, timezone
from typing import Any, Dict, List, Set, cast

import httpx
from bs4 import BeautifulSoup
from crawl4ai import AsyncWebCrawler

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(message)s")

USER_AGENT = "NCCivicMap/1.0 (+civic-data-research)"
LOCALE_DIR = "meck-county"
ADAPTER_FILE = os.path.join(LOCALE_DIR, "adapter_probes.json")
OUTPUT_CSV = os.path.join(LOCALE_DIR, "site_map_urls.csv")

# BFS Configuration
MAX_DEPTH = 3
MAX_PAGES = 2000
POLITE_DELAY_BFS = 1.0

# ID Walk Configuration
ID_WALKS = {
    "doccenter": {
        "path": "/DocumentCenter/View/{id}",
        "max_id": 5000,
        "delay": 0.5,
    },
    "civicalerts": {
        "path": "/CivicAlerts.aspx?AID={id}",
        "max_id": 1000,
        "delay": 0.5, # Assume 0.5 delay to be safe
    },
    "calendar": {
        "path": "/Calendar.aspx?EID={id}",
        "max_id": 500,
        "delay": 0.5, # Assume 0.5 delay
    }
}

class CSVSink:
    def __init__(self, filepath: str) -> None:
        self.filepath = filepath
        self.fields = [
            "locale_id", "url", "depth", "status_code", "content_type",
            "page_title", "response_bytes", "source_method", "discovered_at"
        ]
        self.buffer: List[Dict[str, Any]] = []
        self.last_flush = time.time()
        self.seen_urls: Set[str] = set()

        # Always initialize and truncate file
        with open(self.filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=self.fields)
            writer.writeheader()

    def append(self, record: dict) -> None:
        url = str(record.get("url", ""))
        if not url or url in self.seen_urls:
            return
        self.seen_urls.add(url)

        self.buffer.append(record)
        now = time.time()
        if now - self.last_flush >= 5.0 or len(self.buffer) >= 10:
            self.flush()

    def flush(self) -> None:
        if not self.buffer:
            return

        with open(self.filepath, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=self.fields)
            for row in self.buffer:
                writer.writerow(row)

        self.buffer.clear()
        self.last_flush = time.time()


async def bfs_crawl(primary_domain: str, csv_sink: CSVSink) -> dict:
    domain_parsed = urlparse(primary_domain)
    primary_netloc = domain_parsed.netloc

    queue = [(primary_domain, 0)]
    visited = {primary_domain}
    page_count = 0

    found_patterns = {
        "doccenter": False,
        "civicalerts": False,
        "calendar": False
    }

    try:
        async with AsyncWebCrawler(verbose=False) as crawler:
            while queue and page_count < MAX_PAGES:
                url, depth = queue.pop(0)

                if depth > MAX_DEPTH:
                    continue

                page_count += 1
                start_time = time.time()

                try:
                    result = await crawler.arun(url=url)

                    elapsed_ms = int((time.time() - start_time) * 1000)

                    # Assume 200 status code if successful
                    status_code = result.status_code if hasattr(result, "status_code") and result.status_code is not None else 200
                    response_bytes = len(result.html) if hasattr(result, "html") and result.html is not None else 0
                    content_type = "text/html"
                    page_title = ""

                    if hasattr(result, 'metadata') and result.metadata:
                        page_title = result.metadata.get('title', '')
                    elif hasattr(result, 'title'):
                        page_title = result.title or ""

                    print(f"[walking {depth}/{MAX_DEPTH}] {url} -> {status_code} ({response_bytes}B in {elapsed_ms}ms)")
                    sys.stdout.flush()

                    record = {
                        "locale_id": "meck-county",
                        "url": url,
                        "depth": depth,
                        "status_code": status_code,
                        "content_type": content_type,
                        "page_title": page_title,
                        "response_bytes": response_bytes,
                        "source_method": "bfs",
                        "discovered_at": datetime.now(timezone.utc).isoformat()
                    }
                    csv_sink.append(record)

                    # Check patterns
                    url_lower = url.lower()
                    if "/documentcenter/" in url_lower:
                        found_patterns["doccenter"] = True
                    if "civicalerts.aspx" in url_lower:
                        found_patterns["civicalerts"] = True
                    if "calendar.aspx" in url_lower:
                        found_patterns["calendar"] = True

                    # Extract links
                    # Fallback to simple HTML parsing if crawl4ai links don't work well
                    try:
                        html_content = result.html if hasattr(result, "html") else ""
                        if html_content:
                            soup = BeautifulSoup(html_content, "html.parser")
                            for a_tag in soup.find_all("a", href=True):
                                next_url = a_tag["href"]
                                if not next_url.startswith("javascript:") and not next_url.startswith("mailto:"):
                                    next_url = urljoin(url, next_url)
                                    next_parsed = urlparse(next_url)
                                    if next_parsed.netloc == primary_netloc:
                                        clean_url = next_url.split("#")[0]
                                        if clean_url not in visited:
                                            visited.add(clean_url)
                                            queue.append((clean_url, depth + 1))
                    except Exception as parse_e:
                        print(f"Error parsing links: {parse_e}", file=sys.stderr)

                    await asyncio.sleep(POLITE_DELAY_BFS)

                except Exception as e:
                    print(f"Error crawling {url}: {e}", file=sys.stderr)
                    sys.stderr.flush()
                    continue

    except Exception as e:
        print(f"BFS Crawl Error: {e}", file=sys.stderr)
        sys.stderr.flush()
    finally:
        csv_sink.flush()

    return found_patterns


async def sequential_id_walk(primary_domain: str, patterns: dict, csv_sink: CSVSink) -> None:
    async with httpx.AsyncClient(headers={"User-Agent": USER_AGENT}, timeout=10.0) as client:
        for kind, conf in ID_WALKS.items():
            if not patterns.get(kind, False):
                continue

            path_template = conf["path"]
            max_id = cast(int, conf["max_id"])
            delay = cast(float, conf["delay"])
            path_template = cast(str, conf["path"])

            for cid in range(1, max_id + 1):
                path = path_template.format(id=cid)
                url = urljoin(primary_domain, path)

                try:
                    start_time = time.time()
                    resp = await client.head(url, follow_redirects=True)
                    elapsed_ms = int((time.time() - start_time) * 1000)

                    print(f"[id-walk {kind}] {path} -> {resp.status_code}")
                    sys.stdout.flush()

                    if resp.status_code == 200:
                        # Follow up with GET if 200 to get size and type
                        resp_get = await client.get(url, follow_redirects=True)
                        content_type = resp_get.headers.get("Content-Type", "")
                        response_bytes = len(resp_get.content)

                        record = {
                            "locale_id": "meck-county",
                            "url": url,
                            "depth": -1, # or some indicator
                            "status_code": resp_get.status_code,
                            "content_type": content_type,
                            "page_title": "", # Hard to get without parsing
                            "response_bytes": response_bytes,
                            "source_method": f"id-walk:{kind}",
                            "discovered_at": datetime.now(timezone.utc).isoformat()
                        }
                        csv_sink.append(record)

                    await asyncio.sleep(delay)
                except Exception as e:
                    print(f"Error walking {url}: {e}", file=sys.stderr)
                    sys.stderr.flush()

            csv_sink.flush()


async def main() -> None:
    try:
        with open(ADAPTER_FILE, "r") as f:
            adapters = json.load(f)

        primary_domain = adapters.get("primary_domain")
        if not primary_domain:
            print("No primary domain found in adapter config.", file=sys.stderr)
            return

        csv_sink = CSVSink(OUTPUT_CSV)

        found_patterns = await bfs_crawl(primary_domain, csv_sink)

        # Override to True for testing / to guarantee walks happen if they existed
        # (Though requirement says "only if BFS surfaced these patterns")

        await sequential_id_walk(primary_domain, found_patterns, csv_sink)

    except Exception as e:
        print(f"Main Error: {e}", file=sys.stderr)
        sys.stderr.flush()


if __name__ == "__main__":
    asyncio.run(main())
