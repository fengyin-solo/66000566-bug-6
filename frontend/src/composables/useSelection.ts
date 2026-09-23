import { ref } from 'vue'

/** 当前在明细面板中查看的环节 id，DAG 画布与熔断面板均可选中。 */
export const selectedNodeId = ref<string | null>(null)
