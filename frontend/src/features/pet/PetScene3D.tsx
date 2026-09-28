import { Component, Suspense, useCallback, useEffect, useRef, useState, type PointerEvent, type ReactNode } from 'react'
import { Canvas, useThree } from '@react-three/fiber'
import { ContactShadows, OrbitControls } from '@react-three/drei'
import { useTheme } from '../../contexts/ThemeContext'
import { PetModel } from './PetModel'
import { speciesFor } from './config'
import type { PetCanvasProps } from './PetCanvas3D'

class ModelError extends Component<{children:ReactNode;onError:()=>void},{failed:boolean}>{
  state={failed:false}
  static getDerivedStateFromError(){return {failed:true}}
  componentDidCatch(){this.props.onError()}
  render(){return this.state.failed?null:this.props.children}
}

function DemandFrames(){
  const invalidate=useThree(state=>state.invalidate)
  useEffect(()=>{const timer=window.setInterval(invalidate,66);return()=>window.clearInterval(timer)},[invalidate])
  return null
}

function Lights({dark,shadows}:{dark:boolean;shadows:boolean}){
  return <>
    <ambientLight intensity={dark?.7:1.05}/>
    <directionalLight position={[3.5,5,4]} intensity={dark?2.9:2.5} color="#fff1df" castShadow={shadows} shadow-mapSize={[1024,1024]} shadow-bias={-.0004}/>
    <directionalLight position={[-3,2,2]} intensity={dark?1.4:.95} color="#c2dafa"/>
    <directionalLight position={[1,3,-3]} intensity={dark?2:1.3} color={dark?'#b9acff':'#c6e5de'}/>
  </>
}

export default function PetScene3D({pet,animation='idle',quality='balanced',reducedMotion=false,orbit=false,mini=false,modelUrl}:PetCanvasProps){
  const {theme}=useTheme()
  const spec=speciesFor(pet.animal_type)
  const [visible,setVisible]=useState(true)
  const [systemReduced,setSystemReduced]=useState(false)
  const [mobile,setMobile]=useState(false)
  const [ready,setReady]=useState(false)
  const [failed,setFailed]=useState(false)
  const [eyeTarget,setEyeTarget]=useState<[number,number]>([0,0])
  const holder=useRef<HTMLDivElement>(null)
  const markReady=useCallback(()=>setReady(true),[])
  const markFailed=useCallback(()=>setFailed(true),[])
  useEffect(()=>{setReady(false);setFailed(false)},[spec.modelPath,modelUrl])
  useEffect(()=>{
    const observer=new IntersectionObserver(entries=>setVisible(entries[0]?.isIntersecting!==false&&document.visibilityState==='visible'))
    if(holder.current)observer.observe(holder.current)
    const onVisibility=()=>setVisible(document.visibilityState==='visible')
    document.addEventListener('visibilitychange',onVisibility)
    return()=>{observer.disconnect();document.removeEventListener('visibilitychange',onVisibility)}
  },[])
  useEffect(()=>{
    const media=window.matchMedia('(prefers-reduced-motion: reduce)')
    const update=()=>setSystemReduced(media.matches)
    update();media.addEventListener('change',update)
    return()=>media.removeEventListener('change',update)
  },[])
  useEffect(()=>{
    const media=window.matchMedia('(max-width: 640px)')
    const update=()=>setMobile(media.matches)
    update();media.addEventListener('change',update)
    return()=>media.removeEventListener('change',update)
  },[])
  const quiet=reducedMotion||systemReduced
  const renderQuality=mobile&&quality==='high'?'balanced':mobile&&quality==='balanced'?'performance':quality
  const dark=theme==='dark'||theme==='blue'||theme==='purple'
  const camera=spec.camera
  const position:[number,number,number]=mini?[camera[0],camera[1],camera[2]*.81]:camera
  const moveEye=(event:PointerEvent<HTMLDivElement>)=>{
    if(quiet)return
    const rect=event.currentTarget.getBoundingClientRect()
    setEyeTarget([((event.clientX-rect.left)/rect.width-.5)*2,((event.clientY-rect.top)/rect.height-.5)*2])
  }
  return <div ref={holder} className={`pet-canvas ${mini?'pet-canvas-mini':''} ${ready?'is-ready':''}`} role="img" aria-label={`3D-питомец ${pet.name||spec.label}`} onPointerMove={moveEye} onPointerLeave={()=>setEyeTarget([0,0])}>
    {failed?<div className="pet-asset-empty"><span className="pet-asset-symbol" aria-hidden="true">✦</span><strong>{spec.label}</strong><small>Не удалось загрузить 3D-модель</small></div>:<>
      <Canvas frameloop={visible?(renderQuality==='performance'?'demand':'always'):'never'} dpr={renderQuality==='high'?[1,2]:renderQuality==='performance'?1:[1,1.5]} camera={{position,fov:mini?34:36}} shadows={renderQuality==='high'&&!mini} gl={{antialias:renderQuality!=='performance',powerPreference:'low-power',alpha:true}}>
        {renderQuality==='performance'&&visible&&<DemandFrames/>}
        <Lights dark={dark} shadows={renderQuality==='high'&&!mini}/>
        <ModelError key={modelUrl||spec.modelPath} onError={markFailed}><Suspense fallback={null}>
          <PetModel pet={pet} spec={modelUrl?{...spec,modelPath:modelUrl}:spec} animation={quiet?'idle':animation} reducedMotion={quiet} eyeTarget={eyeTarget} onReady={markReady}/>
        </Suspense></ModelError>
        {!mini&&renderQuality!=='performance'&&<ContactShadows position={[0,-.02,0]} opacity={dark?.35:.25} scale={3.5} blur={2.4} far={2.5} resolution={renderQuality==='high'?512:256}/>}
        {orbit&&<OrbitControls enablePan={false} enableZoom minDistance={2.5} maxDistance={6} minPolarAngle={Math.PI/2.9} maxPolarAngle={Math.PI/1.7} target={spec.target}/>}
      </Canvas>
      {!mini&&pet.animal_type==='bear'&&<a className="pet-model-credit" href="https://poly.pizza/m/3Eb9oLfZYIc" target="_blank" rel="noopener noreferrer">3D-модель медведя: jiang liu · CC BY 3.0</a>}
      {!ready&&<div className="pet-asset-loading">Загружаем 3D-модель…</div>}
    </>}
  </div>
}
