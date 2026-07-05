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
    arguments = arguments if isinstance(arguments, dict) else {}
    source = context.source_payload()
    query = str(arguments.get("query") or source.get("goal_text") or "").strip()
    try:
        limit = max(1, min(int(float(arguments.get("limit") or 5)), 10))
    except (TypeError, ValueError):
        limit = 5
    seeds = workspace_seed_results(context)
    profile = _search_profile_for_arguments(context, arguments)
    if str(arguments.get("provider_profile_id") or "").strip() and not profile:
        return {
            "status": "blocked",
            "query": query,
            "provider": "",
            "provider_configured": False,
            "provider_status": "blocked",
            "fallback_used": bool(seeds),
            "results": seeds[:limit],
            "error": "search provider profile not found",
            "message": "指定的 search provider profile 不存在，已返回 workspace 种子。" if seeds else "指定的 search provider profile 不存在。",
        }
    endpoint = str(
        profile.get("base_url")
        or arguments.get("endpoint")
        or os.environ.get("TOTAL_CONTROL_WEB_SEARCH_ENDPOINT")
        or ""
    ).strip()
    provider = str(
        profile.get("provider")
        or profile.get("search_provider")
        or arguments.get("provider")
        or os.environ.get("TOTAL_CONTROL_WEB_SEARCH_PROVIDER")
        or ""
    ).strip().lower()
    if not provider:
        if os.environ.get("TOTAL_CONTROL_FIRECRAWL_API_KEY"):
            provider = "firecrawl"
        elif os.environ.get("TOTAL_CONTROL_SERPER_API_KEY"):
            provider = "serper"

    if provider == "firecrawl":
        payload = _execute_firecrawl_search(query, limit, seeds, arguments, profile)
    elif provider == "serper":
        payload = _execute_serper_search(query, limit, seeds, arguments, profile)
    elif endpoint:
        payload = _execute_endpoint_search(endpoint, query, limit, seeds, profile)
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
    if profile:
        payload["provider_profile_id"] = str(profile.get("id") or "").strip()
        payload["provider_profile_name"] = str(profile.get("name") or "").strip()
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
        "hint": str(
            payload.get("rate_limit_hint")
            or "Firecrawl/Serper quota 取决于账号；DuckDuckGo HTML 接口未提供官方 quota；endpoint 模式取决于远端服务。"
        ).strip(),
    }
    payload.pop("rate_limit_hint", None)
    return payload


def _search_profile_for_arguments(context: Any, arguments: dict[str, Any]) -> dict[str, Any]:
    profile_id = str(arguments.get("provider_profile_id") or arguments.get("search_provider_profile_id") or "").strip()
    resolver = getattr(context, "search_provider_profile", None)
    if callable(resolver):
        profile = resolver(profile_id)
        if isinstance(profile, dict):
            return profile
    return {}


def _configured_search_key_from_profile(profile: dict[str, Any], env_name: str) -> str:
    return str(profile.get("api_key") or os.environ.get(env_name) or "").strip()


def _sanitize_provider_error(error: Any, *, api_key: str = "") -> str:
    text = str(error or "")
    if api_key:
        text = text.replace(api_key, "***")
    text = re.sub(r"(?i)(api[_-]?key|x-api-key|access[_-]?token|token|secret|password)=([^&\s]+)", r"\1=***", text)
    text = re.sub(r"(?i)(Authorization\s*[:=]\s*Bearer\s+)([^\s,;]+)", r"\1***", text)
    return text[:800]


def _json_request(
    url: str,
    *,
    payload: dict[str, Any],
    headers: dict[str, str],
    timeout: int = 15,
) -> Any:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            **headers,
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8", errors="replace"))


def _query_required_payload(
    *,
    query: str,
    provider: str,
    seeds: list[dict[str, str]],
    limit: int,
    configured: bool = True,
) -> dict[str, Any]:
    return {
        "status": "seeded" if seeds else "blocked",
        "query": query,
        "provider": provider,
        "provider_configured": configured,
        "provider_status": "blocked",
        "fallback_used": bool(seeds),
        "results": seeds[:limit],
        "error": "query is required",
        "message": "缺少检索词，已返回 workspace 种子。" if seeds else "query is required",
    }


