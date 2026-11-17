import json
from pathlib import Path

from catraca_driver import (
    create_turnstile_driver
)
from catraca_monitor import (
    TurnstileRegistry,
    start_monitor_server
)


CONFIG_FILE = Path(
    __file__
).with_name(
    "configCatraca_CELULAR.json"
)


def main():
    with open(
        CONFIG_FILE,
        "r",
        encoding="utf-8"
    ) as file:
        config = json.load(
            file
        )

    monitor_config = config[
        "monitor"
    ]

    device = config[
        "devices"
    ][0]

    registry = TurnstileRegistry()

    monitor_server = (
        start_monitor_server(
            registry,
            monitor_config
        )
    )

    driver = (
        create_turnstile_driver(
            device,
            passage_timeout=15
        )
    )

    try:
        driver.initialize(
            monitor_config
        )

        registry.register(
            driver
        )

        print()
        print(
            "Enviando liberação "
            "para o celular..."
        )

        driver.release()

        print(
            "No celular, toque em "
            "ENTRADA, SAÍDA ou DESISTIR."
        )

        result = (
            driver.wait_for_passage()
        )

        print()
        print(
            "Resultado recebido:"
        )

        print(
            json.dumps(
                result,
                indent=2,
                ensure_ascii=False
            )
        )

    finally:
        monitor_server.shutdown()
        monitor_server.server_close()


if __name__ == "__main__":
    main()
