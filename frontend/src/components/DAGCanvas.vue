<template>
  <canvas ref="cvs" class="dag-canvas" @mousemove="onMouseMove" @click="onClick"></canvas>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, nextTick } from 'vue'
import { useDAGStore } from '../store/dag'
import { selectedNodeId } from '../composables/useSelection'
import { STATUS_COLOR, STATUS_TEXT } from '../utils/status'
import type { TaskNode } from '../types'

const store = useDAGStore()
const cvs = ref<HTMLCanvasElement>()
const hoverId = ref<string | null>(null)
const nodeRects: Record<string, { x: number; y: number; w: number; h: number }> = {}

const NODE_W = 120
const NODE_H = 52

function nodePos(n: TaskNode) {
  return { x: 80 + n.x * 80, y: 60 + n.y * 80 }
}

function draw() {
  const c = cvs.value!
  c.width = c.clientWidth
  c.height = c.clientHeight
  const ctx = c.getContext('2d')!
  const W = c.width, H = c.height
  ctx.fillStyle = '#0f0f23'
  ctx.fillRect(0, 0, W, H)
  Object.keys(nodeRects).forEach(k => delete nodeRects[k])

  const wf = store.execution?.workflow || store.workflow
  if (!wf) return

  const nodes = wf.nodes
  const positions: Record<string, { x: number, y: number }> = {}
  nodes.forEach(n => { positions[n.id] = nodePos(n) })

  // 边：上游失败/阻塞则整条线标红/标黄
  wf.edges.forEach(([u, v]) => {
    const a = positions[u], b = positions[v]
    if (!a || !b) return
    const un = nodes.find(n => n.id === u)!
    let edgeColor = '#2a2a4a'
    if (un.status === 'FAILED') edgeColor = '#e53e3e'
    else if (un.status === 'BLOCKED') edgeColor = '#d69e2e'
    ctx.strokeStyle = edgeColor
    ctx.lineWidth = 2
    ctx.beginPath()
    ctx.moveTo(a.x, a.y)
    const mx = (a.x + b.x) / 2
    ctx.bezierCurveTo(mx, a.y, mx, b.y, b.x, b.y)
    ctx.stroke()

    const angle = Math.atan2(b.y - Math.max(a.y, b.y - 20), b.x - a.x)
    const arrowSize = 8
    ctx.fillStyle = edgeColor
    ctx.beginPath()
    ctx.moveTo(b.x, b.y)
    ctx.lineTo(b.x - arrowSize * Math.cos(angle - 0.5), b.y - arrowSize * Math.sin(angle - 0.5))
    ctx.lineTo(b.x - arrowSize * Math.cos(angle + 0.5), b.y - arrowSize * Math.sin(angle + 0.5))
    ctx.fill()
  })

  // 节点
  nodes.forEach(n => {
    const { x, y } = positions[n.id]
    const color = STATUS_COLOR[n.status] || '#718096'
    const selected = selectedNodeId.value === n.id
    const hovered = hoverId.value === n.id

    if (n.status === 'RUNNING') {
      ctx.shadowColor = color
      ctx.shadowBlur = 15
    }

    const rw = NODE_W, rh = NODE_H, rx = x - rw / 2, ry = y - rh / 2
    nodeRects[n.id] = { x: rx, y: ry, w: rw, h: rh }

    ctx.fillStyle = '#1a1a2e'
    ctx.strokeStyle = color
    ctx.lineWidth = selected || hovered ? 3 : 2
    ctx.beginPath()
    roundRect(ctx, rx, ry, rw, rh, 6)
    ctx.fill()
    ctx.stroke()
    ctx.shadowBlur = 0

    // 顶部状态条
    ctx.fillStyle = color
    ctx.beginPath()
    ctx.moveTo(rx + 6, ry)
    ctx.lineTo(rx + rw - 6, ry)
    ctx.lineTo(rx + rw - 6, ry + 4)
    ctx.lineTo(rx + 6, ry + 4)
    ctx.fill()

    // 名称
    ctx.fillStyle = '#e0e0e0'
    ctx.font = 'bold 11px system-ui'
    ctx.textAlign = 'center'
    ctx.fillText(n.name, x, y - 6)

    // 状态 + 尝试次数（失败/重试时信息明确）
    const attemptInfo = n.attempts?.length
      ? `第${n.attempts.length}次${n.retries > 0 ? ` 重试${n.retries}` : ''}`
      : STATUS_TEXT[n.status]
    ctx.fillStyle = color
    ctx.font = '9px monospace'
    ctx.fillText(`${STATUS_TEXT[n.status]} | ${attemptInfo}`, x, y + 8)

    // 熔断角标：与熔断面板同源
    if (n.circuitState === 'OPEN' || n.circuitState === 'HALF_OPEN') {
      ctx.fillStyle = n.circuitState === 'OPEN' ? '#ef4444' : '#fbbf24'
      ctx.beginPath()
      ctx.arc(rx + rw - 6, ry + 6, 4, 0, Math.PI * 2)
      ctx.fill()
    }

    // 耗时
    if (n.startTime && n.endTime) {
      ctx.font = '8px monospace'
      ctx.fillStyle = '#666'
      ctx.fillText(`${(n.endTime - n.startTime).toFixed(1)}s`, rx + 4, ry + rh - 4)
    }
    ctx.textAlign = 'start'
  })
}

function roundRect(ctx: CanvasRenderingContext2D, x: number, y: number, w: number, h: number, r: number) {
  ctx.moveTo(x + r, y)
  ctx.lineTo(x + w - r, y)
  ctx.arcTo(x + w, y, x + w, y + r, r)
  ctx.lineTo(x + w, y + h - r)
  ctx.arcTo(x + w, y + h, x + w - r, y + h, r)
  ctx.lineTo(x + r, y + h)
  ctx.arcTo(x, y + h, x, y + h - r, r)
  ctx.lineTo(x, y + r)
  ctx.arcTo(x, y, x + r, y, r)
}

function hitTest(e: MouseEvent): string | null {
  const rect = cvs.value!.getBoundingClientRect()
  const mx = e.clientX - rect.left
  const my = e.clientY - rect.top
  for (const [id, r] of Object.entries(nodeRects)) {
    if (mx >= r.x && mx <= r.x + r.w && my >= r.y && my <= r.y + r.h) return id
  }
  return null
}

function onMouseMove(e: MouseEvent) {
  const id = hitTest(e)
  if (id !== hoverId.value) {
    hoverId.value = id
    cvs.value!.style.cursor = id ? 'pointer' : 'default'
    draw()
  }
}

function onClick(e: MouseEvent) {
  selectedNodeId.value = hitTest(e)
  draw()
}

onMounted(() => { nextTick(draw) })
watch(() => [store.workflow, store.execution, selectedNodeId], draw, { deep: true })
</script>

<style scoped>
.dag-canvas { width: 100%; height: 100%; display: block; }
</style>
