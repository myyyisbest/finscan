<template>
  <div class="login-page">
    <div class="login-bg">
      <div class="bg-shape shape1"></div>
      <div class="bg-shape shape2"></div>
      <div class="bg-shape shape3"></div>
    </div>
    <div class="login-card">
      <div class="login-header">
        <div class="logo-icon">📊</div>
        <h1 class="login-title">FinScan</h1>
        <p class="login-subtitle">上市公司财报排雷分析工具</p>
      </div>

      <!-- 手机版服务器配置 -->
      <div v-if="isCapacitor" class="server-config">
        <div class="config-header" @click="showConfig = !showConfig">
          <span class="config-title">
            <SettingOutlined /> 服务器设置
          </span>
          <span class="config-status" :class="{ ok: apiBaseUrl, error: !apiBaseUrl }">
            {{ apiBaseUrl ? '已配置' : '未配置' }}
          </span>
        </div>
        <div v-show="showConfig" class="config-body">
          <a-input
            v-model:value="serverUrl"
            placeholder="http://服务器IP:8000"
            size="large"
            class="server-input"
          >
            <template #prefix><GlobalOutlined /></template>
          </a-input>
          <a-button
            type="primary"
            size="large"
            block
            class="save-config-btn"
            :loading="configLoading"
            @click="saveServerConfig"
          >
            保存并连接服务器
          </a-button>
          <p class="config-tip">
            💡 请确保手机与后端服务器在同一网络下，格式如：http://192.168.1.100:8000
          </p>
        </div>
      </div>
      
      <div class="divider">
        <span>账号登录</span>
      </div>
      
      <a-form :model="form" @finish="handleLogin" layout="vertical">
        <a-form-item name="username" label="用户名" :rules="[{ required: true, message: '请输入用户名' }]">
          <a-input v-model:value="form.username" placeholder="请输入用户名" size="large">
            <template #prefix><UserOutlined /></template>
          </a-input>
        </a-form-item>
        <a-form-item name="password" label="密码" :rules="[{ required: true, message: '请输入密码' }]">
          <a-input-password v-model:value="form.password" placeholder="请输入密码" size="large" @keyup.enter="handleLogin">
            <template #prefix><LockOutlined /></template>
          </a-input-password>
        </a-form-item>
        <a-form-item>
          <a-button type="primary" html-type="submit" size="large" block :loading="loading">
            登录
          </a-button>
        </a-form-item>
      </a-form>
      
      <div class="divider">
        <span>快捷体验</span>
      </div>
      
      <a-button 
        size="large" 
        block 
        class="guest-btn" 
        :loading="guestLoading"
        @click="handleGuestLogin"
      >
        <template #icon>
          <RocketOutlined />
        </template>
        游客免登录体验
      </a-button>
      
      <div class="tips">
        <p>💡 默认管理员账号：admin / admin123</p>
        <p v-if="isCapacitor" class="tip-mobile">📱 首次使用请先配置服务器地址</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { UserOutlined, LockOutlined, RocketOutlined, SettingOutlined, GlobalOutlined } from '@ant-design/icons-vue'
import { useAuthStore } from '@/stores/auth'
import { updateBaseURL } from '@/api'

const router = useRouter()
const authStore = useAuthStore()
const loading = ref(false)
const guestLoading = ref(false)
const configLoading = ref(false)
const showConfig = ref(false)

const isCapacitor = computed(() => (window as any).Capacitor !== undefined)
const apiBaseUrl = computed(() => localStorage.getItem('api_base_url') || '')
const serverUrl = ref(localStorage.getItem('api_base_url') || '')

const form = reactive({
  username: '',
  password: ''
})

async function saveServerConfig() {
  let url = serverUrl.value.trim()
  if (!url) {
    message.warning('请输入服务器地址')
    return
  }
  if (!url.startsWith('http://') && !url.startsWith('https://')) {
    url = 'http://' + url
  }
  if (url.endsWith('/')) {
    url = url.slice(0, -1)
  }
  
  configLoading.value = true
  try {
    updateBaseURL(url)
    // 测试连接
    const ok = await authStore.loginAsGuest()
    if (ok) {
      message.success('服务器连接成功')
      showConfig.value = false
      router.push('/')
    } else {
      message.error('服务器连接失败，请检查地址是否正确')
    }
  } catch (e: any) {
    message.error('服务器连接失败：' + (e.message || '请检查地址和网络'))
  } finally {
    configLoading.value = false
  }
}

