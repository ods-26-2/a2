#!/bin/sh
set -u

RESTART_SECONDS="${A2_PROCESS_RESTART_SECONDS:-2}"

echo "============================================"
echo "Iniciando ODS A2"
echo "============================================"
echo "Banco: ${A2_DATABASE_FILE:-/app/data/acessos.db}"
echo "Kafka: ${KAFKA_BOOTSTRAP_SERVERS:-não configurado}"
echo "Tópico: ${KAFKA_TOPIC:-ods.i6.code_read}"
echo "API local: porta ${A2_LOG_API_PORT:-8001}"
echo "Monitor de catracas: porta 8000"
echo "============================================"

API_PID=""
A2_PID=""
STOPPING=0

start_api() {
    echo "[Supervisor] Iniciando API de logs..."
    python -u acessos_api.py &
    API_PID=$!
}

start_a2() {
    echo "[Supervisor] Iniciando liberar.py..."
    python -u liberar.py &
    A2_PID=$!
}

encerrar() {
    STOPPING=1

    echo ""
    echo "[Supervisor] Encerrando A2 e API..."

    if [ -n "${A2_PID:-}" ]; then
        kill "$A2_PID" 2>/dev/null || true
    fi

    if [ -n "${API_PID:-}" ]; then
        kill "$API_PID" 2>/dev/null || true
    fi

    if [ -n "${A2_PID:-}" ]; then
        wait "$A2_PID" 2>/dev/null || true
    fi

    if [ -n "${API_PID:-}" ]; then
        wait "$API_PID" 2>/dev/null || true
    fi

    exit 0
}

trap encerrar INT TERM

start_api
start_a2

# Os processos são supervisionados separadamente.
#
# Se liberar.py morrer, a API continua online e apenas o A2
# é reiniciado.
#
# Se a API morrer, liberar.py continua rodando e apenas a API
# é reiniciada.
while [ "$STOPPING" -eq 0 ]; do
    if ! kill -0 "$API_PID" 2>/dev/null; then
        wait "$API_PID" 2>/dev/null || true

        echo "[Supervisor] API de logs caiu."
        echo "[Supervisor] Reiniciando em ${RESTART_SECONDS}s..."

        sleep "$RESTART_SECONDS"
        start_api
    fi

    if ! kill -0 "$A2_PID" 2>/dev/null; then
        wait "$A2_PID" 2>/dev/null || true

        echo "[Supervisor] liberar.py caiu."
        echo "[Supervisor] A API permanece ativa."
        echo "[Supervisor] Reiniciando A2 em ${RESTART_SECONDS}s..."

        sleep "$RESTART_SECONDS"
        start_a2
    fi

    sleep 1
done
