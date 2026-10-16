import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { toast } from 'sonner'
import { z } from 'zod'

import { changePassword } from '@/entities/session'
import { applyServerError } from '@/shared/lib/form'
import { passwordSchema, passwordHint } from '@/shared/lib/validation'
import { Button } from '@/shared/ui/button'
import { Field, FieldDescription, FieldError, FieldGroup, FieldLabel } from '@/shared/ui/field'
import { Input } from '@/shared/ui/input'
import { Spinner } from '@/shared/ui/spinner'

const schema = z
  .object({ current_password: z.string().min(1, 'Введите текущий пароль'), new_password: passwordSchema, repeat: z.string() })
  .refine((v) => v.new_password === v.repeat, { path: ['repeat'], message: 'Пароли не совпадают' })
  .refine((v) => v.new_password !== v.current_password, { path: ['new_password'], message: 'Новый пароль совпадает с текущим' })
type Values = z.infer<typeof schema>

export function ChangePasswordForm() {
  const form = useForm<Values>({ resolver: zodResolver(schema), mode: 'onTouched', defaultValues: { current_password: '', new_password: '', repeat: '' } })
  const mutation = useMutation({
    mutationFn: (v: Values) => changePassword({ current_password: v.current_password, new_password: v.new_password }),
    onSuccess: () => {
      toast.success('Пароль изменён', { description: 'Остальные сессии завершены.' })
      form.reset()
    },
    onError: (e) => {
      const msg = applyServerError(e, form.setError, { 'auth.wrong_current_password': 'current_password' })
      if (msg) toast.error(msg)
    },
  })
  const { errors } = form.formState
  const input = (name: keyof Values, label: string, hint?: string) => (
    <Field data-invalid={!!errors[name]}>
      <FieldLabel htmlFor={name}>{label}</FieldLabel>
      <Input id={name} type="password" autoComplete={name === 'current_password' ? 'current-password' : 'new-password'} aria-invalid={!!errors[name]} {...form.register(name)} />
      {hint && !errors[name] && <FieldDescription>{hint}</FieldDescription>}
      <FieldError errors={[errors[name]]} />
    </Field>
  )
  return (
    <form noValidate onSubmit={form.handleSubmit((v) => mutation.mutate(v))}>
      <FieldGroup>
        {input('current_password', 'Текущий пароль')}
        {input('new_password', 'Новый пароль', passwordHint)}
        {input('repeat', 'Повтор нового пароля')}
        <Button type="submit" variant="outline" className="w-fit" disabled={mutation.isPending}>
          {mutation.isPending && <Spinner data-icon="inline-start" />}
          Сменить пароль
        </Button>
      </FieldGroup>
    </form>
  )
}
