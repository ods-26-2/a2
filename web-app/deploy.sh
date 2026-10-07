#!/usr/bin/env bash

set -e

PID_FILE="./app.pid"
LOG_FILE="./app.log"
PORT=80

case "$1" in

  start)
    if [ -f "$PID_FILE" ]; then
      PID=$(cat "$PID_FILE")

      if kill -0 "$PID" 2>/dev/null; then
        echo "Application is already running (PID: $PID)"
        exit 1
      fi

      rm -f "$PID_FILE"
    fi

    echo "Starting application on port $PORT..."

    nohup python main.py "$PORT" > "$LOG_FILE" 2>&1 &
    PID=$!

    sleep 1

    if kill -0 "$PID" 2>/dev/null; then
      echo "$PID" > "$PID_FILE"
      echo "Application started successfully"
      echo "PID: $PID"
      echo "Port: $PORT"
    else
      echo "Failed to start application."
      echo "Check $LOG_FILE for details."
      exit 1
    fi
    ;;

  stop)
    if [ -f "$PID_FILE" ]; then
      PID=$(cat "$PID_FILE")

      if kill -0 "$PID" 2>/dev/null; then
        kill "$PID"
        echo "Application stopped (PID: $PID)"
      else
        echo "Process $PID is not running"
      fi

      rm -f "$PID_FILE"
    else
      echo "PID file not found"
    fi
    ;;

  *)
    echo "Usage: $0 {start|stop}"
    exit 1
    ;;

esac