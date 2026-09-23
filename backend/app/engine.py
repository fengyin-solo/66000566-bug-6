"""DAG 执行引擎。

修复要点：
1. 重试次数耗尽后节点明确进入 FAILED 终态并停止，绝不再显示 SUCCESS；
   每次执行（attempt）都保留独立的数据校验结果，可追溯卡点。
2. 熔断器 OPEN 只拦截当前环节，其它就绪环节继续被调度；冷却结束后自动
   进入 HALF_OPEN 试探，成功则闭合、失败则重新 OPEN。
3. 节点状态与熔断器状态挂在同一份节点数据上，明细与熔断两个面板口径一致。
4. 每次执行生成全新的 DAG 数据并绑定 runId，结束后不再改写，杜绝跨轮次残留。
"""

import random
import time
from collections import defaultdict, deque

MAX_RETRIES = 3              # 最多额外重试 3 次（共 4 次尝试）
FAILURE_THRESHOLD = 3        # 连续失败 3 次触发熔断
COOLDOWN_SECONDS = 5.0
TICK_SECONDS = 0.2

VALIDATION_RULES = ("主键唯一性校验", "非空校验", "取值范围校验", "字段格式校验")

# 终态 / 阻塞态
TERMINAL_STATUSES = ("SUCCESS", "FAILED")


