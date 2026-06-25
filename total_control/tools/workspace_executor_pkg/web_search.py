from __future__ import annotations

import html
import json
import os
import re
import time
import urllib.parse
import urllib.request
from typing import Any


def workspace_seed_results(context: Any) -> list[dict[str, str]]:
    source = context.source_payload()
    return [
        {"type": "repo", "url": url, "title": url, "source": "workspace.input"}
        for url in source["repo_urls"]
    ] + [
        {"type": "paper", "url": url, "title": url, "source": "workspace.input"}
        for url in source["paper_urls"]
    ]


def execute_web_search(context: Any, arguments: dict[str, Any]) -> dict[str, Any]:
    started = time.monotonic()
    source = context.source_payload()
    query = str(arguments.get("query") or source.get("goal_text") or "").strip()
    try:
        limit = max(1, min(int(float(arguments.get("limit") or 5)), 10))
    except (TypeError, ValueError):
        limit = 5
    seeds = workspace_seed_results(context)
    endpoint = str(arguments.get("endpoint") or os.environ.get("TOTAL_CONTROL_WEB_SEARCH_ENDPOINT") or "").strip()
    provider = str(arguments.get("provider") or os.environ.get("TOTAL_CONTROL_WEB_SEARCH_PROVIDER") or "").strip().lower()

    if endpoint:
        payload = _execute_endpoint_search(endpoint, query, limit, seeds)
    elif provider in {"duckduckgo", "ddg"} or bool(arguments.get("network")):
        payload = _execute_duckduckgo_search(query, limit, seeds)
    else:
        payload = {
            "status": "seeded" if seeds else "unconfigured",
            "query": query,
            "provider": provider or "",
            "provider_configured": False,
            "provider_status": "unconfigured",
            "fallback_used": bool(seeds),
            "results": seeds[:limit],
            "message": (
                "返回工作台已有搜索种子；设置 TOTAL_CONTROL_WEB_SEARCH_PROVIDER=duckduckgo "
                "或 TOTAL_CONTROL_WEB_SEARCH_ENDPOINT 接入真实搜索。"
            ),
        }
    latency_ms = round((time.monotonic() - started) * 1000, 1)
    results = payload.get("results") if isinstance(payload.get("results"), list) else []
    payload["latency_ms"] = latency_ms
    payload["result_count"] = len(results)
    payload["result_provenance"] = [
        str(item.get("source") or "unknown").strip() or "unknown"
        for item in results
        if isinstance(item, dict)
    ][:limit]
    payload["rate_limit"] = {
        "provider": str(payload.get("provider") or provider or "seed").strip(),
        "max_results": limit,
        "hint": "DuckDuckGo HTML 接口未提供官方 quota；endpoint 模式取决于远端服务。",
    }
    return payload


