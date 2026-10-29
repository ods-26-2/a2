import sys
from pathlib import Path
from datetime import datetime, date, time, timedelta
from typing import List, Dict, Any, Union

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from utils.AES256 import encrypt
from db.connection import get_user_by_cpf


def cpf_base(cpf: Union[int, str]) -> int:
    digits = "".join(ch for ch in str(cpf) if ch.isdigit())
    return int(digits[:9]) if digits else 0


def build_payload_bytes(cpf: int, data_inicial: datetime, data_final: datetime, valid_days: int = 0) -> bytes:
    """Monta a payload em formato binario (16 bytes):
    - 4 bytes: CPF base (sem digitos verificadores, max 999.999.999)
    - 4 bytes: timestamp de inicio
    - 4 bytes: timestamp de fim
    - 1 byte:  mascara de dias validos (1 bit por dia; 0 = sem filtro)
    - 3 bytes: reservado

    O CPF pode vir completo (11 digitos); apenas os 9 primeiros
    (sem os digitos verificadores) sao gravados nos 4 bytes.
    """
    return (
        cpf_base(cpf).to_bytes(4, "big")
        + int(data_inicial.timestamp()).to_bytes(4, "big")
        + int(data_final.timestamp()).to_bytes(4, "big")
        + bytes([valid_days & 0x7F])
        + b"\x00" * 3  # reservado
    )


compress = build_payload_bytes


def get_dates(cpf: int, length: int = 1) -> List[List[datetime]]:
    """Gera as proximas `length` janelas de acesso VALIDAS (nao passadas).

    - Recorrente: avanca dia a dia e inclui apenas os dias da semana em `access_days`.
    - Nao-recorrente: parte da `specific_date` e gera `length` dias consecutivos.

    Janelas cujo horario de fim ja passou (`end <= agora`) sao ignoradas,
    garantindo que a primeira retornada seja a proxima janela valida.
    """
    user = get_user_by_cpf(cpf)
    if not user or length <= 0:
        return []

    start = time.fromisoformat(user["access_hours"]["start"])
    end = time.fromisoformat(user["access_hours"]["end"])
    now = datetime.now()

    def window(day: date) -> List[datetime]:
        return [datetime.combine(day, start), datetime.combine(day, end)]

    def is_valid(day: date) -> bool:
        return datetime.combine(day, end) > now

    # Nao-recorrente (Data Fixa): possui data inicial e data final
    if not user.get("is_recurring", True):
        spec = user.get("specific_date")
        if not spec:
            return []
        start_d = date.fromisoformat(str(spec)[:10])
        exp = user.get("expiration_date")
        end_d = date.fromisoformat(str(exp)[:10]) if exp else start_d

        dt_ini = datetime.combine(start_d, start)
        dt_fim = datetime.combine(end_d, end)

        if dt_fim > now:
            return [[dt_ini, dt_fim]]
        return []

    if not user.get("access_days"):
        return []

    exp_date = None
    if user.get("expiration_date"):
        try:
            exp_date = date.fromisoformat(str(user["expiration_date"])[:10])
        except Exception:
            exp_date = None

    start_date = date.today()
    if user.get("specific_date"):
        try:
            spec_d = date.fromisoformat(str(user["specific_date"])[:10])
            if spec_d > start_date:
                start_date = spec_d
        except Exception:
            pass

    dates, day = [], start_date
    max_days_lookahead = 365
    day_count = 0
    while len(dates) < length and day_count < max_days_lookahead:
        if exp_date and day > exp_date:
            break
        if day.weekday() in user["access_days"] and is_valid(day):
            dates.append(window(day))
        day += timedelta(days=1)
        day_count += 1

    return dates


def get_payloads(cpf: int, length: int = 1) -> List[Dict[str, Any]]:
    """Retorna uma lista de payloads encriptadas com base no CPF do usuario e tamanho do lote"""
    user = get_user_by_cpf(cpf)
    exp_str = user.get("expiration_date") if user else None
    spec_str = user.get("specific_date") if user else None
    is_recurring = bool(user.get("is_recurring", True)) if user else True

    if not is_recurring:
        days = (user or {}).get("access_days") or []
        if days:
            valid_days_mask = 0
            for d in days:
                valid_days_mask |= (1 << int(d))
        else:
            valid_days_mask = 0x7F  # todos os dias (comportamento padrao)
    else:
        valid_days_mask = 0

    return [
        {
            "data": encrypt(build_payload_bytes(cpf, dt_ini, dt_fim, valid_days_mask)).hex(),
            "startDate": dt_ini.isoformat(),
            "endDate": dt_fim.isoformat(),
            "expirationDate": exp_str,
            "specificDate": spec_str,
            "isRecurring": is_recurring,
        }
        for dt_ini, dt_fim in get_dates(cpf, length=length)
    ]
