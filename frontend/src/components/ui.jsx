import React, {useState} from 'react'
import {motion} from 'framer-motion'
import { AlertCircle, Check, CheckCircle2, CircleHelp, Clock, Film, FileSearch, GraduationCap, Layers3, LoaderCircle, Mic, Sparkles, X } from 'lucide-react'

export const stageInfo = {
  processing_cv: ['Analyzing CV', 'indigo'], awaiting_cv_review: ['CV review', 'amber'], cv_processing_error:['Needs support','red'],
  video_invited:['Video interview','purple'], awaiting_video_review:['Video review','amber'], video_processing_error:['Needs support','red'],
  coding_invited:['Coding assessment','purple'],coding_submitted:['Code review','amber'],individual_pending:['Interview pending','cyan'], individual_scheduled:['Interview scheduled','cyan'],
  offer_extended:['Offer extended','green'], declined_cv:['Closed at CV review','muted'], declined_video:['Closed at video review','muted'], declined_final:['Closed after interview','muted'],declined_code:['Closed at coding review','muted'],hired:['Offer accepted','green'],offer_declined:['Offer declined','muted']
}
export function Stage({name}) { const [text, color] = stageInfo[name] || [name?.replaceAll('_',' ') || 'Unknown','muted']; return <span className={`stage ${color}`}><span className="stage-dot"/>{text}</span> }
export function Badge({children, color='purple'}) { return <span className={`tag ${color}`}>{children}</span> }
export function IconPill({icon:Icon,color='purple'}) { return <span className={`icon-pill ${color}`}><Icon size={19}/></span> }
export function PageHead({eyebrow, title, desc, action}) {return <motion.div initial={{opacity:0,y:13}} animate={{opacity:1,y:0}} transition={{duration:.4,ease:'easeOut'}} className="page-head"><div><div className="eyebrow">{eyebrow}</div><h1>{title}</h1>{desc && <p>{desc}</p>}</div>{action && <div>{action}</div>}</motion.div>}
export function Empty({icon:Icon=Layers3, title='Nothing here yet', desc='', action}) {return <div className="empty"><div className="empty-icon"><Icon size={28}/></div><h3>{title}</h3><p>{desc}</p>{action}</div>}
export function Busy({message='Loading workspace...'}) {return <div className="busy"><LoaderCircle size={30} className="spin"/><span>{message}</span></div>}
export function ErrorText({error}) {return error && <div className="notice error"><AlertCircle size={16}/>{error}</div>}
export function SuccessText({text}) {return text && <div className="notice success"><CheckCircle2 size={17}/>{text}</div>}
export function Modal({title, onClose, children, wide=false}) { return <div className="modal-backdrop" onMouseDown={e=>{if(e.target===e.currentTarget) onClose()}}><div className={`modal glass ${wide?'wide':''}`} role="dialog" aria-modal="true"><div className="modal-head"><h2>{title}</h2><button className="icon-button" onClick={onClose} aria-label="Close"><X size={20}/></button></div>{children}</div></div> }
export function Evidence({data, type='cv'}) {
 if (!data || !Object.keys(data).length) return <Empty icon={FileSearch} title="Evidence pending" desc="Analysis is still processing. Ask a recruiter if this persists." />
 return <div className="evidence-panel"><div className="notice info"><CircleHelp size={17}/><span>Evidence assistance only. <strong>Not a hiring recommendation.</strong> Human review is required for every decision.</span></div>
 <div className="evidence-summary"><span className="eyebrow">{data.mode?.replaceAll('_',' ')||'Evidence'} report</span><p>{data.summary}</p></div>
 <div className="evidence-list">{(data.items||[]).map((e,i)=><div key={i} className="evidence-item"><div className="evidence-title"><span className="index">{String(i+1).padStart(2,'0')}</span><h4>{e.requirement||e.skill}</h4>{e.status && <Badge color={e.status==='evidenced'?'green':e.status==='unclear'?'amber':'muted'}>{e.status.replaceAll('_',' ')}</Badge>}</div>{e.excerpt && <blockquote>“{e.excerpt}”</blockquote>}<p>{e.explanation||e.observation}</p>{e.follow_up && <p className="subtle"><strong>Follow-up:</strong> {e.follow_up}</p>}</div>)}</div>
 {data.recruiter_questions?.length>0 && <div className="panel-note"><strong>Suggested clarifying questions</strong>{data.recruiter_questions.map((q,i)=><p key={i}>• {q}</p>)}</div>}
 {data.limitations?.length>0 && <p className="subtle">Limitations: {data.limitations.join(' · ')}</p>}
 </div>
}
export function useAsync() {const [loading,setLoading]=useState(false),[error,setError]=useState(''); async function run(fn) {setLoading(true);setError('');try {return await fn()} catch(e){setError(e.message); return null}finally{setLoading(false)}}return {loading,error,setError,run}}
export function timeLabel(value) {if(!value)return 'Not scheduled';const dt=new Date(value); return Number.isNaN(dt.getTime())?value:dt.toLocaleString(undefined,{dateStyle:'medium',timeStyle:'short'})}
export function dateLabel(value) {if(!value)return '—';const dt=new Date(value);return Number.isNaN(dt.getTime())?'—':dt.toLocaleDateString(undefined,{month:'short',day:'numeric',year:'numeric'})}
