<template>
  <div class="panel" :style="panelStyle">
    <h4>📋 {{ title }} ({{ count }} 条)</h4>
    <div class="table-wrap" :style="wrapStyle">
      <el-table :data="logs" size="small" :max-height="maxHeight" stripe>
        <el-table-column prop="id" label="#" width="50"/>
        <el-table-column prop="timestamp" label="时间" width="150"/>
        <el-table-column prop="level" label="级别" width="70">
          <template #default="{row}"><el-tag size="small" :type="row.level==='ERROR'||row.level==='error'?'danger':row.level==='WARN'||row.level==='warn'?'warning':'info'">{{ row.level }}</el-tag></template>
        </el-table-column>
        <el-table-column prop="source" label="来源" width="120"/>
        <el-table-column prop="message" label="消息" show-overflow-tooltip/>
      </el-table>
    </div>
  </div>
</template>
<script setup lang="ts">
import { computed } from 'vue'
import { useLogStore } from '../store/log'
import type { LogEntry } from '@/types'
const props = withDefaults(defineProps<{
  title?: string
  logs?: LogEntry[] | null
  total?: number | null
  maxHeight?: number
  height?: string
}>(), { title: '日志流', logs: null, total: null, maxHeight: 400, height: '' })
const store = useLogStore()
const logs = computed(() => props.logs ?? store.result?.logs ?? [])
const count = computed(() => props.total ?? store.result?.totalLogs ?? logs.value.length)
const panelStyle = computed(() => props.height ? { height: props.height } : { height: '100%' })
const wrapStyle = computed(() => props.height ? { height: 'calc(100% - 30px)' } : {})
</script>
<style scoped>.panel{background:#1e293b;border-radius:8px;padding:12px;border:1px solid #334155}.panel h4{color:#38bdf8;font-size:13px;margin-bottom:8px}.table-wrap{height:calc(100% - 30px);overflow:auto}</style>
