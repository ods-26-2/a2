import sys
import json
import sqlite3
from pathlib import Path
from datetime import datetime, date, timedelta
from typing import Optional, Dict, Any, Tuple, List, Union
import bcrypt

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

import config

DB_PATH = config.DB_PATH
DEFAULT_PAYLOAD_BATCH_SIZE = config.PAYLOAD_BATCH_SIZE

_db_initialized = False


def hash_password(password: str) -> str:
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def check_password(password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False


def get_connection() -> sqlite3.Connection:
    global _db_initialized
    db_file = Path(DB_PATH)
    db_file.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(db_file), check_same_thread=False, timeout=10.0)
    conn.row_factory = sqlite3.Row

    if not _db_initialized:
        _db_initialized = True
        _init_schema(conn)

    return conn


def _init_schema(conn: sqlite3.Connection):
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            cpf INTEGER PRIMARY KEY,
            password_hash TEXT NOT NULL,
            is_recurring INTEGER NOT NULL DEFAULT 1,
            specific_date DATE,
            expiration_date DATE,
            access_days TEXT NOT NULL,
            access_hours TEXT NOT NULL,
            active INTEGER NOT NULL DEFAULT 1,
            created_at DATETIME NOT NULL,
            updated_at DATETIME NOT NULL
        )
    """)

    cursor.execute("PRAGMA table_info(users)")
    existing_cols = [row[1] for row in cursor.fetchall()]
    if "expiration_date" not in existing_cols:
        cursor.execute("ALTER TABLE users ADD COLUMN expiration_date DATE")


    cursor.execute("""
        CREATE TABLE IF NOT EXISTS system_config (
            key TEXT PRIMARY KEY,
            payload_batch_size INTEGER NOT NULL DEFAULT 10,
            updated_at DATETIME NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS admins (
            username TEXT PRIMARY KEY,
            password_hash TEXT NOT NULL,
            created_at DATETIME NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS api_keys (
            id INTEGER PRIMARY KEY,
            key TEXT NOT NULL UNIQUE,
            active INTEGER NOT NULL DEFAULT 1,
            created_at DATETIME NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS api_keys (
            id INTEGER PRIMARY KEY,
            key TEXT NOT NULL UNIQUE,
            active INTEGER NOT NULL DEFAULT 1,
            created_at DATETIME NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_sessions (
            token TEXT PRIMARY KEY,
            cpf INTEGER NOT NULL,
            created_at DATETIME NOT NULL,
            expires_at DATETIME NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS admin_tokens (
            token TEXT PRIMARY KEY,
            username TEXT NOT NULL,
            created_at DATETIME NOT NULL,
            expires_at DATETIME NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS access_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cpf INTEGER,
            direction TEXT,
            device_id TEXT,
            status TEXT,
            event_timestamp DATETIME,
            raw_payload TEXT,
            created_at DATETIME NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS building_presence (
            cpf INTEGER PRIMARY KEY,
            is_inside INTEGER NOT NULL DEFAULT 0,
            last_direction TEXT,
            last_device_id TEXT,
            last_entry_at DATETIME,
            last_exit_at DATETIME,
            updated_at DATETIME NOT NULL
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_presence_is_inside ON building_presence(is_inside)")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS building_metrics (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            people_count INTEGER NOT NULL DEFAULT 0,
            total_entries_today INTEGER NOT NULL DEFAULT 0,
            total_exits_today INTEGER NOT NULL DEFAULT 0,
            metric_date DATE NOT NULL,
            last_event_at DATETIME,
            updated_at DATETIME NOT NULL
        )
    """)

    today_dt = datetime.now().strftime("%Y-%m-%d")
    now_dt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
        INSERT OR IGNORE INTO building_metrics (id, people_count, total_entries_today, total_exits_today, metric_date, last_event_at, updated_at)
        VALUES (1, 0, 0, 0, ?, NULL, ?)
    """, (today_dt, now_dt))
    conn.commit()

    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        seed_default_data(conn)

    cursor.execute("SELECT COUNT(*) FROM admins")
    if cursor.fetchone()[0] == 0:
        now_dt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
            INSERT OR IGNORE INTO admins (username, password_hash, created_at)
            VALUES (?, ?, ?)
        """, ("admin", hash_password("admin123"), now_dt))
        conn.commit()



def seed_default_data(conn: sqlite3.Connection, force: bool = False):
    cursor = conn.cursor()
    now_dt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    tomorrow_date = (datetime.now().date() + timedelta(days=1)).strftime("%Y-%m-%d")

    default_users = [ # usuário para testes
        {
            "cpf": 12345678900,
            "password": "teste",
            "is_recurring": 1,
            "specific_date": None,
            "access_days": [0, 1, 2, 3, 4],  # Segunda a Sexta
            "access_hours": {"start": "08:00", "end": "18:00"},
            "active": 1,
        }
    ]

    for user in default_users:
        if force:
            cursor.execute("DELETE FROM users WHERE cpf = ?", (user["cpf"],))

        cursor.execute("""
            INSERT OR IGNORE INTO users (
                cpf, password_hash, is_recurring, specific_date,
                access_days, access_hours, active, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            user["cpf"],
            hash_password(user["password"]),
            user["is_recurring"],
            user["specific_date"],
            json.dumps(user["access_days"]),
            json.dumps(user["access_hours"]),
            user["active"],
            now_dt,
            now_dt,
        ))

    cursor.execute("""
        INSERT OR IGNORE INTO system_config (key, payload_batch_size, updated_at)
        VALUES (?, ?, ?)
    """, ("system_settings", DEFAULT_PAYLOAD_BATCH_SIZE, now_dt))

    conn.commit()


def init_db(force: bool = False):
    conn = get_connection()
    try:
        _init_schema(conn)
        if force:
            seed_default_data(conn, force=True)
    finally:
        conn.close()


def add_user(
    cpf: int,
    password: Optional[str] = None,
    is_recurring: bool = True,
    specific_date: Optional[Union[str, date, datetime]] = None,
    expiration_date: Optional[Union[str, date, datetime]] = None,
    access_days: Optional[List[int]] = None,
    access_hours: Optional[Dict[str, str]] = None,
) -> bool:
    """Adiciona ou atualiza um usuário no banco SQLite identificado apenas por CPF.
    
    is_recurring:
      - True (padrão): acesso recorrente baseado em access_days (dias 0 a 6).
      - False: acesso único baseado em specific_date ('YYYY-MM-DD').
    expiration_date:
      - Data limite até a qual o crachá/recorrência é válido ('YYYY-MM-DD').
    """
    conn = get_connection()
    try:
        now_dt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if access_days is None:
            access_days = [0, 1, 2, 3, 4] if is_recurring else []
        if access_hours is None:
            access_hours = {"start": "08:00", "end": "18:00"}

        date_str = None
        if specific_date:
            if isinstance(specific_date, (datetime, date)):
                date_str = specific_date.strftime("%Y-%m-%d")
            else:
                date_str = str(specific_date).strip()[:10]

        exp_str = None
        if expiration_date:
            if isinstance(expiration_date, (datetime, date)):
                exp_str = expiration_date.strftime("%Y-%m-%d")
            else:
                exp_str = str(expiration_date).strip()[:10]

        cursor = conn.cursor()

        if password:
            password_hash_value = hash_password(password)
        else:
            cursor.execute("SELECT password_hash FROM users WHERE cpf = ?", (int(cpf),))
            existing_row = cursor.fetchone()
            if not existing_row:
                return False
            password_hash_value = existing_row["password_hash"]

        cursor.execute("""
            INSERT INTO users (
                cpf, password_hash, is_recurring, specific_date, expiration_date,
                access_days, access_hours, active, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
            ON CONFLICT(cpf) DO UPDATE SET
                password_hash = excluded.password_hash,
                is_recurring = excluded.is_recurring,
                specific_date = excluded.specific_date,
                expiration_date = excluded.expiration_date,
                access_days = excluded.access_days,
                access_hours = excluded.access_hours,
                updated_at = excluded.updated_at
        """, (
            int(cpf),
            password_hash_value,
            1 if is_recurring else 0,
            date_str,
            exp_str,
            json.dumps(access_days),
            json.dumps(access_hours),
            now_dt,
            now_dt,
        ))
        conn.commit()
        return True
    finally:
        conn.close()


def _parse_user_row(row: sqlite3.Row) -> Dict[str, Any]:
    user = dict(row)
    if isinstance(user.get("access_days"), str):
        try:
            user["access_days"] = json.loads(user["access_days"])
        except Exception:
            user["access_days"] = []
    if isinstance(user.get("access_hours"), str):
        try:
            user["access_hours"] = json.loads(user["access_hours"])
        except Exception:
            user["access_hours"] = {}
    user["active"] = bool(user.get("active", 1))
    user["is_recurring"] = bool(user.get("is_recurring", 1))
    user["specific_date"] = user.get("specific_date")
    user["expiration_date"] = user.get("expiration_date")
    return user



def get_user_by_cpf(cpf: int) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE cpf = ?", (int(cpf),))
        row = cursor.fetchone()
        if not row:
            return None
        return _parse_user_row(row)
    finally:
        conn.close()


def validate_user_access(cpf: int, password: str) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    try:
        user = get_user_by_cpf(cpf)
        if not user:
            return False, "Usuário não encontrado", None

        password_hash = user.get("password_hash", "")
        if not check_password(password, password_hash):
            return False, "Senha incorreta", None

        if user.get("expiration_date"):
            try:
                exp_date = date.fromisoformat(str(user["expiration_date"])[:10])
                if date.today() > exp_date:
                    return False, f"Acesso recorrente expirado em {exp_date.strftime('%d/%m/%Y')}", None
            except Exception:
                pass

        if not user.get("is_recurring", True) and user.get("specific_date"):
            try:
                spec_date = date.fromisoformat(str(user["specific_date"])[:10])
                if date.today() > spec_date:
                    return False, f"Acesso válido apenas para a data {spec_date.strftime('%d/%m/%Y')}", None
            except Exception:
                pass

        return True, "Autenticado com sucesso", user

    except Exception as e:
        return False, f"Erro ao acessar banco de dados: {str(e)}", None


def get_system_config() -> Dict[str, Any]:
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM system_config WHERE key = ?", ("system_settings",))
        row = cursor.fetchone()
        if not row:
            now_dt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute(
                "INSERT INTO system_config (key, payload_batch_size, updated_at) VALUES (?, ?, ?)",
                ("system_settings", DEFAULT_PAYLOAD_BATCH_SIZE, now_dt)
            )
            conn.commit()
            return {
                "key": "system_settings",
                "payload_batch_size": DEFAULT_PAYLOAD_BATCH_SIZE,
                "updated_at": now_dt,
            }
        return dict(row)
    finally:
        conn.close()


def get_payload_batch_size() -> int:
    config_data = get_system_config()
    return int(config_data.get("payload_batch_size", DEFAULT_PAYLOAD_BATCH_SIZE))


def set_payload_batch_size(new_batch_size: int) -> bool:
    try:
        conn = get_connection()
        try:
            now_dt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO system_config (key, payload_batch_size, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    payload_batch_size = excluded.payload_batch_size,
                    updated_at = excluded.updated_at
                """,
                ("system_settings", int(new_batch_size), now_dt)
            )
            conn.commit()
            return True
        finally:
            conn.close()
    except Exception:
        return False


def get_all_users() -> List[Dict[str, Any]]:
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users ORDER BY created_at DESC")
        rows = cursor.fetchall()
        return [_parse_user_row(row) for row in rows]
    finally:
        conn.close()


def delete_user_by_cpf(cpf: int) -> bool:
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM users WHERE cpf = ?", (int(cpf),))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()





def update_admin_password(username: str, new_password: str) -> bool:
    try:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE admins SET password_hash = ? WHERE username = ?",
                (hash_password(new_password), username.strip()),
            )
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()
    except Exception:
        return False


def validate_admin_credentials(username: str, password: str) -> bool:
    if not username or not password:
        return False
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT password_hash FROM admins WHERE username = ?", (username.strip(),))
        row = cursor.fetchone()
        if not row:
            return False
        return check_password(password, row["password_hash"])
    finally:
        conn.close()


def create_admin_session(username: str, duration_hours: int = 24) -> str:
    import secrets
    token = secrets.token_hex(32)
    now = datetime.now()
    now_dt = now.strftime("%Y-%m-%d %H:%M:%S")
    exp_dt = (now + timedelta(hours=duration_hours)).strftime("%Y-%m-%d %H:%M:%S")
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO admin_tokens (token, username, created_at, expires_at)
            VALUES (?, ?, ?, ?)
            """,
            (token, username.strip(), now_dt, exp_dt),
        )
        conn.commit()
        return token
    finally:
        conn.close()


def verify_admin_session(token: str) -> Optional[str]:
    if not token:
        return None
    conn = get_connection()
    try:
        now_dt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT username FROM admin_tokens
            WHERE token = ? AND expires_at > ?
            """,
            (token.strip(), now_dt),
        )
        row = cursor.fetchone()
        return row["username"] if row else None
    finally:
        conn.close()


def delete_admin_session(token: str) -> bool:
    if not token:
        return False
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM admin_tokens WHERE token = ?", (token.strip(),))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def get_api_key() -> "Optional[Dict[str, Any]]":
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM api_keys ORDER BY id DESC LIMIT 1")
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def create_or_regenerate_api_key() -> str:
    import secrets
    new_key = secrets.token_hex(32)
    conn = get_connection()
    try:
        now_dt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM api_keys ORDER BY id DESC LIMIT 1")
        row = cursor.fetchone()
        if row:
            cursor.execute(
                "UPDATE api_keys SET key = ?, active = 1, created_at = ? WHERE id = ?",
                (new_key, now_dt, row["id"]),
            )
        else:
            cursor.execute(
                "INSERT INTO api_keys (key, active, created_at) VALUES (?, ?, ?)",
                (new_key, 1, now_dt),
            )
        conn.commit()
        return new_key
    finally:
        conn.close()


def set_api_key_active(active: bool) -> bool:
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE api_keys SET active = ? WHERE id = (SELECT id FROM api_keys ORDER BY id DESC LIMIT 1)",
            (1 if active else 0,),
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def validate_api_key(key: str) -> bool:
    if not key:
        return False
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT active FROM api_keys WHERE key = ? LIMIT 1", (key.strip(),))
        row = cursor.fetchone()
        return bool(row and row["active"])
    finally:
        conn.close()


def create_user_session(cpf: int, duration_hours: int = 24) -> str:
    import secrets
    token = secrets.token_hex(32)
    now = datetime.now()
    now_dt = now.strftime("%Y-%m-%d %H:%M:%S")
    exp_dt = (now + timedelta(hours=duration_hours)).strftime("%Y-%m-%d %H:%M:%S")
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO user_sessions (token, cpf, created_at, expires_at) VALUES (?, ?, ?, ?)",
            (token, int(cpf), now_dt, exp_dt),
        )
        conn.commit()
        return token
    finally:
        conn.close()


def verify_user_session(token: str) -> Optional[int]:
    if not token:
        return None
    conn = get_connection()
    try:
        now_dt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor = conn.cursor()
        cursor.execute(
            "SELECT cpf FROM user_sessions WHERE token = ? AND expires_at > ?",
            (token.strip(), now_dt),
        )
        row = cursor.fetchone()
        return int(row["cpf"]) if row else None
    finally:
        conn.close()


def delete_user_session(token: str) -> bool:
    if not token:
        return False
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM user_sessions WHERE token = ?", (token.strip(),))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def delete_admin_sessions(username: str) -> bool:
    if not username:
        return False
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM admin_tokens WHERE username = ?", (username.strip(),))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def record_access_event(
    cpf: Optional[int] = None,
    direction: Optional[str] = None,
    device_id: Optional[str] = None,
    status: Optional[str] = "granted",
    event_timestamp: Optional[str] = None,
    raw_payload: Optional[Dict[str, Any]] = None,
) -> int:
    now_dt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ts = event_timestamp or now_dt
    raw_json = json.dumps(raw_payload or {}, ensure_ascii=False)
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO access_events (cpf, direction, device_id, status, event_timestamp, raw_payload, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                int(cpf) if cpf is not None else None,
                direction,
                str(device_id) if device_id is not None else None,
                status,
                ts,
                raw_json,
                now_dt,
            ),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def get_recent_access_events(limit: int = 50) -> List[Dict[str, Any]]:
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT * FROM access_events
            ORDER BY id DESC
            LIMIT ?
            """,
            (max(1, min(limit, 500)),),
        )
        rows = cursor.fetchall()
        result = []
        for r in rows:
            d = dict(r)
            if d.get("raw_payload"):
                try:
                    d["raw_payload"] = json.loads(d["raw_payload"])
                except Exception:
                    pass
            result.append(d)
        return result
    finally:
        conn.close()


def process_access_event(
    cpf: Optional[int] = None,
    direction: Optional[str] = None,
    device_id: Optional[str] = None,
    status: Optional[str] = "granted",
    event_timestamp: Optional[str] = None,
    raw_payload: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Processa um evento de acesso de forma incremental (O(1)).
    
    Atualiza:
    1. access_events: log completo do evento
    2. building_presence: tabela indexada por CPF informando se está dentro (is_inside=1) ou fora (0)
    3. building_metrics: contador de pessoas presentes e totais diários (sem recalcular histórico)
    """
    now_dt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    today_dt = datetime.now().strftime("%Y-%m-%d")
    ts = event_timestamp or now_dt

    # Normalização de status e direção
    st = (status or "granted").strip().lower()
    is_granted = st in ("granted", "liberado", "autorizado", "ok", "success", "1", "true")

    d = (direction or "entrada").strip().lower()
    is_entry = d in ("entrada", "entry", "in", "e", "1")
    resolved_direction = "entrada" if is_entry else "saida"

    raw_json = json.dumps(raw_payload or {}, ensure_ascii=False)

    conn = get_connection()
    try:
        cursor = conn.cursor()

        # 1. Grava no log de eventos
        cursor.execute(
            """
            INSERT INTO access_events (cpf, direction, device_id, status, event_timestamp, raw_payload, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                int(cpf) if cpf is not None else None,
                resolved_direction,
                str(device_id) if device_id is not None else None,
                status or "granted",
                ts,
                raw_json,
                now_dt,
            ),
        )
        event_id = cursor.lastrowid

        # 2. Carrega métricas atuais
        cursor.execute("SELECT people_count, total_entries_today, total_exits_today, metric_date FROM building_metrics WHERE id = 1")
        row_metrics = cursor.fetchone()
        if row_metrics:
            current_people = row_metrics["people_count"]
            entries_today = row_metrics["total_entries_today"]
            exits_today = row_metrics["total_exits_today"]
            metric_date = row_metrics["metric_date"]
        else:
            current_people = 0
            entries_today = 0
            exits_today = 0
            metric_date = today_dt

        # Reseta acumuladores se mudou o dia (mas mantém contagem atual de ocupação)
        if metric_date != today_dt:
            entries_today = 0
            exits_today = 0
            metric_date = today_dt

        delta_people = 0
        delta_entries = 0
        delta_exits = 0
        is_inside_now = None

        # 3. Se acesso foi liberado/válido, atualiza presença e contador
        if is_granted:
            if cpf is not None:
                cpf_int = int(cpf)
                cursor.execute("SELECT is_inside FROM building_presence WHERE cpf = ?", (cpf_int,))
                row_presence = cursor.fetchone()
                was_inside = bool(row_presence["is_inside"]) if row_presence else False

                if is_entry:
                    # Entrando: se ainda não constava como dentro, incrementa
                    if not was_inside:
                        delta_people = 1
                    delta_entries = 1
                    is_inside_now = 1

                    cursor.execute(
                        """
                        INSERT INTO building_presence (cpf, is_inside, last_direction, last_device_id, last_entry_at, updated_at)
                        VALUES (?, 1, ?, ?, ?, ?)
                        ON CONFLICT(cpf) DO UPDATE SET
                            is_inside = 1,
                            last_direction = excluded.last_direction,
                            last_device_id = excluded.last_device_id,
                            last_entry_at = excluded.last_entry_at,
                            updated_at = excluded.updated_at
                        """,
                        (cpf_int, resolved_direction, str(device_id) if device_id else None, ts, now_dt),
                    )
                else:
                    # Saindo: se constava como dentro, decrementa
                    if was_inside:
                        delta_people = -1
                    elif current_people > 0:
                        delta_people = -1
                    delta_exits = 1
                    is_inside_now = 0

                    cursor.execute(
                        """
                        INSERT INTO building_presence (cpf, is_inside, last_direction, last_device_id, last_exit_at, updated_at)
                        VALUES (?, 0, ?, ?, ?, ?)
                        ON CONFLICT(cpf) DO UPDATE SET
                            is_inside = 0,
                            last_direction = excluded.last_direction,
                            last_device_id = excluded.last_device_id,
                            last_exit_at = excluded.last_exit_at,
                            updated_at = excluded.updated_at
                        """,
                        (cpf_int, resolved_direction, str(device_id) if device_id else None, ts, now_dt),
                    )
            else:
                # Caso sem CPF (identificação anônima da catraca)
                if is_entry:
                    delta_people = 1
                    delta_entries = 1
                else:
                    delta_people = -1 if current_people > 0 else 0
                    delta_exits = 1

        new_people_count = max(0, current_people + delta_people)
        new_entries_today = entries_today + delta_entries
        new_exits_today = exits_today + delta_exits

        # 4. Atualização O(1) do contador global do prédio
        cursor.execute(
            """
            INSERT INTO building_metrics (id, people_count, total_entries_today, total_exits_today, metric_date, last_event_at, updated_at)
            VALUES (1, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                people_count = excluded.people_count,
                total_entries_today = excluded.total_entries_today,
                total_exits_today = excluded.total_exits_today,
                metric_date = excluded.metric_date,
                last_event_at = excluded.last_event_at,
                updated_at = excluded.updated_at
            """,
            (new_people_count, new_entries_today, new_exits_today, metric_date, ts, now_dt),
        )

        conn.commit()

        return {
            "event_id": event_id,
            "metrics": {
                "people_count": new_people_count,
                "total_entries_today": new_entries_today,
                "total_exits_today": new_exits_today,
                "metric_date": metric_date,
                "last_event_at": ts,
            },
            "presence": {
                "cpf": int(cpf) if cpf is not None else None,
                "is_inside": is_inside_now,
                "direction": resolved_direction,
                "status": status or "granted",
            } if cpf is not None else None,
        }
    finally:
        conn.close()


def get_building_metrics() -> Dict[str, Any]:
    conn = get_connection()
    try:
        cursor = conn.cursor()
        today_dt = datetime.now().strftime("%Y-%m-%d")
        cursor.execute("SELECT * FROM building_metrics WHERE id = 1")
        row = cursor.fetchone()
        if not row:
            return {
                "people_count": 0,
                "total_entries_today": 0,
                "total_exits_today": 0,
                "metric_date": today_dt,
                "last_event_at": None,
            }
        d = dict(row)
        if d.get("metric_date") != today_dt:
            # Novo dia, reseta contadores diários em visualização
            d["total_entries_today"] = 0
            d["total_exits_today"] = 0
            d["metric_date"] = today_dt
        return d
    finally:
        conn.close()


def get_building_presence_list(
    is_inside: Optional[bool] = None,
    limit: int = 100,
    offset: int = 0,
) -> Dict[str, Any]:
    conn = get_connection()
    try:
        cursor = conn.cursor()
        params = []
        where_clause = ""
        if is_inside is not None:
            where_clause = "WHERE is_inside = ?"
            params.append(1 if is_inside else 0)

        cursor.execute(f"SELECT COUNT(*) FROM building_presence {where_clause}", tuple(params))
        total = cursor.fetchone()[0]

        query = f"""
            SELECT p.cpf, p.is_inside, p.last_direction, p.last_device_id, p.last_entry_at, p.last_exit_at, p.updated_at
            FROM building_presence p
            {where_clause}
            ORDER BY p.updated_at DESC
            LIMIT ? OFFSET ?
        """
        params.extend([max(1, min(limit, 500)), max(0, offset)])
        cursor.execute(query, tuple(params))
        rows = [dict(r) for r in cursor.fetchall()]

        return {
            "total": total,
            "items": rows,
            "limit": limit,
            "offset": offset,
        }
    finally:
        conn.close()


def get_user_presence(cpf: int) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM building_presence WHERE cpf = ?", (int(cpf),))
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()

