# Beitragen

[🇬🇧 English Version](CONTRIBUTING.md)

Vielen Dank für Ihr Interesse an diesem Projekt! Beiträge sind willkommen.

## Wie kann ich beitragen?

**Fehler melden:** Erstellen Sie ein [Issue](../../issues) mit einer klaren Beschreibung des Problems, Schritten zur Reproduktion und der erwarteten vs. tatsächlichen Ausgabe.

**Feature vorschlagen:** Beschreiben Sie den Use Case, idealerweise mit einem Bezug zum Schweizer Bibliotheks- und Bildungskontext (Quellenrecherche, Unterrichtsvorbereitung, Archivarbeit etc.).

**Code beitragen:**

1. Forken Sie das Repository
2. Erstellen Sie einen Feature-Branch: `git checkout -b feature/mein-feature`
3. Installieren Sie die Dev-Abhängigkeiten: `pip install -e ".[dev]"`
4. Schreiben Sie Tests für Ihre Änderungen
5. Lint prüfen: `ruff check src/ tests/`
6. Commit mit aussagekräftiger Nachricht: `git commit -m "feat: e-manuscripta Volltextsuche hinzufügen"`
7. Pull Request erstellen

## Code-Standards

- Python 3.11+, Ruff für Linting
- Docstrings auf Englisch (für internationale Kompatibilität)
- Kommentare und Fehlermeldungen dürfen Deutsch oder Englisch sein
- Alle MCP-Tools müssen `readOnlyHint: True` setzen (nur lesender Zugriff)
- Pydantic-Modelle für alle Tool-Inputs

## Tests

Dieses Projekt benötigt **keinen API-Key** für Unit-Tests:

```bash
# Unit-Tests (kein Netzwerk erforderlich)
PYTHONPATH=src pytest tests/ -m "not live"

# Live-Smoke-Tests (Internetzugang erforderlich)
PYTHONPATH=src pytest tests/ -m "live"
```

Neue Tools müssen mit mindestens einem Unit-Test und einem Live-Smoke-Test abgedeckt sein. Committen Sie **niemals** persönliche Daten oder Zugangsdaten.

## Sicherheit

Bitte melden Sie Sicherheitsprobleme verantwortungsvoll — siehe [SECURITY.md](SECURITY.md).

## Lizenz

Mit Ihrem Beitrag erklären Sie sich einverstanden, dass dieser unter der MIT-Lizenz lizenziert wird — siehe [LICENSE](LICENSE).

---

Dieses Projekt folgt den Konventionen des [Swiss Public Data MCP Portfolios](https://github.com/malkreide).
