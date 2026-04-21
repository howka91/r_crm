"""Health-check and other cross-cutting endpoints."""
from __future__ import annotations

from django.db import connection
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView


class HealthView(APIView):
    """Simple liveness + DB connectivity probe.

    Used by docker-compose healthchecks and external monitoring.
    """

    permission_classes = (AllowAny,)
    authentication_classes = ()

    def get(self, request) -> Response:
        db_ok = True
        try:
            with connection.cursor() as cur:
                cur.execute("SELECT 1")
                cur.fetchone()
        except Exception:
            db_ok = False

        payload = {"status": "ok" if db_ok else "degraded", "db": db_ok}
        http_status = status.HTTP_200_OK if db_ok else status.HTTP_503_SERVICE_UNAVAILABLE
        return Response(payload, status=http_status)
