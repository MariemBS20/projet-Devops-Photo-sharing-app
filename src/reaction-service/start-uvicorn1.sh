#!/bin/bash
set -e

SERVICE_NAME="${SERVICE_NAME:-reaction}"
PID_FILE="/tmp/uvicorn.pid"
LOG_FILE="/tmp/uvicorn.log"

echo "🚀 Starting $SERVICE_NAME API..."

# Nettoyer le PID file si le processus n'existe plus
if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE")
    if ! kill -0 "$OLD_PID" 2>/dev/null; then
        echo "Cleaning stale PID file"
        rm -f "$PID_FILE"
    fi
fi

# Démarrer uvicorn en background
setsid uvicorn main:app --reload --host 0.0.0.0 --port 8000 \
    > "$LOG_FILE" 2>&1 &

# Sauvegarder le PID
echo $! > "$PID_FILE"

echo "✅ $SERVICE_NAME API started (PID: $(cat $PID_FILE))"
echo "📋 Logs: tail -f $LOG_FILE"

# Garder le container vivant en suivant les logs
tail -f "$LOG_FILE"