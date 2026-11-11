"use client";
import {useEffect, useRef, useState} from "react";
import {chartPoints, type MetricEvent} from "../lib/live";
export const number = (value: number) => value === 0 ? "0" : Math.abs(value) >= 1e5 || Math.abs(value) < 0.001 ? value.toExponential(3) : new Intl.NumberFormat("en", {maximumFractionDigits:4}).format(value);
export function Chart({metric, history, latest, index}: {metric:string; history:MetricEvent[]; latest:MetricEvent; index:number}) {
  const points = chartPoints(history, metric); const [hover, setHover] = useState<MetricEvent | null>(null);
  const container = useRef<HTMLDivElement>(null);
  const [size, setSize] = useState({width:800,height:310});
  useEffect(()=>{
    const observer = new ResizeObserver(([entry])=>setSize({width:entry.contentRect.width,height:entry.contentRect.height}));
    if(container.current)observer.observe(container.current);
    return ()=>observer.disconnect();
  },[]);
  const color = ["#c6cbd8", "#8fa4be", "#b6a48d", "#a99bb8"][index % 4];
  const minX = points[0]?.step ?? 0, maxX = points.at(-1)?.step ?? 1;
  const scale = Math.max(...points.map(p=>Math.abs(p.value)), 1e-300);
  const ys = points.map(p=>p.value/scale), minY = Math.min(...ys,0), maxY = Math.max(...ys,0.01);
  const left=82, right=Math.max(left+1,size.width-18), top=28, bottom=size.height-45;
  const x = (v:number) => maxX===minX ? (left+right)/2 : left + ((v-minX)/(maxX-minX))*(right-left);
  const y = (v:number) => bottom - ((v/scale-minY)/(maxY-minY || 1))*(bottom-top);
  const ticks = [...new Set([minX,Math.round(minX+(maxX-minX)/2),maxX])];
  const path = points.map((p,i)=>`${i ? "L":"M"}${x(p.step).toFixed(2)},${y(p.value).toFixed(2)}`).join(" ");
  return <section className="metric-panel" data-testid={`metric-${metric}`}><div className="metric-heading"><h2>{metric}</h2><div className="metric-current"><div className="metric-value" data-testid={`latest-${metric}`}>{number(latest.value)}</div><span className="metric-step">at step {number(latest.step)}</span></div></div>
    <div className="chart-wrap" ref={container}><svg viewBox={`0 0 ${size.width} ${size.height}`} role="img" aria-label={`${metric} by step`} data-testid={`chart-${metric}`} onMouseLeave={()=>setHover(null)}>
      <text x={left-12} y="13" textAnchor="end">Value</text>
      {[0,1,2,3].map(i=><g key={i}><line x1={left} x2={right} y1={top+i*(bottom-top)/3} y2={top+i*(bottom-top)/3} stroke="#ffffff0c"/><text x={left-12} y={top+4+i*(bottom-top)/3} textAnchor="end">{number((maxY-i*(maxY-minY)/3)*scale)}</text></g>)}
      {ticks.map(v=><text key={v} x={x(v)} y={bottom+22} textAnchor="middle">{number(v)}</text>)}<text x={right} y={size.height-5} textAnchor="end">Step</text>
      <path d={path} fill="none" stroke={color} strokeWidth="1.8" strokeLinejoin="round" vectorEffect="non-scaling-stroke"/>
      {points.map((p,i)=><circle key={p.seq} cx={x(p.step)} cy={y(p.value)} r={points.length<80?3:1.5} fill={color} data-seq={p.seq} data-step={p.step} data-value={p.value} tabIndex={i===points.length-1?0:-1} onFocus={()=>setHover(p)} onBlur={()=>setHover(null)} onMouseEnter={()=>setHover(p)}><title>{`Step ${p.step} · ${p.value} · seq ${p.seq}`}</title></circle>)}
    </svg>{hover && <div className="chart-tooltip">Step {hover.step} · {number(hover.value)} <span className="muted">seq {hover.seq}</span></div>}
    {!points.length && <div className="chart-empty">Recovering persisted history…</div>}</div>
    <div className="chart-caption"><span>By logical step · latest commit at each step</span><span>{points.length} points</span></div></section>;
}
