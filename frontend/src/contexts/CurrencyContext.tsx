import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import { useQuery } from '@tanstack/react-query'
import { currencies, getExchangeRates, type Currency } from '../services/exchangeRates'
import { useSession } from '../app/providers'

type CurrencyState = {currency:Currency;setCurrency:(currency:Currency)=>void;rates:Partial<Record<Currency,number>>;isLoading:boolean;lastUpdated:string|null;stale:boolean;available:(currency:Currency)=>boolean}
const CurrencyContext = createContext<CurrencyState|null>(null)
const cacheKey = 'erp_exchange_rates'

function cachedRates() {
  try { return JSON.parse(localStorage.getItem(cacheKey)||'null') as Awaited<ReturnType<typeof getExchangeRates>>|null }
  catch { return null }
}

export function CurrencyProvider({children}:{children:ReactNode}) {
  const {user} = useSession()
  const [currency,setCurrency] = useState<Currency>(()=>currencies.find(item=>item===localStorage.getItem('erp_currency'))||'TJS')
  const [saved,setSaved] = useState(cachedRates)
  const query = useQuery({queryKey:['exchange-rates',user?.id],queryFn:getExchangeRates,enabled:!!user,staleTime:60*60*1000,refetchInterval:60*60*1000,retry:1})
  useEffect(()=>{localStorage.setItem('erp_currency',currency)},[currency])
  useEffect(()=>{if(query.data){setSaved(query.data);localStorage.setItem(cacheKey,JSON.stringify(query.data))}},[query.data])
  const data = query.data||saved
  const rates = data?.rates||{TJS:1}
  const stale = Boolean(data?.updated_at && (query.isError||data.stale||(!query.data&&saved)))
  const available = (code:Currency)=>code==='TJS'||Boolean(rates[code]&&rates[code]>0)
  return <CurrencyContext.Provider value={{currency,setCurrency,rates,isLoading:query.isPending&&!saved,lastUpdated:data?.updated_at||null,stale,available}}>{children}</CurrencyContext.Provider>
}

export function useCurrency(){const context=useContext(CurrencyContext);if(!context)throw new Error('CurrencyProvider missing');return context}
