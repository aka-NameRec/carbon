import { describe, expect, it } from 'vitest'

import { renderMarkdown } from './markdown'

describe('renderMarkdown', () => {
  it('renders Markdown while removing raw HTML and dangerous links', () => {
    const rendered = renderMarkdown(
      '[safe](https://example.test) [blocked](javascript:alert(1)) <img src=x onerror=alert(1)>',
    )

    expect(rendered).toContain('href="https://example.test"')
    expect(rendered).not.toContain('href="javascript:')
    expect(rendered).not.toContain('<img')
  })

  it('allows configured Carbon URI schemes', () => {
    expect(renderMarkdown('[Open](obsidian://open?vault=carbon)')).toContain('obsidian://open')
  })
})
