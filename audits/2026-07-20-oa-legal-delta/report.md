# Delta-Audit-Report: swiss-academic-libraries-mcp (OA-Rechtsliteratur-Pfad)

**Datum:** 2026-07-20
**Auditor:** Claude Code mit [mcp-audit-skill](https://github.com/malkreide/mcp-audit-skill)
**Audit-Typ:** Delta-Audit (nur neue Funktionalität)
**Vergleichsbasis:** [`audits/2026-05-21-re-audit/`](../2026-05-21-re-audit/)
**Server-Version:** 1.1.0 (zuletzt auditiert: 1.0.2)
**Run-ID:** `2026-07-20-oa-legal-delta`

---

## 1. Executive Summary

Delta-Audit des neuen **Open-Access-Rechtsliteratur-Pfads** (v1.1.0): Modul
`oa_legal.py`, die Tools `oa_law_search`/`oa_law_get` und `http_get_with_retry`
in `api_client.py`. Der Katalog-Pfad (swisscovery, e-rara, e-periodica,
e-manuscripta) ist unverändert und wurde am 2026-05-21 auditiert.

**Verdict: Production-ready.** Keine critical/high/medium-Findings. Der Pfad
konstruiert keine ausgehende URL aus User-/LLM-Input, parst externes XML mit
`defusedxml` plus Steuerzeichen-Sanitisierung, validiert Eingaben strikt
(Pydantic `extra="forbid"`), liefert keinen Volltext und setzt `license` nie
leer. Zwei **low**-Findings wurden im selben Audit remediiert.

| Severity  | Neu | Remediiert | Offen |
|-----------|-----|------------|-------|
| critical  | 0   | –          | 0     |
| high      | 0   | –          | 0     |
| medium    | 0   | –          | 0     |
| low       | 2   | 2 ✅       | 0     |

---

## 2. Profil-Snapshot

| Feld | Wert |
|------|------|
| Transport | dual (stdio + streamable-http) |
| Auth-Modell | none |
| Datenklasse | Public Open Data (keine PII) |
| Schreibzugriff | read-only (alle 13 Tools `destructiveHint: false`) |
| Deployment | local-stdio + self-hosted HTTP |
| Neu: externe Requests | ja → `sui-generis.ch`, `ex-ante.ch`, `api.repositorium.ch`, `api.crossref.org` |

---

## 3. Applicability

Geprüft wurde die auf den Delta anwendbare Teilmenge des Katalogs (22 Checks).
Nicht anwendbar und daher nicht aufgeführt: alle OAuth/API-Key-Checks
(`auth_model == none`), HITL/Sampling (read-only), Cloud-Scale/SIEM/Tracing
(`data_class == Public Open Data`, kein neues Cloud-Infra), PII-CH-Checks.

| Kategorie | Geprüft | Ergebnis |
|-----------|---------|----------|
| ARCH | 8 | pass |
| SDK  | 2 | pass |
| SEC  | 6 | pass (2 low remediiert) |
| OBS  | 3 | pass |
| OPS  | 2 | pass |
| CH   | 1 | pass |

---

## 4. Findings

| ID | Severity | Check | Titel | Status |
|----|----------|-------|-------|--------|
| OA-01 | low | ARCH-005 / SEC-013 | Anon-Key hartkodiert ohne Env-Override | ✅ closed |
| OA-02 | low | SEC-021 | Keine Code-Layer-Egress-Allow-List | ✅ closed |

### Finding OA-01 — Repositorium Supabase-Anon-Key hartkodiert

**Severity:** low · **Status:** closed

**Observed:** `REPOSITORIUM_ANON_KEY` war als String-Literal in `oa_legal.py`
verdrahtet, ohne Override-Pfad.

**Kontext/Risiko:** Es handelt sich um den **öffentlichen** Supabase-Anon-Key
(Rolle `anon`, rein lesend), den der Repositorium.ch-Web-Client selbst im
ausgelieferten SPA offenlegt; der Verein bietet die API laut Nutzungsbedingungen
„offen und frei zugänglich" an. Es ist damit kein echtes Secret. Best Practice
(ARCH-005/SEC-013) verlangt dennoch einen Override-Pfad, damit ein rotierter
Schlüssel ohne Code-Änderung greift.

**Remediation:** Env-Var `OA_LAW_REPOSITORIUM_ANON_KEY` als Override ergänzt;
Default bleibt der öffentliche Anon-Key. Kommentar dokumentiert die Nicht-Secret-
Natur. Evidence: `src/swiss_academic_libraries_mcp/oa_legal.py` (`_REPOSITORIUM_ANON_KEY_DEFAULT` + `os.environ.get`).

### Finding OA-02 — Keine explizite Code-Layer-Egress-Allow-List

**Severity:** low · **Status:** closed

**Observed:** Ausgehende Requests gingen an fixe Registry-/Crossref-Hosts, aber
ohne expliziten Allow-List-Check vor dem Request.

**Kontext/Risiko:** Die Ziel-Hosts sind ausschliesslich Konstanten aus
`OA_LEGAL_SOURCES` + `CROSSREF_WORK_URL`; keine URL wird aus User-/LLM-Input
gebaut (Quelle wird gegen `SOURCE_KEYS` validiert, DOI ist regex-begrenzt und
`quote()`-kodiert). Das SSRF-Restrisiko ist daher gering. SEC-021 verlangt als
Defense-in-Depth dennoch einen Code-Layer-Check.

**Remediation:** `ALLOWED_HOSTS` (aus Registry + Crossref abgeleitet) +
`_assert_host_allowed()` vor jedem ausgehenden Request (`_fetch`-Wrapper). Die
Network-Layer-Kontrolle bleibt deployment-seitig (siehe README «Deployment for
Swiss Public Administration»). Evidence: `oa_legal.py` (`ALLOWED_HOSTS`,
`_assert_host_allowed`, `_fetch`); Test `tests/test_oa_legal.py::TestEgressAllowList`.

---

## 5. Geprüfte Checks (Evidenz-Auszug)

| Check | Ergebnis | Evidenz |
|-------|----------|---------|
| ARCH-001 Naming | pass | `oa_law_search`, `oa_law_get` — snake_case, konsistent |
| ARCH-002 Use-Case-Tags | pass | Docstrings mit Beispielanfragen |
| ARCH-003 Not-Found-Heuristik | pass | `oa_law_get` liefert erklärende Meldung statt leerer Antwort; Suche gibt Verfeinerungs-Hinweis |
| ARCH-005 Keine Hardcoded Secrets | pass* | OA-01 remediiert (Env-Override) |
| ARCH-006 Tool-Budget | pass | genau 2 neue High-Level-Tools (Suche + Detailabruf), nicht 1:1-API-Mapping |
| ARCH-008 Drei Primitive | pass | neue Resource `library://oa-legal-sources` ergänzt Tools + Prompts |
| ARCH-009 Tool-Annotations | pass | beide Tools: `readOnlyHint`/`destructiveHint`/`idempotentHint`/`openWorldHint` gesetzt |
| ARCH-011 Repo-Struktur | pass | src-Layout, Tests, bilinguale READMEs |
| SDK-001 Lifespan | pass | unveränderter `@asynccontextmanager`-Lifespan; neuer Pfad nutzt denselben Client |
| SDK-002 Pydantic-v2 | pass | `OaLegalPublication` (v2, `extra="forbid"`), `model_dump()` für JSON-Ausgabe |
| SEC-004 SSRF | pass | keine aus Input konstruierte URL; nur `https://`-Literale; DOI regex-begrenzt + quotiert |
| SEC-013 API-Key-Storage | pass* | OA-01 remediiert |
| SEC-018 Input-Validation | pass | `OaLawSearchInput`/`OaLawGetInput`: `extra="forbid"`, `Field`-Constraints, `source` gegen `SOURCE_KEYS` geprüft |
| SEC-019 Lethal Trifecta | pass | read-only, kein Write-/Send-Tool |
| SEC-020 Command Injection | pass | kein `os.system`/`subprocess`/`eval`/`exec` im neuen Code |
| SEC-021 Egress-Allow-List | pass* | OA-02 remediiert (Code-Layer) |
| OBS-001 Protocol vs Execution Errors | pass | `_to_mcp_error` → `McpError`; Teilausfall wird in der Antwort ausgewiesen |
| OBS-002 Mask Error Details | pass | `handle_api_error` gibt generische Meldungen, keine Stacktraces |
| OBS-004 stderr | pass | geerbte Logging-Konfiguration (stderr); `new_request_id()` je Request |
| OPS-001 Test-Strategie | pass | `respx`-gemockte Unit-Tests + `@pytest.mark.live` (79 not-live + 28 live) |
| OPS-002 Doku-Standard | pass | README/README.de: Architekturdiagramm, «Licensing & Scope», Known Limitations |
| CH-004 OGD-Lizenz-Attribution | pass | Attribution je Quelle in jeder Response; `license` Pflichtfeld, `unknown` statt geraten |

\* nach Remediation im selben Audit.

---

## 6. Audit-Metadata

- **Skill:** mcp-audit-skill (Best-Practice-Katalog, 68 Checks)
- **Scope:** Delta — nur OA-Rechtsliteratur-Pfad (v1.1.0)
- **Artefakte:** `profile.json`, `summary.json`, dieser Report
- **Production-ready:** ja (keine offenen critical/high/medium)
