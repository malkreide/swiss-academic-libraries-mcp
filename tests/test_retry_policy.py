"""Retry-Policy: Retry-After, Jitter und der Deckel.

Zusammen mit dem gehärteten Retry aus der mcp-data-source-probe-Vorlage
übernommen. Geprüft wird das Verhalten, nicht die Konstanten.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from email.utils import format_datetime

import httpx

from swiss_academic_libraries_mcp import api_client

# --- Retry policy: Retry-After, jitter, and the cap --------------------------
# Adopted together with the hardened retry from the mcp-data-source-probe
# reference template. These assert the behaviour, not the constants: a
# deterministic ladder and an unread `Retry-After` are what a sweep across
# eleven servers found on 2026-08-03, and every one of them looked fine.


def _retry_after_error(value: str) -> httpx.HTTPStatusError:
    request = httpx.Request("GET", "https://example.invalid/")
    return httpx.HTTPStatusError(
        "",
        request=request,
        response=httpx.Response(429, headers={"Retry-After": value}, request=request),
    )


def test_retry_after_reads_both_rfc9110_forms() -> None:
    def resp(status: int, headers: dict[str, str]) -> httpx.Response:
        request = httpx.Request("GET", "https://example.invalid/")
        return httpx.Response(status, headers=headers, request=request)

    assert api_client.parse_retry_after(resp(429, {"Retry-After": "120"})) == 120.0

    later = format_datetime(datetime.now(UTC) + timedelta(seconds=90))
    seconds = api_client.parse_retry_after(resp(503, {"Retry-After": later}))
    assert seconds is not None and 80 < seconds <= 90

    # A date in the past means "now", never a negative wait.
    past = "Wed, 21 Oct 2020 07:28:00 GMT"
    assert api_client.parse_retry_after(resp(503, {"Retry-After": past})) == 0.0

    # Unparseable falls back to the curve. It must not crash on the error path,
    # which is the one path already going badly.
    assert api_client.parse_retry_after(resp(429, {"Retry-After": "bald"})) is None
    assert api_client.parse_retry_after(resp(429, {})) is None

    # 500 does not carry a meaningful Retry-After.
    assert api_client.parse_retry_after(resp(500, {"Retry-After": "120"})) is None
    assert api_client.parse_retry_after(None) is None


def test_backoff_is_jittered() -> None:
    delays = {api_client.compute_delay(3, None) for _ in range(300)}
    # attempt 3 -> 2 * 2**2 = 8s, spread into [0.5x, 1.5x]
    assert len(delays) > 1, "a deterministic ladder synchronises every client"
    assert min(delays) >= 4.0
    assert max(delays) <= 12.0


def test_cap_binds_after_the_jitter() -> None:
    # Capping first and then multiplying by up to 1.5 would land at 30s, and
    # the constant would claim a ceiling it does not hold.
    deep = {api_client.compute_delay(9, None) for _ in range(200)}
    assert max(deep) <= api_client.RETRY_MAX_DELAY

    hinted = _retry_after_error("600")
    assert {api_client.compute_delay(1, hinted) for _ in range(100)} == {api_client.RETRY_MAX_DELAY}


def test_retry_after_jitter_is_one_sided() -> None:
    """The source said when. Later is polite; earlier ignores the value read."""
    delays = {api_client.compute_delay(1, _retry_after_error("4")) for _ in range(300)}
    assert min(delays) >= 4.0, "never earlier than the source asked for"
    assert max(delays) <= 5.0  # 4 * 1.25
