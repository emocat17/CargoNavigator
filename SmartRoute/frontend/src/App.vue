<template>
  <q-layout view="hHh lpR fFf">

    <q-header elevated class="bg-primary text-white">
      <q-toolbar>
        <q-toolbar-title>
          <q-avatar>
            <img src="https://cdn.quasar.dev/logo-v2/svg/logo-mono-white.svg">
          </q-avatar>
          SmartRoute (大型货车智能选线)
        </q-toolbar-title>
      </q-toolbar>
    </q-header>

    <q-page-container>
      <router-view />
      <div class="q-pa-md">
        <div class="text-h6">Welcome to SmartRoute</div>
        <p>Frontend is running with Quasar!</p>
      </div>
    </q-page-container>

  </q-layout>
</template>

<script setup>
</script>
