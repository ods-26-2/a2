import threading
import time

import requests

class SimulatedTurnstile:
    def __init__(
        self,
        config,
        passage_timeout
    ):
        self.turnstile_id = config["turnstile_id"]
        self.passage_timeout = passage_timeout

        simulation = config.get("simulation", {})

        self.pass_after = simulation.get(
            "pass_after",
            2
        )

        self.simulated_direction = simulation.get(
            "direction",
            "entrada"
        )

        if self.simulated_direction not in (
            "entrada",
            "saida"
        ):
            raise RuntimeError(
                f"[{self.turnstile_id}] "
                f"Direção simulada inválida: "
                f"{self.simulated_direction}"
            )

    def initialize(
        self,
        monitor_config
    ):
        print(f"[{self.turnstile_id}] Catraca simulada inicializada.")

    def release(self):
        print(f"[{self.turnstile_id}] CATRACA LIBERADA.")

    def wait_for_passage(self):
        if self.pass_after is None:
            time.sleep(self.passage_timeout)
            return {
                "status": "timeout",
                "direction": None
            }

        pass_after = float(self.pass_after)

        if pass_after > self.passage_timeout:
            time.sleep(self.passage_timeout)
            return {
                "status": "timeout",
                "direction": None
            }

        time.sleep(pass_after)

        return {
            "status": "passed",
            "direction": self.simulated_direction
        }


class VisualSimulatedTurnstile:
    def __init__(
        self,
        config,
        passage_timeout,
        simulator_host="127.0.0.1",
        simulator_port=8765
    ):
        self.turnstile_id = config["turnstile_id"]
        self.passage_timeout = passage_timeout
        self.simulator_base_url = (
            f"http://{simulator_host}:{simulator_port}"
        )

        simulation = config.get("simulation", {})

        self.gateway = simulation.get(
            "gateway",
            "clockwise"
        )

        if self.gateway not in (
            "clockwise",
            "anticlockwise"
        ):
            raise RuntimeError(
                f"[{self.turnstile_id}] "
                f"Gateway inválido para simulação visual: "
                f"{self.gateway}"
            )

        self.release_direction = simulation.get(
            "release_direction",
            "both"
        )

        if self.release_direction not in (
            "clockwise",
            "anticlockwise",
            "both"
        ):
            raise RuntimeError(
                f"[{self.turnstile_id}] "
                f"Direção de liberação inválida para simulação visual: "
                f"{self.release_direction}"
            )

        self.request_timeout = float(
            simulation.get(
                "request_timeout",
                5
            )
        )

        self.device_id = simulation.get(
            "device_id",
            f"sim-{self.turnstile_id}"
        )

        self.last_direction = None
        self.passage_event = threading.Event()
        self.give_up_event = threading.Event()

    def post_to_simulator(
        self,
        endpoint,
        payload
    ):
        response = requests.post(
            f"{self.simulator_base_url}{endpoint}",
            json=payload,
            timeout=self.request_timeout
        )
        response.raise_for_status()
        return response

    def initialize(
        self,
        monitor_config
    ):
        callback_port = int(
            monitor_config.get(
                "port",
                8000
            )
        )

        callback_path = str(
            monitor_config.get(
                "path",
                "api/notifications"
            )
        ).strip("/")

        callback_url = (
            f"http://127.0.0.1:{callback_port}/"
            f"{callback_path}/catra_event"
        )

        self.post_to_simulator(
            "/register",
            {
                "turnstile_id": self.turnstile_id,
                "device_id": str(self.device_id),
                "gateway": self.gateway,
                "callback_url": callback_url
            }
        )

        print(
            f"[{self.turnstile_id}] "
            f"Simulador visual registrado com device_id={self.device_id}."
        )

    def release(self):
        self.passage_event.clear()
        self.give_up_event.clear()
        self.last_direction = None

        self.post_to_simulator(
            "/release",
            {
                "turnstile_id": self.turnstile_id,
                "allow": self.release_direction,
                "passage_timeout": self.passage_timeout
            }
        )

        print(f"[{self.turnstile_id}] Liberação enviada ao simulador visual.")

    def get_passage_direction(
        self,
        event_name
    ):
        normalized = (
            str(event_name)
            .strip()
            .upper()
            .replace(" ", "_")
        )

        if normalized.startswith("EVENT_"):
            normalized = normalized[len("EVENT_"):]

        if normalized == "TURN_RIGHT":
            rotation = "clockwise"
        elif normalized == "TURN_LEFT":
            rotation = "anticlockwise"
        else:
            return None

        if rotation == self.gateway:
            return "entrada"

        return "saida"

    def notify_event(
        self,
        event_name
    ):
        normalized = (
            str(event_name)
            .strip()
            .upper()
            .replace(" ", "_")
        )

        if normalized.startswith("EVENT_"):
            normalized = normalized[len("EVENT_"):]

        if normalized in ("TURN_LEFT", "TURN_RIGHT"):
            self.last_direction = self.get_passage_direction(normalized)
            self.passage_event.set()
        elif normalized == "GIVE_UP":
            self.give_up_event.set()

    def wait_for_passage(self):
        deadline = time.monotonic() + self.passage_timeout

        while time.monotonic() < deadline:
            if self.passage_event.wait(timeout=0.05):
                return {
                    "status": "passed",
                    "direction": self.last_direction
                }

            if self.give_up_event.is_set():
                return {
                    "status": "give_up",
                    "direction": None
                }

        return {
            "status": "timeout",
            "direction": None
        }


