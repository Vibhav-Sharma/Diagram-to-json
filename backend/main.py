import os
import io
import json
import base64
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from PIL import Image, ImageDraw
from google import genai
from google.genai import types

from schema import DiagramAnalysis
from prompts import DIAGRAM_EXTRACTION_PROMPT
from localization import localize_structures

# Pipeline imports
from pipeline.segmentation import segment_page, crop_region, merge_regions
from pipeline.ocr import extract_text, extract_question
from pipeline.theory_eval import evaluate_theory
from pipeline.diagram_eval import evaluate_diagram, calculate_diagram_bonus
from pipeline.score_fusion import combine_scores

load_dotenv(override=True)

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


def image_to_base64(image: Image.Image, format: str = "PNG") -> str:
    """Convert a PIL Image to a base64-encoded data URI string."""
    buffered = io.BytesIO()
    image.save(buffered, format=format)
    encoded = base64.b64encode(buffered.getvalue()).decode("utf-8")
    mime = "image/png" if format == "PNG" else "image/jpeg"
    return f"data:{mime};base64,{encoded}"


# ============================================================
# NEW ENDPOINT — Full Page Subjective Answer Evaluation
# ============================================================

@app.post("/evaluate")
async def evaluate_answer(
    file: UploadFile = File(...),
    question: str = Form(default=""),
    auto_extract_question: bool = Form(default=False),
    max_marks: int = Form(default=10)
):
    """
    Full-page subjective answer evaluation pipeline.
    
    Pipeline:
    1. Page Segmentation (Gemini VLM) — detect regions
    2. Crop regions from original image
    3. OCR extraction on theory text crop
    4. (Optional) Auto-extract question from image
    5. Theory evaluation (Gemini LLM)
    6. (If diagram present) Diagram evaluation + bonus calculation
    7. Score fusion
    """
    if not client:
        raise HTTPException(status_code=500, detail="Gemini API Key is missing or invalid.")

    media_type = file.content_type
    if media_type == "image/jpg":
        media_type = "image/jpeg"
    if media_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail="Unsupported file type.")

    image_bytes = await file.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Empty file")

    pil_image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    
    # Track all pipeline results for explainability
    pipeline_result = {
        "question": question,
        "segmentation": None,
        "crops": {},
        "ocr_text": None,
        "diagram_json": None,
        "evaluation": {
            "theory": None,
            "diagram_bonus": None,
            "score_fusion": None
        }
    }

    # ── Step 1: Page Segmentation ──────────────────────────────
    print("[Pipeline] Step 1: Page Segmentation...")
    try:
        segmentation_data = segment_page(client, pil_image)
        pipeline_result["segmentation"] = segmentation_data
    except Exception as e:
        print(f"[Pipeline] Segmentation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Page segmentation failed: {str(e)}")

    regions = segmentation_data.get("regions", [])
    has_diagram = segmentation_data.get("has_diagram", False)
    has_text = segmentation_data.get("has_theory_text", False)

    # ── Step 2: Crop Regions ───────────────────────────────────
    print("[Pipeline] Step 2: Cropping regions...")
    
    theory_crop = merge_regions(pil_image, regions, "theory_text")
    diagram_crop = merge_regions(pil_image, regions, "diagram")
    
    # Convert crops to base64 for frontend visualization
    if theory_crop:
        pipeline_result["crops"]["theory_crop"] = image_to_base64(theory_crop)
    if diagram_crop:
        pipeline_result["crops"]["diagram_crop"] = image_to_base64(diagram_crop)
    
    # Collect label and connector regions for visualization
    label_regions = [r for r in regions if r.get("region_type") == "diagram_label"]
    connector_regions = [r for r in regions if r.get("region_type") == "connector"]
    pipeline_result["crops"]["label_regions"] = label_regions
    pipeline_result["crops"]["connector_regions"] = connector_regions

    # ── Step 3: Question Extraction (if needed) ────────────────
    if auto_extract_question and not question.strip():
        print("[Pipeline] Step 3: Auto-extracting question...")
        try:
            # Try to use question region if detected, else use full page
            question_crop = merge_regions(pil_image, regions, "question_text")
            source_image = question_crop if question_crop else pil_image
            
            q_result = extract_question(client, source_image)
            question = q_result.get("question_text", "")
            pipeline_result["question"] = question
            pipeline_result["extracted_question"] = q_result
        except Exception as e:
            print(f"[Pipeline] Question extraction failed: {e}")
    
    if not question.strip():
        raise HTTPException(
            status_code=400, 
            detail="No question provided. Please type the question or enable auto-extraction."
        )

    # ── Step 4: OCR Text Extraction ────────────────────────────
    ocr_data = {"theory_text": "", "diagram_labels": []}
    
    if theory_crop:
        print("[Pipeline] Step 4: OCR extraction on theory text...")
        try:
            ocr_data = extract_text(client, theory_crop)
            pipeline_result["ocr_text"] = ocr_data
        except Exception as e:
            print(f"[Pipeline] OCR failed: {e}")
            pipeline_result["ocr_text"] = {"theory_text": "", "diagram_labels": [], "error": str(e)}
    elif not has_diagram:
        # No text region detected and no diagram — try OCR on full page
        print("[Pipeline] Step 4: No text region detected, trying full page OCR...")
        try:
            ocr_data = extract_text(client, pil_image)
            pipeline_result["ocr_text"] = ocr_data
        except Exception as e:
            print(f"[Pipeline] Full page OCR failed: {e}")

    student_text = ocr_data.get("theory_text", "")

    # ── Step 5: Theory Evaluation ──────────────────────────────
    theory_eval_data = None
    if student_text.strip():
        print("[Pipeline] Step 5: Theory evaluation...")
        try:
            theory_eval_data = evaluate_theory(client, question, student_text, max_marks=max_marks)
            pipeline_result["evaluation"]["theory"] = theory_eval_data
        except Exception as e:
            print(f"[Pipeline] Theory evaluation failed: {e}")
            pipeline_result["evaluation"]["theory"] = {"error": str(e)}
    else:
        print("[Pipeline] Step 5: Skipped — no theory text extracted")
        theory_eval_data = {
            "score": 0,
            "max_score": max_marks,
            "key_points": [],
            "strengths": [],
            "weaknesses": ["No theory text was detected in the answer."],
            "overall_feedback": "No written answer was detected on the page.",
            "confidence": "low"
        }
        pipeline_result["evaluation"]["theory"] = theory_eval_data

    # ── Step 6: Diagram Evaluation (if diagram present) ────────
    diagram_json = None
    diagram_bonus_data = None
    
    if has_diagram and diagram_crop:
        print("[Pipeline] Step 6: Diagram evaluation + bonus...")
        
        # Full semantic decomposition
        try:
            diagram_json = evaluate_diagram(client, question, diagram_crop)
            pipeline_result["diagram_json"] = diagram_json
        except Exception as e:
            print(f"[Pipeline] Diagram evaluation failed: {e}")
            pipeline_result["diagram_json"] = {"error": str(e)}
        
        # Bonus calculation
        try:
            diagram_bonus_data = calculate_diagram_bonus(client, question, diagram_crop)
            pipeline_result["evaluation"]["diagram_bonus"] = diagram_bonus_data
        except Exception as e:
            print(f"[Pipeline] Diagram bonus calculation failed: {e}")
            diagram_bonus_data = {
                "bonus_awarded": 0,
                "max_bonus": 2,
                "diagram_present": True,
                "diagram_quality": None,
                "feedback": [f"Bonus calculation failed: {str(e)}"]
            }
            pipeline_result["evaluation"]["diagram_bonus"] = diagram_bonus_data
        
        # GroundingDINO localization for diagram structure overlays
        if diagram_json and "structures" in diagram_json:
            structure_names = [s.get("name") for s in diagram_json.get("structures", []) if s.get("name")]
            if structure_names:
                print(f"[Pipeline] Localizing diagram structures: {structure_names}")
                try:
                    bounding_boxes = localize_structures(diagram_crop, structure_names)
                    for struct in diagram_json.get("structures", []):
                        struct_name = struct.get("name")
                        if struct_name in bounding_boxes:
                            xmin, ymin, xmax, ymax = bounding_boxes[struct_name]
                            w, h = diagram_crop.size
                            struct["box_2d"] = [
                                int((ymin / h) * 1000),
                                int((xmin / w) * 1000),
                                int((ymax / h) * 1000),
                                int((xmax / w) * 1000)
                            ]
                except Exception as e:
                    print(f"[Pipeline] GroundingDINO localization failed: {e}")
        
        # Generate diagram overlay visualization
        if diagram_json and diagram_crop:
            vis_overlay = _generate_diagram_overlay(diagram_crop, diagram_json)
            pipeline_result["crops"]["diagram_overlay"] = image_to_base64(vis_overlay)
    else:
        print("[Pipeline] Step 6: Skipped — no diagram detected")

    # ── Step 7: Score Fusion ───────────────────────────────────
    print("[Pipeline] Step 7: Score fusion...")
    
    theory_score = theory_eval_data.get("score", 0) if theory_eval_data else 0
    bonus = diagram_bonus_data.get("bonus_awarded", 0) if diagram_bonus_data else 0
    
    fusion_data = combine_scores(
        theory_score=theory_score,
        max_theory=max_marks,
        diagram_bonus=bonus,
        max_bonus=2,
        has_diagram=has_diagram
    )
    pipeline_result["evaluation"]["score_fusion"] = fusion_data

    print(f"[Pipeline] ✅ Complete — {fusion_data['summary']}")
    
    return pipeline_result


