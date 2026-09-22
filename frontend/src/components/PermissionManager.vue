<template>
  <el-dialog title="大屏数据权限管理（授权清单）" width="860px" append-to-body
    :model-value="true" @close="emit('close')">
    <div v-loading="loading">
      <div class="pm-toolbar">
        <span>选择账号：</span>
        <el-select v-model="target" size="small" style="width:220px" @change="onAccount">
          <el-option v-for="u in accounts" :key="u" :label="accountLabel(u)" :value="u"/>
        </el-select>
        <el-tag v-if="current" size="small" :type="current.enabled ? 'success' : 'info'">
          {{ current.enabled ? `已启用 · v${current.version}` : `已停用 · v${current.version}` }}
        </el-tag>
        <div class="pm-spacer"></div>
        <el-button size="small" @click="addRow" :disabled="!target">＋ 添加授权项</el-button>
        <el-button size="small" type="warning" plain @click="disable" :disabled="!target || !current?.enabled">停用</el-button>
        <el-button size="small" type="primary" :loading="saving" @click="publish" :disabled="!target">校验并启用</el-button>
      </div>

      <el-alert v-if="publishMsg" :type="publishOk ? 'success' : 'error'" :closable="false"
        class="pm-alert" :title="publishMsg"/>

      <table class="pm-table" v-if="target">
        <thead>
          <tr><th style="width:60px">类型</th><th>资源</th><th style="width:110px">动作</th><th style="width:70px">操作</th></tr>
        </thead>
        <tbody>
          <tr v-for="(row, i) in rows" :key="i" :class="{ invalid: rowErrors[i].length }">
            <td>
              <el-select v-model="row.kind" size="small" @change="row.resource = ''">
                <el-option label="数据源" value="source"/>
                <el-option label="面板" value="panel"/>
              </el-select>
            </td>
            <td>
              <el-select v-model="row.resource" size="small" filterable style="width:100%">
                <el-option :label="kindLabel(row.kind) + '：全部 (*)'" :value="row.kind === 'source' ? 'source:*' : 'panel:*'"/>
                <el-option v-for="r in optionsOf(row.kind)" :key="r" :label="kindLabel(row.kind) + '：' + r" :value="r"/>
              </el-select>
              <div v-if="rowErrors[i].length" class="row-err">
                <div v-for="(msg, k) in rowErrors[i]" :key="k">· {{ msg }}</div>
              </div>
            </td>
            <td>
              <el-select v-model="row.effect" size="small">
                <el-option label="允许 allow" value="allow"/>
                <el-option label="拒绝 deny" value="deny"/>
              </el-select>
            </td>
            <td><el-button size="small" text type="danger" @click="rows.splice(i,1)">删除</el-button></td>
          </tr>
          <tr v-if="!rows.length"><td colspan="4" class="pm-empty">授权清单为空 —— 此状态不允许启用，请至少添加 1 个数据源与 1 个面板</td></tr>
        </tbody>
      </table>

      <div class="pm-preview" v-if="target">
        <span class="pp-title">数据源（{{ preview.sources.length }} 个）：</span>
        <el-tag v-for="s in preview.sources" :key="s" size="small" type="success" effect="plain" class="pp-tag">{{ s }}</el-tag>
        <span v-if="!preview.sources.length" class="pp-none">无任何数据源</span>
        <span class="pp-title pp-gap">面板（{{ preview.panels.length }} 个）：</span>
        <el-tag v-for="p in preview.panels" :key="p" size="small" type="warning" effect="plain" class="pp-tag">{{ p }}</el-tag>
        <span v-if="!preview.panels.length" class="pp-none">无任何面板</span>
      </div>
    </div>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessageBox } from 'element-plus'
import { fetchAllScopes, publishScope, setScopeEnabled } from '@/api'
import type { Scope } from '@/types'

const emit = defineEmits<{ (e: 'close'): void; (e: 'published'): void }>()

const accounts = ref<string[]>([])
const scopes = ref<Record<string, Scope>>({})
const catalog = ref<{ sources: string[]; panels: string[] }>({ sources: [], panels: [] })
const target = ref('')
const loading = ref(false)
const saving = ref(false)
const publishMsg = ref('')
const publishOk = ref(false)

interface Row { kind: 'source' | 'panel'; resource: string; effect: 'allow' | 'deny' }
const rows = ref<Row[]>([])

function kindLabel(kind: string) { return kind === 'source' ? '数据源' : '面板' }
function optionsOf(kind: string) { return kind === 'source' ? catalog.value.sources : catalog.value.panels }
function accountLabel(u: string) {
  const s = scopes.value[u]
  return u + (s ? `（v${s.version}·${s.enabled ? '启用' : '停用'}）` : '（未配置）')
}

const current = computed(() => (target.value ? scopes.value[target.value] : undefined))

