[🇬🇧 English Version](README.md)

> 🇨🇭 **Teil des [Swiss Public Data MCP Portfolios](https://github.com/malkreide)**

# 📚 swiss-academic-libraries-mcp

[![PyPI Version](https://img.shields.io/pypi/v/swiss-academic-libraries-mcp)](https://pypi.org/project/swiss-academic-libraries-mcp/)
[![Lizenz: MIT](https://img.shields.io/badge/Lizenz-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![MCP](https://img.shields.io/badge/MCP-Model%20Context%20Protocol-purple)](https://modelcontextprotocol.io/)
[![Kein Auth erforderlich](https://img.shields.io/badge/Authentifizierung-nicht%20erforderlich-lightgrey)](https://github.com/malkreide/swiss-academic-libraries-mcp)
![CI](https://github.com/malkreide/swiss-academic-libraries-mcp/actions/workflows/ci.yml/badge.svg)

> MCP-Server für Schweizer Wissenschaftsbibliotheken — swisscovery, e-rara, e-periodica, e-manuscripta. Kein API-Key erforderlich.

---

## Übersicht

**swiss-academic-libraries-mcp** verbindet KI-Modelle mit der gesamten Schweizer Bibliotheksinfrastruktur über standardisierte, offene Protokolle. Er deckt den [swisscovery](https://swisscovery.slsp.ch)-Gesamtkatalog (500+ Bibliotheken, 10+ Mio. Einträge) und drei Digitalisierungsplattformen ab: historische Druckwerke ([e-rara](https://www.e-rara.ch)), Zeitschriften ([e-periodica](https://www.e-periodica.ch)) und Handschriften ([e-manuscripta](https://www.e-manuscripta.ch)).

Alle Datenquellen nutzen offene, authentifizierungsfreie Protokolle (SRU/MARC21, OAI-PMH/Dublin Core). Der Server unterstützt lokale Nutzung via Claude Desktop (stdio) und Cloud-Deployment (Streamable HTTP).

Über den Katalog hinaus erschliesst der Server **frei zugängliche schweizerische Rechtsliteratur** — Beiträge aus [sui generis](https://sui-generis.ch), [ex/ante](https://ex-ante.ch) und [Repositorium.ch](https://www.repositorium.ch) — als **Metadaten** (Titel, Autorschaft, Jahr, Lizenz, DOI, Link), nie als Volltext.

**Anker-Demo-Abfrage (Katalog):** *«Welche Schweizer Hochschul-Dissertationen zur Primarschulpädagogik sind in Schweizer Bibliotheken vorhanden – und sind einige davon in e-rara digitalisiert?»*

**Anker-Demo-Abfrage (OA-Rechtsliteratur):** *«Welche frei zugänglichen rechtswissenschaftlichen Beiträge gibt es zu Datenschutz? Gib mir Titel, Autorschaft, Jahr, Lizenz und DOI.»* → `oa_law_search(query="Datenschutz")`

---

## Funktionen

- **13 Tools** für 4 Katalogquellen + 3 OA-Rechtsliteratur-Quellen — alle nur lesend, kein API-Key
- **swisscovery-Suche** mit vollständiger CQL-Syntax: Volltext, Titel, Autor, Schlagwort, ISBN/ISSN
- **OAI-PMH-Harvesting** mit Datums- und Sammlungsfilter sowie Pagination via Resumption Tokens
- **MARC21-Parser** mit 20+ Feldern (Titel, Autor, Erscheinungsinfo, Schlagworte, Abstract, URLs)
- **Dublin-Core-Parser** für alle drei Digitalportale
- **Dual Transport**: stdio (Claude Desktop) · Streamable HTTP (Cloud/Self-hosted)
- **OA-Rechtsliteratur-Suche** über sui generis, ex/ante und Repositorium.ch mit deklarativer Quellen-Registry (neue Quelle = eine Konfigurationszeile), best-effort Crossref-Lizenzanreicherung und Graceful Degradation pro Quelle
- **2 eingebaute Prompts**: `research-workflow` und `education-research`
- **Markdown- und JSON-Ausgabe** für alle Tools
- **50 Unit-Tests** (kein Netzwerk) + Live-Smoke-Tests

---

## Datenquellen

| Quelle | Protokoll | Inhalt | Einträge |
|--------|-----------|--------|----------|
| [swisscovery (SLSP)](https://swisscovery.slsp.ch) | SRU / MARC21 | 500+ Schweizer Bibliotheken | 10+ Mio. |
| [e-rara](https://www.e-rara.ch) | OAI-PMH / Dublin Core | Digitalisierte hist. Druckwerke | 250'000+ |
| [e-periodica](https://www.e-periodica.ch) | OAI-PMH / Dublin Core | Digitalisierte Zeitschriften (1750–heute) | 1 Mio.+ |
| [e-manuscripta](https://www.e-manuscripta.ch) | OAI-PMH / Dublin Core | Handschriften & Archivalien | 100'000+ |

### Open-Access-Rechtsliteratur (nur Metadaten)

| Quelle | Protokoll | Inhalt | DOI-Abdeckung |
|--------|-----------|--------|---------------|
| [sui generis](https://sui-generis.ch) | OAI-PMH / Dublin Core | OA-Rechtszeitschrift & Non-Profit-Verlag | ~100 % (`10.21257/…`) |
| [ex/ante](https://ex-ante.ch) | OAI-PMH / Dublin Core | Peer-reviewte Zeitschrift für (junge) Rechtswissenschaft, mehrsprachig | keine (persistente URL) |
| [Repositorium.ch](https://www.repositorium.ch) | Supabase / PostgREST (JSON) | Fachrepositorium zum Schweizer Recht | teilweise |

---

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
| `oa_law_search` | OA-Recht (alle 3) | OA-Rechtsbeiträge durchsuchen (Titel/Abstract/Autor) mit Filtern für Quelle, Sprache, Jahr, Peer-Review |
| `oa_law_get` | OA-Recht (alle 3) | Einzelbeitrag via DOI oder auflösbare URL |

### Beispiel-Abfragen

| Abfrage | Tool |
|---------|------|
| *«Welche Bücher über Volksschule gibt es in Schweizer Bibliotheken?»* | `swisscovery_search` |
| *«Zeige historische Druckwerke der ETH-Bibliothek»* | `erara_list_records` |
| *«Welche Zeitschriften wurden 2023 in e-periodica ergänzt?»* | `eperiodica_list_records` |
| *«Welche Handschriften-Sammlungen hat e-manuscripta?»* | `emanuscripta_list_collections` |
| *«Welche OA-Rechtsbeiträge gibt es zu Gesichtserkennung?»* | `oa_law_search` |

---

## Architektur

Zwei unabhängige Pfade teilen sich einen HTTP-Client (Retry mit exponentiellem Backoff, gemeinsamer Connection-Pool, Projekt-`User-Agent`):

```
                        ┌─────────────────────────────────────────────┐
                        │        swiss-academic-libraries-mcp          │
                        │        (FastMCP · stdio / HTTP)              │
                        └───────────────┬──────────────┬──────────────┘
                                        │              │
                ┌───── KATALOG-Pfad ────┘              └── OA-RECHT-Pfad ──────┐
                │  (api_client.py)                        (oa_legal.py)        │
                │                                                              │
      ┌─────────┴─────────┐                        ┌─────────────────────────┴──────────┐
      │ swisscovery  SRU  │                        │  deklarative Quellen-Registry        │
      │ e-rara       OAI  │                        │   ├─ sui generis   → OAI-PMH         │
      │ e-periodica  OAI  │                        │   ├─ ex/ante       → OAI-PMH         │
      │ e-manuscripta OAI │                        │   └─ Repositorium  → PostgREST/JSON  │
      └─────────┬─────────┘                        │  Harvest → In-Memory-Cache → Filter │
                │                                   │  Crossref DOI→Lizenz-Anreicherung ⟳  │
        MARC21 / Dublin Core                        │  (best-effort, OA_LAW_CROSSREF_ENRICH)│
        → Katalogeinträge                           └────────────────────┬────────────────┘
                                                       OaLegalPublication (nur Metadaten,
                                                       Lizenz nie leer, kein Volltext)
```

- **Katalog-Pfad** liefert bibliografische Einträge (Bücher, Digitalisate, Zeitschriften, Handschriften).
- **OA-Recht-Pfad** harvestet die OA-Rechtsliteratur-Metadaten einmalig, hält sie im Speicher (kleiner Bestand) und filtert lokal — denn OAI-PMH kennt keine eigene Volltextsuche. Eine vierte OA-Quelle ist ein einzelner Registry-Eintrag, kein neuer Code.

---

## Lizenzierung & Geltungsbereich

Der Server ist bewusst zurückhaltend bei dem, was er ausgibt — ein Portfolio, das Governance als Merkmal führt, kann sich hier keine Nachlässigkeit leisten.

- **Metadaten, kein Volltext.** Für OA-Rechtsliteratur liefert der Server **Titel, Autorschaft, Jahr, Lizenz, DOI/Link und — sofern die Quelle es als Metadatum ausliefert — den Abstract**. Der Aufsatz selbst wird nie ingestiert, gespeichert oder ausgegeben. Der Volltext-PDF-Pfad von Repositorium.ch wird bewusst in kein Feld übernommen.
- **`license` ist immer gesetzt.** Open Access heisst *frei lesbar*, **nicht** *frei weiterverwendbar*. Die Bandbreite reicht von CC0 über CC BY bis CC BY-NC-ND, manche Beiträge sind schlicht «kostenlos lesbar» ohne offene Lizenz. Fehlt eine maschinenlesbare Lizenz, steht dort `"unknown"` — nie geraten, nie weggelassen. Die native OAI-Metadatenschicht aller drei Quellen führt nur Copyright-Statements, also ist `"unknown"` der Normalfall; eine best-effort **Crossref**-Abfrage hebt ihn auf die echte CC-Lizenz an, wo ein DOI auflöst (z.B. sui generis → `CC BY-SA 4.0`). Abschaltbar mit `OA_LAW_CROSSREF_ENRICH=0`.
- **Zitierintegrität.** Jeder Treffer trägt eine auflösbare Referenz — einen DOI wo vorhanden, sonst eine persistente URL. Kein Treffer ohne. Eine erfundene Fundstelle in der Rechtsliteratur ist schädlicher als gar keine — lieber ein Treffer weniger als einer erfunden.
- **Sprache wird geführt, nie still gefiltert.** ex/ante und Repositorium.ch sind mehrsprachig (DE/FR/IT/EN). Das Feld `language` ist immer gesetzt, gefiltert wird aber nur auf ausdrücklichen Wunsch — sonst verschwände die halbe Romandie aus den Resultaten.
- **Abgrenzung.** OA-Rechtsliteratur gehört hierhin, weil es dieselbe *Fähigkeit* ist, die dieser Server schon hat — authentifizierungsfreies bibliografisches Metadaten-Harvesting Schweizer Wissenschaftsquellen über Standardprotokolle — mit demselben Output-Vertrag (Metadaten, kein Volltext). Sie ist institutionsunabhängig und fachbezogen und überschneidet daher nicht [`eth-library-mcp`](https://github.com/malkreide/eth-library-mcp) (ETH-Bibliothek Discovery & Persons).

---

## Bekannte Einschränkungen

- **Kleiner, fokussierter Bestand.** Die drei OA-Quellen umfassen zusammen einige hundert Beiträge. Themenkombinierende UND-Abfragen (z.B. *«Datenschutz Bildung»*) können berechtigt **null** Treffer liefern, während breitere Abfragen (*«Datenschutz»*) viele liefern — dieses leere Resultat ist die ehrliche Antwort, kein Fehler. Mit dem Kernbegriff suchen und danach eingrenzen.
- **Keine Volltextsuche.** Gesucht wird nur über Metadaten (Titel, Abstract, Autorschaft), nie im Aufsatzinhalt.
- **Ungleiche DOI-Abdeckung.** sui generis ≈ 100 %, Repositorium.ch teilweise, ex/ante hat **keine DOIs** (nur persistente URLs). Aggregatoren (Crossref/OpenAlex) decken daher sui generis gut ab, verfehlen ex/ante ganz und indexieren Repositorium.ch nicht als Quelle — deshalb harvestet der Server jede Quelle nativ statt auf einen Aggregator zu vertrauen.
- **Lizenzlücken.** Die native Metadatenschicht führt selten eine maschinenlesbare Lizenz; `"unknown"` ist häufig und wird nur dort angehoben, wo ein DOI in Crossref auflöst.
- **Kein Ersatz für eine kostenpflichtige juristische Datenbank.** Erschlossen wird ausschliesslich *frei zugängliche* Schweizer Rechtsliteratur — dies ist kein Swisslex/Weblaw und deckt kein kommerzielles oder kostenpflichtiges juristisches Publizieren ab.

---

## Voraussetzungen

- Python 3.11 oder höher
- [uv](https://docs.astral.sh/uv/) / uvx (empfohlen) oder pip
- Internetzugang (alle APIs sind öffentlich)

---

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
uvx swiss-academic-libraries-mcp --http --port 8000 [--host 127.0.0.1]
```

**Sicherheit & Deployment**

- **Default-Binding ist `127.0.0.1`** (nur loopback). Der Server hat
  keine eingebaute Authentifizierung.
- `--host 0.0.0.0` nur einsetzen, wenn der Server **hinter einem
  Reverse Proxy mit Authentifizierung und per-IP-Rate-Limit läuft**
  (z.B. nginx mit `limit_req` + OAuth2-Proxy). Non-Loopback-Bindings
  erzeugen eine WARN-Log-Zeile.
- Logs werden auf **stderr** geschrieben; Verbosity via
  `MCP_LOG_LEVEL=DEBUG|INFO|WARNING` steuerbar.

### Entwicklung

```bash
git clone https://github.com/malkreide/swiss-academic-libraries-mcp
cd swiss-academic-libraries-mcp
pip install -e .
```

---

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

→ [Weitere Anwendungsbeispiele nach Zielgruppe](EXAMPLES.md) →
```

> 💡 *«Kein API-Key — einfach installieren und loslegen.»*

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

---

## Konfiguration

Keine API-Keys oder Umgebungsvariablen erforderlich.

| Parameter | Standard | Beschreibung |
|-----------|----------|--------------|
| `--http` | aus | Streamable HTTP Transport aktivieren |
| `--port` | 8000 | Port für HTTP-Transport |

---

## Projektstruktur

```
swiss-academic-libraries-mcp/
├── src/
│   └── swiss_academic_libraries_mcp/
│       ├── __init__.py       # Package-Init
│       ├── server.py         # FastMCP-Server, 13 Tools, 2 Prompts, 2 Resources
│       ├── api_client.py     # HTTP-Client (+ Retry), MARC21- + OAI-PMH/DC-Parser
│       └── oa_legal.py       # OA-Rechtsliteratur: Registry, Adapter, Modell
├── tests/
│   ├── test_server.py        # Katalog-Unit-Tests + Live-Smoke-Tests
│   ├── test_20_scenarios.py  # End-to-End-Katalog-Szenarien
│   └── test_oa_legal.py      # OA-Rechtsliteratur-Tests (gemockt + live)
├── pyproject.toml
├── CHANGELOG.md
├── CONTRIBUTING.md            # Beitragsleitfaden (Englisch)
├── CONTRIBUTING.de.md         # Beitragsleitfaden (Deutsch)
├── SECURITY.md               # Sicherheitsrichtlinie (Englisch)
├── SECURITY.de.md            # Sicherheitsrichtlinie (Deutsch)
├── LICENSE
├── README.md                 # Englische Version
└── README.de.md              # Diese Datei
```

---

## Tests

```bash
# Unit-Tests (kein Netzwerk erforderlich)
PYTHONPATH=src pytest tests/ -m "not live"

# Live-Smoke-Tests (Internetzugang erforderlich)
PYTHONPATH=src pytest tests/ -m "live"
```

---

## Contributing

Beiträge sind willkommen! Lies bitte [CONTRIBUTING.de.md](CONTRIBUTING.de.md) für Hinweise zu:

- Fehler melden und Funktionen vorschlagen
- Entwicklungsumgebung einrichten
- Code-Stil und Test-Anforderungen
- Pull Requests einreichen

Dieses Projekt folgt den Konventionen des [Swiss Public Data MCP Portfolios](https://github.com/malkreide).

---

## Sicherheit

Um eine Schwachstelle zu melden, folgen Sie bitte dem Responsible-Disclosure-Prozess in [SECURITY.de.md](SECURITY.de.md). Der Server ist nur lesend und benötigt keinen API-Key; das Sicherheitsmodell ist in [SECURITY.de.md](SECURITY.de.md) beschrieben.

---

## Changelog

Siehe [CHANGELOG.md](CHANGELOG.md)

---

## Deployment für Schweizer Behörden

Beim Self-Hosting für Schulämter, Archive oder kommunale Anwendungen:

- **Datenresidenz:** Wenn möglich On-Premise oder bei einem CH-Cloud-
  Anbieter betreiben. Die Anfragen-Pattern (welche Bibliothekssuchen
  ein:e Sachbearbeiter:in durchführt) können Rückschlüsse auf
  laufende Recherchen erlauben und gehören auf Schweizer Infrastruktur.
- **Upstream-Calls** gehen ausschliesslich an CH-gehostete Dienste:
  SLSP / swisscovery, ETH-Bibliothek (e-rara, e-periodica,
  e-manuscripta). Es verlassen keine Daten die Schweiz.
- **Logging:** Logs werden auf stderr geschrieben; Aufbewahrungsdauer
  gemäss Behörden-IT-Richtlinie konfigurieren (z.B. systemd-journal
  `MaxRetentionSec`).
- **HTTP-Transport** muss hinter einem Reverse Proxy mit
  Authentifizierung und per-IP-Rate-Limit laufen (siehe *Sicherheit &
  Deployment* oben).

---

## Lizenz

MIT-Lizenz — siehe [LICENSE](LICENSE)

---

## Autor

Hayal Oezkan · [github.com/malkreide](https://github.com/malkreide)

---

## Credits & Verwandte Projekte

- **Daten (Katalog):** [swisscovery / SLSP](https://swisscovery.slsp.ch) · [e-rara](https://www.e-rara.ch) · [e-periodica](https://www.e-periodica.ch) · [e-manuscripta](https://www.e-manuscripta.ch)
- **Daten (OA-Rechtsliteratur):** [sui generis](https://sui-generis.ch) · [ex/ante](https://ex-ante.ch) · [Repositorium.ch](https://www.repositorium.ch) — Lizenzanreicherung via [Crossref](https://www.crossref.org). Die Metadaten jeder Quelle werden gemäss deren Bedingungen genutzt; Open-Access-Status bedeutet keine offene Weiterverwendungslizenz.
- **Protokoll:** [Model Context Protocol](https://modelcontextprotocol.io/) — Anthropic / Linux Foundation
- **Verwandt:** [eth-library-mcp](https://github.com/malkreide/eth-library-mcp) — ETH-Bibliothek Discovery & Persons API
- **Portfolio:** [Swiss Public Data MCP Portfolio](https://github.com/malkreide)

| Server | Beschreibung |
|--------|--------------|
| [`zurich-opendata-mcp`](https://github.com/malkreide/zurich-opendata-mcp) | Stadt Zürich Open Data |
| [`eth-library-mcp`](https://github.com/malkreide/eth-library-mcp) | ETH-Bibliothek Discovery & Persons API |
| [`swiss-statistics-mcp`](https://github.com/malkreide/swiss-statistics-mcp) | BFS STAT-TAB (Schweizer Statistik) |
| [`fedlex-mcp`](https://github.com/malkreide/fedlex-mcp) | Bundesrecht via Fedlex SPARQL |
| [`swiss-transport-mcp`](https://github.com/malkreide/swiss-transport-mcp) | OJP Reiseplanung, SIRI-SX Störungen |
