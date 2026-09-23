"""API 层集成测试：运行隔离、历史定格、两面板同口径。

用 TestClient + 真实工作线程，DAG 耗时与退避/冷却都压到毫秒级。
"""
import time
from functools import partial

import pytest
from fastapi.testclient import TestClient

from app import main
from app.engine import ExecutionEngine


@pytest.fixture
def client_fast_dag(monkeypatch):
    def tiny_dag(name="workflow"):
        nodes = [
            {"id": "a", "name": "环节A", "deps": [], "x": 0, "y": 0, "rows": 100},
            {"id": "b", "name": "环节B", "deps": [], "x": 2, "y": 0, "rows": 200},
            {"id": "c", "name": "汇总C", "deps": ["a", "b"], "x": 1, "y": 1, "rows": 300},
        ]
        return {"name": name, "nodes": nodes, "edges": [["a", "c"], ["b", "c"]],
                "durations": {"a": 0.02, "b": 0.02, "c": 0.02}}

    monkeypatch.setattr(main, "generate_dag_workflow", tiny_dag)
    # 全部成功的引擎（覆盖默认 12% 随机失败）
    monkeypatch.setattr(main, "ExecutionEngine",
                        partial(ExecutionEngine, failure_rate=0.0))
    with TestClient(main.app) as client:
        yield client


def _wait_completed(client, run_id, timeout=10.0):
    deadline = time.time() + timeout
    while True:
        r = client.get(f"/api/runs/{run_id}")
        assert r.status_code == 200
        data = r.json()
        if data["completed"]:
            return data
        assert time.time() < deadline, f"运行 {run_id} 超时未完成（疑似卡死）"
        time.sleep(0.05)


def test_run_creates_fresh_runids_and_independent_state(client_fast_dag):
    r1 = client_fast_dag.post("/api/run", json={"workflowId": 1, "workers": 3})
    r2 = client_fast_dag.post("/api/run", json={"workflowId": 1, "workers": 3})
    s1, s2 = r1.json(), r2.json()
    assert s1["runId"] != s2["runId"], "每次执行必须分配新的 runId"
    # 两个运行的节点数据是相互独立的对象
    assert s1["workflow"]["nodes"][0] is not s2["workflow"]["nodes"][0]

    f1 = _wait_completed(client_fast_dag, s1["runId"])
    f2 = _wait_completed(client_fast_dag, s2["runId"])
    for f in (f1, f2):
        assert {n["status"] for n in f["workflow"]["nodes"]} == {"SUCCESS"}
        assert f["stats"]["failed"] == 0
        assert f["stats"]["blocked"] == 0


def test_completed_run_history_is_frozen(client_fast_dag):
    s = client_fast_dag.post("/api/run", json={"workflowId": 1}).json()
    final = _wait_completed(client_fast_dag, s["runId"])

    # 再次回看：历史数据必须逐字一致，不能被后台改写
    again = client_fast_dag.get(f"/api/runs/{s['runId']}").json()
    assert again["completed"] is True
    assert again["workflow"]["nodes"] == final["workflow"]["nodes"]
    assert again["logs"] == final["logs"]
    assert again["stats"] == final["stats"]
    # 等一会儿再取一次，确认没有残留线程继续写入
    time.sleep(0.3)
    third = client_fast_dag.get(f"/api/runs/{s['runId']}").json()
    assert third["workflow"]["nodes"] == final["workflow"]["nodes"]


def test_new_run_does_not_overwrite_previous_run(client_fast_dag):
    s1 = client_fast_dag.post("/api/run", json={"workflowId": 1}).json()
    f1 = _wait_completed(client_fast_dag, s1["runId"])
    s2 = client_fast_dag.post("/api/run", json={"workflowId": 1}).json()
    f2 = _wait_completed(client_fast_dag, s2["runId"])

    # 第二轮的存在不得改写第一轮的任何节点
    old = client_fast_dag.get(f"/api/runs/{s1['runId']}").json()
    assert old["runId"] == f1["runId"]
    assert old["workflow"]["nodes"] == f1["workflow"]["nodes"]
    assert old["runId"] != f2["runId"]

    runs = client_fast_dag.get("/api/runs").json()
    ids = {r["runId"] for r in runs}
    assert {s1["runId"], s2["runId"]} <= ids


def test_unknown_run_returns_404(client_fast_dag):
    assert client_fast_dag.get("/api/runs/99999").status_code == 404


def test_circuit_breaker_view_consistent_with_nodes(client_fast_dag):
    s = client_fast_dag.post("/api/run", json={"workflowId": 1}).json()
    final = _wait_completed(client_fast_dag, s["runId"])
    cb = {c["taskId"]: c for c in final["circuitBreakers"]}
    for n in final["workflow"]["nodes"]:
        assert cb[n["id"]]["status"] == n["status"]
        assert cb[n["id"]]["state"] == n["circuitState"]
        assert cb[n["id"]]["failureCount"] == n["failureCount"]


@pytest.fixture
def client_failing_dag(monkeypatch):
    """a 节点每次都失败；阈值/冷却/退避全部压短。"""
    def tiny_dag(name="workflow"):
        nodes = [
            {"id": "a", "name": "环节A", "deps": [], "x": 0, "y": 0, "rows": 100},
            {"id": "b", "name": "环节B", "deps": [], "x": 2, "y": 0, "rows": 200},
            {"id": "c", "name": "汇总C", "deps": ["a", "b"], "x": 1, "y": 1, "rows": 300},
        ]
        return {"name": name, "nodes": nodes, "edges": [["a", "c"], ["b", "c"]],
                "durations": {"a": 0.02, "b": 0.02, "c": 0.02}}

    monkeypatch.setattr(main, "generate_dag_workflow", tiny_dag)
    monkeypatch.setattr(main, "ExecutionEngine", partial(
        ExecutionEngine, failure_fn=lambda tid, attempt: tid == "a",
        failure_threshold=2, cooldown_seconds=0.2, max_retries=3))
    with TestClient(main.app) as client:
        yield client


def test_failed_node_stops_and_downstream_blocked_with_circuit_logs(client_failing_dag):
    s = client_failing_dag.post("/api/run", json={"workflowId": 1, "workers": 3}).json()
    final = _wait_completed(client_failing_dag, s["runId"], timeout=10.0)
    nm = {n["id"]: n for n in final["workflow"]["nodes"]}

    assert nm["a"]["status"] == "FAILED", "重试耗尽必须 FAILED，不得显示完成"
    assert len(nm["a"]["attempts"]) == 4
    assert nm["b"]["status"] == "SUCCESS", "熔断只隔离 a，b 必须照常完成"
    assert nm["c"]["status"] == "BLOCKED"
    assert "a" in nm["c"]["blockedBy"]

    stats = final["stats"]
    assert stats["failed"] == 1 and stats["success"] == 1 and stats["blocked"] == 1
    assert stats["processedRows"] == nm["b"]["attempts"][-1]["outputRows"]

    statuses = {l["status"] for l in final["logs"] if l["taskId"] == "a"}
    assert {"RUNNING", "FAILED", "CIRCUIT_OPEN", "CIRCUIT_HALF_OPEN"} <= statuses

    cb = {c["taskId"]: c for c in final["circuitBreakers"]}
    assert cb["a"]["status"] == "FAILED"
    assert cb["b"]["status"] == "SUCCESS"
