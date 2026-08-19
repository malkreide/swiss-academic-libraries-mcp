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

### Jeder Live-Test nennt seine Quelle

Jeder Test mit `@pytest.mark.live` trägt zusätzlich `@pytest.mark.quelle("…")` —
an der Funktion oder an ihrer Klasse. Die feinere Ebene gewinnt, ein Ausreisser
in einer sonst einheitlichen Klasse lässt sich also einzeln zuordnen.

```python
# In `test_20_scenarios.py` kommt die `live`-Marke aus dem modulweiten
# `pytestmark = pytest.mark.live` am Dateikopf; hier steht nur die Quelle.
@pytest.mark.quelle("e-rara")
async def test_09_erara_list_collections():
    ...


@pytest.mark.live
@pytest.mark.quelle("swisscovery")
class TestSwisscoveryLive:
    async def test_basic_search(self): ...
```

Zulässige Werte stehen in `GRUPPEN` in
[`scripts/check_gate_consistency.py`](scripts/check_gate_consistency.py) und sind
zugleich die Zeilen der Quellen-Tabelle im Kopf von
[`.github/workflows/live-tests.yml`](.github/workflows/live-tests.yml):

<!-- GRUPPEN-LISTE ANFANG (geprüft von scripts/check_gate_consistency.py) -->
`swisscovery`, `e-rara`, `e-periodica`, `e-manuscripta`, `oa_legal`,
`intl_metadata`, `quellenuebergreifend`, `library_info`
<!-- GRUPPEN-LISTE ENDE -->

`quellenuebergreifend` ist für den einen Test, der mehrere Quellen zugleich
anfasst; `library_info` für den, der gar keine externe Quelle abfragt.

**Ohne Marke wird die CI rot**, ebenso bei einem Wert, den `GRUPPEN` nicht kennt.
Das ist Absicht: `check_gate_consistency.py` zählt die Live-Tests je Quelle und
hält sie gegen jene Tabelle. Ein Test ohne Marke wäre nirgends mitgezählt, und
die Tabelle bliebe grün, obwohl sie zu wenig ausweist.

Bis zum 19.8.2026 riet der Guard die Quelle stattdessen aus Datei- und
Testnamen. Ein Test, der falsch nach einer Quelle hiess, wanderte still in die
falsche Gruppe — gemeldet wurde dann die Tabelle, also die Stelle, die stimmte.
Wer dem folgte, korrigierte eine richtige Zahl. Ein Name kann jetzt nichts mehr
verschieben; die Marke ist in `pyproject.toml` registriert.

## Sicherheit

Bitte melden Sie Sicherheitsprobleme verantwortungsvoll — siehe [SECURITY.md](SECURITY.md).

## Die Live-Suite: wann sie läuft, und wer ein rotes Ergebnis sieht

**Kadenz:** jeden Montag um 04:43 UTC, dazu jederzeit von Hand über *Actions → Live-Tests → Run
workflow*. Siehe [`.github/workflows/live-tests.yml`](.github/workflows/live-tests.yml).

**Wer es sieht:** Ein roter Lauf öffnet ein Issue mit dem Label `upstream` und dem stabilen Titel «Live-Tests gegen die echten Quellen rot (<Datum>)». Ein zweiter roter Lauf erkennt das offene Issue am Titelanfang und hängt sich an denselben Thread, statt ein zweites aufzumachen. Wird die Suite wieder grün, schliesst sich das Issue selbst.

**Vier Antworten, nicht zwei.** `scripts/classify_live_run.py` liest das JUnit-XML statt des
Exit-Codes und unterscheidet:

| Zustand | Heisst | Job | Issue |
|---|---|---|---|
| `clear` | gelaufen, grün | grün | wird geschlossen |
| `finding` | gelaufen, der Vertrag hat sich bewegt | rot | wird geöffnet |
| `upstream` | gelaufen, aber **jeder** Fehlschlag ist ein Quellen-Ausfall | rot | unberührt |
| `unknown` | nicht gelaufen (Install gescheitert, null Tests, alle übersprungen) | rot | unberührt |

Weder `unknown` noch `upstream` schliesst ein Issue: Zuzumachen hiesse zu
behaupten, der Vergleich sei gelaufen. Beide öffnen auch keins — es gäbe nichts
zu fixen.

`upstream` greift **nur**, wenn jeder einzelne Fehlschlag eindeutig ein Ausfall
ist (Timeout, 429, 503, Verbindungsabbruch). Ein Timeout neben einer gerissenen
Zusicherung bleibt `finding`, ebenso ein Fehlschlag, dessen Meldung das Skript
nicht wiedererkennt. Der Fehlermodus dieses Zustands ist nicht der falsche
Alarm, sondern das Wegerklären: Ein `upstream`, das zu breit greift, verwandelt
jeden echten Befund in ein Achselzucken.

**Ein roter Live-Lauf heisst dreierlei**, und keines davon ist aus der
Fehlermeldung abzulesen: Der Vertrag mit der Quelle hat sich geändert; die
Quelle ist gerade aus; oder der Fehler steht bei uns und die Quelle ist
unschuldig. Erst die Quelle abfragen, dann einordnen.

Das Dritte ist keine Theorie: Am 17.8.2026 waren 13 von 30 Live-Tests rot, alle
mit `RuntimeError: Event loop is closed`, während alle Quellen einwandfrei
antworteten. Der Fehler lag in unserem httpx-Client.

Bitte den Lauf lesen, bevor der Job deaktiviert wird — so stirbt dieser Check,
und er ist der einzige im Repo, der einer falschen Grundannahme über eine der
angebundenen Quellen widersprechen kann. Jeder andere Test prüft gegen eine
Fixture, und die Fixture ist aus derselben Annahme geschrieben wie der Code.

## Lizenz

Mit Ihrem Beitrag erklären Sie sich einverstanden, dass dieser unter der MIT-Lizenz lizenziert wird — siehe [LICENSE](LICENSE).

---

Dieses Projekt folgt den Konventionen des [Swiss Public Data MCP Portfolios](https://github.com/malkreide).
