<template>
  <div class="app-root">
    <header class="top-bar">
      <h1>🔀 分布式任务工作流DAG编排与执行引擎</h1>
      <div class="tools">
        <el-input v-model="wfName" placeholder="工作流名称" size="small" style="width:140px"/>
        <el-button size="small" @click="create" :loading="store.loading">创建DAG</el-button>
        <el-select v-model="store.workers" size="small" style="width:96px">
          <el-option :value="1" label="1 Worker"/><el-option :value="3" label="3 Workers"/><el-option :value="5" label="5 Workers"/>
        </el-select>
        <el-select v-model="store.strategy" size="small" style="width:96px">
          <el-option value="fifo" label="FIFO"/><el-option value="priority" label="优先级"/><el-option value="max_concurrent" label="最大并发"/>
        </el-select>
        <el-button type="success" size="small" @click="run" :disabled="!store.workflow" :loading="store.loading">▶ 执行</el-button>
        <el-select
          :model-value="store.currentRunId" size="small" style="width:170px"
          placeholder="历史运行" @change="onSelectRun">
          <el-option v-for="r in store.runList" :key="r.runId" :value="r.runId"
            :label="`#${r.runId} ${runStatusLabel(r.status)} ${formatTime(r.startedAt)}`"/>
        </el-select>
        <span class="ws-dot" :class="{on:store.wsConnected}"></span>
      </div>
    </header>

    <div v-if="stats" class="stats-bar">
      <span class="run-id">运行 #{{ store.execution?.runId }}</span>
      <span class="run-status" :style="{color: runStatusColor(store.execution?.status || 'RUNNING')}">
        {{ runStatusLabel(store.execution?.status || 'RUNNING') }}
      </span>
      <span class="stat">⏳ 等待 {{ stats.pending }}</span>
      <span class="stat running">🔄 执行中 {{ stats.running }}</span>
      <span class="stat success">✅ 成功 {{ stats.success }}</span>
      <span class="stat failed">❌ 失败 {{ stats.failed }}</span>
      <span class="stat skipped">⏭️ 跳过 {{ stats.skipped }}</span>
      <span class="divider">|</span>
      <span class="stat">执行次数 {{ stats.totalAttempts }}（重试不重复计处理量）</span>
      <span class="stat">输入 {{ stats.recordsIn }} 条</span>
      <span class="stat success">有效 {{ stats.recordsValid }} 条</span>
      <span class="stat failed">异常 {{ stats.recordsRejected }} 条</span>
    </div>

    <div class="main-grid">
      <div class="dag-area">
        <DAGCanvas />
      </div>
      <div class="side-area">
        <LogPanel />
        <CircuitBreakerPanel />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, onMounted, onUnmounted } from 'vue'
import DAGCanvas from './components/DAGCanvas.vue'
import LogPanel from './components/LogPanel.vue'
import CircuitBreakerPanel from './components/CircuitBreakerPanel.vue'
import { useDAGStore } from './store/dag'
import { formatTime } from './constants'
const store = useDAGStore()
const wfName = ref('data-pipeline')

const stats = computed(() => store.execution?.stats || null)

function create() { store.createWorkflow(wfName.value) }
function run() { store.run() }
function onSelectRun(id: number) { store.selectRun(id) }

const RUN_STATUS: Record<string, string> = {
  RUNNING: '执行中', SUCCESS: '全部成功', FAILED: '存在失败',
}
function runStatusLabel(s: string) { return RUN_STATUS[s] || s }
function runStatusColor(s: string) {
  return s === 'SUCCESS' ? '#38a169' : s === 'FAILED' ? '#e53e3e' : '#3182ce'
}

onMounted(() => store.connectWS())
onUnmounted(() => store.disconnectWS())
</script>

<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:system-ui,sans-serif;background:#0c0c1d;color:#e0e0e0}
.app-root{height:100vh;display:flex;flex-direction:column}
.top-bar{display:flex;justify-content:space-between;align-items:center;padding:10px 20px;background:#1a1a2e;border-bottom:1px solid #2a2a4a}
.top-bar h1{font-size:1rem;color:#bb86fc}
.tools{display:flex;gap:6px;align-items:center}
.ws-dot{width:8px;height:8px;border-radius:50%;background:#ef4444}.ws-dot.on{background:#22c55e}
.stats-bar{display:flex;gap:14px;align-items:center;padding:6px 20px;background:#14142b;border-bottom:1px solid #2a2a4a;font-size:11px;font-family:monospace;flex-wrap:wrap}
.stats-bar .stat{color:#aaa}.stats-bar .stat.success{color:#38a169}.stats-bar .stat.failed{color:#e53e3e}
.stats-bar .stat.running{color:#3182ce}.stats-bar .stat.skipped{color:#a0aec0}
.run-id{color:#bb86fc;font-weight:700}.run-status{font-weight:700}.divider{color:#333}
.main-grid{display:grid;grid-template-columns:1fr 340px;flex:1;overflow:hidden}
.dag-area{background:#0f0f23;position:relative;overflow:hidden}
.side-area{display:flex;flex-direction:column;gap:8px;padding:8px;overflow:hidden;background:#14142b}
</style>
