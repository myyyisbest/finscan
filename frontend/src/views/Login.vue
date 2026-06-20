<template>
  <div class="login-page">
    <div class="login-container">
      <div class="login-header">
        <h1 class="title">FinScan</h1>
        <p class="subtitle">金融分析系统</p>
      </div>
      <a-card class="login-card">
        <a-tabs v-model:activeKey="activeTab" centered>
          <a-tab-pane key="login" tab="登录">
            <a-form
              :model="loginForm"
              @finish="handleLogin"
              layout="vertical"
            >
              <a-form-item
                name="username"
                :rules="[{ required: true, message: '请输入用户名' }]"
              >
                <a-input
                  v-model:value="loginForm.username"
                  placeholder="用户名"
                  size="large"
                >
                  <template #prefix><UserOutlined /></template>
                </a-input>
              </a-form-item>
              <a-form-item
                name="password"
                :rules="[{ required: true, message: '请输入密码' }]"
              >
                <a-input-password
                  v-model:value="loginForm.password"
                  placeholder="密码"
                  size="large"
                >
                  <template #prefix><LockOutlined /></template>
                </a-input-password>
              </a-form-item>
              <a-form-item>
                <a-button
                  type="primary"
                  html-type="submit"
                  size="large"
                  block
                  :loading="authStore.loading"
                >
                  登录
                </a-button>
              </a-form-item>
            </a-form>
          </a-tab-pane>
          <a-tab-pane key="register" tab="注册">
            <a-form
              :model="registerForm"
              @finish="handleRegister"
              layout="vertical"
            >
              <a-form-item
                name="username"
                :rules="[{ required: true, message: '请输入用户名' }]"
              >
                <a-input
                  v-model:value="registerForm.username"
                  placeholder="用户名"
                  size="large"
                >
                  <template #prefix><UserOutlined /></template>
                </a-input>
              </a-form-item>
              <a-form-item
                name="password"
                :rules="[{ required: true, message: '请输入密码' }, { min: 6, message: '密码至少6位' }]"
              >
                <a-input-password
                  v-model:value="registerForm.password"
                  placeholder="密码"
                  size="large"
                >
                  <template #prefix><LockOutlined /></template>
                </a-input-password>
              </a-form-item>
              <a-form-item
                name="email"
              >
                <a-input
                  v-model:value="registerForm.email"
                  placeholder="邮箱 (可选)"
                  size="large"
                >
                  <template #prefix><MailOutlined /></template>
                </a-input>
              </a-form-item>
              <a-form-item>
                <a-button
                  type="primary"
                  html-type="submit"
                  size="large"
                  block
                  :loading="authStore.loading"
                >
                  注册
                </a-button>
              </a-form-item>
            </a-form>
          </a-tab-pane>
        </a-tabs>
        <a-alert
          v-if="errorMessage"
          :message="errorMessage"
          type="error"
          show-icon
          closable
          class="error-alert"
          @close="errorMessage = ''"
        />
        <a-alert
          v-if="successMessage"
          :message="successMessage"
          type="success"
          show-icon
          closable
          class="success-alert"
          @close="successMessage = ''"
        />
      </a-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { UserOutlined, LockOutlined, MailOutlined } from '@ant-design/icons-vue'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()

const activeTab = ref('login')
const errorMessage = ref('')
const successMessage = ref('')

const loginForm = ref({
  username: '',
  password: ''
})

const registerForm = ref({
  username: '',
  password: '',
  email: ''
})

const handleLogin = async () => {
  errorMessage.value = ''
  try {
    await authStore.login(loginForm.value.username, loginForm.value.password)
    message.success('登录成功')
    router.push('/')
  } catch (error: any) {
    errorMessage.value = error.response?.data?.message || '登录失败，请检查用户名和密码'
  }
}

const handleRegister = async () => {
  errorMessage.value = ''
  successMessage.value = ''
  try {
    await authStore.register(
      registerForm.value.username,
      registerForm.value.password,
      registerForm.value.email
    )
    successMessage.value = '注册成功，请登录'
    activeTab.value = 'login'
    loginForm.value.username = registerForm.value.username
  } catch (error: any) {
    errorMessage.value = error.response?.data?.message || '注册失败'
  }
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.login-container {
  width: 400px;
}

.login-header {
  text-align: center;
  margin-bottom: 24px;
}

.title {
  font-size: 36px;
  font-weight: 700;
  color: #fff;
  margin: 0;
}

.subtitle {
  font-size: 16px;
  color: rgba(255, 255, 255, 0.8);
  margin-top: 8px;
}

.login-card {
  border-radius: 8px;
}

.error-alert {
  margin-top: 16px;
}

.success-alert {
  margin-top: 16px;
}
</style>
