import {
  BellIcon,
  BookPlusIcon,
  CalendarClockIcon,
  CalendarSyncIcon,
  CheckCheckIcon,
  FilePenLineIcon,
  FilePlusIcon,
  FolderPlusIcon,
  GraduationCapIcon,
  InboxIcon,
  MegaphoneIcon,
  type Icon,
  PencilLineIcon,
} from '@/shared/ui/icons'

import type { Notification, NotificationType } from '@/shared/api'

export const NOTIFICATION_ICON: Record<NotificationType, Icon> = {
  course_added: BookPlusIcon,
  assignment_created: FilePlusIcon,
  assignment_updated: FilePenLineIcon,
  material_added: FolderPlusIcon,
  announcement_created: MegaphoneIcon,
  schedule_changed: CalendarSyncIcon,
  submission_reviewed: CheckCheckIcon,
  grade_changed: PencilLineIcon,
  deadline_reminder: CalendarClockIcon,
  submission_created: InboxIcon,
  exam_assigned: GraduationCapIcon,
  exam_changed: GraduationCapIcon,
}

export const notificationIcon = (type: NotificationType): Icon => NOTIFICATION_ICON[type] ?? BellIcon

/** Куда ведёт уведомление: к заданию, курсу, календарю или проверке. */
export function notificationHref(n: Notification): string {
  const t = n.target
  switch (t.section) {
    case 'assignment':
      return `/courses/${t.course_id}/assignments/${t.assignment_id}`
    case 'review':
      return `/courses/${t.course_id}/assignments/${t.assignment_id}/students/${t.student_id}`
    case 'materials':
      return `/courses/${t.course_id}#materials`
    case 'calendar':
      return t.day ? `/calendar?date=${t.day}` : '/calendar'
    case 'schedule':
      return `/courses/${t.course_id}#schedule`
    default:
      return t.course_id ? `/courses/${t.course_id}` : '/'
  }
}
