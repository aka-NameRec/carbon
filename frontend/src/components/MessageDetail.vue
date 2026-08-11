<script setup lang="ts">
import { computed } from 'vue'

import type { Message } from '../api'
import { renderMarkdown } from '../markdown'

const props = defineProps<{ message?: Message }>()
const emit = defineEmits<{
  read: [message: Message]
  remove: [message: Message]
  openExternal: [url: string]
}>()

const renderedBody = computed(() => renderMarkdown(props.message?.body_markdown ?? ''))

function handleLink(event: MouseEvent): void {
  const target = event.target
  const link = target instanceof Element ? target.closest('a[href]') : null
  if (!(link instanceof HTMLAnchorElement)) return
  event.preventDefault()
  emit('openExternal', link.href)
}
</script>

<template>
  <article v-if="message">
    <h2>{{ message.title }}</h2>
    <p class="meta">Severity: {{ message.severity }}</p>
    <div class="message-body" @click="handleLink" v-html="renderedBody" />
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
.meta {
  margin: 0 0 0.5rem;
  color: #666;
  font-size: 0.85rem;
}
.message-body :deep(pre) {
  overflow-x: auto;
}
</style>
