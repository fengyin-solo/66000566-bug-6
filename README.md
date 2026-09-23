# 分布式任务工作流DAG编排与执行引擎

基于Vue 3 + FastAPI的任务编排平台，DAG拓扑排序、任务状态机、多Worker并发池、执行甘特图。

## 目标用户
数据工程师、ETL/ML Pipeline开发者、技术架构师

## 技术栈
- 前端: Vue 3 + TypeScript + Vite + Pinia + Element Plus + ECharts
- 后端: Python FastAPI + NumPy + SQLite + WebSocket

## 核心功能
1. DAG工作流编辑器：拖拽添加任务节点、连线建立依赖关系、BFS拓扑排序验证环检测
2. 任务状态机：PENDING→RUNNING→SUCCESS/FAILED/BLOCKED；重试耗尽的环节明确 FAILED 停止，绝不再显示完成，其下游全部 BLOCKED 并记录卡点来源
3. 多Worker并发池模拟：可配置Worker数量、任务执行耗时模拟
4. 任务编排策略：FIFO/最大并发两种调度策略
5. 重试机制：最多 3 次重试 + 指数退避；每次尝试都保留独立的数据校验结果（输入/实检/不合格/产出行数、未通过规则），可追溯卡在哪一次
6. 执行监控：实时WebSocket推送（按 runId 隔离）、统计栏的成功处理量只统计真实成功环节
7. 熔断保护：连续失败 3 次 OPEN，只拦截当前环节、其它环节继续推进；冷却 5s 后 HALF_OPEN 试探，成功闭合、失败重新开启；重试耗尽则 OPEN 锁定不再试探
8. 运行历史：每次执行分配独立 runId 并保存定格快照，`GET /api/runs` 与 `GET /api/runs/{runId}` 回看历史，历史不会被新执行改写；明细面板与熔断面板读取同一份节点状态，口径一致

## 运行
- 后端：`uvicorn app.main:app --port 8000`（测试：`pytest tests/`）
- 前端：`npm install && npm run dev`

