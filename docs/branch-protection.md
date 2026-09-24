# Branch-Schutz für `main`: was heute wirkt

> Stand **2026-09-17**. Alle Angaben zum Ist-Zustand sind an diesem Tag gegen
> das Repo gemessen, nicht aus der GitHub-Dokumentation übernommen; wo etwas
> ungemessen blieb, steht es als ungemessen dabei.

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

Die fünf Check-Runs dieses Repos heissen `test (3.11)`, `test (3.12)`,
`test (3.13)`, `lint` und `Dependency security scan`. Sie stammen alle aus
`ci.yml`.

---

## Was heute wirkt, ohne neuen Code

Settings → Branches → *Add branch protection rule*, Pattern `main`:

1. **Require status checks to pass before merging.** Danach die fünf Namen
   oben auswählen. Deckt die CI ab — und nur sie.
2. **Require branches to be up to date before merging.** Gemessen an **#101**:
   Ein dazwischen liegender `main`-Merge liess das grüne Häkchen auf einen
   Commit zeigen, den es nicht mehr gab. Diese Option erzwingt, dass der Kopf
   aktuell ist, bevor gemergt wird.
3. **Do not allow bypassing the above settings.** Ohne das gilt die Regel für
   Administratoren nicht — und in einem Repo, das eine Person allein betreibt,
   ist das dieselbe Person. Eine Regel, die der eigene Account übergehen darf,
   ist eine Erinnerung, und Erinnerungen haben hier dreimal nicht getragen.

Was diese drei **nicht** leisten: den Merge davor schützen, zu früh zu
geschehen. Sie verhindern den Merge auf rotem oder veraltetem Stand, nicht den
Merge vier Sekunden nach «ready».

---

## Was diese Notiz ausdrücklich nicht behauptet

- Dass es kein Ruleset gibt. Gemessen ist `protected: false`, nicht mehr.
- Dass sich die Auswahlliste der Oberfläche genau aus den letzten Meldungen
  speist, dass ein unerfüllter Required Check den Merge blockiert, und dass
  GitHub die Selbst-Freigabe verweigert. Alle drei sind bekanntes
  Plattformverhalten und in dieser Session **nicht** nachgemessen — sie stehen
  hier, weil sie die Entscheidung tragen, und sind vor dem Setzen der Regel an
  einem Wegwerf-PR zu prüfen.
