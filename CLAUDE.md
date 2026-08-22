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
Seit diesem Commit meldet das ein SessionStart-Hook beim Sessionstart von
selbst (`.claude/hooks/check-clone-freshness.sh`, Begründung und Gegenproben
in `.claude/hooks/README.md`). Er ersetzt den Handgriff oben nicht, sondern
erinnert daran: Er meldet nur und ändert nichts, und er schweigt, sobald das
Netz klemmt — ein Hook, der bei Netzproblemen die Arbeit anhält, wird
abgeschaltet und schützt danach gar nichts. Wer nichts sieht, weiss deshalb
nicht, dass der Klon aktuell ist; wer etwas sieht, weiss, dass er es nicht ist.
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

## Wenn Codex gar nicht erst hinsieht

Die Zeile oben unterstellt, dass es einen Befund geben *kann*. Das ist nicht
immer so, und man sieht es dem PR nicht an.

Am 21.8.2026 war das Code-Review-Kontingent zwischen 08:41 und 09:48
aufgebraucht — davor echte Reviews, danach in 30 Repos nur noch:

```
You have reached your Codex usage limits for code reviews.
```

Bis mindestens zum 22.8. um 08:30, also 23 Stunden später, blieb es dabei. In
der Zwischenzeit sind 32 PRs mit formal erfülltem Häkchen gemergt worden, ohne
dass jemand hineingesehen hat.

Drei Gründe, warum Codex schweigt, und nur einer davon ist harmlos:

- **Kein Befund** — dann reagiert er mit 👍 und schreibt nichts.
- **Der PR ist ein Draft** — darauf läuft Codex nicht an.
- **Das Kontingent ist weg** — dann schreibt er die Meldung oben.

«Kein Kommentar» heisst also nicht «geprüft und sauber». Unterscheiden lässt es
sich an der Form: Ein echter Review ist ein Review-Objekt («💡 Codex Review»,
mit Commit-Angabe), die Limit-Meldung ein gewöhnlicher Issue-Kommentar. Das
sind zwei verschiedene Abfragen — `get_reviews` gegen `get_comments`; wer nur
eine davon nimmt, übersieht die andere Hälfte. Genau so ist die Limit-Meldung
zuerst durchgerutscht.

Portfolio-weit nachsehen:

```
search_pull_requests: user:malkreide commenter:chatgpt-codex-connector[bot] updated:>=<Datum>
```

Findet nur, wo er *kommentiert* hat. Repos ohne PR-Aktivität tauchen nicht auf
— das ist kein Beleg, dass dort geprüft wurde.

Zweiter Weg, den Prüfer zu verlieren, ganz ohne Kontingentproblem: zu schnell
mergen. Am 21./22.8. lagen zwischen «ready for review» und Merge mehrfach drei
bis fünf Sekunden. Codex wird beim Umschalten von Draft auf ready ausgelöst und
braucht danach Zeit; wer sofort mergt, hat das Häkchen gesetzt und den Review
nicht abgewartet.

Das Kontingent hängt am Konto, nicht am Repo, und Code-Reviews haben einen
eigenen Topf — nur GitHub-getriggerte Reviews zählen hinein. ChatGPT-Pläne
fahren ein rollendes Fünf-Stunden-Fenster plus Wochenlimits; welches greift,
steht im Codex-Dashboard. Zeigt das freies Kontingent, während Reviews weiter
scheitern, ist das ein bekannter Fehler bei mehreren verbundenen Konten — dann
den GitHub-Connector in den Codex-Einstellungen trennen und neu verbinden.

---

## Wenn zwei Agenten dasselbe tun

Vor dem Anlegen eines Branches mit vorgegebenem Namen prüfen, ob es ihn schon
gibt — wieder ohne `bash`-Fence, aus demselben Grund wie oben:

```
git ls-remote --heads origin claude/<name> | wc -l
```

Steht dort `1`, arbeitet jemand anderes daran — mit Schreibrecht auf denselben
Ref.

Ein PR mit leerem Diff wird geschlossen, nicht gemergt. Der Test ist
`get_files` auf dem PR: kommt `[]` zurück, ändert er nichts. Ein grüner Check
sagt dazu nichts — die CI prüft den Head, nicht die Differenz zur Basis.

Am 21.8.2026 liefen zwei Sessions dieselbe Aufgabe über 45 Repos, auf den
Branches `claude/codex-review-audit-templates-9sn6mx` und
`claude/codex-review-audit-7ioh56`. Wo die eine zuerst nach `main` kam, wurde
`main` in den Branch der anderen gemergt und der add/add-Konflikt zugunsten
von `main` aufgelöst. Übrig blieben 14 PRs, die durch sämtliche Gates grün
liefen und nichts enthielten; sie wurden gemergt und hinterliessen leere
Merge-Commits. Mit den zwei Folge-PRs, die aus demselben Grund gegenstandslos
waren, waren 16 der 59 PRs jenes Tages reine Reibung.

