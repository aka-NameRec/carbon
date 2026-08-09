import { getCurrent, onOpenUrl } from '@tauri-apps/plugin-deep-link'
import { invoke } from '@tauri-apps/api/core'
import {
  isPermissionGranted,
  requestPermission,
  sendNotification,
} from '@tauri-apps/plugin-notification'

type Unlisten = () => void
export type TrayState = 'idle' | 'unread' | 'error'

const PUBLIC_ID_PATTERN = /^[a-z0-9]+-[a-z0-9-]+-[a-z0-9]{8}$/

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

export async function notifyAboutNewMessage(): Promise<void> {
  if (!isDesktopShell()) return

  const permitted = (await isPermissionGranted()) || (await requestPermission()) === 'granted'
  if (permitted) sendNotification({ title: 'Carbon', body: 'New message received' })
}

export async function setTrayState(state: TrayState): Promise<void> {
  if (!isDesktopShell()) return
  await invoke('set_tray_state', { state })
}
