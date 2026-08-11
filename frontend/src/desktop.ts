import { getCurrent, onOpenUrl } from '@tauri-apps/plugin-deep-link'
import { invoke } from '@tauri-apps/api/core'
import { openUrl } from '@tauri-apps/plugin-opener'
import {
  isPermissionGranted,
  onAction,
  requestPermission,
  sendNotification,
} from '@tauri-apps/plugin-notification'

type Unlisten = () => void
export type TrayState = 'idle' | 'unread' | 'important' | 'error'

const PUBLIC_ID_PATTERN = /^[a-z0-9]+-[a-z0-9-]+-[a-z0-9]{8}$/
const DEFAULT_ALLOWED_SCHEMES = ['https:', 'http:', 'tg:', 'obsidian:']

function isDesktopShell(): boolean {
  return '__TAURI_INTERNALS__' in window
}

export function messageIdFromUrl(rawUrl: string): string | null {
  try {
    const url = new URL(rawUrl)
    if (url.protocol !== 'carbon:' || url.hostname !== 'message') return null

    const [messageId, extraPath] = url.pathname.split('/').filter(Boolean)
    return messageId && !extraPath && PUBLIC_ID_PATTERN.test(messageId) ? messageId : null
  } catch {
    return null
  }
}

export async function listenForDeepLinks(selectMessage: (id: string) => void): Promise<Unlisten> {
  if (!isDesktopShell()) return () => undefined

  const handleUrls = (urls: string[]) => {
    for (const rawUrl of urls) {
      const messageId = messageIdFromUrl(rawUrl)
      if (messageId) selectMessage(messageId)
    }
  }

  handleUrls((await getCurrent()) ?? [])
  return onOpenUrl(handleUrls)
}

export async function notifyAboutNewMessage(publicId: string): Promise<void> {
  if (!isDesktopShell()) return

  const permitted = (await isPermissionGranted()) || (await requestPermission()) === 'granted'
  if (permitted) {
    sendNotification({
      title: 'Carbon',
      body: 'New message received',
      autoCancel: true,
      extra: { publicId },
    })
  }
}

export async function listenForNotificationActions(
  selectMessage: (id: string) => void,
): Promise<Unlisten> {
  if (!isDesktopShell()) return () => undefined
  const listener = await onAction((notification) => {
    const publicId = notification.extra?.publicId
    if (typeof publicId === 'string' && PUBLIC_ID_PATTERN.test(publicId)) selectMessage(publicId)
  })
  return () => listener.unregister()
}

export async function setTrayState(state: TrayState): Promise<void> {
  if (!isDesktopShell()) return
  await invoke('set_tray_state', { state })
}

export async function openExternalUrl(rawUrl: string): Promise<void> {
  const url = new URL(rawUrl)
  const configured = import.meta.env.VITE_ALLOWED_URI_SCHEMES?.split(',')
    .map((scheme: string) => scheme.trim().toLowerCase())
    .filter(Boolean)
  const allowed = configured?.length ? configured : DEFAULT_ALLOWED_SCHEMES
  if (!allowed.includes(url.protocol))
    throw new Error(`Blocked external URI scheme: ${url.protocol}`)
  if (isDesktopShell()) {
    await openUrl(url)
    return
  }
  window.open(url, '_blank', 'noopener,noreferrer')
}
