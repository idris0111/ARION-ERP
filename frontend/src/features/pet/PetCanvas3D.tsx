import { lazy, Suspense } from 'react'
import type { Pet } from '../break-room/types'
import { speciesFor } from './config'
import type { PetAnimation } from './usePetAnimation'

export type PetCanvasProps={pet:Partial<Pet>;animation?:PetAnimation;quality?:'high'|'balanced'|'performance';reducedMotion?:boolean;orbit?:boolean;mini?:boolean;modelUrl?:string}
const PetScene3D=lazy(()=>import('./PetScene3D'))

export default function PetCanvas3D(props:PetCanvasProps){
  const spec=speciesFor(props.pet.animal_type)
  const mini=Boolean(props.mini)
  if(!props.modelUrl&&!spec.assetReady)return <div className={`pet-canvas ${mini?'pet-canvas-mini':''}`} role="img" aria-label={`3D-питомец ${props.pet.name||spec.label}`}><div className="pet-asset-empty"><span className="pet-asset-symbol" aria-hidden="true">✦</span><strong>{spec.label}</strong><small>3D-модель ещё не добавлена</small></div></div>
  return <Suspense fallback={<div className={`pet-canvas ${mini?'pet-canvas-mini':''} pet-asset-loading`}>Готовим 3D-сцену…</div>}><PetScene3D {...props}/></Suspense>
}
