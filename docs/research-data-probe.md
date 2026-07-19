# Live-Probe: Forschungsdaten-Quellen (SNF & FORS SWISSUbase)

> **Phase 1 — Live-Probe** nach Skill `mcp-data-source-probe`, Schritt 1.
> Durchgeführt am **2026-07-19**. Alle Befunde sind empirisch mit `curl`
> gegen die Live-Endpoints erhoben — nicht aus der Dokumentation abgeleitet.
> *«Dokumentation ist ein Foto, Live-Probe ist der aktuelle Zustand.»*

Dieses Dokument ist die Entscheidungsgrundlage für Phase 2 (Implementierung).
Es trifft **noch keine** Code-Änderungen an den Tools.

---

## 0. Zusammenfassung (TL;DR)

| Quelle | Nutzbare API? | Dump? | Architektur-Empfehlung |
|---|---|---|---|
| **SNF** (data.snf.ch) | Teilweise: Einzel-Grant-Lookup ✅, **keine** brauchbare Such-API ❌ | Ja, CSV 61 MB – **408 MB** | **Architektur B** (Dump-first, API-Fallback) |
| **FORS SWISSUbase** | Ja: öffentliche Katalog-**Metadaten**-Suche ✅ | Nein (öffentlich) | **Architektur A** (Live-API-only) für Metadaten; Daten gated |

Zwei Kernbefunde prägen das Design:

1. **SNF:** Die Volltext-/Facetten-Suche der Website ist **nicht** über eine
   nutzbare API abrufbar (`/api/grants/search` ignoriert die Query). Abstracts
   fehlen komplett in der Live-API und existieren **nur** im CSV-Dump. → Suche
   muss über einen **lokal indexierten Dump** laufen.
2. **FORS:** Metadaten (Titel, Abstract, Datensatz-Liste inkl.
   `licenseAccessLevel`) sind **frei** über `POST /api/v2/catalogue/search`
   abrufbar. Die eigentlichen Forschungsdaten sind hinter 403/Registrierung.
   → Saubere Trennung **«auffindbar» (frei)** vs. **«abrufbar» (gated)**.

---

## 1. SNF — data.snf.ch

**Homepage-Behauptung (Reality-Check):** Der Elasticsearch-Index meldet
`total = 91 005` Grants. Die CSV-Dumps decken denselben Bestand ab
(Applications ab Grant-Nr. 1, Reporting-Jahre ab 1975). Zahlen konsistent.

**Lizenz:** **CC BY-SA 4.0** (ausgewiesen auf `data.snf.ch/datasets`).
→ Attribution **und** Share-Alike-Pflicht. Muss in jede Response (Skill 3.2).
`opendata.swiss` liefert im CKAN-`license_id` keinen Wert — die verbindliche
Angabe ist die Portal-Fussnote CC BY-SA 4.0.

### 1.1 Endpoint-Matrix (Live-API `https://data.snf.ch/api`)

| Endpoint | Methode | HTTP | Status | Bemerkung |
|---|---|---|---|---|
| `/grants/grant/{applicationId}` | GET | 200 | ✅ funktioniert | Voll-Record, **40+ Felder** (Titel, Betrag, Laufzeit, Disziplin, Förderinstrument, Institution, Applicants) |
| `/grants/grant/99999999` | GET | 404 | ✅ sauberer Fehler | `{"statusMessage":"Application not found"}` |
| `/grants/filters` | GET | 200 | ✅ funktioniert | **1,7 MB** Facetten-Definitionen (Förderinstrumente, Disziplinen, Institutionen, States, Calls) |
| `/grants/person-from-numbers?numbers=` | GET | 200 | ✅ funktioniert | Namen zu Personen-Nummern |
| `/grants/search` | POST | 200 | ⚠️ **unbrauchbar** | Ignoriert `query`, `size`, `from`, `search_after`; nur `sort` + `_source` wirken. Gibt fixe 10 Records aus 91 005 zurück |
| `/grants/search` | GET | 405 | ✅ erwartbar | Method Not Allowed (POST-only) |
| `/api/datasets` (SPA-Root) | GET | 404 | – | keine generische Dataset-API |

