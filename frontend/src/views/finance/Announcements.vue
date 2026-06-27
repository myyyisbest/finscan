<template>
  <div class="announcement-page">
    <div class="page-header">
      <h3 class="page-title">公司公告</h3>
      <div class="date-range">
        <span class="range-label">最近90天</span>
      </div>
    </div>

    <a-spin :spinning="loading">
      <a-empty
        v-if="!loading && !announcements.length"
        :description="errorMsg || '暂无公告数据'"
      />

      <div v-else class="announcement-list">
        <a-list
          size="large"
          :data-source="announcements"
        >
          <template #renderItem="{ item, index }">
            <a-list-item class="announce-item">
              <div class="item-index">{{ index + 1 }}</div>
              <div class="item-content">
                <a
                  class="announce-title"
                  :href="getUrl(item.url)"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  {{ item.title }}
                </a>
                <div class="item-meta">
                  <span class="meta-date">{{ item.date }}</span>
                  <span v-if="item.sec_name" class="meta-name">{{ item.sec_name }}</span>
                </div>
              </div>
              <div class="item-action">
                <a-button type="link" size="small" @click.stop="openUrl(item.url)">
                  查看原文
                </a-button>
              </div>
            </a-list-item>
          </template>
        </a-list>

        <div v-if="announcements.length" class="list-footer">
          <span class="footer-text">
            共 {{ announcements.length }} 条公告 · 数据来源：巨潮资讯
          </span>
        </div>
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
const announcements = ref<Announcement[]>([])
const errorMsg = ref('')

function getUrl(url: string): string {
  if (!url) return ''
  if (url.startsWith('http://') || url.startsWith('https://')) return url
  return 'https://' + url
}

function openUrl(url: string) {
  if (url) {
    window.open(getUrl(url), '_blank', 'noopener,noreferrer')
  }
}

async function loadData() {
  if (!props.stockCode) return
  loading.value = true
  errorMsg.value = ''
  announcements.value = []
  try {
    const res = await stockApi.getProfile(props.stockCode)
    if (res.code === 0 && res.data) {
      announcements.value = res.data.announcements || []
      if (res.data.announce_error) {
        errorMsg.value = res.data.announce_error
      }
    } else {
      errorMsg.value = '获取公告失败'
    }
  } catch (e: any) {
    errorMsg.value = e?.message || '网络错误'
  } finally {
    loading.value = false
  }
}

watch(() => props.stockCode, (val) => {
  if (val) loadData()
}, { immediate: true })
</script>

<style scoped>
.announcement-page {
  width: 100%;
  background: #fff;
  border-radius: 4px;
  padding: 20px;
  min-height: 600px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 2px solid #1d4ed8;
  padding-bottom: 12px;
  margin-bottom: 16px;
}

.page-title {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #1d4ed8;
}

.date-range {
  font-size: 13px;
  color: #999;
}

.range-label {
  background: #f0f7ff;
  padding: 4px 10px;
  border-radius: 12px;
  color: #1d4ed8;
  font-size: 12px;
}

.announcement-list {
  margin-top: 8px;
}

.announce-item {
  display: flex !important;
  align-items: flex-start !important;
  gap: 16px;
  padding: 16px 0 !important;
  border-bottom: 1px solid #f0f0f0 !important;
}

.announce-item:last-child {
  border-bottom: none !important;
}

.item-index {
  flex-shrink: 0;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: #f0f7ff;
  color: #1d4ed8;
  font-size: 13px;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-top: 2px;
}

.item-content {
  flex: 1;
  min-width: 0;
}

.announce-title {
  font-size: 14px;
  font-weight: 500;
  color: #1d4ed8;
  text-decoration: none;
  line-height: 1.6;
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  cursor: pointer;
}

.announce-title:hover {
  text-decoration: underline;
  color: #2563eb;
}

.item-meta {
  margin-top: 6px;
  display: flex;
  gap: 12px;
  font-size: 12px;
  color: #999;
}

.meta-date {
  font-variant-numeric: tabular-nums;
}

.meta-name {
  color: #bbb;
}

.item-action {
  flex-shrink: 0;
}

.list-footer {
  margin-top: 16px;
  padding-top: 12px;
  border-top: 1px solid #f0f0f0;
  text-align: center;
}

.footer-text {
  font-size: 12px;
  color: #bbb;
}
</style>
