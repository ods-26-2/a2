import json
import sqlite3
import subprocess
import sys
import threading
import time
from pathlib import Path
import paho.mqtt.client as mqtt
from catraca_driver import create_turnstile_driver
from catraca_monitor import TurnstileRegistry, start_monitor_server
from regras_entrada import liberar_entrada


MQTT_BROKER = "localhost"
MQTT_PORT = 1883
MQTT_TOPIC = "ods/i6/codigos/decodificados"
MQTT_CLIENT_ID = "a2-controle-acesso"

CAMERAS_CONFIG_FILE = Path(__file__).with_name("cameras.json")
TURNSTILES_CONFIG_FILE = Path(__file__).with_name("catracas.json")
HARDWARE_CONFIG_FILE = Path(__file__).with_name("configCatraca.json")
DATABASE_FILE = Path(__file__).with_name("acessos.db")
SIMULATOR_FILE = Path(__file__).with_name("simulador_catracas.py")

DEFAULT_MAX_PENDING_AGE = 2.0
MQTT_DEDUP_TTL = 60.0

SIMULACAO = 1
SIMULATOR_HOST = "127.0.0.1"
SIMULATOR_PORT = 8765


def load_json_file(path):
    try:
        with open(path, "r", encoding="utf-8") as file:
            return json.load(file)
    except FileNotFoundError:
        raise RuntimeError(f"Arquivo não encontrado: {path}")
    except json.JSONDecodeError as e:
        raise RuntimeError(f"JSON inválido em {path}: {e}")


def load_configuration():
    cameras = load_json_file(CAMERAS_CONFIG_FILE)
    turnstiles = load_json_file(TURNSTILES_CONFIG_FILE)
    hardware = load_json_file(HARDWARE_CONFIG_FILE)

    camera_ids = {
        camera["camera_id"]
        for camera in cameras
    }

    logical_mapping = {}

    for turnstile in turnstiles:
        camera_id = turnstile["camera_id"]
        turnstile_id = turnstile["turnstile_id"]

        if camera_id not in camera_ids:
            raise RuntimeError(
                f"A câmera {camera_id} não existe em cameras.json."
            )

        if camera_id in logical_mapping:
            raise RuntimeError(
                f"A câmera {camera_id} está associada a mais de uma catraca."
            )

        logical_mapping[camera_id] = {
            "turnstile_id": turnstile_id,
            "passage_timeout": float(
                turnstile.get("passage_timeout", 5)
            ),
            "max_pending_age": float(
                turnstile.get("max_pending_age", DEFAULT_MAX_PENDING_AGE)
            )
        }

    hardware_by_id = {}

    for device in hardware.get("devices", []):
        turnstile_id = device["turnstile_id"]
        hardware_by_id[turnstile_id] = device

    for logical in logical_mapping.values():
        turnstile_id = logical["turnstile_id"]

        if turnstile_id not in hardware_by_id:
            raise RuntimeError(
                f"Não existe configuração física para {turnstile_id}."
            )

    return (
        logical_mapping,
        hardware_by_id,
        hardware.get("monitor", {})
    )


class AccessLogger:
    def __init__(self):
        self.lock = threading.Lock()

        self.connection = sqlite3.connect(
            DATABASE_FILE,
            check_same_thread=False
        )

        self.connection.execute("PRAGMA journal_mode=WAL")
        self.connection.execute("PRAGMA synchronous=NORMAL")

        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS access_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cpf TEXT NOT NULL,
                direction TEXT NOT NULL,
                occurred_at INTEGER NOT NULL,
                camera_id TEXT NOT NULL,
                turnstile_id TEXT NOT NULL
            )
            """
        )

        self.connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_access_logs_cpf
            ON access_logs(cpf)
            """
        )

        self.connection.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_access_logs_occurred_at
            ON access_logs(occurred_at)
            """
        )

        self.connection.commit()

    def register(
        self,
        cpf,
        direction,
        camera_id,
        turnstile_id
    ):
        occurred_at = int(time.time())

        with self.lock:
            self.connection.execute(
                """
                INSERT INTO access_logs (
                    cpf,
                    direction,
                    occurred_at,
                    camera_id,
                    turnstile_id
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    cpf,
                    direction,
                    occurred_at,
                    camera_id,
                    turnstile_id
                )
            )

            self.connection.commit()

        print(f"[{turnstile_id}] Log registrado: {cpf} - {direction}.")

    def close(self):
        with self.lock:
            self.connection.close()


