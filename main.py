from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import httpx
from PIL import Image, ImageOps
from io import BytesIO
import math
from fastapi.responses import Response

app = FastAPI()

class CollageRequest(BaseModel):
    urls: list[str]
    aspect: float | None = None  # ancho/alto del recuadro; recorta al centro para llenarlo

@app.post("/collage")
async def create_collage(req: CollageRequest):
    if not req.urls:
        raise HTTPException(status_code=400, detail="No se enviaron URLs")

    images = []
    async with httpx.AsyncClient() as client:
        for url in req.urls:
            try:
                response = await client.get(url)
                response.raise_for_status()
                img = Image.open(BytesIO(response.content)).convert("RGB")
                img = ImageOps.fit(img, (640, 640), Image.Resampling.LANCZOS)
                images.append(img)
            except Exception as e:
                print(f"Error descargando imagen: {e}")
                continue

    if not images:
        raise HTTPException(status_code=400, detail="No se pudieron descargar las imágenes")

    cols = math.ceil(math.sqrt(len(images)))
    rows = math.ceil(len(images) / cols)

    w, h = 640, 640
    collage = Image.new('RGB', (cols * w, rows * h), (255, 255, 255))

    for idx, img in enumerate(images):
        x = (idx % cols) * w
        y = (idx // cols) * h
        collage.paste(img, (x, y))

    # Recorte al aspecto del recuadro (fill): llena sin distorsión
    if req.aspect and req.aspect > 0:
        W, H = collage.width, collage.height
        if req.aspect >= W / H:
            target = (W, int(W / req.aspect))
        else:
            target = (int(H * req.aspect), H)
        collage = ImageOps.fit(collage, target, Image.Resampling.LANCZOS)

    img_byte_arr = BytesIO()
    collage.save(img_byte_arr, format='JPEG', quality=85)
    return Response(content=img_byte_arr.getvalue(), media_type="image/jpeg")
