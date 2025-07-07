from fastapi import FastAPI, Query
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.background import BackgroundTask

import qrcode
import hashlib
import os
import uuid
import yt_dlp
from gtts import gTTS

app = FastAPI()

# Enable CORS for all domains (for development)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Replace with specific origins in production
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------- QR Code Generator ----------
@app.get("/generate_qr")
async def generate_qr(link: str = Query(...)):
    filename = hashlib.md5(link.encode()).hexdigest() + ".png"
    qrcode.make(link).save(filename)
    return FileResponse(
        filename,
        media_type="image/png",
        filename="qrcode.png",
        background=BackgroundTask(os.remove, filename)
    )

# -------- YouTube Video Downloader ----------
@app.get("/download_video")
async def download_video(url: str = Query(...), quality: str = Query("best")):
    vid_id = str(uuid.uuid4())
    extension = "mp3" if quality == "audio" else "mp4"
    filename = f"{vid_id}.{extension}"

    # Set yt-dlp format options
    options = {
        'format': 'bestaudio' if quality == "audio" else quality,
        'outtmpl': filename,
        'quiet': True,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192'
        }] if quality == "audio" else []
    }

    try:
        with yt_dlp.YoutubeDL(options) as ydl:
            ydl.download([url])
        return FileResponse(
            filename,
            media_type="audio/mpeg" if quality == "audio" else "video/mp4",
            filename=f"download.{extension}",
            background=BackgroundTask(os.remove, filename)
        )
    except Exception as e:
        return {"error": str(e)}

# -------- Text-to-Speech (TTS) ----------
@app.get("/text_to_speech")
async def text_to_speech(text: str = Query(...), format: str = Query("mp3"), preview: bool = Query(False)):
    tts_id = str(uuid.uuid4())
    filename = f"{tts_id}.{format}"

    try:
        tts = gTTS(text)
        tts.save(filename)
        return FileResponse(
            filename,
            media_type="audio/mpeg" if format == "mp3" else "audio/wav",
            filename=f"tts.{format}",
            background=BackgroundTask(os.remove, filename)
        )
    except Exception as e:
        return {"error": str(e)}
