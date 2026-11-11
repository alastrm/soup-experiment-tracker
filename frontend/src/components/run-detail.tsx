"use client";
import Link from "next/link";
import {useEffect, useRef, useState} from "react";
import {API, api, HTTPError} from "../lib/api";
import {applyEvent, HISTORY_LIMIT, initialModel, SSEParser, type LiveModel, type MetricEvent, type Snapshot} from "../lib/live";
import {Chart} from "./chart";
import {useSession} from "./session";

type Status = "connected"|"disconnected"|"reconnecting"|"error";
export function RunDetail({id}: {id:string}) {return <Detail id={id}/>;}
function Detail({id}: {id:string}) {
  const {key} = useSession();
  const [snapshot,setSnapshot] = useState<Snapshot|null>(null); const [model,setModel] = useState<LiveModel|null>(null);
  const [status,setStatus] = useState<Status>("reconnecting"); const [error,setError] = useState("");
  const [revision,setRevision] = useState(0); const [paused,setPaused] = useState(false);
  const pausedRef=useRef(false); const activeConnection=useRef<AbortController|null>(null);
  const [demoBusy,setDemoBusy]=useState(false); const [demoError,setDemoError]=useState("");
  const demoRequest=useRef<AbortController|null>(null);
  const demoBatch=useRef<{batch_id:string;events:Omit<MetricEvent,"seq">[]}|null>(null);
  useEffect(()=>()=>{demoRequest.current?.abort();},[]);
  async function sendDemo() {
    if(demoRequest.current)return;
    const controller=new AbortController();demoRequest.current=controller;setDemoBusy(true);setDemoError("");
    if(!demoBatch.current)demoBatch.current={batch_id:crypto.randomUUID(),events:Array.from({length:20},(_,i)=>i+1).flatMap(step=>[
      {event_id:crypto.randomUUID(),metric:"demo.loss",step,value:Number((0.1+0.8*Math.exp(-step/7)).toFixed(4)),occurred_at:new Date().toISOString()},
      {event_id:crypto.randomUUID(),metric:"demo.accuracy",step,value:Number((0.5+0.45*(1-Math.exp(-step/6))).toFixed(4)),occurred_at:new Date().toISOString()}
    ])};
    try {await api(`/runs/${id}/metrics`,key,controller.signal,demoBatch.current);demoBatch.current=null;}
    catch {if(!controller.signal.aborted)setDemoError("Could not confirm the demo batch. Retry safely with the same batch ID.");}
    finally {demoRequest.current=null;if(!controller.signal.aborted)setDemoBusy(false);}
  }
  // The effect owns a synchronous model. Publishing that exact immutable object
  // to React never races reconnect against a merely scheduled state update.
  useEffect(()=>{
    const lifetime = new AbortController(); let connection: AbortController|undefined;
    let current: LiveModel|undefined; let stopped=false; let timer: ReturnType<typeof setTimeout>|undefined;
    const pause = (ms:number) => new Promise<void>(resolve=>{
      const finish=()=>{clearTimeout(timer);lifetime.signal.removeEventListener("abort",finish);resolve();};
      timer=setTimeout(finish,ms);lifetime.signal.addEventListener("abort",finish,{once:true});
    });
    setSnapshot(null);setModel(null);setError("");setStatus("reconnecting");
    async function run() {
      let attempt=0;
      while (!lifetime.signal.aborted) {
        if(pausedRef.current){setStatus("disconnected");await pause(250);continue;}
        connection=new AbortController(); const active=connection; activeConnection.current=active;
        const abort=()=>active.abort(); lifetime.signal.addEventListener("abort",abort,{once:true});
        let inactivity: ReturnType<typeof setTimeout>|undefined; let retryAfter=0;
        try {
          if (!current) {
            const snap=await api<Snapshot>(`/runs/${id}`,key,active.signal);
            if(lifetime.signal.aborted)return;
            current=initialModel(snap);setSnapshot(snap);setModel(current);
          }
          setStatus("reconnecting");
          const response=await fetch(`${API}/runs/${id}/events`,{headers:{Authorization:`Bearer ${key}`,Accept:"text/event-stream","Last-Event-ID":String(current.cursor)},
            signal:active.signal,cache:"no-store",credentials:"omit"});
          if(!response.ok) {
            if(response.status===429||response.status>=500) {
              const retry=Number(response.headers.get("Retry-After"));
              if(Number.isFinite(retry)&&retry>0) retryAfter=Math.min(retry,30)*1000;
            } else throw new HTTPError(response.status);
            throw new Error("API temporarily unavailable");
          }
          if(!response.headers.get("content-type")?.startsWith("text/event-stream")||!response.body)throw new Error("Invalid stream response");
          const reader=response.body.getReader(); const decoder=new TextDecoder("utf-8",{fatal:true}); const parser=new SSEParser();
          const arm=()=>{clearTimeout(inactivity);inactivity=setTimeout(()=>active.abort(),25000);};arm();
          try {
            while(!lifetime.signal.aborted) {
              const {value,done}=await reader.read();if(done)break;arm();
              for(const frame of parser.feed(decoder.decode(value,{stream:true}))) {
                if(lifetime.signal.aborted)return;
                if(frame.event==="auth_expired")throw new HTTPError(401);
                const data=JSON.parse(frame.data);
                if(frame.event==="metric") {
                  if(!frame.id||!/^[1-9][0-9]*$/.test(frame.id)||Number(frame.id)!==data.seq)throw new Error("Invalid stream sequence");
                  current=applyEvent(current!,data as MetricEvent);setModel(current);
                } else if(frame.event==="caught_up") {
                  if(data.cursor!==current!.cursor)throw new Error("Incomplete replay");
                  attempt=0;setStatus("connected");setError("");
                } else throw new Error("Unknown stream event");
              }
            }
          } finally {await reader.cancel().catch(()=>{});reader.releaseLock();}
          throw new Error("Connection closed; recovering committed events");
        } catch(e) {
          if(lifetime.signal.aborted)return;
          if(e instanceof HTTPError) {setStatus("error");setError(e.status===409?"Cursor is ahead of storage. Use Reload snapshot to reset explicitly.":e.message);stopped=true;break;}
          const protocol=e instanceof Error && /Invalid|Sequence gap|Incomplete|frame|JSON|Unknown stream/.test(e.message);
          setStatus(pausedRef.current?"disconnected":"reconnecting");setError(pausedRef.current?"":protocol?"Stream validation failed. Recovering from the last applied event…":"Connection interrupted. Recovering from the last applied event…");
        } finally {clearTimeout(inactivity);active.abort();lifetime.signal.removeEventListener("abort",abort);}
        await pause(Math.max(retryAfter,Math.min(10000,500*2**Math.min(attempt++,5)*(0.8+Math.random()*0.4))));
      }
      if(!stopped&&!lifetime.signal.aborted)setStatus("disconnected");
    }
    void run();
    return ()=>{lifetime.abort();connection?.abort();clearTimeout(timer);};
  },[key,id,revision]);
  const values=Object.values(model?.values||{}).sort((a,b)=>a.metric.localeCompare(b.metric));
  return <><Link href="/" className="breadcrumb">← Experiment runs</Link><div className="page-heading mt-6"><div><div className="eyebrow">RUN DETAIL</div><h1>{snapshot?.run.name || "Loading run…"}</h1><p className="mono muted text-xs mt-2">{id}</p></div><div className="flex gap-2 items-center"><span role="status" data-testid="connection-status" className={`connection ${status}`}><i/>{status}</span><button className="secondary" onClick={()=>{pausedRef.current=!pausedRef.current;setPaused(pausedRef.current);activeConnection.current?.abort();}}>{paused?"Reconnect":"Disconnect"}</button></div></div>
    {error&&<div role="alert" className={status==="error"?"error notice":"notice"}>{error} {status==="error"&&<button className="subtle-link ml-3" onClick={()=>setRevision(r=>r+1)}>Reload snapshot</button>}</div>}
    <div className="summary-strip"><div><strong data-testid="event-count">{model?.count??"—"}</strong><span>Committed events</span></div><div><strong>{values.length}</strong><span>Tracked metrics</span></div><div><strong className="mono" data-testid="applied-cursor">{model?.cursor??"—"}</strong><span>Last applied sequence</span></div><div><strong>{status==="connected"?"Up to date":"Recovering"}</strong><span>Stream health</span></div></div>
    <div className="section-heading"><div><h2>Metric history</h2><p className="muted text-sm">Values by logical step. Charts recover from committed history.</p></div><span className="badge">LIVE METRICS</span></div>
    {!snapshot&&<div className="panel empty">Loading persisted metrics…</div>}
    {snapshot&&!values.length&&<div className="panel empty"><h3>This run has no metrics yet</h3><p>Preview live charts by sending 40 generated demo events to this run.</p><button className="primary mt-5" disabled={demoBusy||status!=="connected"} onClick={()=>void sendDemo()}>{demoBusy?"Sending demo metrics…":"Send demo metrics"}</button><p className="footnote">Demo data is labeled demo.loss / demo.accuracy and saved through the real API.</p><p className="footnote mt-3">For your own data, send batches to <code>POST /runs/{id}/metrics</code>.</p></div>}
    {demoError&&<div role="alert" className="notice error mt-4">{demoError}<button className="secondary ml-3" disabled={demoBusy} onClick={()=>void sendDemo()}>Retry demo batch</button></div>}
    <div className="metric-grid">{values.map((e,i)=><Chart key={e.metric} metric={e.metric} latest={e} history={model?.history||[]} index={i}/>)}</div>
    <div className="history-note"><span className="tiny-dot"/> Charts retain the last {HISTORY_LIMIT.toLocaleString("en")} committed events across metrics. Latest values include the full run.</div>
    <details className="panel event-details mt-6"><summary>Inspect recovered events <span className="count-pill" data-testid="history-count">{model?.history.length||0}</span></summary><div className="table-scroll"><table><thead><tr><th>Sequence</th><th>Metric</th><th>Step</th><th>Value</th></tr></thead><tbody>{model?.history.map(e=><tr key={e.seq} data-testid="history-row"><td>{e.seq}</td><td>{e.metric}</td><td>{e.step}</td><td>{e.value}</td></tr>)}</tbody></table></div></details></>;
}