> **Fundstück (für CHANGELOG «Known findings»):** `POST /api/grants/search` ist
> ein *ES-Passthrough mit Maulkorb* — es akzeptiert nur `sort`/`_source` und
> ignoriert jede Query. `total` ist konstant 91 005 (voller Index), egal was im
> Body steht. Wer darauf eine Suche baut, sucht im Nebel. Deshalb Dump.

**Wichtig — Abstract-Lücke:** Der Grant-Record der Live-API enthält **kein**
Abstract-/Summary-Feld (empirisch bestätigt). Abstracts + Lay-Summaries
(DE/EN/FR/IT) existieren **ausschliesslich** im Dump `grants_with_abstracts.csv`
(Spalten `Abstract`, `LaySummary_De/En/Fr/It`, …). Da der Task explizit Abstracts
verlangt, ist der Dump nicht optional, sondern notwendig.

### 1.2 Dump-Verfügbarkeit (`https://data.snf.ch/datasets/…`)

Quelle der URLs: `opendata.swiss` Paket `snsf-data-portal-exports` (14 Ressourcen).
Format: **CSV, `;`-getrennt, UTF-8 mit BOM.**

| Datei | Grösse | Inhalt | Abstracts? |
|---|---|---|---|
| `grants.csv` | **61,2 MB** | Projekte (Titel, Förderinstrument, Institut, Disziplin, Betrag, Laufzeit) | nein |
| `grants_with_abstracts.csv` | **407,6 MB** ⚠️ | wie oben **+ wissenschaftl. Abstracts + Lay-Summaries** | ja |
| `persons.csv` | 45,1 MB | Personen (Name, Institut, ORCID, Grant-Rollen) | – |
| `output_data_scientific_publications.csv` | 232,3 MB | Publikations-Output | – |
| `output_data_datasets.csv` | (klein) | Output-Datensätze | – |
| `SNF_field_of_research_disciplines.csv` | klein | Disziplinen-Mapping | – |
| + 8 weitere Output-CSVs, `NCCR_data.csv.zip` | | | |

Download-URLs sind **stabil** (versionslos, gleicher Pfad seit Portal-Migration).
Update-Frequenz: laufend/wöchentlich (Reporting-Jahre fortlaufend ergänzt).

### 1.3 Architektur-Entscheid SNF → **B (Hybrid: Dump-first, API-Fallback)**

Begründung (live verifiziert 2026-07-19):
- Volltext-/Facetten-Suche ist server-seitig **nicht** verfügbar → Suche über
  lokal indexierten Dump.
- Abstracts existieren nur im Dump → `grants_with_abstracts.csv` ist die
  Abstract-Quelle.
- Einzel-Projekt-Detail live über `/api/grants/grant/{id}` (frisch, reich, klein)
  als **API-Fallback** und für tagesaktuelle Einzelabfragen.

**Caching-Strategie (Dumps NICHT in den Request-Pfad laden):**
- **Out-of-band Ingest:** Dump wird ausserhalb des Request-Zyklus geladen
  (Startup-Task / Cron), nach `~/.cache/…` geschrieben und in eine **SQLite-DB
  mit FTS5-Volltextindex** überführt. Kein CSV-Parsing pro Anfrage.
- **Default-Index `grants.csv` (61 MB)** — schlank, deckt Titel/Institution/
  Disziplin/Betrag/Laufzeit ab. **`grants_with_abstracts.csv` (408 MB)** nur
  **opt-in** (Env-Flag), da RAM/Disk/Download-Kosten erheblich.
- **TTL-Refresh** wöchentlich; `Last-Modified`/Grössen-Vergleich vor Re-Download.
- **Streaming-Download + Retry** (Skill 3.1): 408-MB-Files brauchen Resume-
  fähiges, gebackoff-tes Laden; wöchentliche Exporte sind während der Generierung
  häufig 503.
- **`dump_status()`-Tool** (Skill 3.5): meldet Cache-Alter, letzter erfolgreicher
  Sync, ob Abstract-Index aktiv — nie stumm leere Records.

