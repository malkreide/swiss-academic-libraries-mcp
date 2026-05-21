# Re-Audit-Report: swiss-academic-libraries-mcp

**Datum:** 2026-05-21
**Auditor:** Claude Code mit [mcp-audit-skill](https://github.com/malkreide/mcp-audit-skill)
**Audit-Typ:** Re-Audit nach vollständiger Remediation
**Vergleichsbasis:** [`audits/2026-05-21-swiss-academic-libraries-mcp/`](../2026-05-21-swiss-academic-libraries-mcp/)
**Server-Version:** 1.0.1 (zuvor: 0.2.0)
**Run-ID:** `2026-05-21T07:35:00+02:00-rerun`

---

## 1. Executive Summary

Re-Audit nach Abarbeitung des Remediation-Plans aus dem Erst-Audit. Vier Patch-/Minor-/Major-Releases haben **alle 13 Findings** (4 high · 5 medium · 4 low) geschlossen, ein zusätzlicher CI-Fix die Test-Pipeline grün gemacht.

**Verdict: Production-ready.** Keine Regressionen, keine neuen high/medium-Findings. Vier neue low-Findings betreffen CI-Coverage und Release-Hygiene, nicht Sicherheit oder Funktionalität.

| Severity  | Erst-Audit | Geschlossen | Neu (Re-Audit) | Offen |
|-----------|------------|-------------|----------------|-------|
| critical  | 0          | –           | 0              | 0     |
| high      | 4          | 4 ✅        | 0              | 0     |
| medium    | 5          | 5 ✅        | 0              | 0     |
| low       | 4          | 4 ✅        | 4              | 4     |
| info      | 2          | –           | 2              | –     |

---

## 2. Verifikation: Alle 13 Erst-Audit-Findings geschlossen

| ID    | Sev | Titel                                          | Verifikation                                                   | Status |
|-------|-----|------------------------------------------------|----------------------------------------------------------------|--------|
| F-01  | H   | defusedxml für Upstream-XML                    | 3× `_safe_fromstring` statt `ET.fromstring` in api_client.py   | ✅     |
| F-02  | H   | HTTP-Transport härten                          | `_parse_args` mit `--host`, Default `127.0.0.1`, WARN-Log       | ✅     |
| F-03  | H   | Strukturiertes Logging                         | `logging.basicConfig(stream=stderr)` + Log-Calls in `http_get`  | ✅     |
| F-04  | H   | pip-audit + Dependabot                         | CI-Job `security`, `.github/dependabot.yml` aktiv               | ✅     |
| F-05  | M   | Shared httpx-Client + Semaphore                | `_get_client()` + `_get_semaphore(5)`, lifespan-Shutdown        | ✅     |
| F-06  | M   | User-Agent                                     | `USER_AGENT`-Constant, dynamisch aus `importlib.metadata`       | ✅     |
| F-07  | M   | McpError statt Success-Strings                 | 10× `raise _to_mcp_error(e, ...) from e` in allen Tools         | ✅     |
| F-08  | M   | Prompt-Injection-Disclaimer                    | `DATA_DISCLAIMER` + JSON-`_disclaimer`-Feld                     | ✅     |
| F-09  | M   | CH-Hosting-Hinweis                             | README (DE/EN) Abschnitt "Deployment für Schweizer Behörden"    | ✅     |
| F-10  | L   | SOURCES Single-Source                          | Module-level `SOURCES`-Dict; `library_info` + `library://sources` lesen daraus | ✅ |
| F-11  | L   | Dynamic PyPI-Badge                             | `shields.io/pypi/v/...` in beiden READMEs                       | ✅     |
| F-12  | L   | oai_identifier-Regex                           | `pattern=r"^oai:[A-Za-z0-9.\-_]+:[A-Za-z0-9.\-_:/]+$"`           | ✅     |
| F-13  | L   | request_id-Korrelation                         | `contextvars.ContextVar` + `RequestIdLogFilter` + `new_request_id()` | ✅ |

**Bonus-Fix:** Transport-Bezeichner `streamable_http` → `streamable-http` (korrekte FastMCP-API) — der Code wäre vorher mit aktuellen mcp-Versionen mit TypeError gescheitert.

---

## 3. Regressions-Check

| Bereich                       | Befund                                                                                  |
|-------------------------------|----------------------------------------------------------------------------------------|
| Tool-Annotations              | Alle 11 Tools weiterhin korrekt `readOnly/destructive/idempotent/openWorld`             |
| Input-Validation              | Pydantic-Patterns intakt, neuer `oai_identifier`-Regex bricht keine echten IDs          |
| stdio-Transport               | Logging auf stderr — kein JSON-RPC-Konflikt                                             |
| Lifespan                      | FastMCP-`lifespan`-Context-Manager schliesst Client sauber                              |
| Test-Suite                    | 57 Unit-Tests + 26 Live-Tests; alle Unit-Tests grün auf 3.11 lokal und in CI            |
| CI-Pipeline                   | lint + test (3.11/3.12/3.13) + security alle grün auf `main`                            |

**Keine Regressionen.**

---

## 4. Neue Findings

### NEW-01 · LOW · OPS · CHANGELOG hat doppelten 0.1.0-Eintrag

**Beobachtet:** `CHANGELOG.md` hat zwei `## [0.1.0]`-Sektionen mit verschiedenen Daten (2026-03-23 und 2026-03-13).

**Evidenz:** `CHANGELOG.md:8` vs `CHANGELOG.md:123`.

**Risiko:** Niedrig. Verwirrung beim Release-Lesen, automatische Release-Tooling (z.B. Keep-a-Changelog-Parser) bricht potentiell.

**Remediation:** Eine der beiden Sektionen entfernen oder konsolidieren.

**Effort:** XS

---

### NEW-02 · LOW · OPS · PyPI-Release-Drift

**Beobachtet:** Aktuelle Code-Version ist 1.0.1; PyPI hat noch 0.2.0. Das dynamic Version-Badge (F-11) zeigt deshalb 0.2.0, nicht 1.0.1.

**Evidenz:**
```bash
$ curl -s https://pypi.org/pypi/swiss-academic-libraries-mcp/json | jq .info.version
"0.2.0"
$ grep version pyproject.toml
version = "1.0.1"
```

**Risiko:** Niedrig, aber **wichtig vor dem nächsten Release-Tag.** Wenn ein Nutzer das Badge sieht und denkt "0.2.0 ist current", übersieht er die Audit-Remediation. PyPI muss vor dem nächsten Push aktualisiert werden.

**Remediation:** GitHub-Release v1.0.1 erstellen → `publish.yml` deployt automatisch. (Alle Zwischen-Versionen 0.2.1, 0.3.0, 1.0.0 werden übersprungen, das ist akzeptabel.)

**Effort:** XS — Release Tag in GitHub-UI erstellen.

---

### NEW-03 · LOW · OPS · `ruff check tests/` zeigt 3 Pre-Existing-Errors

**Beobachtet:** `ruff check src/` ist grün (so wie CI prüft). `ruff check tests/` zeigt 3 Errors:

```
E402 Module level import not at top of file       (test_20_scenarios.py:27)
F841 Local variable 'status' assigned but unused  (test_20_scenarios.py:52)
F841 Local variable 'empty_xml' assigned but unused (test_server.py:184)
```

**Evidenz:** `ruff check tests/`.

**Risiko:** Niedrig. Pre-Existing — nicht durch Remediation entstanden. Aber inkonsistent (warum nur `src/` linten?).

**Remediation:** Entweder Errors fixen und `ruff check tests/` in CI ergänzen, oder explizit `[tool.ruff.lint.per-file-ignores]` mit Begründung pinnen.

**Effort:** S (15 min für Fixes oder Ignore-Pin).

---

### NEW-04 · LOW · OPS · Unit-Tests laufen nur auf Python 3.11

**Beobachtet:** CI-Matrix hat `["3.11", "3.12", "3.13"]`, aber Unit-Tests sind durch
```yaml
if: matrix.python-version == '3.11'
```
nur auf 3.11 begrenzt. Auf 3.12/3.13 laufen nur lint + syntax + import.

**Evidenz:** `.github/workflows/ci.yml:44-49`.

**Risiko:** Niedrig. Runtime-Bugs, die nur auf 3.12+ auftreten (z.B. durch deprecated APIs, Type-Hint-Änderungen, asyncio-Verhalten), würden unentdeckt bleiben. Die Library deklariert in `classifiers` Support für 3.11/3.12/3.13.

**Remediation:** `if`-Bedingung entfernen, Tests auf allen drei Matrix-Versionen laufen. Live-Tests bleiben durch `-m "not live"` ausgeschlossen.

**Effort:** XS — eine Zeile aus `ci.yml` entfernen.

---

### NEW-05 · INFO · SDK · Race-Condition-Theorie für `_get_client()`

**Beobachtet:** `_get_client()` checkt `_client is None or _client.is_closed` und konstruiert ggf. einen neuen Client — ohne Lock.

**Risiko:** In Python-asyncio mit single Event Loop ist dieser sync-Code atomar (keine `await`-Punkte im check-and-set), daher safe. Wenn der Server jemals mit mehreren Event-Loops in Threads laufen würde (sehr untypisch für MCP), könnte race condition entstehen.

**Remediation:** Aktuell nicht nötig. Hinweis-Kommentar im Code wäre nice-to-have.

**Effort:** XS — Kommentar.

---

### NEW-06 · INFO · OBS · `respx` ist installiert aber ungenutzt

**Beobachtet:** CI installiert `respx` als Test-Dependency, aber kein Test importiert `respx`. Mocking-Coverage für `http_get` mit dem neuen shared Client fehlt.

**Risiko:** Test-Coverage-Gap. Sicherheits-/Funktions-Auswirkung null.

**Remediation:** Entweder `respx` aus CI-Deps entfernen, oder Mocked-Test für `http_get`-Verhalten ergänzen (Connection-Reuse, Semaphore, User-Agent-Header, request_id-Inkrement).

**Effort:** S — Test schreiben oder dependency entfernen.

---

## 5. Production-Ready-Bewertung

**Empfehlung: PRODUCTION READY** für stdio (Claude Desktop) **und** Streamable-HTTP (mit Reverse-Proxy-Hinweis im README).

| Kriterium                                        | Status |
|--------------------------------------------------|--------|
| Keine offenen critical-Findings                  | ✅     |
| Keine offenen high-Findings                      | ✅     |
| Keine offenen medium-Findings                    | ✅     |
| Test-Pipeline grün auf `main`                    | ✅     |
| Dependency-Scan grün                             | ✅     |
| Logging, Error-Handling, Security-Hinweise da    | ✅     |
| Dokumentation (DE/EN, CH-Hosting, Reverse-Proxy) | ✅     |

---

## 6. Release-Proposal

Nächster Schritt: **GitHub-Release `v1.0.1`** erstellen → `publish.yml` lädt nach PyPI hoch. Das schliesst NEW-02 automatisch.

Anschließend: optional ein Sweep-PR für NEW-01, NEW-03, NEW-04, NEW-06 (alle XS-S).

---

## 7. Audit-Metadaten

- **Skill-Quelle:** https://github.com/malkreide/mcp-audit-skill
- **Methodik:** Statische Code-Review + Spot-Checks (`grep`, `ls`, `ruff`)
- **Vergleichsbasis:** Erst-Audit vom 2026-05-21 (gleicher Tag, frühere Version)
- **Verifikations-Tiefe:** Jedes der 13 Findings durch direktes `grep` der erwarteten Code-Stellen bestätigt
- **Limitationen:** Keine Live-Ausführung des Servers, keine Inspektion der GitHub-Actions-Logs (nur Status-Polling)
