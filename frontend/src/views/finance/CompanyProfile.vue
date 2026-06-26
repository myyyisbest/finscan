<template>
  <div class="company-profile">
    <a-spin :spinning="loading">
      <div v-if="!loading && !profile && !announcements.length && !basic" class="empty-state">
        <a-empty
          :description="errorMessage || '暂无公司简介数据'"
        >
          <template #image>
            <span style="font-size: 48px">📋</span>
          </template>
        </a-empty>
      </div>

      <div v-else class="profile-content">
        <!-- 基础信息卡片：始终显示（即使profile为空） -->
        <a-card class="profile-card" title="公司概况" :bordered="false">
          <div class="info-grid">
            <div class="info-item">
              <span class="info-label">公司名称</span>
              <span class="info-value">{{ getField('org_name_cn') || basic?.full_name || basic?.stock_name || '-' }}</span>
            </div>
            <div class="info-item">
              <span class="info-label">公司简称</span>
              <span class="info-value">{{ getField('org_short_name_cn') || basic?.stock_name || '-' }}</span>
            </div>
            <div class="info-item" v-if="getField('org_name_en')">
              <span class="info-label">英文名称</span>
              <span class="info-value">{{ getField('org_name_en') }}</span>
            </div>
            <div class="info-item" v-if="getField('org_short_name_en')">
              <span class="info-label">英文简称</span>
              <span class="info-value">{{ getField('org_short_name_en') }}</span>
            </div>
            <div class="info-item" v-if="getField('pre_name')">
              <span class="info-label">曾用名</span>
              <span class="info-value">{{ getField('pre_name') }}</span>
            </div>
            <div class="info-item" v-if="getField('org_id')">
              <span class="info-label">股票代码</span>
              <span class="info-value">{{ getField('org_id') }}</span>
            </div>
            <div class="info-item" v-if="getField('cnsp_id')">
              <span class="info-label">CNSP ID</span>
              <span class="info-value">{{ getField('cnsp_id') }}</span>
            </div>
            <div class="info-item" v-if="basic?.market">
              <span class="info-label">上市市场</span>
              <span class="info-value">{{ basic?.market === 'SH' ? '上海证券交易所' : basic?.market === 'SZ' ? '深圳证券交易所' : '北京证券交易所' }}</span>
            </div>
            <div class="info-item" v-if="getField('listed_date') || basic?.list_date">
              <span class="info-label">上市日期</span>
              <span class="info-value">{{ formatDate(getField('listed_date')) || formatDate(basic?.list_date) || '-' }}</span>
            </div>
            <div class="info-item" v-if="getField('established_date')">
              <span class="info-label">成立日期</span>
              <span class="info-value">{{ formatDate(getField('established_date')) }}</span>
            </div>
            <div class="info-item" v-if="getField('currency')">
              <span class="info-label">货币</span>
              <span class="info-value">{{ getField('currency') }}</span>
            </div>
            <div class="info-item" v-if="getField('raised_capital')">
              <span class="info-label">募集资金</span>
              <span class="info-value">{{ getField('raised_capital') }}</span>
            </div>
          </div>
          <a-alert
            v-if="errorMessage"
            class="info-alert"
            :message="`雪球公司简介接口暂不可用：${errorMessage}`"
            type="info"
            show-icon
          />
        </a-card>

        <!-- 主营业务 -->
        <a-card v-if="profile" class="profile-card" title="主营业务" :bordered="false">
          <div class="business-content">
            <p v-if="getField('main_business')" class="business-text">
              <strong>主营业务：</strong>{{ getField('main_business') }}
            </p>
            <p v-if="getField('main_business_scope')" class="business-text">
              <strong>经营范围：</strong>{{ getField('main_business_scope') }}
            </p>
            <p v-if="getField('business_scope')" class="business-text">
              <strong>业务范围：</strong>{{ getField('business_scope') }}
            </p>
            <p v-if="getField('classi_name')" class="business-text">
              <strong>行业分类：</strong>{{ getField('classi_name') }}
            </p>
          </div>
        </a-card>

        <!-- 控股与法人 -->
        <a-card v-if="profile" class="profile-card" title="控股与法人" :bordered="false">
          <div class="info-grid">
            <div class="info-item" v-if="getField('actual_controller')">
              <span class="info-label">实际控制人</span>
              <span class="info-value">{{ getField('actual_controller') }}</span>
            </div>
            <div class="info-item" v-if="getField('actual_controller_amount')">
              <span class="info-label">控制金额</span>
              <span class="info-value">{{ getField('actual_controller_amount') }}</span>
            </div>
            <div class="info-item" v-if="getField('enterprise_type')">
              <span class="info-label">企业类型</span>
              <span class="info-value">{{ getField('enterprise_type') }}</span>
            </div>
            <div class="info-item" v-if="getField('legal_rep')">
              <span class="info-label">法人代表</span>
              <span class="info-value">{{ getField('legal_rep') }}</span>
            </div>
            <div class="info-item" v-if="getField('secretary')">
              <span class="info-label">董事会秘书</span>
              <span class="info-value">{{ getField('secretary') }}</span>
            </div>
            <div class="info-item" v-if="getField('reg_capital')">
              <span class="info-label">注册资本</span>
              <span class="info-value">{{ getField('reg_capital') }}</span>
            </div>
            <div class="info-item" v-if="getField('employees_number')">
              <span class="info-label">员工人数</span>
              <span class="info-value">{{ getField('employees_number') }}</span>
            </div>
            <div class="info-item" v-if="getField('main_holders_count')">
              <span class="info-label">主要股东数</span>
              <span class="info-value">{{ getField('main_holders_count') }}</span>
            </div>
          </div>
        </a-card>

        <!-- 联系信息 -->
        <a-card v-if="profile" class="profile-card" title="联系信息" :bordered="false">
          <div class="info-grid">
            <div class="info-item" v-if="getField('office_address')">
              <span class="info-label">办公地址</span>
              <span class="info-value">{{ getField('office_address') }}</span>
            </div>
            <div class="info-item" v-if="getField('reg_address')">
              <span class="info-label">注册地址</span>
              <span class="info-value">{{ getField('reg_address') }}</span>
            </div>
            <div class="info-item" v-if="getField('org_website')">
              <span class="info-label">公司网站</span>
              <a :href="getField('org_website')" target="_blank" rel="noopener" class="info-value link">
                {{ getField('org_website') }}
              </a>
            </div>
            <div class="info-item" v-if="getField('org_telephone')">
              <span class="info-label">联系电话</span>
              <span class="info-value">{{ getField('org_telephone') }}</span>
            </div>
            <div class="info-item" v-if="getField('org_email')">
              <span class="info-label">电子邮箱</span>
              <span class="info-value">{{ getField('org_email') }}</span>
            </div>
            <div class="info-item" v-if="getField('province') || getField('city')">
              <span class="info-label">所在地区</span>
              <span class="info-value">
                {{ getField('province') }}{{ getField('city') }}{{ getField('area') }}
              </span>
            </div>
          </div>
        </a-card>

        <!-- 公司简介 -->
        <a-card v-if="getField('description')" class="profile-card" title="公司简介" :bordered="false">
          <p class="description-text">{{ getField('description') }}</p>
        </a-card>

        <!-- 最新公告 -->
        <a-card class="profile-card" title="最新公告（近90天）" :bordered="false">
          <a-empty
            v-if="!announcements.length"
            :description="announceError || '暂无公告数据'"
          />
          <a-list
            v-else
            size="small"
            :data-source="announcements"
            :split="false"
          >
            <template #renderItem="{ item }">
              <a-list-item class="announce-item">
                <a
                  v-if="item.url"
                  :href="item.url"
                  target="_blank"
                  rel="noopener"
                  class="announce-title"
                >
                  {{ item.title }}
                </a>
                <span v-else class="announce-title">{{ item.title }}</span>
                <span class="announce-date">{{ item.date }}</span>
              </a-list-item>
            </template>
          </a-list>
        </a-card>
      </div>
    </a-spin>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { stockApi } from '@/api/finance'

