<template>
  <div class="company-profile">
    <a-spin :spinning="loading">
      <div v-if="!loading && !profile && !basic" class="empty-state">
        <a-empty :description="errorMessage || '暂无公司简介数据'">
          <template #image>
            <span style="font-size: 48px">📋</span>
          </template>
        </a-empty>
      </div>

      <div v-else class="profile-content">
        <!-- 公司概况 -->
        <a-card class="profile-card" :bordered="false">
          <template #title>
            <span class="card-title">公司概况</span>
          </template>
          <div class="info-grid">
            <div class="info-item">
              <span class="info-label">公司名称</span>
              <span class="info-value">{{ getField('公司名称') || basic?.full_name || basic?.stock_name || '-' }}</span>
            </div>
            <div class="info-item">
              <span class="info-label">A股简称</span>
              <span class="info-value">{{ getField('A股简称') || basic?.stock_name || '-' }}</span>
            </div>
            <div class="info-item" v-if="getField('英文名称')">
              <span class="info-label">英文名称</span>
              <span class="info-value">{{ getField('英文名称') }}</span>
            </div>
            <div class="info-item" v-if="getField('曾用简称')">
              <span class="info-label">曾用简称</span>
              <span class="info-value">{{ getField('曾用简称') }}</span>
            </div>
            <div class="info-item">
              <span class="info-label">A股代码</span>
              <span class="info-value">{{ getField('A股代码') || basic?.stock_code || '-' }}</span>
            </div>
            <div class="info-item" v-if="getField('所属市场')">
              <span class="info-label">所属市场</span>
              <span class="info-value">{{ getField('所属市场') }}</span>
            </div>
            <div class="info-item" v-if="getField('所属行业')">
              <span class="info-label">所属行业</span>
              <span class="info-value">{{ getField('所属行业') }}</span>
            </div>
            <div class="info-item" v-if="getField('入选指数')">
              <span class="info-label">入选指数</span>
              <span class="info-value">{{ getField('入选指数') }}</span>
            </div>
            <div class="info-item" v-if="getField('上市日期') || basic?.list_date">
              <span class="info-label">上市日期</span>
              <span class="info-value">{{ formatDate(getField('上市日期')) || formatDate(basic?.list_date) || '-' }}</span>
            </div>
            <div class="info-item" v-if="getField('成立日期')">
              <span class="info-label">成立日期</span>
              <span class="info-value">{{ formatDate(getField('成立日期')) }}</span>
            </div>
            <div class="info-item" v-if="getField('法人代表')">
              <span class="info-label">法人代表</span>
              <span class="info-value">{{ getField('法人代表') }}</span>
            </div>
            <div class="info-item" v-if="getField('注册资金')">
              <span class="info-label">注册资金</span>
              <span class="info-value">{{ getField('注册资金') }}</span>
            </div>
          </div>
        </a-card>

        <!-- 主营业务 & 经营范围 -->
        <a-card v-if="getField('主营业务') || getField('经营范围')" class="profile-card" :bordered="false">
          <template #title>
            <span class="card-title">主营业务</span>
          </template>
          <div class="business-content">
            <p v-if="getField('主营业务')" class="business-text">
              <strong class="business-label">主营业务：</strong>{{ getField('主营业务') }}
            </p>
            <p v-if="getField('经营范围')" class="business-text">
              <strong class="business-label">经营范围：</strong>{{ getField('经营范围') }}
            </p>
          </div>
        </a-card>

        <!-- 联系信息 -->
        <a-card v-if="hasContactInfo" class="profile-card" :bordered="false">
          <template #title>
            <span class="card-title">联系信息</span>
          </template>
          <div class="info-grid">
            <div class="info-item" v-if="getField('官方网站')">
              <span class="info-label">官方网站</span>
              <a :href="getUrl(getField('官方网站'))" target="_blank" rel="noopener" class="info-value link">
                {{ getField('官方网站') }}
              </a>
            </div>
            <div class="info-item" v-if="getField('电子邮箱')">
              <span class="info-label">电子邮箱</span>
              <span class="info-value">{{ getField('电子邮箱') }}</span>
            </div>
            <div class="info-item" v-if="getField('联系电话')">
              <span class="info-label">联系电话</span>
              <span class="info-value">{{ getField('联系电话') }}</span>
            </div>
            <div class="info-item" v-if="getField('传真')">
              <span class="info-label">传真</span>
              <span class="info-value">{{ getField('传真') }}</span>
            </div>
            <div class="info-item" v-if="getField('注册地址')">
              <span class="info-label">注册地址</span>
              <span class="info-value">{{ getField('注册地址') }}</span>
            </div>
            <div class="info-item" v-if="getField('办公地址')">
              <span class="info-label">办公地址</span>
              <span class="info-value">{{ getField('办公地址') }}</span>
            </div>
            <div class="info-item" v-if="getField('邮政编码')">
              <span class="info-label">邮政编码</span>
              <span class="info-value">{{ getField('邮政编码') }}</span>
            </div>
          </div>
        </a-card>

        <!-- 机构简介 -->
        <a-card v-if="getField('机构简介')" class="profile-card" :bordered="false">
          <template #title>
            <span class="card-title">公司简介</span>
          </template>
          <p class="description-text">{{ getField('机构简介') }}</p>
        </a-card>

        <div v-if="errorMessage" class="error-tip">
          <a-alert :message="errorMessage" type="warning" show-icon />
        </div>
      </div>
    </a-spin>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { stockApi } from '@/api/finance'

