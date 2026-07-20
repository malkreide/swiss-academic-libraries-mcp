# Live-Probe: Internationale Metadatenebene (Crossref, arXiv, SHARE, Open Library)

> **Phase 1 — Live-Probe** nach Skill `mcp-data-source-probe`, Schritt 1.
> Durchgeführt am **2026-07-20** (Vorbefunde vom 2026-07-19 nachgeprüft). Alle
> Befunde sind empirisch mit `curl` gegen die Live-Endpoints erhoben.
> *«Dokumentation ist ein Foto, Live-Probe ist der aktuelle Zustand.»*

Entscheidungsgrundlage für die Erweiterung um die internationale Metadatenebene.
Ergebnis: **Tool-Extension (kein neuer Server), 3 Tools gebaut, 2 Quellen per
Gate abgelehnt.**

---

## 0. Zusammenfassung (TL;DR)

| Quelle | Nutzbar? | Entscheid | Tool |
|---|---|---|---|
| **Crossref** | ✅ DOI-Auflösung + Suche stabil | **bauen** | `resolve_doi`, `search_publications` |
| **arXiv** | ✅ stabil (zwei Fallen entschärft) | **bauen** | `search_preprints` |
| **SHARE** | ⚠️ erreichbar, aber ohne Support-Zusage | **nicht bauen** | — |
| **Open Library** | ❌ 0 % CH-Lehrmittel-Abdeckung | **nicht bauen** (Gate) | — |
| **Gutendex** | – nur gemeinfreie PG-Titel | **weggelassen** | — |

Architektur-Entscheid: **A (Live-API-only)** — Crossref und arXiv sind klein,
stabil und öffentlich; kein Dump/Cache-Zwang. Retry/Backoff (2s/4s/8s),
Egress-Allow-List und Provenance/Attribution-Envelope wie im OA-Recht-Pfad.

---

## 1. Crossref — grünes Licht

| Endpoint | HTTP | Status | Bemerkung |
|---|---|---|---|
| `GET /works/{doi}` | 200 | ✅ | Voll-Metadaten: `title`, `author[]`, `ISSN`, `ISBN`, `type`, `license[]`, `abstract` |
| `GET /works?query.bibliographic=…&rows=&select=` | 200 | ✅ | Feld-Selektion + `total-results` + `items[]` |
| polite pool (`mailto:` in UA/Query) | 200 | ✅ | konfigurierbar via `CROSSREF_MAILTO`; ohne → anonymer Pool (funktionsfähig, langsamer) |

**Known finding — DE-Bildungsrelevanz schwach (bestätigt):**

| Abfrage | total | Top-Treffer |
|---|---|---|
| `Lehrplan 21` | 2'847'915 | «Der Lehrplan», **book-chapter, 1881** |
| `Sprachstarken Deutsch Volksschule` | 70'488 | «Für die allgemeine Volksschule», 1918 |
| `Kompetenzorientierung Volksschule Schweiz` | 44'682 | book-chapter, 2016 |

→ Crossref ist stark bei DOI-Auflösung und internationaler Forschung, schwach
bei CH-Bildungspublikationen. Für CH-Bildung: `swisscovery_search`/`oa_law_search`.

**Lizenz:** Crossref-Metadaten sind gemeinfrei (**CC0 1.0**, «facts are free»).
Nennung ist Best Practice, keine Pflicht.

---

## 2. arXiv — grünes Licht, zwei Fallen entschärft

| Endpoint | HTTP | Status | Bemerkung |
|---|---|---|---|
| `GET /api/query?search_query=…&max_results=` | 200 | ✅ | Antwort ist **Atom-XML** |

- **Falle 1 — Atom-XML, kein JSON:** Parser via `defusedxml` (bereits Dependency,
  keine neue eingeführt). Felder sauber parsebar: `id`→arXiv-ID, `title`,
  `author/name`, `published`, `primary_category`, `link[title=pdf]`, `arxiv:doi`.
- **Falle 2 — Phrasen-Syntax:** `all:model context protocol` = **1'296'686**
  Treffer (OR), `all:"model context protocol"` = **462** (Phrase). →
  `build_arxiv_query` quotiert automatisch; Feld-Syntax/eigene Quotes bleiben.
