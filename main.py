from fastapi import FastAPI, Query
from fastapi.responses import FileResponse
import qrcode, hashlib, os, uuid
import yt_dlp
from gtts import gTTS

app = FastAPI()

# -------- QR Code Generator ----------
@app.get("/generate_qr")
async def generate_qr(link: str = Query(...)):
    filename = hashlib.md5(link.encode()).hexdigest() + ".png"
    qrcode.make(link).save(filename)
    return FileResponse(
        filename,
        media_type="image/png",
        filename="qrcode.png",
        background=lambda: os.remove(filename)
    )

# -------- YouTube Video Downloader ----------
@app.get("/download_video")
async def download_video(url: str = Query(...)):
    vid_id = str(uuid.uuid4())
    filename = f"{vid_id}.mp4"
    options = {
        'format': 'best',
        'outtmpl': filename,
        'quiet': True,
    }

    try:
        with yt_dlp.YoutubeDL(options) as ydl:
            ydl.download([url])
        return FileResponse(
            filename,
            media_type='video/mp4',
            filename='video.mp4',
            background=lambda: os.remove(filename)
        )
    except Exception as e:
        return {"error": str(e)}

# -------- Text-to-Speech (TTS) ----------
@app.get("/text_to_speech")
async def text_to_speech(text: str = Query(...)):
    tts_id = str(uuid.uuid4())
    filename = f"{tts_id}.mp3"
    try:
        tts = gTTS(text)
        tts.save(filename)
        return FileResponse(
            filename,
            media_type='audio/mpeg',
            filename='tts.mp3',
            background=lambda: os.remove(filename)
        )
    except Exception as e:
        return {"error": str(e)}
