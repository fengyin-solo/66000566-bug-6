"""引擎逻辑测试（纯标准库，可直接 `python3 tests/test_engine.py` 运行）。"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.engine import build_run, execute_run, compute_stats  # noqa: E402


WORKFLOW = {
    "name": "wf",
    "nodes": [
        {"id": "a", "name": "A", "deps": [], "duration": 0.01, "x": 0, "y": 0},
        {"id": "b", "name": "B", "deps": ["a"], "duration": 0.01, "x": 0, "y": 1},
        {"id": "c", "name": "C", "deps": ["a"], "duration": 0.01, "x": 1, "y": 1},
        {"id": "d", "name": "D", "deps": ["b"], "duration": 0.01, "x": 0, "y": 2},
        {"id": "e", "name": "E", "deps": ["c", "d"], "duration": 0.01, "x": 0, "y": 3},
    ],
    "edges": [["a", "b"], ["a", "c"], ["b", "d"], ["c", "e"], ["d", "e"]],
}


def run(fail_nodes=None, max_fail_map=None, cooldown=0.3, workers=3):
    """fail_nodes 中的节点每次都失败直到上限；max_fail_map 指定只在某些尝试失败。"""
    fail_nodes = set(fail_nodes or [])

    def should_fail(tid, attempt):
        if max_fail_map and tid in max_fail_map:
            return attempt in max_fail_map[tid]
        return tid in fail_nodes

    run_obj = build_run(1, WORKFLOW, "wf")
    execute_run(run_obj, workers=workers, cooldown=cooldown, tick=0.01,
                should_fail=should_fail,
                duration_fn=lambda tid, a: 0.01)
    return run_obj


def test_all_success():
    r = run()
    assert r["status"] == "SUCCESS", r["status"]
    assert all(n["status"] == "SUCCESS" for n in r["nodes"])
    # 每个节点只有一次尝试、一条校验通过记录
    for n in r["nodes"]:
        assert len(n["attempts"]) == 1
        assert n["attempts"][0]["validation"]["passed"] is True
    assert compute_stats(r)["success"] == 5
    print("✓ test_all_success")


def test_failed_after_max_attempts_is_not_success():
    """核心问题：d 连续失败到上限，必须是 FAILED 而不是 SUCCESS。"""
    r = run(fail_nodes={"d"})
    d = next(n for n in r["nodes"] if n["id"] == "d")
    assert d["status"] == "FAILED", d["status"]
    assert len(d["attempts"]) == 4  # 首次 + 3 次重试
    assert all(att["status"] == "FAILED" for att in d["attempts"])
    # 每次尝试都有独立的数据校验结果
    for att in d["attempts"]:
        v = att["validation"]
        assert v["passed"] is False
        assert v["recordsRejected"] > 0
        assert v["recordsValid"] + v["recordsRejected"] == v["recordsIn"]
    cb = r["breakers"]["d"]
    assert cb["terminal"] is True
    assert r["status"] == "FAILED"
    print("✓ test_failed_after_max_attempts_is_not_success")


def test_downstream_skipped_and_independent_branch_runs():
    """d 永久失败 -> e 跳过；独立分支 c 不受影响继续成功。"""
    r = run(fail_nodes={"d"})
    status = {n["id"]: n["status"] for n in r["nodes"]}
    assert status["a"] == "SUCCESS"
    assert status["b"] == "SUCCESS"
    assert status["c"] == "SUCCESS"
    assert status["d"] == "FAILED"
    assert status["e"] == "SKIPPED"
    e = next(n for n in r["nodes"] if n["id"] == "e")
    assert len(e["attempts"]) == 0
    print("✓ test_downstream_skipped_and_independent_branch_runs")


def test_circuit_opens_then_recovers_after_cooldown():
    """b 前 3 次失败触发熔断，冷却后第 4 次成功；流水线整体成功。"""
    r = run(max_fail_map={"b": {1, 2, 3}})
    b = next(n for n in r["nodes"] if n["id"] == "b")
    assert b["status"] == "SUCCESS", b["status"]
    assert len(b["attempts"]) == 4
    assert [a["status"] for a in b["attempts"]] == ["FAILED", "FAILED", "FAILED", "SUCCESS"]
    cb = r["breakers"]["b"]
    assert cb["state"] == "CLOSED" and cb["failureCount"] == 0
    assert r["status"] == "SUCCESS"
    logs = [l["status"] for l in r["logs"]]
    assert "CIRCUIT_OPEN" in logs and "CIRCUIT_HALF_OPEN" in logs
    print("✓ test_circuit_opens_then_recovers_after_cooldown")


def test_other_nodes_progress_while_circuit_open():
    """b 熔断冷却期间，独立节点 c 必须照常跑完。"""
    run_obj = build_run(1, WORKFLOW, "wf")

    # b 前三次失败触发熔断，c 永远成功
    def sf(tid, a):
        return tid == "b" and a <= 3

    execute_run(run_obj, workers=3, cooldown=0.5, threshold=3,
                tick=0.01, should_fail=sf, duration_fn=lambda tid, a: 0.01)
    node_map = {n["id"]: n for n in run_obj["nodes"]}
    # c 的结束时间应早于 b 第 4 次尝试开始时间（说明冷却期间 c 在推进）
    b4_start = node_map["b"]["attempts"][3]["startedAt"]
    c_end = node_map["c"]["endTime"]
    assert c_end < b4_start, (c_end, b4_start)
    assert node_map["b"]["status"] == "SUCCESS"
    print("✓ test_other_nodes_progress_while_circuit_open")


def test_terminal_failure_breaks_half_open_cycle():
    """b 始终失败：触发熔断后再来一轮仍失败 -> 永久失败，不会无限重试。"""
    r = run(fail_nodes={"b"}, cooldown=0.2)
    b = next(n for n in r["nodes"] if n["id"] == "b")
    assert b["status"] == "FAILED"
    assert len(b["attempts"]) == 4
    assert r["breakers"]["b"]["terminal"] is True
    status = {n["id"]: n["status"] for n in r["nodes"]}
    assert status["d"] == "SKIPPED" and status["e"] == "SKIPPED"
    print("✓ test_terminal_failure_breaks_half_open_cycle")


def test_stats_consistency():
    r = run(fail_nodes={"d"})
    stats = compute_stats(r)
    assert stats["failed"] == 1 and stats["skipped"] == 1 and stats["success"] == 3
    # 处理量只统计成功节点
    success_nodes = [n for n in r["nodes"] if n["status"] == "SUCCESS"]
    expect_in = sum(n["attempts"][-1]["validation"]["recordsIn"] for n in success_nodes)
    assert stats["recordsIn"] == expect_in
    # 总尝试次数 = 3 个独立成功节点各 1 次 + a/b/c + d 4 次
    assert stats["totalAttempts"] == 4 + 3
    print("✓ test_stats_consistency")


def test_runs_are_isolated():
    r1 = run(fail_nodes={"d"})
    r2 = run()
    assert any(n["status"] == "FAILED" for n in r1["nodes"])
    assert all(n["status"] == "SUCCESS" for n in r2["nodes"])
    # r1 不受 r2 执行影响（历史不被改写）
    d = next(n for n in r1["nodes"] if n["id"] == "d")
    assert d["status"] == "FAILED"
    print("✓ test_runs_are_isolated")


if __name__ == "__main__":
    test_all_success()
    test_failed_after_max_attempts_is_not_success()
    test_downstream_skipped_and_independent_branch_runs()
    test_circuit_opens_then_recovers_after_cooldown()
    test_other_nodes_progress_while_circuit_open()
    test_terminal_failure_breaks_half_open_cycle()
    test_stats_consistency()
    test_runs_are_isolated()
    print("\n全部测试通过")
