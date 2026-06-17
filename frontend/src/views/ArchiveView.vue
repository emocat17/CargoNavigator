<template>
  <div style="height: calc(100vh - 50px); width: 100%;">
    <DigitalArchive ref="archiveRef" />
  </div>
</template>
<script setup>
import { ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import DigitalArchive from '@/components/DigitalArchive.vue'

const route = useRoute()
const archiveRef = ref(null)

watch(
  () => route.query.orderId,
  (orderId) => {
    if (orderId && archiveRef.value) {
      archiveRef.value.loadArchive(orderId)
    }
  },
  { immediate: true }
)
</script>
