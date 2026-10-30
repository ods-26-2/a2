import os
import sqlite3
import threading
import time
from contextlib import asynccontextmanager
from datetime import (
    datetime,
    timezone
)
from pathlib import Path
from typing import Optional

import uvicorn
from fastapi import (
    FastAPI,
    HTTPException,
    Query
)

from database import (
    ensure_access_logs_schema
)


DATABASE_FILE = Path(
    os.getenv(
        "A2_DATABASE_FILE",
        str(
            Path(__file__)
            .with_name(
                "acessos.db"
            )
        )
    )
)

RETENTION_DAYS = int(
    os.getenv(
        "A2_LOG_RETENTION_DAYS",
        "30"
    )
)

RETENTION_SECONDS = (
    RETENTION_DAYS
    * 24
    * 60
    * 60
)

CLEANUP_INTERVAL_SECONDS = int(
    os.getenv(
        "A2_LOG_CLEANUP_INTERVAL_SECONDS",
        str(
            6 * 60 * 60
        )
    )
)

API_HOST = os.getenv(
    "A2_LOG_API_HOST",
    "0.0.0.0"
)

API_PORT = int(
    os.getenv(
        "A2_LOG_API_PORT",
        "8001"
    )
)


def get_connection():
    DATABASE_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    connection = sqlite3.connect(
        DATABASE_FILE,
        timeout=10
    )

    connection.row_factory = (
        sqlite3.Row
    )

    connection.execute(
        "PRAGMA busy_timeout = 10000"
    )

    connection.execute(
        "PRAGMA journal_mode = WAL"
    )

    return connection


def ensure_database():
    with get_connection() as connection:
        ensure_access_logs_schema(
            connection
        )


def cleanup_old_logs():
    cutoff = (
        int(
            time.time()
        )
        - RETENTION_SECONDS
    )

    with get_connection() as connection:
        cursor = connection.execute(
            """
            DELETE FROM access_logs
            WHERE occurred_at < ?
            """,
            (
                cutoff,
            )
        )

        deleted = (
            cursor.rowcount
        )

        connection.commit()

    if deleted > 0:
        print(
            "Limpeza automática: "
            f"{deleted} registro(s) "
            f"com mais de "
            f"{RETENTION_DAYS} dias "
            "removido(s)."
        )

    return deleted


def parse_time_filter(
    value
):
    if value is None:
        return None

    value = value.strip()

    try:
        return int(
            value
        )
    except ValueError:
        pass

    try:
        parsed = datetime.fromisoformat(
            value.replace(
                "Z",
                "+00:00"
            )
        )
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=(
                "Data inválida. "
                "Use timestamp Unix "
                "ou ISO 8601."
            )
        )

    if parsed.tzinfo is None:
        parsed = parsed.replace(
            tzinfo=timezone.utc
        )

    return int(
        parsed.timestamp()
    )


def serialize_log(
    row
):
    occurred_at = int(
        row[
            "occurred_at"
        ]
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
        "id":
            row["id"],

        "cpf":
            row["cpf"],

        "direction":
            row["direction"],

        "occurred_at":
            occurred_at,

        "occurred_at_iso":
            occurred_at_iso,

        "source_id":
            row["source_id"],

        "turnstile_id":
            row["turnstile_id"],

        "i6_message_id":
            row["i6_message_id"],

        "frame_index":
            row["frame_index"],

        "captured_at":
            row["captured_at"],

        "evidence": {
            "status":
                row[
                    "media_status"
                ],

            "request_id":
                row[
                    "media_request_id"
                ],

            "clip_id":
                row[
                    "media_clip_id"
                ],

            "media_type":
                row[
                    "media_type"
                ],

            "media_uri":
                row[
                    "media_uri"
                ],

            "hash_sha256":
                row[
                    "media_hash_sha256"
                ],

            "expires_at":
                row[
                    "media_expires_at"
                ]
        }
    }


