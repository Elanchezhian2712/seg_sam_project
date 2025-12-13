from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as DefaultUserAdmin

from segmentation.models import (
    Project,
    Dataset,
    Image,
    SegmentationTask,
    Batch,
    BatchImage,
    ProjectEmployeeMapping,
)

User = get_user_model()

# Register User model
admin.site.register(User, DefaultUserAdmin)

# Register segmentation models
admin.site.register(Project)
admin.site.register(Dataset)
admin.site.register(Image)
admin.site.register(SegmentationTask)
admin.site.register(Batch)
admin.site.register(BatchImage)
admin.site.register(ProjectEmployeeMapping)
