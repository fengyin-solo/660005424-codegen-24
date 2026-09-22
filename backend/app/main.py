from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .admin import router as admin_router
from .datagen import generate_logs
from .pipeline import analyze_logs
from .screen import router as screen_router

app = FastAPI(title="Log Anomaly Detector")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
app.include_router(admin_router)
app.include_router(screen_router)


class GenerateRequest(BaseModel):
    type: str = "nginx"
    count: int = 1000


class DetectRequest(BaseModel):
    logs: list
    rules: list = []
    query: str = ""


@app.post("/api/generate")
def generate(req: GenerateRequest):
    # 普通模式保持原有行为：非确定性随机数据，不走数据权限
    logs = generate_logs(req.type, req.count, seed=None)
    return analyze_logs(logs, [], "")


@app.post("/api/detect")
def detect(req: DetectRequest):
    return analyze_logs(req.logs, req.rules, req.query)
