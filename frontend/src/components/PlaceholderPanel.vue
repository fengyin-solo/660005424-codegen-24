<template>
  <div class="panel placeholder-panel">
    <h4>{{ title }}</h4>
    <div class="placeholder-body">
      <div class="lock">🔒</div>
      <div class="ph-title">{{ reason || '该模块未授权' }}</div>
      <div class="ph-desc">
        <template v-if="missingSources?.length">
          未授权数据来源：<span class="ph-items">{{ missingSources.join('、') }}</span><br/>
        </template>
        <template v-if="missingLevels?.length">
          未授权日志级别：<span class="ph-items">{{ missingLevels.join('、') }}</span><br/>
        </template>
        {{ hint || '当前账号在大屏口径下不可见此部分数据，故以占位说明代替，不展示任何数值。' }}
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  title: string
  reason?: string
  missingSources?: string[]
  missingLevels?: string[]
  hint?: string
}>()
</script>

<style scoped>
.placeholder-panel{background:#1e293b;border-radius:8px;padding:12px;border:1px dashed #475569;display:flex;flex-direction:column}
.placeholder-panel h4{color:#94a3b8;font-size:13px;margin-bottom:4px}
.placeholder-body{flex:1;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:6px;text-align:center;padding:12px 8px}
.lock{font-size:28px;opacity:.75}
.ph-title{color:#cbd5e1;font-size:13px;font-weight:600}
.ph-desc{color:#7c8aa0;font-size:11px;line-height:1.7;max-width:420px}
.ph-items{color:#fca5a5}
</style>
