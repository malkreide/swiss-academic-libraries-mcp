# Branch-Schutz für `main`: was geht, was nicht, und warum

> Stand **2026-09-17**. Alle Angaben zum Ist-Zustand sind an diesem Tag gegen
> das Repo gemessen, nicht aus der GitHub-Dokumentation übernommen; wo etwas
> ungemessen blieb, steht es als ungemessen dabei.
>
> Anlass ist der Abschnitt «Wenn Codex gar nicht erst hinsieht» in
> [`CLAUDE.md`](../CLAUDE.md). Er hält neun Datenpunkte und sechs
> Merge-vor-Review in sieben Gelegenheiten fest und schliesst mit dem Satz, es
> fehle nicht Evidenz, sondern der Branch-Schutz. Diese Notiz ist die
> Einlösung — und sie beginnt damit, die naheliegende Form zu verwerfen.

---

## Die Environment-Meldung ist kein Urteil über das Repo

Hier stand, die Voraussetzung dieser Notiz sei am 17.9.2026 um 19:02
weggefallen: Codex reviewe das Repo nicht mehr. **Das war falsch**, und der
Fehler ist der, vor dem `CLAUDE.md` unter «Wenn etwas rot ist» warnt — aus der
Meldung geschlossen, statt die Quelle zu fragen.

Der vollständige Verlauf auf #110, dem PR, der diese Notiz brachte:

| Zeit (UTC) | Beobachtung |
|---|---|
| 19:01:51 | als Draft angelegt |
| 19:02:00 | `To use Codex here, create an environment for this repo.` |
| 19:06:38 | auf ready umgeschaltet |
| 19:06:42 | gemergt |
| 19:06:45 | Review startet auf `eb8338a`, Auslöser `Draft marked ready` |
| 19:06:50 | Summary-Tabelle, `🔄 Running` |
| 19:07:55 | `✅ Completed`, `eb8338a`, ohne Befund |

Vier Minuten nach der Meldung lief ein Review an, und er lief sauber durch. Die Meldung beschrieb einen
Versuch, keinen Zustand.

Warum sie kam, ist **ungemessen**; zwei Erklärungen passen gleich gut:

- Die Environment fehlte um 19:02 wirklich und wurde dazwischen angelegt — die
  Meldung nennt die Seite, und sie war weitergegeben worden.
- Die Meldung auf einem Draft sagt nichts über den Lauf, der erst beim
  Umschalten auf ready ausgelöst wird.

Zu unterscheiden wären sie nur durch einen Blick auf die Environment-Seite um
19:02, und den gab es nicht.

**Für diese Notiz bleibt der operative Teil trotzdem stehen:** Bevor ein
Branch-Schutz auf ein Codex-Häkchen wartet, muss belegt sein, dass Codex
reviewt — sonst sperrt die Regel den Merge dauerhaft, und ein Workflow nach
Weg A meldete korrekt `failure` und täte dasselbe. Der Beleg ist aber **ein
Lauf**, nicht das Fehlen oder Vorhandensein einer Meldung: PR auf ready, zwei
Minuten warten, Tabelle auf `Completed` mit dem richtigen Commit. Eine
Environment-Meldung auf einem Draft ist dafür weder Beweis noch Gegenbeweis.

---

## Der naheliegende Vorschlag funktioniert nicht

Er lautet: «Required status check auf *Codex Review*, plus *Require branches to
be up to date*.» So stand er in der Lagemeldung, aus der diese Notiz entstand.
Er ist falsch, und zwar nicht knapp.

Ein Required Status Check kann nur etwas verlangen, das als **Check-Run** oder
als Legacy-Commit-Status am Commit hängt. Codex veröffentlicht beides nicht:

| Abfrage | Ergebnis | gemessen an |
|---|---|---|
| `get_check_runs` | 5 Einträge, alle aus `ci.yml` | #101, #108 |
| `get_reviews` | `[]` | #95, #99, #100, #101, #106, #107, #108 |
| `get_comments` | 1 Kommentar, Marker `<!-- codex-pull-request-review-summary -->` | dieselben |

