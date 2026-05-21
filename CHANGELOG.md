# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0](https://github.com/malkreide/swiss-academic-libraries-mcp/releases/tag/v0.1.0) - 2026-03-23
Initial release. This server connects AI models to the full Swiss academic
library infrastructure via open, authentication-free protocols: the
[swisscovery](https://swisscovery.slsp.ch) union catalogue (500+ libraries,
10 M+ records, SRU/MARC21) and three digitisation platforms —
[e-rara](https://www.e-rara.ch), [e-periodica](https://www.e-periodica.ch)
and [e-manuscripta](https://www.e-manuscripta.ch) (OAI-PMH/Dublin Core).
No API key required. Part of the
[Swiss Public Data MCP Portfolio](https://github.com/malkreide).

## [Unreleased]

## [0.3.0] - 2026-05-21

### Security
- **F-02** Streamable-HTTP-Transport bindet jetzt explizit auf
  `127.0.0.1` (Loopback). Neues `--host`-CLI-Flag erlaubt anderes
  Binding; bei Non-Loopback wird eine WARN-Log mit Hinweis auf
  Reverse-Proxy-Pflicht ausgegeben.
- **F-04** CI-Job `security` scannt Dependencies mit `pip-audit`.
  Dependabot wöchentlich für `pip` und `github-actions`.

### Added
- **F-03** Strukturiertes Logging auf **stderr** (niemals stdout —
  würde stdio-JSON-RPC korrumpieren). Log-Level konfigurierbar via
  `MCP_LOG_LEVEL` (Default: `INFO`). Logs für Tool-Start, Upstream-
  Requests, HTTP-Fehler, Timeouts.
- `--host <addr>`-CLI-Flag für Streamable-HTTP-Transport.
- `.github/dependabot.yml` für automatische Dependency-Updates.

### Fixed
- Transport-Bezeichner korrigiert: `streamable-http` (mit Bindestrich)
  gemäß aktueller MCP-Spec. Vorher `streamable_http`, was mit
  neueren `mcp`-Versionen einen TypeError ausgelöst hätte.
- Host/Port werden jetzt via `mcp.settings.host`/`.port` gesetzt,
  da `FastMCP.run()` keine `host`/`port`-kwargs akzeptiert.

### Audit
- Adressiert Findings F-02, F-03, F-04 aus dem Audit vom 2026-05-21.

## [0.2.1] - 2026-05-21

### Security
- **F-01** XML-Parsing nutzt jetzt `defusedxml.ElementTree.fromstring`
  statt `xml.etree.ElementTree.fromstring`. Schützt gegen XML-Bomben
  (billion-laughs, quadratic blowup) bei kompromittierten Upstream-
  Antworten oder MITM-Angriffen.

### Changed
- **F-06** Alle Upstream-HTTP-Requests senden jetzt einen identifizierenden
  `User-Agent`-Header
  (`swiss-academic-libraries-mcp/<version> (+<repo-url>)`).
  Best Practice gegenüber SLSP / ETH-Bibliothek; ermöglicht Whitelisting
  und Abuse-Differenzierung.

### Audit
- Adressiert Findings aus dem Audit vom 2026-05-21
  (`audits/2026-05-21-swiss-academic-libraries-mcp/`).

## [0.1.0] - 2026-03-13

### Added
- **swisscovery** (SLSP network): search and record retrieval via SRU / MARC21
  - `swisscovery_search` — CQL queries against 500+ Swiss libraries
  - `swisscovery_get_record` — single record by MMS-ID
- **e-rara** (digitised historical prints): OAI-PMH / Dublin Core
  - `erara_list_records` — filter by date and set
  - `erara_get_record` — single item by OAI identifier
  - `erara_list_collections` — list all participating libraries
- **e-periodica** (digitised periodicals): OAI-PMH / Dublin Core
  - `eperiodica_list_records` — filter by date
  - `eperiodica_get_record` — single article by OAI identifier
- **e-manuscripta** (manuscripts and archival material): OAI-PMH / Dublin Core
  - `emanuscripta_list_records` — filter by date and set
  - `emanuscripta_get_record` — single object by OAI identifier
  - `emanuscripta_list_collections` — list all archives and collections
- `library_info` — entry point with overview of all sources and tools
- Dual transport: stdio (Claude Desktop) and Streamable HTTP (`--http --port`)
- 2 prompts: `research-workflow` and `education-research`
- 1 resource: `library://sources` (JSON overview of all data sources)
- 34 unit tests (no network), 6 live smoke tests (`-m live`)
- MARC21 parser (20+ fields) and OAI-PMH/Dublin Core parser
- Pagination via `next_record_position` (SRU) and `resumption_token` (OAI-PMH)
- Markdown and JSON output format for all tools

[0.1.0]: https://github.com/malkreide/swiss-academic-libraries-mcp/releases/tag/v0.1.0
