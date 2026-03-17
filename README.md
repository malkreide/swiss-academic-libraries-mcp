> 🇨🇭 **Part of the [Swiss Public Data MCP Portfolio](https://github.com/malkreide)**

# 📚 swiss-academic-libraries-mcp

![Version](https://img.shields.io/badge/version-0.1.0-blue)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![MCP](https://img.shields.io/badge/MCP-Model%20Context%20Protocol-purple)](https://modelcontextprotocol.io/)
[![No Auth Required](https://img.shields.io/badge/auth-not%20required-lightgrey)](https://github.com/malkreide/swiss-academic-libraries-mcp)

> MCP server providing access to Swiss academic libraries — swisscovery, e-rara, e-periodica, e-manuscripta. No API key required.

[🇩🇪 Deutsche Version](README.de.md)

---

## Overview

**swiss-academic-libraries-mcp** connects AI models to the full Swiss academic library infrastructure via standardised, open protocols. It covers the [swisscovery](https://swisscovery.slsp.ch) union catalogue (500+ libraries, 10M+ records) and three digitalisation platforms: historical prints ([e-rara](https://www.e-rara.ch)), periodicals ([e-periodica](https://www.e-periodica.ch)) and manuscripts ([e-manuscripta](https://www.e-manuscripta.ch)).

All data sources use open, authentication-free protocols (SRU/MARC21, OAI-PMH/Dublin Core). The server supports both local use via Claude Desktop (stdio transport) and cloud deployment (Streamable HTTP).

**Anchor demo query:** *"Which Swiss university dissertations on primary school pedagogy are held in Swiss libraries, and are any of them digitised in e-rara?"*

---

## Features

- **11 tools** across 4 data sources — all read-only, no API key required
- **swisscovery search** with full CQL syntax: full-text, title, author, subject, ISBN/ISSN
- **OAI-PMH harvesting** with date range and collection filters plus pagination via resumption tokens
- **MARC21 parser** extracting 20+ fields (title, creator, publication info, subjects, abstract, URLs)
- **Dublin Core parser** for all three digitalisation portals
- **Dual transport**: stdio for Claude Desktop · Streamable HTTP for cloud/self-hosted deployments
- **2 built-in prompts**: `research-workflow` and `education-research`
- **Markdown and JSON output** for all tools
- **34 unit tests** (no network) + 6 live smoke tests

---

## Data Sources

| Source | Protocol | Content | Records |
|--------|----------|---------|---------||
| [swisscovery (SLSP)](https://swisscovery.slsp.ch) | SRU / MARC21 | 500+ Swiss libraries | 10M+ |
| [e-rara](https://www.e-rara.ch) | OAI-PMH / Dublin Core | Digitised historical prints | 250k+ |
| [e-periodica](https://www.e-periodica.ch) | OAI-PMH / Dublin Core | Digitised periodicals (1750–today) | 1M+ articles |
| [e-manuscripta](https://www.e-manuscripta.ch) | OAI-PMH / Dublin Core | Manuscripts & archival material | 100k+ |

---

## Tools

| Tool | Source | Function |
|------|--------|----------|
| `library_info` | — | Entry point: overview of all sources and tools |
| `swisscovery_search` | swisscovery | Full-text / CQL search across the union catalogue |
| `swisscovery_get_record` | swisscovery | Single record by MMS-ID |
| `erara_list_records` | e-rara | Prints filtered by date / collection |
| `erara_get_record` | e-rara | Single item by OAI identifier |
| `erara_list_collections` | e-rara | All participating libraries |
| `eperiodica_list_records` | e-periodica | Articles filtered by date |
| `eperiodica_get_record` | e-periodica | Single article by OAI identifier |
| `emanuscripta_list_records` | e-manuscripta | Manuscripts filtered by date / collection |
| `emanuscripta_get_record` | e-manuscripta | Single object by OAI identifier |
| `emanuscripta_list_collections` | e-manuscripta | All archives / collections |

### Example Use Cases

| Query | Tool |
|-------|------|
| *"Which books about Swiss primary schools are held in Swiss libraries?"* | `swisscovery_search` |
| *"Show digitised historical works from ETH Library"* | `erara_list_records` |
| *"Which Swiss periodicals were digitised in 2023?"* | `eperiodica_list_records` |
| *"What manuscript collections does e-manuscripta hold?"* | `emanuscripta_list_collections` |

---

## Prerequisites

- Python 3.11 or higher
- [uv](https://docs.astral.sh/uv/) / uvx (recommended) or pip
- Internet access (all APIs are publicly available)

---

## Installation

### Claude Desktop (recommended)

Add to `claude_desktop_config.json`:

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

Restart Claude Desktop — the server starts automatically on first use.

### Cloud / Self-hosted (Streamable HTTP)

```bash
uvx swiss-academic-libraries-mcp --http --port 8000
```

### Development

```bash
git clone https://github.com/malkreide/swiss-academic-libraries-mcp
cd swiss-academic-libraries-mcp
pip install -e .
```

---

## Quickstart

Start by calling `library_info` for a full overview. Then:

```
"Which books about Swiss primary schools are held in Swiss libraries?"
→ swisscovery_search(query='subject = "Volksschule"', max_records=20)

"Show digitised historical works from ETH Library"
→ erara_list_records(set_spec="zut")

"Which Swiss periodicals were digitised in 2023?"
→ eperiodica_list_records(from_date="2023-01-01", until_date="2023-12-31")

"What manuscript collections does e-manuscripta hold?"
→ emanuscripta_list_collections()
```

> 💡 *"No API key — just install and query."*

### CQL Search Syntax (swisscovery)

```
Full text:     Volksschule Zürich
Title:         title = "education reform"
Author:        creator = "Pestalozzi"
Subject:       subject = "pedagogy"
ISBN:          isbn = "978-3-05-006234-0"
Combined:      title = "school" AND creator = "Pestalozzi"
Pagination:    start_record = 11
```

---

## Configuration

No API keys or environment variables required.

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--http` | off | Enable Streamable HTTP transport |
| `--port` | 8000 | Port for HTTP transport |

---

## Project Structure

```
swiss-academic-libraries-mcp/
├── src/
│   └── swiss_academic_libraries_mcp/
│       ├── __init__.py       # Package init
│       ├── server.py         # FastMCP server, 11 tools, 2 prompts, 1 resource
│       └── api_client.py     # HTTP client, MARC21 + OAI-PMH/DC parsers
├── tests/
│   └── test_server.py        # 34 unit tests + 6 live smoke tests
├── pyproject.toml
├── CHANGELOG.md
├── CONTRIBUTING.md
├── LICENSE
├── README.md                 # This file (English)
└── README.de.md              # German version
```

---

## Testing

```bash
# Unit tests (no network required)
PYTHONPATH=src pytest tests/ -m "not live"

# Live smoke tests (internet required)
PYTHONPATH=src pytest tests/ -m "live"
```

---

## Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on:

- Reporting bugs and requesting features
- Setting up the development environment
- Code style and test requirements
- Submitting pull requests

This project follows the conventions of the [Swiss Public Data MCP Portfolio](https://github.com/malkreide).

---

## Changelog

See [CHANGELOG.md](CHANGELOG.md)

---

## License

MIT License — see [LICENSE](LICENSE)

---

## Author

malkreide · [github.com/malkreide](https://github.com/malkreide)

---

## Credits & Related Projects

- **Data:** [swisscovery / SLSP](https://swisscovery.slsp.ch) · [e-rara](https://www.e-rara.ch) · [e-periodica](https://www.e-periodica.ch) · [e-manuscripta](https://www.e-manuscripta.ch)
- **Protocol:** [Model Context Protocol](https://modelcontextprotocol.io/) — Anthropic / Linux Foundation
- **Related:** [eth-library-mcp](https://github.com/malkreide/eth-library-mcp) — ETH Library Discovery & Persons API
- **Portfolio:** [Swiss Public Data MCP Portfolio](https://github.com/malkreide)

| Server | Description |
|--------|-------------|
| [`zurich-opendata-mcp`](https://github.com/malkreide/zurich-opendata-mcp) | City of Zurich Open Data |
| [`eth-library-mcp`](https://github.com/malkreide/eth-library-mcp) | ETH Library Discovery & Persons API |
| [`swiss-statistics-mcp`](https://github.com/malkreide/swiss-statistics-mcp) | Swiss Federal Statistics (BFS) |
| [`fedlex-mcp`](https://github.com/malkreide/fedlex-mcp) | Swiss Federal Law via Fedlex SPARQL |
| [`swiss-transport-mcp`](https://github.com/malkreide/swiss-transport-mcp) | OJP journey planning, SIRI-SX disruptions |
