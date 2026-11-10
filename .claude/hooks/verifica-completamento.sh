#!/bin/bash
# Stop: impedisce all'agente di fermarsi finché ./verifica.sh non passa.
# Exit 0 = può fermarsi; exit 2 = riprende il lavoro (il motivo va su stderr).
# Attivo solo nelle sessioni autonome lanciate da run.sh (F1_AUTONOMO=1),
# così le sessioni interattive con l'utente non vengono trattenute.

INPUT=$(cat)
[[ "${F1_AUTONOMO:-}" == "1" ]] || exit 0

ROOT="${CLAUDE_PROJECT_DIR:-$(pwd)}"
cd "$ROOT" || exit 0
MAX_TENTATIVI=${MAX_TENTATIVI:-5}
SESSIONE=$(jq -r '.session_id // "sconosciuta"' <<<"$INPUT")
mkdir -p logs
CONTATORE="logs/.tentativi-stop-$SESSIONE"
LOG="logs/verifica-stop.log"

[[ -x ./verifica.sh ]] || { echo "verifica.sh non esiste ancora: completa la tappa 0." >&2; exit 2; }

if ./verifica.sh > "$LOG" 2>&1; then
  rm -f "$CONTATORE"
  exit 0
fi

N=$(( $(cat "$CONTATORE" 2>/dev/null || echo 0) + 1 ))
echo "$N" > "$CONTATORE"

if (( N >= MAX_TENTATIVI )); then
  {
    echo
    echo "### Report hook Stop — $(date '+%Y-%m-%d %H:%M') — sessione $SESSIONE"
    echo "verifica.sh fallisce dopo $N tentativi. Ultime righe di $LOG:"
    echo '```'
    tail -n 30 "$LOG"
    echo '```'
  } >> PROGRESS.md
  rm -f "$CONTATORE"
  exit 0
fi

{
  echo "verifica.sh fallisce (tentativo $N/$MAX_TENTATIVI). Riprendi il lavoro. Ultime righe di $LOG:"
  tail -n 40 "$LOG"
} >&2
exit 2
