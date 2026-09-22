"""DAG 调度引擎。

设计约定（与前端 src/constants.ts 中的状态文案保持一致）：

节点状态：PENDING / RUNNING / SUCCESS / FAILED / SKIPPED
- FAILED 且熔断器 terminal=True：已达重试上限，永久停止，下游传播 SKIPPED
- FAILED 且熔断器 OPEN（冷却中）：仅暂停自身，冷却结束自动 HALF_OPEN 试探
- 其它独立环节在冷却期间照常调度

熔断器状态：CLOSED / OPEN / HALF_OPEN，terminal 表示永久熔断
每次执行（含重试）产生一条 attempt 记录，包含数据校验结果。
"""
import random
import time
from collections import defaultdict, deque

FAILURE_THRESHOLD = 3      # 连续失败达到该次数触发熔断
MAX_ATTEMPTS = 4           # 总尝试上限（首次 + 3 次重试），达到后永久失败
COOLDOWN_SECONDS = 5.0     # 熔断冷却时间
TICK_SECONDS = 0.15
FAULTY_NODE_RATE = 0.15    # 每个节点在本轮陷入持续故障的概率

FAIL_REASONS = [
    "空值率超过阈值",
    "主键重复",
    "字段格式不合法",
    "记录数与上游不一致",
    "枚举值越界",
    "时间戳超出允许范围",
]


def _record_volume(node_id: str) -> int:
    """每个环节的数据量固定，保证重试前后口径一致、报表可核对。"""
    return 600 + (sum(ord(c) for c in node_id) * 37) % 1400


def build_run(run_id: int, workflow: dict, name: str = "workflow") -> dict:
    """根据工作流模板创建一次全新的运行实例（状态互不共享）。"""
    nodes = []
    durations = {}
    volumes = {}
    for tpl in workflow["nodes"]:
        nodes.append({
            "id": tpl["id"],
            "name": tpl["name"],
            "deps": list(tpl["deps"]),
            "x": tpl["x"],
            "y": tpl["y"],
            "status": "PENDING",
            "startTime": None,
            "endTime": None,
            "retries": 0,
            "attempts": [],
            "failReason": None,
        })
        durations[tpl["id"]] = tpl.get("duration", 1.5)
        volumes[tpl["id"]] = tpl.get("volume", _record_volume(tpl["id"]))

    now = time.time()
    return {
        "id": run_id,
        "name": name,
        "status": "RUNNING",
        "completed": False,
        "startedAt": now,
        "finishedAt": None,
        "nodes": nodes,
        "edges": [list(e) for e in workflow["edges"]],
        "logs": [],
        "breakers": {},
        "maxAttempts": MAX_ATTEMPTS,
        "_durations": durations,
        "_volumes": volumes,
        "_logSeq": 0,
    }


def _log(run, task_id, status, message, attempt=None, validation=None):
    run["_logSeq"] += 1
    entry = {
        "seq": run["_logSeq"],
        "taskId": task_id,
        "status": status,
        "attempt": attempt,
        "timestamp": time.time(),
        "message": message,
    }
    if validation is not None:
        entry["validation"] = validation
    run["logs"].append(entry)


def _get_breaker(run, task_id):
    cb = run["breakers"].get(task_id)
    if cb is None:
        cb = {"failureCount": 0, "state": "CLOSED",
              "cooldownUntil": 0, "terminal": False}
        run["breakers"][task_id] = cb
    return cb


def compute_stats(run):
    """报表数字唯一来源：每次推送都从节点/尝试记录实时汇总。"""
    stats = {
        "totalNodes": len(run["nodes"]),
        "pending": 0, "running": 0, "success": 0,
        "failed": 0, "skipped": 0,
        "totalAttempts": 0,
        "recordsIn": 0, "recordsValid": 0, "recordsRejected": 0,
    }
    for n in run["nodes"]:
        stats[n["status"].lower() if n["status"].lower() in
              ("pending", "running", "success", "failed", "skipped") else "pending"] += 1
        stats["totalAttempts"] += len(n["attempts"])
        # 处理量只计成功环节的最终一次尝试，避免重试导致重复计数
        if n["status"] == "SUCCESS" and n["attempts"]:
            v = n["attempts"][-1].get("validation")
            if v:
                stats["recordsIn"] += v["recordsIn"]
                stats["recordsValid"] += v["recordsValid"]
                stats["recordsRejected"] += v["recordsRejected"]
    return stats


