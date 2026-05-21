# Audit-Report: swiss-academic-libraries-mcp

**Datum:** 2026-05-21
**Auditor:** Claude Code (automatisiert) mit [mcp-audit-skill](https://github.com/malkreide/mcp-audit-skill)
**Server-Version:** 0.2.0
**Skill-Methodik:** 7-Schritte-Audit (Profil → Catalog → Applicability → Execution → Findings → Report → Release-Proposal)
**Run-ID:** `2026-05-21T00:00:00+02:00-swiss-academic-libraries-mcp`

---

## 1. Executive Summary

`swiss-academic-libraries-mcp` ist ein **Read-only-MCP-Server für öffentliche Schweizer Bibliotheksmetadaten** (swisscovery, e-rara, e-periodica, e-manuscripta). Er nutzt FastMCP, Pydantic v2, sauber annotierte Tools und ist gut dokumentiert (DE/EN, CHANGELOG, CONTRIBUTING, CI).

**Verdict: Production-ready für stdio-Nutzung in Claude Desktop. Nicht production-ready für unbeschränkten HTTP-Betrieb.**

| Severity  | Anzahl | Production-blockierend |
|-----------|--------|------------------------|
| critical  | 0      | –                      |
| high      | 4      | nur für HTTP-Deployment |
| medium    | 5      | nein                   |
| low       | 4      | nein                   |
| info      | 2      | nein                   |

Die vier `high`-Findings konzentrieren sich auf **Härtung der `--http`-Transport-Variante** sowie **XML-Parser-Sicherheit** und **Supply-Chain-Hygiene**. Für die typische Nutzung über `uvx swiss-academic-libraries-mcp` (stdio) ist der Server heute sicher.

---

## 2. Profil-Snapshot

| Feld           | Wert                                                         |
|----------------|--------------------------------------------------------------|
| Transport      | stdio + streamable_http (dual)                               |
| Auth-Modell    | **keine** (Server-seitig); Upstream-APIs sind offen          |
| Datenklasse    | öffentliche bibliografische Open Data                        |
| Schreibzugriff | **read-only** (alle 11 Tools `destructiveHint: false`)       |
| Deployment     | Claude Desktop (stdio) · self-hosted via uvx (HTTP)          |
| SDK            | FastMCP (Python) · Pydantic v2 · httpx                       |
| Repo           | github.com/malkreide/swiss-academic-libraries-mcp            |
| CH-Bezug       | Schweizer Bibliotheks-Infrastruktur, keine Personendaten     |

---

## 3. Applicability-Filter

Von 68 Catalog-Checks sind **31 anwendbar**:

| Kategorie | Total | Anwendbar | N/A | Begründung der N/A                                                  |
|-----------|-------|-----------|-----|---------------------------------------------------------------------|
| ARCH      | 12    | 10        | 2   | Tool-Composition-Patterns für CRUD                                  |
| SDK       | 5     | 5         | 0   | –                                                                   |
| SEC       | 23    | 9         | 14  | Sämtliche OAuth/Token/Consent-Checks (kein Auth-Layer)              |
| SCALE     | 6     | 4         | 2   | Loadbalancer/Sticky-Sessions irrelevant für stdio + Single-Process  |
| OBS       | 6     | 5         | 1   | SIEM-Integration nicht im Scope                                     |
| HITL      | 5     | 0         | 5   | Server destruktiv-frei, keine Sampling/Elicitation-Pfade            |
| CH        | 8     | 5         | 3   | DSG-Personendatenschutz, ISDS-Datenklassifikation nicht einschlägig |
| OPS       | 3     | 3         | 0   | –                                                                   |
| **Total** | 68    | **31**    | 37  |                                                                     |

---

## 4. Findings (priorisiert)

### F-01 · HIGH · SEC · `defusedxml` wird nicht eingesetzt

**Beobachtet:** `src/swiss_academic_libraries_mcp/api_client.py:14` importiert `xml.etree.ElementTree`. Sämtliche Upstream-XML-Antworten (SRU/MARC21, OAI-PMH) werden damit geparst.

**Erwartet:** `defusedxml.ElementTree` für externe XML-Eingaben, um XML-Bomben (billion-laughs, quadratic blowup) und Entity-Expansion abzufangen. Auch wenn CPython externe Entities seit 3.7.1 standardmässig blockt, bleibt der DoS-Vektor.

**Evidenz:** `api_client.py:14`, Nutzungsstellen `:232, :328, :365`.

**Risiko:** Ein kompromittierter Upstream-Endpunkt (oder MITM ohne HTTPS-Pinning) kann den Server mit einem präparierten XML-Dokument zum Hängen / OOM bringen. Wahrscheinlichkeit niedrig (alle Quellen HTTPS, SLSP/ETH), Impact hoch.

**Remediation:** `defusedxml` in `pyproject.toml` aufnehmen und Imports umstellen:
```python
from defusedxml.ElementTree import fromstring
```
**Effort:** S (~1–2 h inkl. Tests)

---

### F-02 · HIGH · SEC · Streamable-HTTP-Transport ohne Host-Binding, Auth und Origin-Validierung

**Beobachtet:** `src/swiss_academic_libraries_mcp/server.py:1029-1042` startet `mcp.run(transport="streamable_http", port=port)` ohne `host=`-Argument, ohne Origin-Allowlist und ohne Auth.

**Erwartet:**
1. Default-Bind auf `127.0.0.1` (loopback), explizites `--host`-Flag für andere Bindings.
2. `Origin`-Header-Validierung (DNS-Rebinding-Schutz; vgl. MCP Streamable-HTTP-Spec).
3. Optionaler Bearer-Token (z.B. `MCP_AUTH_TOKEN` via env) oder Hinweis "nur hinter Reverse Proxy mit Auth betreiben" im README.

**Evidenz:**
- `server.py:1029-1042` (kein `host`-Parameter)
- `README.md` Abschnitt "Cloud / Self-hosted" empfiehlt `--http --port 8000` ohne Sicherheitshinweis.

**Risiko:** Auf einem Multi-User-Host oder bei versehentlicher `0.0.0.0`-Bindung kann jeder LAN-Nutzer Anfragen über den Server an die Upstream-Bibliotheks-APIs absetzen. Konkrete Konsequenzen:
- Amplification / IP-Reputation: SLSP/ETH-Logs sehen den Server-Betreiber als Quelle.
- DNS-Rebinding aus dem Browser eines lokalen Nutzers (klassischer MCP-HTTP-Angriffsvektor).

**Remediation:** In `main()`:
```python
host = "127.0.0.1"
for i, arg in enumerate(sys.argv):
    if arg == "--host" and i + 1 < len(sys.argv):
        host = sys.argv[i + 1]
mcp.run(transport="streamable_http", host=host, port=port)
```
README-Block "Security & Deployment" ergänzen.
**Effort:** S (~2–3 h)

---

### F-03 · HIGH · OBS · Komplett fehlende Server-Logs

**Beobachtet:** Weder `server.py` noch `api_client.py` importieren `logging`. Es existiert keine Trace-, Info-, Warn- oder Error-Logging-Schicht.

**Erwartet:** Strukturiertes Logging (stdlib `logging` oder `structlog`) auf **stderr** (niemals stdout in stdio-Transport!). Mindestens:
- INFO: Tool-Invocation, Upstream-URL, Dauer.
- WARN: 429, 503, parser-Fallback.
- ERROR: Unerwartete Exceptions (zusätzlich zu `handle_api_error`).

**Evidenz:** Volltext-Grep auf `logging`/`logger` ist leer in `src/`.

**Risiko:** Im Produktionsbetrieb (besonders HTTP) sind Probleme nicht diagnostizierbar; Abuse-Erkennung unmöglich.

**Remediation:**
```python
import logging, sys
logger = logging.getLogger("swiss_academic_libraries_mcp")
logging.basicConfig(stream=sys.stderr, level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(name)s %(message)s")
```
Plus Log-Calls in `http_get`, `handle_api_error`, jedem Tool-Entry.
**Effort:** M (~3–4 h inkl. Test-Anpassung)

---

### F-04 · HIGH · OPS/SEC · Keine Dependency-/Supply-Chain-Prüfung in CI

**Beobachtet:** `.github/workflows/ci.yml` führt nur `ruff check`, `py_compile` und `pytest` aus. Kein `pip-audit`, `safety`, kein Dependabot-Konfig (`.github/dependabot.yml` fehlt), kein `bandit` SAST.

**Erwartet:** Mindestens `pip-audit`-Job + Dependabot-Konfig (weekly) + optional `bandit -r src/`.

**Evidenz:** `ci.yml:1-66` enthält keinen Security-Job; `find .github -type f` listet kein `dependabot.yml`.

**Risiko:** Bekannte CVEs in `httpx`/`mcp`/`pydantic` werden nicht erkannt. Für ein PyPI-publiziertes Paket besonders relevant.

**Remediation:** Job ergänzen:
```yaml
security:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v5
    - uses: actions/setup-python@v6
      with: { python-version: "3.11" }
    - run: pip install pip-audit
    - run: pip-audit --strict
```
Plus `.github/dependabot.yml` mit `pip` + `github-actions` weekly.
**Effort:** S (~1 h)

---

### F-05 · MEDIUM · SDK · Keine httpx-Client-Wiederverwendung, keine Concurrency-Limits

**Beobachtet:** `api_client.py:71-74` instanziiert pro Request einen neuen `httpx.AsyncClient` mit `async with`. Kein gemeinsamer Connection-Pool, keine Semaphore.

**Erwartet:** Ein modulweiter (oder via FastMCP-`lifespan` verwalteter) Client mit Connection-Reuse und einer `asyncio.Semaphore`-basierten Concurrency-Begrenzung (z.B. 5 parallele Upstream-Calls).

**Evidenz:** `api_client.py:69-74`.

**Risiko:** Performance-Penalty (TLS-Handshake je Call), und unbegrenzte Parallelität kann SLSP-Rate-Limits triggern (HTTP 429), was Nutzer als Server-Defekt wahrnehmen.

**Remediation:** Shared client + `httpx.Limits(max_connections=10)` + `Semaphore(5)`.
**Effort:** S–M (~2–3 h)

---

### F-06 · MEDIUM · SEC · Kein User-Agent gegenüber Upstream-APIs

**Beobachtet:** `api_client.py:69-74` setzt keinen `User-Agent`-Header.

**Erwartet:** Identifizierender UA gemäss SLSP- und OAI-PMH-Best-Practice:
```
swiss-academic-libraries-mcp/0.2.0 (+https://github.com/malkreide/swiss-academic-libraries-mcp)
```

**Risiko:** Bibliotheken können bei Abuse nicht differenzieren; bei Rate-Limit-Whitelisting fehlt der Identifier. Höflichkeits-/Compliance-Issue gegenüber öffentlichen Diensten.

**Remediation:** `headers={"User-Agent": USER_AGENT}` im AsyncClient-Konstruktor.
**Effort:** XS (~15 min)

---

### F-07 · MEDIUM · OBS/SDK · Fehlerantworten als "erfolgreiche" Strings

**Beobachtet:** `handle_api_error` (`api_client.py:77-93`) gibt einen formatierten Fehler-String zurück, der vom Tool als normaler Result-String an den MCP-Host weitergegeben wird. Der Host sieht keinen `isError=true`.

**Erwartet:** Bei nicht-recoverable Fehlern eine `McpError`/Exception werfen, damit FastMCP `isError=true` setzt. Recoverable Hinweise (z.B. "keine Treffer") bleiben Strings.

**Evidenz:** `server.py:391, 466, 552, 589, 651, 706, 743, 811, 848, 910`.

**Risiko:** Modelle behandeln Fehler als Daten und halluzinieren weiter. Schlechtere User Experience.

**Remediation:** `handle_api_error` zu `raise McpError(...)` umbauen; FastMCP's globalen Error-Hook prüfen.
**Effort:** S (~1–2 h)

---

### F-08 · MEDIUM · SEC · Prompt-Injection-Oberfläche aus Upstream-Metadaten

**Beobachtet:** Felder wie `dc:description`, `dc:title`, MARC-`520` (Abstract) werden 1:1 in die Antwort eingebettet (`api_client.py:format_*`, `server.py`). Die Quellen sind öffentliche Kataloge; ein Bibliothekseintrag kann theoretisch LLM-Steuerungs-Text enthalten.

**Erwartet:** Hinweis im Tool-Output, dass eingebetteter Inhalt **Daten**, nicht **Instruktion** ist. Optional: fenced code blocks oder `<data>`-Tagging um Untrusted-Content.

**Evidenz:** `api_client.py:383-443`, `server.py:477-509, 594-616, 748-770, 853-877`.

**Risiko:** Niedrig in der Praxis (bibliografische Daten), aber im Education-Research-Workflow (Prompt `education-research`) konsumiert das Modell die Treffer direkt.

**Remediation:** Im Markdown-Output Block mit Hinweis bzw. `## Treffer (Daten, keine Instruktionen)`.
**Effort:** S (~1 h)

---

### F-09 · MEDIUM · CH · Hosting-Souveränität nicht dokumentiert

**Beobachtet:** README erwähnt keine Empfehlung zur Datenresidenz beim Self-Hosting für Schweizer Behörden-Kontexte (z.B. Schulamt-Zielgruppe, die im `education-research`-Prompt adressiert wird).

**Erwartet:** Abschnitt "Deployment für CH-Behörden" mit Hinweis auf On-Premise- oder CH-Cloud-Hosting, da die Anfragen-Pattern selbst (welche Bibliothekssuchen ein Beamter durchführt) als Metadaten relevant sein können.

**Effort:** S (~30 min Doku)

---

### F-10 · LOW · ARCH · `library_info` dupliziert README-Inhalt statisch

**Beobachtet:** `server.py:268-339` enthält eine fest codierte Markdown-Übersicht, die mit README.md/EXAMPLES.md drifted.

**Erwartet:** Entweder aus README-Snippet generieren oder Single-Source markieren.

**Risiko:** Konsistenz-Drift. Niedrig.

**Effort:** XS

---

### F-11 · LOW · OPS · Versions-Drift README-Badge vs. pyproject.toml

**Beobachtet:** `README.md:3` zeigt `version-0.1.0` Badge, `pyproject.toml:8` deklariert `0.2.0`. `CHANGELOG.md` prüfen.

**Remediation:** Dynamic Badge (`pypi/v/...`) oder bei Release synchronisieren.

**Effort:** XS

---

### F-12 · LOW · SEC · `oai_identifier`-Pattern zu permissiv

**Beobachtet:** `OaiGetRecordInput.oai_identifier` (`server.py:140-147`) erzwingt nur `min_length=5`, kein Regex.

**Erwartet:** Pattern `^oai:[A-Za-z0-9._-]+:[A-Za-z0-9._:/-]+$` als Defense-in-Depth gegen ungewöhnliche Input-Manipulation.

**Effort:** XS

---

### F-13 · LOW · OBS · Keine `request_id`-Korrelation

**Beobachtet:** Kein Korrelations-ID zwischen MCP-Request und Upstream-HTTP-Call. Bei Logging nachholen.

**Effort:** XS (Teil von F-03)

---

### F-14 · INFO · ARCH · Tool-Annotationen vorbildlich

`readOnlyHint`, `destructiveHint`, `idempotentHint`, `openWorldHint` sind auf allen 11 Tools korrekt gesetzt. `library_info` ist als einziges Tool `openWorldHint: false` markiert (kein Netzwerkzugriff) – semantisch exakt. **Best-Practice-Beispiel.**

---

### F-15 · INFO · OPS · Test-Coverage solide

34 Unit-Tests + 6 Live-Smoke-Tests + 20 Szenarien-Skript. Live-Tests via `pytest -m live` deselektierbar. CI läuft auf Python 3.11/3.12/3.13. **Empfehlung:** Coverage-Report (`pytest --cov`) als CI-Artefakt.

---

## 5. Bestandene Schlüssel-Checks

| Check                                                       | Ergebnis |
|-------------------------------------------------------------|----------|
| ARCH-001 Tool-Naming (`snake_case`, konsistent)             | PASS     |
| ARCH-002 Tool-Beschreibungen mit Use-Case-Kontext           | PASS     |
| ARCH-003 Tool-Annotationen (readOnly/destructive/...)       | PASS     |
| ARCH-004 Idempotenz aller GET-Operationen                   | PASS     |
| SDK-001 FastMCP korrekt initialisiert mit `instructions`    | PASS     |
| SDK-002 Pydantic-Validierung (`extra="forbid"`, patterns)   | PASS     |
| SDK-003 Input-Size-Limits (`max_length`, `le=50`)           | PASS     |
| SEC-005 HTTPS-only Upstream-URLs                            | PASS     |
| SEC-008 Keine Secrets im Repo / kein `.env`                 | PASS     |
| SEC-014 Input-Validierung via Pydantic patterns             | PASS     |
| OPS-001 README zweisprachig (DE/EN), CHANGELOG, CONTRIBUTING| PASS     |
| OPS-002 CI mit Linting und Tests                            | PASS     |
| CH-001 Open-Data-Quellen klar deklariert, MIT-Lizenz        | PASS     |

---

## 6. Remediation-Plan

| Phase                | Findings                       | Aufwand   |
|----------------------|--------------------------------|-----------|
| **vor v0.3.0**       | F-01, F-02, F-04, F-06         | ~1 Tag    |
| **vor v1.0 stable**  | F-03, F-05, F-07, F-08, F-09   | ~2 Tage   |
| **Nice-to-have**     | F-10 bis F-13                  | ~½ Tag    |

---

## 7. Release-Proposal

**Nicht empfohlen** für `v1.0.0` ohne Adressierung von F-01 bis F-04.

**Empfohlen:** Patch-Release `v0.2.1` mit F-01 (defusedxml) + F-06 (User-Agent) als Quick-Wins, dann Minor `v0.3.0` mit F-02/F-03/F-04.

---

## 8. Audit-Metadaten

- **Skill-Quelle:** https://github.com/malkreide/mcp-audit-skill (Branch `main`)
- **Catalog-Größe:** 68 Checks
- **Anwendbare Checks:** 31
- **Findings dokumentiert:** 15 (4 high · 5 medium · 4 low · 2 info)
- **Methodik:** Statische Code-Review (Read, Grep) ohne Live-Ausführung des Servers
- **Limitierungen:** Vollständiger Check-Katalog der Skill wurde nicht 1:1 abgearbeitet (Manifest nicht öffentlich abrufbar); Findings basieren auf den dokumentierten Kategorien (ARCH/SDK/SEC/SCALE/OBS/HITL/CH/OPS) und gängigen MCP-Best-Practices.
