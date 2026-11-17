import json

from interpreta_codigo import (
    decodifica_codigo
)

from regras_entrada import (
    liberar_entrada
)


ENCRYPTED_HEX = (
    "3f9be5fc264431f2b7bbe72ec2953bc5"
)


dados = decodifica_codigo(
    ENCRYPTED_HEX
)

print(
    "Payload decodificada:"
)

print(
    json.dumps(
        dados,
        indent=2,
        ensure_ascii=False
    )
)

print()

resultado = liberar_entrada(
    ENCRYPTED_HEX
)

print(
    "Resultado da regra:"
)

print(
    resultado
)