interface Announcement {
  title: string
  date: string
  time: string
  sec_name: string
  url: string
}

const props = defineProps<{
  stockCode: string
  stockInfo?: any
}>()

const loading = ref(false)
const profile = ref<Record<string, string> | null>(null)
const basic = ref<any>(null)
const errorMessage = ref<string>('')
const announcements = ref<Announcement[]>([])
const announceError = ref<string>('')

function getField(key: string): string {
  if (!profile.value) return ''
  return profile.value[key] || ''
}

function formatDate(d: string | undefined | null): string {
  if (!d) return ''
  const dt = new Date(d)
  if (!isNaN(dt.getTime())) {
    return dt.toISOString().slice(0, 10)
  }
  return d
}

async function loadData() {
  if (!props.stockCode) return
  loading.value = true
  errorMessage.value = ''
  announceError.value = ''
  profile.value = null
  announcements.value = []
  try {
    const res = await stockApi.getProfile(props.stockCode)
    if (res.code === 0 && res.data) {
      basic.value = res.data.basic
      profile.value = res.data.profile
      errorMessage.value = res.data.profile_error || ''
      announcements.value = res.data.announcements || []
      announceError.value = res.data.announce_error || ''
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
  border-radius: 6px;
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 16px 24px;
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
  color: #999;
}

.info-value {
  color: #333;
  font-weight: 500;
  word-break: break-all;
}

.info-value.link {
  color: #1d4ed8;
  text-decoration: none;
}

.info-value.link:hover {
  text-decoration: underline;
}

.business-content {
  font-size: 14px;
  line-height: 1.8;
  color: #333;
}

.business-text {
  margin: 0 0 12px 0;
}

.business-text:last-child {
  margin-bottom: 0;
}

.business-text strong {
  color: #1d4ed8;
  margin-right: 6px;
  font-weight: 600;
}

.description-text {
  font-size: 14px;
  line-height: 1.8;
  color: #333;
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
}

.info-alert {
  margin-top: 12px;
  font-size: 12px;
}

.announce-item {
  padding: 8px 0 !important;
  border-bottom: 1px dashed #f0f0f0;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

.announce-item:last-child {
  border-bottom: none;
}

.announce-title {
  flex: 1;
  color: #1d4ed8;
  text-decoration: none;
  font-size: 13px;
  line-height: 1.5;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.announce-title:hover {
  text-decoration: underline;
}

.announce-date {
  flex-shrink: 0;
  font-size: 12px;
  color: #999;
  font-variant-numeric: tabular-nums;
}

.empty-state {
  padding: 60px 0;
}
</style>