async function handleLogin() {
  if (isCapacitor.value && !apiBaseUrl.value) {
    message.warning('请先配置服务器地址')
    showConfig.value = true
    return
  }
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

async function handleGuestLogin() {
  if (isCapacitor.value && !apiBaseUrl.value) {
    message.warning('请先配置服务器地址')
    showConfig.value = true
    return
  }
  guestLoading.value = true
  try {
    const ok = await authStore.loginAsGuest()
    if (ok) {
      message.success('已进入游客模式')
      router.push('/')
    } else {
      message.error('游客登录失败')
    }
  } catch (e) {
    message.error('游客登录失败')
  } finally {
    guestLoading.value = false
  }
}

// Capacitor移动端：已配置服务器地址则自动游客登录
onMounted(() => {
  if (isCapacitor.value && apiBaseUrl.value && !authStore.token) {
    handleGuestLogin()
  }
  // 手机版且未配置时，默认展开服务器配置
  if (isCapacitor.value && !apiBaseUrl.value) {
    showConfig.value = true
  }
})
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 50%, #6366f1 100%);
  position: relative;
  overflow: hidden;
  padding: 20px;
}

.login-bg {
  position: absolute;
  inset: 0;
  overflow: hidden;
}

.bg-shape {
  position: absolute;
  border-radius: 50%;
  opacity: 0.2;
  filter: blur(60px);
}

.shape1 {
  width: 400px;
  height: 400px;
  background: #60a5fa;
  top: -100px;
  left: -100px;
  animation: float 8s ease-in-out infinite;
}

.shape2 {
  width: 300px;
  height: 300px;
  background: #a78bfa;
  bottom: -50px;
  right: -80px;
  animation: float 6s ease-in-out infinite reverse;
}

.shape3 {
  width: 200px;
  height: 200px;
  background: #f472b6;
  top: 40%;
  left: 60%;
  animation: float 10s ease-in-out infinite;
}

@keyframes float {
  0%, 100% { transform: translate(0, 0); }
  50% { transform: translate(30px, -20px); }
}

.login-card {
  width: 100%;
  max-width: 380px;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(20px);
  padding: 36px 32px;
  border-radius: 20px;
  box-shadow: 0 25px 60px rgba(0, 0, 0, 0.2);
  position: relative;
  z-index: 10;
}

.login-header {
  text-align: center;
  margin-bottom: 28px;
}

.logo-icon {
  font-size: 48px;
  margin-bottom: 12px;
  animation: bounce 2s ease-in-out infinite;
}

@keyframes bounce {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-6px); }
}

.login-title {
  font-size: 28px;
  font-weight: 800;
  color: #1e293b;
  margin: 0 0 6px;
  letter-spacing: 1px;
}

.login-subtitle {
  color: #64748b;
  font-size: 13px;
  margin: 0;
}

.divider {
  display: flex;
  align-items: center;
  margin: 20px 0 16px;
  color: #94a3b8;
  font-size: 12px;
}

.divider span {
  padding: 0 12px;
  background: #fff;
  position: relative;
  z-index: 1;
}

.divider::before {
  content: '';
  flex: 1;
  height: 1px;
  background: #e2e8f0;
}

.guest-btn {
  background: linear-gradient(135deg, #f97316 0%, #ef4444 100%) !important;
  border: none !important;
  color: #fff !important;
  font-weight: 600 !important;
  height: 46px !important;
  border-radius: 10px !important;
  box-shadow: 0 6px 20px rgba(239, 68, 68, 0.35);
  transition: transform 0.2s, box-shadow 0.2s !important;
}

.guest-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 10px 28px rgba(239, 68, 68, 0.45) !important;
}

.tips {
  margin-top: 20px;
  text-align: center;
  font-size: 12px;
  color: #94a3b8;
}

.tips p {
  margin: 0;
}

.server-config {
  background: rgba(255, 255, 255, 0.7);
  border-radius: 12px;
  margin-bottom: 8px;
  overflow: hidden;
}

.config-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  cursor: pointer;
  user-select: none;
  transition: background 0.2s;
}

.config-header:hover {
  background: rgba(0, 0, 0, 0.03);
}

.config-title {
  font-size: 14px;
  font-weight: 600;
  color: #475569;
  display: flex;
  align-items: center;
  gap: 8px;
}

.config-status {
  font-size: 12px;
  padding: 2px 10px;
  border-radius: 12px;
  font-weight: 500;
}

.config-status.ok {
  background: #dcfce7;
  color: #16a34a;
}

.config-status.error {
  background: #fee2e2;
  color: #dc2626;
}

.config-body {
  padding: 0 16px 16px;
}

.server-input {
  margin-bottom: 12px;
}

.save-config-btn {
  background: linear-gradient(135deg, #3b82f6 0%, #6366f1 100%) !important;
  border: none !important;
  color: #fff !important;
  font-weight: 600 !important;
  height: 44px !important;
  border-radius: 10px !important;
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
}

.config-tip {
  font-size: 12px;
  color: #94a3b8;
  margin: 10px 0 0;
  line-height: 1.6;
}

.tip-mobile {
  margin-top: 6px !important;
}

@media (max-width: 480px) {
  .login-card {
    padding: 28px 22px;
  }
  
  .login-title {
    font-size: 24px;
  }
}
</style>
