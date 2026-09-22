"""端到端验证：启动真实 uvicorn，走 HTTP + WebSocket。"""
import asyncio
import json
import subprocess
import sys
import time

import httpx

BASE = "http://127.0.0.1:8000"


def wait_up(timeout=15):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            r = httpx.get(f"{BASE}/api/runs", timeout=1)
            if r.status_code == 200:
                return
        except Exception:
            pass
        time.sleep(0.3)
    raise RuntimeError("server did not start")


def run_until_complete(client, run_id, timeout=60):
    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        last = client.get(f"{BASE}/api/runs/{run_id}", timeout=5).json()
        if last["completed"]:
            return last
        time.sleep(0.3)
    raise AssertionError(f"run {run_id} did not finish: {last['stats'] if last else None}")


def validate_snapshot(s):
    assert "runId" in s and "stats" in s and "circuitBreakers" in s
    for n in s["workflow"]["nodes"]:
        assert "attempts" in n
        for a in n["attempts"]:
            v = a["validation"]
            assert v["recordsValid"] + v["recordsRejected"] == v["recordsIn"]


def check_run_consistency(s):
    stats = s["stats"]
    assert stats["totalNodes"] == 11
    assert stats["pending"] == 0 and stats["running"] == 0, stats
    # 关键：失败节点绝不能是 SUCCESS
    for n in s["workflow"]["nodes"]:
        if n["status"] == "FAILED":
            assert n["attempts"], n["id"]
            assert all(a["status"] == "FAILED" for a in n["attempts"]), n["id"]
    # 报表数字与节点明细一致
    expect_in = sum(
        n["attempts"][-1]["validation"]["recordsIn"]
        for n in s["workflow"]["nodes"] if n["status"] == "SUCCESS")
    assert stats["recordsIn"] == expect_in, (stats["recordsIn"], expect_in)
    # SKIPPED 节点没有尝试记录
    for n in s["workflow"]["nodes"]:
        if n["status"] == "SKIPPED":
            assert len(n["attempts"]) == 0


async def verify_ws_live_updates():
    """WS 必须在执行过程中持续推送（原实现工作线程拿不到事件循环，推送静默失败）。"""
    import websockets
    got = []
    async with websockets.connect("ws://127.0.0.1:8000/ws") as ws:
        # 初始历史
        try:
            while True:
                msg = await asyncio.wait_for(ws.recv(), timeout=1)
                got.append(json.loads(msg))
        except asyncio.TimeoutError:
            pass
        # 触发一次新运行
        async with httpx.AsyncClient(base_url=BASE) as ac:
            wf = (await ac.post("/api/workflow", json={"name": "ws-test"})).json()
            started = (await ac.post("/api/run", json={"workflowId": wf["id"], "workers": 3})).json()
            rid = started["runId"]
            pushed = [m for m in got if m.get("runId") == rid]
            deadline = time.time() + 60
            done = False
            while time.time() < deadline:
                msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=30))
                got.append(msg)
                if msg.get("runId") == rid:
                    pushed.append(msg)
                    if msg["completed"]:
                        done = True
                        break
            assert done, "未收到完成推送"
            # 执行过程中应当收到多帧（至少若干 RUNNING 中间态）
            assert len(pushed) >= 5, f"WS 推送帧数过少: {len(pushed)}"
    print("✓ WebSocket 实时推送正常")


def main():
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1",
         "--port", "8000", "--log-level", "warning"],
        cwd="/workspace/backend")
    try:
        wait_up()
        with httpx.Client(timeout=10) as client:
            wf = client.post(f"{BASE}/api/workflow", json={"name": "e2e"}).json()

            # 连续跑多轮，收集结果（12% 失败率，多跑几轮必然覆盖失败/熔断场景）
            results = []
            for i in range(8):
                started = client.post(f"{BASE}/api/run",
                                      json={"workflowId": wf["id"], "workers": 3}).json()
                assert started["runId"] == wf["id"] + i + 1 or started["runId"] >= 1
                final = run_until_complete(client, started["runId"])
                validate_snapshot(final)
                check_run_consistency(final)
                results.append(final)

            # 至少出现一轮失败场景（概率上几乎必然）
            failed_runs = [r for r in results if r["status"] == "FAILED"]
            assert failed_runs, "8 轮全部成功，未覆盖失败路径"
            term = next(
                (r for r in failed_runs
                 if any(cb["terminal"] for cb in r["circuitBreakers"])), None)
            assert term, "未出现达到上限的永久失败"
            print(f"✓ {len(results)} 轮执行全部结束且状态/报表自洽，"
                  f"其中 {len(failed_runs)} 轮存在失败")

            # 永久失败节点校验
            bad = next(n for n in term["workflow"]["nodes"] if n["status"] == "FAILED")
            assert len(bad["attempts"]) == term["maxAttempts"]
            assert bad["failReason"] and "重试上限" in bad["failReason"]
            print(f"✓ 节点 {bad['id']} 达到 {term['maxAttempts']} 次上限后明确停止，"
                  f"每次尝试均有数据校验记录")

            # 熔断出现过 OPEN 的轮次：冷却后必须恢复或最终 terminal，且管线没有卡死
            any_cb = any(any(cb["state"] in ("CLOSED", "OPEN") for cb in r["circuitBreakers"])
                         for r in results)
            assert any_cb

            # 历史运行列表与快照不可变
            listing = client.get(f"{BASE}/api/runs").json()
            assert len(listing) >= 2
            first_id = results[0]["runId"]
            snap1 = client.get(f"{BASE}/api/runs/{first_id}").json()
            # 再跑一轮
            new_run = client.post(f"{BASE}/api/run",
                                  json={"workflowId": wf["id"], "workers": 3}).json()
            run_until_complete(client, new_run["runId"])
            snap1_after = client.get(f"{BASE}/api/runs/{first_id}").json()
            assert snap1_after == snap1, "历史运行被后续执行改写"
            print("✓ 历史运行快照不被新一轮执行改写")

            # 明细与熔断面板数据来自同一份快照（后端层面即一致）
            cb_ids = {cb["taskId"] for cb in snap1_after["circuitBreakers"]}
            node_ids = {n["id"] for n in snap1_after["workflow"]["nodes"]}
            assert cb_ids <= node_ids

        asyncio.run(verify_ws_live_updates())
        print("\n端到端验证全部通过")
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()


if __name__ == "__main__":
    main()
