import json
import threading
import time
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
            # Se o mesmo driver reconectou e recebeu outro
            # device_id, removemos referências antigas.
            stale_ids = [
                registered_id
                for registered_id, registered_driver
                in self.devices.items()
                if registered_driver is driver
            ]

            for registered_id in stale_ids:
                del self.devices[
                    registered_id
                ]

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
                "Evento recebido de "
                "device_id desconhecido: "
                f"{device_id}"
            )
            return

        print(
            f"[{driver.turnstile_id}] "
            f"Evento físico: {event_name}"
        )

        driver.notify_event(
            event_name
        )


def _build_monitor_server(
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
                self.send_response(404)
                self.end_headers()
                return

            try:
                length = int(
                    self.headers.get(
                        "Content-Length",
                        0
                    )
                )

                raw_data = (
                    self.rfile.read(
                        length
                    )
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

                self.send_response(200)

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

            except Exception as error:
                print(
                    "Erro ao processar "
                    "evento da catraca: "
                    f"{error}"
                )

                self.send_response(400)
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

    # Evita manter a aplicação presa por threads de requests
    # durante shutdown.
    server.daemon_threads = True

    return (
        server,
        bind_host,
        port,
        catra_path
    )


def start_monitor_server(
    registry,
    monitor_config
):
    """
    Modo simples/compatível: tenta abrir o monitor uma vez.

    Para o A2 principal use start_monitor_server_with_retry().
    """

    (
        server,
        bind_host,
        port,
        catra_path
    ) = _build_monitor_server(
        registry,
        monitor_config
    )

    thread = threading.Thread(
        target=server.serve_forever,
        daemon=True
    )

    thread.start()

    print(
        "Monitor HTTP iniciado em "
        f"{bind_host}:{port}"
        f"{catra_path}"
    )

    return server


class RetryingMonitorServer:
    """
    Mantém o monitor HTTP vivo sem derrubar o A2.

    Se bind_host/porta estiverem indisponíveis, continua
    tentando abrir o servidor em segundo plano.
    """

    def __init__(
        self,
        registry,
        monitor_config,
        retry_seconds=5
    ):
        self.registry = registry
        self.monitor_config = (
            monitor_config
        )

        self.retry_seconds = max(
            0.5,
            float(
                retry_seconds
            )
        )

        self.stop_event = (
            threading.Event()
        )

        self.online_event = (
            threading.Event()
        )

        self.lock = threading.Lock()
        self.server = None

        self.thread = threading.Thread(
            target=self._run,
            name="a2-monitor-retry",
            daemon=True
        )

        self.thread.start()

    @property
    def online(self):
        return (
            self.online_event
            .is_set()
        )

    def _set_server(
        self,
        server
    ):
        with self.lock:
            self.server = server

    def _run(self):
        while not self.stop_event.is_set():
            server = None

            try:
                (
                    server,
                    bind_host,
                    port,
                    catra_path
                ) = _build_monitor_server(
                    self.registry,
                    self.monitor_config
                )

                self._set_server(
                    server
                )

                self.online_event.set()

                print(
                    "[Monitor] ONLINE em "
                    f"{bind_host}:{port}"
                    f"{catra_path}"
                )

                # Fica aqui enquanto o servidor estiver saudável.
                server.serve_forever(
                    poll_interval=0.5
                )

            except Exception as error:
                if not self.stop_event.is_set():
                    print(
                        "[Monitor] OFFLINE: "
                        f"{error}"
                    )

                    print(
                        "[Monitor] Nova tentativa em "
                        f"{self.retry_seconds:g}s."
                    )

            finally:
                self.online_event.clear()

                if server is not None:
                    try:
                        server.server_close()
                    except Exception:
                        pass

                self._set_server(
                    None
                )

            if self.stop_event.wait(
                self.retry_seconds
            ):
                break

    def shutdown(self):
        self.stop_event.set()

        with self.lock:
            server = self.server

        if server is not None:
            try:
                server.shutdown()
            except Exception:
                pass

        self.thread.join(
            timeout=2
        )

    def server_close(self):
        # Mantido para compatibilidade com o cleanup antigo.
        self.shutdown()


def start_monitor_server_with_retry(
    registry,
    monitor_config,
    retry_seconds=5
):
    return RetryingMonitorServer(
        registry,
        monitor_config,
        retry_seconds=retry_seconds
    )
