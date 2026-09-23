import asyncio
import copy
import json
import threading

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .engine import ExecutionEngine
from .workflow import generate_dag_workflow

app = FastAPI(title="DAG Workflow Engine")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"],
    allow_methods=["*"], allow_headers=["*"],
)

ACTIVE_CLIENTS: set[WebSocket] = set()
LOOP: asyncio.AbstractEventLoop | None = None

# 运行注册表：run_id -> {engine, snapshot, completed, lock}
RUNS: dict[int, dict] = {}
RUNS_LOCK = threading.Lock()
WORKFLOW_SEQ = 0
RUN_SEQ = 0


@app.on_event("startup")
def _capture_loop():
    global LOOP
    LOOP = asyncio.get_event_loop()


class WorkflowCreate(BaseModel):
    name: str = "data-pipeline"


class RunRequest(BaseModel):
    workflowId: int
    workers: int = 3
    strategy: str = "fifo"


def broadcast(payload: dict):
    """把快照推给所有 WS；前端按 runId 自行过滤。

    快照做深拷贝，避免 JSON 序列化与引擎线程的继续修改相互干扰。
    """
    data = json.dumps(copy.deepcopy(payload), ensure_ascii=False, default=str)
    if LOOP is None:
        return
    for ws in list(ACTIVE_CLIENTS):
        try:
            asyncio.run_coroutine_threadsafe(ws.send_text(data), LOOP)
        except Exception:
            pass


def _register_run(run_id: int, record: dict):
    with RUNS_LOCK:
        RUNS[run_id] = record


def _get_run(run_id: int) -> dict:
    with RUNS_LOCK:
        record = RUNS.get(run_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"运行 {run_id} 不存在")
    return record


def _current_snapshot(record: dict) -> dict:
    with record["lock"]:
        return copy.deepcopy(record["snapshot"])


@app.post("/api/workflow")
def create_workflow(req: WorkflowCreate):
    """只生成 DAG 模板，不保存任何运行期状态。"""
    global WORKFLOW_SEQ
    WORKFLOW_SEQ += 1
    dag = generate_dag_workflow(req.name)
    return {
        "id": WORKFLOW_SEQ,
        "name": req.name,
        "nodes": dag["nodes"],
        "edges": dag["edges"],
        "_durations": dag["durations"],
    }


@app.post("/api/run")
def run_workflow(req: RunRequest):
    """启动一次全新执行：新 runId、全新 DAG 数据，与历史运行完全隔离。"""
    global RUN_SEQ
    RUN_SEQ += 1
    run_id = RUN_SEQ

    # 每次都重新生成 DAG，节点状态/attempts 不沿用上一轮
    dag = generate_dag_workflow("workflow")
    engine = ExecutionEngine(run_id, dag, workers=req.workers, strategy=req.strategy)

    record = {"engine": engine, "snapshot": engine.prepare(),
              "completed": False, "lock": threading.Lock()}

    def on_update(snapshot: dict):
        with record["lock"]:
            record["snapshot"] = snapshot
            record["completed"] = bool(snapshot.get("completed"))
        broadcast(snapshot)

    engine.on_update = on_update
    _register_run(run_id, record)

    thread = threading.Thread(target=engine.run, name=f"run-{run_id}", daemon=True)
    thread.start()

    return _current_snapshot(record)


@app.get("/api/runs")
def list_runs():
    with RUNS_LOCK:
        ids = sorted(RUNS.keys())
    summary = []
    for rid in ids:
        snap = _current_snapshot(RUNS[rid])
        summary.append({
            "runId": rid,
            "name": snap["workflow"]["name"],
            "completed": snap["completed"],
            "stats": snap["stats"],
        })
    return summary


@app.get("/api/runs/{run_id}")
def get_run(run_id: int):
    """重新查看历史运行：返回其定格快照。已完成的运行引擎不再改写数据。"""
    return _current_snapshot(_get_run(run_id))


@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await ws.accept()
    ACTIVE_CLIENTS.add(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        ACTIVE_CLIENTS.discard(ws)
