from django.conf import settings
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from segmentation.models import SegmentationTask
from segmentation.utils.media import media_path_to_url


class MyTasksAPIView(APIView):
    """
    Returns tasks assigned to the logged-in segmenter
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        tasks = SegmentationTask.objects.filter(
            assigned_to=request.user,
            status__in=['ASSIGNED', 'IN_PROGRESS']
        ).select_related('image').order_by('priority', 'created_at')

        data = []
        for task in tasks:
            data.append({
                "task_id": task.id,
                "image_name": task.image.file_name,
                "image_path": media_path_to_url(task.image.file_path),
                "status": task.status,
                "priority": task.priority,
                "created_at": task.created_at
            })

        return Response(data)

import json
import os
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from segmentation.models import SegmentationTask
from segmentation.utils.media import media_path_to_url

class TaskDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, task_id):
        task = get_object_or_404(SegmentationTask, id=task_id)

        # 1. Convert System Path to URL
        mask_url = None
        if task.mask_path:
            if settings.MEDIA_ROOT in task.mask_path:
                rel_path = task.mask_path.replace(settings.MEDIA_ROOT, "")
                mask_url = settings.MEDIA_URL.rstrip('/') + rel_path.replace("\\", "/")
            else:
                mask_url = media_path_to_url(task.mask_path)

        # 2. READ EXISTING METADATA JSON (The Fix)
        metadata_content = {}
        if task.metadata_path and os.path.exists(task.metadata_path):
            try:
                with open(task.metadata_path, 'r') as f:
                    metadata_content = json.load(f)
            except Exception:
                metadata_content = {}

        return Response({
            "task_id": task.id,
            "assigned_to": task.assigned_to.username if task.assigned_to else "Unassigned",
            "image_name": task.image.file_name,
            "image_path": media_path_to_url(task.image.file_path),
            "mask_path": mask_url,
            "metadata": metadata_content, 
            "status": task.status,
            "priority": task.priority,
            "start_time": task.start_time,
            "feedback": task.feedback
        })