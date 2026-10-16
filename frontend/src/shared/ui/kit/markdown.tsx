import ReactMarkdown from 'react-markdown'

import { cn } from '@/shared/lib/utils'

/** Markdown из описаний заданий, материалов и комментариев. */
export function Markdown({ children, className }: { children: string; className?: string }) {
  return (
    <div
      className={cn(
        'max-w-prose text-sm leading-relaxed text-foreground/90',
        '[&_p]:my-2 [&_p:first-child]:mt-0 [&_p:last-child]:mb-0',
        '[&_ul]:my-2 [&_ul]:list-disc [&_ul]:pl-5 [&_ol]:my-2 [&_ol]:list-decimal [&_ol]:pl-5 [&_li]:my-1',
        '[&_a]:text-lesson [&_a]:underline [&_a]:underline-offset-4',
        '[&_code]:rounded [&_code]:bg-muted [&_code]:px-1.5 [&_code]:py-0.5 [&_code]:text-[0.85em]',
        '[&_strong]:font-semibold',
        className,
      )}
    >
      <ReactMarkdown>{children}</ReactMarkdown>
    </div>
  )
}
