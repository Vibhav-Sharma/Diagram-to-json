import os
import io
import json
import base64
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from PIL import Image

from google import genai

# Pipeline imports
from pipeline.extraction import extract_full_page
from pipeline.theory_eval import evaluate_theory
from pipeline.diagram_eval import calculate_diagram_bonus
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

def crop_region_by_bbox(image: Image.Image, box_2d: list) -> Image.Image:
    """Crop an image using a normalized [ymin, xmin, ymax, xmax] box (0-1000)."""
    w, h = image.size
    ymin, xmin, ymax, xmax = box_2d
    # Convert from 0-1000 scale to absolute pixels
    abs_xmin = int(xmin * w / 1000)
    abs_ymin = int(ymin * h / 1000)
    abs_xmax = int(xmax * w / 1000)
    abs_ymax = int(ymax * h / 1000)
    
    # Ensure within bounds
    abs_xmin = max(0, abs_xmin)
    abs_ymin = max(0, abs_ymin)
    abs_xmax = min(w, abs_xmax)
    abs_ymax = min(h, abs_ymax)
    
    return image.crop((abs_xmin, abs_ymin, abs_xmax, abs_ymax))

# ============================================================
# ENDPOINT — Hybrid Semantic Full Page Evaluation
# ============================================================

@app.post("/evaluate")
async def evaluate_answer(
    file: UploadFile = File(...),
    question: str = Form(default=""),
    auto_extract_question: bool = Form(default=False),
    max_marks: int = Form(default=10)
):
    """
    Hybrid Semantic Full-Page Evaluation Pipeline.
    
    Pipeline:
    1. Single Multimodal Extraction Call (or load from local Cache)
    2. Local Cropping and Data Prep
    3. (Optional) Text-based Theory Evaluation
    4. (Optional) Text-based Diagram Bonus Evaluation
    5. Score Fusion
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
    
    # ── Step 1: ONE-PASS SEMANTIC EXTRACTION ──────────────────────────────
    print("[Pipeline] Step 1: Full Page Semantic Extraction...")
    try:
        extraction_data = extract_full_page(client, pil_image)
    except Exception as e:
        print(f"[Pipeline] Extraction failed: {e}")
        raise HTTPException(status_code=500, detail=f"Semantic extraction failed: {str(e)}")

    # Handle Question Extraction
    if auto_extract_question and not question.strip():
        question = extraction_data.get("question_text", "")
    
    if not question.strip():
        raise HTTPException(
            status_code=400, 
            detail="No question provided or detected. Please type the question."
        )

    # Prepare response structure based on the new extraction output
    pipeline_result = {
        "question": question,
        "extraction_status": "loaded_from_cache" if extraction_data.get("from_cache") else "api_call",
        "segmentation": {
            "regions": extraction_data.get("diagram_regions", []),
            "has_diagram": extraction_data.get("has_diagram", False),
            "has_theory_text": extraction_data.get("has_theory_text", False),
            "page_summary": extraction_data.get("page_summary", "")
        },
        "crops": {},
        "ocr_text": {
            "theory_text": extraction_data.get("theory_text", ""),
            "diagram_labels": extraction_data.get("diagram_labels", [])
        },
        "diagram_json": extraction_data.get("diagram_json"),
        "evaluation": {
            "theory": None,
            "diagram_bonus": None,
            "score_fusion": None
        }
    }

    # ── Step 2: Local Cropping for UI Visuals ──────────────────────────────
    print("[Pipeline] Step 2: Local region cropping...")
    regions = pipeline_result["segmentation"]["regions"]
    has_diagram = pipeline_result["segmentation"]["has_diagram"]
    student_text = pipeline_result["ocr_text"]["theory_text"]

    # Simple local cropping based on returned bounding boxes
    diagram_boxes = [r for r in regions if r.get("region_type") == "diagram"]
    if diagram_boxes:
        diagram_crop = crop_region_by_bbox(pil_image, diagram_boxes[0].get("box_2d"))
        pipeline_result["crops"]["diagram_crop"] = image_to_base64(diagram_crop)

    theory_boxes = [r for r in regions if r.get("region_type") == "theory_text"]
    if theory_boxes:
        theory_crop = crop_region_by_bbox(pil_image, theory_boxes[0].get("box_2d"))
        pipeline_result["crops"]["theory_crop"] = image_to_base64(theory_crop)

    # ── Step 3: Text-based Theory Evaluation ──────────────────────────────
    theory_eval_data = None
    if student_text.strip():
        print("[Pipeline] Step 3: Theory evaluation (Text LLM)...")
        try:
            theory_eval_data = evaluate_theory(client, question, student_text, max_marks=max_marks)
            pipeline_result["evaluation"]["theory"] = theory_eval_data
        except Exception as e:
            print(f"[Pipeline] Theory evaluation failed: {e}")
            from pipeline.retry import make_eval_failure
            theory_eval_data = make_eval_failure("gemini_service_error", e)
            pipeline_result["evaluation"]["theory"] = theory_eval_data
    else:
        print("[Pipeline] Step 3: Skipped — no theory text extracted")
        theory_eval_data = {
            "score": 0,
            "max_score": max_marks,
            "key_points": [],
            "strengths": [],
            "weaknesses": ["No theory text was detected in the answer."],
            "overall_feedback": "No written answer was detected on the page.",
            "confidence": "low",
            "status": "success"
        }
        pipeline_result["evaluation"]["theory"] = theory_eval_data

    # ── Step 4: Text-based Diagram Evaluation ──────────────────────────────
    diagram_bonus_data = None
    diagram_json = pipeline_result["diagram_json"]
    
    if has_diagram and diagram_json:
        print("[Pipeline] Step 4: Diagram evaluation (Text LLM)...")
        try:
            diagram_bonus_data = calculate_diagram_bonus(client, question, diagram_json)
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

    # ── Step 5: Score Fusion ──────────────────────────────────────────────
    print("[Pipeline] Step 5: Score fusion...")
    theory_score = theory_eval_data.get("score", 0) if theory_eval_data else 0
    bonus = diagram_bonus_data.get("bonus_awarded", 0) if diagram_bonus_data else 0
    max_bonus = diagram_bonus_data.get("max_bonus", 2) if diagram_bonus_data else 2
    
    fusion_result = combine_scores(theory_score, max_marks, bonus, max_bonus)
    pipeline_result["evaluation"]["score_fusion"] = fusion_result

    print("[Pipeline] Success. Returning final response.")
    return pipeline_result

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
