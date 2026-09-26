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

**Bei einem blockierten PR nennt der Merge-Versuch den Blocker, jede Ableitung
rät.** `mergeable_state: blocked` bei grüner CI heisst: ein required Kontext
fehlt oder steht nicht auf grün. Welcher, sagt die Einstellung — und die sperrt
der Agent-Proxy mit HTTP 403, ein MCP-Werkzeug dafür gibt es nicht. Der Ausweg
ist nicht Indizienarbeit, sondern ein Merge-Versuch über die API:

```
PUT /repos/<owner>/<repo>/pulls/<n>/merge
405 Required status check "Codex hat diesen Head geprueft" is expected.
```

Der Name steht dort wörtlich so, wie er in der Branch Protection eingetragen
ist. Scheitert der Versuch, kostet er nichts.

Am 24./25.9.2026 über drei Repos vermessen, nachdem ein Gate-Workflow entfernt
worden war und seinen required Kontext ohne Berichterstatter zurückliess:

| Repo | eingetragener Kontext | Art |
|---|---|---|
| `register-mcp` | `Codex hat den PR angesehen` | Check-Run |
| `srgssr-mcp` | `review-abgeschlossen` | Check-Run |
| `fedlex-mcp` | `Codex hat diesen Head geprueft` | Check-Run |

**Warum Ableiten hier systematisch fehlgeht.** GitHub nimmt als Check-Run-Name
den **Job**-Namen, nicht den des Workflows. Zwei der drei Kontexte enthalten die
Zeichenfolge «codex-gate» nicht, obwohl sie aus `codex-gate.yml` stammen; wer in
den Einstellungen danach sucht, findet nichts und hält die Regel für abwesend.
Trug der Job kein `name:`, nimmt GitHub die Job-ID — daher `review-abgeschlossen`.

Zwei Fehlschlüsse sind dabei belegt, beide aus **einer** Beobachtung gezogen:

- Aus einem Commit-Status auf den required Kontext geschlossen. In `fedlex-mcp`
  stand der Status `codex-gate` auf dem Head auf `success` und blockierte
  nichts, während der fehlende Check-Run den Merge hielt. Am Kontroll-PR waren
  beide rot — dort ist nicht zu unterscheiden, welcher von beiden eingetragen
  ist. Genommen wurde der auffälligere.
- Aus einer Check-Run-Liste auf den required Kontext geschlossen. Die Liste
  zeigt, was **berichtet** wurde; eingetragen sein kann ein Name, der gerade
  gar nicht erscheint. Genau das ist der Fall, um den es geht.

**Ein Vorbehalt, der zur Methode gehört:** Die Absage nennt immer nur den
**ersten** fehlenden Kontext. Ist ein zweiter eingetragen, zeigt ihn erst der
nächste Versuch. Nach jeder Änderung an der Einstellung also erneut versuchen,
bis der Merge durchgeht oder ein neuer Name fällt.

Die Kosten der Ableitung sind gemessen: ein Arbeitstag, an dem der PR-Text den
falschen Namen trug und in den Einstellungen nach einer Zeichenfolge gesucht
wurde, die dort nicht steht.

**`get_status` sagt in diesem Portfolio nichts über die CI — und sagt es im
Wortlaut «pending».** Am 17.9.2026 auf zwei Commits gemessen, beide mit fünf
grün abgeschlossenen Checks:

```
{"state": "pending", "sha": "ec5bc0a…", "total_count": 0, "statuses": []}
{"state": "pending", "sha": "3dfe64e…", "total_count": 0, "statuses": []}
```

`ec5bc0a` war zum Abfragezeitpunkt seit über zwanzig Minuten fertig, `3dfe64e`
längst gemergt. Kein Transient also: zweimal derselbe Wert, beide Male auf einem
abgeschlossenen Commit. `total_count: 0` heisst, dass es **keine
Legacy-Commit-Statuses gibt** — und `pending` steht daneben, obwohl es nichts
gibt, worauf gewartet wird. Dieselben Commits liefern über `get_check_runs`
fünf Einträge auf `success`; dort steht die Auskunft, die man sucht.

Die Falle ist die Wortwahl: `pending` liest sich als «CI läuft noch». Wer
darauf wartet, wartet auf etwas, das nie kommt — und wer es als «noch nicht
grün» einordnet, hält einen fertigen PR für unfertig. Das ist die Umkehrung der
`comments: 1`-Falle weiter unten: dort trägt eine Zahl drei Bedeutungen, hier
trägt ein Wort eine, die es nicht hat.

Was die Messung **nicht** hergibt, und das ist hier die halbe Geschichte:

