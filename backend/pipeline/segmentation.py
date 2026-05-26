"""
Page Segmentation Module
========================
Uses Gemini VLM to analyze a full answer sheet image and detect distinct regions:
- Theory text areas (full semantic paragraphs)
- Diagram areas
- Diagram labels
- Connectors/arrows
- Question text

IMPORTANT: This module emphasizes SEMANTIC COMPLETENESS over tight localization.
Crops are intentionally generous to preserve handwritten content near boundaries.
"""

import json
from PIL import Image
from google.genai import types

from schema import PageSegmentation
from prompts import PAGE_SEGMENTATION_PROMPT


# ============================================================
# CONFIGURABLE PADDING (in normalized 0-1000 scale)
# ============================================================
# These values control how much extra margin is added around
# detected regions AFTER Gemini returns bounding boxes.
# This is a safety net on top of the prompt-level padding.

PADDING = {
    "theory_text": {"x": 30, "y": 50},   # Generous vertical for handwriting
    "diagram":     {"x": 40, "y": 40},    # Uniform for diagrams + boundary labels
    "diagram_label": {"x": 20, "y": 20},  # Moderate for labels
    "connector":   {"x": 15, "y": 15},    # Minimal for arrows
    "question_text": {"x": 20, "y": 20},  # Moderate for question
    "default":     {"x": 25, "y": 30},    # Fallback
}

# Vertical distance threshold (in 0-1000 scale) for merging
# nearby theory_text regions into one semantic block.
MERGE_VERTICAL_GAP = 80

# Minimum horizontal overlap ratio (0-1) to consider two regions
# as part of the same column/block for merging.
MERGE_HORIZONTAL_OVERLAP = 0.3


def segment_page(client, image: Image.Image) -> dict:
    """
    Analyze a full answer sheet page and return detected regions.
    
    Args:
        client: Gemini API client
        image: PIL Image of the full answer sheet
    
    Returns:
        dict: Parsed PageSegmentation data with post-processed regions
    """
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[
            image,
            PAGE_SEGMENTATION_PROMPT
        ],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=PageSegmentation,
            temperature=0.1  # Low temp for consistent region detection
        )
    )
    
    if not response.text:
        raise ValueError("Empty response from Gemini during page segmentation")
    
    data = json.loads(response.text)
    
    # Post-process: merge fragmented theory_text regions
    data["regions"] = _merge_nearby_text_regions(data.get("regions", []))
    
    # Post-process: apply padding to all regions
    data["regions"] = [_apply_padding(r) for r in data.get("regions", [])]
    
    return data


def _apply_padding(region: dict) -> dict:
    """
    Apply configurable padding to a region's bounding box.
    Ensures handwritten content near boundaries is not clipped.
    """
    region_type = region.get("region_type", "default")
    pad = PADDING.get(region_type, PADDING["default"])
    px, py = pad["x"], pad["y"]
    
    box = region.get("box_2d", [0, 0, 1000, 1000])
    ymin, xmin, ymax, xmax = box
    
    # Expand with padding, clamp to 0-1000
    region["box_2d"] = [
        max(0, ymin - py),
        max(0, xmin - px),
        min(1000, ymax + py),
        min(1000, xmax + px),
    ]
    
    return region


def _merge_nearby_text_regions(regions: list[dict]) -> list[dict]:
    """
    Merge fragmented theory_text regions that are clearly part of the same
    answer paragraph. This prevents the common failure where Gemini returns
    individual lines or small blocks instead of one full answer region.
    
    Merging criteria:
    - Both regions are theory_text
    - Vertical gap between them is small (< MERGE_VERTICAL_GAP)
    - Horizontal overlap is significant (> MERGE_HORIZONTAL_OVERLAP)
    """
    text_regions = [r for r in regions if r.get("region_type") == "theory_text"]
    other_regions = [r for r in regions if r.get("region_type") != "theory_text"]
    
    if len(text_regions) <= 1:
        return regions  # Nothing to merge
    
    # Sort by vertical position (ymin)
    text_regions.sort(key=lambda r: r["box_2d"][0])
    
    merged = [text_regions[0]]
    
    for current in text_regions[1:]:
        last = merged[-1]
        
        if _should_merge(last, current):
            # Merge: expand last region to encompass current
            last["box_2d"] = _union_boxes(last["box_2d"], current["box_2d"])
            last["confidence"] = min(last.get("confidence", 1.0), current.get("confidence", 1.0))
            last["description"] = (last.get("description", "") or "") + " + " + (current.get("description", "") or "")
        else:
            merged.append(current)
    
    return other_regions + merged


