import base64
import json  # <--- Added
import os
from django.conf import settings
from django.utils import timezone
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from segmentation.models import SegmentationTask


class SaveMaskAPIView(APIView):
    """
    Saves the Mask (PNG) and Metadata (JSON).
    Keeps status as IN_PROGRESS.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, task_id):
        task = get_object_or_404(
            SegmentationTask,
            id=task_id,
            assigned_to=request.user
        )

        mask_data = request.data.get("mask")
        metadata_data = request.data.get("metadata", {}) # <--- Get metadata

        if not mask_data:
            return Response({"error": "Mask data missing"}, status=400)

        # 1. Decode Mask
        try:
            header, encoded = mask_data.split(",", 1)
            mask_bytes = base64.b64decode(encoded)
        except ValueError:
            return Response({"error": "Invalid mask data format"}, status=400)

        # 2. Prepare Paths
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

        # 3. Save Mask Image
        mask_path = os.path.join(task_dir, 'mask.png')
        with open(mask_path, 'wb') as f:
            f.write(mask_bytes)

        # 4. Save Metadata JSON  <--- NEW LOGIC
        metadata_path = os.path.join(task_dir, 'metadata.json')
        with open(metadata_path, 'w') as f:
            json.dump(metadata_data, f, indent=4)

        # 5. Update Database
        task.mask_path = mask_path
        task.metadata_path = metadata_path  # <--- Save path to DB
        task.status = 'IN_PROGRESS'
        task.updated_at = timezone.now()
        
        task.save(update_fields=['mask_path', 'metadata_path', 'status', 'updated_at'])

        return Response({
            "message": "Progress saved successfully",
            "mask_path": mask_path
        })


class SubmitTaskAPIView(APIView):
    """
    Finalizes the task.
    Sets status to SUBMITTED, calculates End Time and Duration.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, task_id):
        task = get_object_or_404(
            SegmentationTask,
            id=task_id,
            assigned_to=request.user
        )

        # Ensure a mask exists before submitting
        if not task.mask_path:
            return Response(
                {"error": "Please save the mask before submitting."},
                status=400
            )

        # 1. Set End Time
        now = timezone.now()
        task.end_time = now
        task.status = 'SUBMITTED'

        # 2. Calculate Duration
        if task.start_time:
            task.total_duration = now - task.start_time
        
        # 3. Save
        task.save(update_fields=['status', 'end_time', 'total_duration'])

        return Response({
            "message": "Task submitted successfully",
        })