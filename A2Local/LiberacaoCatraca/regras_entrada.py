import time

from interpreta_codigo import (
    decodifica_codigo
)


def liberar_entrada(
    decoded_data
):
    """
    Retorno preservado para não quebrar liberar.py:

        (True, cpf)
        (False, cpf)
        (False, None)

    O interpretador agora devolve um dict.

    Por enquanto são validados:
        - payload AES/hex válida;
        - CPF obtido da payload;
        - intervalo start_timestamp <= agora <= end_timestamp.

    day_mask é decodificado, mas ainda NÃO participa
    da decisão porque o padrão recebido não informa
    qual dia da semana corresponde aos índices 0..6.
    """

    try:
        dados = decodifica_codigo(
            decoded_data
        )

    except Exception as e:
        print(
            f"Erro ao interpretar código: {e}"
        )

        return (
            False,
            None
        )

    cpf = dados.get(
        "cpf"
    )

    if (
        not isinstance(
            cpf,
            str
        )
        or not cpf.isdigit()
        or len(cpf) != 11
    ):
        print(
            f"CPF inválido: {cpf}"
        )

        return (
            False,
            None
        )

    start_ts = dados.get(
        "start_timestamp"
    )

    end_ts = dados.get(
        "end_timestamp"
    )

    if (
        not isinstance(
            start_ts,
            int
        )
        or not isinstance(
            end_ts,
            int
        )
    ):
        print(
            "Timestamps inválidos."
        )

        return (
            False,
            cpf
        )

    agora = int(
        time.time()
    )

    if (
        start_ts
        <= agora
        <= end_ts
    ):
        print(
            f"CPF {cpf}: "
            "código válido."
        )

        return (
            True,
            cpf
        )

    print(
        f"CPF {cpf}: "
        "código fora do período permitido."
    )

    return (
        False,
        cpf
    )
