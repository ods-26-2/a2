import html
import os
import sqlite3
import threading
import time
from contextlib import asynccontextmanager
from datetime import (
    datetime,
    timedelta,
    timezone
)
from pathlib import Path
from zoneinfo import ZoneInfo
from typing import Optional

import uvicorn
from fastapi import (
    FastAPI,
    HTTPException,
    Query
)
from fastapi.responses import HTMLResponse

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


LOCAL_TIMEZONE_NAME = os.getenv(
    "A2_LOCAL_TIMEZONE",
    "America/Sao_Paulo"
)

try:
    LOCAL_TIMEZONE = ZoneInfo(
        LOCAL_TIMEZONE_NAME
    )
except Exception:
    LOCAL_TIMEZONE = timezone.utc


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


def _dashboard_period(
    periodo
):
    """
    Retorna:
        label amigável,
        timestamp inicial ou None.
    """

    now = datetime.now(
        LOCAL_TIMEZONE
    )

    options = {
        "hoje":
            (
                "Hoje",
                int(
                    now.replace(
                        hour=0,
                        minute=0,
                        second=0,
                        microsecond=0
                    ).timestamp()
                )
            ),

        "7d":
            (
                "Últimos 7 dias",
                int(
                    (
                        now
                        - timedelta(
                            days=7
                        )
                    ).timestamp()
                )
            ),

        "30d":
            (
                "Últimos 30 dias",
                int(
                    (
                        now
                        - timedelta(
                            days=30
                        )
                    ).timestamp()
                )
            ),

        "tudo":
            (
                "Todo o histórico disponível",
                None
            )
    }

    if periodo not in options:
        periodo = "hoje"

    label, start_timestamp = (
        options[
            periodo
        ]
    )

    return (
        periodo,
        label,
        start_timestamp
    )


def _format_local_timestamp(
    timestamp
):
    try:
        return (
            datetime
            .fromtimestamp(
                int(
                    timestamp
                ),
                LOCAL_TIMEZONE
            )
            .strftime(
                "%d/%m/%Y %H:%M:%S"
            )
        )

    except Exception:
        return "-"


def _mask_cpf(
    cpf
):
    cpf = "".join(
        char
        for char in str(
            cpf or ""
        )
        if char.isdigit()
    )

    if len(cpf) != 11:
        return html.escape(
            cpf
        )

    return (
        f"{cpf[:3]}."
        "***."
        "***-"
        f"{cpf[-2:]}"
    )


def _metric_card(
    title,
    value,
    description,
    css_class=""
):
    return f"""
        <section class="metric {css_class}">
            <div class="metric-label">
                {html.escape(str(title))}
            </div>
            <div class="metric-value">
                {html.escape(str(value))}
            </div>
            <div class="metric-description">
                {html.escape(str(description))}
            </div>
        </section>
    """


