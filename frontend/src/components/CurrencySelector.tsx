import { currencies } from '../services/exchangeRates'
import { useCurrency } from '../contexts/CurrencyContext'

export function CurrencySelector(){
  const {currency,setCurrency,isLoading,lastUpdated,stale,available} = useCurrency()
  return <div className="currency-control"><span>Валюта:</span><div className="currency-options" role="group" aria-label="Валюта отображения">{currencies.map(code=><button key={code} type="button" className={currency===code?'active':''} aria-pressed={currency===code} disabled={!available(code)} onClick={()=>setCurrency(code)}>{code}</button>)}</div><small>{isLoading?'Курсы загружаются…':lastUpdated?`Курсы: ${new Date(lastUpdated).toLocaleString('ru-RU')}`:'Курсы недоступны'}{stale?' · данные могут быть устаревшими':''}</small></div>
}
