"""HTTP API route handlers split by method."""

from __future__ import annotations

from .delete_routes import handle_delete
from .get_routes import handle_get
from .post_routes import handle_post
from .put_routes import handle_put

__all__ = ["handle_delete", "handle_get", "handle_post", "handle_put"]
