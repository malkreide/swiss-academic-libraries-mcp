"""
Swiss Academic Libraries MCP Server
======================================
Zugriff auf Schweizer Wissenschaftsbibliotheken via standardisierte Protokolle.

Datenquellen (alle ohne API-Key):
  - swisscovery (SLSP): 500+ Bibliotheken via SRU/MARC21
  - e-rara: Digitalisierte historische Druckwerke (OAI-PMH)
  - e-periodica: Digitalisierte Zeitschriften (OAI-PMH)
  - e-manuscripta: Digitalisierte Handschriften (OAI-PMH)

Verwendung (stdio):
  uvx swiss-academic-libraries-mcp

Verwendung (HTTP):
  uvx swiss-academic-libraries-mcp --http [--port 8000]
"""

from __future__ import annotations

import json
import sys
from typing import Annotated, Any, Optional

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, ConfigDict, Field

from swiss_academic_libraries_mcp.api_client import (
    ERARA_OAI_URL,
    EMANUSCRIPTA_OAI_URL,
    EPERIODICA_OAI_URL,
    SWISSCOVERY_SRU_URL,
    format_marc_record_md,
    format_oai_record_md,
    handle_api_error,
    http_get,
    parse_marc_record,
    parse_oai_response,
    parse_oai_sets,
    parse_sru_response,
)

# ─── Server-Initialisierung ───────────────────────────────────────────────────

mcp = FastMCP(
    "swiss_academic_libraries_mcp",
    instructions=(
        "Schweizer Wissenschaftsbibliotheken: swisscovery (500+ Bibliotheken, SRU), "
        "e-rara (digitalisierte Druckwerke), e-periodica (Zeitschriften), "
        "e-manuscripta (Handschriften). Alle Quellen sind ohne API-Key zugänglich. "
        "Starte mit `library_info` für eine Übersicht aller verfügbaren Tools und Quellen."
    ),
)

# ─── Pydantic-Eingabemodelle ──────────────────────────────────────────────────


class SwisscoverySearchInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    query: str = Field(
        ...,
        description=(
            "Suchanfrage im CQL-Format. Einfache Terme werden als Volltextsuche interpretiert. "
            "Feldspezifisch: title = 'Volksschule', creator = 'Einstein', subject = 'Pädagogik', "
            "isbn = '978-3-05-006234-0'. Kombinieren mit AND/OR/NOT."
        ),
        min_length=1,
        max_length=500,
        examples=["Volksschule Zürich", "title = \"Bildung\" AND creator = \"Pestalozzi\""],
    )
    max_records: int = Field(
        default=10,
        description="Maximale Anzahl Ergebnisse (1–50).",
        ge=1,
        le=50,
    )
    start_record: int = Field(
        default=1,
        description="Startposition für Pagination (1-basiert).",
        ge=1,
    )
    response_format: str = Field(
        default="markdown",
        description="Ausgabeformat: 'markdown' (lesbar) oder 'json' (maschinenlesbar).",
        pattern="^(markdown|json)$",
    )


class SwisscoveryGetRecordInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    mms_id: str = Field(
        ...,
        description=(
            "MMS-ID des Eintrags (aus swisscovery_search-Ergebnissen). "
            "Beispiel: '991134165199705501'."
        ),
        min_length=5,
    )


class OaiSearchInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    from_date: Optional[str] = Field(
        default=None,
        description="Startdatum (ISO 8601: YYYY-MM-DD oder YYYY-MM-DDTHH:MM:SSZ). Beispiel: '2020-01-01'.",
        pattern=r"^\d{4}-\d{2}-\d{2}(T\d{2}:\d{2}:\d{2}Z)?$",
    )
    until_date: Optional[str] = Field(
        default=None,
        description="Enddatum (ISO 8601). Beispiel: '2023-12-31'.",
        pattern=r"^\d{4}-\d{2}-\d{2}(T\d{2}:\d{2}:\d{2}Z)?$",
    )
    set_spec: Optional[str] = Field(
        default=None,
        description=(
            "OAI-Set-Bezeichner zur Einschränkung auf eine Teilsammlung (Bibliothek). "
            "Verfügbare Sets erhältst du mit dem jeweiligen list_collections-Tool. "
            "Beispiele für e-rara: 'zut' (ETH-Bibliothek), 'bau_1' (UB Basel)."
        ),
        max_length=100,
    )
    resumption_token: Optional[str] = Field(
        default=None,
        description=(
            "Paginierungs-Token aus einer vorherigen Antwort (resumption_token-Feld). "
            "Bei Angabe werden from_date, until_date und set_spec ignoriert."
        ),
    )
    response_format: str = Field(
        default="markdown",
        description="Ausgabeformat: 'markdown' oder 'json'.",
        pattern="^(markdown|json)$",
    )


class OaiGetRecordInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    oai_identifier: str = Field(
        ...,
        description=(
            "OAI-Identifier des Eintrags (aus den list_records-Ergebnissen). "
            "Beispiele: 'oai:www.e-rara.ch:29725195', 'oai:agora.ch:ars-006:2023:1::62'."
        ),
        min_length=5,
    )
    response_format: str = Field(
        default="markdown",
        description="Ausgabeformat: 'markdown' oder 'json'.",
        pattern="^(markdown|json)$",
    )


class ListCollectionsInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    filter_name: Optional[str] = Field(
        default=None,
        description="Optionaler Filter: Nur Sammlungen anzeigen, deren Name diesen Text enthält.",
        max_length=100,
    )


# ─── Hilfsfunktionen ─────────────────────────────────────────────────────────


async def _oai_list_records(base_url: str, params: OaiSearchInput) -> dict[str, Any]:
    """Generische OAI-PMH ListRecords-Abfrage für alle drei Digitalportale."""
    if params.resumption_token:
        query_params: dict[str, str] = {
            "verb": "ListRecords",
            "resumptionToken": params.resumption_token,
        }
    else:
        query_params = {
            "verb": "ListRecords",
            "metadataPrefix": "oai_dc",
        }
        if params.from_date:
            query_params["from"] = params.from_date
        if params.until_date:
            query_params["until"] = params.until_date
        if params.set_spec:
            query_params["set"] = params.set_spec

    xml_text = await http_get(base_url, query_params)
    return parse_oai_response(xml_text)


async def _oai_get_record(base_url: str, oai_identifier: str) -> dict[str, Any]:
    """Generische OAI-PMH GetRecord-Abfrage."""
    xml_text = await http_get(base_url, {
        "verb": "GetRecord",
        "identifier": oai_identifier,
        "metadataPrefix": "oai_dc",
    })
    result = parse_oai_response(xml_text)
    records = result.get("records", [])
    if not records:
        raise ValueError(f"Kein Eintrag mit Identifier '{oai_identifier}' gefunden.")
    return records[0]


async def _oai_list_collections(base_url: str, filter_name: str | None = None) -> list[dict[str, str]]:
    """Generische OAI-PMH ListSets-Abfrage."""
    xml_text = await http_get(base_url, {"verb": "ListSets"})
    sets = parse_oai_sets(xml_text)
    if filter_name:
        lower_filter = filter_name.lower()
        sets = [s for s in sets if lower_filter in s["name"].lower() or lower_filter in s["spec"].lower()]
    return sets


def _format_oai_result(result: dict[str, Any], source_name: str, response_format: str) -> str:
    """Formatiert OAI-Listenergebnisse als Markdown oder JSON."""
    records = result["records"]
    total_size = result.get("total_size")
    resumption_token = result.get("resumption_token")

    if response_format == "json":
        output = {
            "source": source_name,
            "count": len(records),
            "total_size": total_size,
            "resumption_token": resumption_token,
            "records": records,
        }
        return json.dumps(output, ensure_ascii=False, indent=2)

    if not records:
        return f"Keine Einträge in **{source_name}** für die angegebenen Filterkriterien gefunden."

    header = f"## {source_name} – {len(records)} Einträge"
    if total_size:
        header += f" (von insgesamt {total_size:,})"

    lines = [header, ""]
    for i, rec in enumerate(records, 1):
        lines.append(format_oai_record_md(rec, index=i))
        lines.append("")

    if resumption_token:
        lines.append(
            f"---\n*Weitere Einträge verfügbar. Nächste Seite abrufen mit:*\n"
            f"`resumption_token = \"{resumption_token}\"`"
        )

    return "\n".join(lines)


# ─── TOOL 1: library_info ─────────────────────────────────────────────────────


