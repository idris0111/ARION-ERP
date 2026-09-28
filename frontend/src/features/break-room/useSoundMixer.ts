import { useEffect, useRef, useState } from 'react'

type Track = {stop:()=>void;gain?:GainNode;element?:HTMLAudioElement}
const frequencies:Record<string,number>={rain:1500,thunder:180,forest:650,birds:2600,ocean:340,river:820,fireplace:420,wind:280,night:1200,cafe:520,'white-noise':2000}

export function useSoundMixer(initialMaster=50){
  const context=useRef<AudioContext|null>(null)
  const buffer=useRef<AudioBuffer|null>(null)
  const tracks=useRef(new Map<string,Track>())
  const [levels,setLevels]=useState<Record<string,number>>({})
  const [master,setMaster]=useState(initialMaster)

  const stopAll=()=>{tracks.current.forEach(track=>track.stop());tracks.current.clear();setLevels({})}
  const activeCount=()=>tracks.current.size
  const toggle=async(id:string,audioUrl='')=>{
    const existing=tracks.current.get(id)
    if(existing){existing.stop();tracks.current.delete(id);setLevels(old=>{const next={...old};delete next[id];return next});return}
    const level=60
    if(audioUrl){
      const element=new Audio(audioUrl)
      element.loop=true
      element.volume=level/100*master/100
      await element.play()
      tracks.current.set(id,{element,stop:()=>{element.pause();element.src=''}})
    }else{
      const audio=context.current||new AudioContext()
      context.current=audio
      await audio.resume()
      if(!buffer.current){
        const noise=audio.createBuffer(1,audio.sampleRate*3,audio.sampleRate)
        const data=noise.getChannelData(0)
        for(let i=0;i<data.length;i++)data[i]=(Math.random()*2-1)*.5
        buffer.current=noise
      }
      const source=audio.createBufferSource();source.buffer=buffer.current;source.loop=true
      const filter=audio.createBiquadFilter();filter.type=['rain','birds','night','white-noise'].includes(id)?'highpass':'lowpass';filter.frequency.value=frequencies[id]||650
      const gain=audio.createGain();gain.gain.value=level/100*master/100*.32
      source.connect(filter).connect(gain).connect(audio.destination);source.start()
      tracks.current.set(id,{gain,stop:()=>{source.stop();source.disconnect();filter.disconnect();gain.disconnect()}})
    }
    setLevels(old=>({...old,[id]:level}))
  }
  const setLevel=(id:string,level:number)=>setLevels(old=>({...old,[id]:level}))
  useEffect(()=>{for(const [id,track] of tracks.current){const volume=(levels[id]||0)/100*master/100;if(track.gain)track.gain.gain.value=volume*.32;if(track.element)track.element.volume=volume}},[levels,master])
  useEffect(()=>()=>{tracks.current.forEach(track=>track.stop());tracks.current.clear();void context.current?.close()},[])
  return {levels,master,setMaster,toggle,setLevel,stopAll,activeCount}
}
