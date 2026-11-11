"""Local TCP fault harness, used only by tests (no deployed proxy/service)."""
import asyncio
import socket
from contextlib import asynccontextmanager

import httpx
import uvicorn


def resident_bytes():
    """Current OS resident memory, not a Python-allocation estimate."""
    import os
    if os.name=="nt":
        import ctypes
        from ctypes import wintypes
        class Counters(ctypes.Structure):
            _fields_=[("cb",wintypes.DWORD),("faults",wintypes.DWORD)]+[(name,ctypes.c_size_t) for name in
                ("peak_working","working","peak_paged","paged","peak_nonpaged","nonpaged","pagefile","peak_pagefile")]
        counters=Counters();counters.cb=ctypes.sizeof(counters)
        current=ctypes.windll.kernel32.GetCurrentProcess;current.restype=wintypes.HANDLE
        get=ctypes.windll.psapi.GetProcessMemoryInfo
        get.argtypes=[wintypes.HANDLE,ctypes.POINTER(Counters),wintypes.DWORD]
        if not get(current(),ctypes.byref(counters),counters.cb):raise ctypes.WinError()
        return counters.working
    with open("/proc/self/statm") as statm:
        return int(statm.read().split()[1])*os.sysconf("SC_PAGE_SIZE")


@asynccontextmanager
async def serve(app):
    sock=socket.socket();sock.bind(("127.0.0.1",0));sock.setblocking(False)
    port=sock.getsockname()[1]
    server=uvicorn.Server(uvicorn.Config(app,lifespan="off",log_level="critical",timeout_graceful_shutdown=0.2))
    task=asyncio.create_task(server.serve(sockets=[sock]))
    async with asyncio.timeout(5):
        while not server.started: await asyncio.sleep(0.01)
    try:
        async with httpx.AsyncClient(base_url=f"http://127.0.0.1:{port}",timeout=6) as client:
            yield client,port
    finally:
        server.should_exit=True
        await asyncio.wait_for(task,3)


class DropReceipt:
    """Drop actual HTTP response after route/transaction committed successfully."""
    def __init__(self,app): self.app=app;self.dropped=False
    async def __call__(self,scope,receive,send):
        async def faulty_send(message):
            if not self.dropped and scope.get("path","").endswith("/metrics") and message["type"]=="http.response.start" and message["status"]==200:
                self.dropped=True
                send.__self__.transport.abort()
                raise ConnectionResetError("injected lost committed receipt")
            await send(message)
        await self.app(scope,receive,faulty_send)


class SmallSocketBuffers:
    def __init__(self,app): self.app=app;self.transport=None;self.maximum=0
    async def __call__(self,scope,receive,send):
        if not scope.get("path","").endswith("/events"):return await self.app(scope,receive,send)
        self.transport=send.__self__.transport
        self.transport.set_write_buffer_limits(high=4096,low=1024)
        self.transport.get_extra_info("socket").setsockopt(socket.SOL_SOCKET,socket.SO_SNDBUF,1024)
        async def observe(message):
            await send(message)
            self.maximum=max(self.maximum,self.transport.get_write_buffer_size())
        await self.app(scope,receive,observe)
