import { http } from '../api/client'

export type Currency = 'TJS'|'USD'|'EUR'|'CNY'
export const currencies:Currency[] = ['TJS','USD','EUR','CNY']
export type ExchangeRates = {base:'TJS';updated_at:string|null;rates:Partial<Record<Currency,number>>;stale:boolean}

export async function getExchangeRates():Promise<ExchangeRates> {
  const {data} = await http.get<ExchangeRates>('exchange-rates/')
  return {...data,rates:Object.fromEntries(Object.entries(data.rates).map(([code,rate])=>[code,Number(rate)]))}
}
