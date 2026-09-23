<template>
  <div class="panel">
    <h4>📜 执行日志</h4>
    <div class="log-list">
      <div v-for="(l, i) in logs" :key="i" class="log-row" :class="l.status.toLowerCase()">
        <span class="l-time">{{ formatTime(l.timestamp) }}</span>
        <span class="l-status">{{ l.status }}</span>
        <span class="l-task" :title="l.taskId">{{ l.name || l.taskId }}</span>
        <span class="l-msg">{{ l.message }}</span>
      </div>
      <div v-if="!logs.length" class="empty">等待执行...</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useDAGStore } from '../store/dag'
const store = useDAGStore()
const logs = computed(() => store.execution?.logs || [])

function formatTime(ts: number) {
  const d = new Date(ts * 1000)
  return `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}:` +
    `${String(d.getSeconds()).padStart(2, '0')}`
}
</script>
<style scoped>
.panel { background: #1a1a2e; border-radius: 8px; padding: 10px; border: 1px solid #2a2a4a; max-height: 260px; display: flex; flex-direction: column; }
.panel h4 { color: #bb86fc; font-size: 12px; margin-bottom: 6px; }
.log-list { overflow-y: auto; font-size: 10px; font-family: monospace; }
.log-row { display: flex; gap: 6px; padding: 2px 4px; border-radius: 2px; margin: 1px 0; align-items: baseline; }
.log-row.running { background: #3182ce15; }
.log-row.success { color: #38a169; }
.log-row.failed { color: #e53e3e; background: #e53e3e10; }
.log-row.retry { color: #d69e2e; }
.log-row.circuit_open { color: #ef4444; background: #ef444415; font-weight: 700; }
.log-row.circuit_half_open { color: #fbbf24; font-weight: 700; }
.log-row.blocked { color: #d69e2e; background: #d69e2e10; }
.l-time { color: #666; min-width: 56px; }
.l-status { font-weight: 700; min-width: 92px; }
.l-task { color: #888; min-width: 60px; }
.l-msg { color: #ccc; }
.empty { color: #4a5568; }
</style>