class ExecutionEngine:
    def __init__(self, run_id, dag, workers=3, strategy="fifo",
                 rng=None, failure_rate=0.12, now=time.time, sleep=time.sleep,
                 on_update=None, failure_fn=None,
                 max_retries=MAX_RETRIES, failure_threshold=FAILURE_THRESHOLD,
                 cooldown_seconds=COOLDOWN_SECONDS):
        self.run_id = run_id
        self.dag = dag
        self.workers = max(1, workers)
        self.strategy = strategy
        self.rng = rng or random.Random()
        self.failure_rate = failure_rate
        self.now = now
        self.sleep = sleep
        self.on_update = on_update or (lambda snapshot: None)
        # failure_fn(tid, attempt_no) -> True 表示本次执行失败；None 时走随机
        self.failure_fn = failure_fn
        self.max_retries = max_retries
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds

        self.nodes = dag["nodes"]
        self.edges = dag["edges"]
        self.durations = dag["durations"]
        self.node_map = {n["id"]: n for n in self.nodes}

        self.in_degree = defaultdict(int)
        self.adj = defaultdict(list)
        for u, v in self.edges:
            self.in_degree[v] += 1
            self.adj[u].append(v)

        self.logs = []
        self.ready = deque()
        self.running = {}          # tid -> {end_time, will_fail, attempt, start_time}
        self.retrying = {}         # tid -> 可再次调度的时间戳（退避中）
        self.circuit_blocked = {}  # tid -> 冷却结束时间戳
        # 调度状态机：只有 QUEUED 的节点会被取出，杜绝重复入队
        # QUEUED(在ready) / RUNNING / WAITING(退避或冷却) / DONE(终态)
        self.sched_state = {}

    # ---------- 状态初始化 / 快照 ----------

    def _init_node_runtime(self):
        for n in self.nodes:
            n["status"] = "PENDING"
            n["startTime"] = None
            n["endTime"] = None
            n["retries"] = 0
            n["attempts"] = []
            n["blockedReason"] = None
            n["blockedBy"] = []
            # 熔断器字段挂在节点上，保证两个面板同源
            n["circuitState"] = "CLOSED"
            n["failureCount"] = 0
            n["cooldownUntil"] = None
            n["cooldownRemaining"] = None

    def snapshot(self, completed=False):
        now = self.now()
        for n in self.nodes:
            if n["circuitState"] == "OPEN" and n["cooldownUntil"]:
                n["cooldownRemaining"] = max(0.0, round(n["cooldownUntil"] - now, 1))
            else:
                n["cooldownRemaining"] = None
        return {
            "runId": self.run_id,
            "workflow": {
                "id": self.run_id,
                "name": self.dag.get("name", "workflow"),
                "nodes": self.nodes,
                "edges": self.edges,
            },
            "logs": list(self.logs),
            # 熔断器视图直接由节点数据派生，两个入口永远同口径
            "circuitBreakers": [{
                "taskId": n["id"],
                "name": n["name"],
                "status": n["status"],
                "state": n["circuitState"],
                "failureCount": n["failureCount"],
                "cooldownUntil": n["cooldownUntil"],
                "cooldownRemaining": n["cooldownRemaining"],
            } for n in self.nodes],
            "stats": self._stats(),
            "completed": completed,
        }

    def _stats(self):
        by_status = defaultdict(int)
        for n in self.nodes:
            by_status[n["status"]] += 1
        processed_rows = 0
        for n in self.nodes:
            if n["status"] == "SUCCESS" and n["attempts"]:
                processed_rows += n["attempts"][-1].get("outputRows", 0)
        return {
            "total": len(self.nodes),
            "pending": by_status["PENDING"],
            "running": by_status["RUNNING"],
            "success": by_status["SUCCESS"],
            "failed": by_status["FAILED"],
            "blocked": by_status["BLOCKED"],
            "processedRows": processed_rows,
        }

    # ---------- 日志 ----------

    def _log(self, tid, status, message):
        self.logs.append({
            "taskId": tid,
            "name": self.node_map[tid]["name"],
            "status": status,
            "timestamp": self.now(),
            "message": message,
        })

    # ---------- 调度 ----------

    def prepare(self):
        """初始化运行期状态并返回首帧快照（/api/run 同步返回用）。"""
        self._prepared = True
        self._init_node_runtime()
        for n in self.nodes:
            if self.in_degree[n["id"]] == 0:
                self.ready.append(n["id"])
                self.sched_state[n["id"]] = "QUEUED"
        return self.snapshot()

    def run(self):
        if not getattr(self, "_prepared", False):
            self.prepare()
        self.on_update(self.snapshot())

        while self.ready or self.running or self.retrying or self.circuit_blocked:
            self._promote_due_tasks()
            self._start_ready_tasks()
            finished = self._collect_finished()
            for tid in finished:
                self._finish(tid)

            self.on_update(self.snapshot())
            self.sleep(TICK_SECONDS)

        self.on_update(self.snapshot(completed=True))

    def _enqueue(self, tid):
        """加入就绪队列；已在队列/在途/终态的节点直接忽略，杜绝重复入队。"""
        if self.sched_state.get(tid) in ("QUEUED", "RUNNING", "WAITING", "DONE"):
            return
        self.ready.append(tid)
        self.sched_state[tid] = "QUEUED"

    def _promote(self, tid):
        """退避/冷却到期：WAITING -> QUEUED。"""
        if self.sched_state.get(tid) != "WAITING":
            return
        self.ready.append(tid)
        self.sched_state[tid] = "QUEUED"

    def _promote_due_tasks(self):
        now = self.now()
        for tid, due_at in list(self.retrying.items()):
            if now >= due_at:
                del self.retrying[tid]
                self._promote(tid)
        for tid, until in list(self.circuit_blocked.items()):
            if now >= until:
                del self.circuit_blocked[tid]
                node = self.node_map[tid]
                # 冷却结束：进入半开，允许一次试探执行
                node["circuitState"] = "HALF_OPEN"
                self._log(tid, "CIRCUIT_HALF_OPEN", "冷却结束，熔断进入半开状态，开始试探执行")
                self._promote(tid)

    def _start_ready_tasks(self):
        while self.ready and len(self.running) < self.workers:
            tid = self._pick_next()
            node = self.node_map[tid]

            # 熔断器开启且仍在冷却：只停泊当前节点，绝不阻塞队头其它环节
            if node["circuitState"] == "OPEN" and node["cooldownUntil"] and self.now() < node["cooldownUntil"]:
                self._park_circuit_open(tid)
                continue
            if node["circuitState"] == "OPEN":
                node["circuitState"] = "HALF_OPEN"

            self.sched_state[tid] = "RUNNING"
            node["status"] = "RUNNING"
            node["blockedReason"] = None
            if node["startTime"] is None:
                node["startTime"] = self.now()

            attempt_no = node["retries"] + 1
            runtime = self.durations.get(tid, 1.5) * self.rng.uniform(0.7, 1.3)
            if self.failure_fn is not None:
                will_fail = self.failure_fn(tid, attempt_no)
            else:
                will_fail = self.rng.random() < self.failure_rate
            self.running[tid] = {
                "start_time": self.now(),
                "end_time": self.now() + runtime,
                "will_fail": will_fail,
                "attempt": attempt_no,
            }
            self._log(tid, "RUNNING", f"第 {attempt_no} 次执行开始（最多 {self.max_retries + 1} 次）")

    def _pick_next(self):
        """根据调度策略取下一个就绪节点（不影响熔断隔离语义）。"""
        if self.strategy == "max_concurrent":
            # “最大并发”优先：能解锁更多下游的节点先跑
            best = max(range(len(self.ready)),
                       key=lambda i: len(self.adj[self.ready[i]]))
            tid = self.ready[best]
            del self.ready[best]
            return tid
        return self.ready.popleft()

    def _park_circuit_open(self, tid):
        node = self.node_map[tid]
        node["status"] = "BLOCKED"
        node["blockedReason"] = "CIRCUIT_OPEN"
        self.circuit_blocked[tid] = node["cooldownUntil"]
        self.sched_state[tid] = "WAITING"
        # 熔断冷却接管重新调度时机，撤销残留的退避计时，避免重复入队
        self.retrying.pop(tid, None)

    def _collect_finished(self):
        now = self.now()
        return [tid for tid, info in self.running.items() if now >= info["end_time"]]

    # ---------- 执行结果处理 ----------

    def _finish(self, tid):
        info = self.running.pop(tid)
        node = self.node_map[tid]
        attempt_no = info["attempt"]
        start, end = info["start_time"], info["end_time"]
        input_rows = node["rows"]

        if not info["will_fail"]:
            attempt = {
                "attempt": attempt_no,
                "startTime": start,
                "endTime": end,
                "duration": round(end - start, 2),
                "result": "SUCCESS",
                "inputRows": input_rows,
                "checkedRows": input_rows,
                "failedRows": 0,
                "outputRows": input_rows,
                "rule": None,
                "message": f"校验通过 {input_rows}/{input_rows} 行，输出 {input_rows} 行",
            }
            node["attempts"].append(attempt)
            node["status"] = "SUCCESS"
            node["endTime"] = end
            node["failureCount"] = 0
            node["circuitState"] = "CLOSED"
            node["cooldownUntil"] = None
            self.sched_state[tid] = "DONE"
            self._log(tid, "SUCCESS",
                      f"第 {attempt_no} 次执行成功：{attempt['message']}")
            self._unlock_downstream(tid)
            return

        # 失败：生成本次执行的校验结果
        rule = VALIDATION_RULES[self.rng.randrange(len(VALIDATION_RULES))]
        checked = int(input_rows * self.rng.uniform(0.5, 0.9))
        failed_rows = max(1, int(checked * self.rng.uniform(0.05, 0.3)))
        passed_rows = checked - failed_rows
        will_retry = node["retries"] < self.max_retries
        attempt = {
            "attempt": attempt_no,
            "startTime": start,
            "endTime": end,
            "duration": round(end - start, 2),
            "result": "RETRYING" if will_retry else "FAILED",
            "inputRows": input_rows,
            "checkedRows": checked,
            "failedRows": failed_rows,
            "outputRows": passed_rows,
            "rule": rule,
            "message": (f"{rule}未通过：{failed_rows}/{checked} 行不合格，"
                        f"本轮仅产出 {passed_rows} 行"),
        }
        node["attempts"].append(attempt)
        node["failureCount"] += 1
        self._log(tid, "FAILED", f"第 {attempt_no} 次执行失败：{attempt['message']}")

        if will_retry:
            # 回到待调度，带指数退避；节点绝不标记为完成
            node["retries"] += 1
            node["status"] = "PENDING"
            backoff = 0.5 * (2 ** (node["retries"] - 1))
            self.retrying[tid] = end + backoff
            self.sched_state[tid] = "WAITING"
            self._log(tid, "RETRY",
                      f"准备第 {node['retries'] + 1}/{self.max_retries + 1} 次执行，退避 {backoff:.1f}s")
        else:
            # 重试上限：明确 FAILED 终态，节点永久停止，下游全部阻塞。
            # 此时绝不能再 OPEN 停泊：否则冷却后会被重新调度，
            # 变成突破重试上限的“无限重试”。
            node["status"] = "FAILED"
            node["endTime"] = end
            node["cooldownUntil"] = None
            self.sched_state[tid] = "DONE"
            # 熔断已达阈值则保持 OPEN 锁定（不再冷却重试），否则维持 CLOSED
            node["circuitState"] = ("OPEN" if node["failureCount"] >= self.failure_threshold
                                    else "CLOSED")
            self._log(tid, "FAILED",
                      f"已达最大尝试次数 {self.max_retries + 1}，环节【{node['name']}】停止，不再重试")
            self._block_downstream(tid)

        # 熔断器：达到连续失败阈值后开启。OPEN 只拦截本环节调度，
        # 其它就绪环节照常由 Worker 推进；冷却结束后 HALF_OPEN 试探，
        # 试探成功即闭合。仅当本次失败之后仍有重试额度时才进入冷却停泊：
        # 若下一次就是最后一次尝试，则直接继续，不让最终判定被冷却拖延。
        retries_remaining = node["retries"] < self.max_retries
        if (will_retry and retries_remaining
                and node["failureCount"] >= self.failure_threshold
                and node["circuitState"] != "OPEN"):
            node["circuitState"] = "OPEN"
            node["cooldownUntil"] = end + self.cooldown_seconds
            self._park_circuit_open(tid)
            self._log(tid, "CIRCUIT_OPEN",
                      f"连续失败 {node['failureCount']} 次，熔断开启，冷却 {self.cooldown_seconds:.0f}s，"
                      f"期间其它环节继续推进")

    def _unlock_downstream(self, tid):
        for nxt in self.adj[tid]:
            self.in_degree[nxt] -= 1
            if self.in_degree[nxt] == 0:
                self._enqueue(nxt)

    def _block_downstream(self, failed_tid):
        """失败节点的全部直接/间接下游标记为 BLOCKED，明确卡点来源。"""
        queue = deque(self.adj[failed_tid])
        seen = set()
        while queue:
            nxt = queue.popleft()
            if nxt in seen:
                continue
            seen.add(nxt)
            node = self.node_map[nxt]
            if node["status"] in TERMINAL_STATUSES or node["status"] == "RUNNING":
                continue
            # 该节点永不参与调度
            self.ready = deque(t for t in self.ready if t != nxt)
            self.retrying.pop(nxt, None)
            self.sched_state[nxt] = "DONE"
            node["status"] = "BLOCKED"
            reasons = set(node["blockedBy"])
            reasons.add(failed_tid)
            node["blockedBy"] = sorted(reasons)
            node["blockedReason"] = "DEPENDENCY_FAILED"
            self._log(nxt, "BLOCKED",
                      f"上游环节【{self.node_map[failed_tid]['name']}】失败，本环节阻塞等待")
            queue.extend(self.adj[nxt])
