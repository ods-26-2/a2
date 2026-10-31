"""Entry point do sistema.

Inicia um único processo que serve:

- A API do backend: /get-payload, /get-payloads, etc.
- O frontend (crachá QR) em /app.

Uso:
    python main.py
    python main.py 8080
"""

import os
import sys

import uvicorn

from backend.config import IP_ADRESS, PORT


if __name__ == "__main__":
    port_env = os.environ.get("PORT")
    port = int(port_env) if port_env else (int(sys.argv[1]) if len(sys.argv) > 1 else PORT)

    uvicorn.run(
        "backend.app:app",
        host=os.environ.get("HOST", IP_ADRESS),
        port=port,
        reload=os.environ.get("RELOAD", "").lower() in ("1", "true", "yes"),
    )