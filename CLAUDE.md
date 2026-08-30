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
  als Entwarnung für die gesperrte nehmen. Das ist dieselbe Asymmetrie wie
  bei der verschwundenen Codex-Meldung weiter unten.

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

## Wenn Codex gar nicht erst hinsieht

Die Zeile oben unterstellt, dass es einen Befund geben *kann*. Das ist nicht
immer so, und man sieht es dem PR nicht an.

Am 21.8.2026 war das Code-Review-Kontingent zwischen 08:41 und 09:48
aufgebraucht — davor echte Reviews, danach in 30 Repos nur noch:

```
You have reached your Codex usage limits for code reviews.
```

Wie lange die Sperre dauerte, geben die Beobachtungen nur als Spanne her. Vier
Zeitpunkte sind belegt: letzter gelungener Review am 21.8. um 08:41, erste
Limit-Meldung um 09:48, letzte beobachtete Limit-Meldung am 22.8. um 11:03,
erste *andere* Meldung am 23.8. um 08:22.

Zwischen erster und letzter Limit-Meldung liegen **25 h 15 min**. Das ist der
Abstand zweier Fehlschläge, nicht die Dauer einer Sperre. Wer ihn Untergrenze
nennt, hat die durchgehende Erschöpfung schon vorausgesetzt, die er belegen
soll: Öffnete sich das Fenster zwischendurch und schloss es sich durch neue
Auslöser wieder, waren es zwei kurze Sperren und nie eine von 25 Stunden.
Untergrenze einer *einzelnen* Sperre sind die 25 h 15 min nur unter genau dieser
Annahme — und die ist unbelegt.

Nach oben trägt die Rechnung dagegen. Die längste mit den Beobachtungen
verträgliche Sperre reicht vom letzten Erfolg um 08:41 bis zur abweichenden
Meldung um 08:22, also **47 h 41 min**; länger kann keine einzelne gewesen sein.
Wer stattdessen ab der ersten Limit-Meldung rechnet, unterschlägt die 67
Minuten, in denen das Kontingent schon weg gewesen sein kann, und nennt die
Spanne zwischen zwei Beobachtungen eine Obergrenze.

Beobachtungspunkte sind keine Messreihe — die 21 Stunden vor der abweichenden
Meldung liefen ganz ohne Codex-Auslöser, dort hat niemand gemessen.

In der Zwischenzeit sind 32 PRs mit formal erfülltem Häkchen gemergt worden,
ohne dass jemand hineingesehen hat, und am 22.8. noch einmal 43.

**Vier** Gründe, warum Codex schweigt, und nur einer davon ist harmlos:

- **Kein Befund** — dann schreibt er einen gewöhnlichen Issue-Kommentar:

  ```
  Codex Review: Didn't find any major issues. Swish!
  ```

  Der Schlusssatz wechselt bei jedem Lauf («Delightful!», «Keep it up!»,
  «More of your lovely PRs please.»); stabil ist nur der Satz davor. Der
  Infokasten, den Codex unter jeden Review setzt, behauptet weiterhin eine
  Reaktion («otherwise it will react with 👍») — am 23.8. kam in sechs Repos
  die Meldung und in keinem die Reaktion. Der Kasten ist keine Quelle.
- **Der PR ist ein Draft** — darauf läuft Codex nicht an.
- **Das Kontingent ist weg** — dann schreibt er die Meldung oben.
- **Für das Repo fehlt eine Environment** — dann schreibt er:

  ```
  To use Codex here, create an environment for this repo.
  ```

Der vierte kam erst zum Vorschein, als der dritte wegfiel, und das ist kein
Zufall: Die Prüfungen liegen hintereinander. Dass es diese Reihenfolge ist und
nicht die umgekehrte, lässt sich an einem einzigen Repo ablesen — in
`swiss-public-data-mcp` bekam PR #54 am 22.8. um 10:56:55 die Kontingent-Meldung
und PR #56 am 23.8. um 08:22:20 die Environment-Meldung. Läge die
Environment-Prüfung vorn, hätte #54 sie schon am Vortag gesehen; die Environment
fehlte ja bereits. Zwei Meldungen aus demselben Repo schlagen hier jede
Vermutung über die Reihenfolge.

