<template>
  <div class="panel"><h4>{{ title }}</h4><div ref="chart" class="chart"></div></div>
</template>
<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted } from 'vue'
import * as echarts from 'echarts'
import { useLogStore } from '../store/log'
import type { TimeWindow } from '@/types'
const props = withDefaults(defineProps<{
  title?: string
  windows?: TimeWindow[] | null
  /** 大屏模式下仅展示已授权级别；普通模式不传 -> 固定四级，标题/图例保持原样 */
  levels?: string[] | null
  height?: string
}>(), { title: '🔥 日志级别热力图', windows: null, levels: null, height: '200px' })
const store = useLogStore(); const chart = ref<HTMLDivElement>(); let inst: echarts.ECharts|null=null
const DEFAULT_LEVELS = ['INFO','WARN','ERROR','DEBUG']
function update() {
  if (!inst) return
  const ws = props.windows ?? store.result?.windows
  if (!ws) return
  const levels = props.levels ?? DEFAULT_LEVELS
  const data: [number,number,number][] = []
  ws.forEach((w,i) => { levels.forEach((lv,j) => { data.push([i,j,w.levels[lv]||0]) }) })
  inst.setOption({
    backgroundColor:'transparent',grid:{left:60,right:15,top:5,bottom:25},
    xAxis:{type:'category',data:ws.map((_,i)=>'W'+i),axisLabel:{color:'#94a3b8',fontSize:8}},
    yAxis:{type:'category',data:levels,axisLabel:{color:'#94a3b8',fontSize:9}},
    visualMap:{min:0,max:Math.max(...data.map(d=>d[2]),1),inRange:{color:['#1e293b','#fef08a','#ef4444']},calculable:false,show:false},
    series:[{type:'heatmap',data,label:{show:true,fontSize:8,color:'#94a3b8'}}],animation:false
  }, true)
}
function resize(){ inst?.resize() }
onMounted(()=>{if(chart.value){inst=echarts.init(chart.value);update();window.addEventListener('resize',resize)}})
watch(()=>store.result,update)
watch(()=>[props.windows,props.levels],update)
onUnmounted(()=>{window.removeEventListener('resize',resize);inst?.dispose()})
</script>
<style scoped>.panel{background:#1e293b;border-radius:8px;padding:12px;border:1px solid #334155}.panel h4{color:#38bdf8;font-size:13px;margin-bottom:4px}.chart{width:100%;height:v-bind(height)}</style>