class TurnstileController:
    def __init__(
        self,
        turnstile_id,
        driver,
        max_pending_age,
        access_logger
    ):
        self.turnstile_id = turnstile_id
        self.driver = driver
        self.max_pending_age = max_pending_age
        self.access_logger = access_logger

        self.condition = threading.Condition()
        self.latest_qr = None
        self.busy = False

        self.worker = threading.Thread(
            target=self.process,
            daemon=True
        )

        self.worker.start()

    def add_qr(
        self,
        decoded_data,
        camera_id,
        captured_at
    ):
        event = {
            "decoded_data": decoded_data,
            "camera_id": camera_id,
            "captured_at": captured_at,
            "received_at": time.monotonic()
        }

        with self.condition:
            had_pending = self.latest_qr is not None
            self.latest_qr = event

            if self.busy:
                if had_pending:
                    print(
                        f"[{self.turnstile_id}] "
                        f"Leitura pendente substituída pela mais recente."
                    )
                else:
                    print(
                        f"[{self.turnstile_id}] "
                        f"Nova leitura aguardando o próximo ciclo."
                    )

            self.condition.notify()

    def take_latest(self):
        with self.condition:
            while self.latest_qr is None:
                self.condition.wait()

            event = self.latest_qr
            self.latest_qr = None
            self.busy = True

            return event

    def finish(self):
        with self.condition:
            self.busy = False
            self.condition.notify()

    def process(self):
        while True:
            event = self.take_latest()

            age = time.monotonic() - event["received_at"]

            if age > self.max_pending_age:
                print(
                    f"[{self.turnstile_id}] "
                    f"QR descartado por estar desatualizado "
                    f"({age:.2f}s)."
                )
                self.finish()
                continue

            decoded_data = event["decoded_data"]
            camera_id = event["camera_id"]

            print(f"\n[{self.turnstile_id}] QR recebido de {camera_id}")
            print(f"[{self.turnstile_id}] Conteúdo: {decoded_data}")

            try:
                valid, cpf = liberar_entrada(decoded_data)
            except Exception as e:
                print(f"[{self.turnstile_id}] Erro ao interpretar QR: {e}")
                self.finish()
                continue

            if not valid:
                print(f"[{self.turnstile_id}] Código inválido.")
                self.finish()
                continue

            print(f"[{self.turnstile_id}] Código válido.")

            try:
                self.driver.release()
                result = self.driver.wait_for_passage()
            except Exception as e:
                print(
                    f"[{self.turnstile_id}] "
                    f"Erro de comunicação com a catraca: {e}"
                )
                self.finish()
                continue

            status = result.get("status")
            direction = result.get("direction")

            if status == "passed":
                if direction not in ("entrada", "saida"):
                    print(
                        f"[{self.turnstile_id}] "
                        f"Passagem confirmada, mas a direção "
                        f"não pôde ser determinada."
                    )
                else:
                    print(
                        f"[{self.turnstile_id}] "
                        f"PASSAGEM CONFIRMADA: {direction.upper()}."
                    )

                    try:
                        self.access_logger.register(
                            cpf=cpf,
                            direction=direction,
                            camera_id=camera_id,
                            turnstile_id=self.turnstile_id
                        )
                    except Exception as e:
                        print(f"[{self.turnstile_id}] Erro ao registrar log: {e}")

            elif status == "give_up":
                print(f"[{self.turnstile_id}] PASSAGEM CANCELADA.")
            else:
                print(f"[{self.turnstile_id}] TIMEOUT SEM PASSAGEM.")

            self.finish()


class AccessController:
    def __init__(
        self,
        logical_mapping,
        hardware_by_id,
        monitor_config,
        registry,
        access_logger
    ):
        self.logical_mapping = logical_mapping
        self.controllers = {}
        self.recent_events = {}
        self.dedup_lock = threading.Lock()

        for camera_id, logical in logical_mapping.items():
            turnstile_id = logical["turnstile_id"]
            hardware = hardware_by_id[turnstile_id]

            try:
                driver = create_turnstile_driver(
                    hardware,
                    logical["passage_timeout"],
                    simulation_mode=bool(SIMULACAO),
                    simulator_host=SIMULATOR_HOST,
                    simulator_port=SIMULATOR_PORT
                )

                driver.initialize(monitor_config)
                registry.register(driver)

                controller = TurnstileController(
                    turnstile_id,
                    driver,
                    logical["max_pending_age"],
                    access_logger
                )

                self.controllers[turnstile_id] = controller

                print(f"{camera_id} -> {turnstile_id}")
            except Exception as e:
                print(f"[{turnstile_id}] Erro ao inicializar: {e}")

    def is_duplicate(
        self,
        camera_id,
        decoded_data,
        captured_at
    ):
        if captured_at is None:
            return False

        key = (
            camera_id,
            repr(decoded_data),
            captured_at
        )

        now = time.monotonic()

        with self.dedup_lock:
            expired = [
                event_key
                for event_key, timestamp in self.recent_events.items()
                if now - timestamp > MQTT_DEDUP_TTL
            ]

            for expired_key in expired:
                del self.recent_events[expired_key]

            if key in self.recent_events:
                return True

            self.recent_events[key] = now

        return False

    def receive_qr(
        self,
        camera_id,
        decoded_data,
        captured_at
    ):
        if self.is_duplicate(
            camera_id,
            decoded_data,
            captured_at
        ):
            print("Evento MQTT duplicado ignorado.")
            return

        logical = self.logical_mapping.get(camera_id)

        if logical is None:
            print(f"Nenhuma catraca associada à câmera {camera_id}.")
            return

        turnstile_id = logical["turnstile_id"]
        controller = self.controllers.get(turnstile_id)

        if controller is None:
            print(f"{turnstile_id} indisponível.")
            return

        controller.add_qr(
            decoded_data,
            camera_id,
            captured_at
        )