Praktisch heisst das: **Eine verschwundene Limit-Meldung ist keine Entwarnung.**
Sie kann bedeuten, dass das Kontingent wieder da ist — und dass jetzt etwas
anderes den Review verhindert. Belegt ist eine Prüfung erst durch ein
Review-Objekt **oder** eine Befundlos-Meldung. Wer nur das Objekt gelten lässt,
zählt jeden befundlosen Review als ungeprüft — und baut sich denselben Fehlalarm
ein, den dieser Abschnitt verhindern soll, nur in die andere Richtung.

«Kein Kommentar» heisst also nicht «geprüft und sauber». Unterscheiden lässt es
sich an der Form: Ein Review **mit** Befund ist ein Review-Objekt
(«💡 Codex Review», mit Commit-Angabe); ein Review **ohne** Befund und die
beiden Ausfallmeldungen — Kontingent wie Environment — sind gewöhnliche
Issue-Kommentare und trennen sich nur im Text. Beim Draft gibt es überhaupt
nichts, weil Codex nicht anläuft; ein kommentarloser Draft ist deshalb kein
Beleg, sondern ein nicht durchgeführter Test.

Das sind verschiedene Abfragen — `get_reviews` fürs Objekt, `get_comments` für
alles andere; wer nur eine nimmt, übersieht den Rest. Genau so ist die
Limit-Meldung zuerst durchgerutscht.

Der Kommentarzähler allein reicht ohnehin nicht: `comments: 1` kann die
Befundlos-, die Kontingent- **oder** die Environment-Meldung sein — drei
gegensätzliche Bedeutungen unter derselben Zahl. Den Text lesen, nicht die Zahl.
Und einen unbekannten vierten Text wörtlich zitieren, statt ihn in eine der
bekannten Schubladen zu zwingen: Dieser Abschnitt musste schon einmal von drei
auf vier Gründe wachsen, und die 👍-Reaktion stand hier zwei Fassungen lang als
Tatsache.

Und ein befundloser Lauf ist kein Freispruch. Am 23.8. lief derselbe Text durch
42 Reviews: 36 meldeten denselben P2-Befund, 6 die Befundlos-Meldung — gleiche
Eingabe, gegenteiliges Urteil, alles in denselben neun Minuten. Ein sauberer
Lauf sagt damit etwas über den Lauf, nicht über den Text. Wer sein Häkchen
daran hängt, hängt es an einen Münzwurf.

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
steht im Codex-Dashboard. Welches hier griff, ist **offen**. Die Lücke oben
schliesst das Fünf-Stunden-Fenster nicht aus: Es kann sich zwischendurch
geöffnet und durch neue Auslöser wieder erschöpft haben. Das auszuschliessen
bräuchte den Nachweis, dass in der ganzen Spanne kein einziger Review durchlief
— den gibt es nicht, weil nur Fehlschläge beobachtet wurden. Eine lange Reihe
von Fehlschlägen belegt eine lange Reihe von Fehlschlägen, nicht ihre Ursache.

Zeigt das Dashboard freies Kontingent, während Reviews weiter scheitern, ist
das ein bekannter Fehler bei mehreren verbundenen Konten — dann den
GitHub-Connector in den Codex-Einstellungen trennen und neu verbinden.

Die Environment legt man unter `chatgpt.com/codex/cloud/settings/environments`
an, und zwar **je Repo**. Die Meldung sagt es selbst («for this repo»), und am
23.8. war es genau so: In `swiss-public-data-mcp` fehlte sie, dort kam kein
Review; in den übrigen Repos lief Codex am selben Morgen durch. Eine
Environment fürs Konto genügt also nicht — wer eine anlegt und den Rest für
erledigt hält, mergt weiter Ungeprüftes.

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
