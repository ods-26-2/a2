import sqlite3


def _column_names(connection):
    return {
        row[1]
        for row in connection.execute(
            "PRAGMA table_info(access_logs)"
        ).fetchall()
    }


def _add_column_if_missing(
    connection,
    column_name,
    sql_definition
):
    columns = _column_names(
        connection
    )

    if column_name in columns:
        return

    try:
        connection.execute(
            f"""
            ALTER TABLE access_logs
            ADD COLUMN {column_name} {sql_definition}
            """
        )

    except sqlite3.OperationalError as error:
        # Proteção contra corrida entre liberar.py e acessos_api.py
        # iniciando ao mesmo tempo no mesmo banco.
        if (
            "duplicate column name"
            not in str(error).lower()
        ):
            raise


def ensure_access_logs_schema(
    connection
):
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS access_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cpf TEXT NOT NULL,
            direction TEXT NOT NULL,
            occurred_at INTEGER NOT NULL,
            source_id TEXT NOT NULL,
            turnstile_id TEXT NOT NULL,

            i6_message_id TEXT,
            frame_index INTEGER,
            captured_at TEXT,

            media_request_id TEXT,
            media_clip_id TEXT,
            media_type TEXT,
            media_uri TEXT,
            media_hash_sha256 TEXT,
            media_expires_at TEXT,
            media_status TEXT NOT NULL DEFAULT 'NONE'
        )
        """
    )

    columns = _column_names(
        connection
    )

    # Compatibilidade com bancos antigos.
    if (
        "camera_id" in columns
        and "source_id" not in columns
    ):
        try:
            connection.execute(
                """
                ALTER TABLE access_logs
                RENAME COLUMN camera_id TO source_id
                """
            )
        except sqlite3.OperationalError as error:
            if (
                "duplicate column name"
                not in str(error).lower()
                and "no such column"
                not in str(error).lower()
            ):
                raise

    _add_column_if_missing(
        connection,
        "i6_message_id",
        "TEXT"
    )

    _add_column_if_missing(
        connection,
        "frame_index",
        "INTEGER"
    )

    _add_column_if_missing(
        connection,
        "captured_at",
        "TEXT"
    )

    _add_column_if_missing(
        connection,
        "media_request_id",
        "TEXT"
    )

    _add_column_if_missing(
        connection,
        "media_clip_id",
        "TEXT"
    )

    _add_column_if_missing(
        connection,
        "media_type",
        "TEXT"
    )

    _add_column_if_missing(
        connection,
        "media_uri",
        "TEXT"
    )

    _add_column_if_missing(
        connection,
        "media_hash_sha256",
        "TEXT"
    )

    _add_column_if_missing(
        connection,
        "media_expires_at",
        "TEXT"
    )

    _add_column_if_missing(
        connection,
        "media_status",
        "TEXT NOT NULL DEFAULT 'NONE'"
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

    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_access_logs_source_id
        ON access_logs(source_id)
        """
    )

    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_access_logs_i6_message_id
        ON access_logs(i6_message_id)
        """
    )

    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_access_logs_media_request_id
        ON access_logs(media_request_id)
        """
    )

    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_access_logs_media_clip_id
        ON access_logs(media_clip_id)
        """
    )

    connection.commit()