def _missing_key_payload(
    *,
    query: str,
    provider: str,
    env_name: str,
    seeds: list[dict[str, str]],
    limit: int,
) -> dict[str, Any]:
    return {
        "status": "seeded" if seeds else "blocked",
        "query": query,
        "provider": provider,
        "provider_configured": False,
        "provider_status": "blocked",
        "fallback_used": bool(seeds),
        "results": seeds[:limit],
        "error": f"{env_name} is not configured",
        "message": f"未配置 {env_name}，已返回 workspace 种子。" if seeds else f"未配置 {env_name}。",
    }


def _execute_firecrawl_search(
    query: str,
    limit: int,
    seeds: list[dict[str, str]],
    arguments: dict[str, Any],
    profile: dict[str, Any],
) -> dict[str, Any]:
    if not query:
        return _query_required_payload(query=query, provider="firecrawl", seeds=seeds, limit=limit)
    api_key = _configured_search_key_from_profile(profile, "TOTAL_CONTROL_FIRECRAWL_API_KEY")
    if not api_key:
        return _missing_key_payload(
            query=query,
            provider="firecrawl",
            env_name="search provider api_key / TOTAL_CONTROL_FIRECRAWL_API_KEY",
            seeds=seeds,
            limit=limit,
        )
    base_url = str(
        profile.get("base_url")
        or arguments.get("base_url")
        or os.environ.get("TOTAL_CONTROL_FIRECRAWL_API_URL")
        or "https://api.firecrawl.dev"
    ).strip().rstrip("/")
    endpoint = base_url if base_url.endswith("/search") else f"{base_url}/v2/search"
    body: dict[str, Any] = {"query": query, "limit": limit}
    country = str(arguments.get("country") or "").strip()
    if country:
        body["country"] = country
    categories = _string_list(arguments.get("categories"))
    if categories:
        body["categories"] = categories
    include_domains = _string_list(arguments.get("include_domains") or arguments.get("includeDomains"))
    if include_domains:
        body["includeDomains"] = include_domains
    exclude_domains = _string_list(arguments.get("exclude_domains") or arguments.get("excludeDomains"))
    if exclude_domains:
        body["excludeDomains"] = exclude_domains
    if isinstance(arguments.get("scrape_options"), dict):
        body["scrapeOptions"] = arguments["scrape_options"]
    elif isinstance(arguments.get("scrapeOptions"), dict):
        body["scrapeOptions"] = arguments["scrapeOptions"]
    try:
        payload = _json_request(
            endpoint,
            payload=body,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=15,
        )
        results = _normalize_firecrawl_results(payload, limit)
        fallback_used = not results and bool(seeds)
        return {
            "status": "found" if results else "seeded" if fallback_used else "empty",
            "query": query,
            "provider": "firecrawl",
            "provider_configured": True,
            "provider_status": "found" if results else "empty",
            "fallback_used": fallback_used,
            "results": (results or seeds)[:limit],
            "message": "" if results else "Firecrawl 未返回结果，已返回 workspace 种子。" if fallback_used else "Firecrawl 未返回结果。",
            "rate_limit_hint": "Firecrawl hosted/self-hosted quota 取决于账号或部署策略。",
        }
    except Exception as exc:  # noqa: BLE001 - search must degrade inside the agent loop.
        fallback_used = bool(seeds)
        return {
            "status": "seeded" if fallback_used else "error",
            "query": query,
            "provider": "firecrawl",
            "provider_configured": True,
            "provider_status": "error",
            "fallback_used": fallback_used,
            "results": seeds[:limit],
            "error": _sanitize_provider_error(exc, api_key=api_key),
            "message": "Firecrawl 搜索失败，已返回 workspace 种子。" if fallback_used else "Firecrawl 搜索失败。",
            "rate_limit_hint": "Firecrawl hosted/self-hosted quota 取决于账号或部署策略。",
        }


