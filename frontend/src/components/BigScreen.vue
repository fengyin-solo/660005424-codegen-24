<template>
  <Teleport to="body">
    <div class="screen-root">
      <!-- 顶部条：账号 / 口径版本 / 授权范围 -->
      <header class="screen-topbar">
        <div class="brand">📊 分布式日志平台 · 数据大屏</div>
        <div class="scope-tags">
          <el-tag size="small" type="info">账号口径</el-tag>
          <el-select v-model="account" size="small" style="width:170px" @change="onAccountChange">
            <el-option v-for="a in store.accounts" :key="a.account"
              :label="`${a.account}（${a.enabled ? 'v'+a.version : '未启用'}）`" :value="a.account"/>
          </el-select>
          <el-tag size="small" :type="meta?.enabled ? 'success' : 'danger'">
            {{ meta?.enabled ? `口径版本 v${store.data?.version ?? meta.version}` : '大屏未启用' }}
          </el-tag>
          <el-tag size="small" type="warning" v-if="store.data">
            来源 {{ store.data.scope.sources.length }} 项 · 级别 {{ store.data.scope.levels.join('/') }}
          </el-tag>
        </div>
        <div class="actions">
          <el-button size="small" @click="permVisible = true">🔑 授权管理</el-button>
          <el-button size="small" type="primary" @click="refresh">🔄 刷新口径</el-button>
          <el-button size="small" type="danger" plain @click="emit('exit')">⏏ 退出大屏</el-button>
        </div>
      </header>

      <!-- 未启用 / 被拒：整块占位说明，不渲染任何数值面板 -->
      <div v-if="!store.data" class="screen-body">
        <div class="denied-box">
          <div class="denied-icon">🔒</div>
          <div class="denied-title">{{ store.error?.code === 'screen_disabled' ? '该账号的大屏未启用' : '大屏数据不可用' }}</div>
          <div class="denied-msg">{{ store.error?.message || '尚未选择账号或数据加载中' }}</div>
          <div v-if="store.loading" class="denied-sub">正在加载…</div>
          <div class="denied-actions">
            <el-button size="small" @click="permVisible = true">前往授权管理</el-button>
            <el-button size="small" type="primary" @click="refresh">重试</el-button>
            <el-button size="small" @click="emit('exit')">返回普通模式</el-button>
          </div>
        </div>
      </div>

      <!-- 已授权口径下的大屏内容 -->
      <main v-else class="screen-body">
        <!-- 第一行：核心指标 -->
        <section class="kpi-row">
          <div class="kpi-card"><div class="kpi-label">授权范围日志总量</div><div class="kpi-value">{{ store.data.totalLogs }}</div></div>
          <div class="kpi-card"><div class="kpi-label">统计窗口数</div><div class="kpi-value">{{ store.data.windows.length }}</div></div>
          <div class="kpi-card"><div class="kpi-label">异常窗口</div><div class="kpi-value danger">{{ anomalyCount }}</div></div>
          <div class="kpi-card"><div class="kpi-label">触发告警</div><div class="kpi-value warn">{{ store.data.alerts.length }}</div></div>
          <div class="kpi-card"><div class="kpi-label">口径生成时间</div><div class="kpi-value small">{{ store.data.generatedAt }}</div></div>
        </section>

        <!-- 第二行：数据来源授权矩阵（未授权来源以占位卡代替，不显示 0） -->
        <section class="panel-section">
          <h4 class="section-title">数据来源授权矩阵</h4>
          <div class="source-grid">
            <div v-for="s in store.catalog.sources" :key="s" class="source-cell" :class="{ denied: !sourceAllowed(s) }">
              <template v-if="sourceAllowed(s)">
                <div class="sc-name">{{ s }}</div>
                <div class="sc-count">{{ store.data.sourceCounts[s] ?? 0 }}</div>
                <div class="sc-cap">条 · 已授权</div>
              </template>
              <template v-else>
                <div class="sc-name muted">{{ s }}</div>
                <div class="sc-lock">🔒</div>
                <div class="sc-cap">未授权 · 占位（不显示数值）</div>
              </template>
            </div>
          </div>
        </section>

        <!-- 第三行：趋势 + 级别热力图；未授权级别维度时整块占位 -->
        <section class="chart-row-2">
          <TrendChart :windows="store.data.windows" height="260px"/>
          <template v-if="store.data.scope.levels.length">
            <HeatmapChart :windows="store.data.windows" :levels="store.data.scope.levels" height="260px"/>
          </template>
          <PlaceholderPanel v-else title="🔥 日志级别热力图" reason="日志级别维度未授权"
            :missing-levels="store.catalog.levels" hint="当前账号在任何日志级别上均无授权，热力图以占位说明代替。"/>
        </section>

        <!-- 第四行：异常 / 告警 / 日志流；数据为空时明确区分「授权但无数据」与「未授权」 -->
        <section class="chart-row-3">
          <AnomalyChart :anomalies="store.data.anomalies" height="100%"/>
          <AlertPanel :alerts="store.data.alerts" auto-height/>
          <LogTable :logs="store.data.logs" :total="store.data.totalLogs" :max-height="260" height="100%" title="授权范围日志流"/>
        </section>

        <!-- 未授权级别 KPI 占位带：授权级别之外的级别以文字占位，不出现 0 值 -->
        <section v-if="deniedLevels.length" class="denied-band">
          🔒 以下日志级别未对当前账号授权，大屏不展示其任何取值：
          <span v-for="lv in deniedLevels" :key="lv" class="denied-chip">{{ lv }}</span>
        </section>
      </main>

      <PermissionDialog v-model:visible="permVisible"/>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useScreenStore } from '../store/screen'
