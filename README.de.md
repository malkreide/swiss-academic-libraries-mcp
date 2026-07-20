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

Zusätzlich kommt die **internationale Metadatenebene** dazu: DOI-Auflösung und internationale Forschungsliteratur via [Crossref](https://www.crossref.org), Preprints via [arXiv](https://arxiv.org). So beantwortet dieselbe Konversation sowohl «gibt es das in der Schweiz?» (nationale Ebene) als auch «was ist das überhaupt und wo steht es sonst?» (internationale Ebene). Jede aufgelöste DOI liefert Titel, ISSN, ISBN und Autor:innen als saubere Top-Level-Felder — direkt weitersuchbar in swisscovery.

**Anker-Demo-Abfrage (national ↔ international):** *«Finde die Originalpublikation zu dieser DOI, prüfe ob eine Preprint-Version existiert, und zeige ob eine Schweizer Bibliothek sie führt.»* → `resolve_doi` → `search_preprints` → `swisscovery_search(query="<ISSN aus resolve_doi>")`.

**Anker-Demo-Abfrage (Katalog):** *«Welche Schweizer Hochschul-Dissertationen zur Primarschulpädagogik sind in Schweizer Bibliotheken vorhanden – und sind einige davon in e-rara digitalisiert?»*

**Anker-Demo-Abfrage (OA-Rechtsliteratur):** *«Welche frei zugänglichen rechtswissenschaftlichen Beiträge gibt es zu Datenschutz im Bildungsbereich? Gib mir Titel, Autorschaft, Jahr, Lizenz und DOI.»* → `oa_law_search(query="Datenschutz im Bildungsbereich")` — Ergebnisse werden nach Relevanz sortiert: Beiträge, die alle Begriffe treffen, stehen oben, Teiltreffer (nur der Kernbegriff «Datenschutz») folgen. So liefert die Abfrage den echten Datenschutz-Bestand statt einer leeren Menge.

---

## Funktionen

- **16 Tools** für 4 Katalogquellen + 3 OA-Rechtsliteratur-Quellen + 2 internationale Metadatenquellen — alle nur lesend, kein API-Key
- **swisscovery-Suche** mit vollständiger CQL-Syntax: Volltext, Titel, Autor, Schlagwort, ISBN/ISSN
- **OAI-PMH-Harvesting** mit Datums- und Sammlungsfilter sowie Pagination via Resumption Tokens
- **MARC21-Parser** mit 20+ Feldern (Titel, Autor, Erscheinungsinfo, Schlagworte, Abstract, URLs)
- **Dublin-Core-Parser** für alle drei Digitalportale
- **Dual Transport**: stdio (Claude Desktop) · Streamable HTTP (Cloud/Self-hosted)
- **OA-Rechtsliteratur-Suche** über sui generis, ex/ante und Repositorium.ch mit deklarativer Quellen-Registry (neue Quelle = eine Konfigurationszeile), best-effort Crossref-Lizenzanreicherung und Graceful Degradation pro Quelle
- **Internationale Metadatenebene**: DOI-Auflösung und bibliografische Suche via Crossref (polite pool via `CROSSREF_MAILTO`), Preprint-Suche via arXiv mit automatischer Phrasen-Quotierung und Request-Throttling — saubere Titel-/ISSN-/ISBN-/Autor:innen-Felder zur Weitersuche in swisscovery
- **3 eingebaute Prompts**: `research-workflow`, `education-research` und `doi-to-swiss-shelf`
- **Markdown- und JSON-Ausgabe** für alle Tools
- **97 Unit-/Mock-Tests** (kein Netzwerk) + 30 Live-Smoke-Tests

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

### Internationale Metadatenebene (nur Metadaten)

| Quelle | Protokoll | Inhalt | Lizenz |
|--------|-----------|--------|--------|
| [Crossref](https://www.crossref.org) | REST / JSON | DOI-Auflösung + internationale Forschungsliteratur | Metadaten CC0 1.0 (gemeinfrei) |
| [arXiv](https://arxiv.org) | Atom / XML | Preprints (Informatik, Physik, Mathematik, Statistik …) | Metadaten CC0 1.0; Preprints je Autor:innen-Lizenz |

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
| `resolve_doi` | Crossref | DOI zu vollständigen Metadaten auflösen (Titel/ISSN/ISBN/Autor:innen → Weitersuche in swisscovery) |
| `search_publications` | Crossref | Internationale Forschungsliteratur durchsuchen; jeder Treffer trägt eine DOI |
| `search_preprints` | arXiv | Preprints durchsuchen, mit automatischer Phrasen-Quotierung; verknüpfte Journal-DOIs führen zu `resolve_doi` |

### Beispiel-Abfragen

| Abfrage | Tool |
|---------|------|
| *«Welche Bücher über Volksschule gibt es in Schweizer Bibliotheken?»* | `swisscovery_search` |
| *«Zeige historische Druckwerke der ETH-Bibliothek»* | `erara_list_records` |
| *«Welche Zeitschriften wurden 2023 in e-periodica ergänzt?»* | `eperiodica_list_records` |
| *«Welche Handschriften-Sammlungen hat e-manuscripta?»* | `emanuscripta_list_collections` |
| *«Welche OA-Rechtsbeiträge gibt es zu Gesichtserkennung?»* | `oa_law_search` |
| *«Löse DOI 10.1038/nature14539 auf und gib mir die ISSN»* | `resolve_doi` |
| *«Finde aktuelle Preprints zu model context protocol»* | `search_preprints` |
| *«Finde die DOI dieses Papers, prüfe auf Preprint, und ob eine CH-Bibliothek es führt»* | `resolve_doi` → `search_preprints` → `swisscovery_search` |

---

## Architektur

Drei unabhängige Pfade teilen sich einen HTTP-Client (Retry mit exponentiellem Backoff, gemeinsamer Connection-Pool, Projekt-`User-Agent`):

```
                    ┌──────────────────────────────────────────────────────┐
                    │            swiss-academic-libraries-mcp               │
                    │            (FastMCP · stdio / HTTP)                   │
                    └────────┬───────────────┬────────────────┬────────────┘
                             │               │                │
          ┌── KATALOG ───────┘   ┌── OA-RECHT ┘     ┌── INTERNATIONAL ──┐
          │   (api_client.py)    │   (oa_legal.py)  │  (intl_metadata.py)│
          │                      │                  │                    │
 ┌────────┴────────┐   ┌─────────┴──────────┐   ┌───┴──────────────────┐ │
 │ swisscovery SRU │   │ Quellen-Registry    │   │ Crossref  REST/JSON  │ │
 │ e-rara      OAI │   │  ├ sui generis  OAI │   │  ├ resolve_doi        │ │
 │ e-periodica OAI │   │  ├ ex/ante      OAI │   │  └ search_publications│ │
 │ e-manuscripta   │   │  └ Repositorium REST│   │ arXiv     Atom/XML   │ │
 └────────┬────────┘   │ Harvest→Cache→Filter│   │  └ search_preprints   │ │
          │            │ Crossref-Lizenz ⟳   │   │ (Phrasen-Quote+Throttle)│
 MARC21 / Dublin Core  └─────────┬──────────┘   └───┬──────────────────┘ │
 → Katalogeinträge     OaLegalPublication         CrossrefWork / Preprint │
                       (nur Metadaten, kein Volltext) (Metadaten, kein Volltext)│
```

- **Katalog-Pfad** liefert bibliografische Einträge (Bücher, Digitalisate, Zeitschriften, Handschriften).
- **OA-Recht-Pfad** harvestet die OA-Rechtsliteratur-Metadaten einmalig, hält sie im Speicher (kleiner Bestand) und filtert lokal — denn OAI-PMH kennt keine eigene Volltextsuche. Eine vierte OA-Quelle ist ein einzelner Registry-Eintrag, kein neuer Code.
- **Internationaler Pfad** löst DOIs auf und durchsucht Crossref/arXiv live (Architektur A — die Endpoints sind klein, stabil und öffentlich, also kein Dump/Cache nötig). Jede Antwort trägt ihre **eigene Quellen-Attribution** (Crossref CC0 · arXiv-Danksagung), nie eine gesammelte, und liefert saubere Top-Level-Felder (Titel/ISSN/ISBN/Autor:innen) zur Weitersuche im Katalog-Pfad. Eine Egress-Allow-List im Code beschränkt ausgehende Aufrufe auf `api.crossref.org` und `export.arxiv.org`.

---

## Lizenzierung & Geltungsbereich

Der Server ist bewusst zurückhaltend bei dem, was er ausgibt — ein Portfolio, das Governance als Merkmal führt, kann sich hier keine Nachlässigkeit leisten.

- **Metadaten, kein Volltext.** Für OA-Rechtsliteratur liefert der Server **Titel, Autorschaft, Jahr, Lizenz, DOI/Link und — sofern die Quelle es als Metadatum ausliefert — den Abstract**. Der Aufsatz selbst wird nie ingestiert, gespeichert oder ausgegeben. Der Volltext-PDF-Pfad von Repositorium.ch wird bewusst in kein Feld übernommen.
- **`license` ist immer gesetzt.** Open Access heisst *frei lesbar*, **nicht** *frei weiterverwendbar*. Die Bandbreite reicht von CC0 über CC BY bis CC BY-NC-ND, manche Beiträge sind schlicht «kostenlos lesbar» ohne offene Lizenz. Fehlt eine maschinenlesbare Lizenz, steht dort `"unknown"` — nie geraten, nie weggelassen. Die native OAI-Metadatenschicht aller drei Quellen führt nur Copyright-Statements, also ist `"unknown"` der Normalfall; eine best-effort **Crossref**-Abfrage hebt ihn auf die echte CC-Lizenz an, wo ein DOI auflöst (z.B. sui generis → `CC BY-SA 4.0`). Abschaltbar mit `OA_LAW_CROSSREF_ENRICH=0`.
- **Zitierintegrität.** Jeder Treffer trägt eine auflösbare Referenz — einen DOI wo vorhanden, sonst eine persistente URL. Kein Treffer ohne. Eine erfundene Fundstelle in der Rechtsliteratur ist schädlicher als gar keine — lieber ein Treffer weniger als einer erfunden.
- **Sprache wird geführt, nie still gefiltert.** ex/ante und Repositorium.ch sind mehrsprachig (DE/FR/IT/EN). Das Feld `language` ist immer gesetzt, gefiltert wird aber nur auf ausdrücklichen Wunsch — sonst verschwände die halbe Romandie aus den Resultaten.
- **Attribution pro Quelle, nicht gesammelt.** Crossref, arXiv und die OA-Rechtsquellen haben unterschiedliche Lizenz- und Nennungsbedingungen, deshalb trägt jede Antwort die Attribution genau der Quelle, aus der sie stammt. Crossref-Metadaten stehen unter **CC0 1.0** (Fakten sind frei); arXiv-Metadaten unter **CC0 1.0** mit der erbetenen Danksagung *«Thank you to arXiv for use of its open access interoperability»*; Preprint- und Aufsatz-Volltexte bleiben unter ihrer je eigenen Lizenz (hier nie ausgegeben).
- **Abgrenzung.** OA-Rechtsliteratur gehört hierhin, weil es dieselbe *Fähigkeit* ist, die dieser Server schon hat — authentifizierungsfreies bibliografisches Metadaten-Harvesting Schweizer Wissenschaftsquellen über Standardprotokolle — mit demselben Output-Vertrag (Metadaten, kein Volltext). Sie ist institutionsunabhängig und fachbezogen und überschneidet daher nicht [`eth-library-mcp`](https://github.com/malkreide/eth-library-mcp) (ETH-Bibliothek Discovery & Persons).

---

## Bekannte Einschränkungen

- **Kleiner, fokussierter Bestand.** Die drei OA-Quellen umfassen zusammen einige hundert Beiträge. Ergebnisse werden nach Relevanz sortiert — Beiträge, die alle Begriffe treffen, zuerst, danach Teiltreffer — sodass eine themenkombinierende Abfrage wie *«Datenschutz im Bildungsbereich»* den (nach Relevanz sortierten) Datenschutz-Bestand liefert statt nichts; deckt kein Beitrag die volle Themenschnittmenge ab, werden die nächstliegenden echten Treffer geliefert, nie ein erfundener. Eine Abfrage, die keinen einzigen Begriff trifft, liefert weiterhin ein ehrliches Leerresultat.
- **Keine Volltextsuche.** Gesucht wird nur über Metadaten (Titel, Abstract, Autorschaft), nie im Aufsatzinhalt.
- **Ungleiche DOI-Abdeckung.** sui generis ≈ 100 %, Repositorium.ch teilweise, ex/ante hat **keine DOIs** (nur persistente URLs). Aggregatoren (Crossref/OpenAlex) decken daher sui generis gut ab, verfehlen ex/ante ganz und indexieren Repositorium.ch nicht als Quelle — deshalb harvestet der Server jede Quelle nativ statt auf einen Aggregator zu vertrauen.
- **Lizenzlücken.** Die native Metadatenschicht führt selten eine maschinenlesbare Lizenz; `"unknown"` ist häufig und wird nur dort angehoben, wo ein DOI in Crossref auflöst.
- **Kein Ersatz für eine kostenpflichtige juristische Datenbank.** Erschlossen wird ausschliesslich *frei zugängliche* Schweizer Rechtsliteratur — dies ist kein Swisslex/Weblaw und deckt kein kommerzielles oder kostenpflichtiges juristisches Publizieren ab.

### Known findings — internationale Ebene (Live-Probe 2026-07-20)

| Befund | Detail | Konsequenz |
|---|---|---|
| **Crossref schwach bei deutschsprachiger CH-Bildungsliteratur** | `query.bibliographic=Lehrplan 21` liefert als Top-Treffer ein **Buchkapitel von 1881**; weitere CH-Bildungs-Abfragen ergeben Millionen irrelevanter Treffer mit alten/abseitigen Spitzen. Crossref ist stark bei DOI-Auflösung und internationaler Forschung, nicht bei CH-Bildungspublikationen. | `search_publications` dokumentiert das und verweist für CH-Bildungsthemen auf `swisscovery_search` / `oa_law_search`. |
| **arXiv interpretiert Leerzeichen als OR, nicht als Phrase** | `all:model context protocol` → ~1'296'686 Treffer (OR); `all:"model context protocol"` → 462 Treffer (Phrase). | `search_preprints` quotiert automatisch; Nutzende brauchen keine arXiv-Syntax. Feld-Syntax (`ti:`, `au:`) und eigene Anführungszeichen werden respektiert. |
| **arXiv liefert Atom-XML, throttlet und leitet `http`→`https` um (301)** | Antwort ist Atom, kein JSON; arXiv bittet um ~3 s zwischen Requests; der `http://`-Endpoint leitet per 301 um. | Parser nutzt `defusedxml` (bereits Dependency — keine neue); ein modulweiter Throttle (`ARXIV_MIN_INTERVAL_SECONDS`, Default 3 s) hält den Abstand; der Client ruft direkt den `https://`-Endpoint. |
| **SHARE (share.osf.io) — geprüft, nicht gebaut** | Der `_search`-Endpoint antwortet (≈58,9 Mio. Records, Elasticsearch-artig), **aber** SHARE hat das Harvesting 2020 heruntergefahren, die Datenbank in CurateND archiviert und führt keine API-Wartungszusage («shutting down / new phase», heute «trove»-Search-API). Für ein auf Verlässlichkeit positioniertes Portfolio ist ein Index ohne Support-Zusage ein schlechter Abhängigkeitskandidat. | **Nicht implementiert.** |
| **Open Library — geprüft, Gate durchgefallen** | Eine 10-ISBN-Probe realer CH-/deutschsprachiger Lehrmittel (Lehrmittelverlag Zürich, Klett und Balmer; ISBNs aus swisscovery geharvestet) ergab **0/10 = 0 %** (Schwelle 60 %). Kontrollen bestätigen, dass Open Library funktioniert (englische + deutschsprachige Trade-Titel lösen auf) — also eine echte Abdeckungslücke, kein Netz-Artefakt. | **Nicht implementiert.** swisscovery deckt CH-Lehrmittel bereits ab; für den Buchhandel wäre GVI oder ein Verlagsverzeichnis der passende Weg. |

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

Kein API-Key erforderlich. Alle Umgebungsvariablen sind optional.

| Parameter | Standard | Beschreibung |
|-----------|----------|--------------|
| `--http` | aus | Streamable HTTP Transport aktivieren |
| `--port` | 8000 | Port für HTTP-Transport |
| `MCP_LOG_LEVEL` | `INFO` | Log-Verbosität (`DEBUG`/`INFO`/`WARNING`) |
| `OA_LAW_CROSSREF_ENRICH` | `1` | OA-Recht: DOI→Lizenz-Anreicherung via Crossref; `0` deaktiviert sie |
| `OA_LAW_REPOSITORIUM_ANON_KEY` | *(öffentl. Key)* | OA-Recht: Override für den öffentlichen, read-only Supabase-Anon-Key von Repositorium.ch (Rotation ohne Code-Änderung) |
| `CROSSREF_MAILTO` | *(nicht gesetzt)* | International: Kontakt-E-Mail für Crossrefs «polite pool» (besserer Durchsatz). Fehlt sie, läuft die Abfrage im anonymen Pool — funktionsfähig, nur langsamer. |
| `ARXIV_MIN_INTERVAL_SECONDS` | `3.0` | International: Mindestabstand zwischen arXiv-Requests (arXiv bittet um Zurückhaltung). |

---

## Projektstruktur

```
swiss-academic-libraries-mcp/
├── src/
│   └── swiss_academic_libraries_mcp/
│       ├── __init__.py       # Package-Init
│       ├── server.py         # FastMCP-Server, 16 Tools, 3 Prompts, 3 Resources
│       ├── api_client.py     # HTTP-Client (+ Retry), MARC21- + OAI-PMH/DC-Parser
│       ├── oa_legal.py       # OA-Rechtsliteratur: Registry, Adapter, Modell
│       └── intl_metadata.py  # Internationale Ebene: Crossref- + arXiv-Adapter, Modelle
├── tests/
│   ├── test_server.py        # Katalog-Unit-Tests + Live-Smoke-Tests
│   ├── test_20_scenarios.py  # End-to-End-Katalog-Szenarien
│   ├── test_oa_legal.py      # OA-Rechtsliteratur-Tests (gemockt + live)
│   └── test_intl_metadata.py # Tests der internationalen Ebene (gemockt + live)
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
