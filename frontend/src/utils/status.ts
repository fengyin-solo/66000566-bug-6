import type { CircuitState, TaskStatus } from '@/types'

/** 节点状态 / 熔断状态的唯一文案来源：DAG、明细面板、熔断面板共用同一说法。 */

export const STATUS_TEXT: Record<TaskStatus, string> = {
  PENDING: '等待中',
  RUNNING: '执行中',
  SUCCESS: '已完成',
  FAILED: '失败停止',
  BLOCKED: '已阻塞',
}

export const STATUS_COLOR: Record<TaskStatus, string> = {
  PENDING: '#718096',
  RUNNING: '#3182ce',
  SUCCESS: '#38a169',
  FAILED: '#e53e3e',
  BLOCKED: '#d69e2e',
}

export const STATUS_DESC: Record<TaskStatus, string> = {
  PENDING: '等待依赖完成或退避结束后调度',
  RUNNING: '环节正在执行',
  SUCCESS: '全部数据校验通过，输出已交下游',
  FAILED: '已达最大尝试次数，本环节明确停止，下游不再推进',
  BLOCKED: '上游失败或熔断保护生效，本环节暂不推进',
}

export const CIRCUIT_TEXT: Record<CircuitState, string> = {
  CLOSED: '闭合正常',
  OPEN: '熔断保护中',
  HALF_OPEN: '半开试探',
}

export const CIRCUIT_COLOR: Record<CircuitState, string> = {
  CLOSED: '#38a169',
  OPEN: '#ef4444',
  HALF_OPEN: '#fbbf24',
}

export function blockedReasonText(reason?: string | null): string {
  if (reason === 'CIRCUIT_OPEN') return '熔断冷却中，冷却结束后自动试探'
  if (reason === 'DEPENDENCY_FAILED') return '上游环节失败停止，本环节无法继续'
  return ''
}