Die fünf Check-Runs heissen `test (3.11)`, `test (3.12)`, `test (3.13)`,
`lint` und `Dependency security scan`. Ein sechster mit «Codex» im Namen
existiert nicht — auch nicht auf **#101**, wo ein vollständiger Review nach
`@codex review` durchlief und `✅ Completed` meldete. Das ist der belastbare
Teil: Es liegt nicht daran, dass der Review noch lief.

**In der GitHub-Oberfläche lässt sich also gar nichts auswählen.** Die Liste
der verlangbaren Checks speist sich aus dem, was zuletzt an Commits des Repos
gemeldet wurde; ein Kommentar steht dort nicht zur Wahl. Wer den Namen von Hand
einträgt, erwartet einen Check, der nie eintrifft — und sperrt den Merge damit
dauerhaft, nicht bis zum Review.

Der letzte Satz ist Plattformverhalten, nicht Messung: Dass ein nie gemeldeter
Required Check als «Expected — waiting for status to be reported» stehenbleibt
und den Merge blockiert, ist bekannt und wurde hier **nicht** ausprobiert. Der
gemessene Teil ist der davor — dass Codex nichts liefert, was man verlangen
könnte.

---

## Ist-Zustand

```
list_branches → {"name": "main", "sha": "aad59e3…", "protected": false}
```

`main` trägt **keinen** klassischen Branch-Schutz. Was das *nicht* hergibt: ob
ein Ruleset (Settings → Rules → Rulesets) greift. Rulesets sind ein zweiter,
neuerer Mechanismus, und ob sich ihre Wirkung im Feld `protected` niederschlägt,
wurde nicht geprüft. Vor dem Anlegen einer Regel deshalb **beide** Stellen
ansehen, sonst entstehen zwei Regelwerke, die sich widersprechen.

---

## Was heute wirkt, ohne neuen Code

Settings → Branches → *Add branch protection rule*, Pattern `main`:

1. **Require status checks to pass before merging.** Danach die fünf Namen
   oben auswählen. Deckt die CI ab — und nur sie.
2. **Require branches to be up to date before merging.** Das ist die Hälfte,
   die wirklich etwas mit Codex zu tun hat: `CLAUDE.md` hält an **#101** fest,
   dass ein dazwischen liegender `main`-Merge das Häkchen auf einen Commit
   zeigen liess, den es nicht mehr gab. Diese Option erzwingt, dass der Kopf
   aktuell ist, bevor gemergt wird.
3. **Do not allow bypassing the above settings.** Ohne das gilt die Regel für
   Administratoren nicht — und in einem Repo, das eine Person allein betreibt,
   ist das dieselbe Person. Eine Regel, die der eigene Account übergehen darf,
   ist eine Erinnerung, und Erinnerungen sind laut `CLAUDE.md` genau das, was
   hier dreimal nicht getragen hat.

Was diese drei **nicht** leisten: den Merge an Codex binden. Sie verhindern den
Merge auf rotem oder veraltetem Stand, nicht den Merge vier Sekunden nach
«ready».

---

## Was den Merge wirklich an Codex bindet

### Weg A — eigener Check-Run aus einem Workflow (empfohlen, existiert noch nicht)

Ein Workflow liest den Codex-Summary-Kommentar, vergleicht den darin genannten
Commit mit dem aktuellen Kopf und veröffentlicht daraus einen **eigenen**
Check-Run. Dieser Check ist dann verlangbar, weil er ein Check-Run ist.

Die Logik, die er braucht, steht schon in `CLAUDE.md` und ist dort gemessen:

- `success` nur, wenn die Tabelle `✅ Completed` zeigt **und** der genannte
  Commit der Kopf ist. `🔄 Running` ist kein Beleg.
- Kein Kommentar heisst nicht «sauber»: In den ersten zehn Sekunden nach
  «ready» existiert die Tabelle noch nicht, das erste Lebenszeichen kommt nach
  6 bis 11 Sekunden. Ein fehlender Kommentar muss deshalb `pending` oder
  `failure` ergeben, nie `success`.
