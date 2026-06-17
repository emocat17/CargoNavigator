<template>
  <div style="height: calc(100vh - 50px); width: 100%;">
    <RoutePlanner @view-transport="onViewTransport" />
  </div>
</template>
<script setup>
import { useRouter } from 'vue-router'
import RoutePlanner from '@/components/RoutePlanner.vue'

const router = useRouter()

function onViewTransport() {
  router.push({ name: 'transport' })
}
</script>
