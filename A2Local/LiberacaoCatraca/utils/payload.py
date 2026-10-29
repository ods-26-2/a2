from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from datetime import datetime
from typing import Union

key = b"a" * 32  # chave temporária


def decrypt(data: bytes) -> bytes:
    """Decripta dados com AES-256-ECB."""
    if isinstance(data, str):
        data = bytes.fromhex(data.strip())
    if len(data) != 16:
        raise ValueError(f"Payload deve ter 16 bytes, recebeu {len(data)}")
    cipher = Cipher(algorithms.AES(key), modes.ECB())
    decryptor = cipher.decryptor()
    return decryptor.update(data) + decryptor.finalize()


def _to_bytes(payload: Union[bytes, str, bytearray]) -> bytes:
    if isinstance(payload, str):
        text = payload.strip()
        if len(text) == 32 and all(c in "0123456789abcdefABCDEF" for c in text):
            return bytes.fromhex(text)
        return text.encode("utf-8")
    if isinstance(payload, (bytes, bytearray)):
        if len(payload) == 16:
            return bytes(payload)
        if len(payload) == 32:
            try:
                return bytes.fromhex(payload.decode("ascii"))
            except Exception:
                pass
    raise ValueError("Payload inválido: esperado 16 bytes ou hex de 32 caracteres")


def payload_to_dict(payload: Union[bytes, str, bytearray]) -> dict:
    """Descriptografa a payload (16 bytes) e a converte em um dicionário."""
    raw = decrypt(_to_bytes(payload))

    cpf_base = int.from_bytes(raw[0:4], "big")
    start_ts = int.from_bytes(raw[4:8], "big")
    end_ts = int.from_bytes(raw[8:12], "big")
    day_mask = raw[12] & 0x7F

    allowed_days = [i for i in range(7) if day_mask & (1 << i)]

    return {
        "cpf_base": cpf_base,
        "cpf": str(cpf_base).zfill(9),
        "start_timestamp": start_ts,
        "end_timestamp": end_ts,
        "start_date": datetime.fromtimestamp(start_ts).isoformat(),
        "end_date": datetime.fromtimestamp(end_ts).isoformat(),
        "day_mask": day_mask,
        "allowed_days": allowed_days,
    }


if __name__ == "__main__":
    # Payload encriptada gerada externamente (hex de 32 caracteres = 16 bytes)
    encrypted_hex = "bc6f369bc724a36878eb176a0754a3b1"
    print("Descriptografado/convertido:")
    print(payload_to_dict(encrypted_hex))
