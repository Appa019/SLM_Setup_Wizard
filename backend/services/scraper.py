import asyncio
import json
import random
import re
import time
from collections import defaultdict
from pathlib import Path
from urllib.parse import parse_qs, quote_plus, unquote, urlparse

import httpx
from bs4 import BeautifulSoup
from services.query_generator import generate_queries

DATA_DIR = Path(__file__).parent.parent.parent / "data" / "raw"

scraping_state: dict = {
    "running": False, "total": 0, "done": 0, "failed": 0,
    "current_url": "", "bytes_collected": 0,
    "start_time": 0.0, "finished": False, "error": "",
}

# ── Pool de 40 User-Agents reais ──────────────────────────────────────────────
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_3) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.0",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 OPR/106.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64; rv:122.0) Gecko/20100101 Firefox/122.0",
    "Mozilla/5.0 (Windows NT 11.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (iPad; CPU OS 17_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Brave/1.63.165",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Linux; Android 13; SM-G998B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 12_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Fedora; Linux x86_64; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Linux; Android 12; Pixel 6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Vivaldi/6.5.3206.63",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Mobile Safari/537.36",
]

SAFE_SOURCES = [
    "wikipedia.org", "archive.org", "github.com", "developer.mozilla.org",
    "docs.python.org", "stackoverflow.com", "arxiv.org", "medium.com",
    "towardsdatascience.com", "huggingface.co",
]

SEARCH_ENGINES = [
    lambda kw: f"https://duckduckgo.com/html/?q={quote_plus(kw)}&kl=br-pt",
    lambda kw: f"https://search.brave.com/search?q={quote_plus(kw)}&source=web",
]


def get_state() -> dict:
    return dict(scraping_state)


def _random_headers(referer: str = "") -> dict:
    ua = random.choice(USER_AGENTS)
    headers = {
        "User-Agent":                ua,
        "Accept":                    "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language":           "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept-Encoding":           "gzip, deflate",
        "DNT":                       "1",
        "Connection":                "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest":            "document",
        "Sec-Fetch-Mode":            "navigate",
        "Sec-Fetch-Site":            "cross-site" if referer else "none",
        "Sec-Fetch-User":            "?1",
        "Cache-Control":             "max-age=0",
    }
    if referer:
        headers["Referer"] = referer
    return headers


def _domain(url: str) -> str:
    return urlparse(url).netloc


def _is_safe_source(url: str) -> bool:
    d = _domain(url)
    return any(s in d for s in SAFE_SOURCES)


def _clean_text(html: str) -> str | None:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header", "aside", "form", "noscript"]):
        tag.decompose()
    text = soup.get_text(separator="\n", strip=True)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text[:8000] if len(text) >= 200 else None


_SKIP_DOMAINS = [
    "google.com", "duckduckgo.com", "brave.com",
    "facebook.com", "twitter.com", "instagram.com",
    "youtube.com", "tiktok.com", "reddit.com",
]
_SKIP_PATTERNS = ["y.js?ad_domain", "javascript:", "mailto:", "/ads/", "?ad=", "&ad="]


