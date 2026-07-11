"""Web search tool using DuckDuckGo (free) or SerpAPI (optional upgrade)."""

from __future__ import annotations

import html
import logging
import os
import re
import time
from collections import OrderedDict

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.tools.base import BaseTool, ToolResult, ToolMeta, ConcurrencyMode

logger = logging.getLogger(__name__)


class WebSearchError(Exception):
    pass


_SERPAPI_KEY: str | None = None
_CACHE: OrderedDict[str, tuple[float, list[dict]]] = OrderedDict()
_CACHE_MAX = 32
_CACHE_TTL = 300  # 5 minutes

_CJK_RE = re.compile(r'[\u4e00-\u9fff\u3000-\u303f\uff00-\uffef]', re.UNICODE)


def _get_serpapi_key() -> str | None:
    global _SERPAPI_KEY
    if _SERPAPI_KEY is None:
        _SERPAPI_KEY = os.environ.get("SERPAPI_API_KEY")
    return _SERPAPI_KEY


def _extract_cjk_chars(text: str) -> set[str]:
    """Extract individual CJK characters from text for overlap scoring."""
    return set(_CJK_RE.findall(text))


def _compute_relevance(query: str, snippet: str) -> float:
    """Compute relevance score between query and snippet, CJK-aware."""
    query_lower = query.lower().strip()
    snippet_lower = snippet.lower().strip()

    cjk_query = _extract_cjk_chars(query_lower)
    cjk_snippet = _extract_cjk_chars(snippet_lower)

    if cjk_query:
        # CJK: character-level overlap
        if not cjk_snippet:
            return 0.0
        overlap = len(cjk_query & cjk_snippet)
        return overlap / len(cjk_query)

    # Non-CJK: word-level overlap
    query_words = set(query_lower.split())
    if not query_words:
        return 0.0
    snippet_words = set(snippet_lower.split())
    overlap = len(query_words & snippet_words)
    return overlap / len(query_words)


def _clean_results(raw: list[dict], query: str, max_results: int = 5) -> list[dict]:
    """Deduplicate, filter, and rank search results."""
    seen_urls: set[str] = set()
    clean: list[dict] = []

    for r in raw:
        url = (r.get("link") or r.get("url") or "").strip()
        snippet = (r.get("snippet") or r.get("description") or "").strip()

        if not url or url in seen_urls:
            continue
        seen_urls.add(url)

        if len(snippet) < 10:
            continue

        relevance = _compute_relevance(query, snippet)

        clean.append({
            "title": (r.get("title") or "").strip(),
            "url": url,
            "snippet": snippet,
            "relevance": round(relevance, 2),
        })

    clean.sort(key=lambda x: x["relevance"], reverse=True)
    return clean[:max_results]


def _cache_get(key: str) -> list[dict] | None:
    if key not in _CACHE:
        return None
    ts, data = _CACHE[key]
    if time.monotonic() - ts > _CACHE_TTL:
        del _CACHE[key]
        return None
    _CACHE.move_to_end(key)
    return data


def _cache_set(key: str, data: list[dict]):
    _CACHE[key] = (time.monotonic(), data)
    while len(_CACHE) > _CACHE_MAX:
        _CACHE.popitem(last=False)


async def _search_serpapi(query: str, max_results: int = 5) -> list[dict]:
    """Search via SerpAPI."""
    key = _get_serpapi_key()
    cache_key = f"serpapi:{query}:{max_results}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(
            "https://serpapi.com/search",
            params={
                "q": query,
                "api_key": key,
                "num": max_results + 3,
                "engine": "google",
            },
        )
        resp.raise_for_status()
        data = resp.json()

    raw = []
    for result in data.get("organic_results", []):
        raw.append({
            "title": result.get("title", ""),
            "link": result.get("link", ""),
            "snippet": result.get("snippet", ""),
        })
    results = _clean_results(raw, query, max_results)
    _cache_set(cache_key, results)
    return results


