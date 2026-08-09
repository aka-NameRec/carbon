<script setup lang="ts">
import type { Message } from '../api'

defineProps<{ message?: Message }>()
defineEmits<{ read: [message: Message]; remove: [message: Message] }>()
</script>

<template>
  <article v-if="message">
    <h2>{{ message.title }}</h2>
    <pre>{{ message.body_markdown }}</pre>
    <button @click="$emit('read', message)">
      {{ message.read_at ? 'Mark unread' : 'Mark read' }}
    </button>
    <button @click="$emit('remove', message)">Delete</button>
  </article>
  <article v-else>Select a message</article>
</template>

<style scoped>
article {
  padding: 1rem;
  border: 1px solid #ddd;
}
pre {
  white-space: pre-wrap;
}
</style>
