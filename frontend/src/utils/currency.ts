import type { Currency } from '../services/exchangeRates'

export function convertCurrency(amount:unknown, fromCurrency:Currency, toCurrency:Currency, rates:Partial<Record<Currency,number>>):number|null {
  if (amount === null || amount === undefined || amount === '') return null
  const value = Number(amount)
  const from = rates[fromCurrency]
  const to = rates[toCurrency]
  if (!Number.isFinite(value) || !from || !to || from <= 0 || to <= 0) return null
  return value / from * to
}

export function formatCurrency(amount:number, currency:Currency, maximumFractionDigits=2):string {
  return new Intl.NumberFormat('ru-RU', {style:'currency',currency,maximumFractionDigits}).format(amount)
}
