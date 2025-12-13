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

from django.conf import settings
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from segmentation.models import SegmentationTask
from segmentation.utils.media import media_path_to_url

class TaskDetailAPIView(APIView):
    """
    View a task details
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, task_id):
        # NOTE: For QA, we remove 'assigned_to=request.user' filter 
        # because the QA person is NOT the person assigned to the task.
        task = get_object_or_404(SegmentationTask, id=task_id)

        # 1. Handle permissions (Optional: Ensure user is allowed to view)
        # if request.user != task.assigned_to and not request.user.is_staff:
        #     return Response({"error": "Unauthorized"}, status=403)

        # 2. Logic to convert System Path (C:\...) to Web URL (/media/...)
        mask_url = None
        if task.mask_path:
            # If path contains the system MEDIA_ROOT, replace it with MEDIA_URL
            if settings.MEDIA_ROOT in task.mask_path:
                rel_path = task.mask_path.replace(settings.MEDIA_ROOT, "")
                # Fix Windows slashes to Web slashes
                mask_url = settings.MEDIA_URL.rstrip('/') + rel_path.replace("\\", "/")
            else:
                # Fallback if logic matches your media_path_to_url utility
                mask_url = media_path_to_url(task.mask_path)

        # 3. Return the response WITH the mask_path
        return Response({
            "task_id": task.id,
            "assigned_to": task.assigned_to.username if task.assigned_to else "Unassigned",
            "image_name": task.image.file_name,
            "image_path": media_path_to_url(task.image.file_path),
            "mask_path": mask_url,  # <--- THIS WAS MISSING
            "status": task.status,
            "priority": task.priority,
            "start_time": task.start_time,
            "feedback": task.feedback # Send feedback if it exists
        })