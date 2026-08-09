<script setup lang="ts">
import { computed } from 'vue'

import type { Message } from '../api'

const props = defineProps<{ items: Message[]; selectedId: string | null }>()
defineEmits<{ select: [publicId: string] }>()

const groups = computed(() => {
  const bySource = new Map<string, Message[]>()
  for (const message of props.items) {
    const group = bySource.get(message.source) ?? []
    group.push(message)
    bySource.set(message.source, group)
  }
  return [...bySource.entries()]
})

function localTime(timestamp: string): string {
  return new Date(timestamp).toLocaleString()
}
</script>

<template>
  <aside class="message-list">
    <section
      v-for="[source, messages] in groups"
      :key="source"
      :aria-label="`Messages from ${source}`"
    >
      <h2>{{ source }}</h2>
      <button
        v-for="message in messages"
        :key="message.public_id"
        :class="{ selected: message.public_id === selectedId, unread: !message.read_at }"
        @click="$emit('select', message.public_id)"
      >
        <strong>{{ message.title }}</strong>
        <small
          >{{ localTime(message.received_at) }} · {{ message.read_at ? 'read' : 'unread' }}</small
        >
      </button>
    </section>
  </aside>
</template>

<style scoped>
.message-list {
  display: grid;
  gap: 0.5rem;
}
section {
  display: grid;
  gap: 0.5rem;
}
h2 {
  font-size: 0.9rem;
  margin: 0.6rem 0 0;
}
button {
  padding: 0.8rem;
  text-align: left;
}
.selected {
  border-color: #2563eb;
}
.unread strong {
  font-weight: 800;
}
small {
  display: block;
  color: #666;
}
</style>
