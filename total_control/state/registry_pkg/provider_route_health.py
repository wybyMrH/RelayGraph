from __future__ import annotations

from typing import Any

from .provider_profiles import provider_profile_health, provider_profile_kind


def build_provider_route_health(
    profiles: list[Any],
    agents: list[Any],
    templates: list[Any],
    workspaces: list[Any],
) -> dict[str, Any]:
    all_profile_index = {
        str(profile.get("id") or "").strip(): profile
        for profile in profiles
        if isinstance(profile, dict) and str(profile.get("id") or "").strip()
    }
    profile_index = {
        profile_id: profile
        for profile_id, profile in all_profile_index.items()
        if provider_profile_kind(profile) == "llm"
    }
    search_profile_index = {
        profile_id: profile
        for profile_id, profile in all_profile_index.items()
        if provider_profile_kind(profile) == "search"
    }
    profile_health = {
        profile_id: provider_profile_health(profile)
        for profile_id, profile in profile_index.items()
    }
    issues: list[dict[str, Any]] = []

    def add_issue(severity: str, code: str, message: str, **extra: Any) -> None:
        issue = {
            "severity": severity,
            "code": code,
            "message": message,
        }
        issue.update({key: value for key, value in extra.items() if value not in (None, "")})
        issues.append(issue)

    configured_profiles = sum(1 for item in profile_health.values() if item.get("ready"))
    for profile_id, profile in profile_index.items():
        health = profile_health.get(profile_id, {})
        missing_fields = health.get("missing_fields") if isinstance(health.get("missing_fields"), list) else []
        missing_severity = "warning" if configured_profiles else "blocking"
        if "api_key" in missing_fields:
            add_issue(missing_severity, "provider_missing_api_key", f"Provider Profile {profile.get('name') or profile_id} 没有 API key。", provider_profile_id=profile_id)
        if "models" in missing_fields:
            add_issue("warning", "provider_missing_model", f"Provider Profile {profile.get('name') or profile_id} 没有模型。", provider_profile_id=profile_id)
        if "base_url" in missing_fields:
            add_issue(missing_severity, "provider_missing_base_url", f"Provider Profile {profile.get('name') or profile_id} 没有 Base URL。", provider_profile_id=profile_id)

    if not profile_index:
        add_issue("blocking", "no_provider_profiles", "还没有 Provider Profile，Agent 无法真实调用模型。")

    for agent in agents:
        if not isinstance(agent, dict):
            continue
        agent_id = str(agent.get("id") or "").strip()
        if agent.get("enabled") is False:
            continue
        agent_profile_id = str(agent.get("provider_profile_id") or "").strip()
        if agent_profile_id and agent_profile_id not in profile_index:
            add_issue(
                "warning",
                "agent_unknown_provider_profile",
                f"Agent {agent.get('name') or agent_id} 指向不存在的 Provider Profile {agent_profile_id}。",
                agent_id=agent_id,
                provider_profile_id=agent_profile_id,
            )
        elif agent_profile_id and not profile_health.get(agent_profile_id, {}).get("ready"):
            add_issue(
                "warning",
                "agent_provider_profile_not_ready",
                f"Agent {agent.get('name') or agent_id} 的 Provider Profile {agent_profile_id} 未就绪。",
                agent_id=agent_id,
                provider_profile_id=agent_profile_id,
            )

    for template in templates:
        if not isinstance(template, dict):
            continue
        template_id = str(template.get("id") or "").strip()
        model = template.get("model") if isinstance(template.get("model"), dict) else {}
        template_profile_id = str(model.get("provider_profile_id") or "").strip()
        routing_mode = str(model.get("routing_mode") or "workspace_default").strip() or "workspace_default"
        if template_profile_id and template_profile_id not in profile_index:
            add_issue(
                "warning",
                "template_unknown_provider_profile",
                f"模板 {template.get('name') or template_id} 指向不存在的 Provider Profile {template_profile_id}。",
                template_id=template_id,
                provider_profile_id=template_profile_id,
            )
        elif template_profile_id and not profile_health.get(template_profile_id, {}).get("ready"):
            add_issue(
                "warning",
                "template_provider_profile_not_ready",
                f"模板 {template.get('name') or template_id} 的 Provider Profile {template_profile_id} 未就绪。",
                template_id=template_id,
                provider_profile_id=template_profile_id,
            )
        if routing_mode == "workspace_default" and not template_profile_id and not configured_profiles:
            add_issue(
                "blocking",
                "template_without_provider_route",
                f"模板 {template.get('name') or template_id} 没有默认 Provider，且全局没有可用 Profile。",
                template_id=template_id,
            )

    for workspace in workspaces:
        if not isinstance(workspace, dict):
            continue
        workspace_id = str(workspace.get("id") or "").strip()
        model = workspace.get("model") if isinstance(workspace.get("model"), dict) else {}
        workspace_profile_id = str(model.get("provider_profile_id") or "").strip()
        if workspace_profile_id and workspace_profile_id not in profile_index:
            add_issue(
                "warning",
                "workspace_unknown_provider_profile",
                f"实例 {workspace.get('name') or workspace_id} 指向不存在的 Provider Profile {workspace_profile_id}。",
                workspace_id=workspace_id,
                provider_profile_id=workspace_profile_id,
            )
        elif workspace_profile_id and not profile_health.get(workspace_profile_id, {}).get("ready"):
            add_issue(
                "warning",
                "workspace_provider_profile_not_ready",
                f"实例 {workspace.get('name') or workspace_id} 的 Provider Profile {workspace_profile_id} 未就绪。",
                workspace_id=workspace_id,
                provider_profile_id=workspace_profile_id,
            )

    blocking_count = sum(1 for item in issues if item.get("severity") == "blocking")
    warning_count = sum(1 for item in issues if item.get("severity") == "warning")
    return {
        "status": "blocked" if blocking_count else "warning" if warning_count else "ready",
        "profile_count": len(profile_index),
        "configured_profile_count": configured_profiles,
        "search_profile_count": len(search_profile_index),
        "configured_search_profile_count": sum(
            1 for profile in search_profile_index.values()
            if provider_profile_health(profile).get("ready")
        ),
        "agent_count": len([item for item in agents if isinstance(item, dict)]),
        "template_count": len([item for item in templates if isinstance(item, dict)]),
        "workspace_count": len([item for item in workspaces if isinstance(item, dict)]),
        "blocking_count": blocking_count,
        "warning_count": warning_count,
        "profiles": [
            {
                "id": profile_id,
                "name": str(profile_index.get(profile_id, {}).get("name") or profile_id),
                **profile_health.get(profile_id, {}),
            }
            for profile_id in sorted(profile_index)
        ],
        "issues": issues,
    }
