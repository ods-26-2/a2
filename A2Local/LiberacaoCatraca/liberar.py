import json
import os
import sqlite3
import subprocess
import sys
import threading
import time
from pathlib import Path

from confluent_kafka import Consumer, KafkaError

from catraca_driver import create_turnstile_driver
from database import ensure_access_logs_schema
from catraca_monitor import (
    TurnstileRegistry,
    start_monitor_server_with_retry
)
from regras_entrada import liberar_entrada
from s4_client import S4Client


def ler_bool(nome, padrao=False):
    valor = os.getenv(nome)
    if valor is None:
        return padrao

    valor = valor.strip().lower()

    if valor in ("1", "true", "yes", "sim", "on"):
        return True

    if valor in ("0", "false", "no", "nao", "não", "off"):
        return False

    raise ValueError(f"{nome} deve ser true ou false.")


# ============================================================
# KAFKA
# ============================================================

KAFKA_BOOTSTRAP_SERVERS = os.getenv(
    "KAFKA_BOOTSTRAP_SERVERS",
    "34.66.235.91:9093"
)

KAFKA_TOPIC = os.getenv(
    "KAFKA_TOPIC",
    "ods.i6.code_read"
)

KAFKA_GROUP_ID = os.getenv(
    "KAFKA_GROUP_ID",
    "a2-controle-acesso"
)

KAFKA_AUTO_OFFSET_RESET = os.getenv(
    "KAFKA_AUTO_OFFSET_RESET",
    "latest"
)

KAFKA_DEDUP_TTL = float(
    os.getenv("KAFKA_DEDUP_TTL", "60")
)


# ============================================================
# ARQUIVOS / SIMULAÇÃO
# ============================================================

TURNSTILES_CONFIG_FILE = Path(__file__).with_name("catracas.json")
HARDWARE_CONFIG_FILE = Path(__file__).with_name("configCatraca.json")
DATABASE_FILE = Path(
    os.getenv(
        "A2_DATABASE_FILE",
        str(Path(__file__).with_name("acessos.db"))
    )
)
SIMULATOR_FILE = Path(__file__).with_name("simulador_catracas.py")

DEFAULT_MAX_PENDING_AGE = float(
    os.getenv("A2_DEFAULT_MAX_PENDING_AGE", "2.0")
)

SIMULACAO = ler_bool(
    "A2_SIMULATION",
    True
)

SIMULATOR_HOST = os.getenv(
    "A2_SIMULATOR_HOST",
    "127.0.0.1"
)

SIMULATOR_PORT = int(
    os.getenv("A2_SIMULATOR_PORT", "8765")
)


TURNSTILE_RETRY_SECONDS = float(
    os.getenv(
        "A2_TURNSTILE_RETRY_SECONDS",
        "5"
    )
)

MONITOR_RETRY_SECONDS = float(
    os.getenv(
        "A2_MONITOR_RETRY_SECONDS",
        "5"
    )
)


# ============================================================
# CONFIGURAÇÃO
# ============================================================

def load_json_file(path):
    try:
        with open(path, "r", encoding="utf-8") as file:
            return json.load(file)
    except FileNotFoundError:
        raise RuntimeError(f"Arquivo não encontrado: {path}")
    except json.JSONDecodeError as e:
        raise RuntimeError(f"JSON inválido em {path}: {e}")


