# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
