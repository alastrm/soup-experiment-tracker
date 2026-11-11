"""Ephemeral local TCP relay: real upstream bytes, intentional frame cut/gate."""
import asyncio
import httpx
from starlette.responses import Response, StreamingResponse


class FrameRelay:
    def __init__(self,upstream,run,*,cut_seq=None,hold_seq=None):
        self.upstream,self.run=upstream,run
        self.cut_seq,self.hold_seq=cut_seq,hold_seq
        self.gate=asyncio.Event();self.waiting=asyncio.Event();self.cursors=[];self.calls=0

    async def __call__(self,scope,receive,send):
        headers={"Access-Control-Allow-Origin":"http://localhost:3000","Access-Control-Allow-Headers":"Authorization, Last-Event-ID, Accept",
            "Access-Control-Allow-Methods":"GET, OPTIONS","Cache-Control":"no-store"}
        if scope["method"]=="OPTIONS":
            return await Response(status_code=200,headers=headers)(scope,receive,send)
        auth=dict(scope["headers"]).get(b"authorization",b"").decode()
        cursor=dict(scope["headers"]).get(b"last-event-id",b"0").decode()
        self.cursors.append(cursor);self.calls+=1;call=self.calls
        async def body():
            if self.cut_seq is not None and call>1:
                self.waiting.set();await self.gate.wait()
            async with httpx.AsyncClient(timeout=None) as client:
                async with client.stream("GET",self.upstream+scope["path"],headers={"Authorization":auth,"Last-Event-ID":cursor}) as response:
                    if response.status_code!=200: return
                    frame=[]
                    async for line in response.aiter_lines():
                        frame.append(line)
                        if line: continue
                        raw=("\n".join(frame)+"\n").encode();frame=[]
                        if scope["path"]==f"/runs/{self.run}/events":
                            if self.cut_seq is not None and call==1 and f"id: {self.cut_seq}\n".encode() in raw:
                                yield raw[:-9]  # Genuine upstream JSON frame, cut before terminator.
                                return
                            if self.hold_seq is not None and f"id: {self.hold_seq}\n".encode() in raw:
                                self.waiting.set();await self.gate.wait()
                        yield raw
        await StreamingResponse(body(),media_type="text/event-stream",headers=headers)(scope,receive,send)


async def route_streams_through(page,port):
    await page.add_init_script(f"""
      (()=>{{const original=window.fetch.bind(window);window.fetch=(input,options)=>{{
        if(typeof input==='string' && new URL(input,location.href).pathname.endsWith('/events')){{
          const url=new URL(input);url.hostname='127.0.0.1';url.port='{port}';return original(url.toString(),options);
        }}return original(input,options);
      }};}})();
    """)