Dieselbe Klasse wie der handgeschriebene Stub, der denselben Feldnamen annahm
wie der Code: Nichts ist rot, weil nichts geprüft wird, worauf es ankommt.

## Dieses Repo

**ruff ist auf `0.16.3` gepinnt** — im `dev`-Extra von `pyproject.toml` und,
weil pre-commit `pyproject.toml` nicht lesen kann, ein zweites Mal als
`rev: v0.16.3` in `.pre-commit-config.yaml`. Beide werden zusammen hochgezogen.

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
python scripts/check_ruff_pin.py
ruff check src/ tests/ scripts/
ruff format --check src/ tests/ scripts/
python -m py_compile src/swiss_academic_libraries_mcp/server.py
python -m py_compile src/swiss_academic_libraries_mcp/api_client.py
python -c "from swiss_academic_libraries_mcp.server import mcp; print('Import OK')"
PYTHONPATH=src pytest tests/ -v -m "not live"
python scripts/check_version_sync.py
python scripts/check_gate_consistency.py
pip-audit --strict -r <runtime-deps> --ignore-vuln PYSEC-2025-183
```

„Wörtlich" ist hier eine Zusicherung, keine Absicht: `check_gate_consistency.py`
hält jede Zeile dieses Blocks gegen `ci.yml` und meldet beide Richtungen — eine
Zeile, die so nicht läuft, und ein Gate der CI, das hier fehlt.

Die Matrix fährt Python 3.11, 3.12 und 3.13 — aber nicht alle Gates liegen im
`test`-Job. `ruff format --check` und `check_gate_consistency.py` stehen im Job
`lint`, `pip-audit` in einem **dritten** Job namens `security`; keiner der
beiden hat eine Matrix, beide laufen auf 3.11. Ein grünes 3.12/3.13 sagt über
diese drei nichts aus. Ein `fail-fast: false` steht nicht da.

Die Jobzuordnung prüft `check_gate_consistency.py` **nicht** — es hält nur, dass
jede Zeile des Blocks irgendwo in `ci.yml` läuft. Genau deshalb stand hier
zwischenzeitlich `pip-audit` im falschen Job, und kein Gate wurde davon rot.

**Zwei Guards, zwei Gegenstände — nicht verwechseln.**
`check_gate_consistency.py` hält ruff-Pin, Gate-Scope und diesen Block gegen
`ci.yml`. Den Versionsabgleich deckt es **nicht** ab; dafür läuft seit diesem
Commit `check_version_sync.py` daneben und hält `pyproject.toml` gegen
`server.json` und die README-Badges.

Seit diesem Commit hält `check_gate_consistency.py` zusätzlich die
Quellen-Aufzählung im Kopfkommentar von `.github/workflows/live-tests.yml`
gegen das, was `src/` wirklich anbindet — gelesen aus Modulkonstanten
(`*_URL`, `*_BASE`) **und** den `base_url`-Einträgen der Repositorien-Tabelle
in `oa_legal`; wer nur die Konstanten liest, übersieht drei von neun Quellen.
Bewusst nicht «jedes `https://` in `src/`»: Das fängt Doku-Links mit ein
(github.com, doi.org, www.crossref.org …) und zwänge dazu, Homepages als
Quellen einzutragen. Zusätzlich meldet es, wenn Job-Name oder Issue-Präfix
eine einzelne Quelle herausgreifen.

Seit diesem Commit hält es auch die **Zahlen** der Tabelle — die Testzahl je
Quelle — gegen die tatsächlichen `-m live`-Tests, gezählt per AST (das Skript
bleibt stdlib-only und läuft im `lint`-Job, wo pytest nichts zu suchen hat).
Beide `live`-Schreibweisen des Repos werden gelesen: modulweites `pytestmark`
und `@pytest.mark.live` an Klasse oder Funktion.

Die Zuordnung Test → Quelle steht **am Test**: Jeder `live`-Test trägt
`@pytest.mark.quelle("…")`, an der Funktion oder an ihrer Klasse (die feinere
Ebene gewinnt). Fehlt die Marke oder nennt sie einen Wert, der nicht in
`GRUPPEN` steht, ist das ein Befund. Bis zum 19.8.2026 riet der Guard die
Quelle stattdessen aus Datei- und Testnamen; ein Test, der falsch nach einer
Quelle hiess, wanderte still in die falsche Gruppe, und gemeldet wurde dann
die Tabelle — also die Stelle, die stimmte. Ein Name kann jetzt nichts mehr
verschieben. Die Marke ist in `pyproject.toml` registriert.

