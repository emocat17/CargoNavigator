<template>
  <div style="height: calc(100vh - 50px); width: 100%;">
    <TransportManager @view-archive="onViewArchive" />
  </div>
</template>
<script setup>
import { useRouter } from 'vue-router'
import TransportManager from '@/components/TransportManager.vue'

const router = useRouter()

function onViewArchive(orderId) {
  router.push({ name: 'archive', query: { orderId } })
}
</script>
