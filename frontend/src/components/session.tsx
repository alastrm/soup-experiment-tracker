"use client";
import {createContext, useContext, useState, type ReactNode} from "react";
import Link from "next/link";
import {useRouter} from "next/navigation";
import {api} from "../lib/api";

const Session = createContext({key: "", label: "", generation: 0, connect: (_key: string, _label: string) => {}, clear: () => {}});
export const useSession = () => useContext(Session);
export function SessionProvider({children}: {children: ReactNode}) {
  const [session, setSession] = useState({key: "", label: "", generation: 0});
  return <Session.Provider value={{...session, connect: (key, label) => setSession(s => ({key,label,generation:s.generation+1})),
    clear: () => setSession(s => ({key:"",label:"",generation:s.generation+1}))}}>{children}</Session.Provider>;
}
function AccessForm() {
  const session = useSession();
  const [key, setKey] = useState(""); const [name, setName] = useState("");
  const [busy, setBusy] = useState(false); const [error, setError] = useState("");
  const [issued, setIssued] = useState("");
  async function connect(create: boolean) {
    setBusy(true); setError("");
    try {
      if (create) {
        const result = await api<{api_key:string; project:{name:string}}>("/projects", "", undefined, {name: name || "My project"});
        setIssued(result.api_key); setKey(result.api_key);
      } else {
        await api("/runs?limit=1", key);
        session.connect(key, name || "Connected project"); setKey("");
      }
    } catch (e) {setError(e instanceof Error ? e.message : "Connection failed.");}
    finally {setBusy(false);}
  }
  return <div className="access panel"><div className="eyebrow">Project access</div><h1>Connect your project.</h1>
    <p className="muted">Connect a project to inspect runs and follow committed metrics live.</p>
    <form onSubmit={e => {e.preventDefault(); void connect(false);}} className="mt-7 grid gap-4">
      <label>Project label <span className="muted">(optional)</span><input aria-label="Project label" value={name} maxLength={100} onChange={e=>setName(e.target.value)} placeholder="Research workspace" /></label>
      <label>Project API key<input aria-label="Project API key" type="password" autoComplete="off" value={key} onChange={e=>setKey(e.target.value)} placeholder="soup_…" required /></label>
      {error && <p role="alert" className="error">{error}</p>}
      <button className="primary" disabled={busy || !key}>{busy ? "Connecting…" : "Connect project →"}</button>
    </form><div className="divider"/><p className="muted text-sm">Starting fresh? Create a local demo project.</p>
    <button className="secondary mt-3" disabled={busy} onClick={()=>void connect(true)}>Create project & key</button>
    {issued && <div className="notice mt-4"><strong>Save this key now.</strong><p>Shown once. Keep it somewhere safe, then connect above.</p><code className="break-all select-all">{issued}</code></div>}
    <p className="footnote mt-6">Keys stay in memory only. Reloading requires key entry again.</p></div>;
}
export function Shell({children}: {children: ReactNode}) {
  const session = useSession();
  const router = useRouter();
  return <div className="app-shell"><aside className="sidebar"><Link className="brand" href="/">soup<span className="brand-sub">tracker</span></Link>
    <div className="project-label"><small>Project</small><strong>{session.label || "No project connected"}</strong></div>
    <Link href="/" className="nav-active"><span aria-hidden="true">↗</span> Experiment runs</Link>
    <div className="sidebar-bottom"><span>Local workspace</span>{session.key && <button className="secondary" onClick={()=>{session.clear();router.push("/");}}>Switch project / key</button>}</div></aside>
    <div className="workspace"><header className="topbar"><span>Experiment tracking</span><span>Local session</span></header>
      <main>{session.key ? <div key={session.generation}>{children}</div> : <AccessForm/>}</main><footer>Soup / Experiment tracker <span>Keys stay in memory</span></footer></div></div>;
}
