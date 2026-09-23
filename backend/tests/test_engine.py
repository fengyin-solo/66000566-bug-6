"""执行引擎的确定性测试：用虚拟时钟驱动，不依赖真实时间与线程。

覆盖用户反馈的四类问题：
1. 重试耗尽必须 FAILED 停止（不得显示 SUCCESS），且保留每次执行的校验结果；
2. 熔断 OPEN 期间其它环节继续推进，冷却后 HALF_OPEN 试探并恢复；
3. 明细（节点）与熔断器面板对同一环节口径一致；
4. 每次执行数据全新，历史不被改写、不残留上一轮结果。
"""
import copy
import random

from app.engine import (
    COOLDOWN_SECONDS, FAILURE_THRESHOLD, MAX_RETRIES, ExecutionEngine,
)
from app.workflow import generate_dag_workflow


def make_dag():
    """两条独立链 a->c、b->c：便于验证熔断隔离与下游阻塞。"""
    nodes = [
        {"id": "a", "name": "环节A", "deps": [], "x": 0, "y": 0, "rows": 1000},
        {"id": "b", "name": "环节B", "deps": [], "x": 2, "y": 0, "rows": 2000},
        {"id": "c", "name": "汇总C", "deps": ["a", "b"], "x": 1, "y": 1, "rows": 3000},
    ]
    edges = [["a", "c"], ["b", "c"]]
    durations = {"a": 1.0, "b": 1.0, "c": 1.0}
    return {"name": "t", "nodes": nodes, "edges": edges, "durations": durations}

class FakeClock:
    """虚拟时钟：sleep 直接跳到最近的事件时间（运行结束/退避到期/冷却到期）。"""

    def __init__(self):
        self.t = 1000.0
        self.engine = None

    def now(self):
        return self.t

    def sleep(self, _):
        assert self.engine is not None
        candidates = [info["end_time"] for info in self.engine.running.values()]
        candidates += list(self.engine.retrying.values())
        candidates += list(self.engine.circuit_blocked.values())
        if not candidates:
            # 本 tick 任务刚结束、下游下一 tick 才启动，推进一个真实 tick
            self.t += 0.2
            return
        nxt = min(candidates)
        if nxt > self.t:
            self.t = nxt
        else:
            self.t += 0.01


def run_engine(dag, failure_fn=None, workers=3, rng_seed=0, strategy="fifo", run_id=1,
               **engine_kwargs):
    clk = FakeClock()
    updates = []
    engine = ExecutionEngine(
        run_id=run_id, dag=dag, workers=workers, strategy=strategy,
        rng=random.Random(rng_seed), now=clk.now, sleep=clk.sleep,
        failure_fn=failure_fn, **engine_kwargs,
        # 生产端广播/落库前会深拷贝，这里同样拷贝，避免历史帧被后续突变改写成终态
        on_update=lambda snap: updates.append(copy.deepcopy(snap)),
    )
    clk.engine = engine
    engine.run()

    # 调度器不变量：ready 队列不得有重复 id；无残留等待；全部节点到达终态
    assert len(engine.ready) == len(set(engine.ready))
    assert not engine.retrying and not engine.circuit_blocked and not engine.running
    for n in engine.nodes:
        assert n["status"] in ("SUCCESS", "FAILED", "BLOCKED")
        assert engine.sched_state[n["id"]] == "DONE"
    return engine, updates


def node(engine, tid):
    return engine.node_map[tid]


# ---------- 1. 失败/重试/终态 ----------

def test_all_success_completes():
    dag = make_dag()
    engine, updates = run_engine(dag, failure_fn=lambda tid, i: False)
    assert updates[-1]["completed"] is True
    for tid in ("a", "b", "c"):
        n = node(engine, tid)
        assert n["status"] == "SUCCESS"
        assert n["retries"] == 0
        assert len(n["attempts"]) == 1
        assert n["attempts"][0]["result"] == "SUCCESS"


