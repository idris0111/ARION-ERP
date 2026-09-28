import { lazy, Suspense, useEffect, useState } from 'react'
import { Brain, CircleDot, Pause, Play, RotateCcw, X } from 'lucide-react'
import { readableError } from '../../api/client'
import { Button, EmptyState, LoadingSkeleton } from '../../components/ui'
import { useBreakSession } from './useBreakSession'
import { useBreakSettings } from './useBreakRoom'

const games={memory:lazy(()=>import('./games/MemoryGame')),reaction:lazy(()=>import('./games/ReactionGame')),tic:lazy(()=>import('./games/TicTacToe'))}
const choices=[{id:'memory',title:'Карточки памяти',description:'Найдите шесть спокойных пар',icon:Brain},{id:'reaction',title:'Реакция',description:'Дождитесь сигнала',icon:CircleDot},{id:'tic',title:'Крестики-нолики',description:'Короткая игра против компьютера',icon:CircleDot}] as const
type GameId=keyof typeof games

export default function GamesPage(){
  const {data:settings}=useBreakSettings()
  const {start,end}=useBreakSession()
  const [selected,setSelected]=useState<GameId|null>(null)
  const [paused,setPaused]=useState(false)
  const [seed,setSeed]=useState(0)
  const [seconds,setSeconds]=useState(0)
  const [failure,setFailure]=useState('')
  useEffect(()=>{if(!selected||paused)return;const id=window.setInterval(()=>setSeconds(value=>value+1),1000);return()=>window.clearInterval(id)},[selected,paused])
  const open=async(id:GameId)=>{try{await start('game');setSelected(id);setPaused(false);setSeconds(0);setFailure('')}catch(error){setFailure(readableError(error))}}
  const exit=async()=>{await end();setSelected(null);setPaused(false)}
  if(settings?.policy.games_enabled===false)return <EmptyState title="Мини-игры отключены для этой компании" description="Другие доступные разделы Break Room продолжат работать."/>
  if(selected){const Game=games[selected];return <div className="break-section"><div className="game-toolbar"><div><span className="break-eyebrow">MINI GAME · {Math.floor(seconds/60)}:{String(seconds%60).padStart(2,'0')}</span><h2>{choices.find(item=>item.id===selected)?.title}</h2></div><div><Button onClick={()=>setPaused(value=>!value)}>{paused?<Play size={16}/>:<Pause size={16}/>} {paused?'Продолжить':'Пауза'}</Button><Button onClick={()=>{setSeed(value=>value+1);setSeconds(0);setPaused(false)}}><RotateCcw size={16}/> Заново</Button><Button onClick={()=>void exit()}><X size={16}/> Выход</Button></div></div>{seconds>=300&&<p className="break-note">Прошло пять минут. Можно спокойно вернуться к работе в любой момент.</p>}<div className="surface game-stage"><Suspense fallback={<LoadingSkeleton/>}><Game key={seed} paused={paused}/></Suspense>{paused&&<div className="game-paused">Пауза</div>}</div></div>}
  return <div className="break-section"><div className="break-section-title"><span className="break-eyebrow">MINI GAMES</span><h2>Небольшая пауза для внимания</h2><p>Три короткие игры без рейтингов и соревнований. Начните и закончите в удобный момент.</p></div>{failure&&<p className="break-error">{failure}</p>}<div className="break-action-grid">{choices.map(item=><button key={item.id} className="surface break-action-card" onClick={()=>void open(item.id)}><item.icon size={24}/><strong>{item.title}</strong><small>{item.description}</small><span>Играть →</span></button>)}</div></div>
}
