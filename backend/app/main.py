import asyncio
import json
import threading

import uvicorn
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .engine import build_run, compute_stats, execute_run

app = FastAPI(title="DAG Workflow Engine")
app.add_middleware(CORSMiddleware, allow_origins=["*"],
                   allow_methods=["*"], allow_headers=["*"])

ACTIVE_CLIENTS = []          # [WebSocket]
MAIN_LOOP = None             # 主事件循环，工作线程推送 WS 必须用它
WORKFLOWS = {}               # id -> workflow 定义
RUNS = {}                    # run_id -> run 快照
RUN_ORDER = []               # run_id 时间顺序
MAX_RUN_HISTORY = 20


class WorkflowCreate(BaseModel):
    name: str = "data-pipeline"


class RunRequest(BaseModel):
    workflowId: int
    workers: int = 3
    strategy: str = "fifo"


def generate_dag_workflow(name: str):
    """创建数据处理流水线 DAG 定义。"""
    nodes = [
        {"id": "extract", "name": "数据提取", "deps": [], "duration": 2.0},
        {"id": "validate", "name": "数据校验", "deps": ["extract"], "duration": 1.5},
        {"id": "clean_a", "name": "清洗分支A", "deps": ["validate"], "duration": 1.8},
        {"id": "clean_b", "name": "清洗分支B", "deps": ["validate"], "duration": 1.2},
        {"id": "transform", "name": "数据转换", "deps": ["clean_a"], "duration": 3.0},
        {"id": "enrich", "name": "数据增强", "deps": ["clean_a", "clean_b"], "duration": 2.0},
        {"id": "aggregate", "name": "聚合计算", "deps": ["transform", "enrich"], "duration": 2.5},
        {"id": "quality", "name": "质量检查", "deps": ["aggregate"], "duration": 1.0},
        {"id": "export_db", "name": "入库", "deps": ["quality"], "duration": 1.8},
        {"id": "export_report", "name": "报表生成", "deps": ["quality"], "duration": 2.2},
        {"id": "notify", "name": "通知", "deps": ["export_db", "export_report"], "duration": 0.5},
    ]
    positions = [
        (0, 0), (0, 1), (-1, 2), (1, 2), (-1, 3),
        (0.5, 3), (-0.3, 4), (-0.3, 5), (-1, 6), (0.5, 6), (-0.3, 7)
    ]
    for i, n in enumerate(nodes):
        n["x"] = positions[i][0] * 2.5 + 2.5
        n["y"] = positions[i][1] * 0.9
    edges = []
    for n in nodes:
        for d in n["deps"]:
            edges.append([d, n["id"]])
    return {"name": name, "nodes": nodes, "edges": edges}


@app.on_event("startup")
def _capture_loop():
    global MAIN_LOOP
    MAIN_LOOP = asyncio.get_event_loop()


@app.post("/api/workflow")
def create_workflow(req: WorkflowCreate):
    wf_id = max(WORKFLOWS, default=0) + 1
    dag = generate_dag_workflow(req.name)
    WORKFLOWS[wf_id] = dag
    return {"id": wf_id, "name": dag["name"],
            "nodes": dag["nodes"], "edges": dag["edges"]}


def run_snapshot(run):
    """生成对外快照：每次都是独立拷贝，历史运行不会被后续运行改写。"""
    return {
        "runId": run["id"],
        "name": run["name"],
        "status": run["status"],
        "completed": run["completed"],
        "startedAt": run["startedAt"],
        "finishedAt": run["finishedAt"],
        "maxAttempts": run["maxAttempts"],
        "workflow": {
            "id": run["id"],
            "name": run["name"],
            "nodes": [dict(n) for n in run["nodes"]],
            "edges": [list(e) for e in run["edges"]],
        },
        "stats": run.get("stats", compute_stats(run)),
        "logs": run["logs"][-200:],
        "circuitBreakers": [
            {"taskId": tid,
             "failureCount": cb["failureCount"], "state": cb["state"],
             "cooldownUntil": cb["cooldownUntil"], "terminal": cb["terminal"]}
            for tid, cb in run["breakers"].items()
        ],
    }


def broadcast(run):
    if MAIN_LOOP is None or not ACTIVE_CLIENTS:
        return
    payload = json.dumps(run_snapshot(run))
    dead = []
    for ws in list(ACTIVE_CLIENTS):
        try:
            asyncio.run_coroutine_threadsafe(ws.send_text(payload), MAIN_LOOP)
        except Exception:
            dead.append(ws)
    for ws in dead:
        if ws in ACTIVE_CLIENTS:
            ACTIVE_CLIENTS.remove(ws)


@app.post("/api/run")
def run_workflow(req: RunRequest):
    if req.workflowId not in WORKFLOWS:
        raise HTTPException(404, "workflow not found")
    run_id = max(RUN_ORDER, default=0) + 1
    dag = WORKFLOWS[req.workflowId]
    run = build_run(run_id, dag, dag["name"])
    RUNS[run_id] = run
    RUN_ORDER.append(run_id)
    if len(RUN_ORDER) > MAX_RUN_HISTORY:
        old = RUN_ORDER.pop(0)
        RUNS.pop(old, None)

    thread = threading.Thread(
        target=execute_run,
        kwargs={"run": run, "workers": req.workers, "on_update": broadcast},
        daemon=True)
    thread.start()
    return run_snapshot(run)


@app.get("/api/runs")
def list_runs():
    items = []
    for rid in reversed(RUN_ORDER):
        r = RUNS[rid]
        items.append({
            "runId": rid, "name": r["name"], "status": r["status"],
            "completed": r["completed"], "startedAt": r["startedAt"],
            "finishedAt": r["finishedAt"],
        })
    return items


@app.get("/api/runs/{run_id}")
def get_run(run_id: int):
    run = RUNS.get(run_id)
    if run is None:
        raise HTTPException(404, "run not found")
    return run_snapshot(run)


@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await ws.accept()
    ACTIVE_CLIENTS.append(ws)
    # 连上后立刻推送所有已知运行（含历史），页面刷新即可回看
    try:
        for rid in reversed(RUN_ORDER):
            await ws.send_text(json.dumps(run_snapshot(RUNS[rid])))
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        if ws in ACTIVE_CLIENTS:
            ACTIVE_CLIENTS.remove(ws)
    except Exception:
        if ws in ACTIVE_CLIENTS:
            ACTIVE_CLIENTS.remove(ws)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
