// Снимки экранов для docs/screenshots. Нужен запущенный `npm run dev` и установленный Google Chrome.
// Запуск: npm run screenshots [-- имя-экрана ...]
import { mkdir } from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

import { chromium } from 'playwright-core'

const BASE = process.env.APP_URL ?? 'http://localhost:5173'
const PASSWORD = process.env.DEMO_PASSWORD ?? 'labka2026'
const OUT = process.env.OUT_DIR ? path.resolve(process.env.OUT_DIR) : path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../../docs/screenshots')

const shots = (await import('./screens.mjs')).default
const only = process.argv.slice(2)

await mkdir(OUT, { recursive: true })
const browser = await chromium.launch({ channel: 'chrome' })

for (const shot of shots.filter((s) => !only.length || only.includes(s.name))) {
  const context = await browser.newContext({
    viewport: shot.viewport ?? { width: 1440, height: 900 },
    deviceScaleFactor: 2,
    locale: 'ru-RU',
    timezoneId: 'Europe/Moscow',
    reducedMotion: 'reduce',
  })
  const page = await context.newPage()
  if (shot.as) {
    await page.goto(`${BASE}/login`)
    await page.getByLabel('Email').fill(`${shot.as}@labka.ru`)
    await page.getByLabel('Пароль').fill(PASSWORD)
    await page.getByRole('button', { name: 'Войти', exact: true }).click()
    await page.waitForURL(`${BASE}/`)
  }
  if (shot.intercept) await shot.intercept(page)
  await page.goto(BASE + shot.path)
  if (shot.idle !== false) await page.waitForLoadState('networkidle')
  if (shot.prepare) await shot.prepare(page)
  await page.waitForTimeout(shot.wait ?? 900)
  const file = path.join(OUT, `${shot.name}.png`)
  await page.screenshot({ path: file, fullPage: shot.fullPage ?? false })
  console.log('✓', path.relative(process.cwd(), file))
  await context.close()
}

await browser.close()
