import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useRef } from 'react'
import { toast } from 'sonner'

import { removeAvatar, setAvatar, UserAvatar } from '@/entities/user'
import type { Profile } from '@/shared/api'
import { LIMITS } from '@/shared/config'
import { toastError } from '@/shared/lib/form'
import { fileSize } from '@/shared/lib/format'
import { fitsSizeLimit } from '@/shared/lib/validation'
import { Button } from '@/shared/ui/button'
import { CameraIcon, Trash2Icon } from '@/shared/ui/icons'
import { Spinner } from '@/shared/ui/spinner'

const ACCEPT = 'image/png,image/jpeg,image/webp,image/gif'

export function AvatarUpload({ profile }: { profile: Profile }) {
  const queryClient = useQueryClient()
  const input = useRef<HTMLInputElement>(null)
  const onSuccess = (p: Profile) => queryClient.setQueryData(['profile'], p)
  const upload = useMutation({ mutationFn: setAvatar, onSuccess: (p) => (onSuccess(p), toast.success('Аватарка обновлена')), onError: toastError })
  const remove = useMutation({ mutationFn: removeAvatar, onSuccess, onError: toastError })
  const busy = upload.isPending || remove.isPending

  return (
    <div className="flex items-center gap-5">
      <div className="relative">
        <UserAvatar person={profile} src={profile.avatar_url} className="size-20 text-lg" />
        {busy && (
          <span className="absolute inset-0 grid place-items-center rounded-full bg-background/70">
            <Spinner />
          </span>
        )}
      </div>
      <div className="flex flex-col gap-2">
        <input
          ref={input}
          type="file"
          accept={ACCEPT}
          className="sr-only"
          aria-label="Выбрать изображение"
          onChange={(e) => {
            const file = e.target.files?.[0]
            e.target.value = ''
            if (!file) return
            if (!ACCEPT.split(',').includes(file.type)) return toast.error('Подойдёт PNG, JPEG, WebP или GIF')
            if (!fitsSizeLimit(file)) return toast.error(`Файл больше ${fileSize(LIMITS.maxFileSizeBytes)}`)
            upload.mutate(file)
          }}
        />
        <div className="flex gap-2">
          <Button variant="outline" disabled={busy} onClick={() => input.current?.click()}>
            <CameraIcon data-icon="inline-start" />
            {profile.avatar_url ? 'Заменить' : 'Загрузить'}
          </Button>
          {profile.avatar_url && (
            <Button variant="ghost" disabled={busy} onClick={() => remove.mutate()}>
              <Trash2Icon data-icon="inline-start" />
              Убрать
            </Button>
          )}
        </div>
        <span className="text-xs text-muted-foreground">PNG, JPEG, WebP или GIF до {fileSize(LIMITS.maxFileSizeBytes)}</span>
      </div>
    </div>
  )
}