def _should_merge(region_a: dict, region_b: dict) -> bool:
    """Check if two theory_text regions should be merged into one."""
    box_a = region_a["box_2d"]  # [ymin, xmin, ymax, xmax]
    box_b = region_b["box_2d"]
    
    # Vertical gap: distance between bottom of A and top of B
    vertical_gap = box_b[0] - box_a[2]  # b.ymin - a.ymax
    
    if vertical_gap > MERGE_VERTICAL_GAP:
        return False  # Too far apart vertically
    
    # If B is above A (overlapping), always merge
    if vertical_gap < 0:
        return True
    
    # Horizontal overlap check
    overlap_left = max(box_a[1], box_b[1])
    overlap_right = min(box_a[3], box_b[3])
    
    if overlap_right <= overlap_left:
        return False  # No horizontal overlap at all
    
    overlap_width = overlap_right - overlap_left
    width_a = box_a[3] - box_a[1]
    width_b = box_b[3] - box_b[1]
    min_width = min(width_a, width_b) if min(width_a, width_b) > 0 else 1
    
    overlap_ratio = overlap_width / min_width
    
    return overlap_ratio >= MERGE_HORIZONTAL_OVERLAP


def _union_boxes(box_a: list[int], box_b: list[int]) -> list[int]:
    """Return the bounding box that encompasses both boxes."""
    return [
        min(box_a[0], box_b[0]),  # ymin
        min(box_a[1], box_b[1]),  # xmin
        max(box_a[2], box_b[2]),  # ymax
        max(box_a[3], box_b[3]),  # xmax
    ]


def crop_region(image: Image.Image, box_2d: list[int]) -> Image.Image:
    """
    Crop a region from the image using normalized 0-1000 scale bounding box.
    
    Args:
        image: PIL Image
        box_2d: [ymin, xmin, ymax, xmax] normalized to 0-1000
    
    Returns:
        PIL Image: Cropped region
    """
    width, height = image.size
    ymin, xmin, ymax, xmax = box_2d
    
    # Convert from 0-1000 normalized to actual pixel coordinates
    left = int((xmin / 1000) * width)
    top = int((ymin / 1000) * height)
    right = int((xmax / 1000) * width)
    bottom = int((ymax / 1000) * height)
    
    # Clamp to image bounds
    left = max(0, min(left, width))
    top = max(0, min(top, height))
    right = max(left + 1, min(right, width))
    bottom = max(top + 1, min(bottom, height))
    
    return image.crop((left, top, right, bottom))


def merge_regions(image: Image.Image, regions: list[dict], region_type: str) -> Image.Image | None:
    """
    Merge multiple regions of the same type into a single crop.
    Finds the bounding box that encompasses all regions of the given type.
    
    Note: Padding has already been applied to individual regions in segment_page(),
    so no additional padding is needed here.
    
    Args:
        image: PIL Image
        regions: List of region dicts from segmentation
        region_type: Type to filter for (e.g., 'theory_text', 'diagram')
    
    Returns:
        PIL Image or None if no regions of that type
    """
    matching = [r for r in regions if r.get("region_type") == region_type]
    
    if not matching:
        return None
    
    if len(matching) == 1:
        return crop_region(image, matching[0]["box_2d"])
    
    # Merge bounding boxes
    all_ymin = min(r["box_2d"][0] for r in matching)
    all_xmin = min(r["box_2d"][1] for r in matching)
    all_ymax = max(r["box_2d"][2] for r in matching)
    all_xmax = max(r["box_2d"][3] for r in matching)
    
    return crop_region(image, [all_ymin, all_xmin, all_ymax, all_xmax])
