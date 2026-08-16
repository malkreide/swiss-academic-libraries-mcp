# CLAUDE.md

Teil 1 gilt portfolioweit, Teil 2 nur für dieses Repo.

## Vor der Arbeit

Klon-Aktualität prüfen — Standard-Branch ermitteln, nicht `main` annehmen.
Bewusst ohne `bash`-Fence: `scripts/check_gate_consistency.py` verlangt, dass
jede Zeile in einer Shell-Fence einem Kommando aus `ci.yml` entspricht. Das
hier ist kein CI-Gate, sondern ein Handgriff davor.

```
B=$(git ls-remote --symref origin HEAD | sed -n 's|^ref: refs/heads/\([^[:space:]]*\).*|\1|p')
git fetch origin "${B:?Standard-Branch nicht ermittelbar}" &&
  git rev-list --count HEAD..FETCH_HEAD
```

Drei Server im Portfolio heissen ihren Standard-Branch `master`
(`openlex-mcp`, `swiss-courts-mcp`, `swisstopo-mcp`); dort scheitert ein fest
verdrahtetes `origin/main` mit «couldn't find remote ref main». Wer das für ein
Netzproblem hält, arbeitet weiter auf genau dem veralteten Klon, vor dem dieser
Absatz warnt. Den `:?`-Schutz nicht weglassen: Bei leerem `B` fetcht git still
den Remote-HEAD und endet mit 0.

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

**ruff ist auf `0.16.1` gepinnt** — im `dev`-Extra von `pyproject.toml` und,
weil pre-commit `pyproject.toml` nicht lesen kann, ein zweites Mal als
`rev: v0.16.1` in `.pre-commit-config.yaml`. Beide werden zusammen hochgezogen.

`.github/workflows/ci.yml` pinnt **nicht** mehr selbst. Vorher tat es das an
zwei Stellen, und `[tool.hatch.envs.default]` zählte seine Abhängigkeiten
ebenfalls eigenständig auf — vier Stellen, die zwar übereinstimmten, deren
Gleichstand aber nichts erzwang: Der CI-Schritt lief nach dem Install und
überschrieb ihn, eine Abweichung im Extra wäre also nur lokal aufgefallen. Die
Hatch-Umgebung zieht das Extra jetzt über `features = ["dev"]`, und im
`lint`-Job steht `pip install -e ".[dev]"` an der Stelle des früheren Pins —
dort war er die einzige Installation, der Schritt ist also nicht redundant.

`check_gate_consistency.py` prüft deshalb zweierlei: dass die zwei
verbleibenden Stellen übereinstimmen, **und** dass `ci.yml` keinen eigenen Pin
zurückbekommt. Nur das Erste wäre zu schwach — ein zurückgekehrter CI-Pin
stimmt ja mit den anderen überein und hebelt sie trotzdem aus. Der Hook greift erst nach `pre-commit install`
im Klon; ohne diesen Schritt bleibt die CI das einzige Gate. Sein Scope ist per
`files: ^(src|tests|scripts)/` deckungsgleich mit der CI und mit den
hatch-Skripten `lint`/`fmt`. Wer einen Scope ändert, ändert alle — das prüft
`scripts/check_gate_consistency.py` in der CI und meldet auch, wenn es seine
Stellen nicht mehr findet. Dieser Absatz wird mitgeprüft, er ist eine davon.

Vor dem Lauf `ruff --version` prüfen: ein älteres ruff früher im `PATH`
schlägt den Pin, ohne dass der Install etwas meldet.

**Gates, wörtlich aus `ci.yml`** (`ruff check` und `ruff format --check` haben
absichtlich denselben Scope — zwei Gates mit zwei Reichweiten sehen aus wie eins):

```bash
ruff check src/ tests/ scripts/
ruff format --check src/ tests/ scripts/
python -m py_compile src/swiss_academic_libraries_mcp/server.py
python -m py_compile src/swiss_academic_libraries_mcp/api_client.py
python -c "from swiss_academic_libraries_mcp.server import mcp; print('Import OK')"
PYTHONPATH=src pytest tests/ -v -m "not live"
python scripts/check_gate_consistency.py
pip-audit --strict -r <runtime-deps> --ignore-vuln PYSEC-2025-183
```

„Wörtlich" ist hier eine Zusicherung, keine Absicht: `check_gate_consistency.py`
hält jede Zeile dieses Blocks gegen `ci.yml` und meldet beide Richtungen — eine
Zeile, die so nicht läuft, und ein Gate der CI, das hier fehlt.

Die Matrix fährt Python 3.11, 3.12 und 3.13 — aber nicht alle Gates liegen im
`test`-Job. `ruff format --check`, `check_gate_consistency.py` und `pip-audit`
stehen im Job `lint`, und der hat keine Matrix: er läuft auf 3.11. Ein grünes
3.12/3.13 sagt über diese drei nichts aus. Ein `fail-fast: false` steht nicht
da.

**Was `check_gate_consistency.py` nicht abdeckt: den Versionsabgleich.** Es
hält ruff-Pin, Gate-Scope und diesen Block gegen `ci.yml` — aber
`pyproject.toml` und `server.json` prüft es nicht gegeneinander. Beide stehen
heute auf `1.2.0`, gehalten wird das von nichts; die meisten Schwester-Server
fahren dafür `scripts/check_version_sync.py`, das es hier nicht gibt. Beim
Anheben also beide Stellen von Hand.

Gerade hier ist diese Lücke leicht zu übersehen, weil dieses Repo mehr Guards
hat als jedes andere im Portfolio. Dass etwas geprüft *aussieht*, heisst nicht,
dass diese eine Sache geprüft wird.

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
