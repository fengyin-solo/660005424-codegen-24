"""账号、登录令牌与数据权限（授权清单）管理。

授权清单的资源粒度：
- 数据源：nginx / api-gateway / ... / docker（共 14 个，见 datagen.ALL_SOURCES）
- 面板：kpi / trend / heatmap / anomaly / alerts / logs

授权条目 {"resource": str, "effect": "allow"|"deny"}，deny 用于在一组
授权里显式剔除某个资源。权限口径：先取全部 allow，再剔除 deny。

启用（发布）前必须通过校验，任一条目不合格都会整体拒绝启用，不会产生
半成品版本：
1. 清单为空 —— 大屏至少要授权一个数据源和一个面板，否则全是占位；
2. 出现未知资源、拼写错误；
3. 同一资源出现完全重复的条目；
4. 同一资源同时 allow 和 deny —— 互相冲突，无法判断口径；
5. 只有 deny 没有 allow（口径为空）；
6. 授权了面板，但一个对应的数据来源都没授权（面板必然无数据）；
7. 通配符 source:* / panel:* 与同类具体资源混用（口径冗余冲突）。

发布后版本号 +1，大屏请求必须携带版本号；版本不是当前版本会被拒绝
（409），由前端拉到新版本后重开，保证同一账号多个窗口取值口径一致。
"""
import threading
import uuid

from .datagen import ALL_SOURCES, PANELS, VALID_RESOURCES

SOURCE_WILDCARD = "source:*"
PANEL_WILDCARD = "panel:*"
VALID_EFFECTS = ("allow", "deny")

# 演示用内置账号（无独立用户库，密码仅用于本地演示）
ACCOUNTS = {
    "admin": {"password": "admin123", "name": "平台管理员", "role": "admin"},
    "sre":   {"password": "sre123",   "name": "SRE 值班工程师", "role": "viewer"},
    "guest": {"password": "guest123", "name": "访客账号", "role": "viewer"},
}

# 初始即已发布、可直接演示的授权清单
DEFAULT_SCOPES = {
    "sre": {
        "version": 1,
        "enabled": True,
        "entries": [{"resource": SOURCE_WILDCARD, "effect": "allow"},
                    {"resource": "panel:*", "effect": "allow"}],
    },
    "guest": {
        "version": 1,
        "enabled": True,
        "entries": [
            {"resource": "nginx", "effect": "allow"},
            {"resource": "api-gateway", "effect": "allow"},
            {"resource": "kpi", "effect": "allow"},
            {"resource": "trend", "effect": "allow"},
            {"resource": "heatmap", "effect": "allow"},
            {"resource": "anomaly", "effect": "allow"},
            {"resource": "alerts", "effect": "allow"},
            # logs 面板未授权 —— 大屏上以占位说明呈现
        ],
    },
}


class PermissionError(Exception):
    """清单校验失败，message 面向用户展示。"""


