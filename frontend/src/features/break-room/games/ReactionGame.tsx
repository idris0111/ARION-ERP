import { useEffect, useRef, useState } from 'react'

export default function ReactionGame({paused}:{paused:boolean}){
  const [phase,setPhase]=useState<'ready'|'waiting'|'go'|'result'>('ready')
  const [result,setResult]=useState('Нажмите «Начать», затем дождитесь сигнала.')
  const started=useRef(0)
  const timer=useRef<number|null>(null)
  const begin=()=>{if(paused)return;setPhase('waiting');setResult('Подождите…');timer.current=window.setTimeout(()=>{started.current=performance.now();setPhase('go')},2000+Math.random()*2500)}
  useEffect(()=>{if(paused&&timer.current!==null){window.clearTimeout(timer.current);timer.current=null;setPhase('ready');setResult('Пауза. Начните снова, когда будете готовы.')}},[paused])
  useEffect(()=>()=>{if(timer.current!==null)window.clearTimeout(timer.current)},[])
  const press=()=>{if(paused)return;if(phase==='ready'||phase==='result'){begin();return}if(phase==='waiting'){if(timer.current!==null)window.clearTimeout(timer.current);setResult('Рановато. Попробуйте ещё раз.');setPhase('result');return}setResult(`Время реакции: ${Math.round(performance.now()-started.current)} мс`);setPhase('result')}
  return <div className="mini-game reaction-game"><p>Спокойная проверка реакции, без счёта и соревнования.</p><button className={`reaction-target ${phase}`} onClick={press}>{phase==='go'?'Нажмите сейчас':phase==='waiting'?'Ждите сигнала':phase==='ready'?'Начать':'Ещё раз'}</button><strong className="game-result">{result}</strong></div>
}