def _parse_ddg_lite_html(text: str) -> list[dict]:
    """Parse DuckDuckGo lite HTML into raw result dicts."""
    results = []
    # Match result rows with flexible class matching
    row_pattern = re.compile(
        r'<tr[^>]*class="[^"]*\bresult\b[^"]*"[^>]*>(.*?)</tr>',
        re.DOTALL | re.IGNORECASE,
    )
    for row_match in row_pattern.finditer(text):
        row = row_match.group(1)

        title_match = re.search(
            r'<a[^>]*class="[^"]*result-link[^"]*"[^>]*>(.*?)</a>',
            row, re.DOTALL | re.IGNORECASE,
        )
        if not title_match:
            continue

        title = html.unescape(re.sub(r'<[^>]+>', '', title_match.group(1)).strip())
        if not title:
            continue

        snippet = ""
        snippet_match = re.search(
            r'<td[^>]*class="[^"]*result-snippet[^"]*"[^>]*>(.*?)</td>',
            row, re.DOTALL | re.IGNORECASE,
        )
        if snippet_match:
            snippet = html.unescape(re.sub(r'<[^>]+>', '', snippet_match.group(1)).strip())

        url = ""
        url_match = re.search(r'href="(https?://[^"]+)"', row)
        if url_match:
            url = html.unescape(url_match.group(1))

        results.append({
            "title": title,
            "link": url,
            "snippet": snippet,
        })

    return results


async def _search_ddg_api(query: str, max_results: int = 5) -> list[dict]:
    """Fallback: search via DuckDuckGo Instant Answer API."""
    async with httpx.AsyncClient(timeout=8.0, follow_redirects=True) as client:
        resp = await client.get(
            "https://api.duckduckgo.com/",
            params={"q": query, "format": "json", "no_html": 1, "skip_disambig": 1},
            headers={"User-Agent": "Mozilla/5.0 (compatible; StoryCAD/1.0)"},
        )
        resp.raise_for_status()
        data = resp.json()

    raw = []

    abstract = data.get("AbstractText", "")
    abstract_src = data.get("AbstractSource", "")
    abstract_url = data.get("AbstractURL", "")
    if abstract and abstract_url:
        raw.append({"title": abstract_src, "link": abstract_url, "snippet": abstract})

    for topic in data.get("RelatedTopics", []):
        if "Topics" in topic:
            for sub in topic["Topics"]:
                text = sub.get("Text", "")
                url = sub.get("FirstURL", "") or sub.get("URL", "")
                if text and url:
                    raw.append({"title": sub.get("Result", "") or text[:60], "link": url, "snippet": text})
        else:
            text = topic.get("Text", "")
            url = topic.get("FirstURL", "") or topic.get("URL", "")
            if text and url:
                raw.append({"title": topic.get("Result", "") or text[:60], "link": url, "snippet": text})

    return _clean_results(raw, query, max_results)


async def _search_duckduckgo(query: str, max_results: int = 5) -> list[dict]:
    """Search via DuckDuckGo. Tries lite HTML first, falls back to Instant Answer API."""
    cache_key = f"ddg:{query}:{max_results}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    # Try lite endpoint first
    try:
        async with httpx.AsyncClient(timeout=8.0, follow_redirects=True) as client:
            resp = await client.post(
                "https://lite.duckduckgo.com/lite/",
                data={"q": query},
                headers={
                    "User-Agent": "Mozilla/5.0 (compatible; StoryCAD/1.0)",
                    "Accept": "text/html",
                },
            )
            resp.raise_for_status()

        raw = _parse_ddg_lite_html(resp.text)
        if raw:
            results = _clean_results(raw, query, max_results)
            _cache_set(cache_key, results)
            return results

        logger.info("DDG lite returned no results, falling back to API for query=%s", query)
    except Exception as e:
        logger.warning("DDG lite failed, falling back to API: %s", e)

    # Fallback to Instant Answer API
    results = await _search_ddg_api(query, max_results)
    _cache_set(cache_key, results)
    return results


class WebSearchTool(BaseTool):
    meta = ToolMeta(
        name="web_search",
        description="搜索网络获取实时信息。适用于查询最新新闻、事实数据、写作参考资料等。",
        concurrency=ConcurrencyMode.SAFE,
        search_hint="web search internet real-time",
    )
    name = "web_search"
    description = "搜索网络获取实时信息。适用于查询最新新闻、事实数据、写作参考资料等。"
    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "搜索关键词（支持中文）",
                "maxLength": 500,
            },
            "max_results": {
                "type": "integer",
                "description": "返回结果数量 (1-10)",
                "default": 5,
            },
        },
        "required": ["query"],
    }

    async def run(self, db: AsyncSession, **kwargs) -> ToolResult:
        query = kwargs.get("query", "").strip()
        if not query:
            return ToolResult(success=False, error="Query is required")

        max_results = max(1, min(kwargs.get("max_results", 5), 10))

        try:
            if _get_serpapi_key():
                results = await _search_serpapi(query, max_results)
            else:
                results = await _search_duckduckgo(query, max_results)
            return ToolResult(success=True, data=results)
        except Exception as e:
            logger.exception("web_search failed for query=%s", query)
            return ToolResult(success=False, error=str(e))
