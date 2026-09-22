<template>
  <div ref="el" class="screen-chart"></div>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, ref, watch } from 'vue'
import * as echarts from 'echarts'

const props = defineProps<{ option: echarts.EChartsCoreOption | null }>()
const el = ref<HTMLDivElement>()
let inst: echarts.ECharts | null = null

function render() {
  if (inst && props.option) inst.setOption(props.option, true)
}
onMounted(() => {
  if (el.value) {
    inst = echarts.init(el.value)
    render()
    window.addEventListener('resize', resize)
  }
})
watch(() => props.option, render)
function resize() { inst?.resize() }
onUnmounted(() => {
  window.removeEventListener('resize', resize)
  inst?.dispose()
  inst = null
})

defineExpose({ resize })
</script>

<style scoped>
.screen-chart{width:100%;height:100%;min-height:0}
</style>
