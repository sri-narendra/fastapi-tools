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
    
    # Determine file extension and format options based on quality request
    if quality == "audio":
        extension = "mp3"
        format_options = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        }
    else:
        extension = "mp4"
        if quality == "best":
            format_options = {'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'}
        elif quality == "720p":
            format_options = {'format': 'bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'}
        elif quality == "480p":
            format_options = {'format': 'bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'}
        else:
            format_options = {'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'}

    filename = f"{vid_id}.{extension}"

    options = {
        'outtmpl': filename,
        'quiet': True,
        'no_warnings': True,
        'restrictfilenames': True,
        **format_options
    }

    try:
        with yt_dlp.YoutubeDL(options) as ydl:
            # First validate the URL
            info_dict = ydl.extract_info(url, download=False)
            if not info_dict:
                return {"error": "Could not extract video information"}
            
            # Then download
            ydl.download([url])
            
            if not os.path.exists(filename):
                return {"error": "Download failed - no file created"}

        return FileResponse(
            filename,
            media_type="audio/mpeg" if quality == "audio" else "video/mp4",
            filename=f"{info_dict.get('title', 'download')}.{extension}",
            background=BackgroundTask(os.remove, filename)
        )
    except yt_dlp.utils.DownloadError as e:
        return {"error": f"Download failed: {str(e)}"}
    except yt_dlp.utils.ExtractorError as e:
        return {"error": f"Extraction failed: {str(e)}"}
    except Exception as e:
        return {"error": f"Unexpected error: {str(e)}"}
    
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
