"""Custom ``drf-spectacular`` ``AutoSchema``.

By default ``drf-spectacular`` derives an operation's Swagger tag from the
first URL-path segment (e.g. ``/api/v1/contracts/`` → ``contracts``). That
fractures logically-related endpoints across many top-level tags — e.g.
``client-contacts`` and ``client-requisites`` end up as separate groups
from ``clients``; ``contract-templates`` / ``payment-schedules`` /
``payments`` drift away from ``contracts``; the 13 lookup URLs get 13 tags.

``TaggedAutoSchema`` respects a ``schema_tags`` attribute on the view/
ViewSet and uses it verbatim. Views without the attribute fall back to
the default URL-segment behaviour. Ordering in the Swagger UI is
controlled by the ``TAGS`` list in ``SPECTACULAR_SETTINGS``.

Usage on a ViewSet::

    class ContractViewSet(viewsets.ModelViewSet):
        schema_tags = ["Договоры"]
        ...

On a plain APIView::

    class LoginView(APIView):
        schema_tags = ["Авторизация"]
        ...
"""
from __future__ import annotations

from drf_spectacular.openapi import AutoSchema


class TaggedAutoSchema(AutoSchema):
    def get_tags(self) -> list[str]:
        override = getattr(self.view, "schema_tags", None)
        if override:
            return list(override)
        return super().get_tags()
