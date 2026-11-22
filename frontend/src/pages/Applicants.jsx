import React,{useEffect,useState} from 'react'
import {Link,useSearchParams} from 'react-router-dom'
import {ArrowRight,ChevronRight,Filter,Search,Users} from 'lucide-react'
import {api} from '../api'
import {Badge,Busy,Empty,PageHead,Stage,dateLabel,stageInfo} from '../components/ui'
export default function Applicants(){
 const [params]=useSearchParams(),[apps,setApps]=useState([]),[jobs,setJobs]=useState([]),[loading,setLoading]=useState(true),[search,setSearch]=useState(params.get('q')||''),[job,setJob]=useState('all'),[stage,setStage]=useState('all')
 useEffect(()=>{Promise.all([api('/applications'),api('/jobs')]).then(([a,j])=>{setApps(a);setJobs(j)}).finally(()=>setLoading(false))},[])
 const visible=apps.filter(a=>(job==='all'||String(a.job_id)===job)&&(stage==='all'||a.stage===stage)&&`${a.candidate_name} ${a.candidate_email} ${a.job_title}`.toLowerCase().includes(search.toLowerCase()))
 const buckets=[['All candidates','all'],['Awaiting CV review','awaiting_cv_review'],['AI video interview','video_invited'],['Video review','awaiting_video_review'],['Coding review','coding_submitted'],['Individual interview','individual_scheduled'],['Offers','offer_extended']]
 return <><PageHead eyebrow="RECRUITMENT / PEOPLE" title={<>Talent <span className="gradient-text">pipeline</span></>} desc="Every candidate, every stage, all in one beautifully clear view."/>
 <div className="pipeline-tabs">{buckets.map(([title,code])=><button key={code} className={stage===code?'active':''} onClick={()=>setStage(code)}>{title}<span>{code==='all'?apps.length:apps.filter(a=>a.stage===code).length}</span></button>)}</div>
 <div className="toolbar glass"><div className="search-field"><Search size={18}/><input value={search} onChange={e=>setSearch(e.target.value)} placeholder="Search candidates or positions..."/></div><div className="filter-input"><Filter size={16}/><select value={job} onChange={e=>setJob(e.target.value)}><option value="all">All positions</option>{jobs.map(j=><option value={j.id} key={j.id}>{j.title}</option>)}</select></div></div>
 {loading?<Busy/>:visible.length?<div className="card glass"><div className="card-title-row"><div><h3>Applicants <span className="count-pill">{visible.length}</span></h3><p>Recruiter review and individual approval are mandatory</p></div><Badge color="cyan">HITL enabled</Badge></div><div className="table-scroll"><table className="data-table"><thead><tr><th>CANDIDATE</th><th>ROLE</th><th>APPLIED</th><th>STATUS</th><th>REVIEW</th></tr></thead><tbody>{visible.map(a=><tr key={a.id}><td><div className="person"><span className="person-avatar">{a.candidate_name.slice(0,1)}</span><div><b>{a.candidate_name}</b><small>{a.candidate_email}</small></div></div></td><td><b>{a.job_title}</b><small className="table-sub">{a.department}</small></td><td>{dateLabel(a.created_at)}</td><td><Stage name={a.stage}/></td><td><Link to={`/applications/${a.id}`} className="review-link">View profile <ArrowRight size={15}/></Link></td></tr>)}</tbody></table></div></div>:<Empty icon={Users} title="No matching applicants" desc={apps.length?'Try adjusting your filters or search terms.':'Your applicants will be shown here once candidates apply.'}/>}
 </>
}
