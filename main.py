from fastapi import FastAPI, Query, UploadFile, File, Form
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.background import BackgroundTask
from typing import Optional
import qrcode
from qrcode.image.styledpil import StyledPilImage
from qrcode.image.styles.moduledrawers import (
    RoundedModuleDrawer, 
    SquareModuleDrawer, 
    CircleModuleDrawer
)
from qrcode.image.styles.colormasks import (
    RadialGradiantColorMask, 
    SquareGradiantColorMask
)
import hashlib
import os
import uuid
import yt_dlp
from gtts import gTTS
from PIL import Image
from io import BytesIO
import base64

app = FastAPI()

# Enable CORS
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

@app.post("/generate_qr_advanced")
async def generate_qr_advanced(
    text: str = Form(...),
    size: int = Form(10),
    border: int = Form(1),
    fill_color: str = Form("black"),
    back_color: str = Form("white"),
    style: str = Form("square"),
    gradient: str = Form("none"),
    logo: UploadFile = File(None)
):
    filename = f"qr_{hashlib.md5(text.encode()).hexdigest()}.png"
    logo_path = None

    try:
        # Handle logo upload
        if logo and logo.filename:
            logo_ext = os.path.splitext(logo.filename)[1].lower()
            if logo_ext not in ['.png', '.jpg', '.jpeg']:
                return JSONResponse(
                    {"error": "Logo must be a PNG or JPG image"},
                    status_code=400
                )
            logo_path = f"temp_logo_{uuid.uuid4().hex}{logo_ext}"
            with open(logo_path, "wb") as buffer:
                buffer.write(await logo.read())
            with Image.open(logo_path) as img:
                img.thumbnail((100, 100))
                img.save(logo_path)

        # Create QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=size,
            border=border,
        )
        qr.add_data(text)
        qr.make(fit=True)

        # Choose module drawer
        if style == "rounded":
            module_drawer = RoundedModuleDrawer()
        elif style == "circle":
            module_drawer = CircleModuleDrawer()
        else:
            module_drawer = SquareModuleDrawer()

        # Handle gradient selection
        color_mask = None
        if gradient == "radial":
            color_mask = RadialGradiantColorMask(
                back_color=back_color,
                center_color=fill_color,
                edge_color=fill_color
            )
        elif gradient == "square":
            color_mask = SquareGradiantColorMask(
                back_color=back_color,
                center_color=fill_color,
                edge_color=fill_color
            )

        # Generate the image
        img = qr.make_image(
            image_factory=StyledPilImage,
            module_drawer=module_drawer,
            color_mask=color_mask,  # Can be None if no gradient
            embeded_image_path=logo_path if logo_path else None
        )

        img.save(filename)
        buffered = BytesIO()
        img.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()

        return {
            "image_url": f"/download_qr/{filename}",
            "image_base64": img_str,
            "filename": filename
        }
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
    finally:
        if logo_path and os.path.exists(logo_path):
            os.remove(logo_path)
            

@app.get("/download_qr/{filename}")
async def download_qr(filename: str):
    if not os.path.exists(filename):
        return JSONResponse({"error": "File not found"}, status_code=404)
    return FileResponse(
        filename,
        media_type="image/png",
        filename="custom_qrcode.png",
        background=BackgroundTask(lambda: os.remove(filename) if os.path.exists(filename) else None)
    )

# -------- YouTube Downloader ----------
@app.get("/download_video")
async def download_video(url: str = Query(...), quality: str = Query("best")):
    vid_id = str(uuid.uuid4())
    filename = ""

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
            ydl.params["socket_timeout"] = 60
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
