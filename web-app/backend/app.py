import sys
from pathlib import Path

# Garante que o diretório do backend esteja no path mesmo quando este módulo
# é importado de fora (ex.: pelo main.py da raiz e pelo reload do uvicorn)
backend_dir = Path(__file__).resolve().parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
import config

from services import payload
from db.connection import validate_user_access, get_payload_batch_size

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
if frontend_dir.exists():
    from fastapi.staticfiles import StaticFiles
    app.mount("/app", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")


def validate_user_password(cpf: int, password: str):
    ok, reason, user = validate_user_access(cpf=cpf, password=password)
    if not ok:
        raise HTTPException(status_code=401, detail=reason)
    return user


@app.get("/")
def index():
    if frontend_dir.exists():
        return RedirectResponse(url="/app/")
    return {"status": "Working"}


@app.get("/get-payloads", dependencies=[Depends(validate_user_password)])
def get_payloads(cpf: int, password: str):
    batch_size = get_payload_batch_size()
    return payload.get_payloads(cpf=cpf, length=batch_size)


@app.get("/get-payload", dependencies=[Depends(validate_user_password)])
def get_payload(cpf: int, password: str):
    return payload.get_payloads(cpf=cpf, length=1)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host=config.IP_ADRESS, port=config.PORT, reload=True)