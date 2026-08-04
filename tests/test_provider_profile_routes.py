from __future__ import annotations

from types import SimpleNamespace

from total_control.http_api.delete_routes import handle_delete
from total_control.http_api.get_routes import handle_get
from total_control.http_api.post_routes import handle_post
from total_control.http_api.put_routes import handle_put


class _JsonHandler:
    headers: dict[str, str] = {}

    def __init__(self, body: dict[str, object] | None = None) -> None:
        self.body = body or {}
        self.payload: dict[str, object] | None = None
        self.status: object = None

    def read_body(self) -> dict[str, object]:
        return dict(self.body)

    def send_json(self, payload: dict[str, object], status: object = None) -> None:
        self.payload = payload
        self.status = status


class _ProviderProfileState:
    def __init__(self) -> None:
        self.get_id = ""
        self.updated: tuple[str, dict[str, object]] | None = None
        self.deleted_id = ""
        self.provider_profiles = [
            {
                "id": "profile-a",
                "name": "OpenAI Main",
                "api_key_masked": "sk-test...1234",
                "has_api_key": True,
                "status": "ready",
                "missing_fields": [],
            }
        ]

    def provider_profile_public_by_id(self, profile_id: str) -> dict[str, object] | None:
        self.get_id = profile_id
        return next((item for item in self.provider_profiles if item["id"] == profile_id), None)

    def update_provider_profile(self, profile_id: str, payload: dict[str, object]) -> dict[str, object]:
        self.updated = (profile_id, payload)
        return {"id": profile_id, **payload, "has_api_key": True}

    def delete_provider_profile(self, profile_id: str) -> None:
        self.deleted_id = profile_id


def _parsed(path: str) -> SimpleNamespace:
    return SimpleNamespace(path=path, query="")


def test_provider_profile_get_route_matches_single_resource():
    state = _ProviderProfileState()
    handler = _JsonHandler()

    handled = handle_get(handler, state, _parsed("/api/provider-profiles/profile-a"))

    assert handled is True
    assert state.get_id == "profile-a"
    assert handler.payload == {"provider_profile": state.provider_profiles[0]}


def test_provider_profile_get_route_rejects_nested_resource_path():
    state = _ProviderProfileState()
    handler = _JsonHandler()

    handled = handle_get(handler, state, _parsed("/api/provider-profiles/profile-a/extra"))

    assert handled is True
    assert state.get_id == ""
    assert handler.payload == {"error": "not found"}


def test_provider_profile_put_route_matches_single_resource():
    state = _ProviderProfileState()
    handler = _JsonHandler({"name": "Updated"})

    handled = handle_put(handler, state, _parsed("/api/provider-profiles/profile-a"))

    assert handled is True
    assert state.updated == ("profile-a", {"name": "Updated"})
    assert handler.payload == {"provider_profile": {"id": "profile-a", "name": "Updated", "has_api_key": True}}


def test_provider_profile_post_fallback_route_matches_single_resource():
    state = _ProviderProfileState()
    handler = _JsonHandler({"name": "Updated"})

    handled = handle_post(handler, state, _parsed("/api/provider-profiles/profile-a"))

    assert handled is True
    assert state.updated == ("profile-a", {"name": "Updated"})
    assert handler.payload == {"provider_profile": {"id": "profile-a", "name": "Updated", "has_api_key": True}}


def test_provider_profile_delete_route_matches_single_resource():
    state = _ProviderProfileState()
    handler = _JsonHandler()

    handled = handle_delete(handler, state, _parsed("/api/provider-profiles/profile-a"))

    assert handled is True
    assert state.deleted_id == "profile-a"
    assert handler.payload == {"ok": True}
