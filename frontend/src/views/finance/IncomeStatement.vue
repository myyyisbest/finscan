<template>
  <FinTable :fetch-data="financeApi.getIncomeStatement" :stock-code="stockCode" />
</template>

<script setup lang="ts">
import FinTable from '@/components/FinTable.vue'
import { financeApi } from '@/api/finance'

defineProps<{
  stockCode: string
  stockInfo?: any
}>()
</script>
