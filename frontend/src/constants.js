/**
 * 状态文案/颜色的唯一来源。
 * 明细面板（节点视角）与熔断面板（熔断器视角）都通过这里的函数生成说法，
 * 保证同一个环节在两个入口的描述完全一致。
 */
export const STATUS_META = {
    PENDING: { label: '等待中', color: '#718096' },
    RUNNING: { label: '执行中', color: '#3182ce' },
    SUCCESS: { label: '已完成', color: '#38a169' },
    FAILED: { label: '失败', color: '#e53e3e' },
    SKIPPED: { label: '已跳过', color: '#a0aec0' },
};
// 日志/尝试事件状态文案
export const LOG_STATUS_META = {
    RUNNING: { label: '开始执行', color: '#3182ce' },
    ATTEMPT_FAILED: { label: '尝试失败', color: '#e53e3e' },
    RETRY: { label: '准备重试', color: '#d69e2e' },
    SUCCESS: { label: '执行成功', color: '#38a169' },
    SKIPPED: { label: '跳过', color: '#a0aec0' },
    CIRCUIT_OPEN: { label: '熔断开启', color: '#ef4444' },
    CIRCUIT_HALF_OPEN: { label: '冷却结束·试探', color: '#fbbf24' },
    TERMINAL_FAILED: { label: '达到上限·停止', color: '#b91c1c' },
    WORKFLOW_FINISHED: { label: '流水线结束', color: '#bb86fc' },
};
export function statusMeta(status) {
    return STATUS_META[status] || { label: status, color: '#718096' };
}
export function logStatusMeta(status) {
    return LOG_STATUS_META[status] || { label: status, color: '#a0aec0' };
}
/**
 * 环节在熔断维度的统一描述。
 * 明细面板与熔断面板都调用它，节点状态 + 熔断器状态决定最终说法。
 */
export function breakerDescription(node, cb, now) {
    const cooling = cb?.state === 'OPEN' && !cb.terminal && now < (cb.cooldownUntil || 0);
    if (node?.status === 'SKIPPED') {
        return { label: '未执行', color: '#a0aec0', detail: '上游环节失败，本环节跳过' };
    }
    if (cb?.terminal) {
        return { label: '熔断中（已停止）', color: '#b91c1c', detail: '失败达到上限，本环节已永久停止' };
    }
    if (cooling && cb) {
        const left = Math.max(0, Math.ceil((cb.cooldownUntil || 0) - now));
        return { label: '熔断冷却中', color: '#ef4444', detail: `连续失败 ${cb.failureCount} 次，${left}s 后自动重试` };
    }
    if (cb?.state === 'HALF_OPEN') {
        return { label: '半开试探', color: '#fbbf24', detail: `冷却结束，正在试探执行（累计失败 ${cb.failureCount} 次）` };
    }
    if (node?.status === 'RUNNING') {
        return { label: '执行中', color: '#3182ce', detail: cb && cb.failureCount > 0 ? `失败计数 ${cb.failureCount}，正在执行` : '执行中' };
    }
    if (node?.status === 'SUCCESS') {
        return { label: '保护正常', color: '#22c55e', detail: '执行成功，无失败记录' };
    }
    if (node?.status === 'FAILED' && cb && cb.failureCount > 0) {
        return { label: '失败，即将重试', color: '#d69e2e', detail: `连续失败 ${cb.failureCount} 次，等待下次尝试` };
    }
    return { label: '保护正常', color: '#4a5568', detail: '等待调度，暂无失败' };
}
export function formatTime(ts) {
    if (!ts)
        return '--:--:--';
    const d = new Date(ts * 1000);
    return d.toLocaleTimeString('zh-CN', { hour12: false });
}
