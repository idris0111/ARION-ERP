import { useEffect, useRef, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Send, Trash2 } from 'lucide-react'
import { readableError } from '../../api/client'
import { Button } from '../../components/ui'
import { breakApi } from './api'
import { useBreakSession } from './useBreakSession'
import { useBreakSettings } from './useBreakRoom'
import type { Pet, PetMessage } from './types'

const replies=['Я устал','Расскажи шутку','Поддержи меня','Давай отдохнём','Как дела?']

function softChime(){
  const audio=new AudioContext(),tone=audio.createOscillator(),gain=audio.createGain()
  tone.type='sine';tone.frequency.value=660;gain.gain.setValueAtTime(.025,audio.currentTime);gain.gain.exponentialRampToValueAtTime(.001,audio.currentTime+.18)
  tone.connect(gain).connect(audio.destination);tone.start();tone.stop(audio.currentTime+.18);tone.onended=()=>void audio.close()
}

export function PetChat({pet,onAnimation}:{pet:Pet;onAnimation?:(animation:'listen'|'talk'|'sit')=>void}){
  const {data:settings}=useBreakSettings()
  const {data:messages,isLoading}=useQuery({queryKey:['pet-messages',pet.id],queryFn:breakApi.messages})
  const client=useQueryClient()
  const {start}=useBreakSession()
  const [text,setText]=useState('')
  const [sending,setSending]=useState(false)
  const [error,setError]=useState('')
  const bottom=useRef<HTMLDivElement>(null)
  const started=useRef(false)
  useEffect(()=>bottom.current?.scrollIntoView({behavior:settings?.reduced_motion?'instant':'smooth'}),[messages?.length])
  const send=async(value=text)=>{if(!value.trim()||sending)return;setSending(true);setError('');onAnimation?.('listen');try{if(!started.current){await start('pet');started.current=true}const answer=await breakApi.chat(value.trim());onAnimation?.(answer.animation==='calm'?'sit':'talk');client.setQueryData<PetMessage[]>(['pet-messages',pet.id],old=>[...(old||[]),{id:Date.now(),role:'user',message:value.trim(),created_at:new Date().toISOString()},{id:Date.now()+1,role:'pet',message:answer.message,created_at:new Date().toISOString()}]);client.setQueryData<Pet|null>(['my-pet'],old=>old?{...old,mood:answer.mood}:old);setText('');if(settings?.pet_sound){try{softChime()}catch{/* Audio is optional. */}}}catch(error){setError(readableError(error))}finally{setSending(false)}}
  const clear=async()=>{await breakApi.clearMessages();client.setQueryData(['pet-messages',pet.id],[])}
  return <section className="surface pet-chat"><div className="pet-chat-header"><div><strong>Разговор с {pet.name}</strong><small>Личная история · последние сообщения</small></div><button onClick={()=>void clear()} title="Очистить разговор" aria-label="Очистить разговор"><Trash2 size={16}/></button></div><div className="pet-messages" aria-live="polite">{isLoading?<p>Загружаем разговор…</p>:!messages?.length?<p className="pet-chat-empty">Поздоровайтесь или выберите короткую тему ниже.</p>:messages.map(message=><div key={message.id} className={`pet-message ${message.role}`}>{message.message}</div>)}<div ref={bottom}/></div><div className="pet-quick-replies">{replies.map(reply=><button key={reply} onClick={()=>void send(reply)}>{reply}</button>)}</div>{error&&<p className="break-error">{error}</p>}<form className="pet-chat-input" onSubmit={event=>{event.preventDefault();void send()}}><input value={text} maxLength={500} onChange={event=>setText(event.target.value)} placeholder="Напишите что-нибудь…" aria-label="Сообщение питомцу"/><Button variant="primary" disabled={sending||!text.trim()} aria-label="Отправить"><Send size={16}/></Button></form></section>
}
