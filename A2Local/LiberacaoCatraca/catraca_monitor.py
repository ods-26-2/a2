import json
import threading
from http.server import (
    BaseHTTPRequestHandler,
    ThreadingHTTPServer
)

class TurnstileRegistry:

    def __init__(self):
        self.devices = {}
        self.lock = threading.Lock()


    def register(
        self,
        driver
    ):
        device_id = getattr(
            driver,
            "device_id",
            None
        )

        if device_id is None:
            return

        with self.lock:
            self.devices[
                str(device_id)
            ] = driver


    def notify(
        self,
        device_id,
        event_name
    ):
        with self.lock:
            driver = self.devices.get(
                str(device_id)
            )

        if driver is None:
            print(
                f"Evento recebido de "
                f"device_id desconhecido: "
                f"{device_id}"
            )

            return

        print(
            f"[{driver.turnstile_id}] "
            f"Evento físico: "
            f"{event_name}"
        )

        driver.notify_event(
            event_name
        )

def start_monitor_server(
    registry,
    monitor_config
):
    bind_host = monitor_config.get(
        "bind_host",
        "0.0.0.0"
    )

    port = int(
        monitor_config.get(
            "port",
            8000
        )
    )

    base_path = str(
        monitor_config.get(
            "path",
            "api/notifications"
        )
    ).strip("/")

    catra_path = (
        f"/{base_path}/catra_event"
    )


    class Handler(
        BaseHTTPRequestHandler
    ):

        def do_POST(self):
            path = self.path.split(
                "?"
            )[0]

            if path != catra_path:
                self.send_response(
                    404
                )

                self.end_headers()

                return

            try:
                length = int(
                    self.headers.get(
                        "Content-Length",
                        0
                    )
                )

                raw_data = self.rfile.read(
                    length
                )

                data = json.loads(
                    raw_data.decode(
                        "utf-8"
                    )
                )

                device_id = data[
                    "device_id"
                ]

                event_name = data[
                    "event"
                ][
                    "name"
                ]

                registry.notify(
                    device_id,
                    event_name
                )

                response = (
                    b'{"ok":true}'
                )

                self.send_response(
                    200
                )

                self.send_header(
                    "Content-Type",
                    "application/json"
                )

                self.send_header(
                    "Content-Length",
                    str(
                        len(response)
                    )
                )

                self.end_headers()

                self.wfile.write(
                    response
                )

            except Exception as e:
                print(
                    f"Erro ao processar "
                    f"evento da catraca: {e}"
                )

                self.send_response(
                    400
                )

                self.end_headers()


        def log_message(
            self,
            format,
            *args
        ):
            return


    server = ThreadingHTTPServer(
        (
            bind_host,
            port
        ),
        Handler
    )

    thread = threading.Thread(
        target=server.serve_forever,
        daemon=True
    )

    thread.start()

    print(
        f"Monitor HTTP iniciado em "
        f"{bind_host}:"
        f"{port}"
        f"{catra_path}"
    )

    return server