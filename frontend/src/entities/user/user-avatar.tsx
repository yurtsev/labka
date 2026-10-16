import { colorFor } from '@/shared/lib/color'
import { initials } from '@/shared/lib/format'
import { cn } from '@/shared/lib/utils'
import { Avatar, AvatarFallback, AvatarImage } from '@/shared/ui/avatar'

type Props = {
  person: { last_name: string; first_name: string; middle_name: string | null }
  src?: string | null
  className?: string
}

/** Аватар как в аккаунте Google: фото или буквы на цветном круге. */
export function UserAvatar({ person, src, className }: Props) {
  return (
    <Avatar className={cn('size-9 after:hidden', className)}>
      {src && <AvatarImage src={src} alt="" />}
      <AvatarFallback className="text-sm font-medium text-white" style={{ backgroundColor: colorFor(`${person.last_name}${person.first_name}`) }}>
        {initials(person)}
      </AvatarFallback>
    </Avatar>
  )
}
