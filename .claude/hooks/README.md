# SessionStart-Hook: Klon-Aktualität

`check-clone-freshness.sh` meldet beim Sessionstart, wie viele Commits der
ausgecheckte Stand hinter `<remote>/<Standard-Branch>` liegt. Registriert ist er
in `.claude/settings.json` unter `hooks.SessionStart`.

## Grund

Ein veralteter Klon hat am 3.8.2026 **zweimal** eine rote CI erzeugt, deren
Ursache nicht im Diff stand — die fehlenden Commits waren jeweils genau die,
die das Gate einführten, an dem der Branch scheiterte. Die Prüfung kostet eine
Sekunde und ersetzt eine Fehlersuche in den falschen Dateien.

Dieser Absatz steht hier und nicht in `settings.json`, weil JSON keine
Kommentare kennt; ein `//`-Schlüssel wäre eine Erfindung, die der Parser
irgendwann meldet. Dieselbe Begründung trägt der Skript-Kopf.

## Zusicherungen, in dieser Reihenfolge wichtig

**Er blockiert die Session niemals.** Kein Netz, kein Remote, detached HEAD,
unborn HEAD, flatterndes DNS, fehlendes `git`, fehlendes `timeout` — jeder
dieser Fälle geht still durch und endet mit `exit 0`. Ein Hook, der bei
Netzproblemen die Arbeit anhält, wird nach dem zweiten Mal abgeschaltet und
schützt danach gar nichts. Deshalb steht im Skript bewusst **kein `set -e`**,
und `main` wird als `main || true` aufgerufen.

**Kurzes Timeout auf das `fetch`.** Standard 5 Sekunden, überschreibbar per
`CLAUDE_FRESHNESS_TIMEOUT`. Fehlt `timeout` (coreutils), bremsen gits eigene
`http.lowSpeedLimit`/`http.lowSpeedTime` mit derselben Frist. Zusätzlich sind
alle interaktiven Abfragen abgeschaltet (`GIT_TERMINAL_PROMPT=0`, `BatchMode`,
`credential.interactive=never`) — ein privates Remote ohne Credentials fällt
sofort durch, statt in ein Timeout zu laufen. Die Hook-Registrierung setzt
`"timeout": 15` als zweite, unabhängige Obergrenze.

**Bei 0 schweigt er.** Ausgabe nur, wenn tatsächlich Commits fehlen.

**Der Standard-Branch wird ermittelt, nicht angenommen.** Erst lokal über
`refs/remotes/<remote>/HEAD` (kostet kein Netz), sonst über
`ls-remote --symref`. Ist beides erfolglos, schweigt der Hook — er rät nicht
`main`. Drei Server im Portfolio heissen ihren Standard-Branch `master`
(`openlex-mcp`, `swiss-courts-mcp`, `swisstopo-mcp`); dort scheitert ein fest
verdrahtetes `main` mit «couldn't find remote ref main». Wer das für ein
Netzproblem hält, arbeitet weiter auf genau dem veralteten Klon — genau diese
Annahme hat schon einmal einen Branch 15 Commits alt werden lassen.

**Er ändert den Arbeitsstand nicht.** `fetch --no-tags` schreibt nur
`FETCH_HEAD`; gezählt wird `git rev-list --count HEAD..FETCH_HEAD`. Kein Merge,
kein Rebase, kein Ref-Update — die Entscheidung bleibt beim Menschen.

## Selbst prüfen

Das Skript ist direkt aufrufbar; es verhält sich ausserhalb der Session gleich.

    .claude/hooks/check-clone-freshness.sh; echo "exit=$?"

Gegenprobe zu «blockiert nie» — jeder dieser Aufrufe muss `exit=0` liefern und
darf nicht hängen:

    ( cd /tmp && .../check-clone-freshness.sh )                 # kein Repo
    CLAUDE_PROJECT_DIR=/nicht/vorhanden .../check-clone-freshness.sh
    git -c ... remote set-url origin https://192.0.2.1/x.git    # totes Netz

Gegenprobe zu «meldet wirklich» — nur ein `git reset --hard HEAD~3` in einem
Wegwerf-Klon zeigt, dass die Meldung nicht bloss nie erscheint.
