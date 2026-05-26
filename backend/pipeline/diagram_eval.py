"""
Diagram Evaluation Module
=========================
Uses Gemini VLM to evaluate a cropped diagram image.
Awards bonus marks (0-2) for including a correct, relevant diagram.
Also performs semantic decomposition of the diagram.
"""

import json
from PIL import Image
from google.genai import types

from schema import DiagramAnalysis, DiagramBonus
from prompts import DIAGRAM_EXTRACTION_PROMPT, DIAGRAM_BONUS_PROMPT
from pipeline.retry import gemini_retry


@gemini_retry
def evaluate_diagram(client, question: str, diagram_image: Image.Image) -> dict:
    """
    Perform semantic decomposition and evaluation of a diagram.
    Uses the existing diagram evaluation rubric.
    
    Args:
        client: Gemini API client
        question: The question being answered
        diagram_image: PIL Image of the cropped diagram
    
    Returns:
        dict: Parsed DiagramAnalysis data
    """
    context = f"The student is answering: {question}\n\n"
    
    response = client.models.generate_content(
        model="gemini-2.0-flash", # Upgraded
        contents=[
            diagram_image,
            context + DIAGRAM_EXTRACTION_PROMPT
        ],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=DiagramAnalysis,
            temperature=0.2
        )
    )
    
    if not response.text:
        raise ValueError("Empty response from Gemini during diagram evaluation")
    
    return json.loads(response.text)


@gemini_retry
def calculate_diagram_bonus(client, question: str, diagram_image: Image.Image) -> dict:
    """
    Calculate bonus marks for including a diagram.
    Diagrams are OPTIONAL — this awards 0-2 extra marks, never penalizes.
    
    Args:
        client: Gemini API client
        question: The question being answered
        diagram_image: PIL Image of the cropped diagram
    
    Returns:
        dict: Parsed DiagramBonus data
    """
    filled_prompt = DIAGRAM_BONUS_PROMPT.format(question=question)
    
    response = client.models.generate_content(
        model="gemini-2.0-flash", # Upgraded
        contents=[
            diagram_image,
            filled_prompt
        ],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=DiagramBonus,
            temperature=0.2
        )
    )
    
    if not response.text:
        raise ValueError("Empty response from Gemini during diagram bonus calculation")
    
    return json.loads(response.text)
