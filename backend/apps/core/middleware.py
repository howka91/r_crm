"""Audit-log middleware.

Captures state-changing API requests (POST/PUT/PATCH/DELETE) into AuditLog.
GET requests are not logged (too noisy).

Bodies and responses are truncated to a safe size to keep rows compact.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Callable

from django.http import HttpRequest, HttpResponse
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger(__name__)

LOGGED_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
MAX_PAYLOAD_BYTES = 8 * 1024  # 8 KB
# Skip admin / docs / schema / media / static — not part of the API surface we care about.
SKIP_PATH_PREFIXES = (
    "/admin/",
    "/static/",
    "/media/",
    "/api/schema",
    "/api/docs",
    "/api/redoc",
)


def _client_ip(request: HttpRequest) -> str | None:
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def _truncate(data: Any, limit: int = MAX_PAYLOAD_BYTES) -> Any:
    """Serialize to JSON and truncate if too large."""
    try:
        encoded = json.dumps(data, ensure_ascii=False, default=str)
    except (TypeError, ValueError):
        return {"_error": "unserialisable"}
    if len(encoded.encode("utf-8")) <= limit:
        return data
    return {"_truncated": True, "_preview": encoded[:limit]}


class AuditLogMiddleware(MiddlewareMixin):
    """Logs mutating requests to the `core.AuditLog` table."""

    def process_request(self, request: HttpRequest) -> None:
        request._audit_payload = self._extract_payload(request)

    def process_response(
        self, request: HttpRequest, response: HttpResponse
    ) -> HttpResponse:
        if not self._should_log(request):
            return response

        # Lazy import to avoid AppRegistryNotReady at start-up.
        from apps.core.models import AuditLog

        actor = getattr(request, "user", None)
        actor_id = actor.pk if actor and actor.is_authenticated else None

        try:
            AuditLog.objects.create(
                actor_id=actor_id,
                method=request.method,
                path=request.path[:512],
                status_code=response.status_code,
                ip_address=_client_ip(request),
                user_agent=request.META.get("HTTP_USER_AGENT", "")[:512],
                payload=_truncate(getattr(request, "_audit_payload", {})),
                response_summary=self._response_summary(response),
            )
        except Exception:  # pragma: no cover — never break the request flow
            logger.exception("AuditLog write failed")

        return response

    # --- internals ---

    @staticmethod
    def _should_log(request: HttpRequest) -> bool:
        if request.method not in LOGGED_METHODS:
            return False
        return not any(request.path.startswith(p) for p in SKIP_PATH_PREFIXES)

    @staticmethod
    def _extract_payload(request: HttpRequest) -> Any:
        if request.method not in LOGGED_METHODS:
            return {}
        content_type = request.META.get("CONTENT_TYPE", "")
        if "application/json" in content_type:
            try:
                return json.loads(request.body.decode("utf-8") or "{}")
            except (UnicodeDecodeError, json.JSONDecodeError):
                return {"_unparsable_body": True}
        if "multipart/form-data" in content_type:
            # Don't log file blobs — just field names.
            return {"_form_fields": list(request.POST.keys())}
        return {}

    @staticmethod
    def _response_summary(response: HttpResponse) -> dict[str, Any]:
        """For non-2xx responses, include the body (truncated) to aid debugging."""
        if 200 <= response.status_code < 300:
            return {}
        try:
            body = response.content.decode("utf-8")[:1024]
        except UnicodeDecodeError:
            body = ""
        return {"body": body}
