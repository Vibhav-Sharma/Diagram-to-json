from pydantic import BaseModel, Field
from typing import List, Optional

# ============================================================
# EXISTING DIAGRAM SCHEMAS (kept for backward compatibility)
# ============================================================

class Structure(BaseModel):
    name: str = Field(description="Name of the detected structure (e.g. cell body, heart outline).")
    description: str = Field(description="Brief description of the structure.")
    confidence: float = Field(description="Confidence score between 0.0 and 1.0.")

class Label(BaseModel):
    text: str = Field(description="Extracted text of the label.")
    points_to: str = Field(description="What the label points to.")
    confidence: float = Field(description="Confidence score between 0.0 and 1.0.")

class Annotation(BaseModel):
    text: str = Field(description="Text of the explanatory annotation.")
    meaning: str = Field(description="Meaning or context of the annotation.")
    confidence: float = Field(description="Confidence score between 0.0 and 1.0.")

class Connector(BaseModel):
    from_element: str = Field(alias="from", description="Origin element of the connector.")
    to_element: str = Field(alias="to", description="Destination element of the connector.")
    type: str = Field(description="Type of connector, e.g. arrow or line.")

class RubricScore(BaseModel):
    score: int = Field(description="Score awarded")
    max: int = Field(description="Maximum possible score")
    feedback: List[str] = Field(description="Feedback explaining the score and any deductions")

class RubricScores(BaseModel):
    figure_structure: RubricScore
    labels: RubricScore
    connectors: RubricScore
    annotations: RubricScore

class Evaluation(BaseModel):
    total_score: int
    max_score: int
    rubric_scores: RubricScores
    overall_feedback: List[str]
    confidence: str = Field(description="Confidence level: high/medium/low")

class DiagramAnalysis(BaseModel):
    detected_figure: str = Field(description="Name of the detected figure being evaluated.")
    evaluation: Evaluation = Field(description="Educational evaluation of the diagram.")
    diagram_type: str = Field(description="Type of the diagram.")
    diagram_summary: str = Field(description="Overall summary of what the diagram represents.")
    structures: List[Structure] = Field(default_factory=list, description="Main structures/regions of the diagram.")
    labels: List[Label] = Field(default_factory=list, description="Extracted labels.")
    annotations: List[Annotation] = Field(default_factory=list, description="Explanatory annotations.")
    connectors: List[Connector] = Field(default_factory=list, description="Connectors such as arrows or lines linking components.")


# ============================================================
# NEW SCHEMAS — Full Page Evaluation Pipeline
# ============================================================

# --- Page Segmentation ---

class PageRegion(BaseModel):
    """A detected region on the answer sheet page."""
    region_type: str = Field(description="Type of region: 'theory_text', 'diagram', 'diagram_label', 'connector', 'question_text'")
    box_2d: List[int] = Field(description="Bounding box as [ymin, xmin, ymax, xmax] normalized to 0-1000 scale")
    confidence: float = Field(description="Confidence score between 0.0 and 1.0")
    description: Optional[str] = Field(default=None, description="Brief description of what is in this region")

class PageSegmentation(BaseModel):
    """Result of page-level layout analysis."""
    regions: List[PageRegion] = Field(description="All detected regions on the page")
    has_diagram: bool = Field(description="Whether a diagram was detected on the page")
    has_theory_text: bool = Field(description="Whether theory/explanatory text was detected on the page")
    page_summary: str = Field(description="Brief summary of the page content and layout")


# --- OCR Extraction ---

class OCRResult(BaseModel):
    """Result of OCR text extraction."""
    theory_text: str = Field(description="Extracted theory/explanatory answer text from the student")
    diagram_labels: List[str] = Field(default_factory=list, description="Extracted diagram label texts, separate from theory text")


# --- Theory Evaluation ---

class KeyPoint(BaseModel):
    """A key concept/point expected in the answer."""
    point: str = Field(description="The key concept or point")
    found: bool = Field(description="Whether this point was found in the student's answer")
    student_text: Optional[str] = Field(default=None, description="The student's text that matches this point, if found")

class TheoryEvaluation(BaseModel):
    """Evaluation of the student's theory/text answer."""
    score: int = Field(description="Score awarded for the theory answer")
    max_score: int = Field(description="Maximum possible score (default 10)")
    key_points: List[KeyPoint] = Field(description="Key concepts expected and whether student covered them")
    strengths: List[str] = Field(description="Strengths of the student's answer")
    weaknesses: List[str] = Field(description="Weaknesses or missing elements in the answer")
    overall_feedback: str = Field(description="Overall feedback summary")
    confidence: str = Field(description="Confidence level: high/medium/low")


# --- Diagram Bonus ---

class DiagramBonus(BaseModel):
    """Bonus marks for including a correct diagram (optional, not penalized if absent)."""
    bonus_awarded: int = Field(description="Bonus marks awarded: 0, 1, or 2")
    max_bonus: int = Field(default=2, description="Maximum possible bonus marks")
    diagram_present: bool = Field(description="Whether a diagram was detected")
    diagram_quality: Optional[str] = Field(default=None, description="Quality assessment: excellent/good/partial/poor")
    feedback: List[str] = Field(default_factory=list, description="Feedback on the diagram")


# --- Score Fusion ---

class ScoreFusion(BaseModel):
    """Final combined score with breakdown."""
    theory_score: int = Field(description="Theory answer score (out of max_theory)")
    max_theory: int = Field(description="Maximum theory marks")
    diagram_bonus: int = Field(description="Bonus marks for diagram (0-2)")
    max_bonus: int = Field(default=2, description="Maximum bonus marks")
    final_score: int = Field(description="Final combined score = theory_score + diagram_bonus")
    max_possible: int = Field(description="Maximum possible score = max_theory + max_bonus")
    summary: str = Field(description="Human-readable score summary")


# --- Question Extraction ---

class ExtractedQuestion(BaseModel):
    """Question text extracted from the answer sheet image."""
    question_text: str = Field(description="The extracted question text")
    confidence: float = Field(description="Confidence in the extraction, 0.0-1.0")
