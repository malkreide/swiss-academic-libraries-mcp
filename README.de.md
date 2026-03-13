# swiss-academic-libraries-mcp

![Version](https://img.shields.io/badge/version-0.1.0-blue)
![Lizenz](https://img.shields.io/badge/Lizenz-MIT-green)
![Python](https://img.shields.io/badge/python-3.11+-blue)
![MCP](https://img.shields.io/badge/MCP-kompatibel-brightgreen)
![Kein Auth](https://img.shields.io/badge/Authentifizierung-nicht%20erforderlich-lightgrey)

> MCP-Server für Schweizer Wissenschaftsbibliotheken — swisscovery, e-rara, e-periodica, e-manuscripta. Kein API-Key erforderlich.

[🇬🇧 English Version](README.md)

---

## Übersicht

Dieser MCP-Server verbindet KI-Modelle mit der gesamten Schweizer Bibliotheksinfrastruktur über standardisierte, offene Protokolle. Er deckt den [swisscovery](https://swisscovery.slsp.ch)-Gesamtkatalog (500+ Bibliotheken, 10+ Mio. Einträge) und drei Digitalisierungsplattformen ab: historische Druckwerke ([e-rara](https://www.e-rara.ch)), Zeitschriften ([e-periodica](https://www.e-periodica.ch)) und Handschriften ([e-manuscripta](https://www.e-manuscripta.ch)).

Alle Datenquellen nutzen offene, authentifizierungsfreie Protokolle (SRU/MARC21, OAI-PMH/Dublin Core). Der Server unterstützt lokale Nutzung via Claude Desktop (stdio) und Cloud-Deployment (Streamable HTTP).

## Funktionen

- **11 Tools** für 4 Datenquellen — alle nur lesend, kein API-Key
- **swisscovery-Suche** mit vollständiger CQL-Syntax: Volltext, Titel, Autor, Schlagwort, ISBN/ISSN
- **OAI-PMH-Harvesting** mit Datums- und Sammlungsfilter sowie Pagination via Resumption Tokens
- **MARC21-Parser** mit 20+ Feldern (Titel, Autor, Erscheinungsinfo, Schlagworte, Abstract, URLs)
- **Dublin-Core-Parser** für alle drei Digitalportale
- **Dual Transport**: stdio (Claude Desktop) · Streamable HTTP (Cloud/Self-hosted)
- **2 eingebaute Prompts**: `research-workflow` und `education-research`
- **Markdown- und JSON-Ausgabe** für alle Tools
- **34 Unit-Tests** (kein Netzwerk) + 6 Live-Smoke-Tests

## Datenquellen

| Quelle | Protokoll | Inhalt | Einträge |
|--------|-----------|--------|----------|
| [swisscovery (SLSP)](https://swisscovery.slsp.ch) | SRU / MARC21 | 500+ Schweizer Bibliotheken | 10+ Mio. |
| [e-rara](https://www.e-rara.ch) | OAI-PMH / Dublin Core | Digitalisierte hist. Druckwerke | 250'000+ |
| [e-periodica](https://www.e-periodica.ch) | OAI-PMH / Dublin Core | Digitalisierte Zeitschriften (1750–heute) | 1 Mio.+ |
| [e-manuscripta](https://www.e-manuscripta.ch) | OAI-PMH / Dublin Core | Handschriften & Archivalien | 100'000+ |

## Tools

| Tool | Quelle | Funktion |
|------|--------|----------|
| `library_info` | — | Einstiegspunkt: Übersicht aller Quellen und Tools |
| `swisscovery_search` | swisscovery | Volltext-/CQL-Suche im Gesamtkatalog |
| `swisscovery_get_record` | swisscovery | Einzeltitel via MMS-ID |
| `erara_list_records` | e-rara | Druckwerke nach Datum/Sammlung filtern |
| `erara_get_record` | e-rara | Einzelwerk via OAI-Identifier |
| `erara_list_collections` | e-rara | Alle beteiligten Bibliotheken |
| `eperiodica_list_records` | e-periodica | Artikel nach Datum filtern |
| `eperiodica_get_record` | e-periodica | Einzelartikel via OAI-Identifier |
| `emanuscripta_list_records` | e-manuscripta | Handschriften nach Datum/Sammlung |
| `emanuscripta_get_record` | e-manuscripta | Einzelobjekt via OAI-Identifier |
| `emanuscripta_list_collections` | e-manuscripta | Alle Archive/Sammlungen |

## Voraussetzungen

- Python 3.11 oder höher
- [uv](https://docs.astral.sh/uv/) / uvx (empfohlen) oder pip
- Internetzugang (alle APIs sind öffentlich)

## Installation

### Claude Desktop (empfohlen)

In `claude_desktop_config.json` einfügen:

**macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "swiss-academic-libraries": {
      "command": "uvx",
      "args": ["swiss-academic-libraries-mcp"]
    }
  }
}
```

Claude Desktop neu starten — der Server startet beim ersten Aufruf automatisch.

### Cloud / Self-hosted (Streamable HTTP)

```bash
uvx swiss-academic-libraries-mcp --http --port 8000
```

### Entwicklung

```bash
git clone https://github.com/malkreide/swiss-academic-libraries-mcp
cd swiss-academic-libraries-mcp
pip install -e .
```

## Verwendung / Quickstart

Starte mit `library_info` für eine vollständige Übersicht. Dann:

```
«Welche Bücher über Volksschule gibt es in Schweizer Bibliotheken?»
→ swisscovery_search(query='subject = "Volksschule"', max_records=20)

«Zeige historische Druckwerke der ETH-Bibliothek»
→ erara_list_records(set_spec="zut")

«Welche Zeitschriften wurden 2023 in e-periodica ergänzt?»
→ eperiodica_list_records(from_date="2023-01-01", until_date="2023-12-31")

«Welche Handschriften-Sammlungen hat e-manuscripta?»
→ emanuscripta_list_collections()
```

### CQL-Suchsyntax (swisscovery)

```
Volltext:      Volksschule Zürich
Titel:         title = "Bildungsreform"
Autor:         creator = "Pestalozzi"
Schlagwort:    subject = "Pädagogik"
ISBN:          isbn = "978-3-05-006234-0"
Kombiniert:    title = "Schule" AND creator = "Pestalozzi"
Pagination:    start_record = 11
```

## Konfiguration

Keine API-Keys oder Umgebungsvariablen erforderlich.

| Parameter | Standard | Beschreibung |
|-----------|----------|--------------|
| `--http` | aus | Streamable HTTP Transport aktivieren |
| `--port` | 8000 | Port für HTTP-Transport |

## Projektstruktur

```
swiss-academic-libraries-mcp/
├── src/
│   └── swiss_academic_libraries_mcp/
│       ├── __init__.py       # Package-Init
│       ├── server.py         # FastMCP-Server, 11 Tools, 2 Prompts, 1 Resource
│       └── api_client.py     # HTTP-Client, MARC21- + OAI-PMH/DC-Parser
├── tests/
│   └── test_server.py        # 34 Unit-Tests + 6 Live-Smoke-Tests
├── pyproject.toml
├── CHANGELOG.md
├── LICENSE
├── README.md                 # Englische Version
└── README.de.md              # Diese Datei
```

## Verwandte Server

Teil des [Swiss Public Data MCP Portfolios](https://github.com/malkreide):

| Server | Beschreibung |
|--------|--------------|
| [`zurich-opendata-mcp`](https://github.com/malkreide/zurich-opendata-mcp) | Stadt Zürich Open Data |
| [`eth-library-mcp`](https://github.com/malkreide/eth-library-mcp) | ETH-Bibliothek Discovery & Persons API |
| [`swiss-statistics-mcp`](https://github.com/malkreide/swiss-statistics-mcp) | BFS STAT-TAB (Schweizer Statistik) |
| [`fedlex-mcp`](https://github.com/malkreide/fedlex-mcp) | Bundesrecht via Fedlex SPARQL |
| [`swiss-transport-mcp`](https://github.com/malkreide/swiss-transport-mcp) | OJP Reiseplanung, SIRI-SX Störungen |

## Changelog

Siehe [CHANGELOG.md](CHANGELOG.md)

## Lizenz

MIT-Lizenz — siehe [LICENSE](LICENSE)

## Autor

malkreide · [github.com/malkreide](https://github.com/malkreide)
