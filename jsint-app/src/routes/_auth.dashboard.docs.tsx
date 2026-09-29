import { createFileRoute, Link } from '@tanstack/react-router'
import { useQuery } from '@tanstack/react-query'
import {
  Children,
  isValidElement,
  useEffect,
  useMemo,
  useRef,
  type ReactElement,
  type ReactNode
} from 'react'
import type { Components } from 'react-markdown'
import { AlertTriangle, ArrowLeft, ArrowRight, Info, Lightbulb } from 'lucide-react'
import { docsService } from '@/api/docs-service'
import { docsKeys } from '@/api/query-keys'
import { MemoizedMarkdown } from '@/components/chat/memoized-markdown'
import { Skeleton } from '@/components/ui/skeleton'
import { cn } from '@/lib/utils'

export const Route = createFileRoute('/_auth/dashboard/docs')({
  // The chapter lives in the URL so a page can be linked, bookmarked and
  // reloaded on — plain path params can't carry the "getting-started/flows"
  // style slugs without a splat route.
  validateSearch: (search: Record<string, unknown>): { chapter?: string } => ({
    chapter: typeof search.chapter === 'string' ? search.chapter : undefined
  }),
  component: DocumentationPage
})

const CALLOUTS = {
  warning: {
    Icon: AlertTriangle,
    className:
      'border-amber-500/40 bg-amber-500/10 text-amber-950 dark:text-amber-50'
  },
  info: { Icon: Info, className: 'border-sky-500/40 bg-sky-500/10 text-sky-950 dark:text-sky-50' },
  tip: {
    Icon: Lightbulb,
    className:
      'border-emerald-500/40 bg-emerald-500/10 text-emerald-950 dark:text-emerald-50'
  }
} as const

type CalloutVariant = keyof typeof CALLOUTS

function textOf(node: ReactNode): string | null {
  if (typeof node === 'string') return node
  if (typeof node === 'number') return String(node)
  // react-markdown hands children down as arrays, not bare strings.
  if (Array.isArray(node)) return node.map(textOf).join('')
  if (isValidElement(node)) {
    return textOf((node as ReactElement<{ children?: ReactNode }>).props.children)
  }
  return null
}

/**
 * The API turns the docs' MDX `<Alert>` blocks into admonition-style
 * blockquote alerts (`> [!WARNING]` + `> **Title**`). Anything without that
 * marker is an ordinary quote and keeps the prose styling.
 */
function Callout({ children }: { children?: ReactNode }) {
  // react-markdown interleaves the source's newlines as text children, so the
  // marker paragraph is not reliably items[0] until they are dropped.
  const items = Children.toArray(children).filter(
    (child) => typeof child !== 'string' || child.trim() !== ''
  )
  const marker = textOf(items[0])?.trim()
  // Canonical form is the marker alone (`> [!WARNING]` then a blank quote
  // line); tolerate text trailing it on the same paragraph so nothing is lost.
  const parsed = marker ? /^\[!(\w+)\]\s*([\s\S]*)$/.exec(marker) : null
  const variant = parsed?.[1].toLowerCase()

  if (!variant || !(variant in CALLOUTS)) {
    return (
      <blockquote className="border-l-2 border-border pl-4 text-muted-foreground italic">
        {children}
      </blockquote>
    )
  }

  const { Icon, className } = CALLOUTS[variant as CalloutVariant]
  return (
    <div className={cn('not-prose my-6 flex gap-3 rounded-lg border px-4 py-3', className)}>
      <Icon className="mt-0.5 size-4 shrink-0" strokeWidth={1.8} />
      <div className="prose prose-sm max-w-none dark:prose-invert [&>*:first-child]:mt-0 [&>*:last-child]:mb-0">
        {parsed?.[2] ? <p>{parsed[2]}</p> : null}
        {items.slice(1)}
      </div>
    </div>
  )
}

