import { describe, expect, it } from 'vitest'

import { messageIdFromUrl } from './desktop'

describe('messageIdFromUrl', () => {
  it('accepts a Carbon message deep link', () => {
    expect(messageIdFromUrl('carbon://message/ft4w9j-tg-mon-1a2b3c4d')).toBe(
      'ft4w9j-tg-mon-1a2b3c4d',
    )
  })

  it.each([
    'https://message/ft4w9j-tg-mon-1a2b3c4d',
    'carbon://message/not-a-public-id',
    'carbon://message/ft4w9j-tg-mon-1a2b3c4d/extra',
    'not a URL',
  ])('rejects an invalid deep link: %s', (url) => {
    expect(messageIdFromUrl(url)).toBeNull()
  })
})
