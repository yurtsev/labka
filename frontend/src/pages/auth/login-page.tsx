import { useState } from 'react'
import { Link } from 'react-router'

import { LoginForm } from '@/features/auth'
import { API_MODE } from '@/shared/config'
import { Button } from '@/shared/ui/button'
import { FieldSeparator } from '@/shared/ui/field'

import { AuthLayout } from './auth-layout'

export function LoginPage() {
  const [demo, setDemo] = useState<{ email: string; password: string }>()
  return (
    <AuthLayout
      title="Вход"
      description="Используйте учётную запись Labka"
      footer={
        <>
          Студент без аккаунта?{' '}
          <Link to="/register" className="font-medium text-primary hover:underline">
            Регистрация студента
          </Link>
        </>
      }
    >
      <LoginForm demo={demo} />
      {API_MODE === 'mock' && (
        <div className="flex flex-col gap-4">
          <FieldSeparator>демо-доступ</FieldSeparator>
          <div className="grid grid-cols-2 gap-2">
            <Button variant="outline" onClick={async () => setDemo((await import('@/shared/api/mock')).DEMO_ACCOUNTS.student)}>
              Студент
            </Button>
            <Button variant="outline" onClick={async () => setDemo((await import('@/shared/api/mock')).DEMO_ACCOUNTS.teacher)}>
              Преподаватель
            </Button>
          </div>
        </div>
      )}
    </AuthLayout>
  )
}
