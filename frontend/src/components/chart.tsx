"use client";
import {useState} from "react";
import {chartPoints, type MetricEvent} from "../lib/live";
export const number = (value: number) => value === 0 ? "0" : Math.abs(value) >= 1e5 || Math.abs(value) < 0.001 ? value.toExponential(3) : new Intl.NumberFormat("en", {maximumFractionDigits:4}).format(value);
export function Chart({metric, history, latest, index}: {metric:string; history:MetricEvent[]; latest:MetricEvent; index:number}) {
  const points = chartPoints(history, metric); const [hover, setHover] = useState<MetricEvent | null>(null);
  const color = ["#8c9eff", "#52c9ae", "#e9b56e", "#ce93e5"][index % 4];
  const minX = points[0]?.step || 0, maxX = points.at(-1)?.step || 1;
  const scale = Math.max(...points.map(p=>Math.abs(p.value)), 1e-300);
  const ys = points.map(p=>p.value/scale), minY = Math.min(...ys,0), maxY = Math.max(...ys,0.01);
  const x = (v:number) => 56 + ((v-minX)/(maxX-minX || 1))*468;
  const y = (v:number) => 198 - ((v/scale-minY)/(maxY-minY || 1))*155;
  const path = points.map((p,i)=>`${i ? "L":"M"}${x(p.step).toFixed(2)},${y(p.value).toFixed(2)}`).join(" ");
  return <section className="panel metric-panel" data-testid={`metric-${metric}`}><div className="flex justify-between gap-4"><div><h2><span style={{background:color}} className="chart-dot"/>{metric}</h2><div className="metric-value" data-testid={`latest-${metric}`}>{number(latest.value)}</div></div><span className="badge">STEP {number(latest.step)}</span></div>
    <div className="chart-wrap"><svg viewBox="0 0 550 240" role="img" aria-label={`${metric} by step`} data-testid={`chart-${metric}`} onMouseLeave={()=>setHover(null)}>
      {[0,1,2,3].map(i=><g key={i}><line x1="56" x2="524" y1={43+i*155/3} y2={43+i*155/3} stroke="#29303c" strokeDasharray="3 4"/><text x="46" y={47+i*155/3} textAnchor="end">{number((maxY-i*(maxY-minY)/3)*scale)}</text></g>)}
      {[minX,(minX+maxX)/2,maxX].map((v,i)=><text key={i} x={x(v)} y="218" textAnchor="middle">{number(v)}</text>)}<text x="524" y="238" textAnchor="end">Step</text>
      <path d={path} fill="none" stroke={color} strokeWidth="2" strokeLinejoin="round"/>
      {points.map(p=><circle key={p.seq} cx={x(p.step)} cy={y(p.value)} r={points.length<80?3:1.5} fill={color} data-seq={p.seq} data-step={p.step} data-value={p.value} onMouseEnter={()=>setHover(p)}><title>{`Step ${p.step} · ${p.value} · seq ${p.seq}`}</title></circle>)}
    </svg>{hover && <div className="chart-tooltip">Step {hover.step} · {number(hover.value)} <span className="muted">seq {hover.seq}</span></div>}
    {!points.length && <div className="chart-empty">Recovering persisted history…</div>}</div>
    <div className="chart-caption"><span>Logical step · equal-step values use latest committed event</span><span>{points.length} points</span></div></section>;
}
