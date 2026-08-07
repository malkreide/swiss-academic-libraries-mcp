"""
Swiss Academic Libraries API Client
====================================
Gemeinsamer HTTP-Client und XML-Parser für:
  - swisscovery SRU (MARC21/XML)
  - e-rara / e-periodica / e-manuscripta (OAI-PMH / Dublin Core)

Kein API-Key erforderlich – alle Quellen sind öffentlich zugänglich.
"""

from __future__ import annotations

import asyncio
import contextvars
import logging
import random
import time
import uuid
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from importlib.metadata import PackageNotFoundError, version
from typing import Any
from urllib.parse import urlsplit
from xml.etree import ElementTree as ET

import httpx
from defusedxml.ElementTree import fromstring as _safe_fromstring

logger = logging.getLogger(__name__)

# Korrelations-ID, die Upstream-Log-Zeilen einer Anfrage zuordnet (F-13).
request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="-")


class RequestIdLogFilter(logging.Filter):
    """Injiziert die aktuelle request_id in jeden LogRecord."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get()
        return True


def new_request_id() -> str:
    """Erzeugt eine 8-stellige Korrelations-ID und setzt sie im Context."""
    rid = uuid.uuid4().hex[:8]
    request_id_var.set(rid)
    return rid


try:
    _PKG_VERSION = version("swiss-academic-libraries-mcp")
except PackageNotFoundError:
    _PKG_VERSION = "0.0.0+local"

USER_AGENT = (
    f"swiss-academic-libraries-mcp/{_PKG_VERSION} "
    "(+https://github.com/malkreide/swiss-academic-libraries-mcp)"
)

# ─── Basis-URLs ───────────────────────────────────────────────────────────────

SWISSCOVERY_SRU_URL = "https://swisscovery.slsp.ch/view/sru/41SLSP_NETWORK"
ERARA_OAI_URL = "https://www.e-rara.ch/oai"
EPERIODICA_OAI_URL = "https://www.e-periodica.ch/oai/dataprovider"
EMANUSCRIPTA_OAI_URL = "https://www.e-manuscripta.ch/oai"

REQUEST_TIMEOUT = 30.0
# --- Retry policy ------------------------------------------------------------
# Adopted from the mcp-data-source-probe reference template (repaired
# 2026-08-07). Three questions: *what* is retried, *how fast*, and *how long*.
# The first is settled in the retry loop (4xx except 429 fails fast); these
# settle the other two.

RETRY_BASE_DELAY = 2.0  # ladder before jitter: 2, 4, 8

# Ceiling on the WHOLE call — every attempt and every wait together. An attempt
# count is not a bound: four attempts against an upstream that takes 30s to time
# out is two minutes inside one tool call, and the number never says so. The
# anchor is measured, not guessed: the Python MCP SDK ships
# MCP_DEFAULT_TIMEOUT = 30.0, so 25s leaves headroom for framing and parsing.
RETRY_TOTAL_BUDGET = 25.0

# Ceiling for a single wait. Bounds the exponential ladder, and bounds a
# `Retry-After` the source may send but we are not obliged to sit through.
RETRY_MAX_DELAY = 20.0

# Jitter spread. Without it every client that hit the same outage retries in
# lockstep, and the load returns as a wave exactly when the source recovers —
# the retry storm extends the outage it was meant to bridge.
RETRY_JITTER_SPREAD = 0.5  # exponential delays land in [0.5x, 1.5x]

# On a `Retry-After`, deliberately one-sided: the source said when to come back,
# so coming back later is fine and coming back earlier is not.
RETRY_AFTER_JITTER = 0.25  # lands in [1.0x, 1.25x]

# Statuses that carry a meaningful `Retry-After` (RFC 9110 section 10.2.3).
RETRY_AFTER_STATUSES = frozenset({429, 503})


class UpstreamUnavailableError(Exception):
    """No request was attempted — the budget was gone before the first try.

    A named type rather than ``RuntimeError``: a caller can branch on this, and
    cannot tell a bare ``RuntimeError`` apart from a bug in this server's own
    code. Raised only when there is no upstream exception to re-raise.
    """


def parse_retry_after(resp: httpx.Response | None) -> float | None:
    """Seconds to wait per the response's ``Retry-After``, or ``None``.

    RFC 9110 section 10.2.3 allows two forms — delta-seconds (``120``) and an
    HTTP-date (``Wed, 21 Oct 2026 07:28:00 GMT``). Both appear in the wild, so
    both are read. Anything unparseable yields ``None`` and the caller falls
    back to its own curve: a malformed header must not become a crash on the
    error path, which is the one path already going badly.
    """
    if resp is None or resp.status_code not in RETRY_AFTER_STATUSES:
        return None
    raw = (resp.headers.get("retry-after") or "").strip()
    if not raw:
        return None
    if raw.isdigit():
        return float(raw)
    try:
        when = parsedate_to_datetime(raw)
    except (TypeError, ValueError):
        return None
    if when is None:
        return None
    if when.tzinfo is None:  # RFC 9110 dates are GMT; a naive one means UTC
        when = when.replace(tzinfo=UTC)
    return max(0.0, (when - datetime.now(UTC)).total_seconds())


def compute_delay(attempt: int, last_error: Exception | None) -> float:
    """Seconds to wait before ``attempt`` (1-based for the first retry).

    The source's own answer beats our guess: a ``Retry-After`` on a 429 or 503
    wins over the exponential curve. Everything is spread, then capped.

    The cap wraps the jitter and not the other way round. ``min(cap, base) *
    jitter`` and ``min(cap, base * jitter)`` both contain a cap and a jitter;
    only the second is bounded — a value capped at 20s and then multiplied by
    up to 1.5 lands at 30s, and the constant would claim a ceiling it does not
    hold.
    """
    hinted = parse_retry_after(getattr(last_error, "response", None))
    if hinted is not None:
        return min(
            hinted * (1.0 + random.random() * RETRY_AFTER_JITTER),
            RETRY_MAX_DELAY,
        )
    return min(
        RETRY_BASE_DELAY
        * 2 ** (attempt - 1)
        * (1.0 - RETRY_JITTER_SPREAD + random.random() * 2 * RETRY_JITTER_SPREAD),
        RETRY_MAX_DELAY,
    )


MAX_CONCURRENT_REQUESTS = 5
MAX_CONNECTIONS = 10
MAX_KEEPALIVE_CONNECTIONS = 5

_client: httpx.AsyncClient | None = None
_semaphore: asyncio.Semaphore | None = None


def _get_semaphore() -> asyncio.Semaphore:
    """Lazy-init der Semaphore (muss innerhalb eines Event-Loops erfolgen)."""
    global _semaphore
    if _semaphore is None:
        _semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)
    return _semaphore


def _get_client() -> httpx.AsyncClient:
    """Modulweiter httpx.AsyncClient mit Connection-Pool und UA-Header."""
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(
            timeout=REQUEST_TIMEOUT,
            headers={"User-Agent": USER_AGENT},
            limits=httpx.Limits(
                max_connections=MAX_CONNECTIONS,
                max_keepalive_connections=MAX_KEEPALIVE_CONNECTIONS,
            ),
        )
    return _client


async def shutdown() -> None:
    """Schliesst den globalen httpx-Client. Im Server-Lifespan aufrufen."""
    global _client
    if _client is not None and not _client.is_closed:
        await _client.aclose()
    _client = None


# ─── XML-Namespaces ───────────────────────────────────────────────────────────

NS_SRW = "http://www.loc.gov/zing/srw/"
NS_MARC = "http://www.loc.gov/MARC21/slim"
NS_OAI = "http://www.openarchives.org/OAI/2.0/"
NS_OAI_DC = "http://www.openarchives.org/OAI/2.0/oai_dc/"
NS_DC = "http://purl.org/dc/elements/1.1/"

NS_MAP = {
    "srw": NS_SRW,
    "marc": NS_MARC,
    "oai": NS_OAI,
    "oai_dc": NS_OAI_DC,
    "dc": NS_DC,
}

# ─── MARC-Felddefinitionen für häufig benötigte Tags ─────────────────────────

MARC_FIELD_MAP: dict[str, str] = {
    "020": "isbn",
    "022": "issn",
    "100": "creator",
    "110": "corporate_author",
    "245": "title",
    "246": "title_variant",
    "260": "publication_info",
    "264": "publication_info",
    "300": "physical_description",
    "336": "content_type",
    "500": "note",
    "520": "abstract",
    "650": "subject",
    "651": "geographic_subject",
    "700": "contributor",
    "710": "corporate_contributor",
    "856": "url",
}


# ─── HTTP-Hilfsfunktionen ─────────────────────────────────────────────────────


async def http_get(url: str, params: dict[str, Any] | None = None) -> str:
    """Generischer GET-Request, gibt Response-Text zurück.

    Nutzt einen modulweiten Client (Connection-Reuse) und limitiert die
    parallelen Upstream-Anfragen via Semaphore, um Rate-Limits zu schonen.
    """
    param_keys = sorted((params or {}).keys())
    new_request_id()
    logger.info("upstream_request url=%s params=%s", url, param_keys)
    client = _get_client()
    async with _get_semaphore():
        try:
            response = await client.get(url, params=params or {})
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            logger.warning(
                "upstream_http_error url=%s status=%d",
                url,
                exc.response.status_code,
            )
            raise
        except httpx.TimeoutException:
            logger.warning("upstream_timeout url=%s timeout=%ss", url, REQUEST_TIMEOUT)
            raise
    logger.info(
        "upstream_response url=%s status=%d bytes=%d",
        url,
        response.status_code,
        len(response.text),
    )
    return response.text


async def http_get_with_retry(
    url: str,
    params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    max_attempts: int = 4,
) -> str:
    """GET mit exponentiellem Backoff (2s/4s/8s) für resiliente Upstream-Abfragen.

    Additive Variante von ``http_get`` — das bestehende Katalog-Verhalten bleibt
    unangetastet. Retried werden 5xx, 429 und Netzwerkfehler; andere 4xx werden
    sofort weitergereicht (kein Retry bei Client-Fehlern). Nutzt denselben
    modulweiten Client (Connection-Reuse, UA-Header) und die Semaphore.
    """
    last_error: Exception | None = None
    client = _get_client()
    deadline = time.monotonic() + RETRY_TOTAL_BUDGET
    attempts = 0

    for attempt in range(max_attempts):
        if attempt > 0:
            delay = compute_delay(attempt, last_error)
            # Eine Wartezeit, die das Budget überdauert, wartet für niemanden:
            # Der Aufrufende hat aufgegeben, bevor sie endet. Dann lieber Schluss.
            if delay >= deadline - time.monotonic():
                break
            await asyncio.sleep(delay)

        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        attempts += 1
        new_request_id()
        logger.info("upstream_request url=%s attempt=%d", url, attempt + 1)
        try:
            async with _get_semaphore():
                # httpx begrenzt pro Operation, und sein Read-Timeout beginnt
                # mit jedem Chunk von vorn — eine tröpfelnde Antwort überdauert
                # jede Einzelschranke, ohne dass ein Read abläuft.
                # `asyncio.timeout` ist die Wanduhr, die das Budget zusagt.
                async with asyncio.timeout(remaining):
                    response = await client.get(url, params=params or {}, headers=headers)
                    response.raise_for_status()
            logger.info(
                "upstream_response url=%s status=%d bytes=%d", url, response.status_code, len(response.text)
            )
            return response.text
        except TimeoutError as exc:  # Budget weg, nicht bloss dieser Versuch
            last_error = exc
            logger.warning("upstream_budget_spent url=%s attempt=%d", url, attempt + 1)
            break
        except httpx.HTTPStatusError as exc:
            last_error = exc
            status = exc.response.status_code
            if 400 <= status < 500 and status != 429:
                logger.warning("upstream_http_error url=%s status=%d (no retry)", url, status)
                raise
            logger.warning("upstream_http_error url=%s status=%d attempt=%d", url, status, attempt + 1)
        except httpx.RequestError as exc:
            last_error = exc
            # Der TYP, nicht nur `err=%s`: httpx.ConnectTimeout, ReadTimeout und
            # ConnectError tragen ein LEERES str() und sind genau die Fehler,
            # die ein echter Ausfall produziert — `err=` endete dann in nichts.
            logger.warning(
                "upstream_request_error url=%s attempt=%d err=%s: %s",
                url,
                attempt + 1,
                type(exc).__name__,
                str(exc) or "keine weitere Angabe",
            )

    if last_error is None:
        raise UpstreamUnavailableError(
            f"Kein Versuch unternommen: Das Budget von {RETRY_TOTAL_BUDGET:g}s "
            f"war schon aufgebraucht (host={urlsplit(url).hostname})."
        )
    # Durchgereicht, nicht verpackt — das war hier schon richtig. Der Aufrufende
    # behält Typ und ``.response``; ein Wrapper nähme beides weg.
    logger.warning(
        "upstream_unreachable url=%s attempts=%d limit=%s err=%s",
        url,
        attempts,
        "attempts" if attempts >= max_attempts else "time_budget",
        type(last_error).__name__,
    )
    raise last_error


def handle_api_error(e: Exception, context: str = "") -> str:
    """Einheitliche, aktionsorientierte Fehlermeldung für alle Tools."""
    prefix = f"Fehler bei {context}: " if context else "Fehler: "
    if isinstance(e, httpx.HTTPStatusError):
        code = e.response.status_code
        if code == 400:
            return f"{prefix}Ungültige Anfrage (400). Bitte Query-Syntax prüfen."
        if code == 429:
            return f"{prefix}Rate-Limit erreicht (429). Bitte kurz warten."
        if code == 503:
            return f"{prefix}Dienst vorübergehend nicht verfügbar (503). Bitte erneut versuchen."
        return f"{prefix}API-Fehler (HTTP {code})."
    if isinstance(e, httpx.TimeoutException):
        return f"{prefix}Zeitüberschreitung. Der Server antwortet nicht."
    if isinstance(e, ET.ParseError):
        return f"{prefix}XML konnte nicht verarbeitet werden. Unerwartetes Format."
    return f"{prefix}Unerwarteter Fehler: {type(e).__name__}: {e}"


# ─── SRU-Parsing (swisscovery) ───────────────────────────────────────────────


def _marc_subfield(field: ET.Element, code: str) -> str | None:
    """Liefert den Text des ersten Subfelds mit gegebenem Code."""
    sf = field.find(f"{{{NS_MARC}}}subfield[@code='{code}']")
    return sf.text.strip() if sf is not None and sf.text else None


def _marc_subfields(field: ET.Element, codes: list[str]) -> list[str]:
    """Liefert alle Subfeld-Texte der angegebenen Codes."""
    result = []
    for sf in field.findall(f"{{{NS_MARC}}}subfield"):
        code = sf.get("code", "")
        if code in codes and sf.text:
            result.append(sf.text.strip())
    return result


def parse_marc_record(record_el: ET.Element) -> dict[str, Any]:
    """
    Parst ein einzelnes MARC21-Record-Element aus SRU-Response.
    Liefert ein flaches Dict mit lesbaren Schlüsseln.
    """
    result: dict[str, Any] = {}

    # Leader / Kontrollfelder
    leader = record_el.find(f"{{{NS_MARC}}}leader")
    if leader is not None and leader.text:
        result["leader"] = leader.text

    for cf in record_el.findall(f"{{{NS_MARC}}}controlfield"):
        tag = cf.get("tag", "")
        if tag == "001" and cf.text:
            result["mms_id"] = cf.text.strip()

    # Datenfelder
    subjects: list[str] = []
    contributors: list[str] = []
    urls: list[str] = []

    for df in record_el.findall(f"{{{NS_MARC}}}datafield"):
        tag = df.get("tag", "")

        if tag == "020":
            isbn = _marc_subfield(df, "a")
            if isbn:
                result["isbn"] = isbn

        elif tag == "022":
            issn = _marc_subfield(df, "a")
            if issn:
                result["issn"] = issn

        elif tag == "100":
            parts = _marc_subfields(df, ["a", "b", "c", "d"])
            if parts:
                result["creator"] = " ".join(parts).rstrip(",. ")

        elif tag == "110":
            parts = _marc_subfields(df, ["a", "b"])
            if parts and "creator" not in result:
                result["creator"] = " ".join(parts)

        elif tag in ("245", "246"):
            a = _marc_subfield(df, "a") or ""
            b = _marc_subfield(df, "b") or ""
            title = f"{a} {b}".strip().rstrip("/ :")
            if tag == "245":
                result["title"] = title
            elif not result.get("title_variant"):
                result["title_variant"] = title

        elif tag in ("260", "264"):
            place = _marc_subfield(df, "a") or ""
            publisher = _marc_subfield(df, "b") or ""
            date = _marc_subfield(df, "c") or ""
            pub_info = ", ".join(filter(None, [place, publisher, date])).rstrip(",. ")
            if pub_info:
                result["publication_info"] = pub_info

        elif tag == "300":
            extent = _marc_subfield(df, "a") or ""
            if extent:
                result["extent"] = extent

        elif tag in ("336", "337", "338"):
            label = _marc_subfield(df, "a")
            if label and tag == "336":
                result["content_type"] = label

        elif tag == "520":
            abstract = _marc_subfield(df, "a")
            if abstract:
                result["abstract"] = abstract

        elif tag in ("650", "651", "655"):
            parts = _marc_subfields(df, ["a", "x", "y", "z"])
            if parts:
                subjects.append(" -- ".join(parts))

        elif tag in ("700", "710", "711"):
            parts = _marc_subfields(df, ["a", "b", "t"])
            if parts:
                contributors.append(" ".join(parts).rstrip(",. "))

        elif tag == "856":
            url = _marc_subfield(df, "u")
            if url:
                urls.append(url)

        elif tag in ("490", "830"):
            series = _marc_subfield(df, "a")
            if series:
                result["series"] = series

        elif tag == "041":
            lang = _marc_subfield(df, "a")
            if lang:
                result["language"] = lang

    if subjects:
        result["subjects"] = subjects
    if contributors:
        result["contributors"] = contributors
    if urls:
        result["urls"] = urls

    return result


def parse_sru_response(xml_text: str) -> dict[str, Any]:
    """
    Parst eine komplette SRU-Response.
    Liefert {'total': int, 'records': [...], 'next_record_position': int|None}
    """
    root = _safe_fromstring(xml_text)

    total_el = root.find(f"{{{NS_SRW}}}numberOfRecords")
    total = int(total_el.text) if total_el is not None and total_el.text else 0

    next_pos_el = root.find(f"{{{NS_SRW}}}nextRecordPosition")
    next_pos = int(next_pos_el.text) if next_pos_el is not None and next_pos_el.text else None

    records = []
    for rec_el in root.findall(f".//{{{NS_SRW}}}recordData/{{{NS_MARC}}}record"):
        parsed = parse_marc_record(rec_el)
        if parsed:
            records.append(parsed)

    return {"total": total, "records": records, "next_record_position": next_pos}


# ─── OAI-PMH-Parsing (e-rara, e-periodica, e-manuscripta) ───────────────────


def _dc_field(dc_el: ET.Element, field: str) -> str | None:
    """Liefert den Text des ersten DC-Elements des angegebenen Namens."""
    el = dc_el.find(f"{{{NS_DC}}}{field}")
    return el.text.strip() if el is not None and el.text else None


def _dc_fields(dc_el: ET.Element, field: str) -> list[str]:
    """Liefert alle Texte der DC-Elemente des angegebenen Namens."""
    return [el.text.strip() for el in dc_el.findall(f"{{{NS_DC}}}{field}") if el.text and el.text.strip()]


def parse_oai_dc_record(record_el: ET.Element) -> dict[str, Any]:
    """
    Parst ein einzelnes OAI-PMH-Record-Element (Dublin Core).
    Liefert ein lesbares Dict.
    """
    result: dict[str, Any] = {}

    # OAI-Header: Identifier und Datestamp
    header = record_el.find(f"{{{NS_OAI}}}header")
    if header is not None:
        ident = header.find(f"{{{NS_OAI}}}identifier")
        if ident is not None and ident.text:
            result["oai_identifier"] = ident.text.strip()
        datestamp = header.find(f"{{{NS_OAI}}}datestamp")
        if datestamp is not None and datestamp.text:
            result["last_modified"] = datestamp.text.strip()

    # Dublin Core Metadaten
    dc_el = record_el.find(f".//{{{NS_OAI_DC}}}dc")
    if dc_el is None:
        return result

    # Einzelfelder
    for field in ("title", "description", "publisher", "date", "type", "format", "rights"):
        value = _dc_field(dc_el, field)
        if value:
            result[field] = value

    # Mehrfachfelder
    creators = _dc_fields(dc_el, "creator")
    if creators:
        result["creators"] = creators

    subjects = _dc_fields(dc_el, "subject")
    if subjects:
        result["subjects"] = subjects

    contributors = _dc_fields(dc_el, "contributor")
    if contributors:
        result["contributors"] = contributors

    relations = _dc_fields(dc_el, "relation")
    if relations:
        result["relations"] = relations

    identifiers = _dc_fields(dc_el, "identifier")
    if identifiers:
        # Ersten URL-Identifier als url hervorheben
        urls = [i for i in identifiers if i.startswith("http")]
        if urls:
            result["url"] = urls[0]
        result["identifiers"] = identifiers

    languages = _dc_fields(dc_el, "language")
    if languages:
        result["language"] = languages[0]

    return result


def parse_oai_response(xml_text: str) -> dict[str, Any]:
    """
    Parst eine OAI-PMH ListRecords- oder GetRecord-Response.
    Liefert {'records': [...], 'resumption_token': str|None, 'total_size': int|None}
    """
    root = _safe_fromstring(xml_text)

    # Fehlerbehandlung auf OAI-Ebene
    error_el = root.find(f"{{{NS_OAI}}}error")
    if error_el is not None:
        code = error_el.get("code", "unknown")
        msg = error_el.text or ""
        raise ValueError(f"OAI-Fehler [{code}]: {msg}")

    records = []
    for rec_el in root.findall(f".//{{{NS_OAI}}}record"):
        parsed = parse_oai_dc_record(rec_el)
        if parsed:
            records.append(parsed)

    # Resumption Token für paginierte Abfragen
    rt_el = root.find(f".//{{{NS_OAI}}}resumptionToken")
    resumption_token = None
    total_size = None
    if rt_el is not None:
        resumption_token = rt_el.text.strip() if rt_el.text and rt_el.text.strip() else None
        total_size_str = rt_el.get("completeListSize")
        if total_size_str:
            try:
                total_size = int(total_size_str)
            except ValueError:
                pass

    return {
        "records": records,
        "resumption_token": resumption_token,
        "total_size": total_size,
    }


def parse_oai_sets_page(xml_text: str) -> dict[str, Any]:
    """Parst EINE Seite einer OAI-PMH ListSets-Response.

    Liefert {'sets': [...], 'resumption_token': str|None}.

    Der Token ist der Punkt. ListSets ist genauso paginiert wie ListRecords:
    e-rara liefert 10 Sets pro Seite bei 105 insgesamt, e-manuscripta 10 bei 49
    (gemessen am 7.8.2026). Wer nur die erste Seite liest, meldet «10
    Sammlungen» und filtert danach in einer Liste, in der 90 % fehlen. Das
    Ergebnis ist dann nicht «Fehler», sondern «nicht gefunden» — ein Ausfall,
    der wie eine Antwort aussieht.
    """
    root = _safe_fromstring(xml_text)
    sets = []
    for set_el in root.findall(f".//{{{NS_OAI}}}set"):
        spec = set_el.find(f"{{{NS_OAI}}}setSpec")
        name = set_el.find(f"{{{NS_OAI}}}setName")
        if spec is not None and spec.text:
            sets.append(
                {
                    "spec": spec.text.strip(),
                    "name": name.text.strip() if name is not None and name.text else "",
                }
            )
    rt_el = root.find(f".//{{{NS_OAI}}}resumptionToken")
    token = rt_el.text.strip() if rt_el is not None and rt_el.text and rt_el.text.strip() else None
    return {"sets": sets, "resumption_token": token}


def parse_oai_sets(xml_text: str) -> list[dict[str, str]]:
    """Die Sets EINER ListSets-Seite.

    Wer alle Sammlungen braucht, nimmt `parse_oai_sets_page` und folgt dem
    `resumption_token` — siehe dort, warum das kein Detail ist.
    """
    return parse_oai_sets_page(xml_text)["sets"]


# ─── Formatierungshilfen ─────────────────────────────────────────────────────


def format_marc_record_md(rec: dict[str, Any], index: int | None = None) -> str:
    """Formatiert ein geparsertes MARC-Record als Markdown-Block."""
    lines = []
    prefix = f"{index}. " if index is not None else ""
    title = rec.get("title", rec.get("title_variant", "Kein Titel"))
    lines.append(f"**{prefix}{title}**")

    if rec.get("creator"):
        lines.append(f"  Autor: {rec['creator']}")
    if rec.get("publication_info"):
        lines.append(f"  Erschienen: {rec['publication_info']}")
    if rec.get("extent"):
        lines.append(f"  Umfang: {rec['extent']}")
    if rec.get("language"):
        lines.append(f"  Sprache: {rec['language']}")
    if rec.get("isbn"):
        lines.append(f"  ISBN: {rec['isbn']}")
    if rec.get("issn"):
        lines.append(f"  ISSN: {rec['issn']}")
    if rec.get("mms_id"):
        lines.append(f"  MMS-ID: {rec['mms_id']}")
        lines.append(
            f"  Link: https://swisscovery.slsp.ch/permalink/41SLSP_NETWORK/1ufb5t2/alma{rec['mms_id']}"
        )
    if rec.get("subjects"):
        lines.append(f"  Schlagworte: {' | '.join(rec['subjects'][:3])}")
    if rec.get("abstract"):
        abstract_short = rec["abstract"][:200] + "…" if len(rec["abstract"]) > 200 else rec["abstract"]
        lines.append(f"  Abstract: {abstract_short}")

    return "\n".join(lines)


def format_oai_record_md(rec: dict[str, Any], index: int | None = None) -> str:
    """Formatiert ein geparsertes OAI/DC-Record als Markdown-Block."""
    lines = []
    prefix = f"{index}. " if index is not None else ""
    title = rec.get("title", "Kein Titel")
    lines.append(f"**{prefix}{title}**")

    if rec.get("creators"):
        lines.append(f"  Autor(en): {', '.join(rec['creators'][:3])}")
    if rec.get("date"):
        lines.append(f"  Datum: {rec['date']}")
    if rec.get("publisher"):
        lines.append(f"  Verlag/Quelle: {rec['publisher']}")
    if rec.get("language"):
        lines.append(f"  Sprache: {rec['language']}")
    if rec.get("type"):
        lines.append(f"  Typ: {rec['type']}")
    if rec.get("subjects"):
        lines.append(f"  Themen: {' | '.join(rec['subjects'][:3])}")
    if rec.get("description"):
        desc = rec["description"][:200] + "…" if len(rec["description"]) > 200 else rec["description"]
        lines.append(f"  Beschreibung: {desc}")
    if rec.get("url"):
        lines.append(f"  URL: {rec['url']}")
    elif rec.get("oai_identifier"):
        lines.append(f"  OAI-ID: {rec['oai_identifier']}")

    return "\n".join(lines)
