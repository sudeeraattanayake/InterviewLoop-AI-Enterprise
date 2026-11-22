import React,{useEffect,useRef,useState} from 'react'
import {AudioLines,Mic,MicOff,ShieldCheck,Sparkles,Volume2,Wifi} from 'lucide-react'
import {post} from '../api'
/** OpenAI Realtime WebRTC; short-lived session credentials minted only on API. */
export default function VoicePanel({applicationId,aiConsent,onUseTranscript}){
 const pcRef=useRef(null),streamRef=useRef(null),soundRef=useRef(null),channelRef=useRef(null)
 const [state,setState]=useState('offline'),[error,setError]=useState(''),[lines,setLines]=useState([]),[muted,setMuted]=useState(false)
 const cleanup=()=>{try{channelRef.current?.close()}catch{}try{pcRef.current?.close()}catch{}streamRef.current?.getTracks().forEach(t=>t.stop());if(soundRef.current){soundRef.current.srcObject=null}pcRef.current=null;streamRef.current=null;channelRef.current=null;setState('offline')}
 useEffect(()=>()=>cleanup(),[])
 const connect=async()=>{
  setError('');setState('connecting')
  let pc,stream
  try{
   const token=await post(`/applications/${applicationId}/voice/token`)
   if(!token.value)throw Error('No ephemeral credential returned by the server')
   pc=new RTCPeerConnection();pcRef.current=pc
   pc.ontrack=e=>{if(soundRef.current)soundRef.current.srcObject=e.streams[0]}
   stream=await navigator.mediaDevices.getUserMedia({audio:{echoCancellation:true,noiseSuppression:true}})
   streamRef.current=stream
   stream.getAudioTracks().forEach(track=>pc.addTrack(track,stream))
   const channel=pc.createDataChannel('oai-events');channelRef.current=channel
   channel.onmessage=event=>{
    let payload;try{payload=JSON.parse(event.data)}catch{return}
    if(payload.type==='conversation.item.input_audio_transcription.completed'&&payload.transcript){setLines(rows=>[...rows,{speaker:'You',text:payload.transcript}].slice(-24))}
    if((payload.type==='response.output_audio_transcript.done'||payload.type==='response.output_text.done')&&payload.transcript||payload.type==='response.output_text.done'&&payload.text){const message=payload.transcript||payload.text;setLines(rows=>[...rows,{speaker:'AI',text:message}].slice(-24))}
    if(payload.type==='error')setError(payload.error?.message||'The realtime provider returned an error')
   }
   channel.onopen=()=>{
    setState('live')
    channel.send(JSON.stringify({type:'response.create',response:{instructions:'Greet the candidate briefly and begin with the first structured job-related interview question.'}}))
   }
   pc.onconnectionstatechange=()=>{if(['failed','disconnected','closed'].includes(pc.connectionState)){setState('offline')}}
   const offer=await pc.createOffer();await pc.setLocalDescription(offer)
   const response=await fetch('https://api.openai.com/v1/realtime/calls',{method:'POST',body:offer.sdp,
       headers:{Authorization:`Bearer ${token.value}`,'Content-Type':'application/sdp'}})
   if(!response.ok)throw Error(`OpenAI Realtime connection error (${response.status})`)
   await pc.setRemoteDescription({type:'answer',sdp:await response.text()})
  }catch(e){setError(e.message||'Voice connection failed');cleanup()}
 }
 const toggleMute=()=>{streamRef.current?.getAudioTracks().forEach(t=>t.enabled=muted);setMuted(x=>!x)}
 const latestCandidate=[...lines].reverse().find(x=>x.speaker==='You')?.text||''
 return <section className="card glass voice-card"><div className="voice-card-header"><div className="voice-icon"><AudioLines size={25}/></div><div><span className="eyebrow">LIVE AI VOICE / WEBRTC</span><h3>Conversational interviewer</h3><p>Natural spoken questions, optional follow-ups and candidate-visible transcription</p></div><span className={`voice-state ${state}`}>{state}</span></div>
 <div className={`voice-wave ${state==='live'?'playing':''}`} aria-hidden="true">{Array.from({length:38},(_,i)=><i key={i} style={{animationDelay:`${i*-37}ms`,height:`${12+(i*17)%44}px`}}/>)}</div>
 {!aiConsent?<p className="notice info">External AI consent was not provided at application time; the standard recorded interview is still available.</p>:<><div className="inline-actions">{state==='offline'?<button className="btn primary" onClick={connect}><Mic size={17}/> Start live AI interviewer</button>:<><button className="btn outline" onClick={toggleMute}>{muted?<MicOff size={17}/>:<Mic size={17}/>} {muted?'Unmute':'Mute'} mic</button><button className="btn outline" onClick={cleanup}>End voice session</button></>}{latestCandidate&&<button className="btn outline" onClick={()=>onUseTranscript(latestCandidate)}>Use last spoken answer as transcript</button>}</div><p className="subtle">Speech goes to OpenAI while connected. Only text you explicitly save into a video answer is submitted to the recruiter. Ending the voice session stops microphone transmission.</p></>}
 {error&&<div className="notice info">{error}</div>}
 {lines.length>0&&<div className="voice-transcript">{lines.slice(-6).map((x,i)=><div key={i}><b>{x.speaker}</b><p>{x.text}</p></div>)}</div>}
 <div className="voice-safe"><ShieldCheck size={16}/> Voice content is not automatically scored for hiring. Test the Realtime API separately before real use.</div>
 <audio ref={soundRef} autoPlay playsInline/>
 </section>
}
