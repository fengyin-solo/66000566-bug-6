<template>
  <div class="panel">
    <h4>⚡ 熔断器状态</h4>
    <div v-for="n in nodes" :key="n.id" class="cb-row"
         :style="{ borderLeftColor: desc(n).color }">
      <div class="cb-main">
        <span class="cb-task">{{ n.name }}</span>
        <span class="cb-state" :style="{ color: desc(n).color }">{{ desc(n).label }}</span>
      </div>
      <span class="cb-detail">{{ desc(n).detail }}</span>
    </div>
    <div v-if="!nodes.length" class="empty">等待执行...</div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useDAGStore } from '../store/dag'
import { breakerDescription } from '../constants'
import type { CircuitBreaker, TaskNode } from '@/types'
const store = useDAGStore()
const nodes = computed<TaskNode[]>(() => store.execution?.workflow.nodes || [])
const breakers = computed<CircuitBreaker[]>(() => store.execution?.circuitBreakers || [])
function cbOf(id: string) {
  return breakers.value.find(b => b.taskId === id)
}
// 与执行明细面板调用同一个函数，两个入口对同一环节的说法必然一致
function desc(n: TaskNode) {
  return breakerDescription(n, cbOf(n.id), store.now)
}
</script>
<style scoped>
.panel{background:#1a1a2e;border-radius:8px;padding:10px;border:1px solid #2a2a4a;max-height:240px;overflow-y:auto}
.panel h4{color:#f87171;font-size:12px;margin-bottom:6px}
.cb-row{display:flex;flex-direction:column;padding:4px 6px;border-left:3px solid transparent;background:#14142b;border-radius:3px;margin:3px 0}
.cb-main{display:flex;justify-content:space-between;align-items:center}
.cb-task{color:#ccc;font-weight:600;font-size:11px}.cb-state{font-weight:700;font-size:10px}
.cb-detail{color:#888;font-size:9px;margin-top:1px}
.empty{color:#4a5568;font-size:11px}
</style>
