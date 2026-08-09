<script setup lang="ts">
import type { Message } from '../api'

defineProps<{ items: Message[]; selectedId: string | null }>()
defineEmits<{ select: [publicId: string] }>()
</script>

<template>
  <aside class="message-list">
    <button
      v-for="message in items"
      :key="message.public_id"
      :class="{ selected: message.public_id === selectedId }"
      @click="$emit('select', message.public_id)"
    >
      <strong>{{ message.title }}</strong>
      <small>{{ message.source }} · {{ message.read_at ? 'read' : 'unread' }}</small>
    </button>
  </aside>
</template>

<style scoped>
.message-list {
  display: grid;
  gap: 0.5rem;
}
button {
  padding: 0.8rem;
  text-align: left;
}
.selected {
  border-color: #2563eb;
}
small {
  display: block;
  color: #666;
}
</style>
