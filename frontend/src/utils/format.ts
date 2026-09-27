export function formatMoney(value: unknown, maximumFractionDigits = 2): string {
  const currency = localStorage.getItem('nexora_currency') || 'TJS'
  try {
    return new Intl.NumberFormat('ru-RU', { style: 'currency', currency, maximumFractionDigits }).format(Number(value || 0))
  } catch {
    return `${new Intl.NumberFormat('ru-RU', { maximumFractionDigits }).format(Number(value || 0))} ${currency}`
  }
}