---

## 2. FORS — SWISSUbase (`www.swissubase.ch`)

Angular-SPA; Backend-API unter `/api/v2`. Katalog `total = 12 526` Studien
(sozialwissenschaftliche Schwerpunkte, mehrsprachige Metadaten).

**Lizenz Metadaten:** DDI-basierte Metadaten, öffentlich einsehbar. Verbindliche
Lizenz-/Attributionsangabe für die Metadaten ist **vor Release zu bestätigen**
(FORS/SWISSUbase-Nutzungsbedingungen; Metadaten üblicherweise offen, Daten
lizenzpflichtig).

### 2.1 Endpoint-Matrix (`https://www.swissubase.ch/api/v2`)

| Endpoint | Methode | HTTP | Status | Bemerkung |
|---|---|---|---|---|
| `/catalogue/search` | POST `{}` | 200 | ✅ **öffentlich** | `{total:12526, items:[…]}`, **10/Seite**. Felder: `studyReferenceNumber`, `studyVersionTitle{de,en,…}`, `studyVersionAbstract{…}`, `studyVersionEndDate`, `datasets:[{licenseAccessLevel}]` |
| `/catalogue/search` | GET | 405 | ✅ erwartbar | POST-only |
| `/datasets` | GET | **403** | 🔒 **gated** | `{"403":"403 error"}` — Daten-API verlangt Auth |
| `/datasets/{id}` | GET | 404/403 | 🔒 gated | JSON-Fehler, nicht öffentlich |
| `/projects`, `/schemas` | GET | 404 | – | nicht ohne Auth/Kontext erreichbar |
| Study-Detail (`{ref}/{versionId}`) | GET | – | ⚠️ **offen** | Routen `:studyRefNumber/:studyVersionId/{datasets,files}` existieren; exakter API-Pfad in Phase 2 zu ermitteln |

### 2.2 «Auffindbar» vs. «Abrufbar» (Known Limitation, **kein Bug**)

| Ebene | Status | Nachweis |
|---|---|---|
| **Auffindbar** (Metadaten: Titel, Abstract, Disziplin-Schema, Datensatz-Liste, `licenseAccessLevel`) | ✅ **frei** via `POST /api/v2/catalogue/search` | 200, keine Auth |
| **Abrufbar** (eigentliche Forschungsdaten-Files) | 🔒 **hinter Registrierung + Datenantrag** | `/api/v2/datasets` → 403; `licenseAccessLevel:"restricted"` pro Datensatz |

Der Katalog liefert pro Datensatz ein **`licenseAccessLevel`** (z. B.
`"restricted"`) — das ist exakt der Hebel für den vorgeschlagenen Parameter
`access_level` in `search_research_datasets`. Der MCP-Server macht Studien
**auffindbar** und kennzeichnet transparent, was nur nach Login **abrufbar** ist.

### 2.3 Architektur-Entscheid FORS → **A (Live-API-only) für Metadaten**

Begründung (live verifiziert 2026-07-19):
- `POST /api/v2/catalogue/search` ist stabil, öffentlich, mehrsprachig, klein
  (10 Records/Seite) → kein Dump nötig, kein Caching-Zwang.
- Actual data downloads bewusst **nicht** im Scope (Phase-1-No-Auth-Prinzip):
  Server macht nur Metadaten zugänglich, verweist für Daten auf SWISSUbase-Login.
- Retry/Backoff + Provenance-Envelope wie bei allen Portfolio-Servern (Skill 3).

### 2.4 Offener Punkt für Phase 2 (kein Blocker)

Die **server-seitige Filterung** (Volltext/Facetten) von `catalogue/search`
konnte per Black-Box nicht rekonstruiert werden: `{}` liefert den vollen Bestand,
jedes zusätzliche Body-Feld quittiert die strikte Validierung mit `400` (leerer
Fehlerbody), und Query-String-Parameter (`?query=`, `?page=`) werden ignoriert.
Aus den JS-Bundles extrahierte Feldnamen (`text`, `schemaCode`, `disciplineCodes`,
`metadataLanguageCode`, `hasDataset`, `sort`, …) ergeben einzeln kein gültiges
DTO — es braucht das **vollständige** Objekt.

