export const money = (value) => {
  if (value === null || value === undefined) return '-'
  const numericValue = Number(value)
  if (Number.isNaN(numericValue)) return '-'
  if (numericValue <= 0) return '무료'
  return `₩${numericValue.toLocaleString('ko-KR')}`
}

export const percent = (value) => `${Number(value || 0)}%`
