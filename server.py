"""Emergency Blood Release — local/API server with working login."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parent
DATA_DIR = Path(os.environ.get("BLOOD_DATA_DIR", ROOT / "data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)

USERS_FILE = DATA_DIR / "users.json"
SESSIONS_FILE = DATA_DIR / "sessions.json"
HISTORY_FILE = DATA_DIR / "history.json"
AUDIT_FILE = DATA_DIR / "audit.json"

DEFAULT_ADMIN_USER = os.environ.get("BLOOD_ADMIN_USER", "admin")
DEFAULT_ADMIN_PASS = os.environ.get("BLOOD_ADMIN_PASSWORD", "admin123")
# Signed tokens work across serverless instances (no shared session file required).
TOKEN_SECRET = os.environ.get("BLOOD_TOKEN_SECRET") or os.environ.get(
    "SECRET_KEY", "blood-release-dev-secret-change-me"
)
TOKEN_TTL_SEC = int(os.environ.get("BLOOD_TOKEN_TTL_SEC", str(60 * 60 * 24 * 30)))
PBKDF2_ITERS = int(os.environ.get("BLOOD_PBKDF2_ITERS", "60000"))

_lock = threading.Lock()

app = FastAPI(title="Emergency Blood Release", version="0.1.0")


class LoginRequest(BaseModel):
    username: str
    password: str


class UserCreateRequest(BaseModel):
    username: str
    password: str
    role: str = "user"


class PasswordChangeRequest(BaseModel):
    username: str
    password: str


class BulkRequest(BaseModel):
    records: list[dict[str, Any]] = Field(default_factory=list)


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(data: str) -> bytes:
    pad = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode((data + pad).encode("ascii"))


def _hash_password(password: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(8)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), PBKDF2_ITERS
    ).hex()
    return f"{salt}${digest}"


def _verify_password(password: str, stored: str) -> bool:
    try:
        salt, digest = stored.split("$", 1)
    except ValueError:
        return False
    # Accept both current and legacy iteration counts so old hashes still work.
    for iters in {PBKDF2_ITERS, 120_000, 60_000}:
        check = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt.encode("utf-8"), iters
        ).hex()
        if hmac.compare_digest(check, digest):
            return True
    return False


def _issue_token(user: dict[str, Any]) -> str:
    payload = {
        "u": user.get("username"),
        "r": user.get("role", "user"),
        "c": user.get("created_at", "—"),
        "exp": int(time.time()) + TOKEN_TTL_SEC,
        "iat": int(time.time()),
    }
    body = _b64url(json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))
    sig = _b64url(hmac.new(TOKEN_SECRET.encode("utf-8"), body.encode("ascii"), hashlib.sha256).digest())
    return f"v1.{body}.{sig}"


def _verify_token(token: str) -> dict[str, Any] | None:
    try:
        kind, body, sig = token.split(".", 2)
        if kind != "v1":
            return None
        expected = _b64url(
            hmac.new(TOKEN_SECRET.encode("utf-8"), body.encode("ascii"), hashlib.sha256).digest()
        )
        if not hmac.compare_digest(sig, expected):
            return None
        payload = json.loads(_b64url_decode(body).decode("utf-8"))
        if int(payload.get("exp", 0)) < int(time.time()):
            return None
        username = str(payload.get("u") or "").strip()
        if not username:
            return None
        return {
            "username": username,
            "role": payload.get("r", "user"),
            "created_at": payload.get("c", "—"),
        }
    except Exception:
        return None


def _read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _write_json(path: Path, data: Any) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


def _public_user(u: dict[str, Any]) -> dict[str, Any]:
    return {
        "username": u.get("username"),
        "role": u.get("role", "user"),
        "created_at": u.get("created_at", "—"),
    }


def ensure_seed_admin() -> None:
    with _lock:
        users = _read_json(USERS_FILE, [])
        if not isinstance(users, list):
            users = []
        if users:
            return
        users.append(
            {
                "username": DEFAULT_ADMIN_USER,
                "password_hash": _hash_password(DEFAULT_ADMIN_PASS),
                "role": "admin",
                "created_at": _now_iso(),
            }
        )
        _write_json(USERS_FILE, users)
        if not SESSIONS_FILE.exists():
            _write_json(SESSIONS_FILE, {})
        if not HISTORY_FILE.exists():
            _write_json(HISTORY_FILE, [])
        if not AUDIT_FILE.exists():
            _write_json(AUDIT_FILE, [])


ensure_seed_admin()


def _get_users() -> list[dict[str, Any]]:
    users = _read_json(USERS_FILE, [])
    return users if isinstance(users, list) else []


def _save_users(users: list[dict[str, Any]]) -> None:
    _write_json(USERS_FILE, users)


def _get_sessions() -> dict[str, Any]:
    sessions = _read_json(SESSIONS_FILE, {})
    return sessions if isinstance(sessions, dict) else {}


def _save_sessions(sessions: dict[str, Any]) -> None:
    _write_json(SESSIONS_FILE, sessions)


def current_user(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Please log in")
    token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise HTTPException(status_code=401, detail="Please log in")

    # Preferred path: signed token (works on multi-instance / serverless hosts).
    verified = _verify_token(token)
    if verified:
        with _lock:
            users = _get_users()
            user = next((u for u in users if u.get("username") == verified["username"]), None)
            if user:
                return _public_user(user)
        # Fresh instance may have an empty users file; reseed then re-check.
        ensure_seed_admin()
        with _lock:
            users = _get_users()
            user = next((u for u in users if u.get("username") == verified["username"]), None)
            if user:
                return _public_user(user)
        return verified

    # Legacy fallback: opaque server-side sessions.
    with _lock:
        sessions = _get_sessions()
        sess = sessions.get(token)
        if not sess:
            raise HTTPException(status_code=401, detail="Please log in")
        username = sess.get("username")
        users = _get_users()
        user = next((u for u in users if u.get("username") == username), None)
        if not user:
            raise HTTPException(status_code=401, detail="Please log in")
        return _public_user(user)


def require_admin(user: dict[str, Any] = Depends(current_user)) -> dict[str, Any]:
    role = str(user.get("role") or "").lower()
    if role not in {"admin", "superuser", "super_admin"}:
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


def _merge_records(existing: list[dict[str, Any]], incoming: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    def key(r: dict[str, Any]) -> str:
        return "|".join(
            str(r.get(k, ""))
            for k in ("time", "action", "unit", "file", "patient", "name", "tech")
        )

    seen = set()
    out: list[dict[str, Any]] = []
    for r in list(incoming) + list(existing):
        if not isinstance(r, dict):
            continue
        k = key(r)
        if k in seen:
            continue
        seen.add(k)
        out.append(r)
    return out[:limit]


@app.get("/api/health")
@app.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "Emergency Blood Release",
        "storage": "local",
    }


@app.post("/api/login")
@app.post("/login")
def login(body: LoginRequest) -> dict[str, Any]:
    ensure_seed_admin()
    username = body.username.strip()
    password = body.password
    if not username or not password:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    with _lock:
        users = _get_users()
        user = next(
            (u for u in users if str(u.get("username", "")).lower() == username.lower()),
            None,
        )
        if not user or not _verify_password(password, user.get("password_hash", "")):
            raise HTTPException(status_code=401, detail="Invalid username or password")
        public = _public_user(user)
        token = _issue_token(user)
        return {"session_token": token, "user": public}


@app.get("/api/me")
@app.get("/me")
def me(user: dict[str, Any] = Depends(current_user)) -> dict[str, Any]:
    return {"user": user}


@app.get("/api/users")
@app.get("/users")
def list_users(_: dict[str, Any] = Depends(require_admin)) -> dict[str, Any]:
    with _lock:
        return {"users": [_public_user(u) for u in _get_users()]}


@app.post("/api/users")
@app.post("/users")
def create_user(
    body: UserCreateRequest, _: dict[str, Any] = Depends(require_admin)
) -> dict[str, Any]:
    username = body.username.strip()
    password = body.password
    role = (body.role or "user").strip() or "user"
    if not username:
        raise HTTPException(status_code=400, detail="Username is required")
    if len(password) < 4:
        raise HTTPException(status_code=400, detail="Password must be at least 4 characters")
    with _lock:
        users = _get_users()
        if any(str(u.get("username", "")).lower() == username.lower() for u in users):
            raise HTTPException(status_code=400, detail="Username already exists")
        users.append(
            {
                "username": username,
                "password_hash": _hash_password(password),
                "role": role,
                "created_at": _now_iso(),
            }
        )
        _save_users(users)
        return {"users": [_public_user(u) for u in users]}


@app.post("/api/users/password")
@app.post("/users/password")
def change_password(
    body: PasswordChangeRequest, admin: dict[str, Any] = Depends(current_user)
) -> dict[str, str]:
    username = body.username.strip()
    password = body.password
    if len(password) < 4:
        raise HTTPException(status_code=400, detail="Password must be at least 4 characters")
    role = str(admin.get("role") or "").lower()
    is_admin = role in {"admin", "superuser", "super_admin"}
    if not is_admin and admin.get("username") != username:
        raise HTTPException(status_code=403, detail="Admin access required")
    with _lock:
        users = _get_users()
        target = next((u for u in users if u.get("username") == username), None)
        if not target:
            raise HTTPException(status_code=404, detail="User not found")
        target["password_hash"] = _hash_password(password)
        _save_users(users)
        return {"status": "ok"}


@app.get("/api/history")
@app.get("/history")
def get_history(_: dict[str, Any] = Depends(current_user)) -> dict[str, Any]:
    with _lock:
        records = _read_json(HISTORY_FILE, [])
        if not isinstance(records, list):
            records = []
        return {"records": records}


@app.post("/api/history")
@app.post("/history")
def add_history(
    body: BulkRequest, _: dict[str, Any] = Depends(current_user)
) -> dict[str, Any]:
    with _lock:
        existing = _read_json(HISTORY_FILE, [])
        if not isinstance(existing, list):
            existing = []
        merged = _merge_records(existing, body.records or [], 500)
        _write_json(HISTORY_FILE, merged)
        return {"records": merged}


@app.get("/api/audit")
@app.get("/audit")
def get_audit(_: dict[str, Any] = Depends(current_user)) -> dict[str, Any]:
    with _lock:
        records = _read_json(AUDIT_FILE, [])
        if not isinstance(records, list):
            records = []
        return {"records": records}


@app.post("/api/audit")
@app.post("/audit")
def add_audit(
    body: BulkRequest, _: dict[str, Any] = Depends(current_user)
) -> dict[str, Any]:
    with _lock:
        existing = _read_json(AUDIT_FILE, [])
        if not isinstance(existing, list):
            existing = []
        merged = _merge_records(existing, body.records or [], 1000)
        _write_json(AUDIT_FILE, merged)
        return {"records": merged}


@app.get("/")
def home() -> FileResponse:
    return FileResponse(ROOT / "index.html")


@app.get("/{path:path}")
def spa(path: str) -> FileResponse:
    # Prefer real static files; otherwise fall back to the app shell.
    candidate = ROOT / path
    if candidate.is_file() and ROOT in candidate.resolve().parents:
        return FileResponse(candidate)
    return FileResponse(ROOT / "index.html")


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", "43147"))
    uvicorn.run("server:app", host="127.0.0.1", port=port, reload=False)
