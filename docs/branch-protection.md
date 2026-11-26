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
2. **Require branches to be up to date before merging — bis 25.11. belegt nicht
   wirksam.**
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

   Am 2026-11-26 als gespeichert gemeldet. Danach gibt es nur Indizien, dass
   sie weiter nicht greift — belegt ist es nicht (Messprotokoll am Ende).
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

#134 war als Probe zu schwach: Dass GitHub eine Lücke von nur einem
Merge-Commit bei identischem Baum nicht als «veraltet» wertet, liess sich nicht
ausschliessen. #135 schloss diese Lücke — ihm fehlte Inhalt —, hier stand
zuerst trotzdem «eindeutig», und das war zu stark: Es stützt sich allein auf
`mergeable_state`, und dass dieser bei wirksamer Option `behind` meldet, ist
auf den gelesenen Doku-Seiten nicht belegt. Die Doku sagt nur, der Branch
müsse vor dem Merge aktuell sein. Eindeutig ist bisher nur #132, vor dem
Speichern: ein Merge mit fehlendem Inhalt, der durchging.

Belegen liesse sich der Stand nach dem 26.11. durch einen Merge-Versuch an
einem PR mit fehlendem Inhalt. Lehnt die API ihn ab, greift die Option; geht
er durch, greift sie nicht — und der PR ist gemergt. Oder ohne Risiko im
Browser: Bei wirksamer Option ist der Merge-Knopf eines solchen PR gesperrt,
bis «Update branch» geklickt wurde.
