import os
from datetime import datetime

from cryptography.hazmat.primitives.ciphers import (
    Cipher,
    algorithms,
    modes
)


# Chave temporária fornecida para testes.
#
# Em produção, configure A2_AES_KEY no .env com exatamente
# 32 bytes/caracteres ASCII.
DEFAULT_TEST_KEY = "a" * 32


def _get_key() -> bytes:
    value = os.getenv(
        "A2_AES_KEY",
        DEFAULT_TEST_KEY
    )

    try:
        key = value.encode(
            "ascii"
        )
    except UnicodeEncodeError as e:
        raise ValueError(
            "A2_AES_KEY deve usar caracteres ASCII."
        ) from e

    if len(key) != 32:
        raise ValueError(
            "A2_AES_KEY deve possuir exatamente "
            "32 bytes para AES-256."
        )

    return key


def _calc_cpf_dv(
    cpf_base: int
) -> str:
    """
    Calcula os dois dígitos verificadores do CPF
    a partir dos nove primeiros dígitos.
    """

    if (
        cpf_base < 0
        or cpf_base > 999_999_999
    ):
        raise ValueError(
            "cpf_base fora do intervalo esperado "
            "de 9 dígitos."
        )

    digits = [
        int(d)
        for d
        in str(cpf_base).zfill(9)
    ]

    # Primeiro dígito verificador.
    s1 = sum(
        d * w
        for d, w
        in zip(
            digits,
            range(10, 1, -1)
        )
    )

    r1 = s1 % 11

    dv1 = (
        0
        if r1 < 2
        else 11 - r1
    )

    # Segundo dígito verificador.
    s2 = sum(
        d * w
        for d, w
        in zip(
            digits + [dv1],
            range(11, 1, -1)
        )
    )

    r2 = s2 % 11

    dv2 = (
        0
        if r2 < 2
        else 11 - r2
    )

    return f"{dv1}{dv2}"


def decrypt(
    data: bytes
) -> bytes:
    """
    Decripta exatamente um bloco de 16 bytes
    usando AES-256-ECB.
    """

    if not isinstance(
        data,
        bytes
    ):
        raise TypeError(
            "A payload criptografada deve ser bytes."
        )

    if len(data) != 16:
        raise ValueError(
            "A payload AES deve possuir exatamente "
            "16 bytes."
        )

    cipher = Cipher(
        algorithms.AES(
            _get_key()
        ),
        modes.ECB()
    )

    decryptor = (
        cipher.decryptor()
    )

    return (
        decryptor.update(
            data
        )
        + decryptor.finalize()
    )


def payload_to_dict(
    payload: bytes
) -> dict:
    """
    Descriptografa a payload de 16 bytes e
    converte os campos para um dicionário.

    Layout recebido:

        bytes 0..3   -> cpf_base
        bytes 4..7   -> start_timestamp
        bytes 8..11  -> end_timestamp
        byte  12     -> day_mask (7 bits menos significativos)
        bytes 13..15 -> não utilizados pelo padrão recebido
    """

    raw = decrypt(
        payload
    )

    cpf_base = int.from_bytes(
        raw[0:4],
        "big"
    )

    start_ts = int.from_bytes(
        raw[4:8],
        "big"
    )

    end_ts = int.from_bytes(
        raw[8:12],
        "big"
    )

    day_mask = (
        raw[12]
        & 0x7F
    )

    if start_ts > end_ts:
        raise ValueError(
            "Payload inválida: start_timestamp "
            "é maior que end_timestamp."
        )

    allowed_days = [
        i
        for i
        in range(7)
        if (
            day_mask
            & (1 << i)
        )
    ]

    dv = _calc_cpf_dv(
        cpf_base
    )

    cpf_full = (
        str(
            cpf_base
        ).zfill(9)
        + dv
    )

    return {
        "cpf_base":
            cpf_base,

        "cpf":
            cpf_full,

        "cpf_formatted":
            (
                f"{cpf_full[:3]}."
                f"{cpf_full[3:6]}."
                f"{cpf_full[6:9]}-"
                f"{cpf_full[9:]}"
            ),

        "start_timestamp":
            start_ts,

        "end_timestamp":
            end_ts,

        # Apenas representação legível.
        # A regra de validade usa os timestamps numéricos.
        "start_date":
            datetime.fromtimestamp(
                start_ts
            ).isoformat(),

        "end_date":
            datetime.fromtimestamp(
                end_ts
            ).isoformat(),

        "day_mask":
            day_mask,

        "allowed_days":
            allowed_days
    }


