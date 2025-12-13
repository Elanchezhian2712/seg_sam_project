import cv2
import numpy as np
import base64
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from segmentation.models import SegmentationTask
from segmentation.ai.sam import predictor


class AIPreSegmentationAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, task_id):
        task = get_object_or_404(
            SegmentationTask,
            id=task_id,
            assigned_to=request.user
        )

        # Load image
        image = cv2.imread(task.image.file_path)
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        # 🔥 REQUIRED STEP (THIS WAS MISSING)
        predictor.set_image(image)

        # Use full-image box prompt
        h, w, _ = image.shape
        input_box = np.array([0, 0, w, h])

        masks, scores, _ = predictor.predict(
            box=input_box,
            multimask_output=False
        )

        mask = masks[0].astype(np.uint8) * 255

        # Encode mask to base64 PNG
        _, buffer = cv2.imencode(".png", mask)
        mask_base64 = base64.b64encode(buffer).decode("utf-8")

        return Response({
            "mask": f"data:image/png;base64,{mask_base64}"
        })
