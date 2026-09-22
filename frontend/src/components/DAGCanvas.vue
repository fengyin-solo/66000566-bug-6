<template>
  <canvas ref="cvs" class="dag-canvas" @mousemove="onMouseMove"></canvas>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, nextTick } from 'vue'
import { useDAGStore } from '../store/dag'
import { STATUS_META } from '../constants'
const store = useDAGStore()
const cvs = ref<HTMLCanvasElement>()

function draw() {
  const c = cvs.value!
  if (!c) return
  c.width = c.clientWidth; c.height = c.clientHeight
  const ctx = c.getContext('2d')!; const W = c.width, H = c.height
  ctx.fillStyle = '#0f0f23'; ctx.fillRect(0, 0, W, H)

  const wf = store.execution?.workflow || store.workflow
  if (!wf) return

  const nodes = wf.nodes
  const nodePos: Record<string, {x:number, y:number}> = {}
  nodes.forEach(n => { nodePos[n.id] = { x: 80 + n.x * 80, y: 60 + n.y * 80 } })

  // Draw edges
  wf.edges.forEach(([u, v]) => {
    const a = nodePos[u], b = nodePos[v]
    if (!a || !b) return
    const failed = nodes.find(n => n.id === u)?.status === 'FAILED' ||
                   nodes.find(n => n.id === u)?.status === 'SKIPPED' ||
                   nodes.find(n => n.id === v)?.status === 'SKIPPED'
    ctx.strokeStyle = failed ? '#7f1d1d' : '#2a2a4a'; ctx.lineWidth = 2
    ctx.beginPath(); ctx.moveTo(a.x, a.y)
    const mx = (a.x + b.x) / 2
    ctx.bezierCurveTo(mx, a.y, mx, b.y, b.x, b.y)
    ctx.stroke()

    // Arrow head
    const angle = Math.atan2(b.y - Math.max(a.y, b.y - 20), b.x - a.x)
    const arrowSize = 8
    ctx.fillStyle = ctx.strokeStyle
    ctx.beginPath()
    ctx.moveTo(b.x, b.y)
    ctx.lineTo(b.x - arrowSize * Math.cos(angle - 0.5), b.y - arrowSize * Math.sin(angle - 0.5))
    ctx.lineTo(b.x - arrowSize * Math.cos(angle + 0.5), b.y - arrowSize * Math.sin(angle + 0.5))
    ctx.fill()
  })

  // Draw nodes
  nodes.forEach(n => {
    const {x, y} = nodePos[n.id]
    const color = STATUS_META[n.status]?.color || '#4a5568'
    const label = STATUS_META[n.status]?.label || n.status

    if (n.status === 'RUNNING') {
      ctx.shadowColor = color; ctx.shadowBlur = 15
    }

    const rw = 120, rh = 44, rx = x - rw/2, ry = y - rh/2
    ctx.fillStyle = '#1a1a2e'; ctx.strokeStyle = color; ctx.lineWidth = 2
    ctx.beginPath(); roundRect(ctx, rx, ry, rw, rh, 6); ctx.fill(); ctx.stroke()
    ctx.shadowBlur = 0

    // Status bar at top
    ctx.fillStyle = color
    ctx.beginPath(); ctx.moveTo(rx+6, ry); ctx.lineTo(rx+rw-6, ry); ctx.lineTo(rx+rw-6, ry+4); ctx.lineTo(rx+6, ry+4); ctx.fill()

    // Text
    ctx.fillStyle = '#e0e0e0'; ctx.font = 'bold 11px system-ui'; ctx.textAlign = 'center'
    ctx.fillText(n.name, x, y - 2)
    ctx.fillStyle = '#888'; ctx.font = '9px monospace'
    const attempts = n.attempts?.length || 0
    const suffix = n.status === 'SKIPPED' ? '' : attempts > 0 ? ` | 尝试${attempts}次` : ''
    ctx.fillText(`${label}${suffix}`, x, y + 14)
    ctx.textAlign = 'start'

    // Duration
    if (n.startTime && n.endTime) {
      ctx.font = '8px monospace'; ctx.fillStyle = '#666'
      ctx.fillText(`${((n.endTime || 0) - (n.startTime || 0)).toFixed(1)}s`, rx + 4, ry + rh - 4)
    }
    // 永久停止原因
    if (n.status === 'FAILED' && n.failReason) {
      ctx.font = '8px monospace'; ctx.fillStyle = '#e53e3e'; ctx.textAlign = 'right'
      ctx.fillText('已停止', rx + rw - 4, ry + rh - 4)
      ctx.textAlign = 'start'
    }
  })
}

function roundRect(ctx: CanvasRenderingContext2D, x: number, y: number, w: number, h: number, r: number) {
  ctx.moveTo(x+r, y); ctx.lineTo(x+w-r, y); ctx.arcTo(x+w, y, x+w, y+r, r)
  ctx.lineTo(x+w, y+h-r); ctx.arcTo(x+w, y+h, x+w-r, y+h, r)
  ctx.lineTo(x+r, y+h); ctx.arcTo(x, y+h, x, y+h-r, r)
  ctx.lineTo(x, y+r); ctx.arcTo(x, y, x+r, y, r)
}

function onMouseMove(_e: MouseEvent) {}

onMounted(() => { nextTick(draw) })
watch(() => [store.workflow, store.execution, store.now], draw, { deep: true })
</script>

<style scoped>
.dag-canvas { width: 100%; height: 100%; display: block; }
</style>