class ScopeStore:
    def __init__(self):
        self._lock = threading.RLock()
        self._scopes = {u: self._clone(scope) for u, scope in DEFAULT_SCOPES.items()}
        self._tokens: dict[str, str] = {}  # token -> username

    @staticmethod
    def _clone(scope):
        return {"version": scope["version"], "enabled": scope["enabled"],
                "entries": [dict(e) for e in scope["entries"]]}

    # ---- 登录 / 身份 ----
    def login(self, username: str, password: str):
        acc = ACCOUNTS.get(username)
        if not acc or acc["password"] != password:
            return None
        token = uuid.uuid4().hex
        with self._lock:
            self._tokens[token] = username
        return token

    def resolve(self, token: str | None):
        if not token:
            return None
        with self._lock:
            username = self._tokens.get(token)
        if not username or username not in ACCOUNTS:
            return None
        return {"username": username, **ACCOUNTS[username]}

    def drop_token(self, token: str):
        with self._lock:
            self._tokens.pop(token, None)

    # ---- 授权清单读取 ----
    def get_scope(self, username: str):
        with self._lock:
            scope = self._scopes.get(username)
            return self._clone(scope) if scope else None

    def list_scopes(self):
        with self._lock:
            return {u: self._clone(s) for u, s in self._scopes.items()}

    def set_enabled(self, username: str, enabled: bool):
        with self._lock:
            scope = self._scopes.get(username)
            if not scope:
                raise PermissionError(f"账号 {username} 不存在，无法修改启用状态")
            if enabled:
                # 重新启用同样要过校验
                grants = self.validate(scope["entries"])
                scope["enabled"] = True
            else:
                grants = effective_grants(scope["entries"])
                scope["enabled"] = False
            return self._clone(scope), grants

    # ---- 校验与发布 ----
    @staticmethod
    def validate(entries) -> dict[str, set[str]]:
        """校验授权清单，不合格直接抛 PermissionError（列出全部不合格项）。"""
        problems: list[str] = []

        if not isinstance(entries, list) or len(entries) == 0:
            raise PermissionError("授权清单为空：大屏至少需要授权 1 个数据源与 1 个面板，"
                                  "请先补充授权项后再启用")

        # 1. 条目结构 / 未知资源 / 非法 effect
        normalized: list[tuple[str, str]] = []
        for idx, e in enumerate(entries):
            label = f"第 {idx + 1} 条"
            if not isinstance(e, dict):
                problems.append(f"{label}：不是合法的授权对象")
                continue
            res, effect = e.get("resource"), e.get("effect")
            if not isinstance(res, str) or not res:
                problems.append(f"{label}：缺少资源标识 resource")
                continue
            if effect not in VALID_EFFECTS:
                problems.append(f"{label}（{res}）：授权动作 effect 必须是 allow 或 deny，当前为 {effect!r}")
                continue
            known = VALID_RESOURCES | {SOURCE_WILDCARD, PANEL_WILDCARD}
            if res not in known:
                problems.append(f"{label}：资源 {res!r} 不存在（可选数据源 {len(ALL_SOURCES)} 个、面板 {len(PANELS)} 个）")
                continue
            normalized.append((res, effect))

        # 2. 完全重复
        seen: set[tuple[str, str]] = set()
        for res, effect in normalized:
            key = (res, effect)
            if key in seen:
                problems.append(f"资源 {res} 的 {effect} 授权重复出现，请合并为一条")
            seen.add(key)

        # 3. 同资源 allow / deny 冲突
        effects_by_res: dict[str, set[str]] = {}
        for res, effect in normalized:
            effects_by_res.setdefault(res, set()).add(effect)
        for res, fx in effects_by_res.items():
            if {"allow", "deny"} <= fx:
                problems.append(f"资源 {res} 同时被允许(allow)与拒绝(deny)，授权口径互相冲突，请二选一")

        grants = effective_grants(normalized)

        # 4. 口径为空（只有 deny / 全部被拒）
        if not grants["sources"]:
            problems.append("没有任何被允许(allow)的数据源，大屏将无数据可取，请至少允许 1 个数据源")
        if not grants["panels"]:
            problems.append("没有任何被允许(allow)的面板，大屏上将全是占位，请至少允许 1 个面板")

        # 5. 通配符与同类具体资源混用（口径冗余、易冲突）
        def wildcard_clash(star: str, concrete: list[str], kind: str):
            if star in effects_by_res:
                clash = [r for r in concrete if r in effects_by_res]
                if clash:
                    problems.append(f"已授权通配符 {star}，又单独列出 {kind} {', '.join(sorted(clash))}，"
                                    f"授权口径冗余冲突：要全部授权请删除具体项，要收窄权限请移除通配符")

        wildcard_clash(SOURCE_WILDCARD, ALL_SOURCES, "数据源")
        wildcard_clash(PANEL_WILDCARD, PANELS, "面板")

        # 6. 面板被授权但没有任何数据源（面板必然取不到数据）
        if grants["panels"] and not grants["sources"]:
            problems.append("已授权面板 " + ", ".join(sorted(grants["panels"])) +
                            " 但未授权任何数据源，面板将无数据可展示")

        if problems:
            raise PermissionError("授权清单校验未通过，共 %d 项不合格：\n- %s"
                                  % (len(problems), "\n- ".join(problems)))
        return grants

    def publish(self, username: str, entries, *, expect_version: int | None = None):
        """校验通过才发布，版本号 +1；失败返回原因且保留旧版本。"""
        if username not in ACCOUNTS:
            raise PermissionError(f"账号 {username} 不存在")
        grants = self.validate(entries)
        with self._lock:
            old = self._scopes.get(username)
            if expect_version is not None and old and old["version"] != expect_version:
                raise PermissionError(f"授权清单已被其他人修改（当前版本 v{old['version']}，"
                                      f"你编辑的是 v{expect_version}），请刷新后重新编辑")
            version = (old["version"] + 1) if old else 1
            scope = {"version": version, "enabled": True,
                     "entries": [{"resource": r, "effect": e} for r, e in
                                 sorted(((e.get("resource"), e.get("effect")) for e in entries),
                                        key=lambda x: x[0])]}
            self._scopes[username] = scope
            return self._clone(scope), grants


def effective_grants(entries) -> dict[str, set[str]]:
    """条目列表 -> 实际生效的 {sources, panels}（先 allow 后 deny）。"""
    allowed_s, denied_s, allowed_p, denied_p = set(), set(), set(), set()
    for e in entries:
        res, effect = (e if isinstance(e, tuple) else (e.get("resource"), e.get("effect")))
        if res == SOURCE_WILDCARD:
            target_a, target_d = allowed_s, denied_s
            universe = ALL_SOURCES
        elif res == PANEL_WILDCARD:
            target_a, target_d = allowed_p, denied_p
            universe = PANELS
        elif res in ALL_SOURCES:
            target_a, target_d = allowed_s, denied_s
            universe = None
        elif res in PANELS:
            target_a, target_d = allowed_p, denied_p
            universe = None
        else:
            continue
        if effect == "allow":
            target_a.update(universe if universe else [res])
        elif effect == "deny":
            target_d.update(universe if universe else [res])
    return {"sources": allowed_s - denied_s, "panels": allowed_p - denied_p}


store = ScopeStore()
