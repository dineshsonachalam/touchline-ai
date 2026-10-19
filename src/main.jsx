import React,{useEffect,useMemo,useState} from 'react';
import{createRoot}from'react-dom/client';
import{ScanSearch,ArrowRight,LoaderCircle}from'lucide-react';
import './style.css';
const clock=t=>`${String(Math.floor(t/60)).padStart(2,'0')}:${String(Math.floor(t%60)).padStart(2,'0')}`;
const X=x=>24+x*752/105,Y=y=>24+y*488/68;
const point=p=>`${X(p[0])},${Y(p[1])}`;
function Pitch({frame,opportunity,mode}){
 const home=frame?.home||[],away=frame?.away||[];
 const start=opportunity?.from, end=mode==='actual'?opportunity?.actual_ball_after_4s:opportunity?.action?.to;
 const color=mode==='actual'?'#ff998e':'#a9ffb1';
 const pathId=`arrow-${mode}`;
 const len=start&&end?Math.hypot(X(end[0])-X(start[0]),Y(end[1])-Y(start[1])):0;
 const ux=len?(X(end[0])-X(start[0]))/len:0,uy=len?(Y(end[1])-Y(start[1]))/len:0;
 // Stop the arrow before the destination marker so its number remains legible.
 const sx=start?X(start[0])+ux*14:0,sy=start?Y(start[1])+uy*14:0;
 const ex=end?X(end[0])-ux*17:0,ey=end?Y(end[1])-uy*17:0;
 return <svg className="pitch" viewBox="0 0 800 536" role="img" aria-label={mode==='actual'?'Recorded synthetic ball movement':'Hypothetical AI pass for Argentina'}>
 <defs><pattern id={`grass-${mode}`} width="92" height="536" patternUnits="userSpaceOnUse"><rect width="46" height="536" fill="#155e44"/><rect x="46" width="46" height="536" fill="#1b684b"/></pattern><marker id={pathId} markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto"><path d="M0 0 L6 3 L0 6" fill="none" stroke={color} strokeWidth="1.8"/></marker></defs>
 <rect width="800" height="536" fill={`url(#grass-${mode})`}/>
 <g fill="none" stroke="#dcf5e6" strokeOpacity=".65" strokeWidth="1.8"><rect x="24" y="24" width="752" height="488"/><path d="M400 24V512 M24 136H148V400H24 M776 136H652V400H776 M24 204H70V332H24 M776 204H730V332H776"/><circle cx="400" cy="268" r="67"/><circle cx="400" cy="268" r="2" fill="#dcf5e6"/></g>
 {opportunity&&start&&end&&len>12&&<g><path d={`M${sx} ${sy} L${ex} ${ey}`} stroke={color} strokeWidth="5.5" strokeDasharray="12 8" strokeLinecap="round" markerEnd={`url(#${pathId})`} fill="none"/><circle cx={X(end[0])} cy={Y(end[1])} r="21" stroke={color} strokeWidth="2.5" fill={color} fillOpacity=".1" strokeDasharray="5 5"/></g>}
 {home.map((p,i)=><g key={'h'+i} transform={`translate(${point(p)})`}><circle r="9.5" fill="#75cfff" stroke="#e7f8ff" strokeWidth="2"/><text y="3.4" fontSize="9" textAnchor="middle" fontWeight="800" fill="#0b3450">{i+1}</text></g>)}
 {away.map((p,i)=><g key={'a'+i} transform={`translate(${point(p)})`}><circle r="9.5" fill="#ff7d88" stroke="#ffe6e9" strokeWidth="2"/><text y="3.4" fontSize="9" textAnchor="middle" fontWeight="800" fill="#511522">{i+1}</text></g>)}
 {opportunity&&start&&<g><circle cx={X(start[0])} cy={Y(start[1])} r="18" fill="none" stroke="white" strokeWidth="2.5" strokeDasharray="4 4"/><circle cx={X(start[0])} cy={Y(start[1])} r="3.5" fill="white"/></g>}
 {!opportunity&&<g><rect x="175" y="217" width="450" height="96" rx="12" fill="#09231b" fillOpacity=".93"/><text x="400" y="259" fontSize="24" textAnchor="middle" fill="#f1fff5" fontWeight="700">Analyse the match</text><text x="400" y="286" fontSize="15" textAnchor="middle" fill="#a6c8b4">Discover three attacking opportunities</text></g>}
 </svg>
}
function App(){
 const[data,setData]=useState(null),[opps,setOpps]=useState([]),[chosen,setChosen]=useState(0),[busy,setBusy]=useState(false),[error,setError]=useState('');
 useEffect(()=>{fetch('/data/match.json').then(r=>{if(!r.ok)throw Error('Match data unavailable');return r.json()}).then(setData).catch(e=>setError(e.message))},[]);
 const scan=async()=>{if(busy)return;setBusy(true);setError('');try{const r=await fetch('/api/scan',{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'});const v=await r.json();if(!r.ok)throw Error(v.error||'Match analysis failed');setOpps(v.opportunities||[]);setChosen(0)}catch(e){setError(e.message)}finally{setBusy(false)}};
 const o=opps[chosen];
 const frame=useMemo(()=>{if(!data)return null;return o?data.frames[o.frame_index]:data.frames[Math.floor(data.frames.length*.53)]},[data,o]);
 return <div className="shell"><header className="header"><div className="logo"><span className="logo-symbol">◈</span> TOUCHLINE <b>AI</b></div><span className="header-tag">FIND WHAT'S POSSIBLE</span></header><main className="layout">
 <div className="toolbar"><div className="toolbar-title"><h1>Find Argentina's next move.</h1><span>FICTIONAL MATCH · SYNTHETIC TRACKING · {data?clock(data.duration):'96 MIN'}</span></div><button className="scan" onClick={scan} disabled={busy||!data}>{busy?<><LoaderCircle size={18} className="spin"/> ANALYSING MATCH…</>:<><ScanSearch size={18}/>{opps.length?'SCAN AGAIN':'ANALYSE MATCH'}<ArrowRight size={18}/></>}</button></div>
 <div className="match-banner"><div className="teams"><strong>🇦🇷 ARGENTINA</strong><span className="vs">vs</span><strong>🇪🇸 SPAIN</strong></div><div className="coach"><span className="dot blue"/> AI COACH FOR ARGENTINA <span className="time">{o?clock(o.time):'MATCH 01'}</span></div></div>
 <div className="comparison">
 <section className="comparison-panel"><div className="panel-heading"><span className="panel-title actual-title"><span className="small-line red-line"/> ACTUAL</span><span className="panel-subtitle">What happened in the synthetic match</span></div><Pitch frame={frame} opportunity={o} mode="actual"/></section>
 <section className="comparison-panel"><div className="panel-heading"><span className="panel-title ai-title"><span className="small-line green-line"/> AI SUGGESTED</span><span className="panel-subtitle">Alternative pass for Argentina</span></div><Pitch frame={frame} opportunity={o} mode="ai"/></section>
 {busy&&<div className="scan-overlay" role="status" aria-live="polite"><LoaderCircle size={38} className="spin"/><strong>Analysing synthetic match</strong><span>Finding Argentina's attacking opportunities…</span><div className="loading-track"><div/></div></div>}
 </div>
 <div className="bottom"><div className="moments">{opps.length?opps.map((item,i)=><button key={item.id} className={'moment '+(chosen===i?'active':'')} onClick={()=>setChosen(i)}><span className="moment-num">0{i+1}</span><span className="moment-time">{clock(item.time)}</span></button>):<div className="empty-moments">{busy?'SCANNING MATCH…':'THREE OPPORTUNITIES WILL APPEAR HERE'}</div>}</div>{o&&<div className="action-detail"><span className="dot blue"/> ARGENTINA {o.carrier_index+1} <ArrowRight size={15}/> {o.action.to_index+1} <span className="tag">AI OPTION</span></div>}</div>
 <div className="disclaimer">Actual = recorded synthetic ball movement, not necessarily a completed pass. AI suggested = hypothetical pass, not a predicted goal.</div>
 {error&&<div className="error" role="alert">{error}<button onClick={()=>setError('')} aria-label="Dismiss error">×</button></div>}
 </main></div>;
}
createRoot(document.getElementById('root')).render(<App/>);
