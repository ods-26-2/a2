import os
import secrets
from pathlib import Path

PAYLOAD_BATCH_SIZE = 10
IP_ADRESS = "0.0.0.0"
PORT = 8080
DB_PATH = Path(__file__).resolve().parent / "db" / "db.db"

# Chave temporária AES-256 (32 bytes) para cifragem dos payloads QR
AES_KEY = b"a" * 32

ENV_PATH = Path(__file__).resolve().parent.parent / ".env"


def get_or_create_access_event_key() -> str:
    """Obtém ou gera a chave fixa para a rota /acess-event.
    
    A chave é gerada na primeira execução e persistida exclusivamente
    no arquivo .env (nunca no banco de dados). Em execuções seguintes,
    a chave existente é reutilizada.
    """
    env_key = os.environ.get("ACCESS_EVENT_KEY")
    if env_key and env_key.strip():
        return env_key.strip()

    if ENV_PATH.exists():
        try:
            content = ENV_PATH.read_text(encoding="utf-8")
            for line in content.splitlines():
                line = line.strip()
                if line.startswith("ACCESS_EVENT_KEY="):
                    key_val = line.split("=", 1)[1].strip()
                    if key_val:
                        os.environ["ACCESS_EVENT_KEY"] = key_val
                        return key_val
        except Exception:
            pass

    # Se não existe, gera uma chave segura de 32 bytes (64 caracteres hex)
    generated_key = secrets.token_hex(32)

    try:
        if ENV_PATH.exists():
            existing = ENV_PATH.read_text(encoding="utf-8")
            prefix = "" if existing.endswith("\n") or not existing else "\n"
            ENV_PATH.write_text(existing + f"{prefix}ACCESS_EVENT_KEY={generated_key}\n", encoding="utf-8")
        else:
            ENV_PATH.write_text(
                f"# Chave fixa para eventos de acesso das catracas (A2 Local)\nACCESS_EVENT_KEY={generated_key}\n",
                encoding="utf-8",
            )
    except Exception as e:
        print(f"[config] Aviso: não foi possível gravar no .env: {e}")

    os.environ["ACCESS_EVENT_KEY"] = generated_key
    return generated_key


ACCESS_EVENT_KEY = get_or_create_access_event_key()
