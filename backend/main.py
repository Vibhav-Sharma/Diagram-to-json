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
from prompts import DIAGRAM_EXTRACTION_PROMPT
from localization import localize_structures

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
        raise HTTPException(status_code=500, detail="Gemini API Key is missing or invalid.")

    media_type = file.content_type
    if media_type == "image/jpg":
        media_type = "image/jpeg"
    if media_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail=f"Unsupported file type.")

    image_bytes = await file.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Empty file")

    pil_image = Image.open(io.BytesIO(image_bytes)).convert("RGB")

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[
                pil_image,
                DIAGRAM_EXTRACTION_PROMPT
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

    import json
    try:
        diagram_data = json.loads(response.text)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to parse JSON from Gemini")

    # Step 2: Localization via GroundingDINO
    structure_names = [s.get("name") for s in diagram_data.get("structures", []) if s.get("name")]
    
    print(f"Localizing structures: {structure_names}")
    try:
        bounding_boxes = localize_structures(pil_image, structure_names)
    except Exception as e:
        print(f"Localization failed: {e}")
        bounding_boxes = {}

    # Generate Visualization Overlay
    vis_image = pil_image.copy().convert("RGBA")
    overlay = Image.new('RGBA', vis_image.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(overlay)
    
    colors = [
        (255, 99, 132),  # Red/Pink
        (54, 162, 235),  # Blue
        (255, 206, 86),  # Yellow
        (75, 192, 192),  # Teal
        (153, 102, 255), # Purple
        (255, 159, 64)   # Orange
    ]

    for idx, struct in enumerate(diagram_data.get("structures", [])):
        struct_name = struct.get("name")
        if struct_name in bounding_boxes:
            xmin, ymin, xmax, ymax = bounding_boxes[struct_name]
            
            # Save the box back to the json so the frontend can use it if desired
            # Format: [ymin, xmin, ymax, xmax] normalized to 0-1000 to match old format
            width, height = vis_image.size
            struct["box_2d"] = [
                int((ymin / height) * 1000),
                int((xmin / width) * 1000),
                int((ymax / height) * 1000),
                int((xmax / width) * 1000)
            ]

            # Choose a color
            r, g, b = colors[idx % len(colors)]
            
            # Draw beautiful translucent mask
            # Low opacity fill, solid thin border
            fill_color = (r, g, b, 70)  # 70/255 opacity
            outline_color = (r, g, b, 200)
            
            # Use a slightly rounded rectangle if possible (Pillow 8.2+ supports rounded_rectangle)
            draw.rounded_rectangle(
                [xmin, ymin, xmax, ymax], 
                radius=8, 
                fill=fill_color, 
                outline=outline_color, 
                width=2
            )
            # Labels will be rendered by the frontend using the box_2d coordinates.

    # Convert visualization to base64
    # Instead of compositing, we return ONLY the transparent overlay.
    # This allows the frontend to absolutely position it over the original image and adjust opacity via CSS.
    buffered = io.BytesIO()
    overlay.save(buffered, format="PNG")
    vis_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")
    
    return {
        "diagram_json": diagram_data,
        "visualization_image": f"data:image/png;base64,{vis_base64}"
    }

@app.get("/health")
def health():
    return {"status": "ok"}