Seit diesem Commit hält der Guard zusätzlich die Werteliste in **beiden**
CONTRIBUTING-Dateien gegen `GRUPPEN` — beide Richtungen, damit weder eine neue
Gruppe unerwähnt bleibt noch ein Wert dokumentiert ist, den es nicht gibt. Die
Liste ist von `<!-- GRUPPEN-LISTE ANFANG/ENDE -->` eingefasst (HTML-Kommentare:
im gerenderten Markdown unsichtbar, für den Guard sichtbar); ohne die Marker
meldet er das, statt sich abzuschalten. Beide Sprachen, weil eine zweisprachige
Doku, die nur einsprachig gepflegt wird, schlimmer ist als eine einsprachige:
Sie sieht vollständig aus.

Seit diesem Commit hält er ausserdem die **Ausfall-Muster** des Klassifikators
gegen den Code, aus dem sie stammen: Die Texte, an denen `classify_live_run.py`
einen Quellen-Ausfall erkennt, gehören nicht ihm, sondern `handle_api_error` in
`api_client.py` (und einer Stelle in `oa_legal.py`). Formuliert dort jemand um,
wird kein Lauf falsch grün — er wird `finding` statt `upstream`, die
konservative Richtung. Aber die vierte Antwort wäre für diesen Fall still tot,
und ein Wächter, der nie mehr anschlägt, sieht aus wie einer, bei dem nichts
vorfällt. Docstrings zählen dabei **nicht** als Vorkommen: Eine Meldung, die
nur noch in einer Beschreibung steht, gibt es im Code nicht mehr. Die
Ausnahme-Typnamen (`ConnectTimeout` und Verwandte) stehen nirgends als Text —
sie erreichen eine Meldung nur über den generischen Zweig
`Unerwarteter Fehler: {type(e).__name__}`, und stellvertretend wird der geprüft. Die Tabelle
ist von `# QUELLEN-TABELLE ANFANG/ENDE` eingefasst; fehlen die Marker, meldet
der Guard das, statt sich still abzuschalten. Der Fliesstext drumherum zählt
nicht als Aufzählung — sonst ginge eine Quelle als «genannt» durch, weil sie
zufällig im historischen Hinweis vorkommt. Anlass war der Workflow, der bis zum
19.8.2026 «gegen api.crossref.org» hiess, während er neun Hosts abfragt: Der
rote Lauf vom 17.8.2026 schickte damit jeden, der den Titel las, zu crossref
— gerissen waren swisscovery, e-rara, e-periodica und e-manuscripta.

Die zwei greifen ineinander: Wer einen Gate-Schritt in `ci.yml` ergänzt und
den Block oben nicht nachzieht, macht `check_gate_consistency.py` rot — beim
Einbau des Versions-Gates ist genau das passiert, und der Guard hat es
gemeldet, bevor die CI es tat.

**Live-Tests sind geplant, nicht nur ausgeschlossen.** `.github/workflows/live-tests.yml`
läuft wöchentlich per cron (`43 4 * * 1`) plus `workflow_dispatch` gegen die
echten Quellen und ordnet das Ergebnis über `scripts/classify_live_run.py` in
`clear` / `finding` / `upstream` / `unknown` ein, statt aus dem Exit-Code zu
schliessen. `upstream` (seit diesem Commit) greift nur, wenn **jeder**
Fehlschlag ein Quellen-Ausfall ist — ein Timeout neben einer gerissenen
Zusicherung bleibt `finding`, sonst wäre der neue Zustand ein Weg, echte
Befunde wegzuerklären.
DRIFT-005 ist damit erfüllt; die PR-CI schliesst `-m "not live"` weiterhin aus,
und das bleibt so. `schedule` greift nur auf dem Default-Branch — Änderungen an
der Datei wirken erst nach dem Merge, vorher von Hand auslösen.

**Fixtures sind aufgezeichnet, nicht geschrieben.** `tests/fixtures/` stammt aus
`scripts/record_fixtures.py`, Stand 2026-08-07, dokumentiert in
`tests/fixtures/PROVENANCE.md`. Nicht von Hand pflegen — neu aufzeichnen und das
Datum mitführen. Die drei OAI-PMH-Portale (e-rara, e-periodica, e-manuscripta)
sind einzeln aufgezeichnet; eines stellvertretend zu nehmen lässt genau die
Unterschiede weg, wegen derer es drei Fixtures gibt.
