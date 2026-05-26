"""
Theory Evaluation Module
========================
Uses Gemini LLM to evaluate the student's theory/text answer 
against the question, using a rubric-based scoring system.
"""

import json
from google.genai import types

from schema import TheoryEvaluation
from prompts import THEORY_EVALUATION_PROMPT
from pipeline.retry import gemini_retry


# Default mark distribution for theory evaluation (out of 10)
DEFAULT_MAX_MARKS = 10
DEFAULT_CONCEPT_MARKS = 4
DEFAULT_COMPLETENESS_MARKS = 3
DEFAULT_ACCURACY_MARKS = 2
DEFAULT_CLARITY_MARKS = 1


@gemini_retry
def evaluate_theory(client, question: str, student_text: str, max_marks: int = DEFAULT_MAX_MARKS) -> dict:
    """
    Evaluate a student's theory answer text against the question.
    
    Args:
        client: Gemini API client
        question: The question being answered
        student_text: The student's extracted answer text (from OCR)
        max_marks: Maximum marks for theory (default 10)
    
    Returns:
        dict: Parsed TheoryEvaluation data
    """
    # Calculate sub-rubric marks proportionally
    concept_marks = round(max_marks * 0.4)
    completeness_marks = round(max_marks * 0.3)
    accuracy_marks = round(max_marks * 0.2)
    clarity_marks = max_marks - concept_marks - completeness_marks - accuracy_marks
    
    # Fill in the prompt template with mark values
    filled_prompt = THEORY_EVALUATION_PROMPT.format(
        max_marks=max_marks,
        concept_marks=concept_marks,
        completeness_marks=completeness_marks,
        accuracy_marks=accuracy_marks,
        clarity_marks=clarity_marks
    )
    
    # Build the evaluation input
    evaluation_input = f"""
QUESTION:
{question}

STUDENT'S ANSWER (extracted via OCR from handwritten text):
{student_text}
"""
    
    response = client.models.generate_content(
        model="gemini-2.5-flash", # Upgraded for stability
        contents=[
            filled_prompt,
            evaluation_input
        ],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=TheoryEvaluation,
            temperature=0.2
        )
    )
    
    if not response.text:
        raise ValueError("Empty response from Gemini during theory evaluation")
    
    return json.loads(response.text)