/** Docs cross-link with library-style `/docs/<chapter>` paths; keep them in the book. */
function DocLink({ href, children }: { href?: string; children?: ReactNode }) {
  if (href?.startsWith('/docs/')) {
    const chapter = href.replace(/^\/docs\//, '').replace(/\.mdx?$/, '').replace(/#.*$/, '')
    return (
      <Link
        to="/dashboard/docs"
        search={{ chapter }}
        className="text-primary underline underline-offset-4 hover:no-underline"
      >
        {children}
      </Link>
    )
  }

  if (href?.startsWith('#')) {
    return <a href={href}>{children}</a>
  }

  return (
    <a
      href={href}
      target="_blank"
      rel="noreferrer"
      className="text-primary underline underline-offset-4 hover:no-underline"
    >
      {children}
    </a>
  )
}

// Module scope on purpose: a fresh object each render would defeat the
// per-block memoisation inside MemoizedMarkdown.
const DOC_COMPONENTS: Components = { a: DocLink, blockquote: Callout }

function DocumentationPage() {
  const { chapter } = Route.useSearch()
  const articleRef = useRef<HTMLDivElement>(null)

  const chaptersQuery = useQuery({
    queryKey: docsKeys.chapters,
    queryFn: docsService.list,
    staleTime: Infinity
  })
  const chapters = useMemo(() => chaptersQuery.data ?? [], [chaptersQuery.data])
  const activeSlug = chapter ?? chapters[0]?.slug

  const docQuery = useQuery({
    queryKey: docsKeys.chapter(activeSlug ?? ''),
    queryFn: () => docsService.get(activeSlug as string),
    enabled: Boolean(activeSlug),
    // A chapter that is not in the index never will be: retrying only delays
    // the "not found" message.
    retry: false
  })

  const groups = useMemo(() => {
    const grouped: { category: string; chapters: typeof chapters }[] = []
    for (const entry of chapters) {
      const last = grouped[grouped.length - 1]
      if (last?.category === entry.category) last.chapters.push(entry)
      else grouped.push({ category: entry.category, chapters: [entry] })
    }
    return grouped
  }, [chapters])

  const position = chapters.findIndex((entry) => entry.slug === activeSlug)
  const previous = position > 0 ? chapters[position - 1] : undefined
  const next = position >= 0 && position < chapters.length - 1 ? chapters[position + 1] : undefined

  // A new chapter is a new page: start reading at the top, not wherever the
  // previous one was left scrolled to.
  useEffect(() => {
    articleRef.current?.scrollTo({ top: 0 })
  }, [activeSlug])

  return (
    <div className="flex h-full min-h-0 w-full bg-background">
      <aside className="hidden w-72 shrink-0 flex-col overflow-y-auto border-r border-border bg-card/40 lg:flex">
        <div className="px-5 pt-6">
          <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            Documentation
          </p>
          {chapters.length > 0 && (
            <p className="mt-1 text-xs text-muted-foreground/70">
              {chapters.length} chapters
            </p>
          )}
        </div>

        {chaptersQuery.isLoading && (
          <div className="space-y-2 p-5">
            {Array.from({ length: 8 }).map((_, index) => (
              <Skeleton key={index} className="h-5 w-full" />
            ))}
          </div>
        )}

        {groups.map((group) => (
          <div key={group.category} className="pb-2">
            <p className="px-5 pb-1 pt-4 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground/70">
              {group.category}
            </p>
            <ul>
              {group.chapters.map((entry) => (
                <li key={entry.slug}>
                  <Link
                    to="/dashboard/docs"
                    search={{ chapter: entry.slug }}
                    className={cn(
                      'block border-l-2 px-5 py-1.5 text-sm transition-colors',
                      entry.slug === activeSlug
                        ? 'border-primary bg-muted/60 font-medium text-foreground'
                        : 'border-transparent text-muted-foreground hover:bg-muted/40 hover:text-foreground'
                    )}
                  >
                    {entry.title}
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </aside>

      <div ref={articleRef} className="min-w-0 flex-1 overflow-y-auto">
        {/* Below lg the chapter list collapses to a scrollable strip. */}
        <div className="flex gap-2 overflow-x-auto border-b border-border px-4 py-2 lg:hidden">
          {chapters.map((entry) => (
            <Link
              key={entry.slug}
              to="/dashboard/docs"
              search={{ chapter: entry.slug }}
              className={cn(
                'shrink-0 rounded-full border border-border px-3 py-1 text-xs',
                entry.slug === activeSlug
                  ? 'bg-muted font-medium text-foreground'
                  : 'text-muted-foreground'
              )}
            >
              {entry.title}
            </Link>
          ))}
        </div>

        <article className="mx-auto max-w-3xl px-6 py-10 pb-24 sm:px-8">
          {docQuery.isLoading && (
            <div className="space-y-4">
              <Skeleton className="h-4 w-24" />
              <Skeleton className="h-9 w-2/3" />
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-64 w-full" />
            </div>
          )}

          {docQuery.isError && (
            <div className="rounded-lg border border-border p-6">
              <h2 className="text-lg font-semibold text-foreground">Chapter not found</h2>
              <p className="mt-1 text-sm text-muted-foreground">
                {chapter ? `There is no chapter at "${chapter}".` : 'Pick a chapter to start reading.'}
              </p>
              {chapters[0] && (
                <Link
                  to="/dashboard/docs"
                  search={{ chapter: chapters[0].slug }}
                  className="mt-4 inline-block text-sm text-primary underline underline-offset-4"
                >
                  Start at {chapters[0].title}
                </Link>
              )}
            </div>
          )}

          {docQuery.data && (
            <>
              <p className="text-xs font-semibold uppercase tracking-wider text-primary">
                {docQuery.data.category}
              </p>
              <h1 className="mt-2 text-3xl font-bold tracking-tight text-foreground">
                {docQuery.data.title}
              </h1>
              {docQuery.data.description && (
                <p className="mt-3 text-base text-muted-foreground">
                  {docQuery.data.description}
                </p>
              )}

              <div className="my-8 h-px bg-border" />

              <MemoizedMarkdown
                content={docQuery.data.content}
                id={docQuery.data.slug}
                components={DOC_COMPONENTS}
                className="max-w-none text-base! leading-7"
              />

              {(previous || next) && (
                <nav className="mt-14 flex items-stretch justify-between gap-4 border-t border-border pt-6">
                  {previous ? (
                    <Link
                      to="/dashboard/docs"
                      search={{ chapter: previous.slug }}
                      className="group flex min-w-0 max-w-[45%] flex-col rounded-lg border border-border px-4 py-3 hover:bg-muted/40"
                    >
                      <span className="flex items-center gap-1 text-xs text-muted-foreground">
                        <ArrowLeft className="size-3" /> Previous
                      </span>
                      <span className="mt-1 truncate text-sm font-medium text-foreground">
                        {previous.title}
                      </span>
                    </Link>
                  ) : (
                    <span />
                  )}

                  {next ? (
                    <Link
                      to="/dashboard/docs"
                      search={{ chapter: next.slug }}
                      className="group ml-auto flex min-w-0 max-w-[45%] flex-col items-end rounded-lg border border-border px-4 py-3 text-right hover:bg-muted/40"
                    >
                      <span className="flex items-center gap-1 text-xs text-muted-foreground">
                        Next <ArrowRight className="size-3" />
                      </span>
                      <span className="mt-1 truncate text-sm font-medium text-foreground">
                        {next.title}
                      </span>
                    </Link>
                  ) : (
                    <span />
                  )}
                </nav>
              )}
            </>
          )}
        </article>
      </div>
    </div>
  )
}