def test_retries_then_success_never_reports_early_completion():
    """前几次失败、最后成功：过程中不得出现 SUCCESS，最终成功且校验记录齐全。"""
    dag = make_dag()

    def fail(tid, attempt):
        # a 的前 2 次失败，第 3 次成功；b 始终成功
        return tid == "a" and attempt < 3

    engine, updates = run_engine(dag, failure_fn=fail)
    a = node(engine, "a")
    assert a["status"] == "SUCCESS"
    assert a["retries"] == 2
    assert [at["result"] for at in a["attempts"]] == ["RETRYING", "RETRYING", "SUCCESS"]
    # 重试阶段（尚未跑完第 3 次尝试）的任何一帧都不允许 a 提前显示完成
    for snap in updates:
        sa = next(n for n in snap["workflow"]["nodes"] if n["id"] == "a")
        if len(sa["attempts"]) < 3:
            assert sa["status"] != "SUCCESS", "重试未结束时不能显示为已完成"
    # 每次失败都有独立的数据校验结果
    for at in a["attempts"][:2]:
        assert at["checkedRows"] > 0
        assert at["failedRows"] > 0
        assert at["rule"]
        assert at["outputRows"] == at["checkedRows"] - at["failedRows"]


def test_exhausted_retries_is_failed_terminal_not_success():
    """核心缺陷回归：重试到上限后必须 FAILED，绝不能再被当作完成。"""
    dag = make_dag()
    engine, updates = run_engine(dag, failure_fn=lambda tid, i: tid == "a")

    a = node(engine, "a")
    assert a["status"] == "FAILED", "重试耗尽必须明确 FAILED"
    assert a["retries"] == MAX_RETRIES
    assert len(a["attempts"]) == MAX_RETRIES + 1
    assert [at["result"] for at in a["attempts"]] == ["RETRYING"] * MAX_RETRIES + ["FAILED"]
    assert a["endTime"] is not None
    # 最后一帧不能把失败节点报成完成
    assert updates[-1]["workflow"]["nodes"][0]["status"] == "FAILED"

    # 下游 c 必须被阻塞，且不得执行（不能像旧实现那样接着往下走）
    c = node(engine, "c")
    assert c["status"] == "BLOCKED"
    assert c["blockedReason"] == "DEPENDENCY_FAILED"
    assert "a" in c["blockedBy"]
    assert c["attempts"] == []

    # 同帧统计：失败 1、阻塞 1、成功 1；处理量只统计真实成功节点
    stats = updates[-1]["stats"]
    assert stats["failed"] == 1
    assert stats["blocked"] == 1
    assert stats["success"] == 1
    assert stats["running"] == 0
    b_rows = node(engine, "b")["attempts"][-1]["outputRows"]
    assert stats["processedRows"] == b_rows  # a 失败、c 未执行，均不得计入


def test_engine_always_terminates_even_with_failures():
    """旧实现会在熔断时队头阻塞、整轮卡死；这里要求一定能跑到 completed。"""
    dag = generate_dag_workflow()
    engine, updates = run_engine(
        dag, failure_fn=lambda tid, i: tid in ("clean_b", "transform"), workers=3
    )
    assert updates[-1]["completed"] is True


# ---------- 2. 熔断隔离 / 冷却恢复 ----------

def test_circuit_open_does_not_block_other_branches():
    """a 熔断冷却期间，独立分支 b 必须照常跑完，不得卡死。"""
    dag = make_dag()
    # 阈值=2：第 2 次失败即 OPEN，之后仍有重试额度，可确定性观察到冷却停泊帧
    engine, updates = run_engine(
        dag, failure_fn=lambda tid, i: tid == "a", failure_threshold=2
    )

    b = node(engine, "b")
    assert b["status"] == "SUCCESS"
    a = node(engine, "a")
    # a 最终 FAILED，熔断到达阈值后曾开启
    assert a["failureCount"] >= 2
    # 存在某一帧：a 因熔断 BLOCKED，而 b 已经 SUCCESS
    seen_isolation = False
    for snap in updates:
        sm = {n["id"]: n for n in snap["workflow"]["nodes"]}
        if sm["a"].get("blockedReason") == "CIRCUIT_OPEN" and sm["b"]["status"] == "SUCCESS":
            seen_isolation = True
    assert seen_isolation, "熔断保护期间其它环节应当继续推进"