- **Warum** der Endpunkt `pending` sagt. Dass es der Vorgabewert für «keine
  Statuses» sei, ist die naheliegende Erklärung und bleibt eine Vermutung —
  die API-Referenz wurde nicht nachgelesen.
- Wie er sich verhält, wo Legacy-Statuses wirklich benutzt werden. In diesem
  Repo tut das keines; die übrigen Repos des Portfolios wurden nicht geprüft.
- Ob `get_check_runs` die einzige verlässliche Quelle ist. Geprüft ist, dass sie
  *eine* ist — andere Endpunkte wurden nicht gegengehalten.

**Ein 4xx ist kein Nein.** Am 29.8.2026 antwortete `past-publications` in
`swiss-procurement-mcp` auf jede Publikation mit Losen mit HTTP 400. Daraus war
geschlossen worden, die Quelle verweigere diese Auskunft; der Befund stand
datiert im Fixture-Nachweis, ein Test bestätigte ihn, alles blieb grün. Die
Spec desselben Endpunkts führt einen als *optional* deklarierten Parameter
`lotId` — für Publikationen mit Losen ist er Pflicht. Mit ihm antwortet
dieselbe Publikation mit 200. Ein Projekt trug sieben Vorgängerpublikationen,
die der Server als «Quelle nicht erreichbar» wegwarf.

Drei Handgriffe daraus:

- **Die Parameterliste der Spec durchgehen, bevor ein Statuscode eingeordnet
  wird.** «Optional» heisst dort oft «optional für die Mehrheit».
- **Einer deterministischen Absage keinen Wiederholungsrat geben.** «Nicht
  erreichbar, bitte später erneut» ist bei einem 400 falsch und liest sich für
  das Modell wie eine Störung. Den Status mitführen und den fehlenden
  Parameter benennen — den Status, nicht den Antwortkörper.
- **Beide Antworten aufzeichnen, mit und ohne den Parameter.** Eine
  Aufzeichnung nur des Fehlschlags kann nicht zeigen, dass er vermeidbar war;
  dass nur der 400er aufgezeichnet war, ist der Grund, warum der falsche
  Befund nicht auffiel.

**Und ein 403 ist gar keine Auskunft.** Am 29.8.2026 sollten für 42 Repos die
Dependabot-Labels nachgemessen werden. Alle 13 Abfragen des ersten Stapels
kamen zurück als:

```
Failed to find label: API rate limit already exceeded for user ID 8864492.
```

Der gefährliche Teil steht vorn: Das Werkzeug verpackt eine Sperre als
Fund-Fehlschlag. Wer die Zeile überfliegt oder nur auf ein leeres Ergebnis
prüft, zählt 39 Repos als «Label fehlt» und hat seine eigene Erschöpfung
gemessen. Das Limit hängt am Konto, nicht am Repo — derselbe Vormittag hatte
es mit 42 eröffneten und 42 gemergten PRs verbraucht.

Das ist der Absatz darüber, andersherum gelesen: dort war ein 400 eine echte,
wiederholbare Antwort und galt als Störung; hier ist eine Störung als Antwort
verpackt. Entscheidend ist nie der Statuscode, sondern ob die Quelle überhaupt
geantwortet hat.

- **Positivkontrolle im selben Repo.** Ein «nicht gefunden» wird erst dadurch
  zur Messung, dass eine gleichzeitige Abfrage etwas findet.
- **Die Messung entlang der Sperre teilen.** `raw.githubusercontent.com` ist
  ein CDN und nicht die REST-API. Um 11:19:27 UTC lieferte es für
  `register-mcp` HTTP 200, während die Label-Abfrage desselben Repos in
  derselben Minute die Sperre meldete. Alle 42 `dependabot.yml` kamen so
  durch, während die Label-Hälfte stand.
- **Am Token vorbei geht es nicht.** Beide Umwege enden am Agent-Proxy, und
  jeder mit einer eigenen irreführenden Begründung. `api.github.com` ohne
  Zugangsdaten:

  ```
  GitHub access is not enabled for this session. An org admin must connect
  the Claude GitHub App for this organization.
  ```

  Das ist keine Aussage über die Organisation, sondern das, was ohne Token
  kommt. Wer ihr folgt, sucht einen Admin für ein Problem, das keiner hat.
  Die HTML-Seite `github.com/<owner>/<repo>/labels` fällt ebenfalls, aber
  anders:

  ```
  This GitHub API path is not available: sessions are bound to their
  configured repositories. Use repository-scoped endpoints
  (repos/{owner}/{repo}/...).
  ```

  Der Proxy behandelt also auch `github.com` als API-Pfad; die zweite Meldung
  klingt nach einem Scope-Problem und ist doch nur dieselbe Sackgasse. Den
  Token aus der Umgebung in einen curl-Header zu setzen, blockiert der
  Klassifikator. Ob es überhaupt hülfe, ist offen: die Sperre nennt ein
  Nutzerkonto, und ob der Token zu diesem gehört, wurde nie geprüft.
