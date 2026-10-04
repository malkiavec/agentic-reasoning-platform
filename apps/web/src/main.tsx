import React from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

type Run={id:string;state:string;model:string;steps:number;tokens:number;latency:string};
const runs:Run[]=[
 {id:"run_01J9A8F2",state:"executing",model:"reasoning-default",steps:12,tokens:8421,latency:"18.4s"},
 {id:"run_01J9A71C",state:"waiting_approval",model:"reasoning-default",steps:7,tokens:5120,latency:"11.2s"},
 {id:"run_01J9A55B",state:"completed",model:"reasoning-default",steps:24,tokens:18420,latency:"42.7s"},
];
function App(){
 return <div className="shell">
  <aside><div className="brand">ARP <span>CONTROL PLANE</span></div>
   <nav><a className="active">Overview</a><a>Runs</a><a>Approvals <b>3</b></a><a>Agents</a><a>Tools</a><a>Memory</a><a>Evaluations</a></nav>
   <div className="tenant"><small>TENANT</small><strong>default</strong><span>Production</span></div>
  </aside>
  <main><header><div><small>OPERATIONS / OVERVIEW</small><h1>Agent Control Plane</h1></div><button>＋ New run</button></header>
   <section className="stats">
    <div><small>ACTIVE RUNS</small><strong>4</strong><em>+2 today</em></div>
    <div><small>AWAITING APPROVAL</small><strong>3</strong><em>2 high risk</em></div>
    <div><small>24H TOKENS</small><strong>1.82M</strong><em>+14.8%</em></div>
    <div><small>SUCCESS RATE</small><strong>97.4%</strong><em>+1.2%</em></div>
   </section>
   <section className="grid"><div className="panel wide"><div className="panelhead"><h2>Live runs</h2><span>● streaming</span></div>
    <table><thead><tr><th>RUN</th><th>STATE</th><th>MODEL</th><th>STEPS</th><th>TOKENS</th><th>LATENCY</th></tr></thead><tbody>
     {runs.map(r=><tr key={r.id}><td className="mono">{r.id}</td><td><i className={"dot "+r.state}/>{r.state.replace("_"," ")}</td><td>{r.model}</td><td>{r.steps}</td><td>{r.tokens.toLocaleString()}</td><td>{r.latency}</td></tr>)}
    </tbody></table></div>
    <div className="panel"><div className="panelhead"><h2>Approvals</h2><span>3 pending</span></div>
      <div className="approval"><div><strong>browser_write</strong><small>HIGH · run_01J9A71C</small></div><button>Review</button></div>
      <div className="approval"><div><strong>shell</strong><small>HIGH · run_01J9A44D</small></div><button>Review</button></div>
      <div className="approval"><div><strong>external_api</strong><small>MEDIUM · run_01J9A32A</small></div><button>Review</button></div>
    </div>
   </section>
   <section className="grid"><div className="panel wide"><div className="panelhead"><h2>Execution stream</h2><span>last 60s</span></div><div className="stream">
    <p><time>12:42:18</time><b>run_01J9A8F2</b> planner created 3-step execution plan</p>
    <p><time>12:42:19</time><b>agent</b> dispatched 2 parallel tool calls</p>
    <p><time>12:42:21</time><b>policy</b> tool <code>browser_write</code> requires approval</p>
    <p><time>12:42:24</time><b>memory</b> retrieved 8 relevant memories · rerank 0.91</p>
   </div></div>
    <div className="panel"><div className="panelhead"><h2>System health</h2><span className="ok">healthy</span></div>
     <div className="health"><label>API <span>99.99%</span></label><div><i style={{width:"99%"}}/></div><label>Worker queue <span>18%</span></label><div><i style={{width:"18%"}}/></div><label>PostgreSQL <span>42ms</span></label><div><i style={{width:"42%"}}/></div><label>Redis <span>8ms</span></label><div><i style={{width:"8%"}}/></div></div>
    </div>
   </section>
  </main>
 </div>
}
createRoot(document.getElementById("root")!).render(<React.StrictMode><App/></React.StrictMode>);