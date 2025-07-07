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
    
    # Set file extension and yt-dlp options
    if quality == "audio":
        extension = "mp3"
        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
            }],
            'outtmpl': f'{vid_id}.%(ext)s',
        }
    else:
        extension = "mp4"
        ydl_opts = {
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'merge_output_format': 'mp4',
            'outtmpl': f'{vid_id}.%(ext)s',
        }

    try:
        # First validate URL
        with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
            info = ydl.extract_info(url, download=False)
            if not info:
                return JSONResponse({"error": "Invalid URL or video unavailable"}, status_code=400)

        # Then download
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
            
        # Verify file exists and has content
        filename = f"{vid_id}.{extension}"
        if not os.path.exists(filename) or os.path.getsize(filename) == 0:
            raise Exception("Downloaded file is empty")

        # Use streaming response for large files
        def cleanup():
            try:
                if os.path.exists(filename):
                    os.remove(filename)
            except:
                pass

        return StreamingResponse(
            open(filename, "rb"),
            media_type="audio/mpeg" if quality == "audio" else "video/mp4",
            headers={
                "Content-Disposition": f'attachment; filename="{info.get("title", "video")}.{extension}"'
            },
            background=BackgroundTask(cleanup)
        )

    except Exception as e:
        return JSONResponse(
            {"error": f"Download failed: {str(e)}"},
            status_code=500
        )
    
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
