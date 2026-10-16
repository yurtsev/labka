// Собирает src/shared/ui/icons.tsx из набора Material Symbols (outlined, 24px).
// Запуск: node scripts/icons.mjs
import { readFileSync, writeFileSync } from 'node:fs'
import { createRequire } from 'node:module'

const require = createRequire(import.meta.url)
const set = JSON.parse(readFileSync(require.resolve('@iconify-json/material-symbols/icons.json'), 'utf8'))

// Имя компонента → имя символа. Для каждого берётся вариант -outline, если он есть.
const MAP = {
  AlertCircleIcon: 'error',
  ArchiveIcon: 'archive',
  ArchiveRestoreIcon: 'unarchive',
  ArrowLeftIcon: 'arrow-back',
  ArrowUpRightIcon: 'arrow-outward',
  AwardIcon: 'workspace-premium',
  BellIcon: 'notifications',
  BellFilledIcon: 'notifications!',
  BellOffIcon: 'notifications-off',
  BookOpenIcon: 'menu-book',
  BookPlusIcon: 'library-add',
  CalendarClockIcon: 'schedule',
  CalendarDaysIcon: 'calendar-month',
  CalendarFilledIcon: 'calendar-month!',
  CalendarPlusIcon: 'calendar-add-on',
  CalendarSyncIcon: 'event-repeat',
  CalendarTodayIcon: 'calendar-today',
  CameraIcon: 'photo-camera',
  CheckCheckIcon: 'done-all',
  CheckIcon: 'check',
  CheckBoxIcon: 'check-box!',
  CheckBoxBlankIcon: 'check-box-outline-blank',
  ChevronDownIcon: 'keyboard-arrow-down',
  ChevronLeftIcon: 'chevron-left',
  ChevronRightIcon: 'chevron-right',
  ChevronUpIcon: 'keyboard-arrow-up',
  CircleCheckIcon: 'check-circle',
  CircleIcon: 'radio-button-unchecked',
  ClockAlertIcon: 'alarm',
  CloudOffIcon: 'cloud-off',
  CompassIcon: 'explore',
  DescriptionIcon: 'description',
  FileIcon: 'draft',
  FilePenLineIcon: 'edit-document',
  FilePlusIcon: 'note-add',
  FileTextIcon: 'description',
  FlagIcon: 'flag',
  FolderOpenIcon: 'folder-open',
  FolderPlusIcon: 'create-new-folder',
  GraduationCapIcon: 'school',
  GroupIcon: 'group',
  HelpIcon: 'help',
  HomeFilledIcon: 'home!',
  HourglassIcon: 'hourglass-empty',
  HouseIcon: 'home',
  ImageIcon: 'image',
  InboxFilledIcon: 'inbox!',
  InboxIcon: 'inbox',
  InfoIcon: 'info',
  Loader2Icon: 'progress-activity',
  LocationIcon: 'location-on',
  LockIcon: 'lock',
  LogOutIcon: 'logout',
  MegaphoneIcon: 'campaign',
  MenuIcon: 'menu',
  MinusIcon: 'remove',
  MoreHorizontalIcon: 'more-horiz',
  MoreVertIcon: 'more-vert',
  NotesIcon: 'notes',
  OctagonXIcon: 'report',
  PanelLeftIcon: 'menu',
  PaperclipIcon: 'attach-file',
  PartyPopperIcon: 'celebration',
  PencilIcon: 'edit',
  PencilLineIcon: 'edit-note',
  PersonIcon: 'person',
  PlusIcon: 'add',
  RotateCcwIcon: 'undo',
  RotateCwIcon: 'refresh',
  SchoolFilledIcon: 'school!',
  ScienceIcon: 'science!',
  SearchIcon: 'search',
  StickyNoteIcon: 'sticky-note-2',
  TodayIcon: 'today',
  VisibilityIcon: 'visibility',
  AssignmentIcon: 'assignment',
  ArrowDropDownIcon: 'arrow-drop-down',
  AccountCircleIcon: 'account-circle',
  KeyboardIcon: 'keyboard',
  EventIcon: 'event',
  TaskAltIcon: 'task-alt',
  GridViewIcon: 'grid-view',
  SendIcon: 'send',
  SettingsIcon: 'settings',
  SubjectIcon: 'subject',
  Trash2Icon: 'delete',
  TriangleAlertIcon: 'warning',
  TrophyIcon: 'trophy',
  UsersIcon: 'group',
  XIcon: 'close',
}

const out = [
  '// Сгенерировано scripts/icons.mjs из Material Symbols (Apache-2.0). Не править вручную.',
  "import type { SVGProps } from 'react'",
  '',
  'export type IconProps = SVGProps<SVGSVGElement>',
  'export type Icon = (props: IconProps) => React.JSX.Element',
  '',
  'const svg = (body: string) =>',
  '  function MaterialIcon(props: IconProps) {',
  '    return <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="currentColor" aria-hidden="true" {...props} dangerouslySetInnerHTML={{ __html: body }} />',
  '  }',
  '',
]
const missing = []
for (const [comp, raw] of Object.entries(MAP)) {
  const filled = raw.endsWith('!')
  const name = raw.replace('!', '')
  const pick = filled ? (set.icons[name] ? name : null) : set.icons[`${name}-outline`] ? `${name}-outline` : set.icons[name] ? name : null
  const icon = pick && (set.icons[pick] ?? null)
  const body = icon?.body ?? (pick && set.aliases?.[pick] && set.icons[set.aliases[pick].parent]?.body)
  if (!body) {
    missing.push(raw)
    continue
  }
  out.push(`export const ${comp} = svg(${JSON.stringify(body)})`)
}
if (missing.length) {
  console.error('Не найдены:', missing.join(', '))
  process.exit(1)
}
writeFileSync(new URL('../src/shared/ui/icons.tsx', import.meta.url), out.join('\n') + '\n')
console.log(`icons.tsx: ${Object.keys(MAP).length} иконок`)
