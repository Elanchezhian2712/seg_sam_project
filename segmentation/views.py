from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from segmentation.models import SegmentationTask

@login_required
def admin_batch_upload_page(request):
    """
    Render admin batch upload page
    """
    return render(request, 'admin/batch_upload.html')


@login_required
def my_tasks_view(request):
    return render(request, 'segmenter/my_tasks.html')


@login_required
def task_detail_view(request, task_id):
    return render(request, 'segmenter/task_detail.html')


@login_required
def qa_tool_view(request, task_id):
    task = get_object_or_404(SegmentationTask, id=task_id)
    return render(request, 'segmenter/qa_tool.html', {'task': task})