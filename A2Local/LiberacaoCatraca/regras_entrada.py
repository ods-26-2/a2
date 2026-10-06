from datetime import datetime, timezone
from interpreta_codigo import decodifica_codigo


def liberar_entrada(decoded_data):
    try:
        cpf, dataEntradaPermitida, dataSaidaPermitida = decodifica_codigo(decoded_data)

        entrada = datetime.fromisoformat(
            dataEntradaPermitida.replace("Z", "+00:00")
        )

        saida = datetime.fromisoformat(
            dataSaidaPermitida.replace("Z", "+00:00")
        )

        agora = datetime.now(timezone.utc)

        if entrada.tzinfo is None:
            entrada = entrada.replace(tzinfo=timezone.utc)

        if saida.tzinfo is None:
            saida = saida.replace(tzinfo=timezone.utc)

        if cpf is None or not isinstance(cpf, str) or not cpf.isdigit() or len(cpf) != 11:
            print(f"CPF inválido: {cpf}")
            return False, None

        if entrada <= agora <= saida:
            print(f"CPF {cpf}: código válido.")
            return True, cpf

        print(f"CPF {cpf}: código fora do período permitido.")
        return False, cpf

    except Exception as e:
        print(f"Erro ao interpretar código: {e}")
        return False, None
