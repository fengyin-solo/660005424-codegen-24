"""大屏数据权限模块。

授权模型
========
- 账号 -> 授权清单（grant 列表），每条 grant 为 {dimension: "source"|"level", value, action: "allow"|"deny"}
- 有效授权口径：同维度同对象若存在 deny 记录则该对象被拒绝；否则需存在 allow 记录才可见。
- 每次启用（保存并生效）生成一个不可变的「版本快照」(version)，快照内的日志数据由
  账号 + 版本号派生的随机种子生成，并按有效授权过滤。同一账号同一版本在任意窗口/时间
  请求，返回取值完全一致（多窗口口径一致）。
"""
import hashlib
import random
import time
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

# 反向复用主模块的日志模板/生成与统计分析能力（main 在末尾导入本模块）
from . import main as engine

router = APIRouter(prefix="/api/screen", tags=["screen"])

# 平台可被授权的全部数据对象
SOURCES = [
    "nginx", "api-gateway", "load-balancer",
    "httpd", "mod_ssl", "mod_rewrite",
    "user-service", "order-service", "payment-service", "auth-service",
    "cron", "systemd", "kernel", "docker",
]
# 各日志类型原始级别写法 -> 大屏统一级别口径
LEVEL_ALIASES = {
    "INFO": "INFO", "WARN": "WARN", "ERROR": "ERROR", "DEBUG": "DEBUG",
    "info": "INFO", "notice": "INFO",
    "warn": "WARN", "warning": "WARN",
    "error": "ERROR",
    "debug": "DEBUG",
}
LEVELS = ["INFO", "WARN", "ERROR", "DEBUG"]
DIMENSIONS = {"source", "level"}
ACTIONS = {"allow", "deny"}

SCREEN_LOG_TYPES = ["nginx", "apache", "json_app", "custom"]
SCREEN_LOG_COUNT_PER_TYPE = 250


# ---------------------------------------------------------------- models
class Grant(BaseModel):
    dimension: str
    value: str
    action: str


class AccountConfigIn(BaseModel):
    grants: List[Grant] = []
    enabled: bool = True


class ScreenDataIn(BaseModel):
    account: str
    # 显式请求的数据对象；只要其中任何一个不在该账号有效授权范围内即判越权拒绝。
    # 缺省（None）表示按账号有效授权口径正常取数。
    sources: Optional[List[str]] = None
    levels: Optional[List[str]] = None


# ---------------------------------------------------------------- storage
def _now():
    return time.strftime("%Y-%m-%d %H:%M:%S")


ACCOUNTS = {
    "admin": {
        "name": "平台管理员",
        "grants": [Grant(dimension="source", value=s, action="allow") for s in SOURCES]
                  + [Grant(dimension="level", value=l, action="allow") for l in LEVELS],
        "enabled": True,
        "version": 1,
        "updatedAt": "2026-09-22 09:00:00",
    },
    "viewer-a": {
        "name": "运维值班员A（来源全放行 / 仅 INFO+WARN）",
        "grants": [Grant(dimension="source", value=s, action="allow") for s in SOURCES]
                  + [
                      Grant(dimension="level", value="INFO", action="allow"),
                      Grant(dimension="level", value="WARN", action="allow"),
                      Grant(dimension="level", value="ERROR", action="deny"),
                      Grant(dimension="level", value="DEBUG", action="deny"),
                  ],
        "enabled": True,
        "version": 1,
        "updatedAt": "2026-09-22 09:00:00",
    },
    "viewer-b": {
        "name": "业务线负责人B（授权清单为空，待配置）",
        "grants": [],
        "enabled": False,
        "version": 0,
        "updatedAt": "2026-09-22 09:00:00",
    },
    "viewer-c": {
        "name": "审计账号C（仅内核与系统来源，全部级别）",
        "grants": [
            Grant(dimension="source", value="kernel", action="allow"),
            Grant(dimension="source", value="systemd", action="allow"),
        ],
        "enabled": False,
        "version": 0,
        "updatedAt": "2026-09-22 09:00:00",
    },
}

# (account, version) -> 已过滤数据集，保证同一版本多次/多窗口请求逐值一致
_DATA_CACHE: dict = {}


