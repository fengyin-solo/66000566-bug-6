<template>
  <div class="panel">
    <h4>⚡ 熔断器状态（与环节明细同口径）</h4>
    <div class="cb-list">
      <div
        v-for="cb in breakers"
        :key="cb.taskId"
        class="cb-row"
        :class="[cb.state.toLowerCase(), { active: selected === cb.taskId }]"
        @click="select(cb.taskId)"
      >
        <div class="cb-main">
          <span class="cb-task">{{ cb.name }}</span>
          <span class="cb-state" :style="{ color: circuitColorOf(cb.state) }">
            {{ circuitTextOf(cb.state) }}
          </span>
        </div>
        <div class="cb-sub">
          <span class="cb-node-status" :style="{ color: statusColorOf(cb.status) }">
            环节状态：{{ statusTextOf(cb.status) }}
          </span>
          <span v-if="cb.state === 'OPEN' && cb.cooldownUntil" class="cb-cooldown">
            冷却 {{ cb.cooldownRemaining ?? '-' }}s
          </span>
          <span v-else-if="cb.state === 'OPEN'" class="cb-locked">已锁定</span>
          <span v-if="cb.failureCount > 0" class="cb-count">{{ cb.failureCount }} 次连续失败</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useDAGStore } from '../store/dag'
import { selectedNodeId } from '../composables/useSelection'
import {
  STATUS_TEXT, STATUS_COLOR, CIRCUIT_TEXT, CIRCUIT_COLOR,
} from '../utils/status'
import type { CircuitState, TaskStatus } from '../types'

const store = useDAGStore()
const selected = selectedNodeId
const breakers = computed(() => store.execution?.circuitBreakers || [])

function statusTextOf(s: TaskStatus) { return STATUS_TEXT[s] }
function statusColorOf(s: TaskStatus) { return STATUS_COLOR[s] }
function circuitTextOf(s: CircuitState) { return CIRCUIT_TEXT[s] }
function circuitColorOf(s: CircuitState) { return CIRCUIT_COLOR[s] }
function select(id: string) { selectedNodeId.value = id }
</script>

<style scoped>
.panel { background: #1a1a2e; border-radius: 8px; padding: 10px; border: 1px solid #2a2a4a; }
.panel h4 { color: #f87171; font-size: 12px; margin-bottom: 6px; }
.cb-list { display: flex; flex-direction: column; gap: 3px; max-height: 200px; overflow-y: auto; }
.cb-row { padding: 4px 8px; border-radius: 4px; font-size: 11px; cursor: pointer; border: 1px solid transparent; }
.cb-row:hover { border-color: #3a3a5a; }
.cb-row.active { border-color: #bb86fc; }
.cb-row.open { background: #ef444415; }
.cb-row.half_open { background: #fbbf2415; }
.cb-main { display: flex; justify-content: space-between; }
.cb-task { color: #ddd; font-weight: 600; }
.cb-state { font-weight: 700; }
.cb-sub { display: flex; gap: 10px; margin-top: 2px; font-size: 10px; color: #888; }
.cb-cooldown { color: #fbbf24; }
.cb-locked { color: #ef4444; }
</style>
