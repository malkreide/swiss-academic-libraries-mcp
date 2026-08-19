#!/usr/bin/env bash
#
# SessionStart-Hook: Wie viele Commits liegt der ausgecheckte Stand hinter
# origin/<Standard-Branch>?
#
# WARUM ES DIESEN HOOK GIBT
# -------------------------
# Ein veralteter Klon hat am 3.8.2026 zweimal eine rote CI erzeugt, deren
# Ursache nicht im Diff stand — die fehlenden Commits waren jeweils genau die,
# die das Gate einfuehrten, an dem der Branch scheiterte. Die Pruefung kostet
# eine Sekunde und ersetzt eine Fehlersuche in den falschen Dateien.
#
# WARUM ER NIEMALS BLOCKIERT
# --------------------------
# Kein Netz, kein Remote, detached HEAD, flatterndes DNS, fehlendes `timeout`:
# jeder dieser Faelle geht still durch und endet mit 0. Ein Hook, der bei
# Netzproblemen die Arbeit anhaelt, wird nach dem zweiten Mal abgeschaltet und
# schuetzt danach gar nichts. Deshalb steht hier bewusst KEIN `set -e`, und
# `main()` laeuft in einem Subshell-Aufruf, dessen Exit-Code verworfen wird.
#
# WARUM DER STANDARD-BRANCH ERMITTELT UND NICHT ANGENOMMEN WIRD
# -------------------------------------------------------------
# Drei Server im Portfolio heissen ihren Standard-Branch `master`
# (openlex-mcp, swiss-courts-mcp, swisstopo-mcp). Ein fest verdrahtetes `main`
# scheitert dort mit «couldn't find remote ref main» — das sieht aus wie ein
# Netzproblem, ist aber die Annahme, und genau sie hat schon einmal einen
# Branch 15 Commits alt werden lassen.

# Absichtlich ohne `set -e`/`set -u`: ein Fehlschlag irgendwo soll den
# Sessionstart nicht beenden, sondern zum stillen Durchgehen fuehren.
set -o pipefail 2>/dev/null || true

# Kein Prompt, keine Passphrase, kein Credential-Helper-Dialog. Ohne das
# haengt `git fetch` bei einem privaten Remote ohne Credentials unbegrenzt —
# ein Timeout allein wuerde das nur nach Sekunden abschneiden, hier faellt es
# sofort durch.
export GIT_TERMINAL_PROMPT=0
export GIT_ASKPASS=true
export SSH_ASKPASS=true
export SSH_ASKPASS_REQUIRE=never
export GIT_CONFIG_PARAMETERS="'credential.interactive=never'"
export GIT_SSH_COMMAND="${GIT_SSH_COMMAND:-ssh} -o BatchMode=yes -o ConnectTimeout=4 -o StrictHostKeyChecking=accept-new"

# Sekunden, die der Sessionstart hoechstens auf das Netz wartet.
FETCH_TIMEOUT="${CLAUDE_FRESHNESS_TIMEOUT:-5}"

# `timeout` ist coreutils und nicht ueberall da (macOS ohne coreutils, schmale
# Container). Fehlt es, uebernehmen gits eigene Bremsen: lowSpeedLimit/-Time
# brechen eine Verbindung ab, die zu langsam liefert.
run_git() {
  if command -v timeout >/dev/null 2>&1; then
    timeout -k 1 "$FETCH_TIMEOUT" git \
      -c "http.lowSpeedLimit=1000" \
      -c "http.lowSpeedTime=$FETCH_TIMEOUT" \
      "$@"
  else
    git \
      -c "http.lowSpeedLimit=1000" \
      -c "http.lowSpeedTime=$FETCH_TIMEOUT" \
      "$@"
  fi
}

# Welcher Remote? Der Upstream des aktuellen Branches, sonst `origin`, sonst
# der erste ueberhaupt. Kein Remote -> nichts zu vergleichen.
resolve_remote() {
  local upstream remote
  upstream="$(git rev-parse --abbrev-ref --symbolic-full-name '@{upstream}' 2>/dev/null)"
  if [ -n "$upstream" ]; then
    remote="${upstream%%/*}"
    if git remote 2>/dev/null | grep -qxF "$remote"; then
      printf '%s\n' "$remote"
      return 0
    fi
  fi
  if git remote 2>/dev/null | grep -qxF origin; then
    printf '%s\n' origin
    return 0
  fi
  git remote 2>/dev/null | head -n 1
}

# Standard-Branch ERMITTELN, nie annehmen. Erst lokal (kostet kein Netz),
# dann ueber das Remote. Beides erfolglos -> still raus, statt `main` zu raten.
resolve_default_branch() {
  local remote="$1" ref branch
  ref="$(git symbolic-ref --quiet --short "refs/remotes/$remote/HEAD" 2>/dev/null)"
  if [ -n "$ref" ]; then
    printf '%s\n' "${ref#"$remote"/}"
    return 0
  fi
  branch="$(run_git ls-remote --symref "$remote" HEAD 2>/dev/null |
    sed -n 's|^ref: refs/heads/\([^[:space:]]*\).*|\1|p' | head -n 1)"
  [ -n "$branch" ] && printf '%s\n' "$branch"
}

main() {
  command -v git >/dev/null 2>&1 || return 0

  cd "${CLAUDE_PROJECT_DIR:-.}" 2>/dev/null || return 0
  [ "$(git rev-parse --is-inside-work-tree 2>/dev/null)" = "true" ] || return 0

  # Unborn HEAD (frisch initialisiertes Repo ohne Commit): nichts zu zaehlen.
  git rev-parse --verify --quiet HEAD >/dev/null 2>&1 || return 0

  local remote default_branch behind
  remote="$(resolve_remote)"
  [ -n "$remote" ] || return 0

  default_branch="$(resolve_default_branch "$remote")"
  [ -n "$default_branch" ] || return 0

  # Nur FETCH_HEAD schreiben, keine lokale Ref anfassen — der Hook aendert
  # den Arbeitsstand nicht, er meldet nur.
  run_git fetch --quiet --no-tags "$remote" "$default_branch" >/dev/null 2>&1 || return 0

  behind="$(git rev-list --count HEAD..FETCH_HEAD 2>/dev/null)"
  case "$behind" in
    '' | *[!0-9]*) return 0 ;;
    0) return 0 ;;  # Aktuell — dann schweigt er.
  esac

  local plural="s"
  [ "$behind" = "1" ] && plural=""

  printf '%s\n' \
    "⚠️  Klon veraltet: $behind Commit$plural hinter $remote/$default_branch." \
    "" \
    "    Fehlende Commits fuehren erfahrungsgemaess genau die Gates ein, an denen" \
    "    der Branch dann scheitert — die Ursache steht in dem Fall NICHT im Diff." \
    "    Am 3.8.2026 ist das zweimal passiert." \
    "" \
    "    Vor der Arbeit einholen:" \
    "        git fetch $remote $default_branch && git merge FETCH_HEAD" \
    "    (auf einem eigenen Branch stattdessen: git rebase FETCH_HEAD)"
}

# Exit-Code bewusst verworfen: der Hook meldet, er blockiert nicht.
main || true
exit 0
