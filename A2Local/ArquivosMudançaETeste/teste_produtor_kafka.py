import json
import os
import uuid
from datetime import datetime, timezone

from confluent_kafka import Producer


BROKER = os.getenv(
    "KAFKA_BOOTSTRAP_SERVERS",
    "34.66.235.91:9093"
)

TOPIC = os.getenv(
    "KAFKA_TOPIC",
    "ods.i6.code_read"
)

SOURCE_ID = os.getenv(
    "TEST_SOURCE_ID",
    "camera-01"
)


def agora_iso():
    return (
        datetime.now(timezone.utc)
        .isoformat(timespec="milliseconds")
        .replace("+00:00", "Z")
    )


evento = {
    "message_type": "event",
    "message_id": str(uuid.uuid4()),
    "schema": "ods.i6.code_read",
    "schema_version": "1.0",
    "producer": "I6",
    "published_at": agora_iso(),
    "captured_at": agora_iso(),
    "source_id": SOURCE_ID,
    "session_id": str(uuid.uuid4()),
    "sequence": 0,
    "artifact_version": "teste-manual-a2",
    "payload": {
        "frame_index": 1,
        "code_type": "QR_CODE",
        "decoded_data": "teste-qr",
        "bbox": [10, 10, 100, 100]
    }
}

producer = Producer(
    {
        "bootstrap.servers": BROKER,
        "enable.idempotence": True,
        "acks": "all"
    }
)

producer.produce(
    TOPIC,
    key=SOURCE_ID.encode("utf-8"),
    value=json.dumps(
        evento,
        ensure_ascii=False
    ).encode("utf-8")
)

producer.flush(10)

print(
    json.dumps(
        evento,
        indent=2,
        ensure_ascii=False
    )
)
