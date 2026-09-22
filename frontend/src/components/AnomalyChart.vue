<template>
  <div class="panel"><h4>{{ title }}</h4><div ref="chart" class="chart"></div></div>
</template>
<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted } from 'vue'
import * as echarts from 'echarts'
import { useLogStore } from '../store/log'
import type { AnomalyScore } from '@/types'
const props = withDefaults(defineProps<{
  title?: string
  anomalies?: AnomalyScore[] | null
  height?: string
}>(), { title: '📈 异常分数 (3-sigma + IQR)', anomalies: null, height: '220px' })
const store = useLogStore(); const chart = ref<HTMLDivElement>(); let inst: echarts.ECharts|null=null
function update() {
  if (!inst) return
  const anoms = props.anomalies ?? store.result?.anomalies
  if (!anoms) return
  inst.setOption({
    backgroundColor:'transparent',grid:{left:40,right:15,top:10,bottom:25},
    xAxis:{type:'category',data:anoms.map(a=>'W'+a.windowIndex),axisLabel:{color:'#94a3b8',fontSize:9}},
    yAxis:{type:'value',axisLabel:{color:'#94a3b8'}},
    series:[
      {type:'line',data:anoms.map(a=>a.sigmaScore),name:'3-sigma',itemStyle:{color:'#f97316'},lineStyle:{width:1.5}},
      {type:'line',data:anoms.map(a=>a.iqrScore),name:'IQR',itemStyle:{color:'#a78bfa'},lineStyle:{width:1.5}}
    ],animation:false,legend:{right:0,textStyle:{color:'#94a3b8',fontSize:10}}
  }, true)
}
function resize(){ inst?.resize() }
onMounted(()=>{if(chart.value){inst=echarts.init(chart.value);update();window.addEventListener('resize',resize)}})
watch(()=>store.result,update)
watch(()=>props.anomalies,update)
onUnmounted(()=>{window.removeEventListener('resize',resize);inst?.dispose()})
</script>
<style scoped>.panel{background:#1e293b;border-radius:8px;padding:12px;border:1px solid #334155}.panel h4{color:#38bdf8;font-size:13px;margin-bottom:4px}.chart{width:100%;height:v-bind(height)}</style>
