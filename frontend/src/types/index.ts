export interface ValidationResult {
  recordsIn: number
  recordsValid: number
  recordsRejected: number
  passed: boolean
  reason: string
}

export interface Attempt {
  attempt: number
  status: string
  startedAt: number
  endedAt: number | null
  duration: number | null
  validation: ValidationResult
  message?: string
}

export interface TaskNode {
  id: string
  name: string
  deps: string[]
  x: number
  y: number
  status: string
  startTime?: number | null
  endTime?: number | null
  retries: number
  attempts: Attempt[]
  failReason?: string | null
}

export interface DAGWorkflow { id: number; name: string; nodes: TaskNode[]; edges: [string, string][] }

export interface ExecutionLog {
  seq?: number
  taskId: string
  status: string
  attempt?: number
  timestamp: number
  message: string
  validation?: ValidationResult
}

export interface CircuitBreaker {
  taskId: string
  failureCount: number
  state: string
  cooldownUntil: number
  terminal: boolean
}

export interface RunStats {
  totalNodes: number
  pending: number
  running: number
  success: number
  failed: number
  skipped: number
  totalAttempts: number
  recordsIn: number
  recordsValid: number
  recordsRejected: number
}

export interface RunSummary {
  runId: number
  name: string
  status: string
  completed: boolean
  startedAt: number
  finishedAt: number | null
}

export interface ExecutionInfo {
  runId: number
  name: string
  status: string
  completed: boolean
  startedAt: number
  finishedAt: number | null
  maxAttempts: number
  workflow: DAGWorkflow
  stats: RunStats
  logs: ExecutionLog[]
  circuitBreakers: CircuitBreaker[]
}
