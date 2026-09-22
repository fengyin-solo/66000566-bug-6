import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import axios from 'axios'
import type { DAGWorkflow, ExecutionInfo, RunSummary } from '@/types'

export const useDAGStore = defineStore('dag', () => {
  const loading = ref(false)
  const workflow = ref<DAGWorkflow | null>(null)
  const wsConnected = ref(false)
  const workers = ref(3)
  const strategy = ref('fifo')

  // 每次执行按 runId 独立存放，历史运行不会被新一轮执行覆盖
  const runs = ref<Record<number, ExecutionInfo>>({})
  const runList = ref<RunSummary[]>([])
  const currentRunId = ref<number | null>(null)
  // 秒级节拍，用于熔断冷却倒计时
  const now = ref(Date.now() / 1000)

  const execution = computed<ExecutionInfo | null>(() =>
    currentRunId.value == null ? null : (runs.value[currentRunId.value] || null))

  let ws: WebSocket | null = null
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null
  let closedByUs = false
  let clockTimer: ReturnType<typeof setInterval> | null = null

  function upsertRun(d: ExecutionInfo, opts: { select?: boolean } = {}) {
    runs.value[d.runId] = d
    // 只在首次收到数据或用户主动执行时切换查看对象，
    // 回看历史时其它运行的实时推送不会打断当前查看
    if (opts.select || currentRunId.value == null) currentRunId.value = d.runId
    refreshRunList(d)
  }

  function refreshRunList(latest?: ExecutionInfo) {
    if (latest) {
      const i = runList.value.findIndex(r => r.runId === latest.runId)
      const summary: RunSummary = {
        runId: latest.runId, name: latest.name, status: latest.status,
        completed: latest.completed, startedAt: latest.startedAt, finishedAt: latest.finishedAt,
      }
      if (i >= 0) runList.value[i] = summary
      else runList.value.unshift(summary)
      runList.value.sort((a, b) => b.runId - a.runId)
    } else {
      axios.get('/api/runs').then(({ data }) => { runList.value = data }).catch(() => {})
    }
  }

  function connectWS() {
    closedByUs = false
    ws = new WebSocket(`ws://${location.host}/ws`)
    ws.onopen = () => { wsConnected.value = true }
    ws.onmessage = (e) => {
      now.value = Date.now() / 1000
      try { upsertRun(JSON.parse(e.data)) } catch { /* 忽略无法解析的帧 */ }
    }
    ws.onclose = () => {
      wsConnected.value = false
      ws = null
      if (!closedByUs) reconnectTimer = setTimeout(connectWS, 2000)
    }
    if (!clockTimer) clockTimer = setInterval(() => { now.value = Date.now() / 1000 }, 1000)
  }

  function disconnectWS() {
    closedByUs = true
    if (reconnectTimer) clearTimeout(reconnectTimer)
    if (clockTimer) { clearInterval(clockTimer); clockTimer = null }
    ws?.close(); ws = null
  }

  async function createWorkflow(name: string) {
    loading.value = true
    try {
      const { data } = await axios.post('/api/workflow', { name })
      workflow.value = data
    } finally { loading.value = false }
  }

  async function run() {
    if (!workflow.value) return
    loading.value = true
    try {
      const { data } = await axios.post<ExecutionInfo>('/api/run', {
        workflowId: workflow.value.id, workers: workers.value, strategy: strategy.value,
      })
      // 新的一轮：切换到全新 runId，上一轮结果保留在 runs 中但不再显示，无残留
      currentRunId.value = data.runId
      upsertRun(data, { select: true })
    } finally { loading.value = false }
  }

  async function selectRun(runId: number) {
    currentRunId.value = runId
    if (!runs.value[runId]) {
      try {
        const { data } = await axios.get<ExecutionInfo>(`/api/runs/${runId}`)
        runs.value[runId] = data
      } catch { /* 已删除的历史运行 */ }
    }
  }

  return {
    loading, workflow, wsConnected, workers, strategy,
    runs, runList, currentRunId, execution, now,
    connectWS, disconnectWS, createWorkflow, run, selectRun,
  }
})