# ---------------------------------------------------------------- helpers
def validate_grants(grants: List[Grant]):
    """返回 (errors, effective)。errors 为不合格项说明；effective 为有效授权口径。"""
    errors: List[str] = []
    if not grants:
        errors.append("授权清单为空：至少需要一条 source 放行规则和一条 level 放行规则")

    seen_pairs = {}
    for i, g in enumerate(grants):
        where = f"第{i + 1}条(dimension={g.dimension!r}, value={g.value!r}, action={g.action!r})"
        if g.dimension not in DIMENSIONS:
            errors.append(f"{where}：dimension 非法，只允许 source / level")
            continue
        if g.action not in ACTIONS:
            errors.append(f"{where}：action 非法，只允许 allow / deny")
        valid_values = SOURCES if g.dimension == "source" else LEVELS
        if g.value not in valid_values:
            errors.append(f"{where}：{g.dimension} 对象 {g.value!r} 不存在，可选值 {valid_values}")
            continue
        key = (g.dimension, g.value)
        if key in seen_pairs:
            errors.append(
                f"{where}：与第{seen_pairs[key] + 1}条重复授权同一对象 {g.value}；"
                f"若两条动作分别为 allow 与 deny 则构成互相冲突，请删除冗余/冲突项"
            )
        else:
            seen_pairs[key] = i

    # 有效口径：deny 优先，否则需有 allow
    effective = {"source": {"allow": set(), "deny": set()},
                 "level": {"allow": set(), "deny": set()}}
    for g in grants:
        if g.dimension in DIMENSIONS and g.action in ACTIONS:
            valid_values = SOURCES if g.dimension == "source" else LEVELS
            if g.value in valid_values:
                effective[g.dimension][g.action].add(g.value)

    for dim, label in (("source", "数据来源"), ("level", "日志级别")):
        allowed = effective[dim]["allow"] - effective[dim]["deny"]
        if not allowed:
            errors.append(f"授权生效后 {label} 维度没有任何放行对象（空授权或被 deny 全部驳回），大屏将无数据可展示")

    return errors, effective


def effective_scope(grants: List[Grant]):
    _, eff = validate_grants(grants)
    return {
        "sources": sorted(eff["source"]["allow"] - eff["source"]["deny"]),
        "levels": sorted(eff["level"]["allow"] - eff["level"]["deny"]),
    }


def get_account(account: str):
    acc = ACCOUNTS.get(account)
    if acc is None:
        raise HTTPException(status_code=403, detail={
            "code": "unknown_account",
            "message": f"账号 {account!r} 不存在或未开通大屏访问权限，请求已拒绝",
            "denied": [],
        })
    return acc


def _seed_for(account: str, version: int) -> int:
    # 稳定哈希：同一 (账号, 版本) 在任意进程/任意时间生成相同数据
    digest = hashlib.sha256(f"screen|{account}|v{version}".encode("utf-8")).digest()
    return int.from_bytes(digest[:4], "big")


def build_version_data(account: str, acc: dict):
    """按 (账号, 版本) 固定种子生成数据并依授权口径过滤；同一版本结果可复现。"""
    version = acc["version"]
    cache_key = (account, version)
    cached = _DATA_CACHE.get(cache_key)
    if cached is not None:
        return cached

    rng = random.Random(_seed_for(account, version))
    raw = []
    for lt in SCREEN_LOG_TYPES:
        raw.extend(engine.build_log_entries(lt, SCREEN_LOG_COUNT_PER_TYPE, rng))

    scope = effective_scope(acc["grants"])
    allowed_sources, allowed_levels = set(scope["sources"]), set(scope["levels"])

    logs = []
    for e in raw:
        canon_level = LEVEL_ALIASES.get(e["level"], e["level"].upper())
        if e["source"] in allowed_sources and canon_level in allowed_levels:
            item = dict(e)
            item["level"] = canon_level  # 大屏统一级别口径
            logs.append(item)
    # 重新连续编号，避免暴露被过滤掉的行
    for new_id, item in enumerate(logs, start=1):
        item["id"] = new_id

    analyzed = engine.analyze_logs([dict(x) for x in logs], [], "", now_str=f"v{version}T00:00:00")
    source_counts = {s: 0 for s in scope["sources"]}
    level_counts = {l: 0 for l in scope["levels"]}
    for item in logs:
        source_counts[item["source"]] = source_counts.get(item["source"], 0) + 1
        level_counts[item["level"]] = level_counts.get(item["level"], 0) + 1

    payload = {
        "account": account,
        "version": version,
        "generatedAt": acc["updatedAt"],
        "scope": scope,
        "totalLogs": analyzed["totalLogs"],
        "sourceCounts": source_counts,
        "levelCounts": level_counts,
        "windows": analyzed["windows"],
        "anomalies": analyzed["anomalies"],
        "alerts": analyzed["alerts"],
        "logs": analyzed["logs"],
    }
    _DATA_CACHE[cache_key] = payload
    return payload


