// Собирает src/shared/ui/file-icons.tsx: цветные иконки файлов из Material Icon Theme (MIT)
// и таблицу «расширение → иконка». Запуск: npm run icons
import { readFileSync, writeFileSync } from 'node:fs'
import { createRequire } from 'node:module'

const require = createRequire(import.meta.url)
const set = JSON.parse(readFileSync(require.resolve('@iconify-json/material-icon-theme/icons.json'), 'utf8'))

// Иконка → расширения (без точки) и особые имена файлов целиком.
const BY_ICON = {
  pdf: ['pdf'],
  word: ['doc', 'docx', 'odt', 'rtf'],
  powerpoint: ['ppt', 'pptx', 'odp', 'pps', 'ppsx'],
  table: ['xls', 'xlsx', 'xlsm', 'ods', 'csv', 'tsv'],
  python: ['py', 'pyw', 'pyi'],
  jupyter: ['ipynb'],
  javascript: ['js', 'mjs', 'cjs'],
  typescript: ['ts', 'mts', 'cts'],
  react: ['jsx'],
  'react-ts': ['tsx'],
  java: ['java', 'jar', 'class'],
  kotlin: ['kt', 'kts'],
  c: ['c', 'h'],
  cpp: ['cpp', 'cc', 'cxx', 'hpp', 'hh', 'hxx'],
  csharp: ['cs'],
  go: ['go'],
  rust: ['rs'],
  php: ['php'],
  ruby: ['rb'],
  swift: ['swift'],
  dart: ['dart'],
  scala: ['scala'],
  haskell: ['hs'],
  lua: ['lua'],
  r: ['r', 'rmd'],
  julia: ['jl'],
  perl: ['pl', 'pm'],
  matlab: ['m', 'mat'],
  assembly: ['asm', 's'],
  html: ['html', 'htm'],
  css: ['css'],
  sass: ['scss', 'sass'],
  vue: ['vue'],
  json: ['json'],
  yaml: ['yml', 'yaml'],
  xml: ['xml'],
  markdown: ['md', 'markdown'],
  tex: ['tex', 'bib'],
  console: ['sh', 'bash', 'zsh', 'bat', 'cmd'],
  powershell: ['ps1'],
  database: ['sql', 'db', 'sqlite', 'sqlite3'],
  settings: ['ini', 'cfg', 'conf', 'toml', 'env', 'properties'],
  log: ['log'],
  zip: ['zip', 'rar', '7z', 'tar', 'gz', 'tgz', 'bz2', 'xz'],
  image: ['png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp', 'ico', 'heic', 'tif', 'tiff'],
  svg: ['svg'],
  video: ['mp4', 'mov', 'avi', 'mkv', 'webm'],
  audio: ['mp3', 'wav', 'ogg', 'flac', 'm4a'],
  font: ['ttf', 'otf', 'woff', 'woff2'],
  exe: ['exe', 'msi'],
  lib: ['dll', 'so', 'lib', 'a'],
  visualstudio: ['sln', 'csproj', 'vcxproj'],
  '3d': ['stl', 'obj', 'fbx', 'blend'],
  certificate: ['pem', 'crt', 'cer'],
  docker: ['dockerfile'],
  makefile: ['makefile'],
  document: ['txt'],
}
// Для неизвестного расширения — по MIME-типу, иначе обычный документ.
const FALLBACK = ['image', 'video', 'audio', 'pdf', 'document']

const icons = new Set([...Object.keys(BY_ICON), ...FALLBACK])
const missing = [...icons].filter((name) => !set.icons[name])
if (missing.length) {
  console.error('Нет в наборе:', missing.join(', '))
  process.exit(1)
}
function icon(name) {
  const { body, left = set.left ?? 0, top = set.top ?? 0, width = set.width ?? 16, height = set.height ?? 16 } = set.icons[name]
  return { viewBox: `${left} ${top} ${width} ${height}`, body }
}
const byExt = Object.fromEntries(Object.entries(BY_ICON).flatMap(([icon, exts]) => exts.map((ext) => [ext, icon])))

const out = `// Сгенерировано scripts/file-icons.mjs из Material Icon Theme (MIT). Не править вручную.
import type { SVGProps } from 'react'

// У каждой иконки своя область рисования: без размеров — 16×16, у некоторых 24, 32, 960 или 1024.
const ICONS: Record<string, { viewBox: string; body: string }> = ${JSON.stringify(Object.fromEntries([...icons].sort().map((name) => [name, icon(name)])), null, 2)}

const BY_EXT: Record<string, string> = ${JSON.stringify(byExt, null, 2)}

/** Иконка по расширению имени файла; если оно незнакомо — по MIME-типу. */
export function fileIconName(fileName: string, contentType = ''): string {
  const lower = fileName.toLowerCase()
  const ext = lower.includes('.') ? lower.slice(lower.lastIndexOf('.') + 1) : lower
  if (BY_EXT[ext]) return BY_EXT[ext]
  if (contentType.startsWith('image/')) return 'image'
  if (contentType.startsWith('video/')) return 'video'
  if (contentType.startsWith('audio/')) return 'audio'
  if (contentType === 'application/pdf') return 'pdf'
  return 'document'
}

type Props = SVGProps<SVGSVGElement> & { fileName: string; contentType?: string }

/** Цветная иконка файла по его типу: PDF, Word, Python, архив и т. д. */
export function FileTypeIcon({ fileName, contentType, ...props }: Props) {
  const { viewBox, body } = ICONS[fileIconName(fileName, contentType)]
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox={viewBox}
      width="24"
      height="24"
      aria-hidden="true"
      {...props}
      dangerouslySetInnerHTML={{ __html: body }}
    />
  )
}
`
writeFileSync(new URL('../src/shared/ui/file-icons.tsx', import.meta.url), out)
console.log(`file-icons.tsx: ${icons.size} иконок, ${Object.keys(byExt).length} расширений`)
