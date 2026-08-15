# CLAUDE.md

Teil 1 gilt portfolioweit, Teil 2 nur für dieses Repo.

## Vor der Arbeit

Klon-Aktualität prüfen: git fetch origin main && git rev-list --count HEAD..origin/main
Ein veralteter Klon erzeugt eine rote CI, deren Ursache nicht im Diff steht.
Am 3.8.2026 zweimal passiert — beide Male fehlten genau die Commits, die
das Gate einführten, an dem der Branch scheiterte.
Gates lokal fahren, mit der GEPINNTEN ruff-Version aus der CI. Eine andere
Version meldet Abweichungen, die niemand verursacht hat.

## Tests

Gegenprobe ist Pflicht. Ein Test, der grün bleibt, wenn man die
Implementierung entfernt, prüft nichts. Jede neue Zusicherung einzeln
neutralisieren und zeigen, dass genau die zugehörigen Tests fallen.
Zwei Fallen, die beide grün blieben:
- Eine Fake-Uhr, die nur beim Schlafen vorrückt, kann eine Zusicherung über
echte Zeit nicht widerlegen.
- monkeypatch.setattr(modul.asyncio, "sleep", ...) greift ins Modul
asyncio selbst und entschärft die Mechanik im ganzen Prozess. Patche
einen Modul-Alias (_sleep = asyncio.sleep), nicht das fremde Modul.
Handgeschriebene Fixtures kodieren die Annahme des Autors und können sie
nicht widerlegen. Mindestens eine aufgezeichnete Antwort pro externem
Endpunkt, mit Aufnahmedatum.

## Wenn etwas rot ist

Roter Live-Test: erst die Quelle abfragen, dann einordnen. Nicht aus der
Fehlermeldung schliessen. Am 3.8.2026 hiess "nicht gefunden" nicht, dass der
Datensatz weg war, sondern dass die Quelle die Schreibweise ihrer Kopfzeile
gewechselt hatte — vier von sechs Datensätzen produktiv kaputt, alle
Unit-Tests grün.
PR ohne jeden Check ist selten ein Repo ohne CI, meistens ein
Merge-Konflikt: GitHub berechnet dafür keinen Merge-Commit und startet nichts.
Ein Codex-Review auf einem PR wird beantwortet oder behoben, nie ignoriert.

---

## Dieses Repo

**ruff ist auf `0.16.1` gepinnt** — in `.github/workflows/ci.yml` (Jobs `test`
und `lint`), in `[tool.hatch.envs.default]` von `pyproject.toml` und als
`rev: v0.16.1` in `.pre-commit-config.yaml`. Alle vier Stellen stimmen überein
und werden zusammen hochgezogen. Der Hook greift erst nach `pre-commit install`
im Klon; ohne diesen Schritt bleibt die CI das einzige Gate. Sein Scope ist per
`files: ^(src|tests)/` deckungsgleich mit der CI — `scripts/` prüft keins von
beidem.

**Gates, wörtlich aus `ci.yml`** (`ruff check` und `ruff format --check` haben
absichtlich denselben Scope — zwei Gates mit zwei Reichweiten sehen aus wie eins):

```bash
ruff check src/ tests/
ruff format --check src/ tests/
python -m py_compile src/swiss_academic_libraries_mcp/server.py
python -m py_compile src/swiss_academic_libraries_mcp/api_client.py
python -c "from swiss_academic_libraries_mcp.server import mcp; print('Import OK')"
PYTHONPATH=src pytest tests/ -v -m "not live"
pip-audit --strict -r <runtime-deps> --ignore-vuln PYSEC-2025-183
```

Die Matrix fährt Python 3.11, 3.12 und 3.13.

**Live-Tests sind geplant, nicht nur ausgeschlossen.** `.github/workflows/live-tests.yml`
läuft wöchentlich per cron (`43 4 * * 1`) plus `workflow_dispatch` gegen die
echten Quellen und ordnet das Ergebnis über `scripts/classify_live_run.py` in
`clear` / `finding` / `unknown` ein, statt aus dem Exit-Code zu schliessen.
DRIFT-005 ist damit erfüllt; die PR-CI schliesst `-m "not live"` weiterhin aus,
und das bleibt so. `schedule` greift nur auf dem Default-Branch — Änderungen an
der Datei wirken erst nach dem Merge, vorher von Hand auslösen.

**Fixtures sind aufgezeichnet, nicht geschrieben.** `tests/fixtures/` stammt aus
`scripts/record_fixtures.py`, Stand 2026-08-07, dokumentiert in
`tests/fixtures/PROVENANCE.md`. Nicht von Hand pflegen — neu aufzeichnen und das
Datum mitführen. Die drei OAI-PMH-Portale (e-rara, e-periodica, e-manuscripta)
sind einzeln aufgezeichnet; eines stellvertretend zu nehmen lässt genau die
Unterschiede weg, wegen derer es drei Fixtures gibt.
