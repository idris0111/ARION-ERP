import { useState } from 'react'
import { createRoot } from 'react-dom/client'
import { Canvas } from '@react-three/fiber'
import { OrbitControls } from '@react-three/drei'
import { PetModel } from './features/pet/PetModel'
import { species, speciesIds, type SpeciesId } from './features/pet/config'
import type { PetAnimation } from './features/pet/usePetAnimation'

function Preview(){
  const [id,setId]=useState<SpeciesId>('cat')
  const [animation,setAnimation]=useState<PetAnimation>('idle')
  const spec=species[id]
  return <><div>{speciesIds.map(value=><button className={id===value?'active':''} key={value} onClick={()=>{setId(value);setAnimation('idle')}}>{value}</button>)}{(['idle','wave','happy','jump','sit'] as PetAnimation[]).map(value=><button className={animation===value?'active':''} key={value} onClick={()=>setAnimation(value)}>{value}</button>)}</div><div className="stage"><Canvas key={id} camera={{position:spec.camera,fov:36}}><ambientLight intensity={1.05}/><directionalLight position={[3.5,5,4]} intensity={2.5}/><directionalLight position={[-3,2,2]} intensity={.95}/><PetModel pet={{animal_type:id}} spec={spec} animation={animation} reducedMotion={false} eyeTarget={[0,0]} onReady={()=>{}}/><OrbitControls target={spec.target}/></Canvas></div></>
}
createRoot(document.getElementById('root')!).render(<Preview/>)
