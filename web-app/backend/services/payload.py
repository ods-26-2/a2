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


def build_payload_bytes(cpf: int, data_inicial: datetime, data_final: datetime) -> bytes:
    """Monta a payload em formato binário (16 bytes):
    - 4 bytes: CPF base (sem dígitos verificadores, max 999.999.999)
    - 4 bytes: timestamp de início
    - 4 bytes: timestamp de fim
    - 4 bytes: reservado

    O CPF pode vir completo (11 dígitos); apenas os 9 primeiros
    (sem os dígitos verificadores) são gravados nos 4 bytes.
    """
    return (
        cpf_base(cpf).to_bytes(4, "big")
        + int(data_inicial.timestamp()).to_bytes(4, "big")
        + int(data_final.timestamp()).to_bytes(4, "big")
        + b"\x00" * 4 # reservado
    )


compress = build_payload_bytes


def get_dates(cpf: int, length: int = 1) -> List[List[datetime]]:
    """Gera as próximas `length` janelas de acesso VÁLIDAS (não passadas).

    - Recorrente: avança dia a dia e inclui apenas os dias da semana em `access_days`.
    - Não-recorrente: parte da `specific_date` e gera `length` dias consecutivos.

    Janelas cujo horário de fim já passou (`end <= agora`) são ignoradas,
    garantindo que a primeira retornada seja a próxima janela válida.
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

    # Não-recorrente: dias consecutivos a partir da specific_date
    if not user.get("is_recurring", True):
        first = date.fromisoformat(str(user["specific_date"])[:10])
        return [
            window(first + timedelta(days=offset))
            for offset in range(length)
            if is_valid(first + timedelta(days=offset))
        ]

    if not user.get("access_days"):
        return []

    dates, day = [], date.today()
    while len(dates) < length:
        if day.weekday() in user["access_days"] and is_valid(day):
            dates.append(window(day))
        day += timedelta(days=1)

    return dates


def get_payloads(cpf: int, length: int = 1) -> List[Dict[str, Any]]:
    """Retorna uma lista de payloads encriptadas com base no CPF do usuário e tamanho do lote"""
    return [
        {
            "data": encrypt(build_payload_bytes(cpf, dt_ini, dt_fim)).hex(),
            "startDate": dt_ini.isoformat(),
            "endDate": dt_fim.isoformat(),
        }
        for dt_ini, dt_fim in get_dates(cpf, length=length)
    ]