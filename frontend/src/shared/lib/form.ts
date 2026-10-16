import type { FieldValues, Path, UseFormSetError } from 'react-hook-form'
import { toast } from 'sonner'

import { ApiError } from '@/shared/api'

/**
 * Ошибка сервера в форме: если код известен — под нужным полем, иначе — общим сообщением.
 * Возвращает текст для общей плашки формы.
 */
export function applyServerError<T extends FieldValues>(
  error: unknown,
  setError: UseFormSetError<T>,
  fields: Partial<Record<string, Path<T>>> = {},
): string | null {
  const message = error instanceof ApiError ? error.message : 'Что-то пошло не так. Попробуйте ещё раз'
  const field = error instanceof ApiError ? fields[error.code] : undefined
  if (field) {
    setError(field, { type: 'server', message })
    return null
  }
  return message
}

export const toastError = (error: unknown) =>
  toast.error(error instanceof ApiError ? error.message : 'Что-то пошло не так. Попробуйте ещё раз')
