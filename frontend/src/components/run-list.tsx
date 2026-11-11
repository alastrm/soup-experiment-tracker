"use client";
import Link from "next/link";
import {useEffect, useState} from "react";
import {api} from "../lib/api";
import type {Run} from "../lib/live";
import {useSession} from "./session";
export function RunList() {
  return <RunListBody/>;
}
function RunListBody() {
  const {key, label} = useSession(); const [runs,setRuns] = useState<Run[]>([]);
  const [after,setAfter] = useState<string|null>(null); const [loading,setLoading] = useState(true);
  const [error,setError] = useState(""); const [filter,setFilter] = useState(""); const [name,setName] = useState("");
  const [revision,setRevision] = useState(0);
  useEffect(()=>{const controller = new AbortController(); setLoading(true); setError("");
    api<{runs:Run[];next_after:string|null}>("/runs?limit=100",key,controller.signal).then(r=>{setRuns(r.runs);setAfter(r.next_after);}).catch(e=>{if(!controller.signal.aborted)setError(e.message);}).finally(()=>{if(!controller.signal.aborted)setLoading(false);});
    return ()=>controller.abort();},[key,revision]);
  async function more() {try {const r=await api<{runs:Run[];next_after:string|null}>(`/runs?limit=100&after=${after}`,key);setRuns(old=>[...old,...r.runs]);setAfter(r.next_after);}catch(e){setError((e as Error).message);}}
  async function create() {if(!name.trim())return;try {await api("/runs",key,undefined,{name:name.trim()});setName("");setRevision(r=>r+1);}catch(e){setError((e as Error).message);}}
  const visible=runs.filter(r=>r.name.toLowerCase().includes(filter.toLowerCase()));
  return <><div className="eyebrow">EXPERIMENT TRACKING</div><div className="page-heading"><div><h1>Experiment runs</h1><p className="muted">{label} <span className="separator">/</span> Inspect persisted runs and their live metrics.</p></div><button className="secondary" onClick={()=>setRevision(r=>r+1)}>↻ Refresh</button></div>
    <div className="summary-strip"><div><strong>{runs.length}{after?"+":""}</strong><span>Runs in this project</span></div><div><strong>Live</strong><span>Recoverable event streams</span></div><div><strong>Isolated</strong><span>Project-scoped access</span></div></div>
    <section className="panel"><div className="table-tools"><div className="flex gap-3 items-center"><h2>Runs</h2><span className="count-pill">{visible.length}</span></div><input aria-label="Search runs" placeholder="Search runs…" value={filter} onChange={e=>setFilter(e.target.value)}/></div>
      {error && <p role="alert" className="error p-5">{error}</p>}
      {loading ? <div className="empty">Loading project runs…</div> : <div className="table-scroll"><table><thead><tr><th>Run name</th><th>Run ID</th><th>Created</th><th>Metrics</th></tr></thead><tbody>{visible.map(run=><tr key={run.id}><td><Link href={`/runs/${run.id}`} className="run-link"><span className="run-icon">↗</span>{run.name}</Link></td><td className="mono muted">{run.id.slice(0,8)}…</td><td className="muted">{new Date(run.created_at).toLocaleString()}</td><td><Link className="subtle-link" href={`/runs/${run.id}`}>View live metrics →</Link></td></tr>)}</tbody></table>{!visible.length&&<div className="empty"><h3>{filter?"No matching runs":"No runs yet"}</h3><p>Create a run below, then send a metric batch to FastAPI.</p></div>}</div>}
      {after&&<button className="secondary m-5" onClick={()=>void more()}>Load more runs</button>}
      <form className="create-run" onSubmit={e=>{e.preventDefault();void create();}}><input aria-label="New run name" placeholder="New run name" maxLength={100} value={name} onChange={e=>setName(e.target.value)} required/><button className="primary" disabled={!name.trim()}>+ Create run</button></form></section>
    <p className="footnote mt-5">Open a run to follow its metrics. List refresh is explicit; run detail updates automatically.</p></>;
}
