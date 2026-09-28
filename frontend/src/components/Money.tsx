import { useCurrency } from '../contexts/CurrencyContext'
import { convertCurrency, formatCurrency } from '../utils/currency'
import type { Currency } from '../services/exchangeRates'

export function Money({amount,currency='TJS',maximumFractionDigits=2}:{amount:unknown;currency?:Currency;maximumFractionDigits?:number}) {
  const {currency:display,rates} = useCurrency()
  const converted = convertCurrency(amount,currency,display,rates)
  return <>{converted===null?'—':formatCurrency(converted,display,maximumFractionDigits)}</>
}
