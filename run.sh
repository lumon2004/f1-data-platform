#!/bin/bash
# Ciclo esterno: rilancia sessioni autonome di Claude Code finché ./verifica.sh non passa.
set -u
cd "$(dirname "$0")"

MAX_SESSIONI=${MAX_SESSIONI:-30}
# Attiva l'hook Stop (verifica-completamento.sh) solo nelle sessioni autonome.
export F1_AUTONOMO=1
mkdir -p logs

for i in $(seq 1 "$MAX_SESSIONI"); do
  ./verifica.sh > "logs/verifica-pre-sessione-$i.log" 2>&1 && {
    echo "Obiettivo raggiunto alla sessione $i"
    exit 0
  }
  claude -p "Leggi CLAUDE.md e PROGRESS.md. Riprendi dalla prima tappa non completata. \
Aggiorna PROGRESS.md prima di chiudere." --output-format json > "logs/sessione-$i.json"
  git add -A
  git diff --cached --quiet || git commit -q -m "Sessione $i"
done

echo "Limite sessioni raggiunto: vedi PROGRESS.md"
exit 1
