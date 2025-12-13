from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from segmentation.models import Project, Dataset
from segmentation.services.batch_upload import process_batch_upload
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from segmentation.api.auth import CsrfExemptSessionAuthentication
from rest_framework.authentication import BasicAuthentication


@method_decorator(csrf_exempt, name='dispatch')
class AdminBatchUploadAPIView(APIView):
    """
    Admin API to upload image ZIP and trigger batch processing
    """
    authentication_classes = (
        CsrfExemptSessionAuthentication,
        BasicAuthentication,
    )

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        try:
            project_id = request.data.get('project_id')
            zip_file = request.FILES.get('zip_file')
            priority = request.data.get('priority', 'MEDIUM')

            if not all([project_id, zip_file]):
                return Response(
                    {"error": "project_id, dataset_id and zip_file are required"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            project = Project.objects.get(id=project_id)

            result = process_batch_upload(
                zip_file=zip_file,
                project=project,
                uploaded_by=request.user,
                priority=priority
            )

            return Response(result, status=status.HTTP_200_OK)

        except Project.DoesNotExist:
            return Response(
                {"error": "Invalid project"},
                status=status.HTTP_404_NOT_FOUND
            )

        except Dataset.DoesNotExist:
            return Response(
                {"error": "Invalid dataset"},
                status=status.HTTP_404_NOT_FOUND
            )

        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
