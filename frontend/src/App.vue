<template>
  <router-view />
</template>

<script setup lang="ts">
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

html, body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'PingFang SC', 'Microsoft YaHei', 'Helvetica Neue', Arial,
    sans-serif;
  background-color: #f5f6fa;
  color: #333;
  -webkit-font-smoothing: antialiased;
}

#app {
  min-height: 100vh;
}

a {
  text-decoration: none;
  color: inherit;
}

/* A股配色：红涨绿跌 */
.text-up {
  color: #cf1322 !important;
}

.text-down {
  color: #389e0d !important;
}

/* 数字等宽 */
.mono-number {
  font-family: 'SF Mono', 'Consolas', 'Monaco', 'DengXian', monospace;
  font-variant-numeric: tabular-nums;
}

/* 滚动条样式 */
::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

::-webkit-scrollbar-track {
  background: #f5f5f5;
}

::-webkit-scrollbar-thumb {
  background: #d9d9d9;
  border-radius: 4px;
}

::-webkit-scrollbar-thumb:hover {
  background: #bfbfbf;
}
</style>
