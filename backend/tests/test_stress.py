"""随机压力测试：任意失败模式下调度器都必须正常终止、无重复调度、状态守恒。"""
import random

from app.engine import ExecutionEngine
from app.workflow import generate_dag_workflow


class Clock:
    def __init__(self):
        self.t = 0.0
        self.engine = None

    def now(self):
        return self.t

    def sleep(self, _):
        c = [i["end_time"] for i in self.engine.running.values()]
        c += list(self.engine.retrying.values())
        c += list(self.engine.circuit_blocked.values())
        self.t = min(c) if c else self.t + 0.2


def run_once(seed):
    rng = random.Random(seed)
    dag = generate_dag_workflow()
    # 每个节点独立失败概率 0~0.9
    rates = {n["id"]: rng.uniform(0, 0.9) for n in dag["nodes"]}

    clk = Clock()
    frames = []
    engine = ExecutionEngine(
        run_id=seed, dag=dag,
        workers=rng.choice([1, 2, 3, 5]),
        strategy=rng.choice(["fifo", "max_concurrent"]),
        rng=rng, now=clk.now, sleep=clk.sleep,
        max_retries=rng.choice([0, 1, 2, 3]),
        failure_threshold=rng.choice([1, 2, 3]),
        cooldown_seconds=rng.choice([0.1, 0.5, 2.0]),
        failure_fn=lambda tid, i, r=rng, rates=rates: r.random() < rates[tid],
        on_update=frames.append,
    )
    clk.engine = engine
    engine.run()
    return engine


def test_stress_random_failures_always_terminates():
    for seed in range(300):
        engine = run_once(seed)
        # 1) 无重复调度 / 无残留
        assert len(engine.ready) == len(set(engine.ready))
        assert not engine.running and not engine.retrying and not engine.circuit_blocked

        statuses = [n["status"] for n in engine.nodes]
        # 2) 每个节点有确定终态
        assert all(s in ("SUCCESS", "FAILED", "BLOCKED") for s in statuses), (seed, statuses)

        # 3) BLOCKED 节点必然可沿依赖边溯源到某个 FAILED
        failed = {n["id"] for n in engine.nodes if n["status"] == "FAILED"}
        nm = engine.node_map

        def reaches_failed(tid, seen):
            if tid in failed:
                return True
            if tid in seen:
                return False
            seen.add(tid)
            return any(reaches_failed(d, seen) for d in nm[tid]["deps"])

        for n in engine.nodes:
            if n["status"] == "BLOCKED":
                assert reaches_failed(n["id"], set()), (seed, n["id"])
                assert engine.sched_state[n["id"]] == "DONE"
            if n["status"] == "FAILED":
                assert len(n["attempts"]) == engine.max_retries + 1
                assert n["attempts"][-1]["result"] == "FAILED"
            if n["status"] == "SUCCESS":
                assert n["attempts"][-1]["result"] == "SUCCESS"

        # 4) SUCCESS 节点的所有上游必须也是 SUCCESS（失败不能被报成完成并放行下游）
        for n in engine.nodes:
            if n["status"] == "SUCCESS":
                for d in n["deps"]:
                    assert nm[d]["status"] == "SUCCESS", (seed, n["id"], d, nm[d]["status"])
