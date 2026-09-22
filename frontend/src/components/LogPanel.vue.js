/// <reference types="../../node_modules/.vue-global-types/vue_3.5_0_0_0.d.ts" />
import { computed } from 'vue';
import { useDAGStore } from '../store/dag';
import { statusMeta, logStatusMeta, breakerDescription, formatTime } from '../constants';
const store = useDAGStore();
const nodes = computed(() => store.execution?.workflow.nodes || []);
const logs = computed(() => store.execution?.logs || []);
const breakers = computed(() => store.execution?.circuitBreakers || []);
function cbOf(id) {
    return breakers.value.find(b => b.taskId === id);
}
function desc(n) {
    return breakerDescription(n, cbOf(n.id), store.now);
}
function taskName(id) {
    return nodes.value.find(n => n.id === id)?.name || (id === '-' ? '流水线' : id);
}
debugger; /* PartiallyEnd: #3632/scriptSetup.vue */
const __VLS_ctx = {};
let __VLS_components;
let __VLS_directives;
/** @type {__VLS_StyleScopedClasses['panel']} */ ;
/** @type {__VLS_StyleScopedClasses['node-card']} */ ;
/** @type {__VLS_StyleScopedClasses['node-card']} */ ;
/** @type {__VLS_StyleScopedClasses['attempt']} */ ;
/** @type {__VLS_StyleScopedClasses['failed']} */ ;
/** @type {__VLS_StyleScopedClasses['att-v']} */ ;
// CSS variable injection 
// CSS variable injection end 
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "panel details" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.h4, __VLS_intrinsicElements.h4)({});
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "detail-list" },
});
for (const [n] of __VLS_getVForSourceType((__VLS_ctx.nodes))) {
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        key: (n.id),
        ...{ class: "node-card" },
        ...{ class: (n.status.toLowerCase()) },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "node-head" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
        ...{ class: "n-name" },
    });
    (n.name);
    __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
        ...{ class: "n-state" },
        ...{ style: ({ color: __VLS_ctx.statusMeta(n.status).color }) },
    });
    (__VLS_ctx.statusMeta(n.status).label);
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "n-cb" },
        ...{ style: ({ color: __VLS_ctx.desc(n).color }) },
    });
    (__VLS_ctx.desc(n).label);
    (__VLS_ctx.desc(n).detail);
    if (n.attempts && n.attempts.length) {
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "attempts" },
        });
        for (const [a] of __VLS_getVForSourceType((n.attempts))) {
            __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
                key: (a.attempt),
                ...{ class: "attempt" },
                ...{ class: (a.status.toLowerCase()) },
            });
            __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
                ...{ class: "att-head" },
            });
            __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({});
            (a.attempt);
            __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
                ...{ class: ('att-' + a.status.toLowerCase()) },
            });
            (a.status === 'SUCCESS' ? '校验通过' : '校验未通过');
            __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
                ...{ class: "att-time" },
            });
            (__VLS_ctx.formatTime(a.endedAt || a.startedAt));
            __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
                ...{ class: "att-v" },
                ...{ class: ({ bad: !a.validation.passed }) },
            });
            (a.validation.recordsIn);
            __VLS_asFunctionalElement(__VLS_intrinsicElements.b, __VLS_intrinsicElements.b)({});
            (a.validation.recordsValid);
            __VLS_asFunctionalElement(__VLS_intrinsicElements.b, __VLS_intrinsicElements.b)({});
            (a.validation.recordsRejected);
            __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
                ...{ class: "att-reason" },
            });
            (a.validation.reason);
        }
    }
    else if (n.status === 'SKIPPED') {
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "skip-reason" },
        });
        (n.failReason || '上游环节失败，未执行');
    }
    else if (n.status === 'PENDING') {
        __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
            ...{ class: "skip-reason" },
        });
    }
}
if (!__VLS_ctx.nodes.length) {
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "empty" },
    });
}
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "panel events" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.h4, __VLS_intrinsicElements.h4)({});
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "log-list" },
});
for (const [l] of __VLS_getVForSourceType(([...__VLS_ctx.logs].reverse()))) {
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        key: (l.seq ?? l.timestamp),
        ...{ class: "log-row" },
        ...{ style: ({ borderLeftColor: __VLS_ctx.logStatusMeta(l.status).color }) },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
        ...{ class: "l-status" },
        ...{ style: ({ color: __VLS_ctx.logStatusMeta(l.status).color }) },
    });
    (__VLS_ctx.logStatusMeta(l.status).label);
    __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
        ...{ class: "l-msg" },
    });
    (__VLS_ctx.taskName(l.taskId));
    if (l.attempt) {
        (l.attempt);
    }
    (l.message);
}
if (!__VLS_ctx.logs.length) {
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "empty" },
    });
}
/** @type {__VLS_StyleScopedClasses['panel']} */ ;
/** @type {__VLS_StyleScopedClasses['details']} */ ;
/** @type {__VLS_StyleScopedClasses['detail-list']} */ ;
/** @type {__VLS_StyleScopedClasses['node-card']} */ ;
/** @type {__VLS_StyleScopedClasses['node-head']} */ ;
/** @type {__VLS_StyleScopedClasses['n-name']} */ ;
/** @type {__VLS_StyleScopedClasses['n-state']} */ ;
/** @type {__VLS_StyleScopedClasses['n-cb']} */ ;
/** @type {__VLS_StyleScopedClasses['attempts']} */ ;
/** @type {__VLS_StyleScopedClasses['attempt']} */ ;
/** @type {__VLS_StyleScopedClasses['att-head']} */ ;
/** @type {__VLS_StyleScopedClasses['att-time']} */ ;
/** @type {__VLS_StyleScopedClasses['att-v']} */ ;
/** @type {__VLS_StyleScopedClasses['att-reason']} */ ;
/** @type {__VLS_StyleScopedClasses['skip-reason']} */ ;
/** @type {__VLS_StyleScopedClasses['skip-reason']} */ ;
/** @type {__VLS_StyleScopedClasses['empty']} */ ;
/** @type {__VLS_StyleScopedClasses['panel']} */ ;
/** @type {__VLS_StyleScopedClasses['events']} */ ;
/** @type {__VLS_StyleScopedClasses['log-list']} */ ;
/** @type {__VLS_StyleScopedClasses['log-row']} */ ;
/** @type {__VLS_StyleScopedClasses['l-status']} */ ;
/** @type {__VLS_StyleScopedClasses['l-msg']} */ ;
/** @type {__VLS_StyleScopedClasses['empty']} */ ;
var __VLS_dollars;
const __VLS_self = (await import('vue')).defineComponent({
    setup() {
        return {
            statusMeta: statusMeta,
            logStatusMeta: logStatusMeta,
            formatTime: formatTime,
            nodes: nodes,
            logs: logs,
            desc: desc,
            taskName: taskName,
        };
    },
});
export default (await import('vue')).defineComponent({
    setup() {
        return {};
    },
});
; /* PartiallyEnd: #4569/main.vue */
