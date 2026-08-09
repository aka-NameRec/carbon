<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'

import { api, type Message } from './api'
import MessageDetail from './components/MessageDetail.vue'
import MessageList from './components/MessageList.vue'

const queryClient = useQueryClient()
const query = ref('')
const selectedId = ref<string | null>(null)

const list = useQuery({ queryKey: ['messages'], queryFn: api.list })
const search = useQuery({
  queryKey: ['search', query],
  queryFn: () => (query.value ? api.search(query.value) : Promise.resolve({ items: [] })),
  enabled: computed(() => query.value.length > 0),
})
const items = computed(() =>
  query.value ? (search.data.value?.items ?? []) : (list.data.value ?? []),
)
const detail = useQuery({
  queryKey: ['message', selectedId],
  queryFn: () => api.detail(selectedId.value!),
  enabled: computed(() => selectedId.value !== null),
})
const selectedMessage = computed<Message | undefined>(() => detail.data.value)

const refresh = () => queryClient.invalidateQueries({ queryKey: ['messages'] })
const action = useMutation({
  mutationFn: ({ id, kind }: { id: string; kind: 'read' | 'unread' | 'delete' }) =>
    kind === 'read' ? api.read(id) : kind === 'unread' ? api.unread(id) : api.remove(id),
  onSuccess: refresh,
})

function toggleRead(message: Message) {
  action.mutate({ id: message.public_id, kind: message.read_at ? 'unread' : 'read' })
}

function remove(message: Message) {
  action.mutate({ id: message.public_id, kind: 'delete' })
  selectedId.value = null
}

onMounted(() => {
  const baseUrl = import.meta.env.VITE_API_BASE ?? 'http://127.0.0.1:8000/api/v1'
  const events = new EventSource(`${baseUrl}/events`)
  for (const type of ['message.created', 'message.read', 'message.unread', 'message.deleted']) {
    events.addEventListener(type, refresh)
  }
  events.onerror = refresh
})
</script>

<template>
  <main>
    <header>
      <h1>Carbon</h1>
      <input v-model="query" placeholder="Search messages" />
    </header>
    <section>
      <MessageList :items="items" :selected-id="selectedId" @select="selectedId = $event" />
      <MessageDetail :message="selectedMessage" @read="toggleRead" @remove="remove" />
    </section>
  </main>
</template>

<style>
main {
  max-width: 1100px;
  margin: auto;
  font-family: sans-serif;
}
header {
  display: flex;
  gap: 1rem;
  align-items: center;
}
input {
  flex: 1;
  padding: 0.7rem;
}
section {
  display: grid;
  grid-template-columns: 40% 1fr;
  gap: 1rem;
}
</style>
