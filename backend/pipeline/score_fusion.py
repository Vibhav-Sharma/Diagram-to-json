"""
Score Fusion Module
===================
Combines theory evaluation score with optional diagram bonus marks.

Scoring Philosophy:
- Theory text answer is the PRIMARY evaluation (out of max_marks, default 10)
- Diagram is OPTIONAL BONUS (+0 to +2 marks)
- Not drawing a diagram is NOT penalized
- Final score = theory_score + diagram_bonus
"""


def combine_scores(
    theory_score: int,
    max_theory: int,
    diagram_bonus: int = 0,
    max_bonus: int = 2,
    has_diagram: bool = False
) -> dict:
    """
    Combine theory score with optional diagram bonus.
    
    Args:
        theory_score: Score for the theory/text answer
        max_theory: Maximum theory marks
        diagram_bonus: Bonus marks for diagram (0-2)
        max_bonus: Maximum bonus possible
        has_diagram: Whether a diagram was present
    
    Returns:
        dict: ScoreFusion data
    """
    # Clamp values
    theory_score = max(0, min(theory_score, max_theory))
    diagram_bonus = max(0, min(diagram_bonus, max_bonus)) if has_diagram else 0
    
    final_score = theory_score + diagram_bonus
    max_possible = max_theory + max_bonus
    
    # Build human-readable summary
    if has_diagram and diagram_bonus > 0:
        summary = (
            f"Theory: {theory_score}/{max_theory} | "
            f"Diagram Bonus: +{diagram_bonus}/{max_bonus} | "
            f"Final: {final_score}/{max_possible}"
        )
    elif has_diagram and diagram_bonus == 0:
        summary = (
            f"Theory: {theory_score}/{max_theory} | "
            f"Diagram: present but no bonus awarded | "
            f"Final: {final_score}/{max_possible}"
        )
    else:
        summary = (
            f"Theory: {theory_score}/{max_theory} | "
            f"No diagram drawn (no penalty) | "
            f"Final: {final_score}/{max_possible}"
        )
    
    return {
        "theory_score": theory_score,
        "max_theory": max_theory,
        "diagram_bonus": diagram_bonus,
        "max_bonus": max_bonus,
        "final_score": final_score,
        "max_possible": max_possible,
        "summary": summary
    }
