"""
Swiss Open-Access Rechtsliteratur
=================================
Erschliesst frei zugängliche schweizerische rechtswissenschaftliche
OA-Publikationen als **Metadaten** (nicht Volltext) über eine deklarative
Quellen-Registry.

Architektur-Entscheid (live verifiziert 2026-07-20): **Option C — Hybrid.**
  - Entdeckung nativ pro Quelle (deckt alle drei ab; Aggregator allein verfehlt
    ~2/3, da ex/ante keine DOIs führt und Repositorium nicht als Source indexiert
    ist):
      * sui generis  → OAI-PMH (oai_dc)      https://sui-generis.ch/oai
      * ex/ante      → OAI-PMH (oai_dc)      https://ex-ante.ch/index.php/exante/oai
      * Repositorium → Supabase/PostgREST    https://api.repositorium.ch/rest/v1
  - Lizenz-Anreicherung best-effort über **Crossref** per DOI (die native
    Metadatenschicht liefert nur Copyright-Statements, keine maschinenlesbare
    CC-Lizenz). Nicht-blockierend, per Env-Flag OA_LAW_CROSSREF_ENRICH=0
    abschaltbar. Fällt Crossref aus → license bleibt "unknown".

Governance-Invarianten (nicht verhandelbar):
  - **Kein Volltext**: weder Ingest noch Speicherung noch Ausgabe. Nur
    Titel, Autorschaft, Jahr, Lizenz, Link, DOI, Abstract (falls als Metadatum
    geliefert). Der Volltext-PDF-Pfad wird bewusst NICHT übernommen.
  - **license nie leer**: fehlt eine maschinenlesbare Lizenz → "unknown".
  - **Kein Treffer ohne auflösbare Referenz**: jeder Record hat url oder doi.
  - **Sprachfeld führen, aber nicht implizit filtern** (Romandie sichtbar halten).
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
from urllib.parse import quote

from defusedxml.ElementTree import fromstring as _safe_fromstring
from pydantic import BaseModel, ConfigDict, Field

from swiss_academic_libraries_mcp.api_client import (
    NS_DC,
    NS_OAI,
    NS_OAI_DC,
    http_get_with_retry,
)

logger = logging.getLogger(__name__)

# ─── Quellen-Registry (deklarativ) ────────────────────────────────────────────
# Neue Schweizer OA-Rechtsquellen kommen mit EINEM Eintrag hinzu — kein
# Refactoring. `kind` bestimmt den Adapter (oai_pmh | supabase_rest).

# Öffentlicher Supabase-Anon-Key des Repositorium.ch-Web-Clients. Der Verein
# stellt laut Nutzungsbedingungen eine "offene und frei zugängliche API" bereit;
# dieser Schlüssel ist im ausgelieferten SPA offengelegt und rein lesend (Rolle
# "anon"). Kein Geheimnis — daher hier dokumentiert statt versteckt.
REPOSITORIUM_ANON_KEY = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImRqZnFyZ3locnF1endhcmNla3FjIiwicm9sZSI6ImFub24iLCJpYXQiOjE2ODUyODA3NDIsImV4cCI6MjAwMDg1Njc0Mn0."
    "fpX6TPr9Q0lQHzqut69dds3DSBwtbz3bFUuLo1zUcRA"
)

OA_LEGAL_SOURCES: dict[str, dict[str, Any]] = {
    "sui-generis": {
        "label": "sui generis",
        "kind": "oai_pmh",
        "base_url": "https://sui-generis.ch/oai",
        "homepage": "https://sui-generis.ch",
        "issn": "2297-105X",
        # sui generis: redaktionell betreut; kein durchgängiges Peer-Review
        # ausgewiesen → unbekannt statt behauptet.
        "peer_reviewed_default": None,
        "attribution": "sui generis — Open-Access-Rechtszeitschrift & Non-Profit-Verlag (sui-generis.ch)",
    },
    "ex-ante": {
        "label": "ex/ante",
        "kind": "oai_pmh",
        "base_url": "https://ex-ante.ch/index.php/exante/oai",
        "homepage": "https://ex-ante.ch",
        "issn": None,
        # ex/ante: peer-reviewte Zeitschrift für (junge) Rechtswissenschaft.
        "peer_reviewed_default": True,
        "attribution": "ex/ante — peer-reviewte Zeitschrift für junge Rechtswissenschaft (ex-ante.ch)",
    },
    "repositorium": {
        "label": "Repositorium.ch",
        "kind": "supabase_rest",
        "base_url": "https://api.repositorium.ch/rest/v1",
        "homepage": "https://www.repositorium.ch",
        "table": "repo",
        "anon_key": REPOSITORIUM_ANON_KEY,
        "entry_url": "https://www.repositorium.ch/entry/{id}",
        # Repositorium führt ein Feld peer_review pro Datensatz → dort ausgewertet.
        "peer_reviewed_default": None,
        "attribution": "Repositorium.ch — Fachrepositorium zum Schweizer Recht (Verein Repositorium.ch)",
    },
}

SOURCE_KEYS = tuple(OA_LEGAL_SOURCES.keys())

# In-Memory-Harvest-Cache pro Quelle: {key: (monotonic_ts, [OaLegalPublication])}.
# Kleines Gesamtvolumen (~420 Records) → vollständiges Harvesting ist tragbar,
# lokale Keyword-Filterung ersetzt die fehlende OAI-Volltextsuche.
_CACHE: dict[str, tuple[float, list[OaLegalPublication]]] = {}
_CACHE_TTL_SECONDS = 6 * 3600
_HARVEST_LOCK = asyncio.Lock()

CROSSREF_WORK_URL = "https://api.crossref.org/works/{doi}"


def _crossref_enabled() -> bool:
    """Crossref-Lizenz-Anreicherung: default AN, per Env-Flag abschaltbar."""
    return os.environ.get("OA_LAW_CROSSREF_ENRICH", "1").strip().lower() not in ("0", "false", "no", "off")


def _now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


# ─── Response-Modell ──────────────────────────────────────────────────────────


class OaLegalPublication(BaseModel):
    """Ein OA-rechtswissenschaftlicher Beitrag — ausschliesslich Metadaten.

    Bewusst KEIN Volltext-Feld: der Server liefert Metadaten, Abstract, Lizenz
    und Link, nie den Aufsatz selbst.
    """

    model_config = ConfigDict(extra="forbid")

    title: str
    authors: list[str] = Field(default_factory=list)
    year: int | None = None
    source_name: str
    doi: str | None = None
    url: str
    license: str = "unknown"  # niemals leer — "unknown" statt Weglassen
    language: str = "unknown"
    is_peer_reviewed: bool | None = None
    abstract: str | None = None
    retrieved_at: str


# ─── Normalisierung ───────────────────────────────────────────────────────────

# Fundstück (2026-07-20): Der ex/ante-OAI-Feed enthält vereinzelt rohe
# Steuerzeichen (z.B. 0x17 mitten im Wort "oft"), die als XML 1.0 nicht
# wohlgeformt sind und den strengen Parser abbrechen lassen. OJS-Exporte
# spiegeln die Rohdaten ungefiltert — also säubern wir vor dem Parsen.
_INVALID_XML_CHARS = re.compile(r"[^\x09\x0a\x0d\x20-퟿-�\U00010000-\U0010ffff]")


def strip_invalid_xml_chars(text: str) -> str:
    """Entfernt in XML 1.0 unzulässige Steuerzeichen (defensive Normalisierung)."""
    return _INVALID_XML_CHARS.sub("", text)


_YEAR_RE = re.compile(r"\b(1[5-9]\d{2}|20\d{2}|21\d{2})\b")
_CC_RE = re.compile(r"creativecommons\.org/licenses/([a-z-]+)/(\d(?:\.\d)?)", re.IGNORECASE)
_CC0_RE = re.compile(r"creativecommons\.org/publicdomain/zero/(\d(?:\.\d)?)", re.IGNORECASE)
_CC_TEXT_RE = re.compile(r"\bCC[ -]?(BY(?:-(?:SA|NC|ND)){0,3}|0)\b(?:[ -]?(\d(?:\.\d)?))?", re.IGNORECASE)
_DOI_RE = re.compile(r"10\.\d{4,9}/[^\s\"'<>]+", re.IGNORECASE)

_LANG_MAP = {
    "de": "de",
    "deu": "de",
    "ger": "de",
    "german": "de",
    "deutsch": "de",
    "fr": "fr",
    "fra": "fr",
    "fre": "fr",
    "french": "fr",
    "franzoesisch": "fr",
    "it": "it",
    "ita": "it",
    "italian": "it",
    "italienisch": "it",
    "en": "en",
    "eng": "en",
    "english": "en",
    "englisch": "en",
    "rm": "rm",
    "roh": "rm",
}


def normalize_language(raw: str | None) -> str:
    """ISO-639-1 wo bekannt, sonst der Rohwert; nie leer."""
    if not raw:
        return "unknown"
    key = raw.strip().lower()
    return _LANG_MAP.get(key, key or "unknown")


def normalize_license(value: str | None) -> str | None:
    """Erkennt eine maschinenlesbare CC-Lizenz aus URL oder Text.

    Gibt ein normalisiertes Label ("CC BY-SA 4.0", "CC0 1.0") zurück oder None,
    wenn kein CC-Muster gefunden wird. Reine Copyright-Statements
    ("Copyright (c) 2016 …") liefern None → der Aufrufer setzt "unknown".
    """
    if not value:
        return None
    m = _CC_RE.search(value)
    if m:
        ver = m.group(2)
        ver = ver if "." in ver else f"{ver}.0"
        return f"CC {m.group(1).upper()} {ver}"
    if _CC0_RE.search(value):
        return "CC0 1.0"
    m = _CC_TEXT_RE.search(value)
    if m:
        code = m.group(1).upper()
        ver = m.group(2)
        if code == "0":
            return "CC0 1.0"
        return f"CC {code} {ver + ('' if ver and '.' in ver else '.0') if ver else '4.0'}"
    return None


def extract_year(*candidates: str | None) -> int | None:
    for cand in candidates:
        if not cand:
            continue
        m = _YEAR_RE.search(str(cand))
        if m:
            return int(m.group(1))
    return None


def extract_doi(*candidates: str | None) -> str | None:
    """Extrahiert eine blanke DOI (10.xxxx/…) aus URL/URN/Identifier."""
    for cand in candidates:
        if not cand:
            continue
        text = str(cand)
        if text.lower().startswith("info:doi/"):
            text = text[len("info:doi/") :]
        m = _DOI_RE.search(text)
        if m:
            return m.group(0).rstrip(".,;)")
    return None


# ─── OAI-PMH-Adapter (sui generis, ex/ante) ──────────────────────────────────


def _dc_all(dc_el: Any, field: str) -> list[str]:
    return [e.text.strip() for e in dc_el.findall(f"{{{NS_DC}}}{field}") if e.text and e.text.strip()]


def _dc_first(dc_el: Any, field: str) -> str | None:
    vals = _dc_all(dc_el, field)
    return vals[0] if vals else None


def _parse_oai_legal_record(record_el: Any, cfg: dict[str, Any]) -> OaLegalPublication | None:
    header = record_el.find(f"{{{NS_OAI}}}header")
    if header is not None and header.get("status") == "deleted":
        return None
    dc_el = record_el.find(f".//{{{NS_OAI_DC}}}dc")
    if dc_el is None:
        return None

    title = _dc_first(dc_el, "title") or "(ohne Titel)"
    authors = _dc_all(dc_el, "creator")
    identifiers = _dc_all(dc_el, "identifier")
    rights = _dc_all(dc_el, "rights")

    doi = extract_doi(*identifiers)
    # url: erster http-Identifier, der NICHT nur die doi.org-Auflösung ist
    url = None
    for ident in identifiers:
        if ident.startswith("http") and "doi.org" not in ident:
            url = ident
            break
    if not url and doi:
        url = f"https://doi.org/{doi}"
    if not url and not doi:
        # Kein Treffer ohne auflösbare Referenz — überspringen.
        return None

    license_label = "unknown"
    for candidate in (*rights, *identifiers):
        found = normalize_license(candidate)
        if found:
            license_label = found
            break

    return OaLegalPublication(
        title=title,
        authors=authors,
        year=extract_year(_dc_first(dc_el, "date")),
        source_name=cfg["label"],
        doi=doi,
        url=url,  # type: ignore[arg-type]
        license=license_label,
        language=normalize_language(_dc_first(dc_el, "language")),
        is_peer_reviewed=cfg.get("peer_reviewed_default"),
        abstract=_dc_first(dc_el, "description"),
        retrieved_at=_now_iso(),
    )


async def _harvest_oai(cfg: dict[str, Any]) -> list[OaLegalPublication]:
    """Vollständiges OAI-PMH-Harvesting mit Resumption-Token über Seitengrenzen."""
    url = cfg["base_url"]
    params: dict[str, str] = {"verb": "ListRecords", "metadataPrefix": "oai_dc"}
    out: list[OaLegalPublication] = []
    seen_tokens: set[str] = set()
    while True:
        xml_text = await http_get_with_retry(url, params)
        root = _safe_fromstring(strip_invalid_xml_chars(xml_text))

        err = root.find(f"{{{NS_OAI}}}error")
        if err is not None:
            code = err.get("code", "unknown")
            if code == "noRecordsMatch":
                break
            raise ValueError(f"OAI-Fehler [{code}]: {err.text or ''}")

        for rec_el in root.findall(f".//{{{NS_OAI}}}record"):
            pub = _parse_oai_legal_record(rec_el, cfg)
            if pub is not None:
                out.append(pub)

        rt_el = root.find(f".//{{{NS_OAI}}}resumptionToken")
        token = rt_el.text.strip() if rt_el is not None and rt_el.text and rt_el.text.strip() else None
        if not token or token in seen_tokens:
            break
        seen_tokens.add(token)
        params = {"verb": "ListRecords", "resumptionToken": token}
    return out


# ─── Supabase/PostgREST-Adapter (Repositorium.ch) ────────────────────────────


def _parse_repositorium_row(row: dict[str, Any], cfg: dict[str, Any]) -> OaLegalPublication | None:
    title = (row.get("titel") or "").strip() or "(ohne Titel)"

    authors: list[str] = []
    author = row.get("author")
    if isinstance(author, dict):
        name = (author.get("full_name") or author.get("username") or "").strip()
        if name:
            authors.append(name)
    for co in row.get("coauthors") or []:
        if isinstance(co, str) and co.strip():
            authors.append(co.strip())

    doi = extract_doi(row.get("doi"))
    # Persistente Landing-Page als url — NICHT der Volltext-PDF-Pfad (datei_url).
    row_id = row.get("id")
    url = (
        cfg["entry_url"].format(id=row_id) if row_id is not None else row.get("link_zur_originalpublikation")
    )
    if not url and doi:
        url = f"https://doi.org/{doi}"
    if not url:
        return None

    license_label = normalize_license(row.get("license")) or "unknown"

    peer = (row.get("peer_review") or "").strip().lower()
    is_pr = True if peer == "ja" else False if peer == "nein" else cfg.get("peer_reviewed_default")

    return OaLegalPublication(
        title=title,
        authors=authors,
        year=extract_year(row.get("erschienen_am"), row.get("erschienen_in"), row.get("created_at")),
        source_name=cfg["label"],
        doi=doi,
        url=url,
        license=license_label,
        language=normalize_language(row.get("sprache")),
        is_peer_reviewed=is_pr,
        abstract=(row.get("abstract") or None),
        retrieved_at=_now_iso(),
    )


async def _harvest_repositorium(cfg: dict[str, Any]) -> list[OaLegalPublication]:
    key = cfg["anon_key"]
    headers = {"apikey": key, "Authorization": f"Bearer {key}"}
    base = f"{cfg['base_url']}/{cfg['table']}"
    out: list[OaLegalPublication] = []
    page_size = 1000
    offset = 0
    while True:
        params = {
            "select": "*,author(full_name,username)",
            "public": "eq.true",
            "order": "id.asc",
            "limit": str(page_size),
            "offset": str(offset),
        }
        text = await http_get_with_retry(base, params, headers=headers)
        rows = json.loads(text)
        if not isinstance(rows, list):
            raise ValueError("Repositorium: unerwartetes Antwortformat (keine Liste).")
        for row in rows:
            pub = _parse_repositorium_row(row, cfg)
            if pub is not None:
                out.append(pub)
        if len(rows) < page_size:
            break
        offset += page_size
    return out


# ─── Harvest-Orchestrierung mit Graceful Degradation ─────────────────────────


async def _harvest_source(key: str, cfg: dict[str, Any]) -> list[OaLegalPublication]:
    if cfg["kind"] == "oai_pmh":
        return await _harvest_oai(cfg)
    if cfg["kind"] == "supabase_rest":
        return await _harvest_repositorium(cfg)
    raise ValueError(f"Unbekannter Quellen-Typ: {cfg['kind']}")


async def get_corpus(force_refresh: bool = False) -> tuple[list[OaLegalPublication], dict[str, str]]:
    """Harvestet alle Quellen (mit Cache) und liefert (records, status_pro_quelle).

    status-Werte: "ok" (frisch geladen), "cached" (frischer Cache),
    "stale_cache" (Quelle aktuell nicht erreichbar, alter Cache genutzt),
    "unreachable" (nicht erreichbar, kein Cache). So geht keine Quelle still
    verloren — der Ausfall wird in der Antwort ausgewiesen.
    """
    async with _HARVEST_LOCK:
        all_pubs: list[OaLegalPublication] = []
        status: dict[str, str] = {}
        for key, cfg in OA_LEGAL_SOURCES.items():
            cached = _CACHE.get(key)
            is_fresh = cached is not None and (time.monotonic() - cached[0] < _CACHE_TTL_SECONDS)
            if is_fresh and not force_refresh:
                all_pubs.extend(cached[1])
                status[key] = "cached"
                continue
            try:
                pubs = await _harvest_source(key, cfg)
                _CACHE[key] = (time.monotonic(), pubs)
                all_pubs.extend(pubs)
                status[key] = "ok"
            except Exception as exc:  # noqa: BLE001 — Graceful Degradation pro Quelle
                logger.warning("oa_harvest_failed source=%s err=%s", key, exc)
                if cached is not None:
                    all_pubs.extend(cached[1])
                    status[key] = "stale_cache"
                else:
                    status[key] = "unreachable"
        return all_pubs, status


# ─── Crossref-Lizenz-Anreicherung (best-effort, nicht blockierend) ───────────


async def enrich_license(pub: OaLegalPublication) -> OaLegalPublication:
    """Hebt license von "unknown" an, wenn Crossref für die DOI eine CC-Lizenz führt.

    Best-effort: nur wenn DOI vorhanden UND license noch "unknown". Jeder Fehler
    (Timeout, 404, Netz) wird verschluckt — die Suche schlägt nie an Crossref fehl.
    """
    if not _crossref_enabled() or not pub.doi or pub.license != "unknown":
        return pub
    try:
        # DOI-Slash NICHT kodieren — Crossref routet works/{doi} über den Pfad.
        # Die /works/{doi}-Route unterstützt KEIN select-Parameter (→ 400).
        text = await http_get_with_retry(
            CROSSREF_WORK_URL.format(doi=quote(pub.doi, safe="/")),
            max_attempts=2,
        )
        data = json.loads(text)
        for lic in data.get("message", {}).get("license", []) or []:
            label = normalize_license(lic.get("URL"))
            if label:
                pub.license = label
                break
    except Exception as exc:  # noqa: BLE001 — Anreicherung darf nie blockieren
        logger.info("crossref_enrich_skipped doi=%s err=%s", pub.doi, exc)
    return pub


async def _enrich_page(pubs: list[OaLegalPublication]) -> None:
    if not _crossref_enabled():
        return
    await asyncio.gather(*(enrich_license(p) for p in pubs))


# ─── Filterung & Suche ───────────────────────────────────────────────────────


def _matches(pub: OaLegalPublication, tokens: list[str]) -> bool:
    if not tokens:
        return True
    haystack = " ".join(
        filter(None, [pub.title, pub.abstract or "", " ".join(pub.authors), pub.source_name])
    ).lower()
    return all(tok in haystack for tok in tokens)


async def search_publications(
    query: str,
    source: str | None = None,
    language: str | None = None,
    year_from: int | None = None,
    year_to: int | None = None,
    peer_reviewed: bool | None = None,
    max_records: int = 20,
) -> dict[str, Any]:
    """Sucht über die harvesteten Metadaten aller Quellen (lokale Keyword-Filterung).

    Sprachfilterung nur, wenn explizit verlangt (Romandie bleibt sonst sichtbar).
    """
    corpus, status = await get_corpus()

    if not corpus and all(v == "unreachable" for v in status.values()):
        raise RuntimeError(
            "Alle OA-Rechtsquellen sind derzeit nicht erreichbar. Bitte in einigen Minuten erneut versuchen."
        )

    tokens = [t for t in query.lower().split() if t]
    results: list[OaLegalPublication] = []
    for pub in corpus:
        if source and _source_key_for(pub) != source:
            continue
        if language and pub.language != language.strip().lower():
            continue
        if year_from is not None and (pub.year is None or pub.year < year_from):
            continue
        if year_to is not None and (pub.year is None or pub.year > year_to):
            continue
        if peer_reviewed is not None and pub.is_peer_reviewed is not peer_reviewed:
            continue
        if _matches(pub, tokens):
            results.append(pub)

    results.sort(key=lambda p: (p.year is None, -(p.year or 0), p.title.lower()))
    total = len(results)
    page = results[:max_records]
    await _enrich_page(page)

    return {"results": page, "total": total, "status": status}


def _source_key_for(pub: OaLegalPublication) -> str | None:
    for key, cfg in OA_LEGAL_SOURCES.items():
        if cfg["label"] == pub.source_name:
            return key
    return None


async def get_publication(identifier: str) -> dict[str, Any]:
    """Ruft einen Einzelbeitrag über DOI oder auflösbare URL ab (aus dem Korpus)."""
    corpus, status = await get_corpus()
    if not corpus and all(v == "unreachable" for v in status.values()):
        raise RuntimeError("Alle OA-Rechtsquellen sind derzeit nicht erreichbar.")

    needle = identifier.strip()
    doi_needle = extract_doi(needle) or (needle if needle.startswith("10.") else None)

    match: OaLegalPublication | None = None
    for pub in corpus:
        if doi_needle and pub.doi and pub.doi.lower() == doi_needle.lower():
            match = pub
            break
        if pub.url == needle or (needle and needle in pub.url):
            match = pub
            break

    if match is None:
        return {"result": None, "status": status}

    await enrich_license(match)
    return {"result": match, "status": status}