- **Rate Limit:** ~3 s Zurückhaltung dokumentiert → modulweiter Throttle
  (`ARXIV_MIN_INTERVAL_SECONDS`, Default 3 s).
- **Fundstück:** `http://export.arxiv.org` leitet per **301** auf `https://` um;
  der geteilte httpx-Client folgt Redirects bewusst nicht → HTTPS direkt.

**Lizenz:** arXiv-Metadaten **CC0 1.0**; erbetene Danksagung *«Thank you to arXiv
for use of its open access interoperability»*. Preprint-Volltexte je Lizenz.

---

## 3. SHARE — geprüft, nicht gebaut

| Endpoint | HTTP | Status | Bemerkung |
|---|---|---|---|
| `POST /api/v2/search/creativeworks/_search` | 200 | ⚠️ | erreichbar, **58'888'883** Records, ES-artige Struktur |

**Status-Recherche:** SHARE hat das Harvesting **2020 heruntergefahren**, die
Datenbank in CurateND (Univ. Notre Dame) archiviert, keine Zusage zur Wartung der
Such-API («SHARE Database Shutting Down While SHARE Services Enter New Phase»,
ARL); heute läuft unter share.osf.io die «trove»-Search-API.

→ Ein 58-Mio-Record-Index ohne Vertrags-/Wartungszusage ist für ein auf
Verlässlichkeit positioniertes Portfolio ein schlechter Abhängigkeitskandidat.
Regel «wenn der Status unklar bleibt, bau es nicht» greift. **Nicht implementiert.**

---

## 4. Open Library — Entscheidungs-Gate, durchgefallen

**Test:** 10 reale CH-/deutschsprachige Lehrmittel-ISBNs (Lehrmittelverlag
Zürich / LMVZ, Klett und Balmer), **aus swisscovery geharvestet** (also
garantiert real und katalogisiert), gegen beide OL-Endpoints
(`/isbn/{isbn}.json` und `/api/books?bibkeys=`).

| Ergebnis | Wert |
|---|---|
| Trefferquote | **0 / 10 = 0 %** |
| Schwelle | 60 % |
| Kontrolle EN (`9780140328721`, Fantastic Mr. Fox) | ✅ 200 |
| Kontrolle DE-Trade (`9783518368527`, Suhrkamp) | ✅ 200 |
| Task-Beispiel-CH-ISBN (`9783906744940`) | `{}` |

→ Open Library funktioniert grundsätzlich (EN + Mainstream-DE lösen auf), aber
Schweizer Lehrmittel fehlen praktisch vollständig. Echte Abdeckungslücke, kein
Netz-Artefakt. **Gate < 60 % → nicht implementiert.**

**Alternativen:** swisscovery deckt CH-Lehrmittel bereits ab (die Test-ISBNs
stammen daher); für den Buchhandel wäre GVI oder ein Verlagsverzeichnis der
passendere Weg.

---

## 5. Gutendex — weggelassen

Liefert ausschliesslich gemeinfreie Project-Gutenberg-Titel. Der einzige
plausible Schulamt-Use-Case (gemeinfreie deutschsprachige Literatur für den
Deutschunterricht) ist durch e-rara/swisscovery bereits abgedeckt; PG ist im
Deutschen dünn. **Nicht gebaut.**

---

## 6. Resultierender Build-Umfang

**3 neue Tools → 16 Tools total** (unter dem Portfolio-Cap von 20):

1. `resolve_doi(doi)` — Crossref, mit Titel/ISSN/ISBN/Autor:innen als
   Top-Level-Feldern für die swisscovery-Verkettung.
2. `search_publications(query, year_from, year_to, limit)` — Crossref.
3. `search_preprints(query, category, limit)` — arXiv, Phrasen-Quotierung + Throttle.

Anker-Abfrage (national ↔ international): *«Finde die Originalpublikation zu
dieser DOI, prüfe ob eine Preprint-Version existiert, und zeige ob eine Schweizer
Bibliothek sie führt.»*
