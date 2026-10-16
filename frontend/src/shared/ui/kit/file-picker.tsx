import { useId, useRef } from 'react'

import { fileSize } from '@/shared/lib/format'
import { fitsSizeLimit } from '@/shared/lib/validation'
import { Button } from '@/shared/ui/button'
import { FileTypeIcon } from '@/shared/ui/file-icons'
import { PaperclipIcon, XIcon } from '@/shared/ui/icons'


type Props = {
  value: File[]
  onChange: (files: File[]) => void
  disabled?: boolean
  accept?: string
  invalid?: boolean
}

/** Выбор нескольких файлов. Файлы держатся в форме и уходят в S3 только при отправке. */
export function FilePicker({ value, onChange, disabled, accept, invalid }: Props) {
  const input = useRef<HTMLInputElement>(null)
  const id = useId()
  return (
    <div className="flex flex-col gap-2">
      <input
        ref={input}
        id={id}
        type="file"
        multiple
        accept={accept}
        className="sr-only"
        disabled={disabled}
        aria-invalid={invalid}
        onChange={(e) => {
          const picked = Array.from(e.target.files ?? [])
          onChange([...value, ...picked.filter((f) => !value.some((v) => v.name === f.name && v.size === f.size))])
          e.target.value = ''
        }}
      />
      <Button type="button" variant="outline" className="w-fit" disabled={disabled} onClick={() => input.current?.click()}>
        <PaperclipIcon data-icon="inline-start" />
        Прикрепить файлы
      </Button>
      {value.length > 0 && (
        <ul className="flex flex-col gap-2">
          {value.map((f, i) => (
            <li key={`${f.name}-${i}`} className="flex h-10 items-center gap-2 rounded-lg border pr-1 pl-3 text-sm">
              <FileTypeIcon fileName={f.name} contentType={f.type} className="size-5 shrink-0" />
              <span className="min-w-0 flex-1 truncate">{f.name}</span>
              <span
                className={!fitsSizeLimit(f) ? 'shrink-0 text-xs text-destructive tabular-nums' : 'shrink-0 text-xs text-muted-foreground tabular-nums'}
              >
                {fileSize(f.size)}
              </span>
              <Button
                type="button"
                variant="ghost"
                size="icon-sm"
                aria-label={`Убрать ${f.name}`}
                disabled={disabled}
                onClick={() => onChange(value.filter((_, j) => j !== i))}
              >
                <XIcon />
              </Button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
