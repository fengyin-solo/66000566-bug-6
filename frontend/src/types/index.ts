export type TaskStatus =
  | 'PENDING'      // 等待依赖 / 等待退避
  | 'RUNNING'      // 执行中
  | 'SUCCESS'      // 成功完成
  | 'FAILED'       // 重试耗尽，明确停止
  | 'BLOCKED'      // 被上游失败或熔断阻塞

export type CircuitState = 'CLOSED' | 'OPEN' | 'HALF_OPEN'

/** 单次执行的数据校验结果（每次尝试一条，历史不可改写） */
export interface AttemptRecord {
  attempt: number
  startTime: number | null
  endTime: number | null
  duration: number
  result: 'SUCCESS' | 'RETRYING' | 'FAILED'
  inputRows: number
  checkedRows: number
  failedRows: number
  outputRows: number
  rule: string | null
  message: string
}

export interface TaskNode {
  id: string
  name: string
  deps: string[]
  x: number
  y: number
  rows: number
  status: TaskStatus
  startTime?: number | null
  endTime?: number | null
  retries: number
  attempts: AttemptRecord[]
  blockedReason?: 'CIRCUIT_OPEN' | 'DEPENDENCY_FAILED' | null
  blockedBy?: string[]
  // 熔断器字段：与节点状态同源
  circuitState: CircuitState
  failureCount: number
  cooldownUntil?: number | null
  cooldownRemaining?: number | null
}

export interface DAGWorkflow {
  id: number
  name: string
  nodes: TaskNode[]
  edges: [string, string][]
}

export interface ExecutionLog {
  taskId: string
  name?: string
  status: string
  timestamp: number
  message: string
}

export interface CircuitBreaker {
  taskId: string
  name: string
  status: TaskStatus
  state: CircuitState
  failureCount: number
  cooldownUntil?: number | null
  cooldownRemaining?: number | null
}

export interface RunStats {
  total: number
  pending: number
  running: number
  success: number
  failed: number
  blocked: number
  processedRows: number
}

export interface ExecutionInfo {
  runId: number
  workflow: DAGWorkflow
  logs: ExecutionLog[]
  circuitBreakers: CircuitBreaker[]
  stats: RunStats
  completed: boolean
}

export interface RunSummary {
  runId: number
  name: string
  completed: boolean
  stats: RunStats
}
