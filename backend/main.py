import os
import io
import base64
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from PIL import Image, ImageDraw
from google import genai
from google.genai import types

from schema import DiagramAnalysis

load_dotenv()

app = FastAPI(title="Diagram Parser API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp", "image/jpg"}

client = None
try:
    api_key = os.getenv("GEMINI_API_KEY")
    if api_key:
        client = genai.Client(api_key=api_key)
except Exception as e:
    print(f"Error initializing Gemini Client: {e}")

@app.post("/analyze")
async def analyze_diagram(file: UploadFile = File(...)):
    if not client:
        raise HTTPException(status_code=500, detail="Gemini API Key is missing or invalid. Set GEMINI_API_KEY environment variable.")

    media_type = file.content_type
    if media_type == "image/jpg":
        media_type = "image/jpeg"
    if media_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {file.content_type}. Use JPEG, PNG, or WebP.")

    image_bytes = await file.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Empty file")

    pil_image = Image.open(io.BytesIO(image_bytes))

    prompt = """
You are an expert multimodal diagram understanding system.
Analyze the provided hand-drawn educational diagram and decompose it into semantic components.

Identify the overall diagram type and provide a summary.
Extract the main "structures" (the core geometric or conceptual components, like a cell body, a heart outline, a flowchart node, etc.).
For each structure, you must provide its bounding box `box_2d` in the format [ymin, xmin, ymax, xmax] scaled to 0-1000.

Also extract:
- labels: standalone text pointing to something.
- annotations: explanatory text or sentences describing parts of the diagram.
- connectors: arrows or lines that link structures together.
    """

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[
                pil_image,
                prompt
            ],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=DiagramAnalysis,
                temperature=0.2
            )
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gemini API call failed: {str(e)}")

    if not response.text:
        raise HTTPException(status_code=500, detail="Empty response from Gemini")

    # The response is JSON conforming to DiagramAnalysis schema
    parsed_json = response.text

    import json
    try:
        diagram_data = json.loads(parsed_json)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to parse JSON from Gemini")

    # Generate Visualization Overlay
    vis_image = pil_image.copy().convert("RGBA")
    draw = ImageDraw.Draw(vis_image, "RGBA")
    width, height = vis_image.size

    for struct in diagram_data.get("structures", []):
        box_2d = struct.get("box_2d")
        if box_2d and len(box_2d) == 4:
            ymin, xmin, ymax, xmax = box_2d
            
            # Scale coordinates from 0-1000 to image dimensions
            y1 = (ymin / 1000) * height
            x1 = (xmin / 1000) * width
            y2 = (ymax / 1000) * height
            x2 = (xmax / 1000) * width

            # Draw semi-transparent fill and border
            draw.rectangle([x1, y1, x2, y2], fill=(0, 255, 0, 40), outline=(0, 255, 0, 255), width=3)
            
            # Draw label
            struct_name = struct.get("name", "")
            draw.text((x1 + 5, y1 + 5), struct_name, fill=(0, 255, 0, 255))

    # Convert visualization to base64
    buffered = io.BytesIO()
    vis_image.convert("RGB").save(buffered, format="JPEG", quality=85)
    vis_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")
    
    return {
        "diagram_json": diagram_data,
        "visualization_image": f"data:image/jpeg;base64,{vis_base64}"
    }

@app.get("/health")
def health():
    return {"status": "ok"}
