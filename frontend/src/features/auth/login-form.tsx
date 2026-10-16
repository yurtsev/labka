import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { useLocation, useNavigate } from 'react-router'
import { z } from 'zod'

import { login } from '@/entities/session'
import { applyServerError } from '@/shared/lib/form'
import { emailSchema, passwordSchema } from '@/shared/lib/validation'
import { Alert, AlertTitle } from '@/shared/ui/alert'
import { Button } from '@/shared/ui/button'
import { Field, FieldError, FieldGroup, FieldLabel } from '@/shared/ui/field'
import { AlertCircleIcon } from '@/shared/ui/icons'
import { Input } from '@/shared/ui/input'
import { Spinner } from '@/shared/ui/spinner'

const schema = z.object({ email: emailSchema, password: passwordSchema })
type Values = z.infer<typeof schema>

export function LoginForm() {
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const from = (useLocation().state as { from?: string } | null)?.from ?? '/'
  const [formError, setFormError] = useState<string | null>(null)
  const form = useForm<Values>({ resolver: zodResolver(schema), defaultValues: { email: '', password: '' } })

  const mutation = useMutation({
    mutationFn: login,
    onSuccess: (user) => {
      queryClient.setQueryData(['session'], user)
      navigate(from, { replace: true })
    },
    onError: (e) => setFormError(applyServerError(e, form.setError)),
  })

  const { errors } = form.formState
  return (
    <form
      noValidate
      onSubmit={form.handleSubmit((v) => {
        setFormError(null)
        mutation.mutate(v)
      })}
    >
      <FieldGroup>
        {formError && (
          <Alert variant="destructive" className="animate-in fade-in-0 slide-in-from-top-1">
            <AlertCircleIcon />
            <AlertTitle>{formError}</AlertTitle>
          </Alert>
        )}
        <Field data-invalid={!!errors.email}>
          <FieldLabel htmlFor="email">Email</FieldLabel>
          <Input id="email" type="email" autoComplete="email" autoFocus aria-invalid={!!errors.email} {...form.register('email')} />
          <FieldError errors={[errors.email]} />
        </Field>
        <Field data-invalid={!!errors.password}>
          <FieldLabel htmlFor="password">Пароль</FieldLabel>
          <Input id="password" type="password" autoComplete="current-password" aria-invalid={!!errors.password} {...form.register('password')} />
          <FieldError errors={[errors.password]} />
        </Field>
        <Button type="submit" className="self-end" disabled={mutation.isPending}>
          {mutation.isPending && <Spinner data-icon="inline-start" />}
          Войти
        </Button>
      </FieldGroup>
    </form>
  )
}
