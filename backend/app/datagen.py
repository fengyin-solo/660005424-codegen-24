"""确定性的模拟日志生成。

同一份种子（账号 + 授权版本 + 日志类型）产出完全一致的数据，
这是"同一账号在多个窗口打开大屏时取值口径必须一致"的基础：
服务端只按已发布版本生成数据，窗口之间不依赖各自的随机数。
"""
import random
import time

LOG_TEMPLATES = {
    "nginx": {
        "generator": lambda r: {
            "timestamp": f"{r.randint(1,28):02d}/{'Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec'.split()[r.randint(0,11)]}/2024:{r.randint(0,23):02d}:{r.randint(0,59):02d}:{r.randint(0,59):02d} +0000",
            "source": r.choice(["nginx", "api-gateway", "load-balancer"]),
            "level": r.choices(["INFO", "WARN", "ERROR", "DEBUG"], weights=[50, 15, 5, 30])[0],
            "message": r.choice([
                'GET /api/users 200 0.032s', 'POST /api/orders 201 0.145s', 'GET /api/products 304 0.008s',
                'GET /static/main.js 200 0.002s', 'POST /api/login 401 0.023s', 'GET /admin 403 0.005s',
                'GET /api/health 200 0.001s', 'GET /api/orders?page=2 200 0.056s', 'connection timeout upstream',
                'SSL handshake failed', 'worker process exited on signal 9', 'upstream server unavailable'
            ])
        }
    },
    "apache": {
        "generator": lambda r: {
            "timestamp": f"{'Sun Mon Tue Wed Thu Fri Sat'.split()[r.randint(0,6)]} {'Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec'.split()[r.randint(0,11)]} {r.randint(1,28):02d} {r.randint(0,23):02d}:{r.randint(0,59):02d}:{r.randint(0,59):02d} 2024",
            "source": r.choice(["httpd", "mod_ssl", "mod_rewrite"]),
            "level": r.choices(["notice", "warn", "error", "info"], weights=[40, 15, 5, 40])[0],
            "message": r.choice(["server configured", "caught SIGTERM", "resuming normal ops", "request exceeded limit",
                        "file does not exist", "client denied by server", "Invalid method in request"])
        }
    },
    "json_app": {
        "generator": lambda r: {
            "timestamp": f"2024-{r.randint(1,12):02d}-{r.randint(1,28):02d}T{r.randint(0,23):02d}:{r.randint(0,59):02d}:{r.randint(0,59):02d}.{r.randint(0,999):03d}Z",
            "source": r.choice(["user-service", "order-service", "payment-service", "auth-service"]),
            "level": r.choices(["INFO", "WARN", "ERROR", "DEBUG"], weights=[45, 20, 5, 30])[0],
            "message": r.choice([
                'User login successful user_id=10' + str(r.randint(100, 999)),
                'Order created order_id=ORD-' + str(r.randint(10000, 99999)),
                'Payment processed amount=' + str(r.randint(10, 999)),
                'Database connection pool exhausted',
                'Cache miss for key user_session_' + str(r.randint(100, 999)),
                'Circuit breaker opened for service payment',
                'Request latency exceeds threshold 5000ms',
                'NullPointerException at com.app.controller.UserController.getProfile'
            ])
        }
    },
    "custom": {
        "generator": lambda r: {
            "timestamp": str(int(time.time()) - r.randint(0, 86400)),
            "source": r.choice(["cron", "systemd", "kernel", "docker"]),
            "level": r.choices(["info", "warning", "error", "debug"], weights=[40, 20, 5, 35])[0],
            "message": r.choice(["OOM killer invoked", "disk usage above 90%", "container restarted", "NTP sync lost",
                        "process oom_score_adj=500", "firewall rule updated", "mount point not found"])
        }
    }
}

# 大屏可授权的全部资源
ALL_SOURCES = [
    "nginx", "api-gateway", "load-balancer",
    "httpd", "mod_ssl", "mod_rewrite",
    "user-service", "order-service", "payment-service", "auth-service",
    "cron", "systemd", "kernel", "docker",
]
PANELS = ["kpi", "trend", "heatmap", "anomaly", "alerts", "logs"]
VALID_RESOURCES = set(ALL_SOURCES) | set(PANELS)

# 面板展示标题（普通模式与大屏模式共用，保证"切回普通模式后标题与图例保持一致"）
PANEL_TITLES = {
    "kpi": "📊 总日志量",
    "trend": "📉 窗口日志量趋势",
    "heatmap": "🔥 日志级别热力图",
    "anomaly": "📈 异常分数 (3-sigma + IQR)",
    "alerts": "🚨 告警列表",
    "logs": "📋 日志流",
}


def generate_logs(log_type: str, count: int = 1000, seed: str | None = None):
    """生成模拟日志。seed 为 None 时走非确定性随机（普通模式行为不变）。"""
    tmpl = LOG_TEMPLATES.get(log_type, LOG_TEMPLATES["nginx"])
    r = random.Random() if seed is None else random.Random(f"screen|{seed}|{log_type}|{count}")
    logs = []
    for i in range(count):
        entry = tmpl["generator"](r)
        logs.append({
            "id": i + 1,
            "timestamp": entry["timestamp"],
            "level": entry["level"],
            "source": entry["source"],
            "message": entry["message"],
            "raw": f"[{entry['timestamp']}] [{entry['level']}] [{entry['source']}] {entry['message']}"
        })
    return logs
