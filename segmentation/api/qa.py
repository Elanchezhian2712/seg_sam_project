from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.utils import timezone
from segmentation.models import SegmentationTask

class QADecisionAPIView(APIView):
    """
    Handles QA Audit: Approve or Reject
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, task_id):
        # 1. Get the task
        task = get_object_or_404(SegmentationTask, id=task_id)

        # 2. Get decision data
        action = request.data.get('action') # 'approve' or 'reject'
        comments = request.data.get('comments', '')

        if action == 'approve':
            task.status = 'COMPLETED'
            task.feedback = "" # Clear previous feedback if any
            task.save(update_fields=['status', 'feedback'])
            return Response({"message": "Task Approved and Completed."})

        elif action == 'reject':
            # Set back to IN_PROGRESS so Segmenter can edit it
            # OR set to REJECTED if you want a specific status
            task.status = 'REJECTED' 
            task.feedback = comments
            task.save(update_fields=['status', 'feedback'])
            return Response({"message": "Task Rejected. Sent back to segmenter."})

        return Response({"error": "Invalid action"}, status=400)