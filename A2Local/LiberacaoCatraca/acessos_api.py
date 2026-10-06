import sqlite3
import threading
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import uvicorn
from fastapi import FastAPI, HTTPException, Query

DATABASE_FILE = Path(__file__).with_name("acessos.db")

RETENTION_DAYS = 30
RETENTION_SECONDS = RETENTION_DAYS * 24 * 60 * 60
CLEANUP_INTERVAL_SECONDS = 6 * 60 * 60

def get_connection():
    connection = sqlite3.connect(
        DATABASE_FILE,
        timeout=10
    )

    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA busy_timeout = 10000")
    connection.execute("PRAGMA journal_mode = WAL")

    return connection

def ensure_database():
    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS access_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cpf TEXT NOT NULL,
                direction TEXT NOT NULL,
                occurred_at INTEGER NOT NULL,
                camera_id TEXT NOT NULL,
                turnstile_id TEXT NOT NULL
            )
            """
        )

        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_access_logs_cpf
            ON access_logs(cpf)
            """
        )

        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_access_logs_occurred_at
            ON access_logs(occurred_at)
            """
        )

        connection.commit()

def cleanup_old_logs():
    cutoff = int(time.time()) - RETENTION_SECONDS

    with get_connection() as connection:
        cursor = connection.execute(
            """
            DELETE FROM access_logs
            WHERE occurred_at < ?
            """,
            (cutoff,)
        )

        deleted = cursor.rowcount
        connection.commit()

    if deleted > 0:
        print(
            f"Limpeza automática: "
            f"{deleted} registro(s) com mais de "
            f"{RETENTION_DAYS} dias removido(s)."
        )

    return deleted

def parse_time_filter(value):
    if value is None:
        return None

    value = value.strip()

    try:
        return int(value)

    except ValueError:
        pass

    try:
        parsed = datetime.fromisoformat(
            value.replace("Z", "+00:00")
        )

    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=(
                "Data inválida. Use timestamp Unix ou "
                "ISO 8601, por exemplo "
                "2026-09-29T15:00:00-03:00."
            )
        )

    if parsed.tzinfo is None:
        parsed = parsed.replace(
            tzinfo=timezone.utc
        )

    return int(parsed.timestamp())

def serialize_log(row):
    occurred_at = int(
        row["occurred_at"]
    )

    occurred_at_iso = (
        datetime
        .fromtimestamp(
            occurred_at,
            timezone.utc
        )
        .isoformat()
        .replace(
            "+00:00",
            "Z"
        )
    )

    return {
        "id": row["id"],
        "cpf": row["cpf"],
        "direction": row["direction"],
        "occurred_at": occurred_at,
        "occurred_at_iso": occurred_at_iso,
        "camera_id": row["camera_id"],
        "turnstile_id": row["turnstile_id"]
    }

@asynccontextmanager
async def lifespan(app):
    ensure_database()
    cleanup_old_logs()

    stop_event = threading.Event()

    def cleanup_worker():
        while not stop_event.wait(
            CLEANUP_INTERVAL_SECONDS
        ):
            try:
                cleanup_old_logs()

            except Exception as e:
                print(
                    f"Erro na limpeza automática: {e}"
                )

    cleanup_thread = threading.Thread(
        target=cleanup_worker,
        daemon=True
    )

    cleanup_thread.start()

    try:
        yield

    finally:
        stop_event.set()
        cleanup_thread.join(
            timeout=1
        )

app = FastAPI(
    title="API de Acessos",
    version="1.0",
    lifespan=lifespan
)

@app.get("/health")
def health():
    return {
        "status": "ok",
        "database": str(DATABASE_FILE),
        "retention_days": RETENTION_DAYS
    }

@app.get("/acessos")
def get_access_logs(
    cpf: Optional[str] = None,
    direction: Optional[str] = None,
    camera_id: Optional[str] = None,
    turnstile_id: Optional[str] = None,
    inicio: Optional[str] = None,
    fim: Optional[str] = None,
    limit: int = Query(
        default=1000,
        ge=1,
        le=5000
    ),
    offset: int = Query(
        default=0,
        ge=0
    )
):
    conditions = []
    parameters = []

    if cpf is not None:
        conditions.append(
            "cpf = ?"
        )

        parameters.append(
            cpf
        )

    if direction is not None:
        direction = (
            direction
            .strip()
            .lower()
        )

        if direction not in (
            "entrada",
            "saida"
        ):
            raise HTTPException(
                status_code=400,
                detail=(
                    "direction deve ser "
                    "'entrada' ou 'saida'."
                )
            )

        conditions.append(
            "direction = ?"
        )

        parameters.append(
            direction
        )

    if camera_id is not None:
        conditions.append(
            "camera_id = ?"
        )

        parameters.append(
            camera_id
        )

    if turnstile_id is not None:
        conditions.append(
            "turnstile_id = ?"
        )

        parameters.append(
            turnstile_id
        )

    inicio_timestamp = parse_time_filter(
        inicio
    )

    fim_timestamp = parse_time_filter(
        fim
    )

    if inicio_timestamp is not None:
        conditions.append(
            "occurred_at >= ?"
        )

        parameters.append(
            inicio_timestamp
        )

    if fim_timestamp is not None:
        conditions.append(
            "occurred_at <= ?"
        )

        parameters.append(
            fim_timestamp
        )

    if (
        inicio_timestamp is not None
        and fim_timestamp is not None
        and inicio_timestamp > fim_timestamp
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "O período informado é inválido: "
                "inicio é maior que fim."
            )
        )

    where = ""

    if conditions:
        where = (
            "WHERE "
            + " AND ".join(
                conditions
            )
        )

    with get_connection() as connection:
        total = connection.execute(
            f"""
            SELECT COUNT(*) AS total
            FROM access_logs
            {where}
            """,
            parameters
        ).fetchone()["total"]

        rows = connection.execute(
            f"""
            SELECT
                id,
                cpf,
                direction,
                occurred_at,
                camera_id,
                turnstile_id
            FROM access_logs
            {where}
            ORDER BY occurred_at DESC, id DESC
            LIMIT ? OFFSET ?
            """,
            parameters
            + [
                limit,
                offset
            ]
        ).fetchall()

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "data": [
            serialize_log(row)
            for row in rows
        ]
    }

@app.get("/acessos/{log_id}")
def get_access_log(log_id: int):
    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT
                id,
                cpf,
                direction,
                occurred_at,
                camera_id,
                turnstile_id
            FROM access_logs
            WHERE id = ?
            """,
            (log_id,)
        ).fetchone()

    if row is None:
        raise HTTPException(
            status_code=404,
            detail="Registro não encontrado."
        )

    return serialize_log(row)

@app.post("/manutencao/limpar")
def run_cleanup():
    deleted = cleanup_old_logs()

    return {
        "deleted": deleted,
        "retention_days": RETENTION_DAYS
    }

if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8001
    )
