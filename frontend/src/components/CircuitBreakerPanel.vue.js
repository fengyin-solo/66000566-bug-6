/// <reference types="../../node_modules/.vue-global-types/vue_3.5_0_0_0.d.ts" />
import { computed } from 'vue';
import { useDAGStore } from '../store/dag';
import { breakerDescription } from '../constants';
const store = useDAGStore();
const nodes = computed(() => store.execution?.workflow.nodes || []);
const breakers = computed(() => store.execution?.circuitBreakers || []);
function cbOf(id) {
    return breakers.value.find(b => b.taskId === id);
}
// 与执行明细面板调用同一个函数，两个入口对同一环节的说法必然一致
function desc(n) {
    return breakerDescription(n, cbOf(n.id), store.now);
}
debugger; /* PartiallyEnd: #3632/scriptSetup.vue */
const __VLS_ctx = {};
let __VLS_components;
let __VLS_directives;
/** @type {__VLS_StyleScopedClasses['panel']} */ ;
// CSS variable injection 
// CSS variable injection end 
__VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
    ...{ class: "panel" },
});
__VLS_asFunctionalElement(__VLS_intrinsicElements.h4, __VLS_intrinsicElements.h4)({});
for (const [n] of __VLS_getVForSourceType((__VLS_ctx.nodes))) {
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        key: (n.id),
        ...{ class: "cb-row" },
        ...{ style: ({ borderLeftColor: __VLS_ctx.desc(n).color }) },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "cb-main" },
    });
    __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
        ...{ class: "cb-task" },
    });
    (n.name);
    __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
        ...{ class: "cb-state" },
        ...{ style: ({ color: __VLS_ctx.desc(n).color }) },
    });
    (__VLS_ctx.desc(n).label);
    __VLS_asFunctionalElement(__VLS_intrinsicElements.span, __VLS_intrinsicElements.span)({
        ...{ class: "cb-detail" },
    });
    (__VLS_ctx.desc(n).detail);
}
if (!__VLS_ctx.nodes.length) {
    __VLS_asFunctionalElement(__VLS_intrinsicElements.div, __VLS_intrinsicElements.div)({
        ...{ class: "empty" },
    });
}
/** @type {__VLS_StyleScopedClasses['panel']} */ ;
/** @type {__VLS_StyleScopedClasses['cb-row']} */ ;
/** @type {__VLS_StyleScopedClasses['cb-main']} */ ;
/** @type {__VLS_StyleScopedClasses['cb-task']} */ ;
/** @type {__VLS_StyleScopedClasses['cb-state']} */ ;
/** @type {__VLS_StyleScopedClasses['cb-detail']} */ ;
/** @type {__VLS_StyleScopedClasses['empty']} */ ;
var __VLS_dollars;
const __VLS_self = (await import('vue')).defineComponent({
    setup() {
        return {
            nodes: nodes,
            desc: desc,
        };
    },
});
export default (await import('vue')).defineComponent({
    setup() {
        return {};
    },
});
; /* PartiallyEnd: #4569/main.vue */
