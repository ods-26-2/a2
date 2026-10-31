import sys
from pathlib import Path

# Garante que o diretório do backend esteja no path mesmo quando este módulo
# é importado de fora (ex.: pelo main.py da raiz e pelo reload do uvicorn)
backend_dir = Path(__file__).resolve().parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from contextlib import asynccontextmanager
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, field_validator, model_validator
from fastapi import FastAPI, HTTPException, Depends, Header, Request, Response, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, FileResponse, HTMLResponse
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
    delete_admin_sessions,
    update_admin_password,
    create_user_session,
    verify_user_session,
    delete_user_session,
    init_db,
    get_api_key,
    create_or_regenerate_api_key,
    set_api_key_active,
    validate_api_key,
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        init_db()
    except Exception:
        pass
    yield


app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)

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


def require_api_key(x_api_key: Optional[str] = Header(None, alias="X-API-Key")) -> str:
    if not x_api_key or not validate_api_key(x_api_key):
        raise HTTPException(status_code=401, detail="Chave de API inválida ou inativa")
    return x_api_key


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
    cpf: Optional[int] = None
    password: Optional[str] = None


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


@app.post("/api/user/login")
def user_login(data: UserAuthRequest, response: Response):
    if data.cpf is None or not data.password:
        raise HTTPException(status_code=400, detail="CPF e senha obrigatórios")
    ok, reason, user = validate_user_access(cpf=data.cpf, password=data.password)
    if not ok:
        raise HTTPException(status_code=401, detail=reason)
    token = create_user_session(data.cpf)
    response.set_cookie(
        key="sessionid",
        value=token,
        httponly=True,
        samesite="lax",
        path="/",
        max_age=24 * 3600,
    )
    return {"status": "success", "cpf": data.cpf}


@app.post("/api/user/logout")
def user_logout(request: Request, response: Response):
    token = request.cookies.get("sessionid")
    if token:
        delete_user_session(token)
    response.delete_cookie("sessionid", path="/")
    return {"status": "success"}


@app.get("/api/user/me")
def user_me(request: Request):
    token = request.cookies.get("sessionid")
    cpf = verify_user_session(token) if token else None
    if not cpf:
        raise HTTPException(status_code=401, detail="Sessão expirada ou inválida")
    return {"cpf": cpf}


@app.post("/get-payloads")
def get_payloads(
    request: Request,
    response: Response,
    data: Optional[UserAuthRequest] = None,
):
    cpf = None
    if data and data.cpf is not None and data.password:
        ok, reason, user = validate_user_access(cpf=data.cpf, password=data.password)
        if not ok:
            raise HTTPException(status_code=401, detail=reason)
        cpf = data.cpf
        token = create_user_session(cpf)
        response.set_cookie(
            key="sessionid",
            value=token,
            httponly=True,
            samesite="lax",
            path="/",
            max_age=24 * 3600,
        )
    else:
        token = request.cookies.get("sessionid")
        cpf = verify_user_session(token) if token else None
        if not cpf:
            raise HTTPException(status_code=401, detail="Sessão expirada ou inválida")
    batch_size = get_payload_batch_size()
    return payload.get_payloads(cpf=cpf, length=batch_size)


