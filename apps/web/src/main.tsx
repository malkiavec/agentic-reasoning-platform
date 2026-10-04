import React, { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

type Run={run_id:string;state:string;model:string;reasoning_effort:string;created_at:string;updated_at:string};
type Tool={name:string;description:string;risk:string;requires_approval:boolean};

async function api<T>(path:string, init?:RequestInit):Promise<T>{
  const response=await fetch(path,{...init,credentials:"include",headers:{"Content-Type":"application/json",...(init?.headers||{})}});
  if(!response.ok) throw new Error((await response.json().catch(()=>({}))).detail||`HTTP ${response.status}`);
  return response.json();
}

function App(){
  const [runs,setRuns]=useState<Run[]>([]);
  const [tools,setTools]=useState<Tool[]>([]);
  const [prompt,setPrompt]=useState("");
  const [error,setError]=useState("");
  const [busy,setBusy]=useState(false);

  const refresh=async()=>{try{
    const [r,t]=await Promise.all([api<Run[]>("/v1/runs"),api<Tool[]>("/v1/tools")]);
    setRuns(r); setTools(t); setError("");
  }catch(e){setError(e instanceof Error?e.message:"Unable to load control plane");}};
  useEffect(()=>{refresh(); const timer=setInterval(refresh,3000); return()=>clearInterval(timer)},[]);

  const newRun=async()=>{
    if(!prompt.trim()) return;
    setBusy(true);
    try{await api("/v1/runs",{method:"POST",body:JSON.stringify({prompt:prompt.trim()})});setPrompt("");await refresh();}
    catch(e){setError(e instanceof Error?e.message:"Unable to create run");}
    finally{setBusy(false);}
  };
  const cancel=async(id:string)=>{try{await api(`/v1/runs/${id}/cancel`,{method:"POST"});await refresh();}catch(e){setError(e instanceof Error?e.message:"Cancel failed");}};
  const retry=async(id:string)=>{try{await api(`/v1/runs/${id}/retry`,{method:"POST"});await refresh();}catch(e){setError(e instanceof Error?e.message:"Retry failed");}};

  const active=runs.filter(r=>!["completed","failed","cancelled"].includes(r.state)).length;
  return <div className="shell">
    <aside><div className="brand">ARP <span>CONTROL PLANE</span></div>
      <nav><a className="active">Overview</a><a>Runs</a><a>Approvals</a><a>Tools</a><a>Memory</a><a>Evaluations</a></nav>
      <div className="tenant"><small>AUTHENTICATED TENANT</small><strong>Current tenant</strong><span>Live control plane</span></div>
    </aside>
    <main><header><div><small>OPERATIONS / OVERVIEW</small><h1>Agent Control Plane</h1></div></header>
      {error&&<div className="panel error">{error}</div>}
      <section className="stats">
        <div><small>ACTIVE RUNS</small><strong>{active}</strong><em>live</em></div>
        <div><small>TOTAL RUNS</small><strong>{runs.length}</strong><em>latest 50</em></div>
        <div><small>REGISTERED TOOLS</small><strong>{tools.length}</strong><em>executable only</em></div>
        <div><small>HIGH-RISK TOOLS</small><strong>{tools.filter(t=>t.requires_approval).length}</strong><em>approval gated</em></div>
      </section>
      <section className="panel composer"><div className="panelhead"><h2>New agent run</h2><span>authenticated</span></div>
        <textarea value={prompt} onChange={e=>setPrompt(e.target.value)} placeholder="Describe the task for the agent..." />
        <button disabled={busy||!prompt.trim()} onClick={newRun}>{busy?"Queueing…":"＋ New run"}</button>
      </section>
      <section className="grid"><div className="panel wide"><div className="panelhead"><h2>Live runs</h2><span>auto-refresh 3s</span></div>
        <table><thead><tr><th>RUN</th><th>STATE</th><th>MODEL</th><th>EFFORT</th><th>UPDATED</th><th>ACTION</th></tr></thead><tbody>
          {runs.map(r=><tr key={r.run_id}><td className="mono">{r.run_id.slice(0,12)}</td><td><i className={"dot "+r.state}/>{r.state.replace("_"," ")}</td><td>{r.model}</td><td>{r.reasoning_effort}</td><td>{new Date(r.updated_at).toLocaleTimeString()}</td><td>{r.state==="failed"||r.state==="cancelled"?<button onClick={()=>retry(r.run_id)}>Retry</button>:r.state!=="completed"?<button onClick={()=>cancel(r.run_id)}>Cancel</button>:null}</td></tr>)}
        </tbody></table>
      </div>
      <div className="panel"><div className="panelhead"><h2>Executable tools</h2><span>{tools.length}</span></div>
        {tools.map(t=><div className="approval" key={t.name}><div><strong>{t.name}</strong><small>{t.risk.toUpperCase()} · {t.requires_approval?"APPROVAL REQUIRED":"AUTOMATED"}</small></div></div>)}
      </div></section>
    </main>
  </div>;
}
createRoot(document.getElementById("root")!).render(<React.StrictMode><App/></React.StrictMode>);