def test_cooldown_half_open_retry_then_success():
    """达到阈值 OPEN -> 冷却结束 HALF_OPEN 试探 -> 成功后 CLOSED 并解锁下游。"""
    dag = make_dag()

    def fail(tid, attempt):
        # 阈值=2：前 2 次失败触发熔断，冷却后半开试探（第 3 次）成功
        return tid == "a" and attempt <= 2

    engine, _ = run_engine(dag, failure_fn=fail, failure_threshold=2)
    a = node(engine, "a")
    assert a["status"] == "SUCCESS"
    assert a["circuitState"] == "CLOSED"
    assert len(a["attempts"]) == 3
    # 冷却结束后确实完成了半开试探
    assert a["attempts"][-1]["attempt"] == 3
    # 下游 c 被解锁执行
    assert node(engine, "c")["status"] == "SUCCESS"

    # 日志必须包含 OPEN 与 HALF_OPEN 的轨迹
    statuses = [l["status"] for l in engine.logs if l["taskId"] == "a"]
    assert "CIRCUIT_OPEN" in statuses
    assert "CIRCUIT_HALF_OPEN" in statuses


def test_final_failure_does_not_revive_after_cooldown():
    """耗尽后即便熔断已 OPEN 也不能借冷却复活出第 5 次执行。"""
    dag = make_dag()
    engine, _ = run_engine(dag, failure_fn=lambda tid, i: tid == "a")
    a = node(engine, "a")
    assert a["status"] == "FAILED"
    assert len(a["attempts"]) == MAX_RETRIES + 1
    # FAILED 节点不再参与冷却停泊，run 结束后没有残留定时器
    assert "a" not in engine.circuit_blocked
    assert "a" not in engine.retrying


# ---------- 3. 两个面板同口径 ----------

def test_circuit_breaker_view_matches_node_status():
    dag = make_dag()
    engine, updates = run_engine(dag, failure_fn=lambda tid, i: tid == "a")
    snap = updates[-1]
    cb = {c["taskId"]: c for c in snap["circuitBreakers"]}
    for n in snap["workflow"]["nodes"]:
        assert cb[n["id"]]["status"] == n["status"], "明细与熔断面板节点状态必须一致"
        assert cb[n["id"]]["state"] == n["circuitState"]
        assert cb[n["id"]]["failureCount"] == n["failureCount"]
    assert cb["a"]["status"] == "FAILED"
    assert cb["a"]["state"] == "OPEN"
    assert cb["b"]["state"] == "CLOSED"


# ---------- 4. 运行隔离 / 历史不改写 ----------

def test_each_engine_run_starts_from_clean_state():
    """同一 DAG 连续跑两轮：第二轮不残留第一轮的 attempts/熔断/计数。"""
    dag = make_dag()
    engine1, _ = run_engine(dag, failure_fn=lambda tid, i: tid == "a")
    assert node(engine1, "a")["status"] == "FAILED"

    # 用同一份 dag 数据再跑一轮、这次全部成功
    engine2, updates2 = run_engine(dag, failure_fn=lambda tid, i: False, run_id=2)
    assert engine2.run_id != engine1.run_id, "两轮执行必须有不同 runId"
    for tid in ("a", "b", "c"):
        n = node(engine2, tid)
        assert n["status"] == "SUCCESS"
        assert len(n["attempts"]) == 1, "上一轮的校验记录不得残留"
        assert n["failureCount"] == 0
        assert n["circuitState"] == "CLOSED"
        assert n["blockedBy"] == []


def test_generate_dag_returns_fresh_runtime_state():
    d1 = generate_dag_workflow()
    d1["nodes"][0]["status"] = "SUCCESS"
    d1["nodes"][0]["attempts"].append({"x": 1})
    d2 = generate_dag_workflow()
    assert d2["nodes"][0]["status"] == "PENDING"
    assert d2["nodes"][0]["attempts"] == []
