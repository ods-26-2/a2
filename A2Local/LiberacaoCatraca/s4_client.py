import hashlib
import json
import os
import threading
import uuid
from datetime import (
    datetime,
    timedelta,
    timezone
)

from confluent_kafka import Producer


def _read_bool(
    name,
    default=False
):
    value = os.getenv(
        name
    )

    if value is None:
        return default

    return (
        value.strip().lower()
        in (
            "1",
            "true",
            "yes",
            "sim",
            "on"
        )
    )


def _utc_now_iso():
    return (
        datetime.now(
            timezone.utc
        )
        .isoformat(
            timespec="milliseconds"
        )
        .replace(
            "+00:00",
            "Z"
        )
    )


class S4Client:
    """
    Integração A2 -> S4 para evidência de mídia.

    Modo real:
        A2 publica ods.s4.capture.command.
        A2 consome reply e ods.s4.clip.

    Modo de teste:
        TESTE_S4=true

        Nenhuma mensagem é enviada ao S4.
        Uma evidência falsa READY é gerada localmente
        para permitir testar o banco/API antes do S4 existir.
    """

    def __init__(
        self,
        access_logger
    ):
        self.access_logger = (
            access_logger
        )

        self.test_mode = _read_bool(
            "TESTE_S4",
            True
        )

        self.bootstrap_servers = (
            os.getenv(
                "KAFKA_BOOTSTRAP_SERVERS",
                "localhost:9092"
            )
        )

        self.command_topic = os.getenv(
            "S4_CAPTURE_COMMAND_TOPIC",
            "ods.s4.capture.command"
        )

        self.reply_topic = os.getenv(
            "S4_CAPTURE_REPLY_TOPIC",
            "ods.s4.capture.command.reply"
        )

        self.clip_topic = os.getenv(
            "S4_CLIP_TOPIC",
            "ods.s4.clip"
        )

        self.cache = {}
        self.lock = threading.Lock()
        self.producer = None

        if self.test_mode:
            print(
                "[S4] TESTE_S4=true. "
                "Evidências serão simuladas."
            )

        else:
            self.producer = Producer(
                {
                    "bootstrap.servers":
                        self.bootstrap_servers,

                    "enable.idempotence":
                        True,

                    "acks":
                        "all"
                }
            )

            print(
                "[S4] integração real habilitada."
            )

            print(
                f"[S4] command topic: "
                f"{self.command_topic}"
            )

            print(
                f"[S4] reply topic: "
                f"{self.reply_topic}"
            )

            print(
                f"[S4] clip topic: "
                f"{self.clip_topic}"
            )

    def consumer_topics(self):
        if self.test_mode:
            return []

        return [
            self.reply_topic,
            self.clip_topic
        ]

    def _merge_cache(
        self,
        request_id,
        fields
    ):
        if not request_id:
            return

        with self.lock:
            current = self.cache.get(
                request_id,
                {
                    "media_request_id":
                        request_id,

                    "media_status":
                        "PENDING"
                }
            )

            current.update(
                {
                    key: value
                    for key, value
                    in fields.items()
                    if value is not None
                }
            )

            self.cache[
                request_id
            ] = current

    def get_evidence(
        self,
        request_id
    ):
        if not request_id:
            return {
                "media_request_id":
                    None,

                "media_clip_id":
                    None,

                "media_type":
                    None,

                "media_uri":
                    None,

                "media_hash_sha256":
                    None,

                "media_expires_at":
                    None,

                "media_status":
                    "NONE"
            }

        with self.lock:
            evidence = dict(
                self.cache.get(
                    request_id,
                    {
                        "media_request_id":
                            request_id,

                        "media_status":
                            "PENDING"
                    }
                )
            )

        evidence.setdefault(
            "media_request_id",
            request_id
        )

        evidence.setdefault(
            "media_clip_id",
            None
        )

        evidence.setdefault(
            "media_type",
            None
        )

        evidence.setdefault(
            "media_uri",
            None
        )

        evidence.setdefault(
            "media_hash_sha256",
            None
        )

        evidence.setdefault(
            "media_expires_at",
            None
        )

        evidence.setdefault(
            "media_status",
            "PENDING"
        )

        return evidence

    def _update_evidence(
        self,
        request_id,
        fields
    ):
        self._merge_cache(
            request_id,
            fields
        )

        evidence = self.get_evidence(
            request_id
        )

        self.access_logger.update_evidence(
            request_id=request_id,
            evidence=evidence
        )

    def _delivery_report(
        self,
        error,
        message
    ):
        if error is not None:
            print(
                "[S4] Falha ao publicar "
                f"capture.command: {error}"
            )

    def request_snapshot(
        self,
        source_id,
        captured_at,
        cpf
    ):
        request_id = str(
            uuid.uuid4()
        )

        initial = {
            "media_request_id":
                request_id,

            "media_type":
                "SNAPSHOT",

            "media_status":
                "PENDING"
        }

        self._merge_cache(
            request_id,
            initial
        )

        if self.test_mode:
            clip_id = str(
                uuid.uuid4()
            )

            fake_hash = hashlib.sha256(
                clip_id.encode(
                    "utf-8"
                )
            ).hexdigest()

            expires_at = (
                datetime.now(
                    timezone.utc
                )
                + timedelta(
                    days=30
                )
            )

            fake_evidence = {
                "media_request_id":
                    request_id,

                "media_clip_id":
                    clip_id,

                "media_type":
                    "SNAPSHOT",

                "media_uri":
                    (
                        "teste-s4://snapshots/"
                        f"{clip_id}.jpg"
                    ),

                "media_hash_sha256":
                    fake_hash,

                "media_expires_at":
                    (
                        expires_at
                        .isoformat(
                            timespec="milliseconds"
                        )
                        .replace(
                            "+00:00",
                            "Z"
                        )
                    ),

                "media_status":
                    "READY"
            }

            self._merge_cache(
                request_id,
                fake_evidence
            )

            print(
                "[S4 TESTE] Snapshot simulado: "
                f"{clip_id}"
            )

            return request_id

        command = {
            "schema":
                "ods.s4.capture.command",

            "schema_version":
                "1.0",

            "message_type":
                "command",

            "message_id":
                request_id,

            "producer":
                "A2",

            "target":
                "S4",

            "published_at":
                _utc_now_iso(),

            "payload": {
                "source_id":
                    source_id,

                "media_type":
                    "SNAPSHOT",

                "at":
                    captured_at,

                "event_id":
                    None,

                "label":
                    f"acesso CPF {cpf}"
            }
        }

        try:
            self.producer.produce(
                self.command_topic,
                key=source_id.encode(
                    "utf-8"
                ),
                value=json.dumps(
                    command,
                    ensure_ascii=False
                ).encode(
                    "utf-8"
                ),
                callback=
                    self._delivery_report
            )

            self.producer.poll(
                0
            )

            print(
                "[S4] Snapshot solicitado "
                f"para {source_id}. "
                f"request_id={request_id}"
            )

        except Exception as error:
            self._update_evidence(
                request_id,
                {
                    "media_status":
                        "ERROR"
                }
            )

            print(
                "[S4] Erro ao solicitar "
                f"snapshot: {error}"
            )

        return request_id

    def handles_schema(
        self,
        schema
    ):
        return schema in (
            "ods.s4.capture.command.reply",
            "ods.s4.capture.reply",
            "ods.s4.clip"
        )

    def handle_message(
        self,
        message
    ):
        schema = message.get(
            "schema"
        )

        if schema == "ods.s4.clip":
            self._handle_clip(
                message
            )
            return

        if schema in (
            "ods.s4.capture.command.reply",
            "ods.s4.capture.reply"
        ):
            self._handle_capture_reply(
                message
            )

    def _handle_capture_reply(
        self,
        message
    ):
        payload = message.get(
            "payload"
        )

        if not isinstance(
            payload,
            dict
        ):
            payload = {}

        request_id = (
            message.get(
                "correlation_id"
            )
            or payload.get(
                "correlation_id"
            )
            or payload.get(
                "request_id"
            )
        )

        if not request_id:
            print(
                "[S4] Reply sem correlation_id."
            )
            return

        status = str(
            payload.get(
                "status",
                "OK"
            )
        ).upper()

        clip_id = payload.get(
            "clip_id"
        )

        if status != "OK":
            self._update_evidence(
                request_id,
                {
                    "media_status":
                        "ERROR"
                }
            )

            print(
                "[S4] Captura rejeitada. "
                f"request_id={request_id}, "
                f"status={status}"
            )

            return

        self._update_evidence(
            request_id,
            {
                "media_clip_id":
                    clip_id,

                "media_type":
                    "SNAPSHOT",

                # O descritor completo ainda virá
                # pelo ods.s4.clip.
                "media_status":
                    "PENDING"
            }
        )

        print(
            "[S4] capture.reply recebido. "
            f"clip_id={clip_id}"
        )

    def _handle_clip(
        self,
        message
    ):
        payload = message.get(
            "payload"
        )

        if not isinstance(
            payload,
            dict
        ):
            print(
                "[S4] ods.s4.clip sem payload."
            )
            return

        request_id = message.get(
            "correlation_id"
        )

        if not request_id:
            print(
                "[S4] ods.s4.clip sem "
                "correlation_id."
            )
            return

        evidence = {
            "media_clip_id":
                payload.get(
                    "clip_id"
                ),

            "media_type":
                payload.get(
                    "media_type"
                ),

            "media_uri":
                payload.get(
                    "media_uri"
                ),

            "media_hash_sha256":
                payload.get(
                    "hash_sha256"
                ),

            "media_expires_at":
                payload.get(
                    "expires_at"
                ),

            "media_status":
                "READY"
        }

        self._update_evidence(
            request_id,
            evidence
        )

        print(
            "[S4] Evidência READY: "
            f"{payload.get('clip_id')}"
        )

    def close(self):
        if (
            self.producer is not None
        ):
            try:
                self.producer.flush(
                    5
                )
            except Exception:
                pass
