<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useInfiniteQuery, useMutation, useQuery, useQueryClient } from '@tanstack/vue-query'
import { useRoute, useRouter } from 'vue-router'

import { api, type MessageFilters } from './api'
import MessageDetail from './components/MessageDetail.vue'
import MessageList from './components/MessageList.vue'
import {
  listenForDeepLinks,
  listenForNotificationActions,
  notifyAboutNewMessage,
  openExternalUrl,
  setTrayState,
  type TrayState,
} from './desktop'

const queryClient = useQueryClient()
const route = useRoute()
const router = useRouter()
const query = ref('')
const source = ref('')
const unreadOnly = ref(false)
const selectedId = ref<string | null>(
  typeof route.params.publicId === 'string' ? route.params.publicId : null,
)
let unlistenDeepLinks: () => void = () => undefined
let unlistenNotificationActions: () => void = () => undefined
let events: EventSource | undefined

const filters = computed<MessageFilters>(() => ({
  source: source.value || undefined,
  unread: unreadOnly.value || undefined,
}))
const list = useInfiniteQuery({
  queryKey: ['messages', filters],
  initialPageParam: null as string | null,
  queryFn: ({ pageParam }) => api.list(filters.value, pageParam),
  getNextPageParam: (page) => page.next_cursor,
})
const search = useQuery({
  queryKey: ['search', query],
  queryFn: () => api.search(query.value),
  enabled: computed(() => query.value.length > 0),
})
const listItems = computed(() => list.data.value?.pages.flatMap((page) => page.items) ?? [])
const items = computed(() => (query.value ? (search.data.value?.items ?? []) : listItems.value))
const unreadCount = computed(() => list.data.value?.pages[0]?.unread_count ?? 0)
const unreadImportantCount = computed(
  () => list.data.value?.pages[0]?.unread_important_count ?? 0,
)
const listHasError = computed(() => list.isError.value || search.isError.value)
const hasNextPage = computed(() => list.hasNextPage.value)
const isFetchingNextPage = computed(() => list.isFetchingNextPage.value)
const detail = useQuery({
  queryKey: ['message', selectedId],
  queryFn: () => api.detail(selectedId.value!),
  enabled: computed(() => selectedId.value !== null),
})
const selectedMessage = computed(() => detail.data.value)
const refresh = () => queryClient.invalidateQueries({ queryKey: ['messages'] })
const action = useMutation({
  mutationFn: ({ id, kind }: { id: string; kind: 'read' | 'unread' | 'delete' }) =>
    kind === 'read' ? api.read(id) : kind === 'unread' ? api.unread(id) : api.remove(id),
  onSuccess: refresh,
})

watch(
  [unreadImportantCount, unreadCount, () => list.isError.value],
  ([important, count, hasError]) => {
    const state: TrayState = hasError
      ? 'error'
      : important > 0
        ? 'important'
        : count > 0
          ? 'unread'
          : 'idle'
    void setTrayState(state).catch(() => undefined)
  },
  { immediate: true },
)
watch(
  () => route.params.publicId,
  (publicId) => {
    selectedId.value = typeof publicId === 'string' ? publicId : null
  },
)

function selectMessage(id: string): void {
  void router.push({ name: 'message', params: { publicId: id } })
}

function toggleRead(): void {
  if (detail.data.value) {
    action.mutate({
      id: detail.data.value.public_id,
      kind: detail.data.value.read_at ? 'unread' : 'read',
    })
  }
}

function remove(): void {
  if (detail.data.value) {
    action.mutate({ id: detail.data.value.public_id, kind: 'delete' })
    void router.push('/')
  }
}

onMounted(() => {
  const baseUrl = import.meta.env.VITE_API_BASE ?? 'http://127.0.0.1:8000/api/v1'
  events = new EventSource(`${baseUrl}/events`)
  events.addEventListener('message.created', (event) => {
    refresh()
    const payload = JSON.parse((event as MessageEvent<string>).data) as { public_id?: string }
    if (payload.public_id) void notifyAboutNewMessage(payload.public_id)
  })
  for (const type of ['message.read', 'message.unread', 'message.deleted', 'message.updated']) {
    events.addEventListener(type, refresh)
  }
  events.onerror = refresh
  void listenForDeepLinks(selectMessage).then((unlisten) => {
    unlistenDeepLinks = unlisten
  })
  void listenForNotificationActions(selectMessage).then((unlisten) => {
    unlistenNotificationActions = unlisten
  })
})

onUnmounted(() => {
  events?.close()
  unlistenDeepLinks()
  unlistenNotificationActions()
})
</script>

<template>
  <main>
    <header>
      <h1>Carbon</h1>
      <input
        v-model="query"
        type="search"
        placeholder="Search messages"
        aria-label="Search messages"
      />
      <input v-model="source" placeholder="Filter by source" aria-label="Filter by source" />
      <label><input v-model="unreadOnly" type="checkbox" /> Unread only ({{ unreadCount }})</label>
    </header>
    <p v-if="listHasError" class="error" role="alert">
      Unable to load messages. Check the Carbon backend connection and try again.
    </p>
    <section>
      <div>
        <MessageList :items="items" :selected-id="selectedId" @select="selectMessage" />
        <button
          v-if="!query && hasNextPage"
          :disabled="isFetchingNextPage"
          @click="list.fetchNextPage()"
        >
          {{ isFetchingNextPage ? 'Loading…' : 'Load more' }}
        </button>
      </div>
      <MessageDetail
        :message="selectedMessage"
        @read="toggleRead"
        @remove="remove"
        @open-external="(url) => void openExternalUrl(url)"
      />
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
  flex-wrap: wrap;
  gap: 0.75rem;
  align-items: center;
}
input {
  padding: 0.7rem;
}
section {
  display: grid;
  grid-template-columns: 40% 1fr;
  gap: 1rem;
}
.error {
  color: #b91c1c;
}
@media (max-width: 700px) {
  section {
    grid-template-columns: 1fr;
  }
}
</style>
