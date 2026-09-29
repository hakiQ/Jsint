import { marked } from 'marked'
import { memo, useMemo } from 'react'
import ReactMarkdown, { type Components } from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { dracula } from 'react-syntax-highlighter/dist/esm/styles/prism'
import { cn } from '@/lib/utils'
import { CopyButton } from '../copy'

function parseMarkdownIntoBlocks(markdown: string): string[] {
  const tokens = marked.lexer(markdown)
  return tokens.map((token) => token.raw)
}

const MemoizedMarkdownBlock = memo(
  ({ content, components }: { content: string; components?: Components }) => {
    return (
      <ReactMarkdown
        components={{
          code({ node: _node, className, children, ...props }) {
            const match = /language-(\w+)/.exec(className || '')
            return match ? (
              <div className="relative">
                <SyntaxHighlighter
                  style={dracula}
                  language={match[1]}
                  PreTag="div"
                  className="rounded border border-border bg-muted px-1 py-0.5 m-0! text-sm w-auto not-prose"
                  {...props}
                >
                  {String(children).replace(/\n$/, '')}
                </SyntaxHighlighter>
                <div className="absolute top-2 right-2">
                  <CopyButton content={String(children).replace(/\n$/, '')} />
                </div>
              </div>
            ) : (
              <code
                className={cn(
                  'rounded border border-border bg-muted text-primary font-normal w-full px-1 py-0.5 text-sm not-prose',
                  className
                )}
                {...props}
              >
                {children}
              </code>
            )
          },
          // Callers layer extra renderers on top — the docs reader maps links
          // back into the reader and turns blockquote alerts into callouts.
          ...components
        }}
        remarkPlugins={[remarkGfm]}
      >
        {content}
      </ReactMarkdown>
    )
  },
  (prevProps, nextProps) => {
    if (prevProps.content !== nextProps.content) return false
    if (prevProps.components !== nextProps.components) return false
    return true
  }
)

MemoizedMarkdownBlock.displayName = 'MemoizedMarkdownBlock'

export const MemoizedMarkdown = memo(
  ({
    content,
    id,
    components,
    className
  }: {
    content: string
    id: string
    components?: Components
    className?: string
  }) => {
    const blocks = useMemo(() => parseMarkdownIntoBlocks(content), [content])

    return (
      <div className={cn('prose max-w-none dark:prose-invert text-sm', className)}>
        {blocks.map((block, index) => (
          <MemoizedMarkdownBlock
            content={block}
            components={components}
            key={`${id}-block_${index}`}
          />
        ))}
      </div>
    )
  }
)

MemoizedMarkdown.displayName = 'MemoizedMarkdown'
