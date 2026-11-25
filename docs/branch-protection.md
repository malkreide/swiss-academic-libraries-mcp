# Branch-Schutz für `main`: was heute wirkt

> Stand **2026-11-24**. Alle Angaben zum Ist-Zustand sind an diesem Tag gegen
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
2. **Require branches to be up to date before merging.** Anlass war **#101**:
   Ein dazwischen liegender `main`-Merge liess das grüne Häkchen auf einen
   Commit zeigen, den es nicht mehr gab. Gesetzt am 2026-11-24; gemessen wird
   die Wirkung an dem PR, der diese Fassung bringt.
3. **Do not allow bypassing the above settings.** Ohne das gilt die Regel für
   Administratoren nicht — und in einem Repo, das eine Person allein betreibt,
   ist das dieselbe Person.

Was diese drei **nicht** leisten: den Merge davor schützen, zu früh zu
geschehen. Sie verhindern den Merge auf rotem oder veraltetem Stand, nicht den
Merge vier Sekunden nach «ready».

---

## Was diese Notiz ausdrücklich nicht behauptet

- Dass die Regel ausser den drei Punkten oben nichts enthält. Lesbar ist nur
  die Zusammenfassung der Status-Checks; Review-Pflichten, Push-Beschränkungen
  und Ähnliches zeigt sie nicht.
- Dass GitHub die Selbst-Freigabe verweigert. Bekanntes Plattformverhalten,
  hier **nicht** nachgemessen.