def load_configuration():
    """
    O A2 não abre câmeras.

    O vínculo agora é diretamente:
        source_id do I6 -> turnstile_id
    """

    turnstiles = load_json_file(TURNSTILES_CONFIG_FILE)
    hardware = load_json_file(HARDWARE_CONFIG_FILE)

    if not isinstance(turnstiles, list):
        raise RuntimeError("catracas.json deve conter uma lista.")

    logical_mapping = {}

    for turnstile in turnstiles:
        source_id = str(turnstile.get("source_id", "")).strip()
        turnstile_id = str(turnstile.get("turnstile_id", "")).strip()

        if not source_id:
            raise RuntimeError("Existe catraca sem source_id.")

        if not turnstile_id:
            raise RuntimeError(
                f"source_id {source_id} não possui turnstile_id."
            )

        if source_id in logical_mapping:
            raise RuntimeError(
                f"source_id duplicado em catracas.json: {source_id}"
            )

        logical_mapping[source_id] = {
            "turnstile_id": turnstile_id,
            "passage_timeout": float(
                turnstile.get("passage_timeout", 5)
            ),
            "max_pending_age": float(
                turnstile.get(
                    "max_pending_age",
                    DEFAULT_MAX_PENDING_AGE
                )
            )
        }

    hardware_by_id = {}

    for device in hardware.get("devices", []):
        turnstile_id = device.get("turnstile_id")

        if not turnstile_id:
            raise RuntimeError(
                "Dispositivo sem turnstile_id em configCatraca.json."
            )

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


# ============================================================
# SQLITE
# ============================================================

class AccessLogger:
    def __init__(self):
        self.lock = threading.Lock()

        DATABASE_FILE.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        self.connection = sqlite3.connect(
            DATABASE_FILE,
            check_same_thread=False,
            timeout=10
        )

        self.connection.execute(
            "PRAGMA busy_timeout = 10000"
        )

        self.connection.execute(
            "PRAGMA journal_mode=WAL"
        )

        self.connection.execute(
            "PRAGMA synchronous=NORMAL"
        )

        ensure_access_logs_schema(
            self.connection
        )

    def register(
        self,
        cpf,
        direction,
        source_id,
        turnstile_id,
        i6_message_id,
        frame_index,
        captured_at,
        evidence
    ):
        occurred_at = int(
            time.time()
        )

        with self.lock:
            cursor = self.connection.execute(
                """
                INSERT INTO access_logs (
                    cpf,
                    direction,
                    occurred_at,
                    source_id,
                    turnstile_id,

                    i6_message_id,
                    frame_index,
                    captured_at,

                    media_request_id,
                    media_clip_id,
                    media_type,
                    media_uri,
                    media_hash_sha256,
                    media_expires_at,
                    media_status
                )
                VALUES (
                    ?, ?, ?, ?, ?,
                    ?, ?, ?,
                    ?, ?, ?, ?, ?, ?, ?
                )
                """,
                (
                    cpf,
                    direction,
                    occurred_at,
                    source_id,
                    turnstile_id,

                    i6_message_id,
                    frame_index,
                    captured_at,

                    evidence.get(
                        "media_request_id"
                    ),
                    evidence.get(
                        "media_clip_id"
                    ),
                    evidence.get(
                        "media_type"
                    ),
                    evidence.get(
                        "media_uri"
                    ),
                    evidence.get(
                        "media_hash_sha256"
                    ),
                    evidence.get(
                        "media_expires_at"
                    ),
                    evidence.get(
                        "media_status",
                        "NONE"
                    )
                )
            )

            self.connection.commit()

            log_id = cursor.lastrowid

        print(
            f"[{turnstile_id}] "
            f"Log registrado: {cpf} - {direction}. "
            f"id={log_id}"
        )

        return log_id

    def update_evidence(
        self,
        request_id,
        evidence
    ):
        if not request_id:
            return 0

        with self.lock:
            cursor = self.connection.execute(
                """
                UPDATE access_logs
                SET
                    media_clip_id = COALESCE(
                        ?,
                        media_clip_id
                    ),
                    media_type = COALESCE(
                        ?,
                        media_type
                    ),
                    media_uri = COALESCE(
                        ?,
                        media_uri
                    ),
                    media_hash_sha256 = COALESCE(
                        ?,
                        media_hash_sha256
                    ),
                    media_expires_at = COALESCE(
                        ?,
                        media_expires_at
                    ),
                    media_status = COALESCE(
                        ?,
                        media_status
                    )
                WHERE media_request_id = ?
                """,
                (
                    evidence.get(
                        "media_clip_id"
                    ),
                    evidence.get(
                        "media_type"
                    ),
                    evidence.get(
                        "media_uri"
                    ),
                    evidence.get(
                        "media_hash_sha256"
                    ),
                    evidence.get(
                        "media_expires_at"
                    ),
                    evidence.get(
                        "media_status"
                    ),
                    request_id
                )
            )

            self.connection.commit()

            return cursor.rowcount

    def close(self):
        with self.lock:
            self.connection.close()