@mcp.tool(
    name="library_info",
    annotations={
        "title": "Übersicht Swiss Academic Libraries MCP",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def library_info() -> str:
    """
    Übersicht aller verfügbaren Datenquellen und Tools dieses MCP-Servers.

    Empfohlen als Einstiegspunkt: zeigt alle vier Bibliotheksquellen,
    die verfügbaren Tools mit kurzen Beschreibungen und Beispielanfragen.
    Kein Netzwerkzugriff erforderlich.

    Returns:
        str: Markdown-Dokumentation mit Datenquellen, Tool-Übersicht und Beispielen.
    """
    return """# Swiss Academic Libraries MCP Server

## Datenquellen (alle ohne API-Key)

| Quelle | Inhalt | Protokoll | Einträge |
|--------|--------|-----------|----------|
| **swisscovery** | 500+ Schweizer Bibliotheken (Bücher, Zeitschriften, AV-Medien) | SRU / MARC21 | 10+ Mio. |
| **e-rara** | Digitalisierte historische Druckwerke | OAI-PMH / Dublin Core | 250'000+ |
| **e-periodica** | Digitalisierte Zeitschriften und Periodika | OAI-PMH / Dublin Core | 1 Mio.+ Artikel |
| **e-manuscripta** | Digitalisierte Handschriften und Archivalien | OAI-PMH / Dublin Core | 100'000+ |

## Verfügbare Tools

### swisscovery (SLSP-Netzwerk)
- `swisscovery_search` — Volltextsuche im Gesamtkatalog (CQL-Syntax)
- `swisscovery_get_record` — Einzeltitel via MMS-ID abrufen

### e-rara (historische Druckwerke)
- `erara_list_records` — Neue/geänderte Einträge nach Datum/Sammlung
- `erara_get_record` — Einzeltitel via OAI-Identifier
- `erara_list_collections` — Alle beteiligten Bibliotheken/Sammlungen

### e-periodica (Zeitschriften)
- `eperiodica_list_records` — Neue/geänderte Artikel nach Datum/Zeitschrift
- `eperiodica_get_record` — Einzelartikel via OAI-Identifier

### e-manuscripta (Handschriften)
- `emanuscripta_list_records` — Neue/geänderte Objekte nach Datum/Sammlung
- `emanuscripta_get_record` — Einzelobjekt via OAI-Identifier

## CQL-Syntax für swisscovery_search

```
Einfache Suche:    Volksschule Zürich
Titelsuche:        title = "Bildungsreform"
Autorensuche:      creator = "Pestalozzi"
Schlagwortsuche:   subject = "Pädagogik"
ISBN:              isbn = "978-3-05-006234-0"
Kombination:       title = "Schule" AND subject = "Zürich"
```

## Beispielanfragen

- *«Welche Bücher über Volksschule erschienen in Zürich?»*
  → `swisscovery_search(query="title = \\"Volksschule\\" AND subject = \\"Zürich\\"")`

- *«Zeige mir historische Druckwerke der ETH-Bibliothek aus 2024»*
  → `erara_list_records(set_spec="zut", from_date="2024-01-01")`

- *«Welche Zeitschriften wurden in e-periodica 2023 ergänzt?»*
  → `eperiodica_list_records(from_date="2023-01-01", until_date="2023-12-31")`

- *«Welche Handschriften-Sammlungen sind in e-manuscripta?»*
  → `emanuscripta_list_collections()`

## Lizenz

Bibliografische Metadaten von swisscovery: Open Data (freie Nutzung gemäss SLSP-Strategie).
e-rara, e-periodica, e-manuscripta: Öffentlich zugänglich, Einzelwerke unter unterschiedlichen Lizenzen.
Dieser MCP-Server: MIT License — github.com/malkreide/swiss-academic-libraries-mcp
"""


# ─── TOOL 2: swisscovery_search ───────────────────────────────────────────────


@mcp.tool(
    name="swisscovery_search",
    annotations={
        "title": "swisscovery Katalogsuche",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def swisscovery_search(params: SwisscoverySearchInput) -> str:
    """
    Durchsucht den swisscovery-Gesamtkatalog (500+ Schweizer Bibliotheken) via SRU.

    Unterstützt einfache Volltextsuche und CQL-Feldsuche:
    - Volltextsuche: "Volksschule Zürich"
    - Titelsuche: title = "Bildungsreform"
    - Autorensuche: creator = "Pestalozzi"
    - Schlagwortsuche: subject = "Pädagogik"
    - Kombiniert: title = "Schule" AND creator = "Pestalozzi"

    Args:
        params (SwisscoverySearchInput): Suchparameter:
            - query (str): CQL-Suchanfrage
            - max_records (int): Maximale Ergebnisanzahl (1–50, Standard: 10)
            - start_record (int): Startposition für Pagination (Standard: 1)
            - response_format (str): 'markdown' oder 'json'

    Returns:
        str: Formatierte Liste der Treffer mit Titel, Autor, Erscheinungsinfo,
             Sprache, ISBN/ISSN, MMS-ID und swisscovery-Link.
             Bei JSON: vollständiges MARC-geparsertes Dict pro Eintrag.
             Enthält Gesamttrefferanzahl und next_record_position für Pagination.
    """
    try:
        sru_params = {
            "version": "1.2",
            "operation": "searchRetrieve",
            "query": params.query,
            "maximumRecords": str(params.max_records),
            "startRecord": str(params.start_record),
            "recordSchema": "marcxml",
        }
        xml_text = await http_get(SWISSCOVERY_SRU_URL, sru_params)
        result = parse_sru_response(xml_text)
    except Exception as e:
        return handle_api_error(e, "swisscovery_search")

    total = result["total"]
    records = result["records"]
    next_pos = result["next_record_position"]

    if params.response_format == "json":
        output = {
            "source": "swisscovery",
            "query": params.query,
            "total": total,
            "start_record": params.start_record,
            "count": len(records),
            "next_record_position": next_pos,
            "records": records,
        }
        return json.dumps(output, ensure_ascii=False, indent=2)

    if total == 0:
        return f"Keine Treffer für **{params.query}** in swisscovery."

    header = f"## swisscovery — {total:,} Treffer für «{params.query}»"
    range_info = f"(Einträge {params.start_record}–{params.start_record + len(records) - 1})"
    lines = [header, range_info, ""]

    for i, rec in enumerate(records, params.start_record):
        lines.append(format_marc_record_md(rec, index=i))
        lines.append("")

    if next_pos:
        lines.append(
            f"---\n*Weitere Treffer vorhanden. Nächste Seite:*\n"
            f"`start_record = {next_pos}`"
        )

    return "\n".join(lines)


# ─── TOOL 3: swisscovery_get_record ──────────────────────────────────────────


@mcp.tool(
    name="swisscovery_get_record",
    annotations={
        "title": "swisscovery Einzeltitel abrufen",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def swisscovery_get_record(params: SwisscoveryGetRecordInput) -> str:
    """
    Ruft einen einzelnen Titel aus swisscovery via MMS-ID ab.

    Die MMS-ID wird aus den Ergebnissen von swisscovery_search (Feld 'mms_id') entnommen.

    Args:
        params (SwisscoveryGetRecordInput): Input mit:
            - mms_id (str): MMS-ID des Titels (z.B. '991134165199705501')

    Returns:
        str: Detaillierter MARC-Eintrag als Markdown inkl. aller verfügbaren Felder:
             Titel, Autor, Erscheinungsinfo, Umfang, Sprache, ISBN/ISSN,
             Schlagworte, Abstract, URLs und swisscovery-Permalink.
    """
    try:
        # SRU-Abfrage via rec.identifier
        sru_params = {
            "version": "1.2",
            "operation": "searchRetrieve",
            "query": f"rec.identifier = \"{params.mms_id}\"",
            "maximumRecords": "1",
            "recordSchema": "marcxml",
        }
        xml_text = await http_get(SWISSCOVERY_SRU_URL, sru_params)
        result = parse_sru_response(xml_text)
    except Exception as e:
        return handle_api_error(e, "swisscovery_get_record")

    records = result["records"]
    if not records:
        return (
            f"Kein Eintrag mit MMS-ID **{params.mms_id}** gefunden. "
            "Bitte MMS-ID aus swisscovery_search-Ergebnissen verwenden."
        )

    rec = records[0]
    # Vollständige Ausgabe aller MARC-Felder
    lines = [f"# {rec.get('title', 'Kein Titel')}"]
    lines.append("")

    field_labels = {
        "creator": "Autor/in",
        "contributors": "Mitwirkende",
        "publication_info": "Erschienen",
        "extent": "Umfang",
        "language": "Sprache",
        "isbn": "ISBN",
        "issn": "ISSN",
        "series": "Reihe",
        "content_type": "Inhaltstyp",
        "mms_id": "MMS-ID",
        "abstract": "Abstract",
        "subjects": "Schlagworte",
        "urls": "Online-Links",
    }

    for key, label in field_labels.items():
        value = rec.get(key)
        if not value:
            continue
        if isinstance(value, list):
            lines.append(f"**{label}:** {' | '.join(value[:5])}")
        else:
            lines.append(f"**{label}:** {value}")

    mms_id = rec.get("mms_id", params.mms_id)
    lines.append(
        f"\n**swisscovery-Link:** "
        f"https://swisscovery.slsp.ch/permalink/41SLSP_NETWORK/1ufb5t2/alma{mms_id}"
    )

    return "\n".join(lines)


# ─── TOOL 4: erara_list_records ──────────────────────────────────────────────


@mcp.tool(
    name="erara_list_records",
    annotations={
        "title": "e-rara: Digitalisierte Druckwerke",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def erara_list_records(params: OaiSearchInput) -> str:
    """
    Listet digitalisierte historische Druckwerke aus e-rara (OAI-PMH).

    e-rara enthält über 250'000 digitalisierte Werke aus Schweizer Bibliotheken,
    darunter historische Bücher, Karten, Flugblätter und Einblattdrucke.

    Verfügbare Sammlungen (set_spec) mit erara_list_collections abrufen.
    Bekannte Sets: 'zut' (ETH-Bibliothek), 'bau_1' (UB Basel),
    'bge_g' (BGE Genf), 'stibi' (Stiftsbibliothek St. Gallen).

    Args:
        params (OaiSearchInput): Filterparameter:
            - from_date (str): Startdatum YYYY-MM-DD (optional)
            - until_date (str): Enddatum YYYY-MM-DD (optional)
            - set_spec (str): Sammlung/Bibliothek (optional)
            - resumption_token (str): Pagination-Token (optional)
            - response_format (str): 'markdown' oder 'json'

    Returns:
        str: Liste der Einträge mit Titel, Autor, Datum, Verlag, Typ, URL.
             Enthält resumption_token für weitere Seiten und Gesamtanzahl.
    """
    try:
        result = await _oai_list_records(ERARA_OAI_URL, params)
    except Exception as e:
        return handle_api_error(e, "erara_list_records")

    return _format_oai_result(result, "e-rara (Digitalisierte Druckwerke)", params.response_format)


# ─── TOOL 5: erara_get_record ─────────────────────────────────────────────────


@mcp.tool(
    name="erara_get_record",
    annotations={
        "title": "e-rara: Einzelwerk abrufen",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def erara_get_record(params: OaiGetRecordInput) -> str:
    """
    Ruft ein einzelnes digitalisiertes Druckwerk aus e-rara ab.

    Die OAI-Identifier stammen aus den Ergebnissen von erara_list_records.
    Format: 'oai:www.e-rara.ch:{id}' (z.B. 'oai:www.e-rara.ch:29725195')

    Args:
        params (OaiGetRecordInput): Input mit:
            - oai_identifier (str): OAI-Identifier des Werks
            - response_format (str): 'markdown' oder 'json'

    Returns:
        str: Vollständige Dublin-Core-Metadaten: Titel, Autor(en), Datum,
             Verlag, Typ, Themen, Beschreibung, Relationen und Digitalisat-URL.
    """
    try:
        rec = await _oai_get_record(ERARA_OAI_URL, params.oai_identifier)
    except Exception as e:
        return handle_api_error(e, "erara_get_record")

    if params.response_format == "json":
        return json.dumps(rec, ensure_ascii=False, indent=2)

    lines = [f"# {rec.get('title', 'Kein Titel')} (e-rara)", ""]
    field_labels = {
        "creators": "Autor(en)",
        "contributors": "Mitwirkende",
        "date": "Datum",
        "publisher": "Verlag/Quelle",
        "type": "Typ",
        "language": "Sprache",
        "subjects": "Themen",
        "description": "Beschreibung",
        "relations": "Relationen",
        "oai_identifier": "OAI-Identifier",
        "last_modified": "Zuletzt geändert",
        "url": "Digitalisat",
    }
    for key, label in field_labels.items():
        value = rec.get(key)
        if not value:
            continue
        if isinstance(value, list):
            lines.append(f"**{label}:** {' | '.join(value[:5])}")
        else:
            lines.append(f"**{label}:** {value}")

    return "\n".join(lines)


# ─── TOOL 6: erara_list_collections ──────────────────────────────────────────


@mcp.tool(
    name="erara_list_collections",
    annotations={
        "title": "e-rara: Sammlungen auflisten",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def erara_list_collections(params: ListCollectionsInput) -> str:
    """
    Listet alle in e-rara vertretenen Bibliotheken und Sammlungen auf.

    Die Set-Bezeichner (spec) können als set_spec in erara_list_records
    verwendet werden, um die Suche auf eine bestimmte Bibliothek einzuschränken.

    Args:
        params (ListCollectionsInput): Input mit:
            - filter_name (str): Filter nach Bibliotheksname (optional)

    Returns:
        str: Tabellarische Übersicht aller Sammlungen mit Set-Bezeichner und Name.
    """
    try:
        sets = await _oai_list_collections(ERARA_OAI_URL, params.filter_name)
    except Exception as e:
        return handle_api_error(e, "erara_list_collections")

    if not sets:
        return "Keine Sammlungen gefunden" + (f" für Filter «{params.filter_name}»." if params.filter_name else ".")

    lines = [f"## e-rara – {len(sets)} Sammlungen/Bibliotheken", ""]
    lines.append("| Set-Bezeichner | Bibliothek/Sammlung |")
    lines.append("|----------------|---------------------|")
    for s in sets:
        lines.append(f"| `{s['spec']}` | {s['name']} |")

    lines.append(
        "\n*Tipp: Verwende den Set-Bezeichner als `set_spec` in `erara_list_records`.*"
    )
    return "\n".join(lines)


# ─── TOOL 7: eperiodica_list_records ─────────────────────────────────────────


@mcp.tool(
    name="eperiodica_list_records",
    annotations={
        "title": "e-periodica: Zeitschriftenartikel",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def eperiodica_list_records(params: OaiSearchInput) -> str:
    """
    Listet digitalisierte Zeitschriftenartikel und Periodika aus e-periodica (OAI-PMH).

    e-periodica bietet Zugriff auf über 1 Million digitalisierte Artikel
    aus Schweizer Zeitschriften (1750–heute), darunter Fachzeitschriften,
    Kulturzeitschriften und historische Periodika.

    OAI-Identifier-Format: 'oai:agora.ch:{zeitschrift}:{jahr}:{heft}::{seite}'

    Args:
        params (OaiSearchInput): Filterparameter:
            - from_date (str): Startdatum YYYY-MM-DD (optional)
            - until_date (str): Enddatum YYYY-MM-DD (optional)
            - set_spec (str): Zeitschriften-Set (optional)
            - resumption_token (str): Pagination-Token (optional)
            - response_format (str): 'markdown' oder 'json'

    Returns:
        str: Liste der Artikel mit Titel, Autor(en), Datum, Quelle/Zeitschrift, URL.
             Enthält resumption_token und Gesamtanzahl für Pagination.
    """
    try:
        result = await _oai_list_records(EPERIODICA_OAI_URL, params)
    except Exception as e:
        return handle_api_error(e, "eperiodica_list_records")

    return _format_oai_result(result, "e-periodica (Zeitschriften)", params.response_format)


# ─── TOOL 8: eperiodica_get_record ───────────────────────────────────────────


@mcp.tool(
    name="eperiodica_get_record",
    annotations={
        "title": "e-periodica: Einzelartikel abrufen",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def eperiodica_get_record(params: OaiGetRecordInput) -> str:
    """
    Ruft einen einzelnen Zeitschriftenartikel aus e-periodica ab.

    Die OAI-Identifier stammen aus den Ergebnissen von eperiodica_list_records.
    Format: 'oai:agora.ch:{zeitschrift}:{jahr}:{heft}::{seite}'

    Args:
        params (OaiGetRecordInput): Input mit:
            - oai_identifier (str): OAI-Identifier des Artikels
            - response_format (str): 'markdown' oder 'json'

    Returns:
        str: Vollständige Dublin-Core-Metadaten: Titel, Autor(en), Datum,
             Quelle, Themen, Beschreibung, Sprache und Digitalisat-URL.
    """
    try:
        rec = await _oai_get_record(EPERIODICA_OAI_URL, params.oai_identifier)
    except Exception as e:
        return handle_api_error(e, "eperiodica_get_record")

    if params.response_format == "json":
        return json.dumps(rec, ensure_ascii=False, indent=2)

    lines = [f"# {rec.get('title', 'Kein Titel')} (e-periodica)", ""]
    field_labels = {
        "creators": "Autor(en)",
        "date": "Datum",
        "publisher": "Zeitschrift/Quelle",
        "language": "Sprache",
        "subjects": "Themen",
        "description": "Beschreibung",
        "relations": "Relationen",
        "oai_identifier": "OAI-Identifier",
        "last_modified": "Zuletzt geändert",
        "url": "Digitalisat",
    }
    for key, label in field_labels.items():
        value = rec.get(key)
        if not value:
            continue
        if isinstance(value, list):
            lines.append(f"**{label}:** {' | '.join(value[:5])}")
        else:
            lines.append(f"**{label}:** {value}")

    return "\n".join(lines)


# ─── TOOL 9: emanuscripta_list_records ───────────────────────────────────────


@mcp.tool(
    name="emanuscripta_list_records",
    annotations={
        "title": "e-manuscripta: Handschriften und Archivalien",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def emanuscripta_list_records(params: OaiSearchInput) -> str:
    """
    Listet digitalisierte Handschriften und Archivalien aus e-manuscripta (OAI-PMH).

    e-manuscripta bietet Zugriff auf digitalisierte Handschriften, Nachlässe,
    Briefe und andere Archivmaterialien aus Schweizer Bibliotheken und Archiven.
    Darunter Bestände der ETH-Bibliothek, ZB Zürich, UB Basel u.a.

    Verfügbare Sammlungen mit emanuscripta_list_collections() abrufen.

    Args:
        params (OaiSearchInput): Filterparameter:
            - from_date (str): Startdatum YYYY-MM-DD (optional)
            - until_date (str): Enddatum YYYY-MM-DD (optional)
            - set_spec (str): Sammlung/Archiv (optional)
            - resumption_token (str): Pagination-Token (optional)
            - response_format (str): 'markdown' oder 'json'

    Returns:
        str: Liste der Objekte mit Titel, Autor(en), Datum, Sammlung, Typ, URL.
             Enthält resumption_token und Gesamtanzahl für Pagination.
    """
    try:
        result = await _oai_list_records(EMANUSCRIPTA_OAI_URL, params)
    except Exception as e:
        return handle_api_error(e, "emanuscripta_list_records")

    return _format_oai_result(result, "e-manuscripta (Handschriften & Archivalien)", params.response_format)


# ─── TOOL 10: emanuscripta_get_record ────────────────────────────────────────


@mcp.tool(
    name="emanuscripta_get_record",
    annotations={
        "title": "e-manuscripta: Einzelobjekt abrufen",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def emanuscripta_get_record(params: OaiGetRecordInput) -> str:
    """
    Ruft ein einzelnes Handschriften-Objekt aus e-manuscripta ab.

    Die OAI-Identifier stammen aus den Ergebnissen von emanuscripta_list_records.
    Format: 'oai:www.e-manuscripta.ch:{id}'

    Args:
        params (OaiGetRecordInput): Input mit:
            - oai_identifier (str): OAI-Identifier des Objekts
            - response_format (str): 'markdown' oder 'json'

    Returns:
        str: Vollständige Dublin-Core-Metadaten: Titel, Autor(en), Datum,
             Sammlung/Archiv, Typ, Themen, Beschreibung, Relationen und URL.
    """
    try:
        rec = await _oai_get_record(EMANUSCRIPTA_OAI_URL, params.oai_identifier)
    except Exception as e:
        return handle_api_error(e, "emanuscripta_get_record")

    if params.response_format == "json":
        return json.dumps(rec, ensure_ascii=False, indent=2)

    lines = [f"# {rec.get('title', 'Kein Titel')} (e-manuscripta)", ""]
    field_labels = {
        "creators": "Autor(en)/Verfasser",
        "date": "Datum/Entstehungszeit",
        "publisher": "Sammlung/Archiv",
        "type": "Objekttyp",
        "language": "Sprache",
        "subjects": "Themen",
        "description": "Beschreibung",
        "relations": "Verwandte Objekte",
        "contributors": "Mitwirkende",
        "oai_identifier": "OAI-Identifier",
        "last_modified": "Zuletzt geändert",
        "url": "Digitalisat",
    }
    for key, label in field_labels.items():
        value = rec.get(key)
        if not value:
            continue
        if isinstance(value, list):
            lines.append(f"**{label}:** {' | '.join(value[:5])}")
        else:
            lines.append(f"**{label}:** {value}")

    return "\n".join(lines)


# ─── Bonus-Tool: emanuscripta_list_collections ───────────────────────────────


@mcp.tool(
    name="emanuscripta_list_collections",
    annotations={
        "title": "e-manuscripta: Sammlungen auflisten",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def emanuscripta_list_collections(params: ListCollectionsInput) -> str:
    """
    Listet alle in e-manuscripta vertretenen Archive und Sammlungen auf.

    Die Set-Bezeichner können als set_spec in emanuscripta_list_records
    verwendet werden.

    Args:
        params (ListCollectionsInput): Input mit:
            - filter_name (str): Filter nach Sammlungsname (optional)

    Returns:
        str: Tabellarische Übersicht aller Sammlungen mit Set-Bezeichner und Name.
    """
    try:
        sets = await _oai_list_collections(EMANUSCRIPTA_OAI_URL, params.filter_name)
    except Exception as e:
        return handle_api_error(e, "emanuscripta_list_collections")

    if not sets:
        return "Keine Sammlungen gefunden" + (f" für Filter «{params.filter_name}»." if params.filter_name else ".")

    lines = [f"## e-manuscripta – {len(sets)} Sammlungen/Archive", ""]
    lines.append("| Set-Bezeichner | Sammlung/Archiv |")
    lines.append("|----------------|-----------------|")
    for s in sets:
        lines.append(f"| `{s['spec']}` | {s['name']} |")

    lines.append(
        "\n*Tipp: Verwende den Set-Bezeichner als `set_spec` in `emanuscripta_list_records`.*"
    )
    return "\n".join(lines)


# ─── Resources ───────────────────────────────────────────────────────────────


@mcp.resource("library://sources")
async def get_sources() -> str:
    """Strukturierte Übersicht aller Datenquellen als JSON-Ressource."""
    sources = {
        "swisscovery": {
            "description": "Nationaler Katalog: 500+ Schweizer Bibliotheken",
            "protocol": "SRU / MARC21",
            "url": SWISSCOVERY_SRU_URL,
            "records": "10+ Millionen",
            "auth_required": False,
            "tools": ["swisscovery_search", "swisscovery_get_record"],
        },
        "e-rara": {
            "description": "Digitalisierte historische Druckwerke",
            "protocol": "OAI-PMH / Dublin Core",
            "url": ERARA_OAI_URL,
            "records": "250'000+",
            "auth_required": False,
            "tools": ["erara_list_records", "erara_get_record", "erara_list_collections"],
        },
        "e-periodica": {
            "description": "Digitalisierte Zeitschriften (1750–heute)",
            "protocol": "OAI-PMH / Dublin Core",
            "url": EPERIODICA_OAI_URL,
            "records": "1 Mio.+ Artikel",
            "auth_required": False,
            "tools": ["eperiodica_list_records", "eperiodica_get_record"],
        },
        "e-manuscripta": {
            "description": "Digitalisierte Handschriften und Archivalien",
            "protocol": "OAI-PMH / Dublin Core",
            "url": EMANUSCRIPTA_OAI_URL,
            "records": "100'000+",
            "auth_required": False,
            "tools": ["emanuscripta_list_records", "emanuscripta_get_record", "emanuscripta_list_collections"],
        },
    }
    return json.dumps(sources, ensure_ascii=False, indent=2)


# ─── Prompts ──────────────────────────────────────────────────────────────────


@mcp.prompt("research-workflow")
async def research_workflow(topic: str) -> str:
    """Strukturierter Recherche-Workflow für ein Thema über alle Quellen."""
    return f"""Führe eine umfassende Recherche zum Thema «{topic}» durch:

1. **swisscovery_search** — Suche im Gesamtkatalog:
   - query: "{topic}" (Volltextsuche)
   - query: subject = "{topic}" (Schlagwortsuche)
   Notiere MMS-IDs interessanter Treffer.

2. **erara_list_records** — Historische Druckwerke zu «{topic}»:
   Keine Datumsbeschränkung für maximale Abdeckung.

3. **eperiodica_list_records** — Zeitschriftenartikel zu «{topic}»:
   from_date: "2010-01-01" für neuere Artikel.

4. **emanuscripta_list_records** — Handschriften/Archivalien zu «{topic}»:
   Falls historische Primärquellen relevant sind.

5. Erstelle eine strukturierte Zusammenfassung:
   - Wichtigste Werke pro Quelle
   - Chronologische Entwicklung des Themas
   - Links zu digitalen Ressourcen wo verfügbar
"""


@mcp.prompt("education-research")
async def education_research(topic: str) -> str:
    """Bildungsrecherche-Workflow für den Schulamt-Kontext."""
    return f"""Bildungsrecherche zum Thema «{topic}» für den Schulamt-Kontext:

1. **swisscovery_search**:
   - query: subject = "{topic}" AND subject = "Bildung"
   - query: title = "{topic}" AND subject = "Volksschule"
   - query: creator = "Pestalozzi" falls historisch relevant

2. **eperiodica_list_records**:
   Fachzeitschriften zu «{topic}» — pädagogische Quellen aus Schweizer Periodika.

3. **erara_list_records** mit set_spec="zut":
   Historische Bildungsquellen der ETH-Bibliothek zu «{topic}».

4. Falls Primärquellen relevant: **emanuscripta_list_records**
   Handschriftliche Quellen (z.B. Schulberichte, Lehrpläne historisch).

Fokus: Schweizer Kontext, Volksschule, praktische Anwendbarkeit für Schulamt Zürich.
"""


# ─── Einstiegspunkt ───────────────────────────────────────────────────────────


def main() -> None:
    transport = "streamable_http" if "--http" in sys.argv else "stdio"
    port = 8000
    for i, arg in enumerate(sys.argv):
        if arg == "--port" and i + 1 < len(sys.argv):
            try:
                port = int(sys.argv[i + 1])
            except ValueError:
                pass

    if transport == "streamable_http":
        mcp.run(transport="streamable_http", port=port)
    else:
        mcp.run()


if __name__ == "__main__":
    main()