**Auflösung in Phase 2:** exakter Request-Body per authentifiziertem
Browser-DevTools-Capture abgreifen (in dieser Sandbox blockiert der Agent-Proxy
Chromium vollständig — `ERR_CONNECTION_RESET` auch gegen `example.com`; curl
funktioniert). **Fallback**, falls kein Server-Filter erschliessbar: paginiertes
Client-seitiges Filtern über den Katalog (12 526 Studien, 10/Seite) mit Cache —
funktional, aber teurer.

---

## 3. Abgrenzung zum Portfolio (Kurzfassung — Detail in Phase 2)

| Server / Tools | Domäne | Objekt |
|---|---|---|
| `swiss-academic-libraries-mcp` (bestehend: swisscovery, e-rara, …) & `eth-library-mcp` | **Bibliothekskatalog** | **Publikationen** (Bücher, Zeitschriften, Digitalisate) |
| Neue SNF/FORS-Tools | **Forschungsförderung & Forschungsdaten** | **Projekte** (Grants) & **Datensätze** (Studien) |

Kernsatz: *Bibliothek = was publiziert wurde; Forschungsdaten = was gefördert
und erhoben wurde.* Ein Nutzer, der beide in einer Session verwendet, kann von
einer geförderten Fragestellung (SNF-Grant) über die erhobenen Daten (FORS-Studie)
bis zur publizierten Literatur (swisscovery) durchgehen — echte Komplementarität.

**Synergie-Check:** Andere Lizenz (CC BY-SA / DDI vs. Bibliotheks-MARC), anderer
Trust-Level und andere Update-Frequenz → rechtfertigt eigene Tools (bzw. je nach
Entscheid eigenen Server). Finale Abgrenzung + Entscheid *Tool-Extension vs.
neuer Server* in Phase 2.

---

## 4. Vorgeschlagene Tools (Phase 2) & Feldabdeckung

| Tool | Quelle | Deckung durch Probe |
|---|---|---|
| `search_research_projects(query, institution, discipline, year_from, year_to)` | SNF-Dump-Index | Titel, Institution (`ResearchInstitution`), Disziplin, Laufzeit, Betrag, Förderinstrument ✅; Abstract nur bei Abstract-Index |
| `get_research_project(project_id)` | SNF Live `/grants/grant/{id}` | Voll-Record ✅ (kein Abstract → ggf. aus Dump anreichern) |
| `search_research_datasets(query, discipline, access_level)` | FORS `/catalogue/search` | Titel, Abstract, `licenseAccessLevel` ✅; `query`/`discipline`-Filter abhängig von DTO-Capture (§2.4) |

## 5. Anchor Demo Query — Machbarkeit

> *«Welche vom SNF geförderten Forschungsprojekte zur Digitalisierung in der
> Volksschule laufen aktuell, und an welchen Institutionen?»*

**Machbar über SNF-Dump-Index (Architektur B):** Volltext auf Titel/Abstract
(`Digitalisierung`, `Volksschule`/`Schule`) + Filter `state = ongoing` +
Rückgabe `ResearchInstitution`. Der Live-`/grants/search` allein könnte das
**nicht** (ignoriert Query) — der Dump ist der Grund, warum die Anchor-Query
überhaupt beantwortbar ist.

---

## 6. Resilienz-Defaults für Phase 2 (nicht verhandelbar, Skill 3)

- Retry mit exp. Backoff (2s/4s/8s) für **alle** HTTP-Aufrufe inkl. Dump-Download.
- Pydantic-Envelope mit `source` (SNF: «Data: SNSF — CC BY-SA 4.0») + `provenance`
  (`weekly_dump` | `live_api` | `cached`) in **jeder** Response.
- `dump_status()` / Graceful Degradation mit Timestamp des letzten Syncs.
- Tests: Happy / Retry-bei-503 / Timeout (respx) + `@pytest.mark.live`.
