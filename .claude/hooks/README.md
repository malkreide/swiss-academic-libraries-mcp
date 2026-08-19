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

## Gegenproben

Zuletzt vollständig gefahren am **2026-08-19**, alle Fälle wie beschrieben.
Wer das Skript ändert, fährt sie erneut und zieht das Datum nach.

Ein Test, der grün bleibt, wenn man die Implementation entfernt, prüft nichts.
Für diesen Hook heisst das: «still und `exit 0`» allein ist wertlos, denn ein
Skript, das gar nichts tut, besteht jede dieser Proben. Deshalb stehen beide
Richtungen hier — dass er in Abschnitt A schweigt **und** dass er in
Abschnitt C wirklich meldet.

Alle Blöcke setzen voraus:

    H="$PWD/.claude/hooks/check-clone-freshness.sh"

### A — blockiert nie

Jeder Aufruf muss `exit=0` liefern **und** darf nicht hängen. Die Dauer gehört
mitgemessen; ein Fall, der erst nach 30 Sekunden mit 0 endet, hat den
Sessionstart trotzdem angehalten.

    # kein Repo
    ( cd /tmp && env -u CLAUDE_PROJECT_DIR "$H"; echo "exit=$?" )

    # Projektverzeichnis existiert nicht
    CLAUDE_PROJECT_DIR=/nicht/vorhanden "$H"; echo "exit=$?"

    # gar kein Remote
    git clone -q --no-local . /tmp/gp-clone && git -C /tmp/gp-clone remote remove origin
    CLAUDE_PROJECT_DIR=/tmp/gp-clone "$H"; echo "exit=$?"

    # unborn HEAD (frisch init, kein Commit)
    git init -q /tmp/gp-unborn
    CLAUDE_PROJECT_DIR=/tmp/gp-unborn "$H"; echo "exit=$?"

    # totes Netz (192.0.2.1 ist TEST-NET-1, nicht routbar)
    git -C /tmp/gp-clone remote add origin https://192.0.2.1/x.git
    time CLAUDE_PROJECT_DIR=/tmp/gp-clone "$H"; echo "exit=$?"

    # DNS löst nicht auf
    git -C /tmp/gp-clone remote set-url origin https://nonexistent.invalid/x.git
    time CLAUDE_PROJECT_DIR=/tmp/gp-clone "$H"; echo "exit=$?"

### B — das Timeout greift wirklich

**Die beiden Netz-Fälle aus A beweisen das Timeout nicht.** Hinter einem
ausgehenden Proxy oder einer Firewall, die mit RST antwortet, kommen sie in
0 Sekunden zurück: die Verbindung scheitert sofort, der Timeout-Pfad läuft
gar nicht erst an. Das sieht aus wie ein bestandener Test und ist keiner —
genau so besteht auch ein Hook mit kaputtem Timeout diese zwei Fälle. Am
2026-08-19 war das in der Container-Umgebung tatsächlich der Fall (0s statt
der erwarteten Wartezeit), deshalb steht dieser Abschnitt hier.

Nötig ist ein Remote, das wirklich hängt statt abzulehnen. Ein `ssh`-Ersatz,
der nur schläft, liefert das ohne Netz:

    printf '#!/usr/bin/env bash\nsleep 120\n' > /tmp/gp-ssh.sh && chmod +x /tmp/gp-ssh.sh
    git clone -q --no-local . /tmp/gp-hang
    git -C /tmp/gp-hang remote set-url origin ssh://git@example.invalid/x.git
    git -C /tmp/gp-hang update-ref -d refs/remotes/origin/HEAD

    # Hook: muss nach ~3s durch sein
    time GIT_SSH_COMMAND=/tmp/gp-ssh.sh CLAUDE_FRESHNESS_TIMEOUT=3 \
        CLAUDE_PROJECT_DIR=/tmp/gp-hang "$H"; echo "exit=$?"

Das `update-ref -d` ist nicht Kosmetik: mit lokalem `refs/remotes/origin/HEAD`
beantwortet `resolve_default_branch` die Frage ohne Netz, und der Aufruf käme
sofort zurück, ohne je zu fetchen — die Probe würde sich selbst entschärfen.

Und die Gegenprobe dazu, ohne die der Block oben nichts zeigt — derselbe
Zugriff ohne die Bremse des Hooks muss wirklich hängen:

    time GIT_SSH_COMMAND=/tmp/gp-ssh.sh timeout 8 \
        git -C /tmp/gp-hang ls-remote --symref origin HEAD; echo "exit=$?"

Erwartet: `exit=124` nach 8 Sekunden — `timeout` musste abschneiden, der
Aufruf wäre also gehangen. Kommt hier etwas anderes als 124, hängt das Remote
nicht, und der Block darüber hat nichts bewiesen.

### C — er meldet wirklich

Ohne diesen Abschnitt ist jede Probe aus A auch von einem `exit 0` als ganzem
Skript erfüllt.

    # zurückgesetzter Stand: meldet «N Commits hinter <remote>/<default>»
    git worktree add -q --detach /tmp/gp-detached HEAD~2
    CLAUDE_PROJECT_DIR=/tmp/gp-detached "$H"; echo "exit=$?"

Erwartet: eine Meldung mit **irgendeinem** N grösser 0, `exit=0`. Nicht auf
N = 2 prüfen: `HEAD~2` folgt den ersten Eltern und springt über Merge-Commits
hinweg, während gezählt wird, was im Klon insgesamt fehlt. Am 2026-08-19 stand
dort deshalb 4, und das war richtig. Wer hier eine feste Zahl erwartet, hält
korrektes Verhalten für einen Fehler.

Der detached HEAD deckt zwei Zusicherungen auf einmal ab: dass gemeldet wird,
und dass ein abgelöster HEAD den Hook nicht aus dem Tritt bringt.

Dass der Standard-Branch **ermittelt** und nicht `main` geraten wird, zeigt nur
ein Repo, das anders heisst — im Portfolio sind das `openlex-mcp`,
`swiss-courts-mcp` und `swisstopo-mcp`:

    git init -q -b master /tmp/gp-master-src
    git -C /tmp/gp-master-src -c user.email=t@t -c user.name=t commit -q --allow-empty -m c1
    git -C /tmp/gp-master-src -c user.email=t@t -c user.name=t commit -q --allow-empty -m c2
    git clone -q /tmp/gp-master-src /tmp/gp-master && git -C /tmp/gp-master reset -q --hard HEAD~1
    CLAUDE_PROJECT_DIR=/tmp/gp-master "$H"; echo "exit=$?"

Erwartet: «1 Commit hinter origin/**master**». Steht dort `main` oder kommt
gar nichts, wird geraten statt ermittelt. Der Fall prüft nebenbei den
Singular — «1 Commits» wäre falsch.

Zuletzt die stille Richtung, die nur im Verbund mit C etwas aussagt:

    CLAUDE_PROJECT_DIR="$PWD" "$H"; echo "exit=$?"

Erwartet auf aktuellem Klon: keine Ausgabe, `exit=0`.

### Aufräumen

    git worktree remove --force /tmp/gp-detached; git worktree prune
    rm -rf /tmp/gp-clone /tmp/gp-unborn /tmp/gp-hang /tmp/gp-master /tmp/gp-master-src /tmp/gp-ssh.sh
