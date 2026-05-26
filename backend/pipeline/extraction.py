"""
Extraction Pipeline Module
==========================
Handles the single Gemini VLM call to extract ALL semantic information
from the handwritten answer sheet image (question, theory text, diagram regions,
labels, annotations, connectors, and structural JSON).

Implements a local JSON cache to prevent redundant API calls for the same image.
"""

import os
import json
import hashlib
from io import BytesIO
from PIL import Image
from google.genai import types

from schema import FullExtractionResult
from prompts import FULL_PAGE_EXTRACTION_PROMPT
from pipeline.retry import gemini_retry

CACHE_DIR = os.path.join(os.path.dirname(__file__), "..", "cache")
os.makedirs(CACHE_DIR, exist_ok=True)

def _hash_image(image: Image.Image) -> str:
    """Compute a SHA-256 hash of the image to use as a cache key."""
    # Convert image to bytes to hash it
    buffer = BytesIO()
    # Use a lossless format for consistent hashing of the current pixel data
    image.save(buffer, format="PNG")
    img_bytes = buffer.getvalue()
    return hashlib.sha256(img_bytes).hexdigest()

def get_cached_extraction(image: Image.Image) -> dict:
    """Retrieve extraction results from local cache if they exist."""
    img_hash = _hash_image(image)
    cache_path = os.path.join(CACHE_DIR, f"{img_hash}.json")
    
    if os.path.exists(cache_path):
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            print(f"[Extraction Cache] Hit for {img_hash}")
            return data
        except Exception as e:
            print(f"[Extraction Cache] Failed to load cache: {e}")
    
    print(f"[Extraction Cache] Miss for {img_hash}")
    return None

def save_cached_extraction(image: Image.Image, data: dict):
    """Save extraction results to local cache."""
    img_hash = _hash_image(image)
    cache_path = os.path.join(CACHE_DIR, f"{img_hash}.json")
    
    try:
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        print(f"[Extraction Cache] Saved for {img_hash}")
    except Exception as e:
        print(f"[Extraction Cache] Failed to save cache: {e}")

@gemini_retry
def extract_full_page(client, image: Image.Image) -> dict:
    """
    Perform a single multimodal Gemini API call to extract all semantic data
    from the answer sheet.
    
    Args:
        client: Gemini API client
        image: PIL Image of the full answer sheet
    
    Returns:
        dict: Parsed FullExtractionResult data
    """
    # Check cache first
    cached_data = get_cached_extraction(image)
    if cached_data:
        return cached_data
        
    print("[Pipeline] Executing ONE-PASS Gemini Semantic Extraction...")
    
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[
            image,
            FULL_PAGE_EXTRACTION_PROMPT
        ],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=FullExtractionResult,
            temperature=0.2
        )
    )
    
    if not response.text:
        raise ValueError("Empty response from Gemini during full page extraction")
    
    data = json.loads(response.text)
    
    # Save to cache
    save_cached_extraction(image, data)
    
    return data
