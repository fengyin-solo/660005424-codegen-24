<template>
  <el-dialog :model-value="true" title="登录大屏账号" width="380px" :close-on-click-modal="false"
    :show-close="false" append-to-body>
    <el-alert type="info" :closable="false" style="margin-bottom:12px"
      title="大屏数据按账号授权展示，普通模式无需登录。演示账号：admin/admin123、sre/sre123、guest/guest123"/>
    <el-form @submit.prevent>
      <el-form-item label="账号">
        <el-input v-model="username" placeholder="admin / sre / guest" @keyup.enter="submit"/>
      </el-form-item>
      <el-form-item label="密码">
        <el-input v-model="password" type="password" show-password @keyup.enter="submit"/>
      </el-form-item>
    </el-form>
    <div v-if="err" class="login-err">{{ err }}</div>
    <template #footer>
      <el-button @click="emit('close')">取消</el-button>
      <el-button type="primary" :loading="loading" @click="submit">登录</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useAuthStore } from '@/store/auth'

const emit = defineEmits<{ (e: 'close'): void; (e: 'success'): void }>()
const auth = useAuthStore()
const username = ref('guest')
const password = ref('guest123')
const loading = ref(false)
const err = ref('')

async function submit() {
  if (!username.value || !password.value) { err.value = '请输入账号和密码'; return }
  loading.value = true
  err.value = ''
  try {
    await auth.login(username.value.trim(), password.value)
    emit('success')
  } catch (e: unknown) {
    err.value = (e as { reason?: string }).reason || '登录失败'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-err{color:#f87171;font-size:12px;margin-top:-6px;white-space:pre-wrap}
</style>
