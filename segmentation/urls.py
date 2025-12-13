from segmentation.api.segmenter_task import SubmitTaskAPIView, SaveMaskAPIView
from django.urls import path
from segmentation.api.admin import AdminBatchUploadAPIView
from segmentation.api.common import ProjectListAPIView, DatasetListAPIView
from segmentation.views import admin_batch_upload_page
from segmentation.api.segmenter import MyTasksAPIView
from segmentation.views import my_tasks_view, task_detail_view
from segmentation.api.segmenter import TaskDetailAPIView
from segmentation.api.ai import AIPreSegmentationAPIView
from segmentation.api.qa import QADecisionAPIView
from segmentation.views import qa_tool_view 

from segmentation.api.qa import QADecisionAPIView, QADashboardAPIView 
from segmentation.views import qa_tool_view, qa_dashboard_view  

urlpatterns = [
    # Admin batch upload
    path(
        'api/admin/batch-upload/',
        AdminBatchUploadAPIView.as_view(),
        name='admin-batch-upload'
    ),

    # Project & Dataset APIs
    path(
        'api/projects/',
        ProjectListAPIView.as_view(),
        name='project-list'
    ),
    path(
        'api/projects/<int:project_id>/datasets/',
        DatasetListAPIView.as_view(),
        name='dataset-list'
    ),

    path(
        'ops/batch-upload/',
        admin_batch_upload_page,
        name='admin-batch-upload-page'
    ),

    path('api/segmenter/my-tasks/', MyTasksAPIView.as_view()),

    path('segmenter/my-tasks/', my_tasks_view, name='my-tasks'),

    path(
        'api/segmenter/task/<int:task_id>/',
        TaskDetailAPIView.as_view(),
        name='task-detail-api'
    ),

    path(
        'segmenter/task/<int:task_id>/',
        task_detail_view,
        name='segmenter-task-detail'
    ),

    path(
        'api/segmenter/task/<int:task_id>/save-mask/',
        SaveMaskAPIView.as_view(),
        name='save-mask'
    ),


    path(
        'api/segmenter/task/<int:task_id>/submit/',
        SubmitTaskAPIView.as_view(),
        name='submit-task'
    ),

    path(
        "api/ai/presegment/<int:task_id>/",
        AIPreSegmentationAPIView.as_view(),
        name="ai-presegment"
    ),


    path('api/qa/task/<int:task_id>/decision/', QADecisionAPIView.as_view(), name='qa_decision'),
    path('qa/task/<int:task_id>/', qa_tool_view, name='qa_tool_page'),

    path('api/qa/dashboard/', QADashboardAPIView.as_view(), name='qa-dashboard-api'),

    path('qa/dashboard/', qa_dashboard_view, name='qa-dashboard-page'),
]
