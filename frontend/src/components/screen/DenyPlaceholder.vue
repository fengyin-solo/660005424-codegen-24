<template>
  <!-- 未授权占位：不给任何数值/空图表，只展示可读的占位说明 -->
  <div class="deny-placeholder">
    <div class="lock">🔒</div>
    <div class="deny-title">数据未授权</div>
    <div class="deny-reason">{{ reason }}</div>
    <div class="deny-foot">如需查看，请联系管理员在授权清单中开通对应资源</div>
  </div>
</template>

<script setup lang="ts">
defineProps<{ reason: string }>()
</script>

<style scoped>
.deny-placeholder{height:100%;min-height:140px;display:flex;flex-direction:column;align-items:center;justify-content:center;
  gap:6px;background:repeating-linear-gradient(45deg,#1e293b,#1e293b 12px,#1a2536 12px,#1a2536 24px);
  border:1px dashed #475569;border-radius:6px;padding:16px;text-align:center}
.lock{font-size:28px;opacity:.8}
.deny-title{color:#94a3b8;font-size:14px;font-weight:700;letter-spacing:2px}
.deny-reason{color:#cbd5e1;font-size:12px;max-width:320px;line-height:1.5}
.deny-foot{color:#64748b;font-size:11px;margin-top:4px}
</style>
