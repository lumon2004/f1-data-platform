#!/bin/bash
# Verifica completa di F1 Data Platform: test dei componenti + test di accettazione + screenshot in review/.
# Termina con 0 solo se tutto passa. Contratto dei test: tests/accettazione/README.md.
# Opzioni (variabili d'ambiente): KEEP_STACK=1 lascia lo stack di verifica avviato alla fine.
set -uo pipefail
cd "$(dirname "$0")"
ROOT=$(pwd)
V="$ROOT/.verifica"
CFG="$ROOT/config/accettazione.json"
cfg() { jq -r "$1" "$CFG"; }

declare -a ESITI=()
esito() { ESITI+=("$1|$2"); }   # nome|0 oppure nome|codice d'errore
titolo() { printf '\n==== %s ====\n' "$1"; }

for cmd in docker jq git java; do
  command -v "$cmd" >/dev/null || { echo "Manca il comando richiesto: $cmd" >&2; exit 1; }
done
docker info >/dev/null 2>&1 || { echo "Docker non è in esecuzione" >&2; exit 1; }

rm -rf "$V"; mkdir -p "$V" "$ROOT/review"

# ---- Copia pulita: i file che un clone del repository conterrebbe ----
titolo "Copia pulita del repository"
git ls-files -co --exclude-standard | while IFS= read -r f; do [[ -e "$f" ]] && echo "$f"; done > "$V/file-versionati.txt"
mkdir -p "$V/clone"
tar -cf - -T "$V/file-versionati.txt" | tar -xf - -C "$V/clone"
echo "$(wc -l < "$V/file-versionati.txt" | tr -d ' ') file copiati in .verifica/clone"

# ---- Test del backend (JUnit + Testcontainers) ----
titolo "Test backend (Maven)"
if [[ -x "$V/clone/backend/mvnw" ]]; then
  (cd "$V/clone/backend" && ./mvnw -B -q verify) ; esito "backend: mvn verify" $?
else
  echo "backend/mvnw assente"; esito "backend: mvn verify" 1
fi

# ---- Stack Docker isolato (progetto, volumi e porte dedicati alla verifica) ----
export COMPOSE_PROJECT_NAME=f1-verifica
export POSTGRES_DB=f1 POSTGRES_USER=f1 POSTGRES_PASSWORD="verifica-$RANDOM$RANDOM"
export POSTGRES_PORT=$(cfg .porte_verifica.postgres) API_PORT=$(cfg .porte_verifica.api) WEB_PORT=$(cfg .porte_verifica.web)
COMPOSE=(docker compose --project-directory "$V/clone" -f "$V/clone/docker-compose.yml")

pulisci() {
  [[ "${KEEP_STACK:-0}" == "1" ]] && { echo "Stack di verifica lasciato attivo (progetto $COMPOSE_PROJECT_NAME)"; return; }
  [[ -f "$V/clone/docker-compose.yml" ]] && "${COMPOSE[@]}" down -v --remove-orphans >/dev/null 2>&1
}
trap pulisci EXIT

titolo "Avvio dello stack Docker"
echo '[]' > "$V/stato-servizi.json"
echo 999999 > "$V/tempo-avvio-s"
if [[ -f "$V/clone/docker-compose.yml" ]]; then
  "${COMPOSE[@]}" down -v --remove-orphans >/dev/null 2>&1
  if "${COMPOSE[@]}" build; then
    INIZIO=$(date +%s)
    "${COMPOSE[@]}" up -d
    LIMITE=$(cfg .docker.max_caricamento_dati_s)
    while :; do
      "${COMPOSE[@]}" ps -a --format json | jq -s 'flatten' > "$V/stato-servizi.json"
      SANI=$(jq '[.[] | select((.Service=="postgres" or .Service=="backend" or .Service=="frontend") and .Health=="healthy")] | length' "$V/stato-servizi.json")
      PIPELINE=$(jq -r '.[] | select(.Service=="pipeline") | "\(.State) \(.ExitCode)"' "$V/stato-servizi.json")
      ORA=$(( $(date +%s) - INIZIO ))
      [[ "$SANI" == "3" && "$(cat "$V/tempo-avvio-s")" == "999999" ]] && echo "$ORA" > "$V/tempo-avvio-s"
      [[ "$SANI" == "3" && "$PIPELINE" == exited* ]] && break
      [[ "$PIPELINE" == exited* && "$PIPELINE" != "exited 0" ]] && break
      (( ORA > LIMITE )) && { echo "Timeout: stack non pronto dopo $LIMITE s"; break; }
      sleep 3
    done
    "${COMPOSE[@]}" ps -a
  else
    esito "docker compose build" 1
  fi
else
  echo "docker-compose.yml assente"
fi

# ---- Test della pipeline e test di accettazione (container dedicato) ----
titolo "Test pipeline e test di accettazione"
docker build -q -t f1-verifica-test "$ROOT/tests/accettazione" >/dev/null || { esito "immagine dei test" 1; }
docker run --rm \
  --add-host host.docker.internal:host-gateway \
  -v "$ROOT:/repo" -w /repo \
  -e PYTHONDONTWRITEBYTECODE=1 \
  -e API_URL="http://host.docker.internal:$API_PORT" \
  -e WEB_URL="http://host.docker.internal:$WEB_PORT" \
  -e POSTGRES_HOST=host.docker.internal -e POSTGRES_PORT="$POSTGRES_PORT" \
  -e POSTGRES_DB -e POSTGRES_USER -e POSTGRES_PASSWORD \
  f1-verifica-test bash -c '
    mkdir -p /tmp/dp
    tar -C /repo/.verifica/clone/data-pipeline -cf - . 2>/dev/null | tar -C /tmp/dp -xf -
    { pip install -q --break-system-packages "/tmp/dp[test]" 2>/dev/null || pip install -q --break-system-packages /tmp/dp; }
    INSTALL=$?
    if [[ $INSTALL -eq 0 && -d /tmp/dp/tests ]]; then python -m pytest -q -p no:cacheprovider /tmp/dp/tests; P=$?; else P=1; fi
    python -m pytest -v -p no:cacheprovider /repo/tests/accettazione; A=$?
    echo "$P $A" > /repo/.verifica/esiti-test
  '
read -r ESITO_PIPELINE ESITO_ACCETTAZIONE < "$V/esiti-test" 2>/dev/null || { ESITO_PIPELINE=1; ESITO_ACCETTAZIONE=1; }
esito "pipeline: pytest data-pipeline/tests" "$ESITO_PIPELINE"
esito "test di accettazione" "$ESITO_ACCETTAZIONE"

# ---- Riepilogo ----
titolo "Riepilogo"
FALLITI=0
for e in "${ESITI[@]}"; do
  nome=${e%|*}; codice=${e##*|}
  if [[ "$codice" == "0" ]]; then echo "  OK    $nome"; else echo "  FAIL  $nome"; FALLITI=1; fi
done
echo "Screenshot in review/: $(ls "$ROOT/review"/*.png 2>/dev/null | wc -l | tr -d ' ')"
exit $FALLITI
