"""大屏数据接口：按已发布的授权版本生成口径一致、越权拒绝的数据。"""
from fastapi import APIRouter, Header, HTTPException, Query
from pydantic import BaseModel

from . import auth as auth_mod
from .datagen import ALL_SOURCES, PANELS, PANEL_TITLES, generate_logs
from .pipeline import analyze_logs

router = APIRouter(prefix="/api/screen", tags=["screen"])


class ScreenRequest(BaseModel):
    type: str = "nginx"
    version: int | None = None


def _current_account(authorization: str | None):
    token = authorization.removeprefix("Bearer ").strip() if authorization else None
    account = auth_mod.store.resolve(token)
    if not account:
        raise HTTPException(status_code=401, detail="未登录或登录已失效，请重新登录后再打开大屏")
    return account


def _published_scope(account, version: int | None):
    """取已发布授权，处理：未启用 / 版本不一致 / 越权拿别人版本等情况。"""
    scope = auth_mod.store.get_scope(account["username"])
    if not scope or not scope.get("enabled"):
        raise HTTPException(
            status_code=403,
            detail=f"账号 {account['username']} 的大屏数据权限尚未启用：需要管理员配置并"
                   f"成功发布授权清单后才能查看大屏，启用失败时请先根据提示修正不合格授权项")
    if version is not None and version != scope["version"]:
        raise HTTPException(
            status_code=409,
            detail=f"授权口径已更新（当前为 v{scope['version']}，本窗口使用的是 v{version}）。"
                   f"为保证多个窗口取值一致，已拒绝旧口径请求，请刷新页面加载最新授权版本")
    grants = auth_mod.effective_grants(scope["entries"])
    return scope, grants


@router.post("/data")
def screen_data(req: ScreenRequest, authorization: str | None = Header(default=None)):
    account = _current_account(authorization)
    scope, grants = _published_scope(account, req.version)

    # 同账号 + 同授权版本 + 同日志类型 => 同一份种子 => 任意窗口取值完全一致
    seed = f"{account['username']}|v{scope['version']}"
    full_logs = generate_logs(req.type, 1000, seed=seed)
    scoped_logs = [l for l in full_logs if l["source"] in grants["sources"]]
    # 大屏按授权数据源过滤后再做窗口聚合与异常检测，统计告警（不传自定义规则）
    result = analyze_logs(scoped_logs, [], "")

    def payload(panel: str):
        if panel == "kpi":
            return {"value": result["totalLogs"],
                    "grantedSources": sorted(grants["sources"])}
        if panel == "trend":
            return {"windows": result["windows"]}
        if panel == "heatmap":
            return {"windows": result["windows"]}
        if panel == "anomaly":
            return {"anomalies": result["anomalies"]}
        if panel == "alerts":
            return {"alerts": result["alerts"]}
        if panel == "logs":
            return {"logs": result["logs"], "totalLogs": result["totalLogs"]}
        return {}

    panels = []
    for panel in PANELS:
        granted = panel in grants["panels"]
        panels.append({
            "panel": panel,
            "title": PANEL_TITLES[panel],
            "status": "granted" if granted else "denied",
            # 未授权：不给任何数值，只给占位说明（前端不渲染空图表/空值）
            "denyReason": None if granted else f"当前账号未被授权「{PANEL_TITLES[panel]}」面板，数据已隐藏",
            "data": payload(panel) if granted else None,
        })

    return {
        "account": {"username": account["username"], "name": account["name"], "role": account["role"]},
        "logType": req.type,
        "scope": {"version": scope["version"], "enabled": True},
        "sources": {
            "granted": sorted(grants["sources"]),
            "denied": sorted(set(ALL_SOURCES) - grants["sources"]),
        },
        "panels": panels,
    }


@router.get("/raw")
def screen_raw(source: str = Query(...), type: str = "nginx",
               version: int | None = None, authorization: str | None = Header(default=None)):
    """明细下钻：只能取本账号已授权数据源，越权请求直接拒绝并写明原因。"""
    account = _current_account(authorization)
    scope, grants = _published_scope(account, version)

    if source not in ALL_SOURCES:
        raise HTTPException(status_code=400, detail=f"数据源 {source!r} 不存在")
    if source not in grants["sources"]:
        raise HTTPException(
            status_code=403,
            detail=f"越权请求被拒绝：账号 {account['username']} 未获授权数据源 {source!r}"
                   f"（授权版本 v{scope['version']}），如需访问请联系管理员调整授权清单")

    seed = f"{account['username']}|v{scope['version']}"
    logs = [l for l in generate_logs(type, 1000, seed=seed) if l["source"] == source]
    return {"source": source, "version": scope["version"], "logs": logs[:200], "total": len(logs)}
