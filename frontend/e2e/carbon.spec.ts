import { expect, test } from '@playwright/test'

const message = {
  public_id: 'ft4w9j-tg-mon-1a2b3c4d',
  source: 'tg-mon',
  title: 'Новое уведомление',
  occurred_at: '2026-08-09T07:42:18Z',
  received_at: '2026-08-09T07:42:18Z',
  read_at: null,
  tags: ['important'],
}

test('renders a grouped message and blocks unsafe Markdown links', async ({ page }) => {
  await page.route('**/api/v1/events', (route) => route.abort())
  await page.route('**/api/v1/messages/**', (route) =>
    route.fulfill({
      contentType: 'application/json',
      body: JSON.stringify({
        ...message,
        body_markdown:
          '[Safe](https://example.test) [Unsafe](javascript:alert(1)) <script>alert(1)</script>',
      }),
    }),
  )
  await page.route('**/api/v1/messages', (route) =>
    route.fulfill({
      contentType: 'application/json',
      body: JSON.stringify({ items: [message], next_cursor: null, unread_count: 1 }),
    }),
  )

  await page.goto('/')
  await page.getByRole('button', { name: /Новое уведомление/ }).click()

  await expect(page.getByRole('heading', { name: 'tg-mon' })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Новое уведомление' })).toBeVisible()
  await expect(page.locator('.message-body a[href="https://example.test"]')).toBeVisible()
  await expect(page.locator('.message-body a[href^="javascript:"]')).toHaveCount(0)
  await expect(page.locator('.message-body script')).toHaveCount(0)
})
