import os
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from typing import Union

key = b"a"*32  # chave temporária


def encrypt(data: Union[bytes, str]) -> bytes:
    """Encripta dados com AES-256-ECB. O dado deve ser múltiplo de 16 bytes."""
    payload_bytes = data.encode() if isinstance(data, str) else data

    if len(payload_bytes) % 16 != 0:
        raise ValueError(f"Dados devem ser múltiplos de 16 bytes, recebeu {len(payload_bytes)}")

    cipher = Cipher(algorithms.AES(key), modes.ECB())
    encryptor = cipher.encryptor()
    return encryptor.update(payload_bytes) + encryptor.finalize()


def decrypt(data: bytes) -> bytes:
    """Decripta dados com AES-256-ECB."""
    cipher = Cipher(algorithms.AES(key), modes.ECB())
    decryptor = cipher.decryptor()
    return decryptor.update(data) + decryptor.finalize()