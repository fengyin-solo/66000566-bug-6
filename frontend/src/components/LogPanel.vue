<template>
  <div class="panel details">
    <h4>📋 执行明细</h4>
    <div class="detail-list">
      <div v-for="n in nodes" :key="n.id" class="node-card" :class="n.status.toLowerCase()">
        <div class="node-head">
          <span class="n-name">{{ n.name }}</span>
          <span class="n-state" :style="{ color: statusMeta(n.status).color }">
            {{ statusMeta(n.status).label }}
          </span>
        </div>

        <!-- 熔断维度说法与熔断面板完全一致 -->
        <div class="n-cb" :style="{ color: desc(n).color }">{{ desc(n).label }} · {{ desc(n).detail }}</div>

        <!-- 每次执行的数据校验结果 -->
        <div v-if="n.attempts && n.attempts.length" class="attempts">
          <div v-for="a in n.attempts" :key="a.attempt" class="attempt" :class="a.status.toLowerCase()">
            <div class="att-head">
              <span>第{{ a.attempt }}次</span>
              <span :class="'att-' + a.status.toLowerCase()">
                {{ a.status === 'SUCCESS' ? '校验通过' : '校验未通过' }}
              </span>
              <span class="att-time">{{ formatTime(a.endedAt || a.startedAt) }}</span>
            </div>
            <div class="att-v" :class="{ bad: !a.validation.passed }">
              输入 {{ a.validation.recordsIn }} 条 ·
              有效 <b>{{ a.validation.recordsValid }}</b> 条 ·
              异常 <b>{{ a.validation.recordsRejected }}</b> 条
              <span class="att-reason">（{{ a.validation.reason }}）</span>
            </div>
          </div>
        </div>
        <div v-else-if="n.status === 'SKIPPED'" class="skip-reason">{{ n.failReason || '上游环节失败，未执行' }}</div>
        <div v-else-if="n.status === 'PENDING'" class="skip-reason">等待调度…</div>
      </div>
      <div v-if="!nodes.length" class="empty">等待执行...</div>
    </div>
  </div>

  <div class="panel events">
    <h4>📜 事件日志</h4>
    <div class="log-list">
      <div v-for="l in [...logs].reverse()" :key="l.seq ?? l.timestamp" class="log-row"
           :style="{ borderLeftColor: logStatusMeta(l.status).color }">
        <span class="l-status" :style="{ color: logStatusMeta(l.status).color }">
          {{ logStatusMeta(l.status).label }}
        </span>
        <span class="l-msg">{{ taskName(l.taskId) }}<template v-if="l.attempt"> · 第{{ l.attempt }}次</template>：{{ l.message }}</span>
      </div>
      <div v-if="!logs.length" class="empty">等待执行...</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useDAGStore } from '../store/dag'
import { statusMeta, logStatusMeta, breakerDescription, formatTime } from '../constants'
import type { CircuitBreaker, TaskNode } from '@/types'

const store = useDAGStore()
const nodes = computed<TaskNode[]>(() => store.execution?.workflow.nodes || [])
const logs = computed(() => store.execution?.logs || [])
const breakers = computed<CircuitBreaker[]>(() => store.execution?.circuitBreakers || [])

function cbOf(id: string) {
  return breakers.value.find(b => b.taskId === id)
}
function desc(n: TaskNode) {
  return breakerDescription(n, cbOf(n.id), store.now)
}
function taskName(id: string) {
  return nodes.value.find(n => n.id === id)?.name || (id === '-' ? '流水线' : id)
}
</script>

<style scoped>
.panel{background:#1a1a2e;border-radius:8px;padding:10px;border:1px solid #2a2a4a}
.details{flex:1;min-height:0;display:flex;flex-direction:column}
.panel h4{color:#bb86fc;font-size:12px;margin-bottom:6px}
.detail-list{overflow-y:auto;display:flex;flex-direction:column;gap:6px;min-height:0}
.node-card{border:1px solid #2a2a4a;border-radius:6px;padding:6px 8px;background:#14142b}
.node-card.failed{border-color:#7f1d1d}.node-card.skipped{opacity:.75}
.node-head{display:flex;justify-content:space-between;align-items:center}
.n-name{color:#e0e0e0;font-size:11px;font-weight:600}
.n-state{font-size:10px;font-weight:700}
.n-cb{font-size:9px;margin-top:2px;color:#888}
.attempts{margin-top:4px;display:flex;flex-direction:column;gap:3px}
.attempt{border-left:2px solid #38a169;padding-left:6px;font-size:9px;font-family:monospace}
.attempt.failed{border-left-color:#e53e3e}
.att-head{display:flex;gap:6px;color:#888}
.att-success{color:#38a169}.att-failed{color:#e53e3e}
.att-time{margin-left:auto}
.att-v{color:#aaa;margin-top:1px}.att-v.bad{color:#e59999}.att-reason{color:#777}
.skip-reason{font-size:9px;color:#888;margin-top:3px}
.events{flex-shrink:0;max-height:220px;display:flex;flex-direction:column}
.log-list{max-height:180px;overflow-y:auto;font-size:10px;font-family:monospace}
.log-row{display:flex;gap:6px;padding:2px 4px;border-left:2px solid transparent;margin:1px 0}
.l-status{font-weight:700;min-width:64px;flex-shrink:0}
.l-msg{color:#ccc}.empty{color:#4a5568;font-size:10px}
</style>
