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
from PIL import Image, ImageColor
from io import BytesIO
import base64

app = FastAPI()

# Enable CORS for all
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/ping")
def ping():
    return {"status": "ok"}

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
        # Handle logo
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

        # Generate QR
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=size,
            border=border,
        )
        qr.add_data(text)
        qr.make(fit=True)

        # Style
        if style == "rounded":
            module_drawer = RoundedModuleDrawer()
        elif style == "circle":
            module_drawer = CircleModuleDrawer()
        else:
            module_drawer = SquareModuleDrawer()

        # Convert colors
        try:
            fill_rgb = ImageColor.getrgb(fill_color)
            back_rgb = ImageColor.getrgb(back_color)
        except ValueError:
            return JSONResponse({"error": "Invalid color format"}, status_code=400)

        # Gradient
        color_mask = None
        if gradient == "radial":
            color_mask = RadialGradiantColorMask(
                back_color=back_rgb,
                center_color=fill_rgb,
                edge_color=fill_rgb
            )
        elif gradient == "square":
            color_mask = SquareGradiantColorMask(
                back_color=back_rgb,
                center_color=fill_rgb,
                edge_color=fill_rgb
            )

        # Create image
        img = qr.make_image(
            image_factory=StyledPilImage,
            module_drawer=module_drawer,
            color_mask=color_mask,
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
