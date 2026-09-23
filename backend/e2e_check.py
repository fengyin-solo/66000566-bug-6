"""真实 HTTP + WebSocket 端到端验证（连正在运行的 uvicorn）。"""
import asyncio
import json

import httpx
import websockets

BASE = "http://127.0.0.1:8000"


async def ws_collector(frames, stop):
    async with websockets.connect("ws://127.0.0.1:8000/ws") as ws:
        while not stop.is_set():
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=1.0)
                frames.append(json.loads(raw))
            except asyncio.TimeoutError:
                pass


async def wait_run(c, rid, timeout=60):
    deadline = asyncio.get_event_loop().time() + timeout
    while True:
        d = (await c.get(f"{BASE}/api/runs/{rid}")).json()
        if d["completed"]:
            return d
        if asyncio.get_event_loop().time() > deadline:
            raise AssertionError(f"run {rid} 卡死未结束")
        await asyncio.sleep(0.3)


async def main():
    frames = []
    stop = asyncio.Event()
    ws_task = asyncio.create_task(ws_collector(frames, stop))
    await asyncio.sleep(0.5)

    async with httpx.AsyncClient(timeout=30) as c:
        wf = (await c.post(f"{BASE}/api/workflow", json={"name": "p"})).json()

        # ---- 第一轮 ----
        r1 = (await c.post(f"{BASE}/api/run",
                           json={"workflowId": wf["id"], "workers": 3})).json()
        rid1 = r1["runId"]
        assert rid1 >= 1
        f1 = await wait_run(c, rid1)

        # 随机失败率下两种终态都合法，但绝不允许失败节点被报成 SUCCESS
        for n in f1["workflow"]["nodes"]:
            if n["status"] == "SUCCESS":
                assert n["attempts"][-1]["result"] == "SUCCESS"
            if n["status"] == "FAILED":
                assert len(n["attempts"]) == 4
                assert n["attempts"][-1]["result"] == "FAILED"
        # 统计口径：success+failed+blocked(+可能正在收尾的 running/pending) 自洽
        st = f1["stats"]
        assert st["success"] + st["failed"] + st["blocked"] + st["running"] + st["pending"] == st["total"]
        print(f"[run1 #{rid1}] stats={st}")

        # WS 至少收到了该轮的帧，且帧带 runId
        assert any(fr["runId"] == rid1 for fr in frames), "WS 未收到本轮推送"
        print(f"[ws] 收到 {len(frames)} 帧")

        # 两面板同口径
        cb = {x["taskId"]: x for x in f1["circuitBreakers"]}
        for n in f1["workflow"]["nodes"]:
            assert cb[n["id"]]["status"] == n["status"]
            assert cb[n["id"]]["state"] == n["circuitState"]

        # ---- 第二轮：历史隔离 ----
        r2 = (await c.post(f"{BASE}/api/run",
                           json={"workflowId": wf["id"], "workers": 3})).json()
        rid2 = r2["runId"]
        assert rid2 != rid1
        f2 = await wait_run(c, rid2)
        print(f"[run2 #{rid2}] stats={f2['stats']}")

        # 第二轮开始/结束后回看第一轮：必须定格不变
        import copy
        before = copy.deepcopy(f1["workflow"]["nodes"])
        again = (await c.get(f"{BASE}/api/runs/{rid1}")).json()
        assert again["workflow"]["nodes"] == before, "历史运行数据被改写"
        assert again["runId"] == rid1
        print("[history] 第一轮历史定格未改写")

        runs = (await c.get(f"{BASE}/api/runs")).json()
        assert {r["runId"] for r in runs} >= {rid1, rid2}
        print(f"[runs] 列表 {[r['runId'] for r in runs]}")

        # 404
        resp = await c.get(f"{BASE}/api/runs/999999")
        assert resp.status_code == 404

    stop.set()
    await ws_task
    print("E2E OK")


asyncio.run(main())
