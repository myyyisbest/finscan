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

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial,
    sans-serif;
  background-color: #F5F7FA;
}

#app {
  min-height: 100vh;
}

.mono-number {
  font-family: 'SF Mono', 'Consolas', 'Monaco', monospace;
}

.positive {
  color: #52c41a;
}

.negative {
  color: #ff4d4f;
}
</style>
