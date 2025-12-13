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


from django.shortcuts import get_object_or_404
from django.utils import timezone


class TaskDetailAPIView(APIView):
    """
    View a task and mark it as IN_PROGRESS
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, task_id):
        task = get_object_or_404(
            SegmentationTask,
            id=task_id,
            assigned_to=request.user
        )

        # Auto-start task if not already started
        if task.status == 'ASSIGNED':
            task.status = 'IN_PROGRESS'
            task.start_time = timezone.now()
            task.save(update_fields=['status', 'start_time'])

        return Response({
            "task_id": task.id,
            "image_name": task.image.file_name,
            "image_path": media_path_to_url(task.image.file_path),
            "status": task.status,
            "priority": task.priority,
            "start_time": task.start_time
        })
