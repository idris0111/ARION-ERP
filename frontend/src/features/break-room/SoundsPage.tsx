import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Bird, CloudLightning, CloudRain, Coffee, Flame, Moon, Radio, Trees, Volume2, Waves, Wind, type LucideIcon } from 'lucide-react'
import { readableError } from '../../api/client'
import { Button, EmptyState, LoadingSkeleton } from '../../components/ui'
import { breakApi } from './api'
import { useBreakSession } from './useBreakSession'
import { useBreakSettings } from './useBreakRoom'
import { useSoundMixer } from './useSoundMixer'

const icons:Record<string,LucideIcon>={CloudRain,CloudLightning,Trees,Bird,Waves,Flame,Wind,Moon,Coffee,Radio}

export default function SoundsPage(){
  const {data:settings}=useBreakSettings()
  const {data:sounds,isLoading,error}=useQuery({queryKey:['break-sounds'],queryFn:breakApi.sounds})
  const {data:presets}=useQuery({queryKey:['break-presets'],queryFn:breakApi.presets})
  const client=useQueryClient()
  const mixer=useSoundMixer(settings?.volume||50)
  const {start,end}=useBreakSession()
  const [name,setName]=useState('')
  const [failure,setFailure]=useState('')
  const toggle=async(id:string,url:string)=>{
    const starting=mixer.activeCount()===0
    try{
      if(starting)await start('sound')
      await mixer.toggle(id,url)
      if(mixer.activeCount()===0)await end()
      setFailure('')
    }catch(error){
      if(starting)await end().catch(()=>undefined)
      setFailure(readableError(error))
    }
  }
  const save=async()=>{if(!name.trim())return;try{await breakApi.createPreset({name:name.trim(),sounds:mixer.levels,master_volume:mixer.master});setName('');client.invalidateQueries({queryKey:['break-presets']});setFailure('')}catch(error){setFailure(readableError(error))}}
  const apply=async(levels:Record<string,number>,master:number)=>{
    try{
      mixer.stopAll()
      await end()
      mixer.setMaster(master)
      if(Object.keys(levels).length)await start('sound')
      for(const [id,level] of Object.entries(levels)){
        const item=sounds?.find(sound=>sound.id===id)
        if(item){await mixer.toggle(id,item.audio_url);mixer.setLevel(id,level)}
      }
      if(mixer.activeCount()===0)await end()
      setFailure('')
    }catch(error){
      mixer.stopAll()
      await end().catch(()=>undefined)
      setFailure(readableError(error))
    }
  }
  if(isLoading)return <LoadingSkeleton/>
  if(error)return <EmptyState title="Звуки недоступны" description={readableError(error)}/>
  return <div className="break-section"><div className="break-section-title"><span className="break-eyebrow">SOUND MIXER</span><h2>Соберите своё спокойное пространство</h2><p>Добавьте несколько звуков и настройте каждый отдельно. Воспроизведение начнётся только после нажатия.</p></div>{failure&&<p className="break-error">{failure}</p>}<div className="surface surface-padding sound-master"><Volume2 size={19}/><strong>Общая громкость</strong><input type="range" min="0" max="100" value={mixer.master} onChange={e=>mixer.setMaster(Number(e.target.value))}/><span>{mixer.master}%</span><Button onClick={()=>{mixer.stopAll();void end()}}>Выключить всё</Button></div><div className="sound-grid">{sounds?.map(item=>{const Icon=icons[item.icon]||Volume2;const active=mixer.levels[item.id]!==undefined;return <div key={item.id} className={`surface sound-card ${active?'active':''}`}><span className="sound-icon"><Icon size={21}/></span><div><strong>{item.name}</strong><small>{active?'Воспроизводится':'Выключен'}</small></div><button className="sound-toggle" role="switch" aria-checked={active} aria-label={`${item.name}: ${active?'выключить':'включить'}`} onClick={()=>void toggle(item.id,item.audio_url)}><span/></button><input aria-label={`Громкость ${item.name}`} type="range" min="0" max="100" value={mixer.levels[item.id]??60} disabled={!active} onChange={e=>mixer.setLevel(item.id,Number(e.target.value))}/><span className="sound-level">{mixer.levels[item.id]??60}%</span></div>})}</div><div className="surface surface-padding preset-panel"><div><h3>Мои наборы</h3><p>Сохраните текущее сочетание для следующего перерыва.</p></div><div className="preset-create"><input value={name} maxLength={60} placeholder="Название набора" onChange={e=>setName(e.target.value)}/><Button variant="primary" disabled={!name.trim()||!Object.keys(mixer.levels).length} onClick={()=>void save()}>Сохранить</Button></div><div className="preset-list">{presets?.map(preset=><div key={preset.id}><span>{preset.name}</span><Button size="sm" onClick={()=>void apply(preset.sounds,preset.master_volume)}>Включить</Button><button onClick={()=>void breakApi.deletePreset(preset.id).then(()=>client.invalidateQueries({queryKey:['break-presets']}))} aria-label={`Удалить ${preset.name}`}>×</button></div>)}</div></div></div>
}
