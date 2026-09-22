/// <reference types="../node_modules/.vue-global-types/vue_3.5_0_0_0.d.ts" />
import { computed, ref, onMounted, onUnmounted } from 'vue';
import DAGCanvas from './components/DAGCanvas.vue';
import LogPanel from './components/LogPanel.vue';
import CircuitBreakerPanel from './components/CircuitBreakerPanel.vue';
import { useDAGStore } from './store/dag';
import { formatTime } from './constants';
const store = useDAGStore();
const wfName = ref('data-pipeline');
const stats = computed(() => store.execution?.stats || null);
function create() { store.createWorkflow(wfName.value); }
function run() { store.run(); }
function onSelectRun(id) { store.selectRun(id); }
const RUN_STATUS = {
    RUNNING: '执行中', SUCCESS: '全部成功', FAILED: '存在失败',
};
function runStatusLabel(s) { return RUN_STATUS[s] || s; }
function runStatusColor(s) {
    return s === 'SUCCESS' ? '#38a169' : s === 'FAILED' ? '#e53e3e' : '#3182ce';
}
onMounted(() => store.connectWS());
onUnmounted(() => store.disconnectWS());
debugger; /* PartiallyEnd: #3632/scriptSetup.vue */
const __VLS_ctx = {};
let __VLS_components;
let __VLS_directives;
// CSS variable injection 
// CSS variable injection end 
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "app-root" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.header, __VLS_intrinsicElements.header)({
    ...{ class: "top-bar" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.h1, __VLS_intrinsicElements.h1)({});
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "tools" },
});
const __VLS_0 = {}.ElInput;
/** @type {[typeof __VLS_components.ElInput, typeof __VLS_components.elInput, ]} */ ;
// @ts-ignore
const __VLS_1 = __VLS_asFunctionalComponent(__VLS_0, new __VLS_0({
    modelValue: (__VLS_ctx.wfName),
    placeholder: "工作流名称",
    size: "small",
    ...{ style: {} },
}));
const __VLS_2 = __VLS_1({
    modelValue: (__VLS_ctx.wfName),
    placeholder: "工作流名称",
    size: "small",
    ...{ style: {} },
}, ...__VLS_functionalComponentArgsRest(__VLS_1));
const __VLS_4 = {}.ElButton;
/** @type {[typeof __VLS_components.ElButton, typeof __VLS_components.elButton, typeof __VLS_components.ElButton, typeof __VLS_components.elButton, ]} */ ;
// @ts-ignore
const __VLS_5 = __VLS_asFunctionalComponent(__VLS_4, new __VLS_4({
    ...{ 'onClick': {} },
    size: "small",
    loading: (__VLS_ctx.store.loading),
}));
const __VLS_6 = __VLS_5({
    ...{ 'onClick': {} },
    size: "small",
    loading: (__VLS_ctx.store.loading),
}, ...__VLS_functionalComponentArgsRest(__VLS_5));
let __VLS_8;
let __VLS_9;
let __VLS_10;
const __VLS_11 = {
    onClick: (__VLS_ctx.create)
};
__VLS_7.slots.default;
var __VLS_7;
const __VLS_12 = {}.ElSelect;
/** @type {[typeof __VLS_components.ElSelect, typeof __VLS_components.elSelect, typeof __VLS_components.ElSelect, typeof __VLS_components.elSelect, ]} */ ;
// @ts-ignore
const __VLS_13 = __VLS_asFunctionalComponent(__VLS_12, new __VLS_12({
    modelValue: (__VLS_ctx.store.workers),
    size: "small",
    ...{ style: {} },
}));
const __VLS_14 = __VLS_13({
    modelValue: (__VLS_ctx.store.workers),
    size: "small",
    ...{ style: {} },
}, ...__VLS_functionalComponentArgsRest(__VLS_13));
__VLS_15.slots.default;
const __VLS_16 = {}.ElOption;
/** @type {[typeof __VLS_components.ElOption, typeof __VLS_components.elOption, ]} */ ;
// @ts-ignore
const __VLS_17 = __VLS_asFunctionalComponent(__VLS_16, new __VLS_16({
    value: (1),
    label: "1 Worker",
}));
const __VLS_18 = __VLS_17({
    value: (1),
    label: "1 Worker",
}, ...__VLS_functionalComponentArgsRest(__VLS_17));
const __VLS_20 = {}.ElOption;
/** @type {[typeof __VLS_components.ElOption, typeof __VLS_components.elOption, ]} */ ;
// @ts-ignore
const __VLS_21 = __VLS_asFunctionalComponent(__VLS_20, new __VLS_20({
    value: (3),
    label: "3 Workers",
}));
const __VLS_22 = __VLS_21({
    value: (3),
    label: "3 Workers",
}, ...__VLS_functionalComponentArgsRest(__VLS_21));
const __VLS_24 = {}.ElOption;
/** @type {[typeof __VLS_components.ElOption, typeof __VLS_components.elOption, ]} */ ;
// @ts-ignore
const __VLS_25 = __VLS_asFunctionalComponent(__VLS_24, new __VLS_24({
    value: (5),
    label: "5 Workers",
}));
const __VLS_26 = __VLS_25({
    value: (5),
    label: "5 Workers",
}, ...__VLS_functionalComponentArgsRest(__VLS_25));
var __VLS_15;
const __VLS_28 = {}.ElSelect;
/** @type {[typeof __VLS_components.ElSelect, typeof __VLS_components.elSelect, typeof __VLS_components.ElSelect, typeof __VLS_components.elSelect, ]} */ ;
// @ts-ignore
const __VLS_29 = __VLS_asFunctionalComponent(__VLS_28, new __VLS_28({
    modelValue: (__VLS_ctx.store.strategy),
    size: "small",
    ...{ style: {} },
}));
const __VLS_30 = __VLS_29({
    modelValue: (__VLS_ctx.store.strategy),
    size: "small",
    ...{ style: {} },
}, ...__VLS_functionalComponentArgsRest(__VLS_29));
__VLS_31.slots.default;
const __VLS_32 = {}.ElOption;
/** @type {[typeof __VLS_components.ElOption, typeof __VLS_components.elOption, ]} */ ;
// @ts-ignore
const __VLS_33 = __VLS_asFunctionalComponent(__VLS_32, new __VLS_32({
    value: "fifo",
    label: "FIFO",
}));
const __VLS_34 = __VLS_33({
    value: "fifo",
    label: "FIFO",
}, ...__VLS_functionalComponentArgsRest(__VLS_33));
const __VLS_36 = {}.ElOption;
/** @type {[typeof __VLS_components.ElOption, typeof __VLS_components.elOption, ]} */ ;
// @ts-ignore
const __VLS_37 = __VLS_asFunctionalComponent(__VLS_36, new __VLS_36({
    value: "priority",
    label: "优先级",
}));
const __VLS_38 = __VLS_37({
    value: "priority",
    label: "优先级",
}, ...__VLS_functionalComponentArgsRest(__VLS_37));
const __VLS_40 = {}.ElOption;
/** @type {[typeof __VLS_components.ElOption, typeof __VLS_components.elOption, ]} */ ;
// @ts-ignore
const __VLS_41 = __VLS_asFunctionalComponent(__VLS_40, new __VLS_40({
    value: "max_concurrent",
    label: "最大并发",
}));
const __VLS_42 = __VLS_41({
    value: "max_concurrent",
    label: "最大并发",
}, ...__VLS_functionalComponentArgsRest(__VLS_41));
var __VLS_31;
const __VLS_44 = {}.ElButton;
/** @type {[typeof __VLS_components.ElButton, typeof __VLS_components.elButton, typeof __VLS_components.ElButton, typeof __VLS_components.elButton, ]} */ ;
// @ts-ignore
const __VLS_45 = __VLS_asFunctionalComponent(__VLS_44, new __VLS_44({
    ...{ 'onClick': {} },
    type: "success",
    size: "small",
    disabled: (!__VLS_ctx.store.workflow),
    loading: (__VLS_ctx.store.loading),
}));
const __VLS_46 = __VLS_45({
    ...{ 'onClick': {} },
    type: "success",
    size: "small",
    disabled: (!__VLS_ctx.store.workflow),
    loading: (__VLS_ctx.store.loading),
}, ...__VLS_functionalComponentArgsRest(__VLS_45));
let __VLS_48;
let __VLS_49;
let __VLS_50;
const __VLS_51 = {
    onClick: (__VLS_ctx.run)
};
__VLS_47.slots.default;
var __VLS_47;
const __VLS_52 = {}.ElSelect;
/** @type {[typeof __VLS_components.ElSelect, typeof __VLS_components.elSelect, typeof __VLS_components.ElSelect, typeof __VLS_components.elSelect, ]} */ ;
// @ts-ignore
const __VLS_53 = __VLS_asFunctionalComponent(__VLS_52, new __VLS_52({
    ...{ 'onChange': {} },
    modelValue: (__VLS_ctx.store.currentRunId),
    size: "small",
    ...{ style: {} },
    placeholder: "历史运行",
}));
const __VLS_54 = __VLS_53({
    ...{ 'onChange': {} },
    modelValue: (__VLS_ctx.store.currentRunId),
    size: "small",
    ...{ style: {} },
    placeholder: "历史运行",
}, ...__VLS_functionalComponentArgsRest(__VLS_53));
let __VLS_56;
let __VLS_57;
let __VLS_58;
const __VLS_59 = {
    onChange: (__VLS_ctx.onSelectRun)
};
__VLS_55.slots.default;
for (const [r] of __VLS_getVForSourceType((__VLS_ctx.store.runList))) {
    const __VLS_60 = {}.ElOption;
    /** @type {[typeof __VLS_components.ElOption, typeof __VLS_components.elOption, ]} */ ;
    // @ts-ignore
    const __VLS_61 = __VLS_asFunctionalComponent(__VLS_60, new __VLS_60({
        key: (r.runId),
        value: (r.runId),
        label: (`#${r.runId} ${__VLS_ctx.runStatusLabel(r.status)} ${__VLS_ctx.formatTime(r.startedAt)}`),
    }));
    const __VLS_62 = __VLS_61({
        key: (r.runId),
        value: (r.runId),
        label: (`#${r.runId} ${__VLS_ctx.runStatusLabel(r.status)} ${__VLS_ctx.formatTime(r.startedAt)}`),
    }, ...__VLS_functionalComponentArgsRest(__VLS_61));
}
var __VLS_55;
__VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
    ...{ class: "ws-dot" },
    ...{ class: ({ on: __VLS_ctx.store.wsConnected }) },
});
if (__VLS_ctx.stats) {
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "stats-bar" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
        ...{ class: "run-id" },
    });
    (__VLS_ctx.store.execution?.runId);
    __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
        ...{ class: "run-status" },
        ...{ style: ({ color: __VLS_ctx.runStatusColor(__VLS_ctx.store.execution?.status || 'RUNNING') }) },
    });
    (__VLS_ctx.runStatusLabel(__VLS_ctx.store.execution?.status || 'RUNNING'));
    __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
        ...{ class: "stat" },
    });
    (__VLS_ctx.stats.pending);
    __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
        ...{ class: "stat running" },
    });
    (__VLS_ctx.stats.running);
    __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
        ...{ class: "stat success" },
    });
    (__VLS_ctx.stats.success);
    __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
        ...{ class: "stat failed" },
    });
    (__VLS_ctx.stats.failed);
    __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
        ...{ class: "stat skipped" },
    });
    (__VLS_ctx.stats.skipped);
    __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
        ...{ class: "divider" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
        ...{ class: "stat" },
    });
    (__VLS_ctx.stats.totalAttempts);
    __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
        ...{ class: "stat" },
    });
    (__VLS_ctx.stats.recordsIn);
    __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
        ...{ class: "stat success" },
    });
    (__VLS_ctx.stats.recordsValid);
    __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
        ...{ class: "stat failed" },
    });
    (__VLS_ctx.stats.recordsRejected);
}
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "main-grid" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "dag-area" },
});
/** @type {[typeof DAGCanvas, ]} */ ;
// @ts-ignore
const __VLS_64 = __VLS_asFunctionalComponent(DAGCanvas, new DAGCanvas({}));
const __VLS_65 = __VLS_64({}, ...__VLS_functionalComponentArgsRest(__VLS_64));
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "side-area" },
});
/** @type {[typeof LogPanel, ]} */ ;
// @ts-ignore
const __VLS_67 = __VLS_asFunctionalComponent(LogPanel, new LogPanel({}));
const __VLS_68 = __VLS_67({}, ...__VLS_functionalComponentArgsRest(__VLS_67));
/** @type {[typeof CircuitBreakerPanel, ]} */ ;
// @ts-ignore
const __VLS_70 = __VLS_asFunctionalComponent(CircuitBreakerPanel, new CircuitBreakerPanel({}));
const __VLS_71 = __VLS_70({}, ...__VLS_functionalComponentArgsRest(__VLS_70));
/** @type {__VLS_StyleScopedClasses['app-root']} */ ;
/** @type {__VLS_StyleScopedClasses['top-bar']} */ ;
/** @type {__VLS_StyleScopedClasses['tools']} */ ;
/** @type {__VLS_StyleScopedClasses['ws-dot']} */ ;
/** @type {__VLS_StyleScopedClasses['stats-bar']} */ ;
/** @type {__VLS_StyleScopedClasses['run-id']} */ ;
/** @type {__VLS_StyleScopedClasses['run-status']} */ ;
/** @type {__VLS_StyleScopedClasses['stat']} */ ;
/** @type {__VLS_StyleScopedClasses['stat']} */ ;
/** @type {__VLS_StyleScopedClasses['running']} */ ;
/** @type {__VLS_StyleScopedClasses['stat']} */ ;
/** @type {__VLS_StyleScopedClasses['success']} */ ;
/** @type {__VLS_StyleScopedClasses['stat']} */ ;
/** @type {__VLS_StyleScopedClasses['failed']} */ ;
/** @type {__VLS_StyleScopedClasses['stat']} */ ;
/** @type {__VLS_StyleScopedClasses['skipped']} */ ;
/** @type {__VLS_StyleScopedClasses['divider']} */ ;
/** @type {__VLS_StyleScopedClasses['stat']} */ ;
/** @type {__VLS_StyleScopedClasses['stat']} */ ;
/** @type {__VLS_StyleScopedClasses['stat']} */ ;
/** @type {__VLS_StyleScopedClasses['success']} */ ;
/** @type {__VLS_StyleScopedClasses['stat']} */ ;
/** @type {__VLS_StyleScopedClasses['failed']} */ ;
/** @type {__VLS_StyleScopedClasses['main-grid']} */ ;
/** @type {__VLS_StyleScopedClasses['dag-area']} */ ;
/** @type {__VLS_StyleScopedClasses['side-area']} */ ;
var __VLS_dollars;
const __VLS_self = (await import('vue')).defineComponent({
    setup() {
        return {
            DAGCanvas: DAGCanvas,
            LogPanel: LogPanel,
            CircuitBreakerPanel: CircuitBreakerPanel,
            formatTime: formatTime,
            store: store,
            wfName: wfName,
            stats: stats,
            create: create,
            run: run,
            onSelectRun: onSelectRun,
            runStatusLabel: runStatusLabel,
            runStatusColor: runStatusColor,
        };
    },
});
export default (await import('vue')).defineComponent({
    setup() {
        return {};
    },
});
; /* PartiallyEnd: #4569/main.vue */
