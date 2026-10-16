import { createBrowserRouter } from 'react-router'

import { LoginPage, RegisterPage } from '@/pages/auth'
import { HomePage } from '@/pages/home'
import { AppShell } from '@/widgets/app-shell'

import { GuestOnly, RequireAuth, TeacherOnly } from './guards'

// Вход и главная грузятся сразу, остальные страницы — отдельными частями при первом переходе.
const page = <M,>(load: () => Promise<M>, pick: (m: M) => React.ComponentType) => ({
  lazy: async () => ({ Component: pick(await load()) }),
})

export const router = createBrowserRouter([
  {
    element: <GuestOnly />,
    children: [
      { path: '/login', element: <LoginPage /> },
      { path: '/register', element: <RegisterPage /> },
    ],
  },
  {
    element: <RequireAuth />,
    children: [
      {
        element: <AppShell />,
        children: [
          { index: true, element: <HomePage /> },
          { path: 'calendar', ...page(() => import('@/pages/calendar'), (m) => m.CalendarPage) },
          { path: 'notifications', ...page(() => import('@/pages/notifications'), (m) => m.NotificationsPage) },
          { path: 'profile', ...page(() => import('@/pages/profile'), (m) => m.ProfilePage) },
          { path: 'courses/archive', ...page(() => import('@/pages/archive'), (m) => m.ArchivePage) },
          { path: 'courses/:courseId', ...page(() => import('@/pages/course'), (m) => m.CoursePage) },
          { path: 'courses/:courseId/assignments/:assignmentId', ...page(() => import('@/pages/assignment'), (m) => m.AssignmentPage) },
          {
            element: <TeacherOnly />,
            children: [
              { path: 'courses/new', ...page(() => import('@/pages/course-editor'), (m) => m.NewCoursePage) },
              { path: 'courses/:courseId/settings', ...page(() => import('@/pages/course-editor'), (m) => m.CourseSettingsPage) },
              { path: 'courses/:courseId/assignments/new', ...page(() => import('@/pages/assignment-editor'), (m) => m.NewAssignmentPage) },
              { path: 'courses/:courseId/assignments/:assignmentId/edit', ...page(() => import('@/pages/assignment-editor'), (m) => m.EditAssignmentPage) },
              { path: 'courses/:courseId/assignments/:assignmentId/students/:studentId', ...page(() => import('@/pages/review'), (m) => m.ReviewPage) },
              { path: 'reviews', ...page(() => import('@/pages/review-queue'), (m) => m.ReviewQueuePage) },
            ],
          },
          { path: '*', ...page(() => import('@/pages/not-found'), (m) => m.NotFoundPage) },
        ],
      },
    ],
  },
])

// Код страниц подгружаем заранее, когда браузер свободен: переход не ждёт сети и не мигает.
const PAGES = [
  () => import('@/pages/calendar'),
  () => import('@/pages/notifications'),
  () => import('@/pages/profile'),
  () => import('@/pages/archive'),
  () => import('@/pages/course'),
  () => import('@/pages/assignment'),
  () => import('@/pages/course-editor'),
  () => import('@/pages/assignment-editor'),
  () => import('@/pages/review'),
  () => import('@/pages/review-queue'),
  () => import('@/pages/not-found'),
]
const idle = window.requestIdleCallback ?? ((cb: () => void) => setTimeout(cb, 1500))
idle(() => PAGES.forEach((load) => load().catch(() => {})))
