import base64
import os
from django.conf import settings
from django.utils import timezone
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from segmentation.models import SegmentationTask


class SaveMaskAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, task_id):
        task = get_object_or_404(
            SegmentationTask,
            id=task_id,
            assigned_to=request.user
        )

        mask_data = request.data.get("mask")
        if not mask_data:
            return Response({"error": "Mask data missing"}, status=400)

        # Decode base64
        header, encoded = mask_data.split(",", 1)
        mask_bytes = base64.b64decode(encoded)

        # Build path
        image = task.image
        dataset = image.dataset
        project = dataset.project

        task_dir = os.path.join(
            settings.MEDIA_ROOT,
            'projects',
            project.code,
            'datasets',
            dataset.code,
            'annotations',
            f'task_{task.id}'
        )

        os.makedirs(task_dir, exist_ok=True)

        mask_path = os.path.join(task_dir, 'mask.png')

        with open(mask_path, 'wb') as f:
            f.write(mask_bytes)

        # Update task
        task.mask_path = mask_path
        task.status = 'IN_PROGRESS'
        task.last_updated = timezone.now()
        task.save(update_fields=['mask_path', 'status', 'last_updated'])

        return Response({
            "message": "Mask saved successfully",
            "mask_path": mask_path
        })



class SubmitTaskAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, task_id):
        task = get_object_or_404(
            SegmentationTask,
            id=task_id,
            assigned_to=request.user
        )

        if not task.mask_path:
            return Response(
                {"error": "Please save mask before submitting"},
                status=400
            )

        task.status = 'SUBMITTED'
        task.completed_at = timezone.now()
        task.save(update_fields=['status', 'completed_at'])

        return Response({
            "message": "Task submitted successfully"
        })
