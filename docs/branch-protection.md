# Branch-Schutz für `main`: was heute wirkt

> Stand **2026-11-26**. Alle Angaben zum Ist-Zustand sind an diesem Tag gegen
> das Repo gemessen, nicht aus der GitHub-Dokumentation übernommen; wo etwas
> ungemessen blieb, steht es als ungemessen dabei. Die erste Fassung vom
> 2026-09-17 mass `protected: false`; die Regel ist seither gesetzt.

---

## Ist-Zustand

Die Einstellung selbst ist von hier aus nicht lesbar: Der Endpunkt
`branches/main/protection` antwortet dem Agent-Zugang mit HTTP 403
(«Resource not accessible by integration»), Schreibzugriffe sperrt der Proxy
ebenso. Was sich lesen lässt, ist die Zusammenfassung im Branch-Endpunkt:

```
branches/main → "protected": true,
  "required_status_checks": {
    "contexts": ["Dependency security scan", "lint",
                 "test (3.11)", "test (3.12)", "test (3.13)"],
    "enforcement_level": "everyone" }
rulesets                → []
rules/branches/main     → []
```

Daraus folgt:

- **Verlangt sind genau die fünf Check-Runs aus `ci.yml`**, alle von GitHub
  Actions (`app_id` 15368). Ein zusätzlicher, verwaister Kontext — wie er in
  anderen Repos des Portfolios nach dem Entfernen eines Gate-Workflows
  zurückblieb — steht nicht darin.
- **Es gibt kein Ruleset**, weder am Repo noch als Regel, die auf `main`
  greift. Die Frage aus der ersten Fassung ist damit beantwortet: Es gibt
  nur ein Regelwerk.
- **`enforcement_level: "everyone"`** spricht dafür, dass die Checks auch für
  Administratoren gelten. Die Einstellung «Do not allow bypassing» selbst ist
  nicht lesbar; belegt ist sie damit nicht.

---

## Was gesetzt ist

Settings → Branches, Regel für `main`:

1. **Require status checks to pass before merging**, mit den fünf Namen oben.
   Deckt die CI ab — und nur sie.
2. **Require branches to be up to date before merging — belegt nicht wirksam,
   auch nach dem Speichern am 26.11.**
   Anlass war **#101**: Ein dazwischen liegender `main`-Merge liess das grüne
   Häkchen auf einen Commit zeigen, den es nicht mehr gab. Die Option wurde am
   2026-11-24 als gesetzt gemeldet; die Messung widerspricht:

   | Messung an #132 (UTC) | Rückstand auf `main` | `mergeable_state` |
   |---|---|---|
   | 24.11. 19:00:36, Draft, 5/5 grün | 2 Commits | `clean` |
   | 24.11. 19:00:56–19:01:12, ready, viermal | 2 Commits | `clean` |
   | 24.11. 19:59:55 und 25.11. 00:01:54 | 2 Commits | `clean` |
   | 25.11. 06:46:35, **gemergt** | 2 Commits | — |

   Mit wirksamer Option muss der Branch laut Doku vor dem Merge aktuell sein
   («The branch **must** be up to date with the base branch before merging»).
   Hier ging der Merge mit Rückstand durch (`cd8943c`, Eltern `3fe6136` und
   `c811ae3`; gefehlt hat unter anderem der Inhalts-Commit `9517a3c`). Ob die
   Option nicht gespeichert wurde oder an einer anderen Regel hing, ist von hier
   nicht lesbar; belegt ist nur, dass sie auf `main` nicht griff. Die
   `clean`-Werte darüber sind dafür kein eigener Beleg: Welchen Zustand die API
   bei wirksamer Option meldet, steht auf den gelesenen Doku-Seiten nicht.

   Am 2026-11-26 als gespeichert gemeldet. Danach ebenso nicht wirksam: #139
   ging am 26.11. um 04:38:13 UTC mit fehlendem Inhalts-Commit durch
   (Messprotokoll am Ende).
3. **Do not allow bypassing the above settings.** Ohne das gilt die Regel für
   Administratoren nicht — und in einem Repo, das eine Person allein betreibt,
   ist das dieselbe Person.

Was diese drei **nicht** leisten: den Merge davor schützen, zu früh zu
geschehen. Wirksam verhindern sie heute nur den Merge auf rotem Stand — den auf
veraltetem erst, wenn Punkt 2 greift —, und den Merge vier Sekunden nach
«ready» gar nicht.

---

## Was diese Notiz ausdrücklich nicht behauptet

- Dass die Regel ausser den drei Punkten oben nichts enthält. Lesbar ist nur
  die Zusammenfassung der Status-Checks; Review-Pflichten, Push-Beschränkungen
  und Ähnliches zeigt sie nicht.
- Dass GitHub die Selbst-Freigabe verweigert. Bekanntes Plattformverhalten,
  hier **nicht** nachgemessen.

---

## Messprotokoll «Require branches to be up to date»

Gemessen an PRs, die absichtlich hinter `main` liegen. Greift die Option, muss
ein solcher PR vor dem Merge aktualisiert werden. Erwartet war dafür der Zustand
`behind`; gesehen wurde er nie, und belegt ist er nicht.

| Datum (UTC) | PR | fehlt gegenüber `main` | Ergebnis |
|---|---|---|---|
| 24./25.11.2026 | #132 | 2 Commits mit Inhalt | `clean`; gemergt mit Rückstand |
| 26.11.2026 | #134 | nur Merge-Commit `a5b2464`, Baum identisch | `clean`; gemergt mit Rückstand — nicht eindeutig |
| 26.11.2026 03:33:14–03:33:30, ready, viermal | #135 | Inhalts-Commit `3e2923b` und Merge-Commit `aee4b99`, kein Konflikt | `clean`; erst nach dem Aktualisieren gemergt — Indiz, kein Beleg |
| 26.11.2026 04:37:04–04:37:13, ready, dreimal; gemergt 04:38:13 | #139 | Inhalts-Commit `d6da326` und Merge-Commit `9e96194`, kein Konflikt | `clean`; **gemergt mit Rückstand** (`176c08d`, Eltern `9e96194` und `a21e579`) — **Beleg: greift nicht** |

