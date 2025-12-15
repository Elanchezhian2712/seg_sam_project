from django.utils import timezone
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from segmentation.models import SegmentationTask
from segmentation.utils.media import media_path_to_url
import json
import os
from django.shortcuts import get_object_or_404


class MyTasksAPIView(APIView):
    """
    Returns tasks assigned to the logged-in segmenter
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        tasks = SegmentationTask.objects.filter(
            assigned_to=request.user,
            status__in=['ASSIGNED', 'IN_PROGRESS', 'QC_REVIEW']
        ).select_related('image').order_by('-created_at')

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


class TaskDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, task_id):
        task = get_object_or_404(SegmentationTask, id=task_id)

        # Correct authorization
        if task.assigned_to != request.user and task.segmenter != request.user:
            return Response(
                {"detail": "You are not allowed to access this task"},
                status=403
            )

        # Restart work if rejected
        if task.status == 'QC_REVIEW':
            task.start_time = timezone.now()
            task.end_time = None
            task.total_duration = None
            task.status = 'IN_PROGRESS'
            task.save(update_fields=[
                'start_time',
                'end_time',
                'total_duration',
                'status',
                'updated_at'
            ])


        elif task.status == 'ASSIGNED' and task.start_time is None:
            task.start_time = timezone.now()
            task.status = 'IN_PROGRESS'
            task.save(update_fields=['start_time', 'status', 'updated_at'])

        mask_url = media_path_to_url(task.mask_path) if task.mask_path else None

        metadata_content = {}
        if task.metadata_path and os.path.exists(task.metadata_path):
            try:
                with open(task.metadata_path, 'r') as f:
                    metadata_content = json.load(f)
            except Exception:
                pass

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