class ControlIDBlock:
    def __init__(
        self,
        config,
        passage_timeout
    ):
        self.turnstile_id = config["turnstile_id"]
        self.protocol = config.get("protocol", "http")
        self.host = config["host"]
        self.port = int(config.get("port", 80))
        self.username = config.get("username", "admin")
        self.password = config.get("password", "admin")

        self.release_direction = config.get(
            "direction",
            "both"
        )

        if self.release_direction not in (
            "clockwise",
            "anticlockwise",
            "both"
        ):
            raise RuntimeError(
                f"[{self.turnstile_id}] "
                f"Direção de liberação inválida: {self.release_direction}"
            )

        self.verify_tls = bool(config.get("verify_tls", False))
        self.request_timeout = float(config.get("request_timeout", 5))
        self.passage_timeout = passage_timeout
        self.http = requests.Session()
        self.session_token = None
        self.device_id = None
        self.gateway = None
        self.last_direction = None
        self.passage_event = threading.Event()
        self.give_up_event = threading.Event()

    @property
    def base_url(self):
        return f"{self.protocol}://{self.host}:{self.port}"

    def request(
        self,
        endpoint,
        json_data=None,
        use_session=True
    ):
        params = {}

        if use_session and self.session_token:
            params["session"] = self.session_token

        response = self.http.post(
            f"{self.base_url}{endpoint}",
            params=params,
            json=json_data,
            timeout=self.request_timeout,
            verify=self.verify_tls
        )
        response.raise_for_status()
        return response

    def login(self):
        response = self.request(
            "/login.fcgi",
            {
                "login": self.username,
                "password": self.password
            },
            use_session=False
        )

        data = response.json()
        self.session_token = data.get("session")

        if not self.session_token:
            raise RuntimeError(f"[{self.turnstile_id}] Falha no login da catraca.")

    def get_system_information(self):
        response = self.request("/system_information.fcgi", {})
        data = response.json()
        self.device_id = data.get("device_id")

        if self.device_id is None:
            raise RuntimeError(f"[{self.turnstile_id}] device_id não retornado.")

        return data

    def get_gateway(self):
        response = self.request(
            "/get_configuration.fcgi",
            {
                "catra": [
                    "gateway"
                ]
            }
        )

        data = response.json()
        catra = data.get("catra", {})
        self.gateway = catra.get("gateway")

        if self.gateway not in ("clockwise", "anticlockwise"):
            raise RuntimeError(
                f"[{self.turnstile_id}] Gateway inválido ou não retornado: {self.gateway}"
            )

        print(
            f"[{self.turnstile_id}] "
            f"Sentido configurado como entrada: {self.gateway}"
        )

    def configure_timeout(self):
        timeout_ms = int(self.passage_timeout * 1000)

        self.request(
            "/set_configuration.fcgi",
            {
                "general": {
                    "catra_timeout": str(timeout_ms)
                }
            }
        )

    def configure_monitor(
        self,
        monitor_config
    ):
        hostname = monitor_config.get("hostname")

        if not hostname:
            raise RuntimeError(
                f"[{self.turnstile_id}] monitor.hostname não configurado."
            )

        port = int(monitor_config.get("port", 8000))
        path = monitor_config.get("path", "api/notifications").strip("/")

        self.request(
            "/set_configuration.fcgi",
            {
                "monitor": {
                    "request_timeout": "5000",
                    "hostname": hostname,
                    "port": str(port),
                    "path": path,
                    "inform_access_event_id": "1"
                }
            }
        )

    def initialize(
        self,
        monitor_config
    ):
        self.login()
        info = self.get_system_information()
        self.get_gateway()
        self.configure_timeout()
        self.configure_monitor(monitor_config)

        print(f"[{self.turnstile_id}] Control iD conectada.")
        print(f"[{self.turnstile_id}] device_id = {self.device_id}")

        version = info.get("version")

        if version is not None:
            print(f"[{self.turnstile_id}] firmware = {version}")

    def release(self):
        self.passage_event.clear()
        self.give_up_event.clear()
        self.last_direction = None

        self.request(
            "/execute_actions.fcgi",
            {
                "actions": [
                    {
                        "action": "catra",
                        "parameters": f"allow={self.release_direction}"
                    }
                ]
            }
        )

        print(f"[{self.turnstile_id}] Comando de liberação enviado.")

    def get_passage_direction(
        self,
        event_name
    ):
        normalized = (
            str(event_name)
            .strip()
            .upper()
            .replace(" ", "_")
        )

        if normalized.startswith("EVENT_"):
            normalized = normalized[len("EVENT_"):]

        if normalized == "TURN_RIGHT":
            rotation = "clockwise"
        elif normalized == "TURN_LEFT":
            rotation = "anticlockwise"
        else:
            return None

        if rotation == self.gateway:
            return "entrada"

        return "saida"

    def notify_event(
        self,
        event_name
    ):
        normalized = (
            str(event_name)
            .strip()
            .upper()
            .replace(" ", "_")
        )

        if normalized.startswith("EVENT_"):
            normalized = normalized[len("EVENT_"):]

        if normalized in ("TURN_LEFT", "TURN_RIGHT"):
            self.last_direction = self.get_passage_direction(normalized)
            self.passage_event.set()
        elif normalized == "GIVE_UP":
            self.give_up_event.set()

    def wait_for_passage(self):
        deadline = time.monotonic() + self.passage_timeout

        while time.monotonic() < deadline:
            if self.passage_event.wait(timeout=0.05):
                return {
                    "status": "passed",
                    "direction": self.last_direction
                }

            if self.give_up_event.is_set():
                return {
                    "status": "give_up",
                    "direction": None
                }

        return {
            "status": "timeout",
            "direction": None
        }


def create_turnstile_driver(
    hardware_config,
    passage_timeout,
    simulation_mode=False,
    simulator_host="127.0.0.1",
    simulator_port=8765
):
    model = str(hardware_config.get("model", "")).lower()
    protocol = str(hardware_config.get("protocol", "")).lower()

    if model == "simulated" or protocol == "simulation":
        if simulation_mode:
            return VisualSimulatedTurnstile(
                hardware_config,
                passage_timeout,
                simulator_host=simulator_host,
                simulator_port=simulator_port
            )

        return SimulatedTurnstile(
            hardware_config,
            passage_timeout
        )

    if model == "controlid_idblock" and protocol in ("http", "https"):
        return ControlIDBlock(
            hardware_config,
            passage_timeout
        )

    raise RuntimeError(
        f"Modelo/protocolo de catraca não suportado: {model}/{protocol}"
    )
