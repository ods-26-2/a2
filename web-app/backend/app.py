import sys
from pathlib import Path

# Garante que o diretório do backend esteja no path mesmo quando este módulo
# é importado de fora (ex.: pelo main.py da raiz e pelo reload do uvicorn)
backend_dir = Path(__file__).resolve().parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, FileResponse
import config

from services import payload
from db.connection import (
    validate_user_access,
    get_payload_batch_size,
    set_payload_batch_size,
    get_system_config,
    get_all_users,
    get_user_by_cpf,
    add_user,
    delete_user_by_cpf,
    validate_admin_credentials,
    create_admin_session,
    verify_admin_session,
    delete_admin_session,
    update_user_expiration,
    update_admin_password,
)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer(auto_error=False)


def require_admin_auth(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    x_admin_token: Optional[str] = Header(None, alias="X-Admin-Token"),
) -> str:
    token = None
    if credentials and credentials.scheme.lower() == "bearer":
        token = credentials.credentials
    elif x_admin_token:
        token = x_admin_token

    if not token:
        raise HTTPException(
            status_code=401,
            detail="Autenticação administrativa obrigatória",
            headers={"WWW-Authenticate": "Bearer"},
        )

    username = verify_admin_session(token)
    if not username:
        raise HTTPException(
            status_code=401,
            detail="Sessão administrativa expirada ou inválida. Faça login novamente.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return username


frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
dist_dir = frontend_dir / "dist"
static_dir = dist_dir if dist_dir.exists() else frontend_dir
if static_dir.exists():
    from fastapi.staticfiles import StaticFiles
    app.mount("/app", StaticFiles(directory=str(static_dir), html=True), name="frontend")
    assets_dir = static_dir / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="root_assets")
        app.mount("/admin/assets", StaticFiles(directory=str(assets_dir)), name="admin_assets")


class UserAuthRequest(BaseModel):
    cpf: int
    password: str


@app.get("/")
def index():
    if frontend_dir.exists():
        return RedirectResponse(url="/app/")
    return {"status": "Working"}


@app.get("/admin")
@app.get("/admin/")
def admin_page():
    if static_dir.exists():
        index_file = static_dir / "index.html"
        if index_file.exists():
            return FileResponse(index_file)
    return RedirectResponse(url="/app/")


@app.post("/get-payloads")
def get_payloads(data: UserAuthRequest):
    ok, reason, user = validate_user_access(cpf=data.cpf, password=data.password)
    if not ok:
        raise HTTPException(status_code=401, detail=reason)
    batch_size = get_payload_batch_size()
    return payload.get_payloads(cpf=data.cpf, length=batch_size)


@app.post("/get-payload")
def get_payload(data: UserAuthRequest):
    ok, reason, user = validate_user_access(cpf=data.cpf, password=data.password)
    if not ok:
        raise HTTPException(status_code=401, detail=reason)
    return payload.get_payloads(cpf=data.cpf, length=1)


# ==============================================================================
# ADMIN AUTH & API ENDPOINTS
# ==============================================================================

class AdminLoginRequest(BaseModel):
    username: str
    password: str


class AdminUserCreate(BaseModel):
    cpf: int
    password: Optional[str] = None
    is_recurring: bool = True
    specific_date: Optional[str] = None
    expiration_date: Optional[str] = None
    access_days: Optional[List[int]] = None
    access_hours: Optional[Dict[str, str]] = None


class AdminConfigUpdate(BaseModel):
    payload_batch_size: int


@app.post("/api/admin/login")
def admin_login(data: AdminLoginRequest):
    if not validate_admin_credentials(data.username, data.password):
        raise HTTPException(status_code=401, detail="Usuário ou senha de administrador incorretos")
    token = create_admin_session(data.username)
    return {
        "status": "success",
        "token": token,
        "username": data.username.strip(),
    }


@app.post("/api/admin/logout")
def admin_logout(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    x_admin_token: Optional[str] = Header(None, alias="X-Admin-Token"),
):
    token = None
    if credentials and credentials.scheme.lower() == "bearer":
        token = credentials.credentials
    elif x_admin_token:
        token = x_admin_token

    if token:
        delete_admin_session(token)
    return {"status": "success"}


@app.get("/api/admin/me")
def admin_me(username: str = Depends(require_admin_auth)):
    return {"status": "authenticated", "username": username}


@app.get("/api/admin/users", dependencies=[Depends(require_admin_auth)])
def list_admin_users():
    return get_all_users()


@app.post("/api/admin/users", dependencies=[Depends(require_admin_auth)])
def save_admin_user(data: AdminUserCreate):
    existing = get_user_by_cpf(data.cpf)
    if not existing and not data.password:
        raise HTTPException(status_code=400, detail="Senha obrigatória para novo usuário")
    success = add_user(
        cpf=data.cpf,
        password=data.password,
        is_recurring=data.is_recurring,
        specific_date=data.specific_date,
        expiration_date=data.expiration_date,
        access_days=data.access_days,
        access_hours=data.access_hours,
    )
    if not success:
        raise HTTPException(status_code=500, detail="Erro ao salvar usuário no banco")
    return {"status": "success", "cpf": data.cpf}


class AdminUserExpirationUpdate(BaseModel):
    expiration_date: Optional[str] = None


@app.put("/api/admin/users/{cpf}/expiration", dependencies=[Depends(require_admin_auth)])
def update_expiration(cpf: int, data: AdminUserExpirationUpdate):
    updated_exp = update_user_expiration(cpf, data.expiration_date)
    return {"status": "success", "cpf": cpf, "expiration_date": updated_exp}


@app.delete("/api/admin/users/{cpf}", dependencies=[Depends(require_admin_auth)])
def delete_user(cpf: int):
    deleted = delete_user_by_cpf(cpf)
    if not deleted:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    return {"status": "success", "cpf": cpf}


@app.get("/api/admin/stats", dependencies=[Depends(require_admin_auth)])
def get_admin_stats():
    users = get_all_users()
    total = len(users)
    recurring = sum(1 for u in users if u.get("is_recurring"))
    batch_size = get_payload_batch_size()
    return {
        "total_users": total,
        "recurring_users": recurring,
        "payload_batch_size": batch_size,
    }


@app.get("/api/admin/config", dependencies=[Depends(require_admin_auth)])
def get_config():
    return get_system_config()


@app.post("/api/admin/config", dependencies=[Depends(require_admin_auth)])
def update_config(data: AdminConfigUpdate):
    if data.payload_batch_size < 1 or data.payload_batch_size > 100:
        raise HTTPException(status_code=400, detail="Batch size deve estar entre 1 e 100")
    ok = set_payload_batch_size(data.payload_batch_size)
    if not ok:
        raise HTTPException(status_code=500, detail="Erro ao atualizar configurações")
    return {"status": "success", "payload_batch_size": data.payload_batch_size}


class AdminPasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str


@app.post("/api/admin/change-password")
def change_admin_password(data: AdminPasswordChangeRequest, username: str = Depends(require_admin_auth)):
    if not validate_admin_credentials(username, data.current_password):
        raise HTTPException(status_code=400, detail="Senha atual incorreta")
    if not data.new_password or len(data.new_password.strip()) < 4:
        raise HTTPException(status_code=400, detail="A nova senha deve ter pelo menos 4 caracteres")
    ok = update_admin_password(username, data.new_password.strip())
    if not ok:
        raise HTTPException(status_code=500, detail="Erro ao alterar a senha do administrador")
    return {"status": "success"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host=config.IP_ADRESS, port=config.PORT, reload=True)