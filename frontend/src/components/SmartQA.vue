<template>
  <div class="q-pa-md">
    <div class="text-h6 q-mb-md">智能问答助手</div>
    <q-chat-message
      label="Today"
    />
    <q-chat-message
      name="AI Assistant"
      avatar="https://cdn.quasar.dev/img/avatar3.jpg"
      :text="['您好！我是您的智能路线助手。请问有什么可以帮您？']"
      bg-color="amber-7"
    />
    <q-chat-message
      name="Me"
      avatar="https://cdn.quasar.dev/img/avatar4.jpg"
      :text="['这张地图的数据是最新的吗？']"
      sent
      bg-color="primary"
      text-color="white"
    />
    <q-chat-message
      name="AI Assistant"
      avatar="https://cdn.quasar.dev/img/avatar3.jpg"
      :text="['是的，我们使用的是高德地图实时数据。']"
      bg-color="amber-7"
    />
    
    <div class="q-mt-md">
        <q-input outlined v-model="message" label="请输入您的问题..." dense>
            <template v-slot:after>
                <q-btn round dense flat icon="send" color="primary" />
            </template>
        </q-input>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const message = ref('')
</script>
