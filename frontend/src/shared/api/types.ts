import type { components } from './schema'

type S = components['schemas']

export type UserRole = S['UserRole']
export type User = S['UserResponse']
export type Profile = S['ProfileResponse']
export type Teacher = S['TeacherResponse']
export type Person = S['PersonResponse']
export type Ref = S['CourseRefResponse']

export type Home = S['HomeResponse']
export type HomeDeadline = S['HomeDeadlineResponse']
export type HomeLesson = S['HomeLessonResponse']
export type HomeCourse = S['HomeCourseResponse']

export type Semester = S['SemesterResponse']
export type Scale = S['ScaleResponse']
export type CoursePreview = S['CoursePreviewResponse']
export type Course = S['CourseResponse']
export type Group = S['GroupResponse']

export type Material = S['MaterialResponse']
export type FileInfo = S['MaterialFileResponse']

export type FeedEntry = S['FeedEntryResponse']
export type FeedAssignment = S['FeedAssignmentResponse']
export type FeedAnnouncement = S['FeedAnnouncementResponse']
export type Announcement = S['AnnouncementResponse']

export type AssignmentType = S['AssignmentType']
export type DeadlineType = S['DeadlineType']
export type ProgressStatus = S['ProgressStatus']
export type Progress = S['ProgressResponse']
export type Grade = S['GradeResponse']
export type Summary = S['SummaryResponse']
export type Assignment = S['AssignmentResponse']
export type AssignmentCreate = S['AssignmentCreateRequest']

export type Attempt = S['src__api__submissions__schemas__AttemptResponse']
export type ReviewAttempt = S['src__api__reviews__schemas__AttemptResponse']
export type ReviewVerdict = S['ReviewVerdict']
export type StudentAttempts = S['StudentAttemptsResponse']
export type StudentRow = S['StudentRowResponse']
export type QueueItem = S['QueueItemResponse']

export type LessonType = S['LessonType']
export type ScheduleRepeat = S['ScheduleRepeat']
export type Slot = S['SlotResponse']
export type CourseSchedule = S['CourseScheduleResponse']
export type Rule = S['RuleResponse']
export type RuleRequest = S['RuleRequest']

export type CalendarView = S['CalendarView']
export type Calendar = S['CalendarResponse']
export type CalendarItem = S['CalendarItemResponse']
export type CalendarWeek = S['WeekResponse']
export type ExamType = S['ExamType']
export type PersonalTask = S['TaskResponse']
export type PersonalTaskRequest = S['TaskRequest']

export type Notification = S['NotificationResponse']
export type NotificationType = S['NotificationType']

export type Page<T> = { items: T[]; page: number; per_page: number; total: number; pages: number }
