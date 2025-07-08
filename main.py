from fastapi import FastAPI, Query
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.background import BackgroundTask

import qrcode
import hashlib
import os
import uuid
import yt_dlp
from gtts import gTTS

app = FastAPI()

# Enable CORS for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/ping")
def ping():
    return {"status": "ok"}

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

# -------- YouTube Downloader ----------
@app.get("/download_video")
async def download_video(url: str = Query(...), quality: str = Query("best")):
    vid_id = str(uuid.uuid4())
    filename = ""
    
    # Add browser-like headers to avoid restrictions
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }

    if quality == "audio":
        filename = f"{vid_id}.mp3"
        ydl_opts = {
            "format": "bestaudio/best",
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }],
            "outtmpl": filename,
            "http_headers": headers,
        }
    elif quality == "720p":
        filename = f"{vid_id}.mp4"
        ydl_opts = {
            "format": "bestvideo[height<=720]+bestaudio/best",
            "merge_output_format": "mp4",
            "outtmpl": filename,
            "http_headers": headers,
        }
    elif quality == "480p":
        filename = f"{vid_id}.mp4"
        ydl_opts = {
            "format": "bestvideo[height<=480]+bestaudio/best",
            "merge_output_format": "mp4",
            "outtmpl": filename,
            "http_headers": headers,
        }
    else:
        filename = f"{vid_id}.mp4"
        ydl_opts = {
            "format": "best",
            "outtmpl": filename,
            "http_headers": headers,
        }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.params["socket_timeout"] = 60  # increase timeout
            ydl.download([url])

        return FileResponse(
            filename,
            media_type="audio/mpeg" if quality == "audio" else "video/mp4",
            filename=f"youtube_video.{filename.split('.')[-1]}",
            background=BackgroundTask(os.remove, filename)
        )
    except Exception as e:
        error_msg = str(e)
        if "login" in error_msg.lower() or "cookies" in error_msg.lower():
            return JSONResponse(
                {"error": "❌ This video requires login (age-restricted or private). We can't download it without authentication."},
                status_code=403
            )
        return JSONResponse({"error": f"Download failed: {error_msg}"}, status_code=500)

# -------- Text-to-Speech (TTS) ----------
@app.get("/text_to_speech")
async def text_to_speech(text: str = Query(...), format: str = Query("mp3")):
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
        return JSONResponse({"error": str(e)}, status_code=500)
