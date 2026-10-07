"""Entry point do sistema.

Inicia um único processo que serve:
- A API do backend: `/get-payload`, `/get-payloads`, etc.
- O frontend (crachá QR) em `/app` (montado pelo backend/app.py).

Uso: python main.py
"""
import uvicorn

from backend.config import IP_ADRESS, PORT

if __name__ == "__main__":
    uvicorn.run(
        "backend.app:app",
        host=IP_ADRESS,
        port=PORT,
        reload=True,
    )