- **Die Sperre gilt nicht dem Dienst, sondern dem Zugangspfad.** Unmittelbar
  nachdem eine Abfrage der Checks eines PR sauber durchlief, meldete die
  Label-Abfrage weiter die Sperre. Von einem blockierten Werkzeug also nicht
  auf «GitHub ist zu» schliessen — und umgekehrt eine gelungene Abfrage nicht
  als Entwarnung für die gesperrte nehmen.

Wann die Sperre fällt, geben diese Beobachtungen nicht her. Die Meldung nennt
keinen Zeitpunkt, und die `X-RateLimit`-Kopfzeilen sind hinter dem Proxy nicht
zu sehen. Belegt sind drei gesperrte Zeitpunkte — 11:14, 11:16 und 11:19 UTC.
Wer daraus eine Dauer macht, hat sie erfunden.

**Dieselbe Falle bei einer Konfigurationsoption: die Vorgabe lesen, bevor man
einen Schlüssel für wirkungslos hält.** Am 29.8.2026 fielen die
`labels:`-Zeilen aus den `dependabot.yml` des Portfolios, begründet mit
«Dependabot legt Labels nicht an». Eine Messung danach zeigte, dass
`dependencies` in 36 von 42 Repos sehr wohl existiert, 35 davon mit GitHubs
Standardbeschreibung. Das las sich zuerst wie ein Beleg, dass die Aktion
falsch war.

Die Optionsreferenz kehrt es um:

```
Dependabot creates these default labels automatically, as necessary in
your repository.

If you define more than one package manager, an additional label for the
ecosystem or language is added to each pull request.

The labels specified are used instead of the default labels.
```

Ohne `labels:` vergibt Dependabot also `dependencies` — und, sobald mehr als
ein Paketmanager deklariert ist, zusätzlich ein Ökosystem-Label — und legt sie
selbst an; eine eigene Liste **ersetzt** diesen Satz, und «if any of these
labels is not defined in the repository, it is ignored». Die Zeile war nicht
wirkungslos — sie tauschte einen sich selbst pflegenden Vorgabesatz gegen eine
starre Liste.

**Die Bedingung nicht weglassen.** Bei nur einem Paketmanager steht das
Ökosystem-Label gar nicht zu; wer es dort trotzdem erwartet, schreibt genau
den Fehlbefund auf, gegen den dieser Abschnitt geschrieben ist — der Abschnitt
liefe an sich selbst vorbei. Im Portfolio deklariert jede `dependabot.yml`
zwei (`pip` und `github-actions`), die Bedingung ist hier also überall
erfüllt; anderswo nicht unbedingt. Aufgefallen ist die fehlende Bedingung
nicht beim Schreiben, sondern durch einen Codex-Review auf
`swiss-environment-mcp` PR #113 — vierzehn Sekunden vor dem Merge desselben
PR.

Was das kostet, ist an `openlex-mcp` gemessen: zwei Ökosysteme deklariert,
also stünden `dependencies` **und** ein Ökosystem-Label zu; vorhanden ist nur
das erste, `github-actions` und `github_actions` fehlen beide (Kontrolle `bug`
vorhanden). `register-mcp` ist die Gegenprobe: dort existieren alle vier
deklarierten Namen mit handgeschriebener Beschreibung, die Liste ist gewollt
und vollständig.

**Dreimal falsch eingeordnet, in drei Richtungen.** Erst die Zeile für bloss
wirkungslos gehalten. Dann die gefundenen Labels für einen Widerspruch. Dann,
auf denselben Fund gestützt, einen richtigen PR geschlossen mit dem Argument,
das Label existiere ja — obwohl es existiert, *weil* die Vorgabe es anlegt.
Der dritte Fehler ist der teuerste, weil er wie eine Messung aussah.

Was die Messung **nicht** hergibt: wer die 36 Labels angelegt hat. Die
Referenz sagt, Dependabot tue es; die Objekt-IDs liegen aber so dicht
beieinander, dass sie eher aus einem Stapellauf stammen. Beides passt zum
Befund, keines ist belegt — die Herkunft blieb ungemessen.