def _propagate_skipped(run, root_id, adj, node_map, decided):
    """上游永久失败后，下游全部标记 SKIPPED（BFS）。"""
    stack = list(adj.get(root_id, []))
    while stack:
        tid = stack.pop()
        node = node_map[tid]
        if node["status"] in ("SUCCESS", "SKIPPED") or node["status"] == "FAILED" \
                and run["breakers"].get(tid, {}).get("terminal"):
            continue
        if node["status"] == "RUNNING":
            continue  # 理论上不会发生：上游未成功下游不可能启动
        node["status"] = "SKIPPED"
        node["endTime"] = time.time()
        node["failReason"] = "上游环节失败，未执行"
        decided.add(tid)
        _log(run, tid, "SKIPPED", "上游环节失败，本环节跳过")
        stack.extend(adj.get(tid, []))


def execute_run(run, workers=3, cooldown=COOLDOWN_SECONDS,
                max_attempts=MAX_ATTEMPTS, threshold=FAILURE_THRESHOLD,
                tick=TICK_SECONDS, should_fail=None, duration_fn=None,
                on_update=None, sleep_enabled=True):
    """执行一次运行。should_fail/duration_fn 可注入用于测试。"""
    nodes = run["nodes"]
    durations = run["_durations"]
    volumes = run["_volumes"]
    node_map = {n["id"]: n for n in nodes}
    adj = defaultdict(list)
    in_degree = defaultdict(int)
    for u, v in run["edges"]:
        adj[u].append(v)
        in_degree[v] += 1

    rng = random.Random()

    if should_fail is not None:
        fail_fn = should_fail
    else:
        # 持续性故障模型：每个节点有概率在本轮陷入故障期，
        # 前 k 次尝试连续失败，之后恢复（模拟脏数据清理/依赖恢复）；
        # k == max_attempts 时故障持续到上限，环节永久停止。
        faulty = {}
        for n in nodes:
            if rng.random() < FAULTY_NODE_RATE:
                faulty[n["id"]] = rng.randint(1, max_attempts)

        def fail_fn(tid, attempt):
            return attempt <= faulty.get(tid, 0)

    dur_fn = duration_fn or (lambda tid, attempt: durations.get(tid, 1.5) * rng.uniform(0.7, 1.3))

    ready = deque(n["id"] for n in nodes if in_degree[n["id"]] == 0)
    running = {}        # tid -> {end_time, fail, attempt, validation}
    cooling = {}        # tid -> cooldownUntil（只暂停自身，不影响其他环节）
    decided = set()     # SUCCESS / 永久 FAILED / SKIPPED

    def emit():
        run["stats"] = compute_stats(run)
        if on_update:
            on_update(run)

    while len(decided) < len(nodes):
        now = time.time()

        # 冷却结束的节点重新入队（熔断器仍为 OPEN，派发时转 HALF_OPEN）
        for tid, until in list(cooling.items()):
            if now >= until:
                del cooling[tid]
                ready.append(tid)

        # 派发就绪节点；冷却中的节点从队列移出，循环继续处理后面的节点
        while ready and len(running) < workers:
            tid = ready.popleft()
            node = node_map[tid]
            if tid in decided or tid in running:
                continue
            cb = _get_breaker(run, tid)
            if cb["terminal"]:
                continue
            if cb["state"] == "OPEN":
                if now < cb["cooldownUntil"]:
                    cooling[tid] = cb["cooldownUntil"]
                    continue  # 本轮跳过，队列中的其它环节照常派发
                cb["state"] = "HALF_OPEN"
                _log(run, tid, "CIRCUIT_HALF_OPEN",
                     f"冷却结束，进入半开试探（第 {len(node['attempts']) + 1} 次尝试）",
                     attempt=len(node["attempts"]) + 1)

            attempt_no = len(node["attempts"]) + 1
            if node["startTime"] is None:
                node["startTime"] = now
            node["status"] = "RUNNING"
            volume = volumes[tid]
            will_fail = fail_fn(tid, attempt_no)
            if will_fail:
                rejected = max(1, int(volume * rng.uniform(0.05, 0.25)))
                validation = {
                    "recordsIn": volume,
                    "recordsValid": volume - rejected,
                    "recordsRejected": rejected,
                    "passed": False,
                    "reason": rng.choice(FAIL_REASONS),
                }
            else:
                validation = {
                    "recordsIn": volume,
                    "recordsValid": volume,
                    "recordsRejected": 0,
                    "passed": True,
                    "reason": "校验通过",
                }
            attempt = {
                "attempt": attempt_no,
                "status": "RUNNING",
                "startedAt": now,
                "endedAt": None,
                "duration": None,
                "validation": validation,
            }
            node["attempts"].append(attempt)
            running[tid] = {
                "end_time": now + dur_fn(tid, attempt_no),
                "fail": will_fail,
                "attempt": attempt_no,
                "validation": validation,
            }
            _log(run, tid, "RUNNING",
                 f"开始执行 {node['name']}（第 {attempt_no} 次尝试，数据量 {volume} 条）",
                 attempt=attempt_no)
            emit()

        if not running:
            # 没有在跑的任务：等待最近的冷却结束（有 tick 休眠，不会空转）
            if cooling:
                wait = max(0.0, min(cooling.values()) - time.time())
                if sleep_enabled:
                    time.sleep(min(tick, wait) if wait > 0 else tick)
                emit()
                continue
            # 理论上不可达：无运行任务且无冷却却未全部终态
            break

        # 等待最近一个任务到期（用休眠而非忙等）
        nearest = min(info["end_time"] for info in running.values())
        wait = max(0.0, nearest - time.time())
        if cooling:
            wait = min(wait, max(0.0, min(cooling.values()) - time.time()))
        if sleep_enabled and wait > 0:
            time.sleep(min(tick, wait))

        now = time.time()
        due = [tid for tid, info in running.items() if now >= info["end_time"]]
        for tid in due:
            info = running.pop(tid)
            node = node_map[tid]
            cb = _get_breaker(run, tid)
            attempt_rec = node["attempts"][info["attempt"] - 1]
            attempt_rec["endedAt"] = now
            attempt_rec["duration"] = round(now - attempt_rec["startedAt"], 2)
            attempt_rec["validation"] = info["validation"]
            v = info["validation"]

            if not info["fail"]:
                attempt_rec["status"] = "SUCCESS"
                node["status"] = "SUCCESS"
                node["endTime"] = now
                cb["failureCount"] = 0
                cb["state"] = "CLOSED"
                cb["cooldownUntil"] = 0
                decided.add(tid)
                _log(run, tid, "SUCCESS",
                     f"完成 {node['name']}：校验通过，{v['recordsValid']} 条记录全部有效",
                     attempt=info["attempt"], validation=v)
                for nxt in adj[tid]:
                    in_degree[nxt] -= 1
                    if in_degree[nxt] == 0:
                        ready.append(nxt)
                continue

            # 本次尝试失败：如实记录，绝不允许落入成功分支
            attempt_rec["status"] = "FAILED"
            attempt_rec["message"] = (
                f"数据校验未通过：{v['recordsRejected']} 条异常（{v['reason']}），"
                f"有效 {v['recordsValid']}/{v['recordsIn']}")
            node["status"] = "FAILED"
            node["retries"] = info["attempt"]
            node["endTime"] = now
            cb["failureCount"] += 1
            _log(run, tid, "ATTEMPT_FAILED", attempt_rec["message"],
                 attempt=info["attempt"], validation=v)

            if info["attempt"] >= max_attempts:
                # 到达总尝试上限：环节明确停下来，不再重试，下游跳过
                cb["state"] = "OPEN"
                cb["terminal"] = True
                cb["cooldownUntil"] = 0
                node["failReason"] = f"已达重试上限（{max_attempts} 次尝试均失败），环节停止"
                decided.add(tid)
                _log(run, tid, "TERMINAL_FAILED",
                     f"已达重试上限（{max_attempts} 次尝试均失败），{node['name']} 停止执行",
                     attempt=info["attempt"])
                _propagate_skipped(run, tid, adj, node_map, decided)
            elif cb["failureCount"] >= threshold:
                # 触发熔断：只熔断本环节，其它环节继续推进；冷却后自动重试
                cb["state"] = "OPEN"
                cb["cooldownUntil"] = now + cooldown
                cooling[tid] = cb["cooldownUntil"]
                _log(run, tid, "CIRCUIT_OPEN",
                     f"连续 {cb['failureCount']} 次失败，熔断 {cooldown:.0f}s，"
                     f"冷却结束后自动重试；其它环节继续执行",
                     attempt=info["attempt"])
            else:
                _log(run, tid, "RETRY",
                     f"准备第 {info['attempt'] + 1} 次尝试（{info['attempt']}/{max_attempts}）",
                     attempt=info["attempt"])
                ready.appendleft(tid)

        emit()

    run["completed"] = True
    run["finishedAt"] = time.time()
    has_failure = any(
        n["status"] == "FAILED" or n["status"] == "SKIPPED" for n in nodes)
    run["status"] = "FAILED" if has_failure else "SUCCESS"
    _log(run, "-", "WORKFLOW_FINISHED",
         f"流水线结束：{run['status'] == 'SUCCESS' and '全部环节成功' or '存在失败/跳过环节'}")
    emit()
    return run