def _extract_links(html: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    links = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        # Decode DuckDuckGo redirect: //duckduckgo.com/l/?uddg=ENCODED_URL
        if "duckduckgo.com/l/" in href:
            parsed = urlparse("https:" + href if href.startswith("//") else href)
            uddg = parse_qs(parsed.query).get("uddg", [""])
            href = unquote(uddg[0]) if uddg[0] else ""
        if not href.startswith("http"):
            continue
        if any(skip in href for skip in _SKIP_DOMAINS + _SKIP_PATTERNS):
            continue
        links.append(href)
    return list(dict.fromkeys(links))[:25]


class DomainRateLimiter:
    def __init__(self, max_per_minute: int = 3):
        self.max     = max_per_minute
        self.history: dict[str, list[float]] = defaultdict(list)

    async def wait(self, url: str):
        domain = _domain(url)
        now    = time.time()
        self.history[domain] = [t for t in self.history[domain] if now - t < 60]
        if len(self.history[domain]) >= self.max:
            wait_time = 60 - (now - self.history[domain][0]) + random.uniform(0.5, 2.0)
            if wait_time > 0:
                await asyncio.sleep(wait_time)
        self.history[domain].append(time.time())


async def _fetch_with_retry(
    client: httpx.AsyncClient,
    url: str,
    referer: str = "",
    max_retries: int = 3,
) -> str | None:
    for attempt in range(max_retries):
        try:
            resp = await client.get(
                url,
                headers=_random_headers(referer),
                follow_redirects=True,
                timeout=12,
            )
            if resp.status_code == 200:
                return resp.text
            if resp.status_code in (429, 503):
                await asyncio.sleep((2 ** attempt) * random.uniform(1.5, 3.0))
                continue
            if resp.status_code in (403, 404, 410):
                return None
        except (httpx.TimeoutException, httpx.ConnectError):
            await asyncio.sleep((2 ** attempt) * 1.5)
        except Exception:
            return None
    return None


async def _playwright_fetch(url: str) -> str | None:
    """Fallback: usa Playwright para sites JS-heavy que httpx nao consegue."""
    try:
        from playwright.async_api import async_playwright  # noqa: PLC0415
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page    = await browser.new_page(
                user_agent=random.choice(USER_AGENTS),
                extra_http_headers={"Accept-Language": "pt-BR,pt;q=0.9"},
            )
            await page.goto(url, timeout=15000, wait_until="domcontentloaded")
            await asyncio.sleep(random.uniform(1.5, 3.0))
            html = await page.content()
            await browser.close()
            return html
    except Exception:
        return None


async def run_scraping(topic_profile: dict, url_count: int):
    global scraping_state
    scraping_state.update({
        "running": True, "total": url_count, "done": 0, "failed": 0,
        "current_url": "", "bytes_collected": 0,
        "start_time": time.time(), "finished": False, "error": "",
    })
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    raw_keywords: list[str] = topic_profile.get("keywords", []) + [topic_profile.get("area", "")]
    raw_keywords = [k for k in raw_keywords if k]
    keywords = await generate_queries(topic_profile)
    if not keywords:
        keywords = raw_keywords
    results:  list[dict] = []
    limiter   = DomainRateLimiter(max_per_minute=3)
    cookies   = httpx.Cookies()

    async with httpx.AsyncClient(cookies=cookies, timeout=15) as client:
        # ── Phase 1: coletar links via search engines ──────────────────────
        all_links: list[str] = []
        used_engine_idx = 0

        for kw in keywords:
            engine     = SEARCH_ENGINES[used_engine_idx % len(SEARCH_ENGINES)]
            search_url = engine(kw)
            used_engine_idx += 1
            scraping_state["current_url"] = search_url
            html = await _fetch_with_retry(client, search_url)
            if html:
                all_links.extend(_extract_links(html))
            # Delay humanizado entre buscas
            await asyncio.sleep(random.uniform(2.0, 4.0))

        # Priorizar fontes seguras + deduplicar + embaralhar outros
        safe   = [u for u in all_links if _is_safe_source(u)]
        others = [u for u in all_links if not _is_safe_source(u)]
        random.shuffle(others)
        all_links = list(dict.fromkeys(safe + others))[:url_count]
        scraping_state["total"] = len(all_links)

        # ── Phase 2: scraping paralelo com semaforo ────────────────────────
        sem = asyncio.Semaphore(4)

        async def scrape_one(url: str):
            async with sem:
                await limiter.wait(url)
                scraping_state["current_url"] = url

                # Simula origem via busca
                referer = SEARCH_ENGINES[0](keywords[0]) if keywords else ""
                html = await _fetch_with_retry(client, url, referer=referer)

                # Playwright fallback para sites JS-heavy
                if html is None and not _is_safe_source(url):
                    html = await _playwright_fetch(url)

                if html:
                    text = _clean_text(html)
                    if text:
                        results.append({"url": url, "text": text})
                        scraping_state["bytes_collected"] += len(text.encode())
                        scraping_state["done"] += 1
                        return

                scraping_state["failed"] += 1
                await asyncio.sleep(random.uniform(0.5, 1.5))

        tasks = [scrape_one(link) for link in all_links]
        await asyncio.gather(*tasks)

    # Salvar resultados
    output = DATA_DIR / "scraped.jsonl"
    with output.open("w", encoding="utf-8") as f:
        for item in results:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    scraping_state["running"]  = False
    scraping_state["finished"] = True
