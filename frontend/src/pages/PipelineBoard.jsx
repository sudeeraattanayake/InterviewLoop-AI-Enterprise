import React,{useEffect,useState} from 'react'
import {useNavigate} from 'react-router-dom'
import {api} from '../api'
import {PageHead,Stage,Busy,ErrorText} from '../components/ui'
import {ArrowUpRight,GripVertical,ShieldCheck} from 'lucide-react'

const groups=[
 {name:'Incoming & CV review',stages:['processing_cv','awaiting_cv_review','cv_processing_error']},
 {name:'AI video studio',stages:['video_invited','awaiting_video_review','video_processing_error']},
 {name:'Technical assessment',stages:['coding_invited','coding_submitted']},
 {name:'Individual interview',stages:['individual_pending','individual_scheduled']},
 {name:'Final outcomes',stages:['offer_extended','hired','offer_declined','declined_cv','declined_video','declined_code','declined_final']},
]
export default function PipelineBoard(){
 const [apps,setApps]=useState([]),[loading,setLoading]=useState(true),[error,setError]=useState(''),[dragged,setDragged]=useState(null),[hint,setHint]=useState('')
 const navigate=useNavigate()
 useEffect(()=>{api('/applications').then(setApps).catch(e=>setError(e.message)).finally(()=>setLoading(false))},[])
 return <><PageHead eyebrow="RECRUITMENT / BOARD" title={<>Visual <span className="gradient-text">pipeline</span></>} desc="Drag a candidate onto another column to open the required human approval step. Dragging never skips an interview or silently changes a hiring decision."/>
 {loading?<Busy/>:<><ErrorText error={error}/>{hint&&<div className="notice info">{hint}</div>}<div className="kanban-board">{groups.map(group=><section className="kanban-column glass" key={group.name} onDragOver={e=>e.preventDefault()} onDrop={e=>{e.preventDefault();if(dragged){setHint(`Opening application #${dragged}: review evidence and record a human decision before changing any stage.`);navigate(`/applications/${dragged}`)}}}>
 <div className="kanban-header"><b>{group.name}</b><span>{apps.filter(a=>group.stages.includes(a.stage)).length}</span></div>
 <div className="kanban-cards">{apps.filter(a=>group.stages.includes(a.stage)).map(a=><div key={a.id} draggable onDragStart={()=>setDragged(a.id)} onDragEnd={()=>setDragged(null)} className="kanban-card" onClick={()=>navigate(`/applications/${a.id}`)} role="button" tabIndex={0} onKeyDown={e=>e.key==='Enter'&&navigate(`/applications/${a.id}`)}>
 <div className="kanban-top"><span className="eyebrow">#{a.id.toString().padStart(4,'0')}</span><GripVertical size={15}/></div><strong>{a.candidate_name}</strong><p>{a.job_title}</p><Stage name={a.stage}/><div className="kanban-bottom"><span>Human-led</span><ArrowUpRight size={15}/></div></div>)}{!apps.some(a=>group.stages.includes(a.stage))&&<div className="kanban-empty">Drop a candidate here to review the required stage action.</div>}</div>
 </section>)}</div><p className="subtle"><ShieldCheck size={15} style={{verticalAlign:'middle'}}/> All decisions are recorded through dedicated approval endpoints, with immutable stage transitions for this demo.</p></>}</>
}
