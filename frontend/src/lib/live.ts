export type MetricEvent = { event_id: string; metric: string; step: number; value: number; occurred_at: string; seq: number };
export type Run = { id: string; name: string; created_at: string };
export type Snapshot = { run: Run; last_seq: number; event_count: number; metrics: MetricEvent[] };
export type LiveModel = { cursor: number; count: number; high: number; values: Record<string, MetricEvent>; history: MetricEvent[] };
export const HISTORY_LIMIT = 2000;
export function initialModel(snapshot: Snapshot): LiveModel {
  return {cursor: 0, count: snapshot.event_count, high: snapshot.last_seq,
    values: Object.fromEntries(snapshot.metrics.map(e => [e.metric, e])), history: []};
}
export function applyEvent(model: LiveModel, event: MetricEvent): LiveModel {
  if (!Number.isSafeInteger(event.seq) || event.seq <= 0 || !Number.isSafeInteger(event.step) || event.step < 0 ||
      !Number.isFinite(event.value) || Math.abs(event.value)>1e308 || typeof event.metric!=="string" || !/^[A-Za-z][A-Za-z0-9_.-]{0,63}$/.test(event.metric) ||
      typeof event.event_id !== "string" || !/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/.test(event.event_id) ||
      typeof event.occurred_at!=="string" || !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{1,6})?Z$/.test(event.occurred_at) ||
      !(Date.parse(event.occurred_at)>=Date.UTC(2000,0,1) && Date.parse(event.occurred_at)<Date.UTC(2100,0,1)))
    throw new Error("Invalid metric event");
  if (event.seq <= model.cursor) return model;
  if (event.seq !== model.cursor + 1) throw new Error("Sequence gap; recovering from last applied event");
  const values = {...model.values};
  const previous = Object.hasOwn(values,event.metric) ? values[event.metric] : undefined;
  if (!previous || event.step > previous.step || (event.step === previous.step && event.seq > previous.seq)) values[event.metric] = event;
  return {cursor: event.seq, high: Math.max(model.high, event.seq), count: Math.max(model.count, event.seq), values,
    history: [...model.history, event].slice(-HISTORY_LIMIT)};
}
export type Frame = { event: string; id?: string; data: string };
export class SSEParser {
  private pending = "";
  feed(chunk: string): Frame[] {
    this.pending += chunk;
    const frames: Frame[] = [];
    while (true) {
      const match = /\r?\n\r?\n/.exec(this.pending);
      if (!match) break;
      const raw = this.pending.slice(0, match.index);
      this.pending = this.pending.slice(match.index + match[0].length);
      if (new TextEncoder().encode(raw).length > 8192) throw new Error("Stream frame too large");
      let event = "message", id: string | undefined;
      const data: string[] = [];
      for (const line of raw.split(/\r?\n/)) {
        if (line.startsWith(":")) continue;
        const colon = line.indexOf(":");
        const name = colon < 0 ? line : line.slice(0, colon);
        const value = colon < 0 ? "" : line.slice(colon + 1).replace(/^ /, "");
        if (name === "event") event = value;
        if (name === "id") id = value;
        if (name === "data") data.push(value);
      }
      if (data.length) frames.push({event, id, data: data.join("\n")});
    }
    if (new TextEncoder().encode(this.pending).length > 8192) throw new Error("Stream frame too large");
    return frames;
  }
}
export function chartPoints(history: MetricEvent[], metric: string): MetricEvent[] {
  const byStep = new Map<number, MetricEvent>();
  for (const e of history) if (e.metric === metric) {
    const old = byStep.get(e.step);
    if (!old || e.seq > old.seq) byStep.set(e.step, e);
  }
  return [...byStep.values()].sort((a,b) => a.step - b.step);
}
