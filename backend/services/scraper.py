import asyncio
import json
import re
import time
from pathlib import Path
from urllib.parse import quote_plus

import httpx
from bs4 import BeautifulSoup

DATA_DIR = Path(__file__).parent.parent.parent / "data" / "raw"

# Global state for progress tracking
scraping_state: dict = {
    "running": False,
    "total": 0,
    "done": 0,
    "failed": 0,
    "current_url": "",
    "bytes_collected": 0,
    "start_time": 0.0,
    "finished": False,
    "error": "",
}


def get_state() -> dict:
    return dict(scraping_state)


def _build_search_urls(keywords: list[str], url_count: int) -> list[str]:
    """Generate search query URLs based on keywords."""
    queries = []
    for kw in keywords[:8]:
        queries.append(f"https://www.google.com/search?q={quote_plus(kw)}&num=10")
        queries.append(f"https://duckduckgo.com/html/?q={quote_plus(kw)}")
    # Pad with Wikipedia searches
    for kw in keywords[:4]:
        queries.append(f"https://en.wikipedia.org/w/index.php?search={quote_plus(kw)}")
    return queries[:max(url_count // 10, 5)]


def _extract_links_from_search(html: str, base_url: str) -> list[str]:
    """Extract result links from a search page."""
    soup = BeautifulSoup(html, "html.parser")
    links = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.startswith("http") and not any(
            skip in href for skip in ["google.com", "duckduckgo.com", "javascript:", "mailto:"]
        ):
            links.append(href)
    return list(dict.fromkeys(links))[:20]


def _clean_text(html: str, url: str) -> str | None:
    """Extract clean text from HTML."""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header", "aside", "form"]):
        tag.decompose()
    text = soup.get_text(separator="\n", strip=True)
    # Remove excessive blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)
    if len(text) < 200:
        return None
    return text[:8000]  # Cap per page


async def _fetch(client: httpx.AsyncClient, url: str) -> str | None:
    try:
        response = await client.get(url, follow_redirects=True, timeout=10)
        if response.status_code == 200:
            return response.text
    except Exception:
        pass
    return None


async def run_scraping(topic_profile: dict, url_count: int):
    global scraping_state
    scraping_state.update({
        "running": True, "total": url_count, "done": 0, "failed": 0,
        "current_url": "", "bytes_collected": 0,
        "start_time": time.time(), "finished": False, "error": "",
    })

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    keywords: list[str] = topic_profile.get("keywords", []) + [topic_profile.get("area", "")]
    results: list[dict] = []

    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
    }

    async with httpx.AsyncClient(headers=headers) as client:
        search_urls = _build_search_urls(keywords, url_count)
        all_links: list[str] = []

        # Phase 1: collect links from search engines
        for surl in search_urls:
            scraping_state["current_url"] = surl
            html = await _fetch(client, surl)
            if html:
                links = _extract_links_from_search(html, surl)
                all_links.extend(links)
            await asyncio.sleep(0.5)

        # Deduplicate
        all_links = list(dict.fromkeys(all_links))[:url_count]
        scraping_state["total"] = len(all_links)

        # Phase 2: scrape each link
        sem = asyncio.Semaphore(5)

        async def scrape_one(url: str):
            async with sem:
                scraping_state["current_url"] = url
                html = await _fetch(client, url)
                if html:
                    text = _clean_text(html, url)
                    if text:
                        results.append({"url": url, "text": text})
                        scraping_state["bytes_collected"] += len(text.encode())
                        scraping_state["done"] += 1
                    else:
                        scraping_state["failed"] += 1
                else:
                    scraping_state["failed"] += 1
                await asyncio.sleep(0.2)

        tasks = [scrape_one(link) for link in all_links]
        await asyncio.gather(*tasks)

    # Save results
    output = DATA_DIR / "scraped.jsonl"
    with output.open("w", encoding="utf-8") as f:
        for item in results:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    scraping_state["running"] = False
    scraping_state["finished"] = True
