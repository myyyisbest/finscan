<template>
  <div class="announcement-page">
    <a-empty description="公告功能开发中，敬请期待">
      <template #description>
        <span>公告功能将在后续版本中提供</span>
      </template>
    </a-empty>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  stockCode: string
  stockInfo?: any
}>()
</script>

<style scoped>
.announcement-page {
  padding: 60px 0;
  text-align: center;
}
</style>