# ============================================================
# CONTROLE DE CADA CATRACA
# ============================================================

class TurnstileController:
    def __init__(
        self,
        turnstile_id,
        driver,
        monitor_config,
        registry,
        max_pending_age,
        access_logger,
        s4_client,
        retry_seconds
    ):
        self.turnstile_id = (
            turnstile_id
        )

        self.driver = driver

        self.monitor_config = (
            monitor_config
        )

        self.registry = registry

        self.max_pending_age = (
            max_pending_age
        )

        self.access_logger = (
            access_logger
        )

        self.s4_client = (
            s4_client
        )

        self.retry_seconds = max(
            0.5,
            float(
                retry_seconds
            )
        )

        self.condition = (
            threading.Condition()
        )

        self.latest_qr = None
        self.busy = False

        # Estado de conexão da catraca.
        self.online_event = (
            threading.Event()
        )

        self.stop_event = (
            threading.Event()
        )

        self.connection_lock = (
            threading.Lock()
        )

        # Worker que processa QR.
        self.worker = threading.Thread(
            target=self.process,
            name=(
                f"a2-qr-{turnstile_id}"
            ),
            daemon=True
        )

        # Worker independente que mantém a catraca conectada.
        self.connection_worker = (
            threading.Thread(
                target=self.connection_loop,
                name=(
                    f"a2-connect-{turnstile_id}"
                ),
                daemon=True
            )
        )

        self.worker.start()
        self.connection_worker.start()

    @property
    def online(self):
        return (
            self.online_event
            .is_set()
        )

    def mark_offline(
        self,
        reason=None
    ):
        was_online = self.online_event.is_set()

        self.online_event.clear()

        if reason is not None:
            print(
                f"[{self.turnstile_id}] "
                "OFFLINE: "
                f"{reason}"
            )

        elif was_online:
            print(
                f"[{self.turnstile_id}] "
                "OFFLINE."
            )

    def try_connect(self):
        """
        Uma tentativa de inicialização/configuração da catraca.

        Pode fazer /configure no simulador, login na Control iD,
        configurar callback etc.
        """

        with self.connection_lock:
            self.driver.initialize(
                self.monitor_config
            )

            # Em Control iD o device_id pode só existir depois
            # do initialize(). Por isso registramos aqui.
            self.registry.register(
                self.driver
            )

            self.online_event.set()

    def connection_loop(self):
        first_attempt = True

        while not self.stop_event.is_set():
            if self.online:
                # Não fazemos polling agressivo.
                # Uma falha de I/O em release() marca OFFLINE
                # e este worker volta a inicializar.
                self.stop_event.wait(
                    0.5
                )
                continue

            if not first_attempt:
                print(
                    f"[{self.turnstile_id}] "
                    "Tentando reconectar..."
                )

            first_attempt = False

            try:
                self.try_connect()

                print(
                    f"[{self.turnstile_id}] "
                    "ONLINE."
                )

            except Exception as error:
                self.mark_offline(
                    error
                )

                print(
                    f"[{self.turnstile_id}] "
                    "Nova tentativa em "
                    f"{self.retry_seconds:g}s."
                )

                if self.stop_event.wait(
                    self.retry_seconds
                ):
                    break

    def add_qr(
        self,
        decoded_data,
        source_id,
        captured_at,
        frame_index,
        message_id
    ):
        event = {
            "decoded_data":
                decoded_data,

            "source_id":
                source_id,

            "captured_at":
                captured_at,

            "frame_index":
                frame_index,

            "message_id":
                message_id,

            "received_at":
                time.monotonic()
        }

        with self.condition:
            had_pending = (
                self.latest_qr
                is not None
            )

            self.latest_qr = event

            if self.busy:
                if had_pending:
                    print(
                        f"[{self.turnstile_id}] "
                        "Leitura pendente substituída "
                        "pela mais recente."
                    )
                else:
                    print(
                        f"[{self.turnstile_id}] "
                        "Nova leitura aguardando "
                        "o próximo ciclo."
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

            age = (
                time.monotonic()
                - event[
                    "received_at"
                ]
            )

            if age > self.max_pending_age:
                print(
                    f"[{self.turnstile_id}] "
                    "QR descartado por estar "
                    f"desatualizado ({age:.2f}s)."
                )

                self.finish()
                continue

            decoded_data = event[
                "decoded_data"
            ]

            source_id = event[
                "source_id"
            ]

            captured_at = event[
                "captured_at"
            ]

            frame_index = event[
                "frame_index"
            ]

            i6_message_id = event[
                "message_id"
            ]

            print(
                f"\n[{self.turnstile_id}] "
                f"QR recebido de {source_id}"
            )

            print(
                f"[{self.turnstile_id}] "
                f"Conteúdo: {decoded_data}"
            )

            try:
                valid, cpf = (
                    liberar_entrada(
                        decoded_data
                    )
                )

            except Exception as error:
                print(
                    f"[{self.turnstile_id}] "
                    "Erro ao interpretar QR: "
                    f"{error}"
                )

                self.finish()
                continue

            if not valid:
                print(
                    f"[{self.turnstile_id}] "
                    "Código inválido."
                )

                self.finish()
                continue

            print(
                f"[{self.turnstile_id}] "
                "Código válido."
            )

            # QR válido não deve derrubar o processo só porque
            # o dispositivo está temporariamente fora da rede.
            if not self.online:
                print(
                    f"[{self.turnstile_id}] "
                    "Catraca OFFLINE. "
                    "Liberação não realizada."
                )

                self.finish()
                continue

            # ------------------------------------------------
            # Evidência S4
            # ------------------------------------------------

            media_request_id = (
                self.s4_client
                .request_snapshot(
                    source_id=
                        source_id,

                    captured_at=
                        captured_at,

                    cpf=
                        cpf
                )
            )

            try:
                self.driver.release()

                result = (
                    self.driver
                    .wait_for_passage()
                )

            except Exception as error:
                # Qualquer falha de comunicação faz a catraca
                # voltar para OFFLINE e o worker de conexão
                # começa a tentar novamente.
                self.mark_offline(
                    error
                )

                print(
                    f"[{self.turnstile_id}] "
                    "Falha durante a liberação. "
                    "A reconexão continuará "
                    "em segundo plano."
                )

                self.finish()
                continue

            status = result.get(
                "status"
            )

            direction = result.get(
                "direction"
            )

            if status == "passed":
                if direction not in (
                    "entrada",
                    "saida"
                ):
                    print(
                        f"[{self.turnstile_id}] "
                        "Passagem confirmada, mas "
                        "direção desconhecida."
                    )

                else:
                    print(
                        f"[{self.turnstile_id}] "
                        "PASSAGEM CONFIRMADA: "
                        f"{direction.upper()}."
                    )

                    evidence = (
                        self.s4_client
                        .get_evidence(
                            media_request_id
                        )
                    )

                    try:
                        self.access_logger.register(
                            cpf=cpf,
                            direction=direction,
                            source_id=source_id,
                            turnstile_id=
                                self.turnstile_id,
                            i6_message_id=
                                i6_message_id,
                            frame_index=
                                frame_index,
                            captured_at=
                                captured_at,
                            evidence=evidence
                        )

                    except Exception as error:
                        print(
                            f"[{self.turnstile_id}] "
                            "Erro ao registrar log: "
                            f"{error}"
                        )

            elif status == "give_up":
                print(
                    f"[{self.turnstile_id}] "
                    "PASSAGEM CANCELADA."
                )

            else:
                print(
                    f"[{self.turnstile_id}] "
                    "TIMEOUT SEM PASSAGEM."
                )

            self.finish()

    def close(self):
        self.stop_event.set()

# ============================================================
# CONTROLE GERAL
# ============================================================

class AccessController:
    def __init__(
        self,
        logical_mapping,
        hardware_by_id,
        monitor_config,
        registry,
        access_logger,
        s4_client
    ):
        self.logical_mapping = logical_mapping
        self.controllers = {}
        self.recent_events = {}
        self.dedup_lock = threading.Lock()

        for (
            source_id,
            logical
        ) in logical_mapping.items():
            turnstile_id = logical[
                "turnstile_id"
            ]

            hardware = hardware_by_id[
                turnstile_id
            ]

            try:
                # Criar o objeto do driver não conecta à rede.
                # A conexão real fica no worker do controller.
                driver = create_turnstile_driver(
                    hardware,
                    logical[
                        "passage_timeout"
                    ],
                    simulation_mode=bool(
                        SIMULACAO
                    ),
                    simulator_host=
                        SIMULATOR_HOST,
                    simulator_port=
                        SIMULATOR_PORT
                )

                controller = (
                    TurnstileController(
                        turnstile_id=
                            turnstile_id,

                        driver=
                            driver,

                        monitor_config=
                            monitor_config,

                        registry=
                            registry,

                        max_pending_age=
                            logical[
                                "max_pending_age"
                            ],

                        access_logger=
                            access_logger,

                        s4_client=
                            s4_client,

                        retry_seconds=
                            TURNSTILE_RETRY_SECONDS
                    )
                )

                # A catraca entra no mapa mesmo estando OFFLINE.
                self.controllers[
                    turnstile_id
                ] = controller

                print(
                    f"{source_id} -> "
                    f"{turnstile_id} "
                    "(conexão assíncrona)"
                )

            except Exception as error:
                # Configuração/modelo inválido não derruba A2
                # nem a API. Apenas esse dispositivo fica
                # indisponível.
                print(
                    f"[{turnstile_id}] "
                    "Não foi possível criar "
                    "o driver: "
                    f"{error}"
                )

    def is_duplicate(
        self,
        message_id,
        source_id,
        decoded_data,
        captured_at
    ):
        if message_id:
            key = (
                "message_id",
                message_id
            )

        else:
            key = (
                "fallback",
                source_id,
                repr(
                    decoded_data
                ),
                captured_at
            )

        now = time.monotonic()

        with self.dedup_lock:
            expired = [
                event_key
                for (
                    event_key,
                    timestamp
                )
                in self.recent_events.items()
                if (
                    now - timestamp
                    > KAFKA_DEDUP_TTL
                )
            ]

            for expired_key in expired:
                del self.recent_events[
                    expired_key
                ]

            if key in self.recent_events:
                return True

            self.recent_events[
                key
            ] = now

        return False

    def receive_qr(
        self,
        source_id,
        decoded_data,
        captured_at,
        frame_index,
        message_id=None
    ):
        if self.is_duplicate(
            message_id,
            source_id,
            decoded_data,
            captured_at
        ):
            print(
                "Evento Kafka "
                "duplicado ignorado."
            )
            return

        logical = (
            self.logical_mapping
            .get(
                source_id
            )
        )

        if logical is None:
            print(
                "Nenhuma catraca "
                "associada ao source_id "
                f"{source_id}."
            )
            return

        turnstile_id = logical[
            "turnstile_id"
        ]

        controller = (
            self.controllers
            .get(
                turnstile_id
            )
        )

        if controller is None:
            print(
                f"{turnstile_id} "
                "não possui driver válido."
            )
            return

        controller.add_qr(
            decoded_data,
            source_id,
            captured_at,
            frame_index,
            message_id
        )

    def close(self):
        for controller in (
            self.controllers
            .values()
        ):
            controller.close()

# ============================================================
# KAFKA: I6 + S4
# ============================================================

def process_i6_event(
    message,
    access_controller
):
    if message.get(
        "message_type"
    ) != "event":
        return

    if message.get(
        "schema_version"
    ) != "1.0":
        print(
            "[Kafka] schema_version "
            "não suportada para I6."
        )
        return

    if message.get(
        "producer"
    ) != "I6":
        print(
            "[Kafka] producer "
            "inesperado para I6."
        )
        return

    source_id = message.get(
        "source_id"
    )

    captured_at = message.get(
        "captured_at"
    )

    message_id = message.get(
        "message_id"
    )

    payload = message.get(
        "payload"
    )

    if (
        not isinstance(
            source_id,
            str
        )
        or not source_id.strip()
    ):
        print(
            "[Kafka] source_id inválido."
        )
        return

    if (
        not isinstance(
            captured_at,
            str
        )
        or not captured_at.strip()
    ):
        print(
            "[Kafka] captured_at inválido."
        )
        return

    if not isinstance(
        payload,
        dict
    ):
        print(
            "[Kafka] payload inválido."
        )
        return

    frame_index = payload.get(
        "frame_index"
    )

    if (
        not isinstance(
            frame_index,
            int
        )
        or frame_index < 0
    ):
        print(
            "[Kafka] frame_index inválido."
        )
        return

    decoded_data = payload.get(
        "decoded_data"
    )

    if (
        not isinstance(
            decoded_data,
            str
        )
        or not decoded_data
    ):
        print(
            "[Kafka] decoded_data inválido."
        )
        return

    access_controller.receive_qr(
        source_id=
            source_id.strip(),

        decoded_data=
            decoded_data,

        captured_at=
            captured_at,

        frame_index=
            frame_index,

        message_id=
            message_id
    )


def process_kafka_message(
    message,
    access_controller,
    s4_client
):
    if not isinstance(
        message,
        dict
    ):
        print(
            "[Kafka] JSON não é objeto."
        )
        return

    schema = message.get(
        "schema"
    )

    if schema == "ods.i6.code_read":
        process_i6_event(
            message,
            access_controller
        )
        return

    if s4_client.handles_schema(
        schema
    ):
        s4_client.handle_message(
            message
        )


def run_kafka_consumer(
    access_controller,
    s4_client
):
    consumer = Consumer(
        {
            "bootstrap.servers":
                KAFKA_BOOTSTRAP_SERVERS,

            "group.id":
                KAFKA_GROUP_ID,

            "auto.offset.reset":
                KAFKA_AUTO_OFFSET_RESET,

            "enable.auto.commit":
                False
        }
    )

    topics = [
        KAFKA_TOPIC
    ]

    topics.extend(
        s4_client.consumer_topics()
    )

    topics = list(
        dict.fromkeys(
            topics
        )
    )

    consumer.subscribe(
        topics
    )

    print(
        "[Kafka] consumidor iniciado."
    )

    print(
        f"[Kafka] broker: "
        f"{KAFKA_BOOTSTRAP_SERVERS}"
    )

    for topic in topics:
        print(
            f"[Kafka] assinando: {topic}"
        )

    print(
        f"[Kafka] group.id: "
        f"{KAFKA_GROUP_ID}"
    )

    try:
        while True:
            msg = consumer.poll(
                1.0
            )

            if msg is None:
                continue

            if msg.error():
                if (
                    msg.error().code()
                    == KafkaError._PARTITION_EOF
                ):
                    continue

                print(
                    "[Kafka] erro: "
                    f"{msg.error()}"
                )
                continue

            try:
                raw = msg.value()

                if raw is None:
                    print(
                        "[Kafka] mensagem vazia."
                    )
                else:
                    message = json.loads(
                        raw.decode(
                            "utf-8"
                        )
                    )

                    process_kafka_message(
                        message,
                        access_controller,
                        s4_client
                    )

            except (
                UnicodeDecodeError,
                json.JSONDecodeError
            ):
                print(
                    "[Kafka] mensagem "
                    "JSON inválida."
                )

            except Exception as error:
                print(
                    "[Kafka] erro ao "
                    "processar evento: "
                    f"{error}"
                )

            finally:
                try:
                    consumer.commit(
                        message=msg,
                        asynchronous=False
                    )

                except Exception as error:
                    print(
                        "[Kafka] erro "
                        f"no commit: {error}"
                    )

    finally:
        consumer.close()


# ============================================================
# SIMULADOR VISUAL ATUAL
# ============================================================

def start_visual_simulator_if_needed(
    hardware_by_id
):
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
        raise RuntimeError(
            f"Arquivo do simulador não encontrado: {SIMULATOR_FILE}"
        )

    print(
        "A2_SIMULATION=true. "
        "Iniciando simulador visual de catracas..."
    )

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


# ============================================================
# MAIN
# ============================================================

def main():
    access_logger = None
    s4_client = None
    monitor_server = None
    simulator_process = None
    access_controller = None

    try:
        (
            logical_mapping,
            hardware_by_id,
            monitor_config
        ) = load_configuration()

    except RuntimeError as error:
        print(
            "Erro de configuração: "
            f"{error}"
        )
        return

    try:
        access_logger = (
            AccessLogger()
        )

    except Exception as error:
        print(
            "Erro ao inicializar "
            "banco de logs: "
            f"{error}"
        )
        return

    s4_client = S4Client(
        access_logger
    )

    registry = (
        TurnstileRegistry()
    )

    has_controlid = any(
        str(
            config.get(
                "model",
                ""
            )
        ).lower()
        == "controlid_idblock"
        for config
        in hardware_by_id.values()
    )

    has_mobile = any(
        str(
            config.get(
                "model",
                ""
            )
        ).lower()
        == "mobile"
        for config
        in hardware_by_id.values()
    )

    needs_monitor = (
        has_controlid
        or has_mobile
        or bool(
            SIMULACAO
        )
    )

    if needs_monitor:
        # Esta chamada NÃO falha o A2 se a porta/IP estiverem
        # indisponíveis. O manager tenta de novo em background.
        monitor_server = (
            start_monitor_server_with_retry(
                registry,
                monitor_config,
                retry_seconds=
                    MONITOR_RETRY_SECONDS
            )
        )

    try:
        simulator_process = (
            start_visual_simulator_if_needed(
                hardware_by_id
            )
        )

    except Exception as error:
        # O simulador visual é auxiliar. Falhar nele não deve
        # derrubar Kafka, banco ou API.
        print(
            "Erro ao iniciar "
            "simulador visual: "
            f"{error}"
        )

    access_controller = (
        AccessController(
            logical_mapping,
            hardware_by_id,
            monitor_config,
            registry,
            access_logger,
            s4_client
        )
    )

    if not access_controller.controllers:
        print(
            "Nenhuma catraca com driver válido. "
            "A2 continuará ativo e consumindo Kafka."
        )

    try:
        run_kafka_consumer(
            access_controller,
            s4_client
        )

    except KeyboardInterrupt:
        print(
            "\nEncerrando A2..."
        )

    except Exception as error:
        print(
            f"Erro no A2: {error}"
        )

    finally:
        if access_controller is not None:
            access_controller.close()

        if monitor_server is not None:
            monitor_server.shutdown()

        if simulator_process is not None:
            try:
                simulator_process.terminate()
            except Exception:
                pass

        if s4_client is not None:
            s4_client.close()

        if access_logger is not None:
            access_logger.close()


if __name__ == "__main__":
    main()
