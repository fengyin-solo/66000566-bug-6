import { defineStore } from 'pinia'
import { ref } from 'vue'
import axios from 'axios'
import type { DAGWorkflow, ExecutionInfo, RunSummary } from '@/types'

export const useDAGStore = defineStore('dag', () => {
  const loading = ref(false)
  const workflow = ref<DAGWorkflow | null>(null)
  const execution = ref<ExecutionInfo | null>(null)
  const historyRuns = ref<RunSummary[]>([])
  const wsConnected = ref(false)
  const workers = ref(3)
  const strategy = ref('fifo')

  let ws: WebSocket | null = null

  function connectWS() {
    ws = new WebSocket(`ws://${location.hostname}:8000/ws`)
    ws.onopen = () => { wsConnected.value = true }
    ws.onclose = () => { wsConnected.value = false }
    ws.onmessage = (e) => {
      try {
        const d = JSON.parse(e.data) as ExecutionInfo
        // 只接收当前查看的这一轮：正在浏览历史时，其它运行的推送不得改写页面
        if (execution.value && d.runId !== execution.value.runId) return
        execution.value = d
      } catch { /* 忽略无法解析的帧 */ }
    }
  }

  async function createWorkflow(name: string) {
    loading.value = true
    try {
      const { data } = await axios.post('/api/workflow', { name })
      workflow.value = data
    } finally {
      loading.value = false
    }
  }

  async function run() {
    if (!workflow.value) return
    loading.value = true
    try {
      const { data } = await axios.post('/api/run', {
        workflowId: workflow.value.id,
        workers: workers.value,
        strategy: strategy.value,
      })
      // 每轮执行都是全新 runId 的数据，直接替换，不残留上一轮结果
      execution.value = data
      await refreshHistory()
    } finally {
      loading.value = false
    }
  }

  /** 回看历史运行：拉取后由 runId 过滤保证不被其它运行的 WS 推送改写。 */
  async function viewRun(runId: number) {
    loading.value = true
    try {
      const { data } = await axios.get(`/api/runs/${runId}`)
      execution.value = data
    } finally {
      loading.value = false
    }
  }

  async function refreshHistory() {
    const { data } = await axios.get('/api/runs')
    historyRuns.value = data
  }

  function disconnectWS() {
    ws?.close()
    ws = null
  }

  return {
    loading, workflow, execution, historyRuns, wsConnected, workers, strategy,
    connectWS, createWorkflow, run, viewRun, refreshHistory, disconnectWS,
  }
})