async function load() {
  loading.value = true
  try {
    const d = await fetchAllScopes()
    accounts.value = d.accounts
    scopes.value = d.scopes
    catalog.value = d.resourceCatalog
    if (!target.value && d.accounts.length) { target.value = d.accounts[0]; onAccount() }
  } finally { loading.value = false }
}
onMounted(load)

function onAccount() {
  publishMsg.value = ''
  const s = scopes.value[target.value]
  rows.value = s ? s.entries.map(e => ({
    kind: e.resource.startsWith('panel') ? 'panel' : 'source',
    resource: e.resource, effect: e.effect,
  })) : []
}

function addRow() { rows.value.push({ kind: 'source', resource: '', effect: 'allow' }) }

// 前端即时校验（与后端规则保持一致），行内标出不合格项
const rowErrors = computed<string[][]>(() => {
  const seen = new Set<string>()
  const byRes = new Map<string, Set<string>>()
  return rows.value.map((r) => {
    const errs: string[] = []
    if (!r.resource) errs.push('请选择资源')
    if (r.resource) {
      const key = `${r.resource}|${r.effect}`
      if (seen.has(key)) errs.push('与另一条完全重复')
      seen.add(key)
      if (!byRes.has(r.resource)) byRes.set(r.resource, new Set())
      byRes.get(r.resource)!.add(r.effect)
      if (byRes.get(r.resource)!.size === 2) errs.push('该资源同时 allow / deny，冲突')
    }
    return errs
  })
})

const preview = computed(() => {
  let sources = new Set<string>()
  let panels = new Set<string>()
  const denyS = new Set<string>(), denyP = new Set<string>()
  for (const r of rows.value) {
    if (!r.resource) continue
    if (r.resource === 'source:*') {
      (r.effect === 'allow' ? sources : denyS)
      if (r.effect === 'allow') catalog.value.sources.forEach(s => sources.add(s))
      else catalog.value.sources.forEach(s => denyS.add(s))
    } else if (r.resource === 'panel:*') {
      if (r.effect === 'allow') catalog.value.panels.forEach(p => panels.add(p))
      else catalog.value.panels.forEach(p => denyP.add(p))
    } else if (r.kind === 'source') {
      (r.effect === 'allow' ? sources : denyS).add(r.resource)
    } else {
      (r.effect === 'allow' ? panels : denyP).add(r.resource)
    }
  }
  sources = new Set([...sources].filter(s => !denyS.has(s)))
  panels = new Set([...panels].filter(p => !denyP.has(p)))
  return { sources: [...sources].sort(), panels: [...panels].sort() }
})

async function publish() {
  saving.value = true
  publishMsg.value = ''
  try {
    const entries = rows.value
      .filter(r => r.resource)
      .map(r => ({ resource: r.resource, effect: r.effect }))
    const { message, scope } = await publishScope(target.value, entries, current.value?.version)
    publishOk.value = true
    scopes.value[target.value] = scope
    onAccount()
    // onAccount 会清空提示，成功文案在其之后设置
    publishMsg.value = '✅ ' + message
    emit('published')
  } catch (e: unknown) {
    publishOk.value = false
    publishMsg.value = '⛔ ' + ((e as { reason?: string }).reason || '启用失败')
  } finally { saving.value = false }
}

async function disable() {
  try {
    await ElMessageBox.confirm(`确认停用账号 ${target.value} 的大屏数据权限？停用后该账号打开大屏将被拒绝。`,
      '停用确认', { type: 'warning' })
    const d = await setScopeEnabled(target.value, false)
    scopes.value[target.value] = d.scope
    publishOk.value = true
    publishMsg.value = `✅ 账号 ${target.value} 的大屏权限已停用`
    onAccount()
  } catch { /* 取消或失败 */ }
}
</script>

<style scoped>
.pm-toolbar{display:flex;align-items:center;gap:10px;margin-bottom:10px}
.pm-spacer{flex:1}
.pm-alert{margin-bottom:10px;white-space:pre-wrap}
.pm-table{width:100%;border-collapse:collapse;font-size:12px}
.pm-table th{text-align:left;color:#94a3b8;font-weight:600;padding:6px 8px;border-bottom:1px solid #334155}
.pm-table td{padding:6px 8px;border-bottom:1px solid #1e293b;vertical-align:top}
.pm-table tr.invalid{background:#7f1d1d22}
.row-err{color:#f87171;font-size:11px;margin-top:2px;line-height:1.4}
.pm-empty{text-align:center;color:#f87171;padding:18px}
.pm-preview{margin-top:12px;display:flex;flex-wrap:wrap;gap:6px;align-items:center;font-size:12px}
.pp-title{color:#94a3b8}
.pp-title.pp-gap{margin-left:12px}
.pp-none{color:#f87171}
</style>
