import base64
import json
import os
from django.conf import settings
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from segmentation.models import SegmentationTask, TaskReview
from segmentation.utils.media import media_path_to_url


class QADashboardAPIView(APIView):
    """
    Returns a list of tasks waiting for QA (Status = SUBMITTED)
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        tasks = SegmentationTask.objects.filter(
            status='QA_REVIEW'
        ).select_related('image', 'assigned_to').order_by('-priority', 'updated_at')

        data = []
        for task in tasks:
            data.append({
                "task_id": task.id,
                "image_name": task.image.file_name,
                "image_path": media_path_to_url(task.image.file_path),
                "priority": task.priority,
                "status": task.status,
                "assigned_to": task.assigned_to.username if task.assigned_to else "Unknown",
                "submitted_at": task.updated_at
            })

        return Response(data)


class QADecisionAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, task_id):
        task = get_object_or_404(SegmentationTask, id=task_id)

        # 1. EXTRACT DATA
        action = request.data.get('action') # 'approve', 'reject', or 'save'
        comments = request.data.get('comments', '')
        mask_data = request.data.get('mask')
        new_metadata = request.data.get('metadata', {})
        qa_start_time_str = request.data.get('qa_start_time')

        if not mask_data:
            return Response({"error": "Mask data missing"}, status=400)

        # ---------------------------------------------------
        # 2. SAVE THE MASK (Images are overwritten)
        # ---------------------------------------------------
        try:
            header, encoded = mask_data.split(",", 1)
            mask_bytes = base64.b64decode(encoded)
        except ValueError:
            return Response({"error": "Invalid mask data format"}, status=400)

        image = task.image
        dataset = image.dataset
        project = dataset.project

        task_dir = os.path.join(
            settings.MEDIA_ROOT, 'projects', project.code, 
            'datasets', dataset.code, 'annotations', f'task_{task.id}'
        )
        os.makedirs(task_dir, exist_ok=True)

        mask_filename = 'mask.png'
        mask_path = os.path.join(task_dir, mask_filename)
        with open(mask_path, 'wb') as f:
            f.write(mask_bytes)

        # ---------------------------------------------------
        # 3. MERGE JSON LOGIC (Read existing -> Update -> Write)
        # ---------------------------------------------------
        metadata_path = os.path.join(task_dir, 'metadata.json')
        final_json_data = {}

        # A. Read existing
        if os.path.exists(metadata_path):
            try:
                with open(metadata_path, 'r') as f:
                    final_json_data = json.load(f)
            except Exception:
                final_json_data = {}

        # B. Prepare updates
        incoming_meta = new_metadata.get('meta', {})
        incoming_shapes = new_metadata.get('shapes', [])

        incoming_meta['saved_mask_path'] = mask_path
        incoming_meta['modified_by'] = request.user.username
        incoming_meta['last_action'] = action
        incoming_meta['timestamp'] = timezone.now().isoformat()

        # C. Merge
        if 'meta' not in final_json_data: final_json_data['meta'] = {}
        final_json_data['meta'].update(incoming_meta)
        final_json_data['shapes'] = incoming_shapes # Shapes are overwritten by the canvas state

        # D. Write
        with open(metadata_path, 'w') as f:
            json.dump(final_json_data, f, indent=4)

        # ---------------------------------------------------
        # 4. UPDATE TASK OBJECT
        # ---------------------------------------------------
        task.mask_path = mask_path
        task.metadata_path = metadata_path
        task.updated_at = timezone.now()

        # Handle 'Save Draft' (No review record needed)
        if action == 'save':
            task.save(update_fields=['mask_path', 'metadata_path', 'updated_at'])
            return Response({"message": "QA Draft Saved Successfully"})

        # ---------------------------------------------------
        # 5. HANDLE TIME & DECISION
        # ---------------------------------------------------
        start_time = None
        end_time = timezone.now()
        duration = None

        if qa_start_time_str:
            try:
                start_time = parse_datetime(qa_start_time_str)
                if start_time:
                    duration = end_time - start_time
            except Exception:
                pass

        decision_enum = ''
        
        if action == 'approve':
            decision_enum = 'APPROVED'
            task.status = 'COMPLETED'
            task.feedback = "" 
            task.end_time = end_time 
            
        elif action == 'reject':
            decision_enum = 'REJECT_EDIT'
            task.status = 'QC_REVIEW'
            task.feedback = comments
            # Do NOT set task.end_time because it needs to be redone

        task.save(update_fields=['status', 'feedback', 'mask_path', 'metadata_path', 'updated_at', 'end_time'])

        # Create Review Record
        TaskReview.objects.create(
            task=task,
            reviewer=request.user,
            review_type='QA',
            decision=decision_enum,
            comments=comments,
            start_time=start_time,
            end_time=end_time,
            duration=duration
        )

        return Response({
            "message": f"Task {action}ed successfully.",
            "status": task.status
        })