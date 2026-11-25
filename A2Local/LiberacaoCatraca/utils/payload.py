from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from datetime import datetime


key = b"a" * 32  # chave temporária


def _calc_cpf_dv(cpf_base: int) -> str:
    """Calcula os 2 dígitos verificadores do CPF a partir dos 9 primeiros dígitos."""
    digits = [int(d) for d in str(cpf_base).zfill(9)]
    # Primeiro DV
    s1 = sum(d * w for d, w in zip(digits, range(10, 1, -1)))
    r1 = s1 % 11
    dv1 = 0 if r1 < 2 else 11 - r1
    # Segundo DV
    s2 = sum(d * w for d, w in zip(digits + [dv1], range(11, 1, -1)))
    r2 = s2 % 11
    dv2 = 0 if r2 < 2 else 11 - r2
    return f"{dv1}{dv2}"


def decrypt(data: bytes) -> bytes:
    """Decripta dados (16 bytes) com AES-256-ECB."""
    cipher = Cipher(algorithms.AES(key), modes.ECB())
    decryptor = cipher.decryptor()
    return decryptor.update(data) + decryptor.finalize()


def payload_to_dict(payload: bytes) -> dict:
    """Descriptografa a payload (16 bytes) e a converte em um dicionário."""
    raw = decrypt(payload)

    cpf_base = int.from_bytes(raw[0:4], "big")
    start_ts = int.from_bytes(raw[4:8], "big")
    end_ts = int.from_bytes(raw[8:12], "big")
    day_mask = raw[12] & 0x7F

    allowed_days = [i for i in range(7) if day_mask & (1 << i)]

    dv = _calc_cpf_dv(cpf_base)
    cpf_full = str(cpf_base).zfill(9) + dv

    return {
        "cpf_base": cpf_base,
        "cpf": cpf_full,
        "cpf_formatted": f"{cpf_full[:3]}.{cpf_full[3:6]}.{cpf_full[6:9]}-{cpf_full[9:]}",
        "start_timestamp": start_ts,
        "end_timestamp": end_ts,
        "start_date": datetime.fromtimestamp(start_ts).isoformat(),
        "end_date": datetime.fromtimestamp(end_ts).isoformat(),
        "day_mask": day_mask,
        "allowed_days": allowed_days,
    }


if __name__ == "__main__":
    encrypted_hex = "3f9be5fc264431f2b7bbe72ec2953bc5"
    print(payload_to_dict(bytes.fromhex(encrypted_hex)))
