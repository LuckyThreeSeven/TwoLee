# main.py
import asyncio
import time
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from aiortc import RTCPeerConnection, RTCSessionDescription
from aiortc.contrib.media import MediaRecorder, MediaRelay

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

BASE = Path(__file__).parent
RECS = BASE / "recordings"
RECS.mkdir(exist_ok=True)

relay = MediaRelay()

state = {
    "pc_pub": None,
    "recorder": None,
    "started_evt": None,
    "mp4_path": None,
}

class SDP(BaseModel):
    sdp: str
    type: str  # "offer" or "answer"

@app.post("/publish/offer")
async def publish_offer(s: SDP):
    # 기존 세션/레코더 정리
    if state["pc_pub"] is not None:
        await state["pc_pub"].close()
        state["pc_pub"] = None
    if state["recorder"] is not None:
        try:
            await state["recorder"].stop()
        except Exception:
            pass
        state["recorder"] = None

    pc = RTCPeerConnection()
    started_evt = asyncio.Event()
    state["started_evt"] = started_evt

    ts = int(time.time())
    mp4_path = RECS / f"stream_{ts}.mp4"
    state["mp4_path"] = mp4_path

    # 핵심: MP4로 저장 (코덱 인자 없이, 옵션만 faststart)
    recorder = MediaRecorder(
        str(mp4_path),
        format="mp4",
        options={"movflags": "faststart"},
    )
    state["recorder"] = recorder

    @pc.on("track")
    def on_track(track):
        subscribed = relay.subscribe(track)
        recorder.addTrack(subscribed)

        async def _start_once():
            if not started_evt.is_set():
                await recorder.start()
                started_evt.set()
        asyncio.create_task(_start_once())

    # 서버는 수신 전용
    pc.addTransceiver("video", direction="recvonly")
    pc.addTransceiver("audio", direction="recvonly")

    await pc.setRemoteDescription(RTCSessionDescription(s.sdp, s.type))
    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)

    state["pc_pub"] = pc
    return {"sdp": pc.localDescription.sdp, "type": pc.localDescription.type}

@app.post("/publish/stop")
async def publish_stop():
    # start가 실제로 시작되었는지 잠깐 대기 (moov 보장)
    if state["started_evt"] is not None:
        try:
            await asyncio.wait_for(state["started_evt"].wait(), timeout=2)
        except asyncio.TimeoutError:
            pass

    if state["recorder"] is not None:
        try:
            await state["recorder"].stop()
        except Exception:
            pass
        state["recorder"] = None

    if state["pc_pub"] is not None:
        try:
            await state["pc_pub"].close()
        except Exception:
            pass
        state["pc_pub"] = None

    state["started_evt"] = None
    return {
        "ok": True,
        "mp4": str(state["mp4_path"]) if state["mp4_path"] else None
    }
