"""
Diagram Evaluation Module
=========================
Uses Gemini LLM to evaluate the semantic JSON of a diagram.
Awards bonus marks (0-2) for including a correct, relevant diagram.
"""

import json
from google.genai import types

from schema import DiagramBonus
from prompts import DIAGRAM_BONUS_PROMPT
from pipeline.retry import gemini_retry

@gemini_retry
def calculate_diagram_bonus(client, question: str, diagram_json: dict) -> dict:
    """
    Calculate bonus marks for including a diagram based purely on its semantic JSON.
    Diagrams are OPTIONAL — this awards 0-2 extra marks, never penalizes.
    
    Args:
        client: Gemini API client
        question: The question being answered
        diagram_json: The semantic representation extracted by the multimodal pipeline
    
    Returns:
        dict: Parsed DiagramBonus data
    """
    filled_prompt = DIAGRAM_BONUS_PROMPT.format(question=question)
    
    evaluation_input = f"""
STUDENT'S DIAGRAM DATA (Extracted Semantics):
{json.dumps(diagram_json, indent=2)}

Please evaluate the diagram based on this semantic structure.
"""
    
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[
            filled_prompt,
            evaluation_input
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
