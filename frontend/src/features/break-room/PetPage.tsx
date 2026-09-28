import { lazy, Suspense, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useSearchParams } from 'react-router-dom'
import { readableError } from '../../api/client'
import { Button, EmptyState, LoadingSkeleton } from '../../components/ui'
import { PetCreator3D } from '../pet/PetCreator3D'
import { PetSettingsPanel, usePetSettings } from '../pet/PetSettingsPanel'
import { usePetAnimation } from '../pet/usePetAnimation'
import { breakApi } from './api'
import { PetChat } from './PetChat'
import { useBreakSettings } from './useBreakRoom'
import type { Pet } from './types'
import '../pet/pet.css'

const PetCanvas3D=lazy(()=>import('../pet/PetCanvas3D'))
const actions=[['pet','Погладить'],['joke','Расскажи шутку'],['support','Поддержи меня'],['motivate','Мотивируй меня'],['rest','Давай отдохнём'],['play','Играть']]

export default function PetPage(){
  const [searchParams]=useSearchParams()
  const {data:breakSettings}=useBreakSettings()
  const {data:petSettings}=usePetSettings()
  const {data:pet,isLoading,error}=useQuery({queryKey:['my-pet'],queryFn:breakApi.pet,enabled:breakSettings?.policy.pet_enabled!==false&&petSettings?.pet_enabled!==false})
  const client=useQueryClient()
  const reduced=Boolean(breakSettings?.reduced_motion||petSettings?.reduced_motion||!petSettings?.animation_enabled)
  const {animation,play}=usePetAnimation(reduced)
  const [editing,setEditing]=useState(searchParams.get('edit')==='1')
  const [message,setMessage]=useState('')
  const [failure,setFailure]=useState('')
  const [tab,setTab]=useState<'room'|'chat'|'settings'>('room')
  const interact=async(kind:string)=>{
    try{const reply=await breakApi.interact(kind);setMessage(reply.message);play(kind==='pet'?'petted':reply.animation);client.setQueryData<Pet|null>(['my-pet'],old=>old?{...old,mood:reply.mood}:old);setFailure('')}
    catch(cause){setFailure(readableError(cause))}
  }
  const remove=async()=>{
    if(!window.confirm('Удалить питомца и личную историю разговора?'))return
    try{await breakApi.deletePet();client.setQueryData(['my-pet'],null);client.removeQueries({queryKey:['pet-messages']});setEditing(false)}catch(cause){setFailure(readableError(cause))}
  }
  if(breakSettings?.policy.pet_enabled===false)return <EmptyState title="Питомец недоступен для этой компании"/>
  if(petSettings?.pet_enabled===false)return <div className="break-section"><div className="break-section-title"><h2>Питомец выключен</h2><p>Вы можете включить его в личных настройках.</p></div><PetSettingsPanel/></div>
  if(isLoading)return <LoadingSkeleton/>
  if(error)return <EmptyState title="Не удалось открыть питомца" description={readableError(error)}/>
  if(!pet)return <PetCreator3D onCreated={value=>client.setQueryData(['my-pet'],value)}/>
  if(editing)return <div><Button onClick={()=>setEditing(false)}>Назад к питомцу</Button><PetCreator3D initial={pet} onSaved={value=>{client.setQueryData(['my-pet'],value);setEditing(false)}}/></div>
  return <div className="break-section pet-full-page"><div className="break-section-title"><span className="break-eyebrow">MY PET / FULL</span><h2>{pet.name}</h2><p>Ваш личный 3D компаньон. Чат виден только вам и не связан с рабочими данными.</p></div>
    <div className="pet-page-tabs"><button className={tab==='room'?'active':''} onClick={()=>setTab('room')}>Комната</button><button className={tab==='chat'?'active':''} onClick={()=>setTab('chat')}>Чат</button><button className={tab==='settings'?'active':''} onClick={()=>setTab('settings')}>Настройки</button></div>
    {tab==='room'&&<div className="pet-layout"><aside className="surface pet-profile"><span className="break-eyebrow">COMPANION</span><h3>{pet.name}</h3><dl><div><dt>Вид</dt><dd>{pet.animal_type}</dd></div><div><dt>Настроение</dt><dd>{pet.mood}</dd></div><div><dt>Уровень</dt><dd>{pet.level}</dd></div><div><dt>Опыт</dt><dd>{pet.experience}</dd></div></dl><Button onClick={()=>setEditing(true)}>Изменить внешность</Button></aside><section className={`surface pet-3d-stage room-${pet.appearance?.room||'cozy'}`}><Suspense fallback={<LoadingSkeleton/>}><PetCanvas3D pet={pet} animation={animation} quality={petSettings?.quality} reducedMotion={reduced} orbit/></Suspense><div className="pet-stage-caption"><strong>{pet.name}</strong><span>{pet.animal_type} · {pet.mood} · {animation}</span></div></section><section className="surface pet-room-actions"><h3>Проведите время вместе</h3><p>{message||'Нажмите на действие или откройте чат.'}</p><div className="pet-action-grid">{actions.map(([kind,label])=><Button key={kind} onClick={()=>void interact(kind)}>{label}</Button>)}</div><div className="pet-destinations"><Link to="/break-room/nature">Природа</Link><Link to="/break-room/sounds">Звуки</Link><Link to="/break-room/games">Игры</Link><Link to="/break-room/breathing">Дыхание</Link></div><Button onClick={()=>setTab('chat')}>Поговорить</Button>{failure&&<p className="break-error">{failure}</p>}</section></div>}
    {tab==='chat'&&<div className="pet-chat-full"><PetChat pet={pet} onAnimation={play}/><section className="surface pet-chat-aside"><Suspense fallback={<LoadingSkeleton/>}><PetCanvas3D pet={pet} animation={animation} quality={petSettings?.quality} reducedMotion={reduced}/></Suspense><strong>{pet.name} слушает вас</strong></section></div>}
    {tab==='settings'&&<><PetSettingsPanel/><div className="surface pet-danger-zone"><h3>Питомец</h3><p>Удаление также удалит его личную историю сообщений. После этого можно создать нового питомца.</p><Button onClick={()=>void remove()}>Удалить питомца</Button>{failure&&<p className="break-error">{failure}</p>}</div></>}
  </div>
}
