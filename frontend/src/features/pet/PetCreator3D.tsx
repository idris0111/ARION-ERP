import { lazy, Suspense, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { ArrowLeft, ArrowRight } from 'lucide-react'
import { readableError } from '../../api/client'
import { Button } from '../../components/ui'
import { breakApi } from '../break-room/api'
import type { Pet, PetAppearance } from '../break-room/types'
import { appearanceOptions, defaults, eyePalette, palette, species, speciesIds, type SpeciesId } from './config'
import type { PetAnimation } from './usePetAnimation'

const PetCanvas3D=lazy(()=>import('./PetCanvas3D'))
const steps=['Вид','Тело','Мордочка','Окрас','Одежда','Аксессуары','Характер','Имя','Просмотр']
const personalities=['friendly','funny','calm','energetic','motivating','smart','playful']
const styles=['short','normal','talkative']
const labels:Record<string,string>={classic:'Классический',compact:'Компактный',tall:'Высокий',pointed:'Острые',floppy:'Висячие',round:'Круглые',long:'Длинные',short:'Короткие',fluffy:'Пушистый',soft:'Мягкие',sand:'Песочный',cloud:'Облачный',cocoa:'Какао',peach:'Персиковый',sage:'Шалфей',slate:'Серо-синий',cream:'Кремовый',charcoal:'Графит',warm:'Тёплый',blue:'Голубой',green:'Зелёный',amber:'Янтарный',mask:'Маска',blaze:'Полоса',freckles:'Веснушки',spots:'Пятна',stripe:'Полоса',hoodie:'Худи',sweater:'Свитер',shirt:'Футболка',jacket:'Куртка',scarf:'Шарф',collar:'Ошейник',bow:'Бант',glasses:'Очки',hat:'Шляпа',bell:'Колокольчик',necklace:'Подвеска',headphones:'Наушники',cozy:'Уютная комната',forest:'Лес',mountains:'Горы',beach:'Пляж',night:'Ночная комната',minimal:'Минимализм',friendly:'Дружелюбный',funny:'Весёлый',calm:'Спокойный',energetic:'Энергичный',motivating:'Вдохновляющий',smart:'Умный',playful:'Игривый',normal:'Обычный',talkative:'Общительный'}
const label=(value:string)=>value?labels[value]||value:'Без оформления'
const previews:PetAnimation[]=['idle','happy','wave','sit']

export function PetCreator3D({onCreated,initial,onSaved}:{onCreated?:(pet:Pet)=>void;initial?:Pet;onSaved?:(pet:Pet)=>void}){
  const [step,setStep]=useState(0)
  const [speciesId,setSpeciesId]=useState<SpeciesId>((initial?.animal_type as SpeciesId)||'cat')
  const [appearance,setAppearance]=useState<PetAppearance>({...defaults,...initial?.appearance})
  const [name,setName]=useState(initial?.name||'')
  const [personality,setPersonality]=useState(initial?.personality||'friendly')
  const [style,setStyle]=useState(initial?.communication_style||'normal')
  const [previewAnimation,setPreviewAnimation]=useState<PetAnimation>('idle')
  const [hoverSpecies,setHoverSpecies]=useState<SpeciesId|null>(null)
  const [error,setError]=useState('')
  const [saving,setSaving]=useState(false)
  const {data:serverOptions}=useQuery({queryKey:['pet-options'],queryFn:breakApi.petOptions})
  const {data:serverAppearance}=useQuery({queryKey:['pet-appearance-options'],queryFn:breakApi.appearanceOptions})
  const earOptions=serverOptions?.species[speciesId]?.ears||species[speciesId].ears
  const tailOptions=serverOptions?.species[speciesId]?.tails||species[speciesId].tails
  const setField=(field:keyof PetAppearance,value:string)=>setAppearance(old=>({...old,[field]:value}))
  const field=(key:keyof PetAppearance,title:string,values:readonly string[])=><label key={key} className="creator-field">{title}<select value={appearance[key]} onChange={e=>setField(key,e.target.value)}>{values.map(value=><option key={value} value={value}>{label(value)}</option>)}</select></label>
  const swatches=(key:'primary_color'|'secondary_color'|'eye_color',values:readonly string[])=><fieldset className="creator-swatches"><legend>{key==='primary_color'?'Основной цвет':key==='secondary_color'?'Дополнительный цвет':'Цвет глаз'}</legend>{values.map(value=><button key={value} type="button" title={label(value)} aria-label={label(value)} aria-pressed={appearance[key]===value} className={appearance[key]===value?'selected':''} style={{'--swatch':(key==='eye_color'?eyePalette:palette)[value]} as React.CSSProperties} onClick={()=>setField(key,value)}><span/></button>)}</fieldset>
  const preview={...initial,name:name||'Ваш питомец',animal_type:speciesId,appearance,mood:'happy'} as Pet
  const save=async()=>{
    setSaving(true);setError('')
    try{
      const payload={name:name.trim(),animal_type:speciesId,personality,communication_style:style,appearance,color:appearance.primary_color,eyes:appearance.eye_color,ears:appearance.ears,clothes:appearance.clothes,accessory:appearance.accessory,background:appearance.room}
      const pet=initial?await breakApi.updatePet(payload):await breakApi.createPet(payload)
      onSaved?.(pet);onCreated?.(pet)
    }catch(cause){setError(readableError(cause))}finally{setSaving(false)}
  }
  return <div className="pet-creator"><div className="break-section-title"><span className="break-eyebrow">MY PET / CREATOR</span><h2>{initial?'Изменить питомца':'Создайте своего компаньона'}</h2><p>Выберите внешность и характер. Всё можно изменить позже.</p></div>
    <nav className="creator-progress" aria-label="Этапы создания">{steps.map((title,index)=><button key={title} type="button" className={index===step?'active':''} aria-current={index===step?'step':undefined} onClick={()=>setStep(index)}><span>{String(index+1).padStart(2,'0')}</span>{title}</button>)}</nav>
    <div className="creator-layout"><div className="surface creator-preview"><div className="creator-preview-heading"><span>Живой просмотр</span><strong>{species[speciesId].label} · {name||'без имени'}</strong></div><Suspense fallback={<div className="pet-canvas pet-asset-loading">Загружаем просмотр…</div>}><PetCanvas3D pet={preview} animation={previewAnimation} orbit/></Suspense><div className="creator-preview-controls">{previews.map(value=><button key={value} type="button" className={previewAnimation===value?'selected':''} onClick={()=>setPreviewAnimation(value)}>{({idle:'Спокойно',happy:'Радость',wave:'Привет',sit:'Сидит'} as Record<PetAnimation,string>)[value]}</button>)}</div><p>{species[speciesId].assetReady?'Поверните или приблизьте модель мышью либо пальцем.':'Для этого вида ещё требуется готовая GLB-модель. Настройки питомца можно сохранить.'}</p></div>
      <div className="surface creator-fields"><div className="creator-step-head"><span>Шаг {step+1} из {steps.length}</span><h3>{steps[step]}</h3></div>
        {step>=1&&step<=3&&<p className="creator-hint">В бесплатных 3D-моделях нет вариантов формы, окраса и отметин. Выбор сохранится в настройках, но пока не изменит саму модель.</p>}
        {step===0&&<div className="creator-species-grid">{speciesIds.map(id=><button key={id} type="button" className={speciesId===id?'selected':''} onMouseEnter={()=>setHoverSpecies(id)} onMouseLeave={()=>setHoverSpecies(null)} onFocus={()=>setHoverSpecies(id)} onBlur={()=>setHoverSpecies(null)} onClick={()=>{setSpeciesId(id);setAppearance(old=>({...old,ears:'classic',tail:'classic'}))}}><span className="creator-species-art" aria-hidden="true">{species[id].assetReady&&(hoverSpecies===id||speciesId===id)?<Suspense fallback={null}><PetCanvas3D pet={{animal_type:id,appearance}} animation={hoverSpecies===id?'blink':'idle'} mini quality="performance"/></Suspense>:'✦'}</span><strong>{species[id].label}</strong><small>{species[id].assetReady?'3D-модель готова':'3D-модель ожидается'}</small></button>)}</div>}
        {step===1&&<div className="creator-field-stack">{field('body_style','Телосложение',serverAppearance?.body_style||appearanceOptions.body_style)}{field('ears','Форма ушей',['classic',...earOptions.filter(value=>value!=='classic')])}{field('tail','Хвост',['classic',...tailOptions.filter(value=>value!=='classic')])}</div>}
        {step===2&&<div className="creator-field-stack">{field('eye_color','Глаза',serverAppearance?.eye_color||appearanceOptions.eye_color)}{swatches('eye_color',appearanceOptions.eye_color)}{field('face_markings','Отметины на мордочке',serverAppearance?.face_markings||appearanceOptions.face_markings)}</div>}
        {step===3&&<div className="creator-field-stack">{swatches('primary_color',appearanceOptions.primary_color)}{swatches('secondary_color',appearanceOptions.secondary_color)}{field('body_markings','Рисунок шерсти',serverAppearance?.body_markings||appearanceOptions.body_markings)}</div>}
        {step===4&&<div className="creator-field-stack">{field('clothes','Одежда',serverAppearance?.clothes||appearanceOptions.clothes)}<p className="creator-hint">Предмет появится на 3D-модели после добавления подходящего GLB-ассета.</p></div>}
        {step===5&&<div className="creator-field-stack">{field('accessory','Аксессуар',serverAppearance?.accessory||appearanceOptions.accessory)}<p className="creator-hint">3D-аксессуары появятся после добавления соответствующих файлов.</p>{field('room','Атмосфера комнаты',serverAppearance?.room||appearanceOptions.room)}</div>}
        {step===6&&<div className="creator-field-stack"><h4>Характер</h4><div className="choice-grid">{(serverOptions?.personalities||personalities).map(value=><button key={value} type="button" className={personality===value?'selected':''} onClick={()=>setPersonality(value)}>{label(value)}</button>)}</div><h4>Стиль общения</h4><div className="choice-grid">{(serverOptions?.styles||styles).map(value=><button key={value} type="button" className={style===value?'selected':''} onClick={()=>setStyle(value)}>{label(value)}</button>)}</div></div>}
        {step===7&&<label className="creator-field">Как зовут питомца?<input maxLength={40} value={name} onChange={e=>setName(e.target.value)} placeholder="Имя питомца" autoFocus/></label>}
        {step===8&&<div className="creator-summary"><p><strong>{name||'Питомец'}</strong> · {species[speciesId].label}</p><p>{label(personality)} · {label(style)}</p><p>После сохранения вы сможете общаться и играть с питомцем.</p></div>}
        {error&&<p className="break-error">{error}</p>}
        <div className="creator-actions"><Button disabled={step===0} onClick={()=>setStep(value=>value-1)}><ArrowLeft size={15}/> Назад</Button>{step<steps.length-1?<Button variant="primary" disabled={step===7&&!name.trim()} onClick={()=>setStep(value=>value+1)}>Дальше <ArrowRight size={15}/></Button>:<Button variant="primary" disabled={saving||!name.trim()} onClick={()=>void save()}>{saving?'Сохраняем…':initial?'Сохранить':'Создать питомца'}</Button>}</div>
      </div></div></div>
}
