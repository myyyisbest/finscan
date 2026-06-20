<template>
  <a-badge :status="statusType" :text="labelText" :class="'risk-badge ' + level" />
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  level: 'low' | 'medium' | 'high' | 'very_high' | 'excluded'
}>()

const statusType = computed(() => {
  switch (props.level) {
    case 'low':
      return 'success'
    case 'medium':
      return 'warning'
    case 'high':
      return 'error'
    case 'very_high':
      return 'error'
    case 'excluded':
      return 'default'
    default:
      return 'default'
  }
})

const labelText = computed(() => {
  switch (props.level) {
    case 'low':
      return '低风险'
    case 'medium':
      return '中风险'
    case 'high':
      return '高风险'
    case 'very_high':
      return '极高风险'
    case 'excluded':
      return '直接排除'
    default:
      return '未知'
  }
})
</script>

<style scoped>
.risk-badge {
  font-weight: 500;
}

.risk-badge.low {
  color: #52c41a;
}

.risk-badge.medium {
  color: #faad14;
}

.risk-badge.high {
  color: #ff7a45;
}

.risk-badge.very_high {
  color: #ff4d4f;
}

.risk-badge.excluded {
  color: #8c8c8c;
}
</style>
