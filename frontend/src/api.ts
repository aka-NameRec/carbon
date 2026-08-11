export interface Message {
  public_id: string
  source: string
  title: string
  severity: string
  occurred_at: string
  received_at: string
  read_at: string | null
  tags: string[]
  body_markdown?: string
  source_event_id?: string | null
}

export interface MessagePage {
  items: Message[]
  next_cursor: string | null
  unread_count: number
  unread_important_count: number
}

export interface MessageFilters {
  source?: string
  unread?: boolean
}
const base = import.meta.env.VITE_API_BASE ?? 'http://127.0.0.1:8000/api/v1'
async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const r = await fetch(`${base}${path}`, init)
  if (!r.ok) throw new Error(`API request failed: ${r.status}`)
  return r.status === 204 ? (undefined as T) : (r.json() as Promise<T>)
}
export const api = {
  list: (filters: MessageFilters = {}, cursor?: string | null) => {
    const params = new URLSearchParams()
    if (filters.source) params.set('source', filters.source)
    if (filters.unread) params.set('unread', 'true')
    if (cursor) params.set('cursor', cursor)
    const query = params.size ? `?${params}` : ''
    return request<MessagePage>(`/messages${query}`)
  },
  detail: (id: string) => request<Message>(`/messages/${id}`),
  search: (q: string) =>
    request<{ items: Message[] }>('/messages/search?q=' + encodeURIComponent(q)),
  read: (id: string) => request<void>(`/messages/${id}/read`, { method: 'POST' }),
  unread: (id: string) => request<void>(`/messages/${id}/unread`, { method: 'POST' }),
  remove: (id: string) => request<void>(`/messages/${id}`, { method: 'DELETE' }),
}
