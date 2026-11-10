#!/bin/bash
# PreToolUse: blocca le azioni rischiose. Exit 2 = azione bloccata (il motivo va su stderr).
# Input: JSON su stdin con tool_name e tool_input.

INPUT=$(cat)
TOOL=$(jq -r '.tool_name // ""' <<<"$INPUT")
FILE=$(jq -r '.tool_input.file_path // .tool_input.notebook_path // .tool_input.path // ""' <<<"$INPUT")
CMD=$(jq -r '.tool_input.command // ""' <<<"$INPUT")
ROOT="${CLAUDE_PROJECT_DIR:-$(pwd)}"

blocca() {
  echo "BLOCCATO dall'hook blocca-azioni-rischiose: $1" >&2
  exit 2
}

# Soglia dimensione file versionati (MB): da config/accettazione.json se presente, altrimenti 5.
SOGLIA_MB=$(jq -r '.repository.max_file_mb // empty' "$ROOT/config/accettazione.json" 2>/dev/null)
SOGLIA_MB=${SOGLIA_MB:-5}

# Percorsi protetti in scrittura (test bloccati e configurazione degli hook).
PROTETTI='(^|/)(tests/accettazione/|verifica\.sh$|config/accettazione\.json$|\.claude/hooks/|\.claude/settings(\.hooks)?\.json$)'
PROTETTI_CMD='(tests/accettazione|verifica\.sh|config/accettazione\.json|\.claude/hooks|\.claude/settings)'

# File di credenziali: .env e varianti (escluso .env.example), kaggle.json.
SEGRETI='(^|/)(\.env(\.[^/]*)?|kaggle\.json)$'
e_segreto() { [[ "$1" =~ $SEGRETI ]] && [[ ! "$1" =~ \.env\.example$ ]]; }

case "$TOOL" in
  Write|Edit|MultiEdit|NotebookEdit)
    REL="${FILE#"$ROOT"/}"
    [[ "$REL" =~ $PROTETTI ]] && blocca "$REL è protetto (test di accettazione o hook bloccati). Se un test sembra sbagliato, segnalalo all'utente."
    e_segreto "$FILE" && blocca "scrittura di un file di credenziali ($REL)."
    ;;
  Read)
    e_segreto "$FILE" && blocca "lettura di un file di credenziali. Usa i nomi delle variabili in .env.example."
    ;;
  Bash)
    # Credenziali: file .env / kaggle.json, dump dell'ambiente, stampa di variabili segrete.
    if grep -Eq '(^|[^A-Za-z0-9_.-])\.env([^.A-Za-z]|\.[A-Za-z]|$)' <<<"$CMD" && ! grep -Eq '\.env\.example' <<<"$CMD"; then
      blocca "il comando tocca un file .env."
    fi
    grep -Eq 'kaggle\.json|\.kaggle/' <<<"$CMD" && blocca "il comando tocca le credenziali Kaggle."
    grep -Eq '(^|[;&|[:space:]])(printenv|env|set|export -p|declare -x)([[:space:]]*($|[;&|>]))' <<<"$CMD" && blocca "dump delle variabili d'ambiente."
    grep -Eiq '\$\{?[A-Z_]*(PASSWORD|TOKEN|SECRET|KAGGLE_KEY)' <<<"$CMD" && blocca "il comando espande una variabile con credenziali."

    # Test e hook bloccati: nessuna modifica via shell.
    if grep -Eq "$PROTETTI_CMD" <<<"$CMD" && \
       grep -Eq '(>|\btee\b|sed[[:space:]]+-i|perl[[:space:]]+-[a-z]*i|\brm\b|\bmv\b|\bcp\b|\btruncate\b|\bchmod\b|\bln\b|git[[:space:]]+(checkout|restore|rm|mv|reset|stash))' <<<"$CMD"; then
      blocca "modifica via shell di test di accettazione o hook bloccati."
    fi

    # Git: dati completi, forzature, file oltre soglia.
    if grep -Eq '\bgit\b.*\badd\b' <<<"$CMD"; then
      grep -Eq 'data-pipeline/(raw|processed)' <<<"$CMD" && blocca "git add di dati completi o intermedi."
      grep -Eq '[[:space:]](-f|--force)\b' <<<"$CMD" && blocca "git add --force aggira .gitignore."
    fi
    if grep -Eq '\bgit\b.*\bcommit\b' <<<"$CMD"; then
      cd "$ROOT" || exit 0
      while IFS= read -r f; do
        [[ -f "$f" ]] || continue
        [[ "$f" =~ ^data-pipeline/(raw|processed)/ ]] && blocca "commit di dati completi o intermedi ($f)."
        e_segreto "$f" && blocca "commit di un file di credenziali ($f)."
        SIZE=$(stat -f%z "$f" 2>/dev/null || stat -c%s "$f")
        (( SIZE > SOGLIA_MB * 1024 * 1024 )) && blocca "commit di $f oltre la soglia di ${SOGLIA_MB} MB."
      done < <(git diff --cached --name-only --diff-filter=AM 2>/dev/null)
    fi

    # Push sul ramo principale, pubblicazione, deploy.
    if grep -Eq '\bgit\b.*\bpush\b' <<<"$CMD"; then
      grep -Eq '\b(main|master)\b|--all|--mirror|[[:space:]](-f|--force)' <<<"$CMD" && blocca "push sul ramo principale o forzato."
      RAMO=$(git -C "$ROOT" rev-parse --abbrev-ref HEAD 2>/dev/null)
      [[ "$RAMO" == "main" || "$RAMO" == "master" ]] && blocca "push dal ramo principale ($RAMO)."
    fi
    grep -Eq '\b(npm|pnpm|yarn)[[:space:]]+publish\b|\bdocker[[:space:]]+push\b|\bgh[[:space:]]+(release|repo[[:space:]]+(create|edit|delete))\b|\bmvn\b.*\bdeploy\b|\bdeploy\b' <<<"$CMD" && \
      blocca "pubblicazione o deploy."

    # Cancellazioni distruttive.
    grep -Eq '\brm[[:space:]]+(-[a-zA-Z]*[rR][a-zA-Z]*|--recursive)\b' <<<"$CMD" && blocca "rm ricorsivo."
    grep -Eq '\bdocker[[:space:]]+(volume[[:space:]]+(rm|prune)|system[[:space:]]+prune)|\bdocker[[:space:]]+compose\b.*\bdown\b.*(-v\b|--volumes)' <<<"$CMD" && blocca "cancellazione di volumi Docker."
    grep -Eiq 'DROP[[:space:]]+(DATABASE|SCHEMA)|\bdropdb\b' <<<"$CMD" && blocca "DROP DATABASE/SCHEMA."
    grep -Eq '\bgit[[:space:]]+(clean[[:space:]]+-[a-z]*f|reset[[:space:]]+--hard)|\bfind\b.*-delete\b' <<<"$CMD" && blocca "cancellazione massiva."
    ;;
esac

exit 0
