/**
 * Лимиты форм из frontend/.env — те же значения, что в backend/config.toml. Сервер проверяет их сам;
 * здесь они нужны для понятной ошибки под полем. Наличие переменных проверяет vite.config.ts.
 */
export const LIMITS = {
  maxFileSizeBytes: Number(import.meta.env.VITE_MAX_FILE_SIZE_BYTES),
  passwordMinLength: Number(import.meta.env.VITE_PASSWORD_MIN_LENGTH),
  passwordMaxLength: Number(import.meta.env.VITE_PASSWORD_MAX_LENGTH),
}
