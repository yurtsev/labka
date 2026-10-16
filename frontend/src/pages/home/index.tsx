import { useUser } from '@/entities/session'

import { StudentHome } from './student-home'
import { TeacherHome } from './teacher-home'

export function HomePage() {
  const user = useUser()
  return (
    user.role === 'teacher' ? <TeacherHome /> : <StudentHome />
  )
}
