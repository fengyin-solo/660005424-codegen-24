<template>
  <el-dialog :model-value="visible" title="🔑 大屏数据授权管理" width="860px" @update:model-value="(v: boolean) => emit('update:visible', v)" @open="onOpen">
    <div class="dlg">
      <div class="row-bar">
        <el-select v-model="account" size="small" style="width:300px" @change="onAccountChange">
          <el-option v-for="a in store.accounts" :key="a.account"
            :label="`${a.account} · ${a.name}`" :value="a.account"/>
        </el-select>
        <el-tag size="small" :type="meta?.enabled ? 'success' : 'danger'">
          {{ meta?.enabled ? `已启用 · 口径 v${meta.version}` : '未启用' }}
        </el-tag>
        <el-tag size="small" type="info" v-if="meta">更新于 {{ meta.updatedAt }}</el-tag>
      </div>

      <!-- 客户端预检提示（与服务端校验口径一致；最终以后端返回的不合格项为准） -->
      <el-alert v-if="localErrors.length" type="error" :closable="false" show-icon class="alert"
        title="授权清单存在不合格项，此时启用将被后端拒绝：">
        <div v-for="(e, i) in localErrors" :key="i" class="err-line">· {{ e }}</div>
      </el-alert>
      <!-- 服务端返回的启用失败说明 -->
      <el-alert v-if="serverError" type="error" :closable="false" show-icon class="alert"
        :title="serverError.message || '启用失败'">
        <div v-for="(e, i) in serverError.errors || []" :key="i" class="err-line">· {{ e }}</div>
        <div v-if="(serverError.denied||[]).length" class="err-line">
          被拒对象：{{ serverError.denied!.map(d => `${d.dimension}=${d.value}`).join('，') }}
        </div>
      </el-alert>
      <el-alert v-if="successMsg" type="success" :closable="false" show-icon class="alert" :title="successMsg"/>

      <div class="edit-grid">
        <div class="rules-col">
          <div class="col-head">
            <span>授权清单（{{ grants.length }} 条）</span>
            <el-button size="small" @click="addGrant">+ 添加规则</el-button>
          </div>
          <div class="rule-row" v-for="(g, i) in grants" :key="i">
            <el-select v-model="g.dimension" size="small" style="width:100px">
              <el-option label="数据来源" value="source"/>
              <el-option label="日志级别" value="level"/>
            </el-select>
            <el-select v-model="g.value" size="small" style="width:180px" filterable>
              <el-option v-for="v in valuesFor(g.dimension)" :key="v" :label="v" :value="v"/>
            </el-select>
            <el-select v-model="g.action" size="small" style="width:100px">
              <el-option label="✅ 允许" value="allow"/>
              <el-option label="🚫 拒绝" value="deny"/>
            </el-select>
            <el-button size="small" type="danger" plain @click="grants.splice(i,1)">删</el-button>
          </div>
          <div v-if="!grants.length" class="empty-hint">授权清单为空 —— 不允许启用大屏。</div>
        </div>
        <div class="scope-col">
          <div class="col-head">生效口径预览（deny 优先）</div>
          <div class="scope-block">
            <div class="sb-label">可看来源（{{ preview.sources.length }}）</div>
            <div class="chips">
              <el-tag v-for="s in preview.sources" :key="s" size="small" class="chip">{{ s }}</el-tag>
              <span v-if="!preview.sources.length" class="empty-hint">无任何放行来源</span>
            </div>
          </div>
          <div class="scope-block">
            <div class="sb-label">可看级别（{{ preview.levels.length }}）</div>
            <div class="chips">
              <el-tag v-for="l in preview.levels" :key="l" size="small" class="chip">{{ l }}</el-tag>
              <span v-if="!preview.levels.length" class="empty-hint">无任何放行级别</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 越权请求验证：显式索要未授权对象时后端应拒绝并写明原因 -->
      <el-divider content-position="left">越权请求验证（以服务端判定为准）</el-divider>
      <div class="probe-row">
        <el-select v-model="probeSources" multiple collapse-tags size="small" placeholder="选择要请求的来源" style="width:300px">
          <el-option v-for="s in store.catalog.sources" :key="s" :label="s" :value="s"/>
        </el-select>
        <el-select v-model="probeLevels" multiple collapse-tags size="small" placeholder="选择要请求的级别" style="width:240px">
          <el-option v-for="l in store.catalog.levels" :key="l" :label="l" :value="l"/>
        </el-select>
        <el-button size="small" type="warning" @click="runProbe">发起越权测试请求</el-button>
      </div>
      <el-alert v-if="probeResult.ok" type="success" :closable="false" show-icon class="alert"
        :title="`请求通过（v${probeResult.version}）：返回 ${probeResult.totalLogs} 条，均在授权口径内`"/>
      <el-alert v-else-if="probeResult.message" type="error" :closable="false" show-icon class="alert" :title="probeResult.message">
        <div v-if="(probeResult.denied||[]).length" class="err-line">
          被拒对象：{{ probeResult.denied!.map(d => `${d.dimension}=${d.value}`).join('，') }}
        </div>
      </el-alert>
    </div>

    <template #footer>
      <el-button @click="emit('update:visible', false)">关闭</el-button>
      <el-button type="info" plain :disabled="!meta?.enabled" @click="onDisable">停用大屏</el-button>
      <el-button type="primary" @click="onEnable(true)">保存并启用</el-button>
      <el-button @click="onEnable(false)">仅保存草稿（不启用）</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import axios from 'axios'
