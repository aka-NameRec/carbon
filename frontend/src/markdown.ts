import DOMPurify from 'dompurify'
import MarkdownIt from 'markdown-it'

const ALLOWED_URI_REGEXP = /^(?:(?:https?|tg|obsidian):|[^a-z]|[a-z+.-]+(?:[^a-z+.-:]|$))/i

const markdown = new MarkdownIt({
  html: false,
  linkify: true,
  typographer: true,
})

markdown.validateLink = (url: string) => ALLOWED_URI_REGEXP.test(url)

export function renderMarkdown(source: string): string {
  return DOMPurify.sanitize(markdown.render(source), {
    ALLOWED_ATTR: ['href', 'title', 'target', 'rel'],
    ALLOWED_TAGS: [
      'a',
      'blockquote',
      'br',
      'code',
      'em',
      'h1',
      'h2',
      'h3',
      'h4',
      'h5',
      'h6',
      'li',
      'ol',
      'p',
      'pre',
      'strong',
      'ul',
    ],
    ALLOWED_URI_REGEXP,
  })
}