const props = defineProps<{
  stockCode: string
  stockInfo?: any
}>()

const loading = ref(false)
const profile = ref<Record<string, string> | null>(null)
const basic = ref<any>(null)
const errorMessage = ref<string>('')

function getField(key: string): string {
  if (!profile.value) return ''
  const val = profile.value[key]
  if (val === undefined || val === null || val === 'nan' || val === 'None') return ''
  return val
}

const hasContactInfo = computed(() => {
  return ['官方网站', '电子邮箱', '联系电话', '传真', '注册地址', '办公地址', '邮政编码']
    .some(k => getField(k))
})

function formatDate(d: string | undefined | null): string {
  if (!d) return ''
  const dt = new Date(d)
  if (!isNaN(dt.getTime())) {
    return dt.toISOString().slice(0, 10)
  }
  // 处理 "2001年08月27日" 之类的格式
  return d
}

function getUrl(url: string): string {
  if (!url) return ''
  if (!url.startsWith('http')) return 'http://' + url
  return url
}

async function loadData() {
  if (!props.stockCode) return
  loading.value = true
  errorMessage.value = ''
  profile.value = null
  try {
    const res = await stockApi.getProfile(props.stockCode)
    if (res.code === 0 && res.data) {
      basic.value = res.data.basic
      profile.value = res.data.profile
      if (res.data.profile_error) {
        errorMessage.value = res.data.profile_error
      }
    } else {
      errorMessage.value = '接口返回异常'
    }
  } catch (e: any) {
    errorMessage.value = e?.message || '获取公司简介失败'
  } finally {
    loading.value = false
  }
}

watch(() => props.stockCode, (val) => {
  if (val) loadData()
}, { immediate: true })
</script>

<style scoped>
.company-profile {
  width: 100%;
}

.profile-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.profile-card {
  border-radius: 8px;
  border: 1px solid #e8e8e8;
}

.card-title {
  font-size: 15px;
  font-weight: 600;
  color: #1d4ed8;
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 14px 24px;
}

.info-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  font-size: 13px;
  line-height: 1.6;
}

.info-label {
  flex-shrink: 0;
  min-width: 84px;
  color: #9ca3af;
  font-weight: 400;
}

.info-value {
  color: #374151;
  font-weight: 500;
  word-break: break-all;
}

.info-value.link {
  color: #2563eb;
  text-decoration: none;
}
.info-value.link:hover {
  text-decoration: underline;
}

.business-content {
  font-size: 14px;
  line-height: 1.8;
  color: #374151;
}

.business-text {
  margin: 0 0 12px 0;
}
.business-text:last-child { margin-bottom: 0; }

.business-label {
  color: #1d4ed8;
  margin-right: 6px;
  font-weight: 600;
}

.description-text {
  font-size: 14px;
  line-height: 1.8;
  color: #374151;
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
  text-indent: 2em;
}

.empty-state {
  padding: 60px 0;
}

.error-tip {
  margin-top: 8px;
  font-size: 12px;
}
</style>
