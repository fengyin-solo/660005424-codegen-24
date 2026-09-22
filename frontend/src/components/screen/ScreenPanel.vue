<template>
  <div class="screen-panel" :class="{ 'is-denied': panel.status === 'denied' }">
    <h4 class="panel-title">{{ panel.title }}</h4>
    <DenyPlaceholder v-if="panel.status === 'denied'" :reason="panel.denyReason || '未授权'" />
    <div v-else class="panel-body">
      <!-- KPI：总日志量 + 已授权数据源 -->
      <template v-if="panel.panel === 'kpi'">
        <div class="kpi-value">{{ kpi?.value ?? 0 }}</div>
        <div class="kpi-label">已授权日志总数（按授权数据源统计）</div>
        <div class="kpi-sources">
          <el-tag v-for="s in kpi?.grantedSources || []" :key="s" size="small"
            type="success" effect="dark" class="src-tag">{{ s }}</el-tag>
        </div>
      </template>

      <ScreenChart v-else-if="panel.panel === 'trend'" :option="trendOpt" />
      <ScreenChart v-else-if="panel.panel === 'heatmap'" :option="heatmapOpt" />
      <ScreenChart v-else-if="panel.panel === 'anomaly'" :option="anomalyOpt" />

      <template v-else-if="panel.panel === 'alerts'">
        <div v-if="!alerts.length" class="body-empty">暂无告警</div>
        <div v-for="a in alerts.slice(0, 12)" :key="a.id" class="alert-row" :class="a.severity">
          <span class="a-sev" :class="a.severity">{{ a.severity.toUpperCase() }}</span>
          <span class="a-msg">{{ a.message }}</span>
        </div>
      </template>

      <template v-else-if="panel.panel === 'logs'">
        <el-table :data="logs" size="small" max-height="100%" stripe class="screen-table">
          <el-table-column prop="id" label="#" width="50"/>
          <el-table-column prop="timestamp" label="时间" width="150"/>
          <el-table-column prop="level" label="级别" width="70">
            <template #default="{ row }">
              <el-tag size="small" :type="row.level==='ERROR'||row.level==='error'?'danger':row.level==='WARN'||row.level==='warn'?'warning':'info'">{{ row.level }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="source" label="来源" width="120"/>
          <el-table-column prop="message" label="消息" show-overflow-tooltip/>
        </el-table>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { ScreenPanel } from '@/types'
import type { AnomalyScore, Alert, LogEntry, TimeWindow } from '@/types'
import DenyPlaceholder from './DenyPlaceholder.vue'
import ScreenChart from './ScreenChart.vue'
import { anomalyOption, heatmapOption, trendOption } from '../chartOptions'

const props = defineProps<{ panel: ScreenPanel }>()
const d = computed(() => props.panel.data || {})

const kpi = computed(() => d.value as { value: number; grantedSources: string[] } | undefined)
const trendOpt = computed(() => trendOption((d.value.windows || []) as TimeWindow[]))
const heatmapOpt = computed(() => heatmapOption((d.value.windows || []) as TimeWindow[]))
const anomalyOpt = computed(() => anomalyOption((d.value.anomalies || []) as AnomalyScore[]))
const alerts = computed(() => (d.value.alerts || []) as Alert[])
const logs = computed(() => (d.value.logs || []) as LogEntry[])
</script>

<style scoped>
.screen-panel{background:rgba(30,41,59,.85);border:1px solid #334155;border-radius:10px;
  padding:14px;display:flex;flex-direction:column;min-height:0;min-width:0;backdrop-filter:blur(4px)}
.screen-panel.is-denied{border-style:dashed}
.panel-title{color:#38bdf8;font-size:15px;margin-bottom:10px;letter-spacing:1px;flex:none}
.panel-body{flex:1;min-height:0;display:flex;flex-direction:column}
.body-empty{color:#64748b;font-size:13px}
.kpi-value{font-size:46px;font-weight:800;color:#38bdf8;line-height:1.1;text-shadow:0 0 18px rgba(56,189,248,.45)}
.kpi-label{color:#94a3b8;font-size:12px;margin-top:6px}
.kpi-sources{margin-top:12px;display:flex;flex-wrap:wrap;gap:6px;overflow:auto}
.src-tag{font-size:11px}
.alert-row{display:flex;gap:8px;padding:5px 8px;margin:3px 0;border-radius:4px;font-size:12px;align-items:flex-start}
.alert-row.high{background:#7f1d1d33}
.alert-row.critical{background:#991b1b55}
.alert-row.medium{background:#78350f33}
.a-sev{font-weight:700;min-width:54px;font-size:10px;padding:1px 4px;border-radius:2px;text-align:center}
.a-sev.critical{color:#fca5a5;background:#991b1b}
.a-sev.high{color:#f87171;background:#7f1d1d}
.a-sev.medium{color:#fbbf24;background:#78350f}
.a-msg{color:#e2e8f0}
:deep(.screen-table){background:transparent;flex:1;min-height:0}
:deep(.screen-table .el-table__inner-wrapper){background:transparent}
</style>