Beim Aufräumen gilt deshalb dieselbe Frage wie bei `lotId`: Was ist die
*Vorgabe*, wenn man das Ding weglässt — nicht bloss, ob der aktuelle Wert
etwas bewirkt.

**`results[0]` ist nur so verlässlich wie die Zusicherung danach.** Pinnt die
Abfrage einen bekannten Datensatz, ist der erste Treffer eine Drift-Wache und
in Ordnung. Hängt die Zusicherung dagegen davon ab, *welche* Variante die
Quelle heute zuoberst hat, prüft der Test den Tag: am 25.8.2026 rot, weil die
neueste Zürcher Publikation zufällig Lose hatte, am 26.8. grün, ohne dass sich
etwas geändert hätte. Den Fall gezielt wählen und beide Zweige fahren.

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

**ruff ist exakt gepinnt** — im `dev`-Extra von `pyproject.toml` und,
weil pre-commit `pyproject.toml` nicht lesen kann, ein zweites Mal als
`rev:` in `.pre-commit-config.yaml`. Die Version steht an diesen beiden Stellen,
nicht in diesem Text. Beide werden zusammen hochgezogen.

«Zusammen» ist der ganze Satz, und am 17.9.2026 ist er einmal nicht eingehalten
worden: Dependabot-PR #105 zog `pyproject.toml` auf `0.16.7` und liess die
anderen drei Stellen stehen. `check_gate_consistency.py` meldete das, `lint` und
`test (3.11)` standen seit 04:54 UTC auf `failure` — gemergt wurde um 18:00:04
trotzdem, und danach war der Default-Branch rot. Ein Dependabot-PR auf ruff ist
deshalb nie ein Ein-Zeilen-PR: er braucht die drei Nachzüge im selben Commit.

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

Seit diesem Commit hält er zusätzlich die **Wanduhr**, über die allein ein
nackter `TimeoutError` entsteht. Die übrigen Typnamen in `UPSTREAM_TYPEN`
erreichen eine Meldung über den generischen Zweig von `handle_api_error`;
dieser eine nicht. `http_get_with_retry` spannt mit `asyncio.timeout` eine
Schranke über den Versuch, weil httpx' Read-Timeout mit jedem Chunk von vorn
beginnt — und reicht den Fehler roh durch. Wer die Funktion direkt ruft statt
über ein MCP-Tool, und die `intl_metadata`-Live-Tests tun genau das, sieht den
nackten Ausnahmenamen, nie eine deutsche Meldung. Geprüft wird der **Aufruf**
per AST, nicht der Text: In `api_client.py` steht `asyncio.timeout` als
Erklärung direkt neben der Schranke, und eine Textsuche hielte sie noch für
gespannt, nachdem sie entfernt wurde.

Anlass war der Live-Lauf vom 14.9.2026. Neun Fehlschläge, acht davon e-rara mit
HTTP 403, einer der Budget-Timeout aus `search_preprints` — erkannt wurde als
Ausfall **kein einziger**. Der 403 ist dabei richtig eingeordnet und bleibt es:
Er ist vieldeutig (eine Sperre vor der Anwendung, aber ebenso gut eine neu
verlangte Authentisierung, und das wäre ein Vertragsbruch), und `upstream` ist
der Zustand, dessen Fehlermodus das Wegerklären ist. Der Timeout dagegen war
eine echte Lücke, und die unangenehme Sorte: der einzige Timeout, den dieses
Repo selbst erzeugt, war der einzige, den der Wächter nicht kannte.

Seit dem 23.9.2026 hat der 403 in `handle_api_error` eine eigene, längere
Meldung — ohne Wiederholungsrat, mit Ausweg. Länger heisst hier riskanter:
`_ist_ausfall` prüft Teilstrings, und ein beiläufiges Ausfall-Muster in diesem
Text machte jede Sperre still zu `upstream`. Das hält `test_403_bleibt_finding`
fest, gebaut aus der **echten** Funktion. Die Aufzeichnung
`live-report-403.xml` allein könnte es nicht: Sie friert den Text vom
Aufnahmetag ein und bliebe grün, wenn jemand die Meldung später umformuliert —
in der Gegenprobe genau so geschehen.

Dass es überhaupt zu belegen war, ist Glück gewesen. `live-report.xml` starb mit
dem Runner, und die 40 Zeilen `tail` im Issue tragen die Meldungen nicht, die
der Klassifikator liest; nachweisbar wurde der Befund erst, als der Ausfall sich
nachstellen liess. Seit diesem Commit hebt `live-tests.yml` den Report als
Artefakt auf — die Einordnung behauptet etwas über den Lauf, und ohne den Report
lässt sich das nicht nachprüfen.

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
