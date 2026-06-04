# Sicherheitsrichtlinie

[🇬🇧 English Version](SECURITY.md)

## Unterstützte Versionen

Sicherheitsupdates werden für die jeweils neueste auf
[PyPI](https://pypi.org/project/swiss-academic-libraries-mcp/) veröffentlichte
Version bereitgestellt. Bitte aktualisieren Sie immer auf die aktuellste
Version, bevor Sie ein Problem melden.

## Eine Schwachstelle melden

Bitte melden Sie Sicherheitslücken **vertraulich** — eröffnen Sie für
sicherheitsrelevante Meldungen **kein** öffentliches Issue.

- Nutzen Sie [GitHub Security Advisories](../../security/advisories/new) für
  eine vertrauliche Meldung, **oder**
- kontaktieren Sie den Maintainer über
  [github.com/malkreide](https://github.com/malkreide).

Bitte fügen Sie bei:

- eine Beschreibung der Schwachstelle und ihrer möglichen Auswirkungen
- Schritte zur Reproduktion (Proof of Concept, betroffenes Tool/Endpoint)
- die betroffene Version und Ihre Umgebung (OS, Python-Version, Transport)

Sie erhalten innerhalb von **7 Tagen** eine erste Rückmeldung. Nach
Veröffentlichung eines Fixes nennen wir Sie im Changelog, sofern Sie nicht
anonym bleiben möchten.

## Sicherheitsmodell

Dieser Server ist **nur lesend** und benötigt **keinen API-Key**:

- Alle Tools führen HTTP-`GET`-Anfragen gegen öffentliche SRU- und
  OAI-PMH-Endpoints aus — es werden keine Daten geschrieben, verändert oder
  gelöscht.
- Es werden keine personenbezogenen Daten (PII) von Bibliotheksnutzenden
  verarbeitet oder gespeichert. Die APIs liefern ausschliesslich öffentliche
  bibliografische Metadaten.
- Der Server erzwingt ein Timeout von 30 s pro Anfrage.

### Härtung beim Deployment

- **Default-Binding ist `127.0.0.1`** (nur Loopback). Der Server hat **keine
  eingebaute Authentifizierung**.
- `--host 0.0.0.0` nur einsetzen, wenn der Server **hinter einem Reverse
  Proxy mit Authentifizierung und per-IP-Rate-Limit läuft** (z.B. nginx mit
  `limit_req` + OAuth2-Proxy). Non-Loopback-Bindings erzeugen eine
  `WARN`-Log-Zeile.
- Logs werden auf **stderr** geschrieben; Verbosity via
  `MCP_LOG_LEVEL=DEBUG|INFO|WARNING` steuerbar. Prüfen Sie Ihre
  Aufbewahrungsrichtlinie, bevor Sie `DEBUG` aktivieren.

## Geltungsbereich

Im Geltungsbereich: der Code in diesem Repository (MCP-Server, Parser und
Transport-Schicht). Ausserhalb des Geltungsbereichs: Schwachstellen in
Upstream-Diensten (SLSP / swisscovery, ETH-Bibliothek e-rara / e-periodica /
e-manuscripta) — bitte melden Sie diese direkt den jeweiligen Anbietern.

---

Dieses Projekt folgt den Konventionen des
[Swiss Public Data MCP Portfolios](https://github.com/malkreide).
