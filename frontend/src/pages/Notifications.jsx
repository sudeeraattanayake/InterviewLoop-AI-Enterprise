import React,{useEffect,useState} from 'react'
import {Bell,CheckCheck,ShieldCheck} from 'lucide-react'
import {Link} from 'react-router-dom'
import {api,post,patch} from '../api'
import {PageHead,ErrorText,Busy,dateLabel} from '../components/ui'
import {useAuth} from '../App'
export default function Notifications(){const {user}=useAuth(),[messages,setMessages]=useState(null),[checked,setChecked]=useState(!!user.email_opt_in),[error,setError]=useState(''),[saved,setSaved]=useState('')
 const refresh=()=>api('/notifications').then(setMessages).catch(e=>setError(e.message))
 useEffect(()=>{refresh()},[])
 return <><PageHead eyebrow="WORKSPACE / NOTIFICATIONS" title={<>Your <span className="gradient-text">inbox</span></>} desc="Private application updates, reminders and interview scheduling. Emails are optional and require explicit consent."/><ErrorText error={error}/>
 <div className="card glass"><h3>Communication preferences</h3><label className="consent-line"><input type="checkbox" checked={checked} onChange={e=>setChecked(e.target.checked)}/><span>Allow optional interview invitation emails when my organization has SMTP configured.</span></label><button className="btn small outline" onClick={async()=>{try{await patch('/auth/preferences',{email_opt_in:checked});setSaved('Preference saved')}catch(e){setError(e.message)}}}>Save preference</button> <span className="subtle">{saved}</span></div>
 {!messages?<Busy/>:<div className="card glass"><h3>Recent activity</h3>{messages.length===0&&<p>No notifications yet.</p>}{messages.map(n=><div className={`message-card ${!n.read?'unread':''}`} key={n.id}><Bell size={20}/><div><strong>{n.subject}</strong><p>{n.body}</p><small>{dateLabel(n.created_at)}</small>{n.application_id&&<div><Link to={`/applications/${n.application_id}`} className="text-link">Open application</Link></div>}</div>{!n.read&&<button className="btn small outline" onClick={async()=>{await post(`/notifications/${n.id}/read`);refresh()}}><CheckCheck size={15}/> Read</button>}</div>)}</div>}</>
}
