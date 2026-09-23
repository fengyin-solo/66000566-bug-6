<template>
  <div class="app-root">
    <header class="top-bar">
      <h1>🔀 分布式任务工作流DAG编排与执行引擎</h1>
      <div class="tools">
        <el-input v-model="wfName" placeholder="工作流名称" size="small" style="width:140px"/>
        <el-button size="small" @click="create" :loading="store.loading">创建DAG</el-button>
        <el-select v-model="store.workers" size="small" style="width:100px">
          <el-option :value="1" label="1 Worker"/><el-option :value="3" label="3 Workers"/><el-option :value="5" label="5 Workers"/>
        </el-select>
        <el-select v-model="store.strategy" size="small" style="width:110px">
          <el-option value="fifo" label="FIFO"/><el-option value="priority" label="优先级"/><el-option value="max_concurrent" label="最大并发"/>
        </el-select>
        <el-button type="success" size="small" @click="run" :disabled="!store.workflow" :loading="store.loading">▶ 执行</el-button>
        <el-select size="small" style="width:150px" placeholder="回看历史运行"
                   :model-value="store.execution?.runId" @change="onViewRun">
          <el-option v-for="r in store.historyRuns" :key="r.runId" :value="r.runId"
                     :label="`#${r.runId} ${r.completed ? '已结束' : '进行中'}`"/>
        </el-select>
        <span class="ws-dot" :class="{ on: store.wsConnected }"></span>
      </div>
    </header>

    <div v-if="stats" class="stats-bar">
      <span class="run-id">运行 #{{ store.execution?.runId }}</span>
      <span class="chip total">共 {{ stats.total }} 环节</span>
      <span class="chip running">执行中 {{ stats.running }}</span>
      <span class="chip pending">等待 {{ stats.pending }}</span>
      <span class="chip success">完成 {{ stats.success }}</span>
      <span class="chip failed">失败停止 {{ stats.failed }}</span>
      <span class="chip blocked">阻塞 {{ stats.blocked }}</span>
      <span class="chip rows">实际成功处理量 {{ stats.processedRows.toLocaleString() }} 行</span>
      <span v-if="store.execution?.completed" class="done-tag"
            :class="{ bad: stats.failed > 0 || stats.blocked > 0 }">
        {{ stats.failed > 0 || stats.blocked > 0 ? '本轮存在失败/阻塞环节' : '本轮全部完成' }}
      </span>
    </div>

    <div class="main-grid">
      <div class="dag-area">
        <DAGCanvas />
      </div>
      <div class="side-area">
        <NodeDetailPanel />
        <LogPanel />
        <CircuitBreakerPanel />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import DAGCanvas from './components/DAGCanvas.vue'
import LogPanel from './components/LogPanel.vue'
import CircuitBreakerPanel from './components/CircuitBreakerPanel.vue'
import NodeDetailPanel from './components/NodeDetailPanel.vue'
import { useDAGStore } from './store/dag'

const store = useDAGStore()
const wfName = ref('data-pipeline')
const stats = computed(() => store.execution?.stats ?? null)

function create() { store.createWorkflow(wfName.value) }
function run() { store.run() }
function onViewRun(runId: number) { store.viewRun(runId) }

onMounted(() => {
  store.connectWS()
  store.refreshHistory()
})
onUnmounted(() => store.disconnectWS())
</script>

<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: system-ui, sans-serif; background: #0c0c1d; color: #e0e0e0; }
.app-root { height: 100vh; display: flex; flex-direction: column; }
.top-bar { display: flex; justify-content: space-between; align-items: center; padding: 10px 20px; background: #1a1a2e; border-bottom: 1px solid #2a2a4a; }
.top-bar h1 { font-size: 1rem; color: #bb86fc; }
.tools { display: flex; gap: 6px; align-items: center; }
.ws-dot { width: 8px; height: 8px; border-radius: 50%; background: #ef4444; }
.ws-dot.on { background: #22c55e; }
.stats-bar { display: flex; gap: 8px; align-items: center; padding: 6px 20px; background: #14142b; border-bottom: 1px solid #2a2a4a; font-size: 11px; flex-wrap: wrap; }
.run-id { color: #bb86fc; font-weight: 700; margin-right: 4px; }
.chip { padding: 2px 8px; border-radius: 10px; background: #1f1f3a; color: #bbb; }
.chip.running { color: #63b3ed; }
.chip.success { color: #48bb78; }
.chip.failed { color: #fc8181; }
.chip.blocked { color: #f6d28a; }
.chip.rows { color: #9f7aea; font-weight: 700; }
.done-tag { margin-left: auto; font-weight: 700; color: #48bb78; }
.done-tag.bad { color: #fc8181; }
.main-grid { display: grid; grid-template-columns: 1fr 340px; flex: 1; overflow: hidden; }
.dag-area { background: #0f0f23; position: relative; overflow: hidden; }
.side-area { display: flex; flex-direction: column; gap: 8px; padding: 8px; overflow-y: auto; background: #14142b; }
</style>
