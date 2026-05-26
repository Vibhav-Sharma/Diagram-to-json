"""
OCR Extraction Module
=====================
Uses Gemini VLM to extract handwritten text from cropped answer regions.
Separates theory text from diagram labels.
"""

import json
from PIL import Image
from google.genai import types

from schema import OCRResult, ExtractedQuestion
from prompts import OCR_EXTRACTION_PROMPT, QUESTION_EXTRACTION_PROMPT


def extract_text(client, image: Image.Image) -> dict:
    """
    Extract handwritten text from a cropped theory-text region.
    
    Args:
        client: Gemini API client
        image: PIL Image of the cropped text region
    
    Returns:
        dict: Parsed OCRResult data with theory_text and diagram_labels
    """
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[
            image,
            OCR_EXTRACTION_PROMPT
        ],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=OCRResult,
            temperature=0.1  # Low temp for accurate transcription
        )
    )
    
    if not response.text:
        raise ValueError("Empty response from Gemini during OCR extraction")
    
    return json.loads(response.text)


def extract_question(client, image: Image.Image) -> dict:
    """
    Extract question text from the answer sheet image.
    
    Args:
        client: Gemini API client
        image: PIL Image (full page or cropped question region)
    
    Returns:
        dict: Parsed ExtractedQuestion data
    """
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[
            image,
            QUESTION_EXTRACTION_PROMPT
        ],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=ExtractedQuestion,
            temperature=0.1
        )
    )
    
    if not response.text:
        raise ValueError("Empty response from Gemini during question extraction")
    
    return json.loads(response.text)
