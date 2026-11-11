import {test} from "node:test";
import assert from "node:assert/strict";
import {applyEvent, chartPoints, initialModel, SSEParser, HISTORY_LIMIT} from "../src/lib/live.ts";
const e=(seq:number, step=seq)=>({seq,step,event_id:`00000000-0000-4000-8000-${String(seq).padStart(12,"0")}`,metric:"loss",value:seq,occurred_at:"2026-01-01T00:00:00Z"});
test("snapshot summary + full chart replay, then missing 11–30 and duplicates",()=>{
  let model=initialModel({run:{id:"r",name:"r",created_at:""},last_seq:10,event_count:10,metrics:[e(10)]});
  for(let i=1;i<=10;i++)model=applyEvent(model,e(i));
  assert.equal(model.count,10);assert.equal(model.history.length,10);
  for(let i=11;i<=30;i++)model=applyEvent(model,e(i));
  const same=applyEvent(model,e(30));assert.equal(same,model);
  assert.deepEqual(chartPoints(model.history,"loss").map(p=>p.seq),Array.from({length:30},(_,i)=>i+1));
  assert.throws(()=>applyEvent(model,e(32)),/gap/);assert.equal(model.cursor,30);
  model=applyEvent(model,e(31,1));assert.equal(model.values.loss.seq,30);
  model=applyEvent(model,e(32,30));assert.equal(model.values.loss.seq,32);
});
test("bounded chart history preserves full latest values",()=>{
  let model=initialModel({run:{id:"r",name:"r",created_at:""},last_seq:0,event_count:0,metrics:[]});
  for(let i=1;i<=HISTORY_LIMIT+5;i++)model=applyEvent(model,e(i));
  assert.equal(model.history.length,HISTORY_LIMIT);assert.equal(model.count,HISTORY_LIMIT+5);
});
test("valid metric names cannot collide with inherited object properties",()=>{
  let model=initialModel({run:{id:"r",name:"r",created_at:""},last_seq:0,event_count:0,metrics:[]});
  model=applyEvent(model,{...e(1),metric:"constructor"});
  assert.equal(model.values["constructor"].value,1);
});
test("malformed metric payload never advances applied cursor",()=>{
  const model=initialModel({run:{id:"r",name:"r",created_at:""},last_seq:0,event_count:0,metrics:[]});
  for(const changed of [{metric:undefined},{event_id:"bad"},{occurred_at:"bad"},{value:Infinity}])
    assert.throws(()=>applyEvent(model,{...e(1),...changed} as ReturnType<typeof e>));
  assert.equal(model.cursor,0);
});
test("SSE chunk boundaries, CRLF, comments, joined lines and bounded partial frame",()=>{
  const parser=new SSEParser();assert.deepEqual(parser.feed(": hello\r\n\r\nevent: met"),[]);
  assert.deepEqual(parser.feed("ric\r\nid: 1\r\ndata: {\r\ndata: }\r\n\r\n"),[{event:"metric",id:"1",data:"{\n}"}]);
  assert.deepEqual(parser.feed("event: metric\nid: 2\ndata: partial"),[]);
  assert.throws(()=>parser.feed("x".repeat(9000)),/large/);
});
