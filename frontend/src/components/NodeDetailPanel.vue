<template>
  <div class="panel">
    <h4>🔎 环节明细（数据校验结果）</h4>

    <div v-if="!node" class="empty">
      点击 DAG 节点或下方熔断条目，查看每次执行的校验结果与卡点说明
    </div>

    <template v-else>
      <div class="head">
        <span class="n-name">{{ node.name }}</span>
        <span class="n-id">{{ node.id }}</span>
      </div>

      <div class="status-line">
        <span class="badge" :style="{ background: statusColor, color: '#fff' }">
          当前状态：{{ statusText }}
        </span>
        <span v-if="node.status === 'FAILED'" class="stop-tag">已停止 · 不再重试</span>
      </div>
      <div class="desc">{{ statusDesc }}</div>

      <div v-if="blockText" class="block-box">
        <span class="block-label">卡点：</span>{{ blockText }}
        <div v-if="node.blockedBy?.length" class="block-by">
          阻塞来源：
          <a v-for="bid in node.blockedBy" :key="bid" @click="select(bid)" class="link">{{ nameOf(bid) }}</a>
        </div>
      </div>

      <div class="cb-line">
        熔断器：
        <span :style="{ color: circuitColor, fontWeight: 700 }">{{ circuitText }}</span>
        <span v-if="node.circuitState === 'OPEN' && node.cooldownUntil" class="cooldown">
          冷却剩余 {{ node.cooldownRemaining ?? '-' }}s，结束后自动试探
        </span>
        <span v-else-if="node.circuitState === 'OPEN'" class="cooldown locked">
          熔断锁定：重试已耗尽，不再试探
        </span>
        <span v-if="node.failureCount > 0" class="fail-count">连续失败 {{ node.failureCount }} 次</span>
      </div>

      <div class="attempts-title">每次执行的校验记录（共 {{ node.attempts.length }} 次）</div>
      <div v-if="!node.attempts.length" class="muted">尚未执行</div>

      <div v-for="a in node.attempts" :key="a.attempt" class="attempt" :class="a.result.toLowerCase()">
        <div class="a-head">
          <span class="a-no">第 {{ a.attempt }} 次</span>
          <span class="a-result" :class="a.result.toLowerCase()">
            {{ resultText(a.result) }}
          </span>
          <span class="a-dur">耗时 {{ a.duration.toFixed(1) }}s</span>
        </div>
        <div class="a-rule" v-if="a.rule">未通过规则：{{ a.rule }}</div>
        <div class="a-rows">
          <span>输入 {{ a.inputRows }}</span>
          <span>实检 {{ a.checkedRows }}</span>
          <span :class="{ bad: a.failedRows > 0 }">不合格 {{ a.failedRows }}</span>
          <span :class="{ ok: a.result === 'SUCCESS' }">本轮产出 {{ a.outputRows }}</span>
        </div>
        <div class="a-msg">{{ a.message }}</div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useDAGStore } from '../store/dag'
import { selectedNodeId } from '../composables/useSelection'
import {
  STATUS_TEXT, STATUS_COLOR, STATUS_DESC, CIRCUIT_TEXT, CIRCUIT_COLOR,
  blockedReasonText,
} from '../utils/status'
import type { TaskNode } from '../types'

const store = useDAGStore()

const node = computed<TaskNode | undefined>(() =>
  store.execution?.workflow.nodes.find(n => n.id === selectedNodeId.value)
)

const statusText = computed(() => node.value ? STATUS_TEXT[node.value.status] : '')
const statusColor = computed(() => node.value ? STATUS_COLOR[node.value.status] : '')
const statusDesc = computed(() => node.value ? STATUS_DESC[node.value.status] : '')
const circuitText = computed(() => node.value ? CIRCUIT_TEXT[node.value.circuitState] : '')
const circuitColor = computed(() => node.value ? CIRCUIT_COLOR[node.value.circuitState] : '')
const blockText = computed(() => node.value ? blockedReasonText(node.value.blockedReason) : '')

function resultText(r: string) {
  if (r === 'SUCCESS') return '校验通过'
  if (r === 'RETRYING') return '校验未过 · 已重试'
  return '校验未过 · 终态失败'
}

function nameOf(id: string) {
  return store.execution?.workflow.nodes.find(n => n.id === id)?.name || id
}
function select(id: string) {
  selectedNodeId.value = id
}
</script>

<style scoped>
.panel { background: #1a1a2e; border-radius: 8px; padding: 10px; border: 1px solid #2a2a4a; flex: 1; min-height: 200px; }
.panel h4 { color: #bb86fc; font-size: 12px; margin-bottom: 8px; }
.empty { color: #4a5568; font-size: 11px; line-height: 1.6; }
.head { display: flex; align-items: baseline; gap: 8px; margin-bottom: 6px; }
.n-name { font-weight: 700; color: #e0e0e0; font-size: 13px; }
.n-id { color: #666; font-size: 10px; font-family: monospace; }
.status-line { display: flex; align-items: center; gap: 8px; margin-bottom: 4px; }
.badge { font-size: 10px; padding: 2px 8px; border-radius: 10px; }
.stop-tag { color: #ef4444; font-size: 10px; font-weight: 700; }
.desc { color: #888; font-size: 10px; margin-bottom: 6px; }
.block-box { background: #d69e2e15; border-left: 3px solid #d69e2e; padding: 6px 8px; border-radius: 4px; font-size: 11px; color: #f6d28a; margin-bottom: 6px; }
.block-label { font-weight: 700; }
.block-by { margin-top: 4px; font-size: 10px; color: #cbb47a; display: flex; gap: 6px; flex-wrap: wrap; align-items: center; }
.link { color: #60a5fa; cursor: pointer; text-decoration: underline; }
.cb-line { font-size: 11px; color: #aaa; margin-bottom: 6px; display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
.cooldown { color: #fbbf24; font-size: 10px; }
.fail-count { color: #888; font-size: 10px; }
.attempts-title { color: #bb86fc; font-size: 11px; font-weight: 700; margin: 8px 0 4px; }
.muted { color: #555; font-size: 10px; }
.attempt { border: 1px solid #2a2a4a; border-radius: 6px; padding: 6px 8px; margin: 4px 0; font-size: 10px; background: #14142b; }
.attempt.failed { border-color: #e53e3e66; }
.attempt.retrying { border-color: #d69e2e66; }
.a-head { display: flex; align-items: center; gap: 8px; margin-bottom: 3px; }
.a-no { font-weight: 700; color: #ccc; }
.a-result { font-weight: 700; }
.a-result.success { color: #38a169; }
.a-result.retrying { color: #d69e2e; }
.a-result.failed { color: #ef4444; }
.a-dur { color: #666; margin-left: auto; font-family: monospace; }
.a-rule { color: #f6a0a0; margin-bottom: 2px; }
.a-rows { display: flex; gap: 10px; color: #999; font-family: monospace; margin-bottom: 2px; flex-wrap: wrap; }
.a-rows .bad { color: #ef4444; }
.a-rows .ok { color: #38a169; }
.a-msg { color: #aaa; line-height: 1.5; }
</style>
