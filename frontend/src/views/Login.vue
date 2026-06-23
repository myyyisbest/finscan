<template>
  <div class="login-page">
    <div class="login-card">
      <div class="login-header">
        <h1 class="login-title">FinScan</h1>
        <p class="login-subtitle">上市公司财务分析工具</p>
      </div>
      <a-form :model="form" @finish="handleLogin" layout="vertical">
        <a-form-item name="username" label="用户名" :rules="[{ required: true, message: '请输入用户名' }]">
          <a-input v-model:value="form.username" placeholder="请输入用户名" size="large" />
        </a-form-item>
        <a-form-item name="password" label="密码" :rules="[{ required: true, message: '请输入密码' }]">
          <a-input-password v-model:value="form.password" placeholder="请输入密码" size="large" @keyup.enter="handleLogin" />
        </a-form-item>
        <a-form-item>
          <a-button type="primary" html-type="submit" size="large" block :loading="loading">
            登录
          </a-button>
        </a-form-item>
      </a-form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()
const loading = ref(false)

const form = reactive({
  username: '',
  password: ''
})

async function handleLogin() {
  loading.value = true
  try {
    const ok = await authStore.login(form.username, form.password)
    if (ok) {
      message.success('登录成功')
      router.push('/')
    } else {
      message.error('用户名或密码错误')
    }
  } catch (e) {
    message.error('登录失败')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #1e3a8a 0%, #1d4ed8 50%, #3b82f6 100%);
}

.login-card {
  width: 400px;
  background: #fff;
  padding: 40px;
  border-radius: 12px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
}

.login-header {
  text-align: center;
  margin-bottom: 32px;
}

.login-title {
  font-size: 32px;
  font-weight: 700;
  color: #1d4ed8;
  margin: 0 0 8px;
  letter-spacing: 2px;
}

.login-subtitle {
  color: #666;
  font-size: 14px;
  margin: 0;
}
</style>