#134 war als Probe zu schwach: Dass GitHub eine Lücke von nur einem
Merge-Commit bei identischem Baum nicht als «veraltet» wertet, liess sich nicht
ausschliessen. #135 schloss diese Lücke — ihm fehlte Inhalt —, hier stand
zuerst trotzdem «eindeutig», und das war zu stark: Es stützt sich allein auf
`mergeable_state`, und dass dieser bei wirksamer Option `behind` meldet, ist
auf den gelesenen Doku-Seiten nicht belegt. Die Doku sagt nur, der Branch
müsse vor dem Merge aktuell sein. Eindeutig war deshalb nur #132, vor dem
Speichern: ein Merge mit fehlendem Inhalt, der durchging.

#139 liefert denselben Beleg für die Zeit danach. Er war als Probe für den
Browser gebaut — der Merge-Knopf sollte zeigen, ob die Option greift — und
wurde gemergt, ohne dass «Update branch» geklickt worden wäre: Der Kopf blieb
`a21e579`, dem `d6da326` fehlte. Eine wirksame Option hätte genau diesen Merge
gesperrt. Die Probe-Datei, die er mitbrachte, ist im Folge-PR wieder entfernt.

Warum die Option nicht greift, ist von hier nicht lesbar. Das Speichern wurde
gemeldet; ob es eine andere Regel traf oder nicht durchging, zeigt nur die
Einstellungsseite.

---

## Vermutungen zur Ursache — ungeprüft

> Stand **2026-11-26**. Anders als der Rest dieser Notiz stützt sich dieser
> Abschnitt auf die GitHub-Dokumentation, nicht auf eine Messung am Repo.
> Zitiert wird wörtlich aus zwei Seiten:
> [A] «Managing a branch protection rule»
> (`docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/managing-a-branch-protection-rule`),
> [B] «About protected branches»
> (`…/managing-protected-branches/about-protected-branches`). Keine der
> Vermutungen ist belegt; geprüft werden kann jede nur auf der
> Einstellungsseite.

### 1. Das Kästchen wirkt nur zusammen mit verlangten Status-Checks — für `main` ausgeschlossen

«Require branches to be up to date» ist in der Doku ein Unterpunkt der
Status-Checks. [A] führt ihn als eingerückten Punkt unter «Select **Require
status checks to pass before merging**.», [B] unterscheidet die Fälle so:

| Fall | Einstellung laut [B] |
|---|---|
| Strict | «The **Require branches to be up to date before merging** checkbox is checked.» |
| Loose | «… checkbox is **not** checked.» |
| Disabled | «The **Require status checks to pass before merging** checkbox is **not** checked.» |

Zum Fall «Disabled» sagt [B]: «If required status checks aren't enabled,
collaborators can merge the branch at any time», und zwar «regardless of
whether it is up to date with the base branch». Daraus entstand die Vermutung,
das Kästchen wirke nicht, solange in der Regel keine Status-Checks verlangt
sind.

**Für `main` trägt sie nicht.** Der Branch-Endpunkt nennt die fünf verlangten
Kontexte (Ist-Zustand oben), die Status-Checks sind also aktiviert. Die
schärfere Fassung, das Kästchen wirke erst ab mindestens einem eingetragenen
Check, steht auf keiner der beiden Seiten. Sie bleibt hier stehen, damit
niemand sie aus dem Gedächtnis neu aufbringt.

### 2. Gespeichert wurde in einer Regel, die auf `main` nicht greift — offen

Auf einen Branch wirkt immer nur eine einzige klassische Regel. [B]: «Only a
single branch protection rule can apply at a time, which means it can be
difficult to know which rule will apply when multiple versions of a rule
target the same branch.» Welche greift, regelt [A]:

- «… the rules that include a specific branch name have the highest priority»
- «If there is more than one protected branch rule that references the same
  specific branch name, then the branch rule created first will have higher
  priority.»
- «Protected branch rules that mention a special character, such as `*`, `?`,
  or `]`, are applied in the order they were created, so older rules with these
  characters have a higher priority.»

Gibt es also neben der Regel, die die fünf Checks trägt, eine zweite, und wurde
das Kästchen dort gesetzt, bliebe es auf `main` wirkungslos. Das wäre der Fall
bei einem Muster wie `main*` neben `main`, oder bei einer zweiten Regel `main`,
die nach der ersten angelegt wurde. Die Messung widerspricht dem nicht: Die Zusammenfassung
im Branch-Endpunkt zeigt naheliegenderweise die Checks der Regel, die greift,
und `strict` zeigt sie gar nicht.

Rulesets kommen dafür nicht in Frage: `rulesets` und `rules/branches/main`
sind leer (Ist-Zustand oben), und [B] nimmt sie von der Ein-Regel-Grenze
ausdrücklich aus («This restriction does not apply to rulesets»).

**Prüfen:** Settings → Branches. Wie viele Regeln stehen dort, mit welchem
Muster, und in welcher ist «Require branches to be up to date before merging»
angehakt? Ist es genau eine Regel `main` mit angehaktem Kästchen, ist diese
Vermutung widerlegt.

### 3. Das Speichern ging nicht durch — offen

Bleibt übrig, wenn sich Vermutung 2 nicht bestätigt: Die Seite zeigt das
Kästchen dann nicht angehakt. Dazu gibt die Doku nichts her.