access_controller = None


def on_connect(
    client,
    userdata,
    flags,
    reason_code,
    properties
):
    if reason_code == 0:
        print(f"Conectado ao MQTT {MQTT_BROKER}:{MQTT_PORT}")
        client.subscribe(
            MQTT_TOPIC,
            qos=1
        )
        print(f"Assinando: {MQTT_TOPIC}")
    else:
        print(f"Erro MQTT: {reason_code}")


def on_message(
    client,
    userdata,
    msg
):
    try:
        message = json.loads(msg.payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        print("Mensagem MQTT inválida.")
        return

    if message.get("message_type") != "event":
        return

    if message.get("schema") != "ods.codigos.i6":
        return

    payload = message.get("payload")

    if not isinstance(payload, dict):
        return

    camera_id = payload.get("camera_id")
    decoded_data = payload.get("decoded_data")
    captured_at = payload.get("captured_at")

    if not isinstance(camera_id, str):
        print("camera_id inválido.")
        return

    if decoded_data is None:
        print("decoded_data inválido.")
        return

    access_controller.receive_qr(
        camera_id,
        decoded_data,
        captured_at
    )


def start_visual_simulator_if_needed(hardware_by_id):
    if not SIMULACAO:
        return None

    has_simulated_turnstile = any(
        str(config.get("model", "")).lower() == "simulated"
        or str(config.get("protocol", "")).lower() == "simulation"
        for config in hardware_by_id.values()
    )

    if not has_simulated_turnstile:
        return None

    if not SIMULATOR_FILE.exists():
        raise RuntimeError(f"Arquivo do simulador não encontrado: {SIMULATOR_FILE}")

    print("Modo SIMULACAO = 1. Iniciando simulador visual de catracas...")

    process = subprocess.Popen(
        [
            sys.executable,
            str(SIMULATOR_FILE),
            "--host",
            SIMULATOR_HOST,
            "--port",
            str(SIMULATOR_PORT)
        ]
    )

    time.sleep(1.0)

    return process


def main():
    global access_controller

    access_logger = None
    monitor_server = None
    simulator_process = None

    try:
        (
            logical_mapping,
            hardware_by_id,
            monitor_config
        ) = load_configuration()
    except RuntimeError as e:
        print(f"Erro de configuração: {e}")
        return

    try:
        access_logger = AccessLogger()
    except Exception as e:
        print(f"Erro ao inicializar banco de logs: {e}")
        return

    registry = TurnstileRegistry()

    has_controlid = any(
        str(config.get("model", "")).lower() == "controlid_idblock"
        for config in hardware_by_id.values()
    )

    needs_monitor = has_controlid or bool(SIMULACAO)

    if needs_monitor:
        try:
            monitor_server = start_monitor_server(
                registry,
                monitor_config
            )
        except Exception as e:
            print(f"Erro ao iniciar monitor HTTP: {e}")
            access_logger.close()
            return

    try:
        simulator_process = start_visual_simulator_if_needed(hardware_by_id)
    except Exception as e:
        print(f"Erro ao iniciar simulador visual: {e}")

        if monitor_server is not None:
            monitor_server.shutdown()
            monitor_server.server_close()

        access_logger.close()
        return

    access_controller = AccessController(
        logical_mapping,
        hardware_by_id,
        monitor_config,
        registry,
        access_logger
    )

    if not access_controller.controllers:
        print("Nenhuma catraca disponível.")

        if simulator_process is not None:
            simulator_process.terminate()

        if monitor_server is not None:
            monitor_server.shutdown()
            monitor_server.server_close()

        access_logger.close()
        return

    client = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2,
        client_id=MQTT_CLIENT_ID
    )

    client.on_connect = on_connect
    client.on_message = on_message

    try:
        client.connect(
            MQTT_BROKER,
            MQTT_PORT,
            keepalive=60
        )
        client.loop_forever()

    except KeyboardInterrupt:
        print("\nEncerrando A2...")

    except Exception as e:
        print(f"Erro: {e}")

    finally:
        try:
            client.disconnect()
        except Exception:
            pass

        if monitor_server is not None:
            monitor_server.shutdown()
            monitor_server.server_close()

        if simulator_process is not None:
            simulator_process.terminate()

        if access_logger is not None:
            access_logger.close()


if __name__ == "__main__":
    main()
