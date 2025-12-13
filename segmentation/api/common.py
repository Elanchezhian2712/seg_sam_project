from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from segmentation.models import Project, Dataset


class ProjectListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        projects = Project.objects.filter(status='ACTIVE')
        return Response([
            {"id": p.id, "name": p.name}
            for p in projects
        ])


class DatasetListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, project_id):
        datasets = Dataset.objects.filter(
            project_id=project_id,
            status='ACTIVE'
        )
        return Response([
            {"id": d.id, "name": d.name}
            for d in datasets
        ])
