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
            access_days TEXT NOT NULL,
            access_hours TEXT NOT NULL,
            active INTEGER NOT NULL DEFAULT 1,
            created_at DATETIME NOT NULL,
            updated_at DATETIME NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS system_config (
            key TEXT PRIMARY KEY,
            payload_batch_size INTEGER NOT NULL DEFAULT 10,
            updated_at DATETIME NOT NULL
        )
    """)
    conn.commit()

    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        seed_default_data(conn)


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
    password: str,
    is_recurring: bool = True,
    specific_date: Optional[Union[str, date, datetime]] = None,
    access_days: Optional[List[int]] = None,
    access_hours: Optional[Dict[str, str]] = None,
    active: bool = True,
) -> bool:
    """Adiciona ou atualiza um usuário no banco SQLite identificado apenas por CPF.
    
    is_recurring:
      - True (padrão): acesso recorrente baseado em access_days (dias 0 a 6).
      - False: acesso único baseado em specific_date ('YYYY-MM-DD').
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

        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO users (
                cpf, password_hash, is_recurring, specific_date,
                access_days, access_hours, active, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(cpf) DO UPDATE SET
                password_hash = excluded.password_hash,
                is_recurring = excluded.is_recurring,
                specific_date = excluded.specific_date,
                access_days = excluded.access_days,
                access_hours = excluded.access_hours,
                active = excluded.active,
                updated_at = excluded.updated_at
        """, (
            int(cpf),
            hash_password(password),
            1 if is_recurring else 0,
            date_str,
            json.dumps(access_days),
            json.dumps(access_hours),
            1 if active else 0,
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

        if not user.get("active", True):
            return False, "Usuário desativado no sistema", None

        password_hash = user.get("password_hash", "")
        if not check_password(password, password_hash):
            return False, "Senha incorreta", None

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
