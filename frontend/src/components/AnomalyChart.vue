<template>
  <div class="panel"><h4>📈 异常分数 (3-sigma + IQR)</h4><div ref="chart" class="chart"></div></div>
</template>
<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted } from 'vue'
import * as echarts from 'echarts'
import { useLogStore } from '../store/log'
import { anomalyOption } from './chartOptions'
const store = useLogStore(); const chart = ref<HTMLDivElement>(); let inst: echarts.ECharts|null=null
function update() {
  if (!inst||!store.result) return
  inst.setOption(anomalyOption(store.result.anomalies), true)
}
onMounted(()=>{if(chart.value){inst=echarts.init(chart.value);update()}})
watch(()=>store.result,update)
onUnmounted(()=>inst?.dispose())
</script>
<style scoped>.panel{background:#1e293b;border-radius:8px;padding:12px;border:1px solid #334155}.panel h4{color:#38bdf8;font-size:13px;margin-bottom:4px}.chart{width:100%;height:220px}</style>