- Die Kontingent- und die Environment-Meldung sind ebenfalls Kommentare und
  bedeuten «nicht geprüft». Sie dürfen nicht als Erfolg durchgehen; der Text
  entscheidet, nicht die Existenz eines Kommentars.
- Auslöser: `issue_comment` (`created` **und** `edited`) — die Tabelle
  überschreibt sich selbst, der Wechsel auf `Completed` ist eine Bearbeitung,
  kein neuer Kommentar. Dazu `pull_request` für den Ausgangszustand.

**Ungemessen und vor dem Bau zu klären:** ob ein aus `issue_comment` heraus
erzeugter Check-Run von der Branch-Schutz-Regel als derselbe Check erkannt wird
wie einer aus `pull_request`; welche Berechtigung der Workflow genau braucht
(`checks: write` ist die Erwartung, nicht geprüft); und ob ein Check, der beim
Öffnen des PR `pending` setzt, den Merge-Button wie gewünscht sperrt statt den
PR nur als unvollständig zu zeigen. Nichts davon ist hier gelaufen — dieser
Abschnitt ist ein Bauplan, kein Protokoll.

### Weg B — Codex-seitig, falls es das gibt

Die Codex-Einstellungen für dieses Repo liegen unter
`chatgpt.com/codex/cloud/settings/general`. Ob sich dort einstellen lässt, dass
Codex seinen Review als Check-Run statt als Kommentar meldet, ist **ungemessen**
— die Seite wurde nicht geöffnet. Wäre es möglich, entfiele Weg A vollständig.
Diese Frage zuerst zu klären, ist billiger als der Workflow.

### Weg C — Pull-Request-Review verlangen (stumpf, und hier gefährlich)

**Require a pull request before merging → Require approvals: 1** erzwingt eine
Pause. Aber: Codex erzeugt kein Review-Objekt (siehe Tabelle oben), zählt also
nicht als Approval. Verlangt würde die Zustimmung eines *Menschen*.

In einem Ein-Personen-Repo ist das keine Bremse, sondern ein Riegel: GitHub
lässt niemanden den eigenen Pull Request freigeben. Zusammen mit Punkt 3
(«Do not allow bypassing») wäre danach **kein** eigener PR mehr mergebar. Diese
Kombination also nur, wenn es tatsächlich eine zweite Person gibt.

> Dass GitHub die Selbst-Freigabe verweigert, ist bekanntes Verhalten der
> Plattform und hier **nicht** nachgemessen. Wer Weg C wählt, probiere es an
> einem Wegwerf-PR aus, bevor die Regel auf `main` steht.

---

## Empfehlung

Die drei Optionen aus «Was heute wirkt» jetzt setzen — sie kosten nichts und
schliessen den #101-Fall (veralteter Stand unter grünem Häkchen). Danach
**Weg B prüfen**, weil eine Einstellung billiger ist als ein Workflow. Erst
wenn es die nicht gibt, Weg A bauen.

Weg C nicht, solange das Repo von einer Person betrieben wird.

---

## Was diese Notiz ausdrücklich nicht behauptet

- Dass die drei Optionen das dokumentierte Problem lösen. Sie lösen es nicht;
  sie lösen ein anderes daneben.
- Dass Weg A funktioniert. Er ist plausibel und in drei Punkten ungeprüft.
- Dass es kein Ruleset gibt. Gemessen ist `protected: false`, nicht mehr.
- Dass Codex nie einen Check-Run liefert. Gemessen sind sieben PRs dieses
  Repos. Ob eine andere Codex-Konfiguration das ändert, sagt die Messung nicht.
- Dass sich die Auswahlliste der Oberfläche genau aus den letzten Meldungen
  speist, dass ein unerfüllter Required Check den Merge blockiert, und dass
  GitHub die Selbst-Freigabe verweigert. Alle drei sind bekanntes
  Plattformverhalten und in dieser Session **nicht** nachgemessen — sie stehen
  hier, weil sie die Entscheidung tragen, und sind vor dem Setzen der Regel an
  einem Wegwerf-PR zu prüfen.