import { ElMessage } from 'element-plus'
import { useScreenStore } from '../store/screen'
import type { Grant, GrantDimension, ScreenApiError } from '@/types'

const props = defineProps<{ visible: boolean }>()
const emit = defineEmits<{ (e: 'update:visible', v: boolean): void }>()
const store = useScreenStore()

const account = ref('')
const grants = ref<Grant[]>([])
const serverError = ref<ScreenApiError | null>(null)
const successMsg = ref('')
const probeSources = ref<string[]>([])
const probeLevels = ref<string[]>([])
const probeResult = ref<{ ok: boolean; message: string; denied?: {dimension:string;value:string}[]; version?: number; totalLogs?: number }>({ ok: false, message: '' })

const meta = computed(() => store.accounts.find(a => a.account === account.value))

function valuesFor(dim: GrantDimension) {
  return dim === 'source' ? store.catalog.sources : store.catalog.levels
}
function addGrant() {
  grants.value.push({ dimension: 'source', value: valuesFor('source')[0] || '', action: 'allow' })
}
watch(
  () => grants.value.map(g => `${g.dimension}|${g.value}`).join(','),
  () => grants.value.forEach(g => {
    if (!valuesFor(g.dimension).includes(g.value)) g.value = valuesFor(g.dimension)[0] || ''
  })
)

const preview = computed(() => store.effectiveScopeOf(grants.value))

// 与后端 validate_grants 同口径的客户端预检
const localErrors = computed<string[]>(() => {
  const errs: string[] = []
  if (!grants.value.length) errs.push('授权清单为空：至少需要一条 source 放行规则和一条 level 放行规则')
  const seen = new Map<string, number>()
  grants.value.forEach((g, i) => {
    const key = `${g.dimension}|${g.value}`
    if (!valuesFor(g.dimension).includes(g.value)) errs.push(`第${i+1}条：${g.dimension} 对象 ${g.value} 不存在`)
    if (seen.has(key)) errs.push(`第${i+1}条与第${seen.get(key)!+1}条重复授权 ${g.value}；allow/deny 并存即互相冲突`)
    else seen.set(key, i)
  })
  if (grants.value.length && !preview.value.sources.length) errs.push('生效后「数据来源」维度没有任何放行对象')
  if (grants.value.length && !preview.value.levels.length) errs.push('生效后「日志级别」维度没有任何放行对象')
  return errs
})

function onOpen() {
  serverError.value = null; successMsg.value = ''
  if (!store.accounts.length) void store.loadAccounts()
  void store.loadCatalog()
  if (!account.value && store.accounts.length) account.value = store.currentAccount || store.accounts[0].account
  loadGrants()
}
function onAccountChange() { loadGrants(); serverError.value = null; successMsg.value = ''; probeResult.value = { ok: false, message: '' } }
function loadGrants() {
  const m = meta.value
  grants.value = m ? m.grants.map(g => ({ ...g })) : []
}

async function onEnable(enabled: boolean) {
  serverError.value = null; successMsg.value = ''
  try {
    const res = await store.saveConfig(account.value, grants.value, enabled)
    grants.value = meta.value ? meta.value.grants.map(g => ({ ...g })) : grants.value
    ElMessage.success(res.message)
    successMsg.value = res.message
  } catch (e: any) {
    const detail = e?.response?.data?.detail
    serverError.value = detail ?? { code: 'request_failed', message: e?.message || '请求失败' }
    // 启用失败后以后端状态为准（原授权与启用状态不变）
    await store.loadAccounts()
    loadGrants()
    ElMessage.error(serverError.value?.message || '启用失败')
  }
}

async function onDisable() {
  serverError.value = null
  try {
    await store.disable(account.value)
    ElMessage.success('大屏已停用')
    successMsg.value = '大屏已停用'
  } catch (e: any) {
    const detail = e?.response?.data?.detail
    serverError.value = detail ?? { code: 'request_failed', message: e?.message || '停用失败' }
  }
}

async function runProbe() {
  probeResult.value = { ok: false, message: '' }
  try {
    const body: Record<string, unknown> = { account: account.value }
    if (probeSources.value.length) body.sources = probeSources.value
    if (probeLevels.value.length) body.levels = probeLevels.value
    const { data } = await axios.post('/api/screen/data', body)
    probeResult.value = { ok: true, message: '', version: data.version, totalLogs: data.totalLogs }
  } catch (e: any) {
    const d = e?.response?.data?.detail
    probeResult.value = {
      ok: false,
      message: d?.message || e?.message || '请求失败',
      denied: d?.denied,
      version: d?.version,
    }
  }
}
</script>

<style scoped>
.row-bar{display:flex;gap:10px;align-items:center;margin-bottom:10px}
.alert{margin:8px 0}
.err-line{font-size:12px;line-height:1.7}
.edit-grid{display:grid;grid-template-columns:1.2fr 1fr;gap:14px;border:1px solid #334155;border-radius:8px;padding:10px}
.col-head{display:flex;justify-content:space-between;align-items:center;font-size:12px;color:#94a3b8;margin-bottom:8px;font-weight:600}
.rule-row{display:flex;gap:6px;margin:6px 0;align-items:center}
.empty-hint{color:#94a3b8;font-size:12px;padding:6px 2px}
.scope-block{margin-bottom:10px}
.sb-label{font-size:12px;color:#cbd5e1;margin-bottom:4px}
.chips{display:flex;flex-wrap:wrap;gap:4px}
.chip{margin:0}
.probe-row{display:flex;gap:8px;align-items:center;flex-wrap:wrap}
</style>
