
import type { FileInfo } from '@/shared/api'
import { fileSize } from '@/shared/lib/format'
import { cn } from '@/shared/lib/utils'
import { FileTypeIcon } from '@/shared/ui/file-icons'

/** Файлы со ссылками на скачивание: у задания, материала и попытки. */
export function FileList({ files, className }: { files: FileInfo[]; className?: string }) {
  if (!files.length) return null
  return (
    <ul className={cn('flex flex-wrap gap-2', className)}>
      {files.map((f) => {
        return (
          <li key={f.id}>
            <a
              href={f.download_url}
              download={f.file_name}
              className="group flex h-10 max-w-80 items-center gap-2 rounded-lg border pr-4 pl-3 text-sm transition-colors hover:bg-foreground/6 focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
            >
              <FileTypeIcon fileName={f.file_name} contentType={f.content_type} className="size-5 shrink-0" />
              <span className="truncate">{f.file_name}</span>
              <span className="shrink-0 text-xs text-muted-foreground tabular-nums">{fileSize(f.file_size)}</span>
            </a>
          </li>
        )
      })}
    </ul>
  )
}