@app.post("/get-payload")
def get_payload(
    request: Request,
    response: Response,
    data: Optional[UserAuthRequest] = None,
):
    cpf = None
    if data and data.cpf is not None and data.password:
        ok, reason, user = validate_user_access(cpf=data.cpf, password=data.password)
        if not ok:
            raise HTTPException(status_code=401, detail=reason)
        cpf = data.cpf
        token = create_user_session(cpf)
        response.set_cookie(
            key="sessionid",
            value=token,
            httponly=True,
            samesite="lax",
            path="/",
            max_age=24 * 3600,
        )
    else:
        token = request.cookies.get("sessionid")
        cpf = verify_user_session(token) if token else None
        if not cpf:
            raise HTTPException(status_code=401, detail="Sessão expirada ou inválida")
    return payload.get_payloads(cpf=cpf, length=1)


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

    @field_validator("password")
    @classmethod
    def _validate_password(cls, v):
        if v is None:
            return v
        v = v.strip()
        if v == "":
            return None
        return v

    @field_validator("access_days")
    @classmethod
    def _validate_access_days(cls, v):
        if v is None:
            return v
        for d in v:
            if not isinstance(d, int) or d < 0 or d > 6:
                raise ValueError("access_days deve conter inteiros entre 0 e 6")
        return sorted(set(v))

    @field_validator("access_hours")
    @classmethod
    def _validate_access_hours(cls, v):
        if v is None:
            return v
        if not isinstance(v, dict):
            raise ValueError("access_hours deve ser um objeto")
        for k in ("start", "end"):
            if k not in v:
                raise ValueError("access_hours deve conter start e end")
            try:
                from datetime import time
                time.fromisoformat(v[k])
            except Exception:
                raise ValueError(f"Horário inválido em access_hours.{k}")
        return v

    @field_validator("specific_date", "expiration_date")
    @classmethod
    def _validate_date(cls, v):
        if v is None:
            return v
        v = str(v).strip()
        if v == "":
            return None
        try:
            from datetime import date
            date.fromisoformat(v[:10])
        except Exception:
            raise ValueError("Data inválida (use YYYY-MM-DD)")
        return v[:10]

    @model_validator(mode="after")
    def _validate_date_range(self):
        if not self.is_recurring:
            if not self.specific_date:
                raise ValueError("specific_date obrigatório para acesso fixo")
            if not self.expiration_date:
                raise ValueError("expiration_date obrigatório para acesso fixo")
        if self.specific_date and self.expiration_date:
            from datetime import date
            s = date.fromisoformat(self.specific_date[:10])
            e = date.fromisoformat(self.expiration_date[:10])
            if e < s:
                raise ValueError("expiration_date não pode ser anterior a specific_date")
        return self


class AdminConfigUpdate(BaseModel):
    payload_batch_size: int


class ApiKeyToggleRequest(BaseModel):
    active: bool

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
    delete_admin_sessions(username)
    return {"status": "success"}


# ==============================================================================
# API KEYS (admin management + external access)
# ==============================================================================

@app.get("/api/admin/api-key", dependencies=[Depends(require_admin_auth)])
def get_api_key_info():
    info = get_api_key()
    if not info:
        return {"key": None, "active": False, "created_at": None}
    return {
        "key": info["key"],
        "active": bool(info["active"]),
        "created_at": info["created_at"],
    }


@app.post("/api/admin/api-key/regenerate", dependencies=[Depends(require_admin_auth)])
def regenerate_api_key():
    key = create_or_regenerate_api_key()
    return {"key": key, "active": True}


@app.post("/api/admin/api-key/toggle")
def toggle_api_key(data: ApiKeyToggleRequest, username: str = Depends(require_admin_auth)):
    ok = set_api_key_active(data.active)
    if not ok:
        raise HTTPException(status_code=404, detail="Nenhuma chave de API encontrada")
    return {"active": data.active}


@app.post("/api/external/users", dependencies=[Depends(require_api_key)])
def external_save_user(data: AdminUserCreate):
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


@app.delete("/api/external/users/{cpf}", dependencies=[Depends(require_api_key)])
def external_delete_user(cpf: int):
    deleted = delete_user_by_cpf(cpf)
    if not deleted:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    return {"status": "success", "cpf": cpf}


@app.get("/admin/docs", include_in_schema=False)
def admin_docs_page(request: Request, token: Optional[str] = Query(None)):
    auth_token = token
    if not auth_token:
        auth = request.headers.get("authorization")
        if auth and auth.lower().startswith("bearer "):
            auth_token = auth[7:]
    if not auth_token:
        auth_token = request.headers.get("x-admin-token")
    if not auth_token or not verify_admin_session(auth_token):
        return RedirectResponse(url="/admin/")
    docs_file = Path(__file__).resolve().parent / "docs.html"
    return HTMLResponse(content=docs_file.read_text(encoding="utf-8"))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host=config.IP_ADRESS, port=config.PORT, reload=True)