import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useAppStore = defineStore('app', () => {
  const collapsed = ref(false)
  const selectedGroup = ref<string | null>(null)

  function toggleSidebar() {
    collapsed.value = !collapsed.value
  }

  function setSelectedGroup(group: string | null) {
    selectedGroup.value = group
  }

  return {
    collapsed,
    selectedGroup,
    toggleSidebar,
    setSelectedGroup
  }
})
