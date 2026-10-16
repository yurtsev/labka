import { Link } from 'react-router'

import { LoginForm } from '@/features/auth'

import { AuthLayout } from './auth-layout'

export function LoginPage() {
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
      <LoginForm />
    </AuthLayout>
  )
}