def _generate_diagram_overlay(diagram_image: Image.Image, diagram_data: dict) -> Image.Image:
    """Generate a transparent overlay with bounding boxes for diagram structures."""
    overlay = Image.new('RGBA', diagram_image.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(overlay)
    
    colors = [
        (255, 99, 132),   # Red/Pink
        (54, 162, 235),   # Blue
        (255, 206, 86),   # Yellow
        (75, 192, 192),   # Teal
        (153, 102, 255),  # Purple
        (255, 159, 64)    # Orange
    ]

    for idx, struct in enumerate(diagram_data.get("structures", [])):
        if not struct.get("box_2d"):
            continue
            
        ymin_n, xmin_n, ymax_n, xmax_n = struct["box_2d"]
        w, h = diagram_image.size
        
        xmin = int((xmin_n / 1000) * w)
        ymin = int((ymin_n / 1000) * h)
        xmax = int((xmax_n / 1000) * w)
        ymax = int((ymax_n / 1000) * h)
        
        r, g, b = colors[idx % len(colors)]
        fill_color = (r, g, b, 70)
        outline_color = (r, g, b, 200)
        
        draw.rounded_rectangle(
            [xmin, ymin, xmax, ymax],
            radius=8,
            fill=fill_color,
            outline=outline_color,
            width=2
        )
    
    return overlay


# ============================================================
# LEGACY ENDPOINT — Diagram-Only Analysis (backward compat)
# ============================================================

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
            
            width, height = vis_image.size
            struct["box_2d"] = [
                int((ymin / height) * 1000),
                int((xmin / width) * 1000),
                int((ymax / height) * 1000),
                int((xmax / width) * 1000)
            ]

            r, g, b = colors[idx % len(colors)]
            fill_color = (r, g, b, 70)
            outline_color = (r, g, b, 200)
            
            draw.rounded_rectangle(
                [xmin, ymin, xmax, ymax], 
                radius=8, 
                fill=fill_color, 
                outline=outline_color, 
                width=2
            )

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