def decoded_data_to_bytes(
    decoded_data
) -> bytes:
    """
    Converte decoded_data para os 16 bytes criptografados
    usados pelo AES.

    Aceita DUAS formas:

    1) HEX textual:
       "b486c08c912653049354b954a1fa2439"

       -> 32 caracteres hexadecimais
       -> convertido com bytes.fromhex()

    2) Os 16 bytes AES diretamente.

       Pode chegar como:
           bytes
       ou como:
           str de 16 caracteres preservados em Latin-1

       Nesse segundo caso cada caractere é convertido de volta
       para o byte original com encode("latin-1").
    """

    # --------------------------------------------------------
    # Caso 1: bytes / bytearray / memoryview
    # --------------------------------------------------------
    if isinstance(
        decoded_data,
        (
            bytes,
            bytearray,
            memoryview
        )
    ):
        raw = bytes(
            decoded_data
        )

        # 16 bytes = ciphertext AES direto.
        if len(raw) == 16:
            return raw

        # Também tolera 32 bytes ASCII contendo HEX.
        if len(raw) == 32:
            try:
                text = raw.decode(
                    "ascii"
                )

                return bytes.fromhex(
                    text
                )

            except (
                UnicodeDecodeError,
                ValueError
            ) as e:
                raise ValueError(
                    "decoded_data com 32 bytes deve conter "
                    "texto hexadecimal válido."
                ) from e

        raise ValueError(
            "decoded_data em bytes deve possuir "
            "16 bytes AES diretos ou 32 bytes ASCII HEX."
        )

    # --------------------------------------------------------
    # Caso 2: string
    # --------------------------------------------------------
    if isinstance(
        decoded_data,
        str
    ):
        # Primeiro testamos HEX.
        #
        # Aqui strip() é seguro porque só é usado para
        # verificar a representação textual hexadecimal.
        hex_text = (
            decoded_data
            .strip()
        )

        if len(hex_text) == 32:
            try:
                payload = bytes.fromhex(
                    hex_text
                )

                if len(payload) == 16:
                    return payload

            except ValueError:
                # Se não for HEX, ainda pode ser outra
                # representação e seguimos para o teste abaixo.
                pass

        # Depois testamos os 16 bytes representados diretamente
        # como caracteres Latin-1.
        #
        # NÃO usamos strip() aqui, pois um byte válido pode
        # corresponder a um caractere considerado espaço.
        if len(decoded_data) == 16:
            try:
                payload = decoded_data.encode(
                    "latin-1"
                )

            except UnicodeEncodeError as e:
                raise ValueError(
                    "decoded_data possui 16 caracteres, mas "
                    "não preserva bytes Latin-1. "
                    "O I6 provavelmente alterou os bytes "
                    "originais durante a conversão para texto."
                ) from e

            if len(payload) == 16:
                return payload

        raise ValueError(
            "decoded_data deve ser uma destas formas: "
            "32 caracteres hexadecimais ou "
            "16 bytes AES diretos."
        )

    raise TypeError(
        "decoded_data deve ser str, bytes, "
        "bytearray ou memoryview."
    )


def decodifica_codigo(
    decoded_data
) -> dict:
    """
    Função usada pelo A2.

    Entrada:
        decoded_data recebido do I6.

    Aceita:
        - HEX com 32 caracteres;
        - 16 bytes AES diretamente;
        - string Latin-1 que preserve esses 16 bytes.

    Saída:
        dicionário com CPF, timestamps e day_mask.

    Em caso de payload inválida ou chave incorreta,
    lança uma exceção e regras_entrada.py rejeita o acesso.
    """

    payload = decoded_data_to_bytes(
        decoded_data
    )

    return payload_to_dict(
        payload
    )


if __name__ == "__main__":
    # --------------------------------------------------------
    # Teste 1: formato HEX
    # --------------------------------------------------------
    encrypted_hex = (
        "3f9be5fc264431f2b7bbe72ec2953bc5"
    )

    print(
        "Teste HEX:"
    )

    print(
        decodifica_codigo(
            encrypted_hex
        )
    )

    print()

    # --------------------------------------------------------
    # Teste 2: bytes AES diretos
    # QR real analisado durante a integração.
    # --------------------------------------------------------
    encrypted_bytes = bytes.fromhex(
        "b486c08c912653049354b954a1fa2439"
    )

    print(
        "Teste bytes diretos:"
    )

    print(
        decodifica_codigo(
            encrypted_bytes
        )
    )

    print()

    # --------------------------------------------------------
    # Teste 3: os mesmos 16 bytes transportados como string
    # Latin-1, caso o I6 esteja publicando dessa forma.
    # --------------------------------------------------------
    encrypted_latin1 = (
        encrypted_bytes
        .decode(
            "latin-1"
        )
    )

    print(
        "Teste string Latin-1:"
    )

    print(
        decodifica_codigo(
            encrypted_latin1
        )
    )
