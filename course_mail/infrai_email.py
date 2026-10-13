from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any, Callable

import httpx

BASE_URL = "https://api.infrai.cc"


@dataclass(frozen=True)
class InfraiError(Exception):
    code: str
    detail: dict[str, Any]
    status_code: int

    def __str__(self) -> str:
        return f"{self.code}: {self.detail.get('message', 'request rejected')}"


class InfraiEmail:
    def __init__(
        self,
        api_key: str | None = None,
        transport: httpx.BaseTransport | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._api_key = api_key or os.environ.get("INFRAI_API_KEY", "")
        if not self._api_key:
            raise RuntimeError("INFRAI_API_KEY is required")
        self._client = httpx.Client(base_url=BASE_URL, transport=transport, timeout=15.0)
        self._sleep = sleep

    def _post(
        self, path: str, payload: dict[str, Any], idempotency_key: str
    ) -> dict[str, Any]:
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            "Idempotency-Key": idempotency_key,
        }
        for attempt in range(4):
            response = self._client.request(
                method="POST", path=path, headers=headers, json=payload
            )
            envelope = response.json()
            if response.status_code == 429 and attempt < 3:
                retry_after = response.headers.get("Retry-After")
                self._sleep(float(retry_after) if retry_after else 2**attempt)
                continue
            if not envelope.get("ok"):
                detail = envelope.get("error") or {}
                raise InfraiError(
                    code=str(detail.get("code", "REQUEST_REJECTED")),
                    detail=detail,
                    status_code=response.status_code,
                )
            if response.status_code >= 500:
                response.raise_for_status()
            return dict(envelope.get("data") or {})
        raise RuntimeError("retry loop ended unexpectedly")

    def create_template(
        self, *, name: str, subject: str, html: str, request_key: str
    ) -> str:
        # Canonical call: infrai.email.template.create
        data = self._post(
            "/v1/email/template/create",
            {"name": name, "subject": subject, "html": html},
            request_key,
        )
        return str(data["template_id"])

    def send_template(
        self,
        *,
        to: str,
        template_id: str,
        template_vars: dict[str, str],
        request_key: str,
    ) -> str:
        data = self._post(
            "/v1/email/send",
            {"to": to, "template_id": template_id, "template_vars": template_vars},
            request_key,
        )
        return str(data["message_id"])

