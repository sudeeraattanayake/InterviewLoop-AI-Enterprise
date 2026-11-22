import React,{createContext,useContext,useEffect,useState} from 'react'
import {Link, Navigate, NavLink, Route, Routes, useLocation, useNavigate} from 'react-router-dom'
import { Activity, ArrowRight, Bell, BriefcaseBusiness, ChartNoAxesCombined, ChevronDown, CircleHelp, Command, FileText, LayoutDashboard, LogOut, Menu, MicVocal, Search, ShieldCheck, Sparkles, UserRound, Users, WandSparkles, X } from 'lucide-react'
import {api,clearAuth,getCachedUser,getToken} from './api'
import Auth from './pages/Auth'
import Dashboard from './pages/Dashboard'
import Jobs from './pages/Jobs'
import Applicants from './pages/Applicants'
import ApplicationDetail from './pages/ApplicationDetail'
import Interview from './pages/Interview'
import Candidate from './pages/Candidate'
import ActivityPage from './pages/Activity'
import PipelineBoard from './pages/PipelineBoard'
import Workspace from './pages/Workspace'
import Analytics from './pages/Analytics'
import Notifications from './pages/Notifications'
import Reports from './pages/Reports'
import ChallengeSetup from './pages/ChallengeSetup'
import Coding from './pages/Coding'
import IndividualRoom from './pages/IndividualRoom'
import PrivacyCenter from './pages/PrivacyCenter'
import {KanbanSquare, Building2, Code2, BarChart3, FolderDown} from 'lucide-react'
const AuthContext=createContext(null)
export const useAuth=()=>useContext(AuthContext)

