import torch
import os
from django.conf import settings
from segment_anything import sam_model_registry, SamPredictor

MODEL_TYPE = "vit_b"
SAM_CHECKPOINT = os.path.join(
    settings.BASE_DIR,
    "models",
    "sam_vit_b_01ec64.pth"
)

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

sam = sam_model_registry[MODEL_TYPE](checkpoint=SAM_CHECKPOINT)
sam.to(device=DEVICE)

predictor = SamPredictor(sam)
