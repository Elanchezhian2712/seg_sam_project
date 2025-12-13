import base64
import json
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

        # 3. Save Mask Image (PNG)
        mask_filename = 'mask.png'
        mask_path = os.path.join(task_dir, mask_filename)
        
        with open(mask_path, 'wb') as f:
            f.write(mask_bytes)

        # ---------------------------------------------------------
        # 4. INJECT PATHS INTO METADATA (The Fix)
        # ---------------------------------------------------------
        
        # Ensure 'meta' key exists
        if 'meta' not in metadata_data:
            metadata_data['meta'] = {}

        # Add Absolute System Paths (for internal use)
        metadata_data['meta']['saved_mask_path'] = mask_path
        metadata_data['meta']['source_image_path'] = image.file_path

        # Add Web URLs (for frontend display)
        # Construct relative path: /media/projects/.../mask.png
        relative_mask_path = f"projects/{project.code}/datasets/{dataset.code}/annotations/task_{task.id}/{mask_filename}"
        mask_url = os.path.join(settings.MEDIA_URL, relative_mask_path).replace("\\", "/")
        
        metadata_data['meta']['mask_url'] = mask_url

        # ---------------------------------------------------------
        # 5. Save Metadata (JSON)
        # ---------------------------------------------------------
        metadata_path = os.path.join(task_dir, 'metadata.json')
        with open(metadata_path, 'w') as f:
            json.dump(metadata_data, f, indent=4)

        # 6. Update Database
        task.mask_path = mask_path
        task.metadata_path = metadata_path
        task.status = 'IN_PROGRESS'
        task.updated_at = timezone.now()
        
        task.save(update_fields=['mask_path', 'metadata_path', 'status', 'updated_at'])

        return Response({
            "message": "Progress saved successfully",
            "mask_path": mask_path,
            "metadata_path": metadata_path
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
            return Response({"error": "Please save the mask before submitting."}, status=400)

        now = timezone.now()
        task.end_time = now
        task.status = 'SUBMITTED'

        if task.start_time:
            task.total_duration = now - task.start_time
        
        task.save(update_fields=['status', 'end_time', 'total_duration'])

        return Response({"message": "Task submitted successfully"})