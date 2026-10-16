// Палитра аватаров и обложек курсов, как в Google Classroom и контактах Google.
const PALETTE = ['#1a73e8', '#188038', '#c5221f', '#e37400', '#9334e6', '#007b83', '#b06000', '#d01884', '#3c4043', '#1967d2']

function hash(s: string): number {
  let h = 0
  for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) | 0
  return Math.abs(h)
}

/** Постоянный цвет для курса или человека по идентификатору. */
export const colorFor = (key: string) => PALETTE[hash(key) % PALETTE.length]
