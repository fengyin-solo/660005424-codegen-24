"""登录、当前账号信息与（管理员）授权清单管理接口。"""
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from . import auth as auth_mod
from .auth import ACCOUNTS, PermissionError
from .datagen import ALL_SOURCES, PANELS

router = APIRouter(prefix="/api", tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


class ScopeRequest(BaseModel):
    entries: list = []
    enabled: bool = True
    expectVersion: int | None = None  # 乐观锁：避免覆盖别人刚发布的清单


def _account(authorization: str | None, *, admin: bool = False):
    token = authorization.removeprefix("Bearer ").strip() if authorization else None
    account = auth_mod.store.resolve(token)
    if not account:
        raise HTTPException(status_code=401, detail="未登录或登录已失效，请重新登录")
    if admin and account["role"] != "admin":
        raise HTTPException(status_code=403,
                            detail=f"越权请求被拒绝：仅管理员可管理数据授权，账号 {account['username']} 无此权限")
    return account


@router.post("/login")
def login(req: LoginRequest):
    token = auth_mod.store.login(req.username, req.password)
    if not token:
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    return {"token": token, "username": req.username, "name": ACCOUNTS[req.username]["name"],
            "role": ACCOUNTS[req.username]["role"]}


@router.post("/logout")
def logout(authorization: str | None = Header(default=None)):
    if authorization:
        auth_mod.store.drop_token(authorization.removeprefix("Bearer ").strip())
    return {"ok": True}


@router.get("/me")
def me(authorization: str | None = Header(default=None)):
    account = _account(authorization)
    scope = auth_mod.store.get_scope(account["username"])
    return {"username": account["username"], "name": account["name"], "role": account["role"],
            "isAdmin": account["role"] == "admin",
            "scope": scope,
            "resourceCatalog": {"sources": ALL_SOURCES, "panels": PANELS}}


@router.get("/scopes")
def list_scopes(authorization: str | None = Header(default=None)):
    _account(authorization, admin=True)
    return {"accounts": [u for u in ACCOUNTS if u != "admin"],
            "scopes": auth_mod.store.list_scopes(),
            "resourceCatalog": {"sources": ALL_SOURCES, "panels": PANELS}}


@router.put("/scopes/{username}")
def update_scope(username: str, req: ScopeRequest, authorization: str | None = Header(default=None)):
    """发布（启用）授权清单。校验不过 -> 422 并逐项说明，旧版本保留。"""
    _account(authorization, admin=True)
    try:
        if req.enabled:
            scope, grants = auth_mod.store.publish(
                username, req.entries, expect_version=req.expectVersion)
            message = f"授权清单已启用并发布为 v{scope['version']}"
        else:
            scope, grants = auth_mod.store.set_enabled(username, False)
            message = f"账号 {username} 的大屏权限已停用"
    except PermissionError as exc:
        # 启用失败：保留原版本，HTTP 422 + 可读原因
        old = auth_mod.store.get_scope(username)
        raise HTTPException(status_code=422, detail={
            "reason": "启用失败：授权清单存在不合格项，未产生新版本，线上仍保持原授权口径",
            "errors": str(exc).split("\n"),
            "currentVersion": old["version"] if old else None,
        })
    return {"ok": True, "message": message, "scope": scope,
            "grants": {"sources": sorted(grants["sources"]), "panels": sorted(grants["panels"])}}