@app.get(
    "/visualizar",
    response_class=HTMLResponse,
    include_in_schema=True
)
def visualizar(
    periodo: str = Query(
        default="hoje",
        description=(
            "Período do painel: "
            "hoje, 7d, 30d ou tudo."
        )
    )
):
    """
    Painel visual e simplificado dos acessos.

    Não altera os dados e não substitui /acessos.
    """

    (
        periodo,
        period_label,
        start_timestamp
    ) = _dashboard_period(
        periodo
    )

    conditions = []
    parameters = []

    if start_timestamp is not None:
        conditions.append(
            "occurred_at >= ?"
        )
        parameters.append(
            start_timestamp
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
        summary = connection.execute(
            f"""
            SELECT
                COUNT(*) AS movements,

                COALESCE(
                    SUM(
                        CASE
                            WHEN direction = 'entrada'
                            THEN 1
                            ELSE 0
                        END
                    ),
                    0
                ) AS entries,

                COALESCE(
                    SUM(
                        CASE
                            WHEN direction = 'saida'
                            THEN 1
                            ELSE 0
                        END
                    ),
                    0
                ) AS exits,

                COUNT(
                    DISTINCT cpf
                ) AS unique_people

            FROM access_logs
            {where}
            """,
            parameters
        ).fetchone()

        completed = connection.execute(
            f"""
            SELECT
                COUNT(*) AS total
            FROM (
                SELECT
                    cpf
                FROM access_logs
                {where}
                GROUP BY cpf
                HAVING
                    SUM(
                        CASE
                            WHEN direction = 'entrada'
                            THEN 1
                            ELSE 0
                        END
                    ) > 0
                    AND
                    SUM(
                        CASE
                            WHEN direction = 'saida'
                            THEN 1
                            ELSE 0
                        END
                    ) > 0
            )
            """,
            parameters
        ).fetchone()[
            "total"
        ]

        # Último movimento conhecido de cada CPF no histórico
        # retido no banco. É um indicativo operacional, não uma
        # garantia de ocupação física.
        last_state_rows = connection.execute(
            """
            SELECT
                latest.direction,
                COUNT(*) AS total
            FROM access_logs AS latest
            WHERE latest.id = (
                SELECT previous.id
                FROM access_logs AS previous
                WHERE previous.cpf = latest.cpf
                ORDER BY
                    previous.occurred_at DESC,
                    previous.id DESC
                LIMIT 1
            )
            GROUP BY latest.direction
            """
        ).fetchall()

        last_state = {
            "entrada": 0,
            "saida": 0
        }

        for row in last_state_rows:
            direction = row[
                "direction"
            ]

            if direction in last_state:
                last_state[
                    direction
                ] = row[
                    "total"
                ]

        by_turnstile = connection.execute(
            f"""
            SELECT
                turnstile_id,

                SUM(
                    CASE
                        WHEN direction = 'entrada'
                        THEN 1
                        ELSE 0
                    END
                ) AS entries,

                SUM(
                    CASE
                        WHEN direction = 'saida'
                        THEN 1
                        ELSE 0
                    END
                ) AS exits,

                COUNT(*) AS movements

            FROM access_logs
            {where}
            GROUP BY turnstile_id
            ORDER BY movements DESC,
                     turnstile_id ASC
            """,
            parameters
        ).fetchall()

        recent_rows = connection.execute(
            f"""
            SELECT
                id,
                cpf,
                direction,
                occurred_at,
                source_id,
                turnstile_id,
                media_status
            FROM access_logs
            {where}
            ORDER BY
                occurred_at DESC,
                id DESC
            LIMIT 20
            """,
            parameters
        ).fetchall()

    movements = int(
        summary[
            "movements"
        ]
    )

    entries = int(
        summary[
            "entries"
        ]
    )

    exits = int(
        summary[
            "exits"
        ]
    )

    unique_people = int(
        summary[
            "unique_people"
        ]
    )

    cards = "".join(
        [
            _metric_card(
                "Entradas registradas",
                entries,
                (
                    "Passagens confirmadas "
                    "no sentido de entrada."
                ),
                "positive"
            ),

            _metric_card(
                "Saídas registradas",
                exits,
                (
                    "Passagens confirmadas "
                    "no sentido de saída."
                ),
                "neutral"
            ),

            _metric_card(
                "Pessoas diferentes",
                unique_people,
                (
                    "CPFs distintos com pelo "
                    "menos um registro no período."
                ),
                "info"
            ),

            _metric_card(
                "Entraram e saíram",
                int(
                    completed
                ),
                (
                    "CPFs que possuem ao menos "
                    "uma entrada e uma saída "
                    "no período selecionado."
                ),
                "complete"
            ),

            _metric_card(
                "Movimentações",
                movements,
                (
                    "Total de entradas e saídas "
                    "registradas no período."
                ),
                "muted"
            ),

            _metric_card(
                "Último registro = entrada",
                int(
                    last_state[
                        "entrada"
                    ]
                ),
                (
                    "Estimativa operacional pelo "
                    "último movimento conhecido; "
                    "não representa ocupação exata."
                ),
                "warning"
            )
        ]
    )

    if by_turnstile:
        turnstile_rows = "".join(
            f"""
            <tr>
                <td>
                    {html.escape(str(row["turnstile_id"]))}
                </td>
                <td class="number">
                    {int(row["entries"] or 0)}
                </td>
                <td class="number">
                    {int(row["exits"] or 0)}
                </td>
                <td class="number strong">
                    {int(row["movements"] or 0)}
                </td>
            </tr>
            """
            for row in by_turnstile
        )
    else:
        turnstile_rows = """
            <tr>
                <td colspan="4" class="empty">
                    Nenhuma movimentação neste período.
                </td>
            </tr>
        """

    if recent_rows:
        recent_html = "".join(
            f"""
            <tr>
                <td>
                    {_format_local_timestamp(row["occurred_at"])}
                </td>
                <td>
                    {_mask_cpf(row["cpf"])}
                </td>
                <td>
                    <span class="badge {'entry' if row["direction"] == 'entrada' else 'exit'}">
                        {html.escape(str(row["direction"]).capitalize())}
                    </span>
                </td>
                <td>
                    {html.escape(str(row["turnstile_id"]))}
                </td>
                <td>
                    {html.escape(str(row["source_id"]))}
                </td>
                <td>
                    <span class="evidence">
                        {html.escape(str(row["media_status"] or "NONE"))}
                    </span>
                </td>
            </tr>
            """
            for row in recent_rows
        )
    else:
        recent_html = """
            <tr>
                <td colspan="6" class="empty">
                    Nenhum acesso registrado neste período.
                </td>
            </tr>
        """

    options = [
        (
            "hoje",
            "Hoje"
        ),
        (
            "7d",
            "Últimos 7 dias"
        ),
        (
            "30d",
            "Últimos 30 dias"
        ),
        (
            "tudo",
            "Todo o histórico"
        )
    ]

    options_html = "".join(
        f"""
        <option
            value="{value}"
            {'selected' if value == periodo else ''}
        >
            {label}
        </option>
        """
        for (
            value,
            label
        ) in options
    )

    generated_at = (
        datetime
        .now(
            LOCAL_TIMEZONE
        )
        .strftime(
            "%d/%m/%Y %H:%M:%S"
        )
    )

    document = f"""
<!doctype html>
<html lang="pt-BR">
<head>
    <meta charset="utf-8">
    <meta
        name="viewport"
        content="width=device-width, initial-scale=1"
    >
    <title>Painel de Acessos - A2</title>

    <style>
        :root {{
            color-scheme: light;
            --bg: #f4f7fb;
            --panel: #ffffff;
            --text: #172033;
            --muted: #667085;
            --border: #e4e7ec;
            --accent: #3157d5;
            --green: #16794b;
            --green-bg: #eaf8f1;
            --blue-bg: #edf3ff;
            --purple-bg: #f3efff;
            --amber: #9a6700;
            --amber-bg: #fff7df;
            --gray-bg: #f2f4f7;
        }}

        * {{
            box-sizing: border-box;
        }}

        body {{
            margin: 0;
            background: var(--bg);
            color: var(--text);
            font-family:
                Inter,
                ui-sans-serif,
                system-ui,
                -apple-system,
                BlinkMacSystemFont,
                "Segoe UI",
                sans-serif;
        }}

        .page {{
            max-width: 1240px;
            margin: 0 auto;
            padding: 32px 20px 48px;
        }}

        .header {{
            display: flex;
            align-items: flex-start;
            justify-content: space-between;
            gap: 24px;
            margin-bottom: 24px;
        }}

        h1 {{
            margin: 0 0 6px;
            font-size: clamp(26px, 4vw, 38px);
            line-height: 1.1;
        }}

        .subtitle {{
            margin: 0;
            color: var(--muted);
            max-width: 740px;
        }}

        .filter {{
            display: flex;
            align-items: center;
            gap: 8px;
            background: var(--panel);
            border: 1px solid var(--border);
            padding: 8px 10px;
            border-radius: 12px;
        }}

        .filter label {{
            color: var(--muted);
            font-size: 14px;
        }}

        .filter select {{
            border: 0;
            background: transparent;
            color: var(--text);
            font: inherit;
            font-weight: 600;
            cursor: pointer;
            outline: none;
        }}

        .metrics {{
            display: grid;
            grid-template-columns:
                repeat(3, minmax(0, 1fr));
            gap: 14px;
            margin-bottom: 22px;
        }}

        .metric {{
            background: var(--panel);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 19px;
            min-width: 0;
        }}

        .metric-label {{
            color: var(--muted);
            font-size: 14px;
            font-weight: 650;
            margin-bottom: 10px;
        }}

        .metric-value {{
            font-size: 34px;
            line-height: 1;
            font-weight: 800;
            letter-spacing: -0.04em;
            margin-bottom: 10px;
        }}

        .metric-description {{
            color: var(--muted);
            font-size: 13px;
            line-height: 1.45;
        }}

        .metric.positive {{
            background: var(--green-bg);
        }}

        .metric.info {{
            background: var(--blue-bg);
        }}

        .metric.complete {{
            background: var(--purple-bg);
        }}

        .metric.warning {{
            background: var(--amber-bg);
        }}

        .metric.muted {{
            background: var(--gray-bg);
        }}

        .grid {{
            display: grid;
            grid-template-columns:
                minmax(0, 0.9fr)
                minmax(0, 1.5fr);
            gap: 18px;
            margin-bottom: 18px;
        }}

        .panel {{
            background: var(--panel);
            border: 1px solid var(--border);
            border-radius: 16px;
            overflow: hidden;
        }}

        .panel-header {{
            padding: 18px 20px 12px;
        }}

        .panel-header h2 {{
            font-size: 18px;
            margin: 0 0 4px;
        }}

        .panel-header p {{
            margin: 0;
            color: var(--muted);
            font-size: 13px;
        }}

        .table-wrap {{
            overflow-x: auto;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            min-width: 520px;
        }}

        th,
        td {{
            text-align: left;
            padding: 12px 16px;
            border-top: 1px solid var(--border);
            font-size: 13px;
            white-space: nowrap;
        }}

        th {{
            color: var(--muted);
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 0.04em;
        }}

        .number {{
            text-align: right;
        }}

        .strong {{
            font-weight: 750;
        }}

        .badge {{
            display: inline-flex;
            align-items: center;
            border-radius: 999px;
            padding: 4px 9px;
            font-size: 12px;
            font-weight: 700;
        }}

        .badge.entry {{
            color: var(--green);
            background: var(--green-bg);
        }}

        .badge.exit {{
            color: #344054;
            background: var(--gray-bg);
        }}

        .evidence {{
            color: var(--muted);
            font-size: 12px;
            font-weight: 650;
        }}

        .empty {{
            text-align: center;
            color: var(--muted);
            padding: 28px;
        }}

        .note {{
            background: var(--amber-bg);
            border: 1px solid #f2d78b;
            border-radius: 14px;
            padding: 14px 16px;
            color: #634700;
            font-size: 13px;
            line-height: 1.5;
            margin-bottom: 18px;
        }}

        .footer {{
            display: flex;
            justify-content: space-between;
            gap: 12px;
            flex-wrap: wrap;
            color: var(--muted);
            font-size: 12px;
            margin-top: 16px;
        }}

        .footer a {{
            color: var(--accent);
            text-decoration: none;
            font-weight: 650;
        }}

        @media (max-width: 900px) {{
            .header {{
                flex-direction: column;
            }}

            .metrics {{
                grid-template-columns:
                    repeat(2, minmax(0, 1fr));
            }}

            .grid {{
                grid-template-columns: 1fr;
            }}
        }}

        @media (max-width: 560px) {{
            .page {{
                padding: 22px 12px 36px;
            }}

            .metrics {{
                grid-template-columns: 1fr;
            }}

            .filter {{
                width: 100%;
                justify-content: space-between;
            }}
        }}
    </style>
</head>

<body>
    <main class="page">
        <header class="header">
            <div>
                <h1>Painel de acessos</h1>
                <p class="subtitle">
                    Visão simplificada das movimentações
                    registradas pelo A2 — {html.escape(period_label)}.
                </p>
            </div>

            <form
                class="filter"
                method="get"
                action="/visualizar"
            >
                <label for="periodo">
                    Período
                </label>

                <select
                    id="periodo"
                    name="periodo"
                    onchange="this.form.submit()"
                >
                    {options_html}
                </select>
            </form>
        </header>

        <section class="metrics">
            {cards}
        </section>

        <div class="note">
            <strong>Importante:</strong>
            o A2 registra cada passagem confirmada, mas atualmente
            não aplica regra de anti-reentrada. Por isso,
            “Último registro = entrada” é somente um indicativo
            baseado no último evento conhecido de cada CPF e não
            deve ser interpretado como contagem física exata de
            pessoas presentes.
        </div>

        <section class="grid">
            <div class="panel">
                <div class="panel-header">
                    <h2>Movimento por catraca</h2>
                    <p>
                        Entradas e saídas no período selecionado.
                    </p>
                </div>

                <div class="table-wrap">
                    <table>
                        <thead>
                            <tr>
                                <th>Catraca</th>
                                <th class="number">Entradas</th>
                                <th class="number">Saídas</th>
                                <th class="number">Total</th>
                            </tr>
                        </thead>
                        <tbody>
                            {turnstile_rows}
                        </tbody>
                    </table>
                </div>
            </div>

            <div class="panel">
                <div class="panel-header">
                    <h2>Últimos registros</h2>
                    <p>
                        Os 20 eventos mais recentes do período.
                    </p>
                </div>

                <div class="table-wrap">
                    <table>
                        <thead>
                            <tr>
                                <th>Horário</th>
                                <th>CPF</th>
                                <th>Movimento</th>
                                <th>Catraca</th>
                                <th>Câmera</th>
                                <th>Evidência</th>
                            </tr>
                        </thead>
                        <tbody>
                            {recent_html}
                        </tbody>
                    </table>
                </div>
            </div>
        </section>

        <footer class="footer">
            <span>
                Atualizado em {generated_at}
                ({html.escape(LOCAL_TIMEZONE_NAME)})
            </span>

            <span>
                <a href="/acessos">Dados em JSON</a>
                &nbsp;·&nbsp;
                <a href="/docs">Swagger / API</a>
            </span>
        </footer>
    </main>
</body>
</html>
    """

    return HTMLResponse(
        content=document
    )


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
