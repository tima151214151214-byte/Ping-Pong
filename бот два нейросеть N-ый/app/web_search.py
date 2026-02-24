from __future__ import annotations

import re
from dataclasses import dataclass
from html import unescape

import httpx

_HTTP_HEADERS = {
    "User-Agent": "BibleTelegramBot/1.0 (+https://t.me/Bot736363637373bot)"
}


@dataclass(frozen=True)
class WebHit:
    title: str
    url: str
    snippet: str


async def search_web(query: str, max_results: int) -> list[WebHit]:
    hits = await _duckduckgo_instant(query=query, max_results=max_results)
    if len(hits) < max_results:
        needed = max_results - len(hits)
        for lang in ("ru", "en"):
            wiki_hits = await _wikipedia_search(query=query, max_results=needed, lang=lang)
            hits = _merge_hits(hits, wiki_hits)
            needed = max_results - len(hits)
            if needed <= 0:
                break
    return hits[:max_results]


async def _duckduckgo_instant(query: str, max_results: int) -> list[WebHit]:
    api_url = "https://api.duckduckgo.com/"
    params = {
        "q": query,
        "format": "json",
        "no_redirect": "1",
        "no_html": "1",
    }

    try:
        async with httpx.AsyncClient(timeout=12, headers=_HTTP_HEADERS) as client:
            response = await client.get(api_url, params=params)
            response.raise_for_status()
            payload = response.json()
    except Exception:
        return []

    hits: list[WebHit] = []

    abstract_text = str(payload.get("AbstractText", "")).strip()
    abstract_url = str(payload.get("AbstractURL", "")).strip()
    heading = str(payload.get("Heading", "")).strip() or "DuckDuckGo Abstract"
    if abstract_text and abstract_url:
        hits.append(WebHit(title=heading, url=abstract_url, snippet=abstract_text))

    related_topics = payload.get("RelatedTopics", [])
    if isinstance(related_topics, list):
        for item in related_topics:
            if len(hits) >= max_results:
                break
            if isinstance(item, dict) and "Topics" in item:
                nested_topics = item.get("Topics", [])
                if isinstance(nested_topics, list):
                    for nested in nested_topics:
                        if len(hits) >= max_results:
                            break
                        _append_related_hit(hits, nested)
                continue
            _append_related_hit(hits, item)

    return hits[:max_results]


def _append_related_hit(target: list[WebHit], item: object) -> None:
    if not isinstance(item, dict):
        return
    text = str(item.get("Text", "")).strip()
    url = str(item.get("FirstURL", "")).strip()
    if not text or not url:
        return
    title = text.split(" - ", maxsplit=1)[0].strip() or "DuckDuckGo Result"
    target.append(WebHit(title=title, url=url, snippet=text))


async def _wikipedia_search(query: str, max_results: int, lang: str) -> list[WebHit]:
    api_url = f"https://{lang}.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "list": "search",
        "srsearch": query,
        "format": "json",
        "utf8": "1",
        "srlimit": str(max_results),
    }

    try:
        async with httpx.AsyncClient(timeout=12, headers=_HTTP_HEADERS) as client:
            response = await client.get(api_url, params=params)
            response.raise_for_status()
            payload = response.json()
    except Exception:
        return []

    search_items = payload.get("query", {}).get("search", [])
    if not isinstance(search_items, list):
        return []

    rows: list[WebHit] = []
    for item in search_items:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title", "")).strip()
        page_id = item.get("pageid")
        raw_snippet = str(item.get("snippet", "")).strip()
        timestamp = str(item.get("timestamp", "")).strip()

        if not title or not isinstance(page_id, int):
            continue

        clean_snippet = _clean_html(raw_snippet)
        if timestamp:
            clean_snippet = f"{clean_snippet} (updated: {timestamp})"

        url = f"https://{lang}.wikipedia.org/?curid={page_id}"
        rows.append(WebHit(title=title, url=url, snippet=clean_snippet))

    return rows[:max_results]


def _clean_html(text: str) -> str:
    without_tags = re.sub(r"<[^>]+>", "", text)
    return unescape(without_tags).strip()


def _merge_hits(primary: list[WebHit], extra: list[WebHit]) -> list[WebHit]:
    seen_urls = {hit.url for hit in primary}
    merged = list(primary)
    for hit in extra:
        if hit.url in seen_urls:
            continue
        merged.append(hit)
        seen_urls.add(hit.url)
    return merged


def format_web_hits(hits: list[WebHit]) -> str:
    if not hits:
        return "No web results available."

    lines: list[str] = []
    for idx, hit in enumerate(hits, start=1):
        lines.append(f"{idx}. {hit.title}\nURL: {hit.url}\nSnippet: {hit.snippet}")
    return "\n\n".join(lines)