def _execute_serper_search(
    query: str,
    limit: int,
    seeds: list[dict[str, str]],
    arguments: dict[str, Any],
    profile: dict[str, Any],
) -> dict[str, Any]:
    if not query:
        return _query_required_payload(query=query, provider="serper", seeds=seeds, limit=limit)
    api_key = _configured_search_key_from_profile(profile, "TOTAL_CONTROL_SERPER_API_KEY")
    if not api_key:
        return _missing_key_payload(
            query=query,
            provider="serper",
            env_name="search provider api_key / TOTAL_CONTROL_SERPER_API_KEY",
            seeds=seeds,
            limit=limit,
        )
    endpoint = str(
        profile.get("base_url")
        or arguments.get("endpoint")
        or os.environ.get("TOTAL_CONTROL_SERPER_SEARCH_URL")
        or "https://google.serper.dev/search"
    ).strip()
    body = {"q": query, "num": limit}
    location = str(arguments.get("location") or "").strip()
    if location:
        body["location"] = location
    try:
        payload = _json_request(
            endpoint,
            payload=body,
            headers={"X-API-KEY": api_key},
            timeout=15,
        )
        results = _normalize_serper_results(payload, limit)
        fallback_used = not results and bool(seeds)
        return {
            "status": "found" if results else "seeded" if fallback_used else "empty",
            "query": query,
            "provider": "serper",
            "provider_configured": True,
            "provider_status": "found" if results else "empty",
            "fallback_used": fallback_used,
            "results": (results or seeds)[:limit],
            "message": "" if results else "Serper 未返回结果，已返回 workspace 种子。" if fallback_used else "Serper 未返回结果。",
            "rate_limit_hint": "Serper quota 取决于账号套餐。",
        }
    except Exception as exc:  # noqa: BLE001 - search must degrade inside the agent loop.
        fallback_used = bool(seeds)
        return {
            "status": "seeded" if fallback_used else "error",
            "query": query,
            "provider": "serper",
            "provider_configured": True,
            "provider_status": "error",
            "fallback_used": fallback_used,
            "results": seeds[:limit],
            "error": _sanitize_provider_error(exc, api_key=api_key),
            "message": "Serper 搜索失败，已返回 workspace 种子。" if fallback_used else "Serper 搜索失败。",
            "rate_limit_hint": "Serper quota 取决于账号套餐。",
        }


def _execute_endpoint_search(
    endpoint: str,
    query: str,
    limit: int,
    seeds: list[dict[str, str]],
    profile: dict[str, Any],
) -> dict[str, Any]:
    if not query:
        return _query_required_payload(query=query, provider="endpoint", seeds=seeds, limit=limit)
    api_key = str(profile.get("api_key") or os.environ.get("TOTAL_CONTROL_WEB_SEARCH_API_KEY") or "").strip()
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
            "error": _sanitize_provider_error(exc, api_key=api_key),
            "message": "搜索 provider 失败，已返回 workspace 种子。" if fallback_used else "搜索 provider 失败。",
        }


def _execute_duckduckgo_search(query: str, limit: int, seeds: list[dict[str, str]]) -> dict[str, Any]:
    if not query:
        return _query_required_payload(query=query, provider="duckduckgo", seeds=seeds, limit=limit)
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
            "error": _sanitize_provider_error(exc),
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


def _string_list(value: Any) -> list[str]:
    if isinstance(value, str):
        raw_items = re.split(r"[,\n]", value)
    elif isinstance(value, list):
        raw_items = value
    else:
        raw_items = []
    items: list[str] = []
    for item in raw_items:
        text = str(item or "").strip()
        if text and text not in items:
            items.append(text)
    return items


def _normalize_firecrawl_results(payload: Any, limit: int) -> list[dict[str, str]]:
    source_items: list[Any] = []
    if isinstance(payload, dict):
        data = payload.get("data")
        if isinstance(data, dict):
            for key in ("web", "news", "images"):
                if isinstance(data.get(key), list):
                    source_items.extend(data[key])
        elif isinstance(data, list):
            source_items = data
        elif isinstance(payload.get("results"), list):
            source_items = payload["results"]
    elif isinstance(payload, list):
        source_items = payload
    return _normalize_search_items(source_items, limit, source="firecrawl")


def _normalize_serper_results(payload: Any, limit: int) -> list[dict[str, str]]:
    source_items: list[Any] = []
    if isinstance(payload, dict):
        for key in ("organic", "news", "places"):
            if isinstance(payload.get(key), list):
                source_items.extend(payload[key])
        if not source_items and isinstance(payload.get("results"), list):
            source_items = payload["results"]
    elif isinstance(payload, list):
        source_items = payload
    return _normalize_search_items(source_items, limit, source="serper")


def _normalize_search_items(items: list[Any], limit: int, *, source: str) -> list[dict[str, str]]:
    results: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in items:
        if not isinstance(item, dict):
            continue
        url = str(item.get("url") or item.get("link") or item.get("href") or item.get("website") or "").strip()
        if not url or url in seen:
            continue
        seen.add(url)
        results.append(
            {
                "type": str(item.get("type") or "web").strip() or "web",
                "title": str(item.get("title") or item.get("name") or url).strip(),
                "url": url,
                "snippet": str(item.get("description") or item.get("snippet") or item.get("summary") or "").strip(),
                "source": str(item.get("source") or source).strip() or source,
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
