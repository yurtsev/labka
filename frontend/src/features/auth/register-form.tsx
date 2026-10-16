import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { useNavigate } from 'react-router'
import { z } from 'zod'

import { register } from '@/entities/session'
import { applyServerError } from '@/shared/lib/form'
import { emailSchema, passwordSchema, requiredText, passwordHint } from '@/shared/lib/validation'
import { Alert, AlertTitle } from '@/shared/ui/alert'
import { Button } from '@/shared/ui/button'
import { Field, FieldDescription, FieldError, FieldGroup, FieldLabel } from '@/shared/ui/field'
import { AlertCircleIcon } from '@/shared/ui/icons'
import { Input } from '@/shared/ui/input'
import { Spinner } from '@/shared/ui/spinner'

const schema = z
  .object({
    email: emailSchema,
    group_code: requiredText('Введите код группы'),
    last_name: requiredText('Введите фамилию'),
    first_name: requiredText('Введите имя'),
    middle_name: z.string().trim(),
    password: passwordSchema,
    password_repeat: z.string(),
  })
  .refine((v) => v.password === v.password_repeat, { path: ['password_repeat'], message: 'Пароли не совпадают' })
type Values = z.infer<typeof schema>

const FIELD_BY_CODE = {
  'auth.invalid_group_code': 'group_code',
  'auth.email_not_invited': 'email',
  'auth.email_already_registered': 'email',
} as const

export function RegisterForm() {
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const [formError, setFormError] = useState<string | null>(null)
  const form = useForm<Values>({
    resolver: zodResolver(schema),
    mode: 'onTouched',
    defaultValues: { email: '', group_code: '', last_name: '', first_name: '', middle_name: '', password: '', password_repeat: '' },
  })

  const mutation = useMutation({
    mutationFn: register,
    onSuccess: (user) => {
      queryClient.setQueryData(['session'], user)
      navigate('/', { replace: true })
    },
    onError: (e) => setFormError(applyServerError(e, form.setError, FIELD_BY_CODE)),
  })

  const { errors } = form.formState
  const field = (name: keyof Values, label: string, props: React.ComponentProps<'input'> = {}, hint?: string) => (
    <Field data-invalid={!!errors[name]}>
      <FieldLabel htmlFor={name}>{label}</FieldLabel>
      <Input id={name} aria-invalid={!!errors[name]} {...props} {...form.register(name)} />
      {hint && !errors[name] && <FieldDescription>{hint}</FieldDescription>}
      <FieldError errors={[errors[name]]} />
    </Field>
  )

  return (
    <form
      noValidate
      onSubmit={form.handleSubmit(({ password_repeat: _repeat, middle_name, ...v }) => {
        setFormError(null)
        mutation.mutate({ ...v, middle_name: middle_name || null })
      })}
    >
      <FieldGroup>
        {formError && (
          <Alert variant="destructive">
            <AlertCircleIcon />
            <AlertTitle>{formError}</AlertTitle>
          </Alert>
        )}
        {field('email', 'Email', { type: 'email', autoComplete: 'email', autoFocus: true }, 'Та же почта, что в списке вашей группы')}
        {field('group_code', 'Код группы', { autoComplete: 'off', placeholder: 'например, BVT-7Q4K' })}
        <div className="grid gap-4 sm:grid-cols-2">
          {field('last_name', 'Фамилия', { autoComplete: 'family-name' })}
          {field('first_name', 'Имя', { autoComplete: 'given-name' })}
        </div>
        {field('middle_name', 'Отчество', { autoComplete: 'additional-name' }, 'Если есть')}
        <div className="grid gap-4 sm:grid-cols-2">
          {field('password', 'Пароль', { type: 'password', autoComplete: 'new-password' }, passwordHint)}
          {field('password_repeat', 'Повтор пароля', { type: 'password', autoComplete: 'new-password' })}
        </div>
        <Button type="submit" className="self-end" disabled={mutation.isPending}>
          {mutation.isPending && <Spinner data-icon="inline-start" />}
          Зарегистрироваться
        </Button>
      </FieldGroup>
    </form>
  )
}
