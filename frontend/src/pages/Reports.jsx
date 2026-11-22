import React,{useEffect,useState} from 'react'
import {FileText,Download,ShieldCheck} from 'lucide-react'
import {Link} from 'react-router-dom'
import {api} from '../api'
import {PageHead,Busy,ErrorText,Stage} from '../components/ui'
export async function downloadProtected(url,name){const b=await api(url,{blob:true}),a=document.createElement('a'),href=URL.createObjectURL(b);a.href=href;a.download=name;document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(href),1500)}
export default function Reports(){const [apps,setApps]=useState(null),[error,setError]=useState('')
 useEffect(()=>{api('/applications').then(setApps).catch(e=>setError(e.message))},[])
 return <><PageHead eyebrow="REPORTING / EVIDENCE" title={<>Interview <span className="gradient-text">reports</span></>} desc="On-demand PDF packets: requirements evidence, written transcripts and clearly separated human decision notes."/><ErrorText error={error}/>{!apps?<Busy/>:<div className="card glass"><div className="card-title-row"><h3>Evidence packets</h3><span className="pill-outline">{apps.length} applications</span></div>{apps.map(a=><div className="report-row" key={a.id}><span className="report-icon"><FileText size={21}/></span><div><strong>{a.candidate_name}</strong><p>{a.job_title} · application #{a.id}</p></div><Stage name={a.stage}/><button className="btn small outline" onClick={()=>downloadProtected(`/applications/${a.id}/report`,`interviewloop-report-${a.id}.pdf`).catch(e=>setError(e.message))}><Download size={14}/> PDF</button><Link to={`/applications/${a.id}`} className="text-link">Details</Link></div>)}{!apps.length&&<p>No application reports yet.</p>}</div>}<div className="notice info"><ShieldCheck size={16}/> Reports document evidence. They do not rank people, infer emotions, or decide employment outcomes.</div></>
}