SELECT_COLUMNS = """
    id,
    cpf,
    direction,
    occurred_at,
    source_id,
    turnstile_id,
    i6_message_id,
    frame_index,
    captured_at,
    media_request_id,
    media_clip_id,
    media_type,
    media_uri,
    media_hash_sha256,
    media_expires_at,
    media_status
"""


@asynccontextmanager
async def lifespan(
    app
):
    ensure_database()
    cleanup_old_logs()

    stop_event = (
        threading.Event()
    )

    def cleanup_worker():
        while not stop_event.wait(
            CLEANUP_INTERVAL_SECONDS
        ):
            try:
                cleanup_old_logs()

            except Exception as error:
                print(
                    "Erro na limpeza "
                    f"automática: {error}"
                )

    cleanup_thread = (
        threading.Thread(
            target=cleanup_worker,
            daemon=True
        )
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
    title="API Local de Acessos",
    version="1.3",
    lifespan=lifespan
)


@app.get(
    "/health"
)
def health():
    return {
        "status":
            "ok",

        "database":
            str(
                DATABASE_FILE
            ),

        "retention_days":
            RETENTION_DAYS
    }


@app.get(
    "/acessos"
)
def get_access_logs(
    cpf: Optional[str] = None,
    direction: Optional[str] = None,
    source_id: Optional[str] = None,
    turnstile_id: Optional[str] = None,
    media_status: Optional[str] = None,
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

    if source_id is not None:
        conditions.append(
            "source_id = ?"
        )
        parameters.append(
            source_id
        )

    if turnstile_id is not None:
        conditions.append(
            "turnstile_id = ?"
        )
        parameters.append(
            turnstile_id
        )

    if media_status is not None:
        media_status = (
            media_status
            .strip()
            .upper()
        )

        if media_status not in (
            "NONE",
            "PENDING",
            "READY",
            "ERROR"
        ):
            raise HTTPException(
                status_code=400,
                detail=(
                    "media_status deve ser "
                    "NONE, PENDING, READY ou ERROR."
                )
            )

        conditions.append(
            "media_status = ?"
        )

        parameters.append(
            media_status
        )

    inicio_timestamp = (
        parse_time_filter(
            inicio
        )
    )

    fim_timestamp = (
        parse_time_filter(
            fim
        )
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
        inicio_timestamp
        is not None
        and fim_timestamp
        is not None
        and inicio_timestamp
        > fim_timestamp
    ):
        raise HTTPException(
            status_code=400,
            detail=(
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
        ).fetchone()[
            "total"
        ]

        rows = connection.execute(
            f"""
            SELECT
                {SELECT_COLUMNS}
            FROM access_logs
            {where}
            ORDER BY
                occurred_at DESC,
                id DESC
            LIMIT ? OFFSET ?
            """,
            parameters
            + [
                limit,
                offset
            ]
        ).fetchall()

    return {
        "total":
            total,

        "limit":
            limit,

        "offset":
            offset,

        "data": [
            serialize_log(
                row
            )
            for row
            in rows
        ]
    }


@app.get(
    "/acessos/{log_id}"
)
def get_access_log(
    log_id: int
):
    with get_connection() as connection:
        row = connection.execute(
            f"""
            SELECT
                {SELECT_COLUMNS}
            FROM access_logs
            WHERE id = ?
            """,
            (
                log_id,
            )
        ).fetchone()

    if row is None:
        raise HTTPException(
            status_code=404,
            detail=(
                "Registro não encontrado."
            )
        )

    return serialize_log(
        row
    )


@app.post(
    "/manutencao/limpar"
)
def run_cleanup():
    deleted = cleanup_old_logs()

    return {
        "deleted":
            deleted,

        "retention_days":
            RETENTION_DAYS
    }


if __name__ == "__main__":
    uvicorn.run(
        app,
        host=API_HOST,
        port=API_PORT
    )