# ---------------------------------------------------------------- endpoints
@router.get("/accounts")
def list_accounts():
    """大屏账号清单及各自的授权/启用状态（账号选择器与状态徽标使用）。"""
    return {
        "accounts": [
            {
                "account": a,
                "name": acc["name"],
                "enabled": acc["enabled"],
                "version": acc["version"],
                "updatedAt": acc["updatedAt"],
                "grants": [g.model_dump() for g in acc["grants"]],
                "effectiveScope": effective_scope(acc["grants"]) if acc["grants"] else {"sources": [], "levels": []},
            }
            for a, acc in ACCOUNTS.items()
        ]
    }


@router.get("/catalog")
def catalog():
    """平台可授权对象全集，供授权管理界面渲染清单。"""
    return {"sources": SOURCES, "levels": LEVELS}


@router.get("/config/{account}")
def get_config(account: str):
    acc = get_account(account)
    return {
        "account": account,
        "name": acc["name"],
        "enabled": acc["enabled"],
        "version": acc["version"],
        "updatedAt": acc["updatedAt"],
        "grants": [g.model_dump() for g in acc["grants"]],
        "effectiveScope": effective_scope(acc["grants"]) if acc["grants"] else {"sources": [], "levels": []},
    }


@router.post("/config/{account}")
def save_config(account: str, req: AccountConfigIn):
    """保存授权清单并按 enabled 决定是否启用大屏。

    启用前强制校验授权清单；清单为空/含冲突或未知项时整单拒绝，保持原状态不变，
    并逐条返回不合格项与原因。
    """
    acc = get_account(account)
    grants = list(req.grants)

    if req.enabled:
        errors, _ = validate_grants(grants)
        if errors:
            raise HTTPException(status_code=400, detail={
                "code": "invalid_grants",
                "message": "授权清单校验未通过，大屏未启用，原有授权与启用状态保持不变",
                "errors": errors,
            })

    acc["grants"] = grants
    if req.enabled:
        acc["enabled"] = True
        acc["version"] += 1
        if acc["version"] <= 0:
            acc["version"] = 1
        acc["updatedAt"] = _now()
        _DATA_CACHE.pop((account, acc["version"]), None)
        return {
            "ok": True,
            "enabled": True,
            "version": acc["version"],
            "updatedAt": acc["updatedAt"],
            "effectiveScope": effective_scope(grants),
            "message": f"授权已生效，大屏口径版本 v{acc['version']}",
        }

    # 保存但不启用：允许先存草稿；版本冻结，仍在启用时再校验
    acc["enabled"] = False
    return {
        "ok": True,
        "enabled": False,
        "version": acc["version"],
        "updatedAt": acc["updatedAt"],
        "effectiveScope": effective_scope(grants) if grants else {"sources": [], "levels": []},
        "message": "授权清单已保存，但大屏处于停用状态；清单合格后重新启用方可访问",
    }


@router.post("/disable/{account}")
def disable_screen(account: str):
    acc = get_account(account)
    if not acc["enabled"]:
        raise HTTPException(status_code=400, detail={
            "code": "not_enabled",
            "message": f"账号 {account} 的大屏当前本就处于停用状态",
            "errors": [],
        })
    acc["enabled"] = False
    return {"ok": True, "enabled": False, "version": acc["version"],
            "message": f"账号 {account} 的大屏已停用，版本 v{acc['version']} 口径冻结"}


@router.post("/data")
def screen_data(req: ScreenDataIn):
    """大屏取数：默认按有效授权口径返回；显式索要未授权对象即判越权并写明原因。"""
    acc = get_account(req.account)
    if not acc["enabled"]:
        raise HTTPException(status_code=403, detail={
            "code": "screen_disabled",
            "message": (f"账号 {req.account!r} 的大屏未启用（授权清单为空或未通过启用校验），"
                        f"请管理员配置合格授权后再访问"),
            "denied": [],
        })

    scope = effective_scope(acc["grants"])
    allowed_sources, allowed_levels = set(scope["sources"]), set(scope["levels"])

    denied = []
    if req.sources is not None:
        for s in req.sources:
            if s not in allowed_sources:
                denied.append({"dimension": "source", "value": s})
    if req.levels is not None:
        for lv in req.levels:
            canon = LEVEL_ALIASES.get(lv, lv.upper())
            if canon not in allowed_levels:
                denied.append({"dimension": "level", "value": lv})
    if denied:
        raise HTTPException(status_code=403, detail={
            "code": "out_of_scope",
            "message": (f"越权请求被拒绝：账号 {req.account!r}（口径版本 v{acc['version']}）"
                        f"对以下 {len(denied)} 个数据对象没有访问授权，服务端未执行任何取数"),
            "denied": denied,
            "version": acc["version"],
        })

    return build_version_data(req.account, acc)
