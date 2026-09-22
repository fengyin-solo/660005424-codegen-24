<template>
  <div class="app-root">
    <header class="top-bar">
      <h1>📊 分布式日志聚合与智能异常检测平台</h1>
      <div class="toolbar">
        <el-select v-model="store.logType" size="small" style="width:140px">
          <el-option v-for="t in ['nginx','apache','json_app','custom']" :key="t" :label="t" :value="t"/>
        </el-select>
        <el-input v-model="store.searchQuery" placeholder="搜索关键词..." size="small" style="width:200px" clearable/>
        <el-button size="small" @click="store.generate()" :loading="store.loading">🔍 生成日志</el-button>
        <el-button size="small" type="warning" @click="store.detect()" :disabled="!store.result">⚠ 检测异常</el-button>
        <el-divider direction="vertical"/>
        <template v-if="auth.account">
          <span class="account-chip" :title="'授权口径 v' + (auth.account.scope?.version ?? '-')">
            👤 {{ auth.account.name }}
            <el-tag v-if="auth.account.isAdmin" size="small" type="danger" effect="plain">管理员</el-tag>
            <el-tag v-else size="small" :type="auth.account.scope?.enabled ? 'success' : 'info'">
              {{ auth.account.scope?.enabled ? `大屏v${auth.account.scope.version}` : '大屏未启用' }}
            </el-tag>
          </span>
          <el-button v-if="auth.account.isAdmin" size="small" type="danger" plain @click="showPerm = true">🔐 数据授权</el-button>
          <el-button size="small" type="primary" @click="openScreen">🖥 大屏模式</el-button>
          <el-button size="small" @click="onLogout">退出登录</el-button>
        </template>
        <el-button v-else size="small" type="primary" plain @click="showLogin = true">登录 / 大屏</el-button>
      </div>
    </header>
    <div class="main-grid">
      <div class="grid-col">
        <LogTable />
      </div>
      <div class="grid-col">
        <AnomalyChart />
        <AlertPanel />
      </div>
    </div>
    <div class="bottom-row">
      <TrendChart />
      <HeatmapChart />
    </div>

    <LoginDialog v-if="showLogin" @close="showLogin = false" @success="onLoginSuccess"/>
    <PermissionManager v-if="showPerm" @close="showPerm = false" @published="onScopePublished"/>
    <!-- 大屏为独立全屏覆盖层，不改动普通模式面板布局；退出即恢复 -->
    <ScreenView v-if="screen.active"/>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import LogTable from './components/LogTable.vue'
import AnomalyChart from './components/AnomalyChart.vue'
import AlertPanel from './components/AlertPanel.vue'
import TrendChart from './components/TrendChart.vue'
import HeatmapChart from './components/HeatmapChart.vue'
import LoginDialog from './components/LoginDialog.vue'
import PermissionManager from './components/PermissionManager.vue'
import ScreenView from './components/screen/ScreenView.vue'
import { useLogStore } from './store/log'
import { useAuthStore } from './store/auth'
import { useScreenStore } from './store/screen'

const store = useLogStore()
const auth = useAuthStore()
const screen = useScreenStore()
const showLogin = ref(false)
const showPerm = ref(false)

onMounted(() => { void auth.restore() })

async function onLoginSuccess() {
  showLogin.value = false
  ElMessage.success(`欢迎，${auth.account?.name}`)
}

function onLogout() {
  if (screen.active) screen.close()
  auth.logout()
  ElMessage.info('已退出登录（普通模式不受影响）')
}

async function openScreen() {
  if (!auth.account) { showLogin.value = true; return }
  if (!auth.account.scope?.enabled) {
    ElMessage.warning('当前账号的大屏数据权限尚未启用，请联系管理员配置并成功发布授权清单')
    return
  }
  try {
    await screen.open(store.logType)
  } catch {
    /* 拒绝原因已在大屏内展示，这里不弹重复提示 */
  }
}

async function onScopePublished() {
  await auth.refreshMe()
  ElMessage.success('授权清单已发布，已通知各大屏窗口切换到最新口径')
}
</script>

<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:system-ui,monospace;background:#0f172a;color:#e2e8f0}
.app-root{min-height:100vh}
.top-bar{display:flex;justify-content:space-between;align-items:center;padding:10px 20px;background:#1e293b;border-bottom:1px solid #334155}
.top-bar h1{font-size:1.1rem;color:#38bdf8}
.toolbar{display:flex;gap:8px;align-items:center}
.account-chip{display:inline-flex;align-items:center;gap:6px;font-size:12px;color:#cbd5e1}
.main-grid{display:grid;grid-template-columns:1fr 400px;gap:12px;padding:12px 20px;min-height:50vh}
.grid-col{overflow:hidden}
.bottom-row{display:grid;grid-template-columns:1fr 1fr;gap:12px;padding:0 20px 16px}
</style>