import TrendChart from './TrendChart.vue'
import HeatmapChart from './HeatmapChart.vue'
import AnomalyChart from './AnomalyChart.vue'
import AlertPanel from './AlertPanel.vue'
import LogTable from './LogTable.vue'
import PlaceholderPanel from './PlaceholderPanel.vue'
import PermissionDialog from './PermissionDialog.vue'

const emit = defineEmits<{ (e: 'exit'): void }>()
const store = useScreenStore()
const permVisible = ref(false)

const account = ref(store.currentAccount)
const meta = computed(() => store.currentMeta())
const anomalyCount = computed(() => store.data?.anomalies.filter(a => a.isAnomaly).length ?? 0)
const deniedLevels = computed(() => store.catalog.levels.filter(l => !store.data?.scope.levels.includes(l)))
function sourceAllowed(s: string) { return !!store.data?.scope.sources.includes(s) }

async function onAccountChange(v: string) { await store.selectAccount(v) }
async function refresh() {
  await store.loadAccounts()
  await store.loadData()
}

// 多窗口一致性：BroadcastChannel 即时同步 + 定时轮询兜底（版本/启用状态以服务端为准）
let bc: BroadcastChannel | null = null
let timer: number | undefined
function onStorage(e: StorageEvent) {
  if (e.key !== 'screen-permission-state-v1' || !e.newValue) return
  try { void store.handleCrossTab(JSON.parse(e.newValue)) } catch { /* ignore */ }
}
onMounted(async () => {
  await Promise.all([store.loadCatalog(), store.loadAccounts()])
  if (!store.currentAccount) {
    const first = store.accounts[0]?.account
    if (first) await store.selectAccount(first)
    account.value = store.currentAccount
  } else {
    account.value = store.currentAccount
    await store.loadData()
  }
  if (typeof BroadcastChannel !== 'undefined') {
    bc = new BroadcastChannel('log-platform-screen-permission')
    bc.onmessage = (ev) => { void store.handleCrossTab(ev.data) }
  }
  window.addEventListener('storage', onStorage)
  // 轮询服务端状态：其他窗口（或管理员）停用/改版本时，本窗口必须对齐同一取值口径
  timer = window.setInterval(async () => {
    const before = store.data?.version
    await store.loadAccounts()
    const cur = store.currentMeta()
    if (cur && (!cur.enabled || cur.version !== before)) await store.loadData({ silent: true })
  }, 10000)
})
onUnmounted(() => {
  bc?.close(); if (timer) window.clearInterval(timer)
  window.removeEventListener('storage', onStorage)
})
</script>

<style scoped>
.screen-root{position:fixed;inset:0;z-index:2000;background:#0b1220;color:#e2e8f0;display:flex;flex-direction:column;overflow:auto}
.screen-topbar{display:flex;align-items:center;gap:16px;padding:10px 20px;background:#111c33;border-bottom:1px solid #1e3a5f}
.brand{font-size:1.05rem;font-weight:700;color:#38bdf8;white-space:nowrap}
.scope-tags{display:flex;align-items:center;gap:8px;flex:1}
.actions{display:flex;gap:8px}
.screen-body{flex:1;padding:14px 20px;display:flex;flex-direction:column;gap:12px;min-height:0}
.kpi-row{display:grid;grid-template-columns:repeat(5,1fr);gap:12px}
.kpi-card{background:linear-gradient(135deg,#13233f,#0f1b30);border:1px solid #1e3a5f;border-radius:8px;padding:12px 16px}
.kpi-label{color:#8aa0bd;font-size:11px;margin-bottom:6px}
.kpi-value{font-size:26px;font-weight:700;color:#38bdf8;font-variant-numeric:tabular-nums}
.kpi-value.danger{color:#f87171}.kpi-value.warn{color:#fbbf24}.kpi-value.small{font-size:13px;line-height:28px}
.panel-section{background:#1e293b;border:1px solid #334155;border-radius:8px;padding:10px 12px}
.section-title{color:#38bdf8;font-size:13px;margin-bottom:8px}
.source-grid{display:grid;grid-template-columns:repeat(7,1fr);gap:8px}
.source-cell{border-radius:6px;padding:8px;text-align:center;border:1px solid #1e3a5f;background:#13233f}
.source-cell.denied{border:1px dashed #475569;background:#172033}
.sc-name{font-size:11px;color:#cbd5e1;font-weight:600}
.sc-name.muted{color:#64748b}
.sc-count{font-size:20px;font-weight:700;color:#7dd3fc;margin:2px 0;font-variant-numeric:tabular-nums}
.sc-cap{font-size:10px;color:#64748b}
.sc-lock{font-size:18px;margin:2px 0}
.chart-row-2{display:grid;grid-template-columns:1fr 1fr;gap:12px}
.chart-row-3{display:grid;grid-template-columns:1fr 1fr 1.1fr;gap:12px;min-height:320px}
.chart-row-3 > *{height:100%}
.denied-band{background:#3b2417;border:1px solid #92400e;color:#fcd34d;border-radius:6px;padding:8px 12px;font-size:12px}
.denied-chip{display:inline-block;margin-left:6px;padding:1px 8px;background:#78350f;border-radius:10px;color:#fde68a}
.denied-box{margin:auto;max-width:560px;text-align:center;background:#1e293b;border:1px dashed #64748b;border-radius:12px;padding:40px}
.denied-icon{font-size:48px}.denied-title{font-size:18px;font-weight:700;color:#fca5a5;margin:10px 0 6px}
.denied-msg{color:#cbd5e1;font-size:13px;line-height:1.7}.denied-sub{color:#94a3b8;font-size:12px;margin-top:8px}
.denied-actions{margin-top:18px;display:flex;gap:8px;justify-content:center}
</style>
