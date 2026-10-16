import { Link } from 'react-router'

import { RegisterForm } from '@/features/auth'

import { AuthLayout } from './auth-layout'

export function RegisterPage() {
  return (
    <AuthLayout
      title="Регистрация студента"
      description="Код группы выдаёт администратор. Преподавателям аккаунт создаёт администратор."
      footer={
        <>
          Уже есть аккаунт?{' '}
          <Link to="/login" className="font-medium text-primary hover:underline">
            Войти
          </Link>
        </>
      }
    >
      <RegisterForm />
    </AuthLayout>
  )
}
