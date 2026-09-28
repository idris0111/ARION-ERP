import { useState } from 'react'
import { Button } from '../../components/ui'
import { BreakTimer } from './BreakTimer'
import { useBreakSession } from './useBreakSession'
import { useBreakSettings } from './useBreakRoom'

export default function BreathingPage(){
  const {data:settings}=useBreakSettings()
  const {start,end}=useBreakSession()
  const [active,setActive]=useState(false)
  const [done,setDone]=useState(false)
  const [minutes,setMinutes]=useState(2)
  const [key,setKey]=useState(0)
  const begin=async()=>{await start('breathing');setDone(false);setActive(true);setKey(value=>value+1)}
  return <div className="break-section"><div className="break-section-title"><span className="break-eyebrow">SHORT BREAK</span><h2>Несколько спокойных вдохов</h2><p>Дышите в удобном для себя темпе. Здесь нет цели или оценки.</p></div><div className="surface breathing-panel"><div className={`breathing-orb ${active&&!settings?.reduced_motion?'moving':''}`}><span>{active?'Вдох · выдох':'Пауза'}</span></div><div className="breathing-copy"><h3>{done?'Перерыв завершён':'Побудьте здесь немного'}</h3><p>Медленный вдох, мягкий выдох. Если ритм не подходит, дышите как комфортно.</p><div className="duration-options">{[2,5,10,15].map(value=><button key={value} className={minutes===value?'active':''} onClick={()=>setMinutes(value)}>{value} мин</button>)}</div>{active?<><BreakTimer key={key} minutes={minutes} onComplete={()=>{void end();setActive(false);setDone(true)}}/><Button onClick={()=>{void end();setActive(false)}}>Завершить</Button></>:<Button variant="primary" onClick={()=>void begin()}>{done?'Ещё один перерыв':'Начать'}</Button>}</div></div></div>
}