def _execute_endpoint_search(endpoint: str, query: str, limit: int, seeds: list[dict[str, str]]) -> dict[str, Any]:
    if not query:
        return {
            "status": "seeded" if seeds else "blocked",
            "query": query,
            "provider": "endpoint",
            "provider_configured": True,
            "provider_status": "blocked",
            "fallback_used": bool(seeds),
            "results": seeds[:limit],
            "error": "query is required",
            "message": "缺少检索词，已返回 workspace 种子。" if seeds else "query is required",
        }
    api_key = os.environ.get("TOTAL_CONTROL_WEB_SEARCH_API_KEY", "")
    url = endpoint
    data: bytes | None = None
    headers = {"Accept": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    if "{query}" in endpoint:
        url = endpoint.replace("{query}", urllib.parse.quote(query))
    else:
        sep = "&" if "?" in endpoint else "?"
        url = f"{endpoint}{sep}{urllib.parse.urlencode({'q': query, 'limit': limit})}"
    try:
        request = urllib.request.Request(url, data=data, headers=headers, method="GET")
        with urllib.request.urlopen(request, timeout=12) as response:
            payload = json.loads(response.read().decode("utf-8", errors="replace"))
        results = _normalize_endpoint_results(payload, limit)
        fallback_used = not results and bool(seeds)
        return {
            "status": "found" if results else "seeded" if fallback_used else "empty",
            "query": query,
            "provider": "endpoint",
            "provider_configured": True,
            "provider_status": "found" if results else "empty",
            "fallback_used": fallback_used,
            "results": (results or seeds)[:limit],
            "message": "" if results else "搜索 provider 未返回结果，已返回 workspace 种子。" if fallback_used else "搜索 provider 未返回结果。",
        }
    except Exception as exc:  # noqa: BLE001 - provider failures should degrade inside the tool.
        fallback_used = bool(seeds)
        return {
            "status": "seeded" if fallback_used else "error",
            "query": query,
            "provider": "endpoint",
            "provider_configured": True,
            "provider_status": "error",
            "fallback_used": fallback_used,
            "results": seeds[:limit],
            "error": str(exc),
            "message": "搜索 provider 失败，已返回 workspace 种子。" if fallback_used else "搜索 provider 失败。",
        }


def _execute_duckduckgo_search(query: str, limit: int, seeds: list[dict[str, str]]) -> dict[str, Any]:
    if not query:
        return {
            "status": "seeded" if seeds else "blocked",
            "query": query,
            "provider": "duckduckgo",
            "provider_configured": True,
            "provider_status": "blocked",
            "fallback_used": bool(seeds),
            "results": seeds[:limit],
            "error": "query is required",
            "message": "缺少检索词，已返回 workspace 种子。" if seeds else "query is required",
        }
    try:
        url = "https://duckduckgo.com/html/?" + urllib.parse.urlencode({"q": query})
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": "RelayGraph/1.0 (+workspace web.search)",
                "Accept": "text/html,application/xhtml+xml",
            },
            method="GET",
        )
        with urllib.request.urlopen(request, timeout=12) as response:
            body = response.read().decode("utf-8", errors="replace")
        results = _parse_duckduckgo_html(body, limit)
        fallback_used = not results and bool(seeds)
        return {
            "status": "found" if results else "seeded" if fallback_used else "empty",
            "query": query,
            "provider": "duckduckgo",
            "provider_configured": True,
            "provider_status": "found" if results else "empty",
            "fallback_used": fallback_used,
            "results": (results or seeds)[:limit],
            "message": "" if results else "DuckDuckGo 未返回结果，已返回 workspace 种子。" if fallback_used else "DuckDuckGo 未返回结果。",
        }
    except Exception as exc:  # noqa: BLE001 - search should not break the agent loop.
        fallback_used = bool(seeds)
        return {
            "status": "seeded" if fallback_used else "error",
            "query": query,
            "provider": "duckduckgo",
            "provider_configured": True,
            "provider_status": "error",
            "fallback_used": fallback_used,
            "results": seeds[:limit],
            "error": str(exc),
            "message": "DuckDuckGo 搜索失败，已返回 workspace 种子。" if fallback_used else "DuckDuckGo 搜索失败。",
        }


def _normalize_endpoint_results(payload: Any, limit: int) -> list[dict[str, str]]:
    raw = []
    if isinstance(payload, dict):
        for key in ("results", "items", "data"):
            if isinstance(payload.get(key), list):
                raw = payload[key]
                break
    elif isinstance(payload, list):
        raw = payload
    results: list[dict[str, str]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        url = str(item.get("url") or item.get("link") or item.get("href") or "").strip()
        if not url:
            continue
        results.append(
            {
                "type": str(item.get("type") or "web").strip() or "web",
                "title": str(item.get("title") or item.get("name") or url).strip(),
                "url": url,
                "snippet": str(item.get("snippet") or item.get("description") or item.get("summary") or "").strip(),
                "source": str(item.get("source") or "provider").strip() or "provider",
            }
        )
        if len(results) >= limit:
            break
    return results


def _parse_duckduckgo_html(body: str, limit: int) -> list[dict[str, str]]:
    results: list[dict[str, str]] = []
    seen: set[str] = set()
    pattern = re.compile(r'<a[^>]+class="result__a"[^>]+href="(?P<href>[^"]+)"[^>]*>(?P<title>.*?)</a>', re.I | re.S)
    for match in pattern.finditer(body):
        raw_url = html.unescape(match.group("href"))
        parsed = urllib.parse.urlparse(raw_url)
        query = urllib.parse.parse_qs(parsed.query)
        url = query.get("uddg", [raw_url])[0]
        url = urllib.parse.unquote(url).strip()
        if not url or url in seen:
            continue
        title = re.sub(r"<[^>]+>", "", match.group("title"))
        title = html.unescape(" ".join(title.split())).strip() or url
        seen.add(url)
        results.append({"type": "web", "title": title, "url": url, "snippet": "", "source": "duckduckgo"})
        if len(results) >= limit:
            break
    return results