function Logo({small=false}) {return <div className="brand"><span className="brand-symbol"><span/><span/><span/><span/></span>{!small&&<div className="brand-name">Interview<span>Loop</span><sup>AI</sup></div>}</div>}
function Shell({children}) {
 const {user,logout}=useAuth(),[mobile,setMobile]=useState(false),[search,setSearch]=useState(''),navigate=useNavigate(),loc=useLocation()
 useEffect(()=>setMobile(false),[loc.pathname])
 const recruiter=user.role==='recruiter'
 const nav=recruiter?[
  {to:'/',name:'Overview',icon:LayoutDashboard},{to:'/jobs',name:'Job openings',icon:BriefcaseBusiness},
  {to:'/applicants',name:'Talent pipeline',icon:Users},{to:'/pipeline',name:'ATS board',icon:KanbanSquare},{to:'/analytics',name:'Analytics',icon:BarChart3},{to:'/reports',name:'Evidence reports',icon:FolderDown},{to:'/workspace',name:'Team workspace',icon:Building2},{to:'/notifications',name:'Notifications',icon:Bell},{to:'/activity',name:'Audit trail',icon:Activity}
 ]:[{to:'/',name:'My space',icon:LayoutDashboard},{to:'/opportunities',name:'Explore jobs',icon:BriefcaseBusiness},{to:'/applications',name:'My applications',icon:FileText},{to:'/notifications',name:'Notifications',icon:Bell},{to:'/privacy',name:'Privacy center',icon:ShieldCheck}]
 const jump=(e)=>{e.preventDefault(); if(search.trim())navigate(recruiter?`/applicants?q=${encodeURIComponent(search)}`:`/opportunities?q=${encodeURIComponent(search)}`)}
 return <div className="app-shell"><div className="background-orb orb-a"/><div className="background-orb orb-b"/><div className="background-grid"/>
  {mobile&&<div className="mobile-shade" onClick={()=>setMobile(false)}/>}
  <aside className={`sidebar glass ${mobile?'open':''}`}>
   <div className="sidebar-brand"><Logo/><button className="icon-button side-close" onClick={()=>setMobile(false)}><X size={18}/></button></div>
   <div className="workspace-switch"><div className="workspace-icon"><Command size={19}/></div><div><b>{recruiter?'Talent workspace':'Candidate portal'}</b><span>{recruiter?'Recruitment intelligence':'Your career, in motion'}</span></div><ChevronDown size={16} className="dim"/></div>
   <div className="sidebar-label">WORKSPACE</div><nav className="nav-list">{nav.map(({to,name,icon:Icon})=><NavLink end={to==='/'} to={to} key={to} className={({isActive})=>`nav-item ${isActive?'active':''}`}><Icon size={19}/><span>{name}</span>{to==='/'&&<span className="nav-star"/>}</NavLink>)}</nav>
   <div className="sidebar-label spaced">AI SYSTEM</div><div className="nav-item muted-nav"><WandSparkles size={18}/>Agentic subgraphs <span className="mini-status"/></div><div className="nav-item muted-nav"><ShieldCheck size={18}/>Human approval gates</div>
   <div className="sidebar-spacer"/>
   <div className="side-spotlight"><div className="spotlight-glow"/><Sparkles size={22}/><h4>Hire with clarity.</h4><p>Evidence-led decisions. Humans always in control.</p><span className="mini-rule">Ethical AI by design</span></div>
   <button className="profile-side" onClick={logout}><span className="avatar">{user.name.slice(0,1).toUpperCase()}</span><span><strong>{user.name}</strong><small>{recruiter?'Recruiter admin':'Candidate'}</small></span><LogOut size={17}/></button>
  </aside>
  <main className="main"><header className="topbar"><div className="topbar-left"><button className="icon-button mobile-menu" onClick={()=>setMobile(true)} aria-label="Open menu"><Menu size={21}/></button><div className="breadcrumb">Workspace <span>/</span> <b>{nav.find(n=>loc.pathname===n.to)?.name||'Details'}</b></div></div><div className="topbar-actions"><form className="global-search" onSubmit={jump}><Search size={17}/><input value={search} onChange={e=>setSearch(e.target.value)} placeholder={recruiter?'Search talent...':'Search opportunities...'}/><kbd>↵</kbd></form><span className="connection-pill"><span/>Secured workspace</span><span className="top-avatar">{user.name.slice(0,1).toUpperCase()}</span></div></header>
  <div className="content">{children}</div><footer className="footer"><span>© 2026 InterviewLoop AI · Recruiter-controlled by design</span><span><ShieldCheck size={14}/> Privacy-aware workspace</span></footer></main>
 </div>
}
export default function App(){
 const [user,setUser]=useState(getCachedUser()),[checking,setChecking]=useState(!!getToken())
 useEffect(()=>{let live=true;if(getToken()){api('/auth/me').then(u=>{if(live)setUser(u)}).catch(()=>{if(live)setUser(null)}).finally(()=>{if(live)setChecking(false)})}else setChecking(false);const handle=()=>setUser(null);window.addEventListener('interviewloop:unauthorized',handle);return ()=>{live=false;window.removeEventListener('interviewloop:unauthorized',handle)}},[])
 const login=(x)=>setUser(x.user),logout=()=>{clearAuth();setUser(null)}
 if(checking)return <div className="splash"><Logo/><div className="loader-pulse"/></div>
 return <AuthContext.Provider value={{user,login,logout}}>{!user?<Auth/>:<Shell><Routes>{user.role==='recruiter'?<>
  <Route path="/" element={<Dashboard/>}/><Route path="/jobs" element={<Jobs/>}/><Route path="/applicants" element={<Applicants/>}/><Route path="/applications/:id" element={<ApplicationDetail/>}/><Route path="/activity" element={<ActivityPage/>}/><Route path="/pipeline" element={<PipelineBoard/>}/><Route path="/analytics" element={<Analytics/>}/><Route path="/reports" element={<Reports/>}/><Route path="/workspace" element={<Workspace/>}/><Route path="/challenges/:id" element={<ChallengeSetup/>}/><Route path="/room/:id" element={<IndividualRoom/>}/><Route path="/notifications" element={<Notifications/>}/><Route path="*" element={<Navigate to="/"/>}/>
 </>:<><Route path="/" element={<Candidate home/>}/><Route path="/opportunities" element={<Candidate/>}/><Route path="/applications" element={<Candidate applicationsOnly/>}/><Route path="/applications/:id" element={<ApplicationDetail/>}/><Route path="/interview/:id" element={<Interview/>}/><Route path="/coding/:id" element={<Coding/>}/><Route path="/room/:id" element={<IndividualRoom/>}/><Route path="/notifications" element={<Notifications/>}/><Route path="/privacy" element={<PrivacyCenter/>}/><Route path="*" element={<Navigate to="/"/>}/></>}</Routes></Shell>}</AuthContext.Provider>
}
