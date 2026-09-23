"""DAG 工作流模板定义。"""

# 节点拓扑：id / 名称 / 依赖 / 模拟耗时(秒) / 模拟数据量(行)
NODE_SPECS = [
    ("extract",       "数据提取", [],                                         2.0, 10000),
    ("validate",      "数据校验", ["extract"],                                1.5,  9980),
    ("clean_a",       "清洗分支A", ["validate"],                              1.8,  4960),
    ("clean_b",       "清洗分支B", ["validate"],                              1.2,  5020),
    ("transform",     "数据转换", ["clean_a"],                                3.0,  4960),
    ("enrich",        "数据增强", ["clean_a", "clean_b"],                     2.0,  9980),
    ("aggregate",     "聚合计算", ["transform", "enrich"],                    2.5,   240),
    ("quality",       "质量检查", ["aggregate"],                              1.0,   240),
    ("export_db",     "入库",     ["quality"],                                1.8,   240),
    ("export_report", "报表生成", ["quality"],                                2.2,    12),
    ("notify",        "通知",     ["export_db", "export_report"],             0.5,     1),
]

POSITIONS = [
    (0, 0), (0, 1), (-1, 2), (1, 2), (-1, 3),
    (0.5, 3), (-0.3, 4), (-0.3, 5), (-1, 6), (0.5, 6), (-0.3, 7),
]


def generate_dag_workflow(name: str = "data-pipeline"):
    """生成一份全新的 DAG（每次执行必须重新生成，避免轮次间数据残留）。"""
    nodes = []
    durations = {}
    for i, (nid, nname, deps, duration, rows) in enumerate(NODE_SPECS):
        px, py = POSITIONS[i]
        nodes.append({
            "id": nid,
            "name": nname,
            "deps": list(deps),
            "x": px * 2.5 + 2.5,
            "y": py * 0.9,
            "rows": rows,
            # ---- 运行期状态 ----
            "status": "PENDING",       # PENDING / WAITING / RUNNING / SUCCESS / FAILED / BLOCKED
            "startTime": None,         # 首次开始执行的时间
            "endTime": None,           # 到达终态的时间
            "retries": 0,              # 已使用的重试次数 (0..MAX_RETRIES)
            "attempts": [],            # 每次执行的校验结果，见 engine._finish_attempt
        })
        durations[nid] = duration

    edges = [[d, nid] for nid, _, deps, _, _ in NODE_SPECS for d in deps]
    return {"name": name, "nodes": nodes, "edges": edges, "durations": durations}
