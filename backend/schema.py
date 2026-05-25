from pydantic import BaseModel, Field
from typing import List, Optional

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
