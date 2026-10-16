import { z } from 'zod'

import { LIMITS } from '@/shared/config'
import { fileSize } from '@/shared/lib/format'

// Правила совпадают с backend: длина пароля — из .env (как в backend/config.toml), почта — корректный адрес.
export const emailSchema = z.string().trim().min(1, 'Введите email').pipe(z.email('Неверный формат email'))
export const passwordSchema = z
  .string()
  .min(LIMITS.passwordMinLength, `Пароль — не короче ${LIMITS.passwordMinLength} символов`)
  .max(LIMITS.passwordMaxLength, `Пароль — не длиннее ${LIMITS.passwordMaxLength} символов`)
export const requiredText = (message: string) => z.string().trim().min(1, message)

/** Подсказка под полем нового пароля — по лимитам из .env. */
export const passwordHint = `От ${LIMITS.passwordMinLength} до ${LIMITS.passwordMaxLength} символов`

/** Файл не больше лимита из .env (тот же, что у backend). */
export const fitsSizeLimit = (file: File) => file.size <= LIMITS.maxFileSizeBytes

export const filesSchema = z
  .array(z.instanceof(File))
  .refine((files) => files.every(fitsSizeLimit), `Каждый файл — не больше ${fileSize(LIMITS.maxFileSizeBytes)}`)
