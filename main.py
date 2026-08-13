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

@app.post("/collage")
async def create_collage(req: CollageRequest):
    if not req.urls:
        raise HTTPException(status_code=400, detail="No se enviaron URLs")
    
    images = []
    # 1. Descargar todas las imágenes de forma asíncrona
    async with httpx.AsyncClient() as client:
        for url in req.urls:
            try:
                response = await client.get(url)
                response.raise_for_status()
                img = Image.open(BytesIO(response.content)).convert("RGB")
                # Forzar un tamaño cuadrado de 600x600 recortando el centro para que se vea estético
                img = ImageOps.fit(img, (600, 600), Image.Resampling.LANCZOS)
                images.append(img)
            except Exception as e:
                print(f"Error descargando imagen: {e}")
                continue

    if not images:
        raise HTTPException(status_code=400, detail="No se pudieron descargar las imágenes")

    # Si solo hay una foto, devolverla tal cual
    if len(images) == 1:
        img_byte_arr = BytesIO()
        images[0].save(img_byte_arr, format='JPEG', quality=85)
        return Response(content=img_byte_arr.getvalue(), media_type="image/jpeg")

    # 2. Calcular la cuadrícula (Grid)
    cols = math.ceil(math.sqrt(len(images)))
    rows = math.ceil(len(images) / cols)
    
    w, h = 600, 600
    collage_width = cols * w
    collage_height = rows * h
    
    # 3. Crear el lienzo en blanco
    collage = Image.new('RGB', (collage_width, collage_height), (255, 255, 255))
    
    # 4. Pegar las imágenes en la cuadrícula
    for idx, img in enumerate(images):
        x = (idx % cols) * w
        y = (idx // cols) * h
        collage.paste(img, (x, y))

    # 5. Exportar y devolver
    img_byte_arr = BytesIO()
    collage.save(img_byte_arr, format='JPEG', quality=85)
    
    return Response(content=img_byte_arr.getvalue(), media_type="image/jpeg")