"""Web search tool using DuckDuckGo (free) or SerpAPI (optional upgrade)."""

from __future__ import annotations

import logging
import os
import re

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.tools.base import BaseTool, ToolResult

logger = logging.getLogger(__name__)

SERPAPI_KEY = os.environ.get("SERPAPI_API_KEY")


class WebSearchError(Exception):
    pass


def _clean_results(raw: list[dict], query: str, max_results: int = 5) -> list[dict]:
    """Deduplicate, filter, and rank search results."""
    seen_urls: set[str] = set()
    clean: list[dict] = []

    for r in raw:
        url = r.get("link", r.get("url", ""))
        snippet = r.get("snippet", r.get("description", ""))

        if url in seen_urls or not url:
            continue
        seen_urls.add(url)

        if len(snippet.strip()) < 20:
            continue

        query_words = set(query.lower().split())
        snippet_words = set(snippet.lower().split())
        overlap = len(query_words & snippet_words)
        relevance = overlap / max(len(query_words), 1) if query_words else 0

        clean.append({
            "title": r.get("title", ""),
            "url": url,
            "snippet": snippet.strip(),
            "relevance": round(relevance, 2),
        })

    clean.sort(key=lambda x: x["relevance"], reverse=True)
    return clean[:max_results]


async def _search_serpapi(query: str, max_results: int = 5) -> list[dict]:
    """Search via SerpAPI."""
    if not SERPAPI_KEY:
        raise WebSearchError("SERPAPI_API_KEY not configured")

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(
            "https://serpapi.com/search",
            params={
                "q": query,
                "api_key": SERPAPI_KEY,
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
    return _clean_results(raw, query, max_results)


async def _search_duckduckgo(query: str, max_results: int = 5) -> list[dict]:
    """Search via DuckDuckGo HTML lite endpoint."""
    async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
        resp = await client.post(
            "https://lite.duckduckgo.com/lite/",
            data={"q": query},
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; StoryCAD/1.0)",
                "Accept": "text/html",
            },
        )
        resp.raise_for_status()

    text = resp.text
    results = []

    rows = re.findall(
        r'<tr[^>]*class="result"[^>]*>.*?</tr>',
        text,
        re.DOTALL,
    )
    for row in rows[:max_results + 3]:
        title_match = re.search(r'<a[^>]*class="result-link"[^>]*>(.*?)</a>', row, re.DOTALL)
        snippet_match = re.search(r'<td[^>]*class="result-snippet"[^>]*>(.*?)</td>', row, re.DOTALL)
        url_match = re.search(r'href="(https?://[^"]+)"', row)

        if title_match:
            title = re.sub(r'<[^>]+>', '', title_match.group(1)).strip()
            snippet = ""
            if snippet_match:
                snippet = re.sub(r'<[^>]+>', '', snippet_match.group(1)).strip()
            url = url_match.group(1) if url_match else ""

            if title and url:
                results.append({
                    "title": title,
                    "link": url,
                    "snippet": snippet,
                })

    return _clean_results(results, query, max_results)


class WebSearchTool(BaseTool):
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
            if SERPAPI_KEY:
                results = await _search_serpapi(query, max_results)
            else:
                results = await _search_duckduckgo(query, max_results)
            return ToolResult(success=True, data=results)
        except Exception as e:
            logger.exception("web_search failed for query=%s", query)
            return ToolResult(success=False, error=str(e))
