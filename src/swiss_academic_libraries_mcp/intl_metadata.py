"""
Internationale Metadatenebene
=============================
Ergänzt die nationale Bibliotheksebene (swisscovery, e-rara, …) um die
internationale bibliografische Metadatenebene:

  - **Crossref** — DOI-Auflösung und Suche in der internationalen
    Forschungsliteratur (REST-API, ``https://api.crossref.org``).
  - **arXiv** — Preprints (Atom-XML-API, ``http://export.arxiv.org/api/query``).

Beide Quellen sind ohne API-Key zugänglich und liefern ausschliesslich
**Metadaten** (kein Volltext). Die Verkettung zur nationalen Ebene ist der
Kern dieser Erweiterung: jede Auflösung liefert Titel, ISSN, ISBN und
Autor:innen als saubere Top-Level-Felder, mit denen sich in swisscovery
weitersuchen lässt («gibt es das in einer Schweizer Bibliothek?»).

Architektur-Entscheid (live verifiziert 2026-07-20): **Tool-Extension,
Architektur A (Live-API-only)** — beide Endpoints sind stabil, klein und
öffentlich, kein Dump/Cache-Zwang. Retry/Backoff, Egress-Allow-List und
Provenance-Envelope wie im OA-Rechtspfad (``oa_legal``).

Known findings (Live-Probe 2026-07-20):
  - **Crossref DE-Bildung schwach:** ``query.bibliographic=Lehrplan 21`` liefert
    als Top-Treffer ein Buchkapitel von 1881. Stark bei DOI-Auflösung und
    internationaler Forschung, schwach bei CH-Bildungspublikationen.
  - **arXiv-Phrasen-Falle:** ``all:model context protocol`` wird als OR
    interpretiert (~1,3 Mio. Treffer); ``all:"model context protocol"`` als
    Phrase (462 Treffer). ``build_arxiv_query`` quotiert daher automatisch.
  - **arXiv Atom-XML, kein JSON:** Parser via ``defusedxml`` (bereits Dependency).
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import time
from datetime import UTC, datetime
from typing import Any
from urllib.parse import quote, urlparse

from defusedxml.ElementTree import fromstring as _safe_fromstring
from pydantic import BaseModel, ConfigDict, Field

from swiss_academic_libraries_mcp.api_client import http_get_with_retry

logger = logging.getLogger(__name__)

# ─── Endpoints & Attribution (pro Quelle, nicht gesammelt) ───────────────────
# Jede Response trägt die Attribution GENAU DER Quelle, aus der sie stammt.
# Crossref und arXiv haben unterschiedliche Lizenz- und Nennungsbedingungen.

CROSSREF_BASE = "https://api.crossref.org"
CROSSREF_WORKS_URL = f"{CROSSREF_BASE}/works"
# HTTPS direkt — export.arxiv.org antwortet auf http:// mit 301 auf https://,
# und der geteilte httpx-Client folgt Redirects bewusst nicht (Konsistenz mit
# den übrigen Quellen). Der HTTPS-Endpoint vermeidet den Redirect-Hop.
ARXIV_API_URL = "https://export.arxiv.org/api/query"

# Crossref stellt bibliografische Metadaten via REST-API gemeinfrei (CC0) bereit;
# «facts are free». Die Nennung ist Best Practice, nicht Lizenzpflicht.
CROSSREF_ATTRIBUTION = (
    "Metadaten: Crossref REST API (CC0 1.0, gemeinfrei) — https://www.crossref.org. "
    "Volltext/Lizenz je Publikation beim Verlag."
)
# arXiv stellt seine Metadaten unter CC0 bereit; die API-Nutzungsbedingungen
# bitten um die folgende Danksagung. Preprints selbst je Autor:innen-Lizenz.
ARXIV_ATTRIBUTION = (
    "Metadaten: arXiv.org (Cornell University) via arXiv API. "
    "«Thank you to arXiv for use of its open access interoperability.» "
    "Preprint-Volltexte je Lizenz des Preprints (arXiv perpetual / CC)."
)

# ─── Egress-Allow-List (Code-Layer, Defense-in-Depth wie oa_legal SEC-021) ───
# Ausgehende Requests dürfen NUR diese Hosts erreichen. Keine URL wird aus
# User-/LLM-Input konstruiert (DOI/Query landen ausschliesslich in Parametern).
ALLOWED_HOSTS = frozenset(
    h
    for h in (
        urlparse(CROSSREF_BASE).hostname,
        urlparse(ARXIV_API_URL).hostname,
    )
    if h
)


def _assert_host_allowed(url: str) -> None:
    host = urlparse(url).hostname or ""
    if host not in ALLOWED_HOSTS:
        raise ValueError(f"Egress-Host nicht erlaubt: {host!r} (Allow-List: {sorted(ALLOWED_HOSTS)})")


# ─── Crossref polite pool ─────────────────────────────────────────────────────
# Ohne mailto landet man im anonymen Pool mit schlechterem Durchsatz. Wir setzen
# einen konfigurierbaren mailto (CROSSREF_MAILTO). Fehlt er, läuft die Abfrage
# funktionsfähig weiter (anonymer Pool) — kein harter Fehler, aber ein Hinweis.

_MAILTO_WARNED = False


def _crossref_mailto() -> str | None:
    value = os.environ.get("CROSSREF_MAILTO", "").strip()
    return value or None


def _crossref_headers() -> dict[str, str]:
    """User-Agent mit mailto für den polite pool; ohne mailto ein einmaliger Hinweis."""
    global _MAILTO_WARNED
    mailto = _crossref_mailto()
    base = "swiss-academic-libraries-mcp (+https://github.com/malkreide/swiss-academic-libraries-mcp)"
    if mailto:
        return {"User-Agent": f"{base}; mailto:{mailto}"}
    if not _MAILTO_WARNED:
        logger.info(
            "crossref_polite_pool_off — setze CROSSREF_MAILTO=you@example.org für besseren "
            "Durchsatz (aktuell anonymer Pool)."
        )
        _MAILTO_WARNED = True
    return {"User-Agent": base}


def _crossref_params(params: dict[str, str]) -> dict[str, str]:
    """Ergänzt mailto als Query-Param (Crossref akzeptiert beide Wege)."""
    mailto = _crossref_mailto()
    if mailto:
        return {**params, "mailto": mailto}
    return params


# ─── arXiv Rate Limit / Throttle ──────────────────────────────────────────────
# arXiv bittet um Zurückhaltung (~3 s zwischen Requests). Ein modulweiter Lock
# serialisiert arXiv-Abfragen und hält den Mindestabstand ein.

_ARXIV_MIN_INTERVAL = float(os.environ.get("ARXIV_MIN_INTERVAL_SECONDS", "3.0"))
_arxiv_lock = asyncio.Lock()
_arxiv_last_ts = 0.0


async def _arxiv_throttle() -> None:
    global _arxiv_last_ts
    async with _arxiv_lock:
        wait = _ARXIV_MIN_INTERVAL - (time.monotonic() - _arxiv_last_ts)
        if wait > 0:
            logger.info("arxiv_throttle sleep=%.2fs", wait)
            await asyncio.sleep(wait)
        _arxiv_last_ts = time.monotonic()


# ─── HTTP mit Egress-Prüfung + Retry (wiederverwendet http_get_with_retry) ───


async def _fetch(
    url: str,
    params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    max_attempts: int = 4,
) -> str:
    """Ausgehender GET mit Egress-Allow-List, dann Retry/Backoff (2s/4s/8s)."""
    _assert_host_allowed(url)
    return await http_get_with_retry(url, params=params, headers=headers, max_attempts=max_attempts)


def _now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


# ─── Response-Modelle (Pydantic v2, mirror oa_legal-Konvention) ──────────────


class CrossrefWork(BaseModel):
    """Eine über Crossref aufgelöste Publikation — nur Metadaten.

    Die Felder ``title``, ``issn``, ``isbn`` und ``authors`` sind bewusst
    saubere Top-Level-Felder: mit ihnen lässt sich direkt in swisscovery
    weitersuchen, ob eine Schweizer Bibliothek den Titel führt.
    """

    model_config = ConfigDict(extra="forbid")

    doi: str
    title: str
    authors: list[str] = Field(default_factory=list)
    year: int | None = None
    type: str | None = None
    container_title: str | None = None  # Zeitschrift / Buchreihe
    publisher: str | None = None
    issn: list[str] = Field(default_factory=list)
    isbn: list[str] = Field(default_factory=list)
    license: str = "unknown"  # nie leer — "unknown" statt Weglassen
    url: str  # auflösbar (https://doi.org/…)
    abstract: str | None = None
    source: str = CROSSREF_ATTRIBUTION
    retrieved_at: str


class Preprint(BaseModel):
    """Ein arXiv-Preprint — nur Metadaten (keine Volltexte).

    ``doi`` ist gesetzt, sobald arXiv eine verknüpfte Journal-DOI führt — dann
    lässt sich via ``resolve_doi`` die peer-reviewte Fassung anschliessen.
    """

    model_config = ConfigDict(extra="forbid")

    arxiv_id: str
    title: str
    authors: list[str] = Field(default_factory=list)
    summary: str | None = None
    primary_category: str | None = None
    categories: list[str] = Field(default_factory=list)
    published: str | None = None
    updated: str | None = None
    year: int | None = None
    doi: str | None = None
    abs_url: str
    pdf_url: str | None = None
    license: str = "unknown"
    source: str = ARXIV_ATTRIBUTION
    retrieved_at: str


# ─── Hilfen: Normalisierung ───────────────────────────────────────────────────

_CC_RE = re.compile(r"creativecommons\.org/licenses/([a-z-]+)/(\d(?:\.\d)?)", re.IGNORECASE)
_CC0_RE = re.compile(r"creativecommons\.org/publicdomain/zero/(\d(?:\.\d)?)", re.IGNORECASE)


def normalize_license(url: str | None) -> str | None:
    """Erkennt eine maschinenlesbare CC-Lizenz aus einer Lizenz-URL (sonst None)."""
    if not url:
        return None
    m = _CC_RE.search(url)
    if m:
        ver = m.group(2)
        ver = ver if "." in ver else f"{ver}.0"
        return f"CC {m.group(1).upper()} {ver}"
    if _CC0_RE.search(url):
        return "CC0 1.0"
    return None


def _clean_abstract(raw: str | None) -> str | None:
    """Crossref-Abstracts sind JATS-XML-Fragmente; grob zu Text säubern."""
    if not raw:
        return None
    text = re.sub(r"<[^>]+>", " ", raw)  # JATS-Tags entfernen
    text = re.sub(r"\s+", " ", text).strip()
    return text or None


# ─── Crossref-Adapter ─────────────────────────────────────────────────────────

# Nur diese Felder anfordern (kleiner, schneller); reicht für die Verkettung.
_CROSSREF_SELECT = "DOI,title,author,issued,type,container-title,publisher,ISSN,ISBN,license,abstract,URL"


def _parse_crossref_message(msg: dict[str, Any]) -> CrossrefWork:
    """Baut ein CrossrefWork aus dem message-Objekt eines Crossref-Records."""
    title = (msg.get("title") or ["(ohne Titel)"])[0]
    authors = []
    for a in msg.get("author") or []:
        name = " ".join(filter(None, [a.get("given"), a.get("family")])).strip()
        if not name:
            name = (a.get("name") or "").strip()
        if name:
            authors.append(name)

    year = None
    issued = (msg.get("issued") or {}).get("date-parts") or []
    if issued and issued[0] and issued[0][0]:
        year = issued[0][0]

    license_label = "unknown"
    for lic in msg.get("license") or []:
        found = normalize_license(lic.get("URL"))
        if found:
            license_label = found
            break

    doi = (msg.get("DOI") or "").strip()
    url = msg.get("URL") or (f"https://doi.org/{doi}" if doi else "")

    return CrossrefWork(
        doi=doi,
        title=title,
        authors=authors,
        year=year,
        type=msg.get("type"),
        container_title=(msg.get("container-title") or [None])[0],
        publisher=msg.get("publisher"),
        issn=list(msg.get("ISSN") or []),
        isbn=list(msg.get("ISBN") or []),
        license=license_label,
        url=url,
        abstract=_clean_abstract(msg.get("abstract")),
        retrieved_at=_now_iso(),
    )


async def resolve_doi(doi: str) -> CrossrefWork | None:
    """Löst eine DOI über Crossref zu vollständigen Metadaten auf (oder None)."""
    clean = doi.strip()
    if clean.lower().startswith("http"):
        # https://doi.org/10.xxxx/… → blanke DOI extrahieren
        m = re.search(r"10\.\d{4,9}/\S+", clean)
        clean = m.group(0) if m else clean
    if clean.lower().startswith("doi:"):
        clean = clean[4:].strip()

    # DOI-Slash NICHT kodieren — Crossref routet works/{doi} über den Pfad.
    # Die /works/{doi}-Route unterstützt KEIN select-Parameter (→ 400).
    url = f"{CROSSREF_WORKS_URL}/{quote(clean, safe='/')}"
    try:
        text = await _fetch(url, params=_crossref_params({}), headers=_crossref_headers(), max_attempts=4)
    except Exception as exc:
        status = getattr(getattr(exc, "response", None), "status_code", None)
        if status == 404:
            return None
        raise
    data = json.loads(text)
    msg = data.get("message")
    if not isinstance(msg, dict):
        return None
    return _parse_crossref_message(msg)


async def search_publications(
    query: str,
    year_from: int | None = None,
    year_to: int | None = None,
    limit: int = 10,
) -> list[CrossrefWork]:
    """Sucht in der internationalen Forschungsliteratur (Crossref, bibliografisch)."""
    params: dict[str, str] = {
        "query.bibliographic": query,
        "rows": str(max(1, min(limit, 50))),
        "select": _CROSSREF_SELECT,
    }
    date_filters = []
    if year_from is not None:
        date_filters.append(f"from-pub-date:{year_from}-01-01")
    if year_to is not None:
        date_filters.append(f"until-pub-date:{year_to}-12-31")
    if date_filters:
        params["filter"] = ",".join(date_filters)

    text = await _fetch(
        CROSSREF_WORKS_URL, params=_crossref_params(params), headers=_crossref_headers(), max_attempts=4
    )
    data = json.loads(text)
    items = (data.get("message") or {}).get("items") or []
    return [_parse_crossref_message(it) for it in items if isinstance(it, dict)]


# ─── arXiv-Adapter ────────────────────────────────────────────────────────────

_ARXIV_FIELD_RE = re.compile(r"\b(all|ti|au|abs|co|cat|jr|rn|id):", re.IGNORECASE)
NS_ATOM = "http://www.w3.org/2005/Atom"
NS_ARXIV = "http://arxiv.org/schemas/atom"
NS_OPENSEARCH = "http://a9.com/-/spec/opensearch/1.1/"


def build_arxiv_query(query: str, category: str | None = None) -> str:
    """Baut die arXiv-``search_query`` und umgeht die impliziten-OR-Falle.

    arXiv interpretiert ``all:model context protocol`` als OR-Verknüpfung
    (~1,3 Mio. Treffer). Wir quotieren die Anfrage daher automatisch als
    exakte Phrase (``all:"model context protocol"`` → 462 Treffer), damit
    Nutzende keine arXiv-Syntax lernen müssen. Enthält die Anfrage bereits
    ein Feld-Präfix (``ti:``, ``au:`` …) oder Anführungszeichen, wird sie
    unverändert respektiert.
    """
    q = query.strip()
    if _ARXIV_FIELD_RE.search(q) or '"' in q:
        search = q
    else:
        search = f'all:"{q}"'
    if category:
        search = f"({search}) AND cat:{category.strip()}"
    return search


def _arxiv_text(el: Any, path: str) -> str | None:
    node = el.find(path)
    if node is not None and node.text:
        return node.text.strip()
    return None


def parse_arxiv_feed(xml_text: str, limit: int) -> list[Preprint]:
    """Parst eine arXiv-Atom-Antwort zu Preprint-Modellen."""
    root = _safe_fromstring(xml_text)
    out: list[Preprint] = []
    for entry in root.findall(f"{{{NS_ATOM}}}entry"):
        abs_url = _arxiv_text(entry, f"{{{NS_ATOM}}}id") or ""
        # arXiv-ID aus der abs-URL (…/abs/2607.16085v1 → 2607.16085v1)
        arxiv_id = abs_url.rsplit("/abs/", 1)[-1] if "/abs/" in abs_url else abs_url

        authors = [
            a.text.strip()
            for a in entry.findall(f"{{{NS_ATOM}}}author/{{{NS_ATOM}}}name")
            if a.text and a.text.strip()
        ]
        categories = [c.get("term") for c in entry.findall(f"{{{NS_ATOM}}}category") if c.get("term")]
        primary = entry.find(f"{{{NS_ARXIV}}}primary_category")
        published = _arxiv_text(entry, f"{{{NS_ATOM}}}published")
        year = int(published[:4]) if published and published[:4].isdigit() else None

        pdf_url = None
        for link in entry.findall(f"{{{NS_ATOM}}}link"):
            if link.get("title") == "pdf":
                pdf_url = link.get("href")
                break

        out.append(
            Preprint(
                arxiv_id=arxiv_id,
                title=re.sub(r"\s+", " ", (_arxiv_text(entry, f"{{{NS_ATOM}}}title") or "")).strip()
                or "(ohne Titel)",
                authors=authors,
                summary=re.sub(r"\s+", " ", (_arxiv_text(entry, f"{{{NS_ATOM}}}summary") or "")).strip()
                or None,
                primary_category=primary.get("term") if primary is not None else None,
                categories=categories,
                published=published,
                updated=_arxiv_text(entry, f"{{{NS_ATOM}}}updated"),
                year=year,
                doi=_arxiv_text(entry, f"{{{NS_ARXIV}}}doi"),
                abs_url=abs_url,
                pdf_url=pdf_url,
                retrieved_at=_now_iso(),
            )
        )
        if len(out) >= limit:
            break
    return out


async def search_preprints(query: str, category: str | None = None, limit: int = 10) -> list[Preprint]:
    """Sucht Preprints auf arXiv (Atom-XML), mit automatischer Phrasen-Quotierung."""
    n = max(1, min(limit, 50))
    params = {
        "search_query": build_arxiv_query(query, category),
        "start": "0",
        "max_results": str(n),
        "sortBy": "relevance",
        "sortOrder": "descending",
    }
    await _arxiv_throttle()
    xml_text = await _fetch(ARXIV_API_URL, params=params, max_attempts=4)
    return parse_arxiv_feed(xml_text, n)
