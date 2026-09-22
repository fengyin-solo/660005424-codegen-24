<template>
  <div class="screen-root">
    <header class="screen-header">
      <div class="h-left">
        <span class="live-dot"></span>
        <h2>📊 分布式日志聚合与智能异常检测平台 · 数据大屏</h2>
      </div>
      <div class="h-right">
        <el-select :model-value="store.logType" size="small" style="width:130px"
          @change="(v: string) => store.changeType(v)">
          <el-option v-for="t in ['nginx','apache','json_app','custom']" :key="t" :label="t" :value="t"/>
        </el-select>
        <span class="meta">账号：{{ data?.account.name }}（{{ data?.account.username }}）</span>
        <span class="meta version">授权口径 v{{ data?.scope.version }}</span>
        <span class="meta">更新于 {{ store.lastUpdated }}</span>
        <el-button size="small" :loading="store.loading" @click="store.load()">🔄 刷新</el-button>
        <el-button size="small" type="primary" plain @click="store.close()">退出大屏</el-button>
      </div>
    </header>

    <!-- 数据源授权口径：已授权正常展示，未授权以占位标签代替（不留空） -->
    <section class="source-bar" v-if="data">
      <span class="sb-label">数据源授权：</span>
      <el-tag v-for="s in data.sources.granted" :key="s" size="small" type="success"
        effect="dark" class="sb-tag">✓ {{ s }}</el-tag>
      <span v-for="s in data.sources.denied" :key="s" class="sb-denied" title="该数据源未授权，数据已隐藏">
        🔒 {{ s }}<em>·未授权</em>
      </span>
    </section>

    <div v-if="store.error" class="screen-error">
      <div class="err-icon">⛔</div>
      <pre class="err-text">{{ store.error }}</pre>
      <div class="err-actions">
        <el-button size="small" type="primary" @click="store.load()">重新加载</el-button>
        <el-button size="small" @click="store.close()">返回普通模式</el-button>
      </div>
    </div>

    <main v-else-if="data" class="screen-grid">
      <ScreenPanel
        v-for="p in data.panels"
        :key="p.panel"
        :panel="p"
        :class="['cell-' + p.panel]"
      />
    </main>

    <div v-else class="screen-loading">
      <el-icon class="is-loading" :size="32"><Loading /></el-icon>
      <div>正在按授权口径加载大屏数据…</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Loading } from '@element-plus/icons-vue'
import { useScreenStore } from '@/store/screen'
import ScreenPanel from './ScreenPanel.vue'

const store = useScreenStore()
const data = computed(() => store.data)
</script>

<style scoped>
.screen-root{position:fixed;inset:0;z-index:2000;background:radial-gradient(1200px 700px at 20% -10%,#0b2540 0%,#0f172a 55%,#0a0f1e 100%);
  display:flex;flex-direction:column;padding:14px 18px;color:#e2e8f0;overflow:hidden}
.screen-header{display:flex;justify-content:space-between;align-items:center;flex:none;
  padding-bottom:10px;border-bottom:1px solid #1e3a5f}
.h-left{display:flex;align-items:center;gap:12px}
.h-left h2{font-size:20px;color:#7dd3fc;letter-spacing:2px;font-weight:700}
.live-dot{width:10px;height:10px;border-radius:50%;background:#22c55e;box-shadow:0 0 10px #22c55e;animation:pulse 1.6s infinite}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.35}}
.h-right{display:flex;align-items:center;gap:12px}
.meta{font-size:12px;color:#94a3b8}
.meta.version{color:#fbbf24;font-weight:700}
.source-bar{display:flex;flex:none;flex-wrap:wrap;align-items:center;gap:8px;padding:10px 2px;min-height:42px}
.sb-label{font-size:12px;color:#94a3b8}
.sb-tag{font-size:11px}
.sb-denied{font-size:11px;color:#64748b;background:#1e293b88;border:1px dashed #475569;border-radius:4px;
  padding:2px 8px;white-space:nowrap}
.sb-denied em{font-style:normal;margin-left:4px;color:#94a3b8}

/* 大屏独立网格：kpi 顶栏，下面三块图表，底部告警 + 日志 */
.screen-grid{flex:1;min-height:0;display:grid;gap:12px;
  grid-template-columns:1fr 1fr 1fr;
  grid-template-rows:auto minmax(0,1fr) minmax(0,1.15fr);
  grid-template-areas:
    "kpi kpi kpi"
    "trend heatmap anomaly"
    "alerts logs logs";
}
.cell-kpi{grid-area:kpi}
.cell-trend{grid-area:trend}
.cell-heatmap{grid-area:heatmap}
.cell-anomaly{grid-area:anomaly}
.cell-alerts{grid-area:alerts}
.cell-logs{grid-area:logs}
.cell-kpi :deep(.panel-body){flex-direction:row;align-items:center;gap:26px;flex-wrap:wrap}
.cell-kpi :deep(.kpi-sources){margin-top:0}

.screen-error{flex:1;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:14px}
.err-icon{font-size:44px}
.err-text{color:#fca5a5;font-size:13px;white-space:pre-wrap;text-align:center;max-width:720px;line-height:1.7;
  background:#450a0a33;border:1px solid #7f1d1d;padding:14px 18px;border-radius:8px;font-family:inherit}
.err-actions{display:flex;gap:10px}
.screen-loading{flex:1;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:12px;color:#94a3b8}
</style>
