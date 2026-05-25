import torch
from transformers import AutoProcessor, AutoModelForZeroShotObjectDetection
from PIL import Image

# Initialize models lazily to avoid heavy loading on startup if not needed immediately
_processor = None
_model = None

def get_grounding_dino():
    global _processor, _model
    if _model is None:
        model_id = "IDEA-Research/grounding-dino-tiny"
        device = "cuda" if torch.cuda.is_available() else "cpu"
        _processor = AutoProcessor.from_pretrained(model_id)
        _model = AutoModelForZeroShotObjectDetection.from_pretrained(model_id).to(device)
    return _processor, _model

def localize_structures(image: Image.Image, structure_names: list[str]) -> dict:
    """
    Takes an image and a list of structure names (e.g. ["left ventricle", "right atrium"]).
    Returns a dictionary mapping structure names to their bounding boxes [xmin, ymin, xmax, ymax].
    """
    if not structure_names:
        return {}

    processor, model = get_grounding_dino()
    device = "cuda" if torch.cuda.is_available() else "cpu"
    
    # GroundingDINO requires text queries to be lowercase and separated by periods
    text_query = ". ".join([name.lower() for name in structure_names]) + "."
    
    inputs = processor(images=image, text=text_query, return_tensors="pt").to(device)
    
    with torch.no_grad():
        outputs = model(**inputs)
        
    # Process outputs
    # We use a lower threshold to ensure we don't miss structures
    results = processor.post_process_grounded_object_detection(
        outputs,
        inputs.input_ids,
        box_threshold=0.25,
        text_threshold=0.25,
        target_sizes=[image.size[::-1]] # (height, width)
    )[0]
    
    # results contains: "boxes", "scores", "labels"
    # Note: grounding dino might match partial words or multiple boxes for a label.
    # We will pick the highest scoring box for each structure name requested.
    
    boxes = results["boxes"].cpu().numpy()
    scores = results["scores"].cpu().numpy()
    labels = results["labels"] # list of strings
    
    best_boxes = {}
    for req_name in structure_names:
        req_lower = req_name.lower()
        best_score = -1.0
        best_box = None
        
        for box, score, label in zip(boxes, scores, labels):
            # If the detected label matches the requested structure (e.g. "left ventricle")
            if req_lower in label or label in req_lower:
                if score > best_score:
                    best_score = score
                    best_box = box.tolist() # [xmin, ymin, xmax, ymax]
                    
        if best_box is not None:
            best_boxes[req_name] = best_box
            
    return best_boxes
