from django.conf import settings
from django.db import models


class Project(models.Model):
    PROJECT_STATUS_CHOICES = [
        ('ACTIVE', 'Active'),
        ('ARCHIVED', 'Archived'),
        ('ON_HOLD', 'On Hold'),
    ]

    name = models.CharField(max_length=255)
    code = models.CharField(
        max_length=50,
        unique=True,
        help_text="Unique project identifier (e.g., project_001)"
    )
    description = models.TextField(null=True, blank=True)

    status = models.CharField(
        max_length=20,
        choices=PROJECT_STATUS_CHOICES,
        default='ACTIVE'
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='created_projects'
    )

    storage_path = models.CharField(
        max_length=500,
        help_text="Root storage path for this project"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.code})"

class Dataset(models.Model):
    DATASET_STATUS_CHOICES = [
        ('ACTIVE', 'Active'),
        ('ARCHIVED', 'Archived'),
    ]

    project = models.ForeignKey(
        'segmentation.Project',
        on_delete=models.CASCADE,
        related_name='datasets'
    )

    name = models.CharField(max_length=255)
    code = models.CharField(
        max_length=100,
        help_text="Dataset identifier (e.g., dataset_001)"
    )
    description = models.TextField(null=True, blank=True)

    status = models.CharField(
        max_length=20,
        choices=DATASET_STATUS_CHOICES,
        default='ACTIVE'
    )

    storage_path = models.CharField(
        max_length=500,
        help_text="Root storage path for this dataset"
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='created_datasets'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('project', 'code')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.project.code} / {self.name}"



class Image(models.Model):
    IMAGE_STATUS_CHOICES = [
        ('UPLOADED', 'Uploaded'),
        ('ASSIGNED', 'Assigned'),
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed'),
        ('ARCHIVED', 'Archived'),
        ('FAILED', 'Failed'),
    ]

    dataset = models.ForeignKey(
        'segmentation.Dataset',
        on_delete=models.CASCADE,
        related_name='images'
    )

    file_name = models.CharField(max_length=255)
    file_path = models.CharField(
        max_length=500,
        help_text="Absolute or relative path to the image file"
    )

    width = models.IntegerField()
    height = models.IntegerField()
    file_size = models.BigIntegerField(help_text="File size in bytes")

    checksum = models.CharField(
        max_length=64,
        help_text="SHA256 checksum for duplicate detection"
    )

    status = models.CharField(
        max_length=20,
        choices=IMAGE_STATUS_CHOICES,
        default='UPLOADED'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['checksum']),
        ]
        unique_together = ('dataset', 'checksum')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.file_name} ({self.dataset.code})"


class SegmentationTask(models.Model):
    TASK_STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('ASSIGNED', 'Assigned'),
        ('IN_PROGRESS', 'In Progress'),
        ('SUBMITTED', 'Submitted'),
        ('COMPLETED', 'Completed'),
        ('REJECTED', 'Rejected'),
    ]

    PRIORITY_CHOICES = [
        ('LOW', 'Low'),
        ('MEDIUM', 'Medium'),
        ('HIGH', 'High'),
        ('URGENT', 'Urgent'),
    ]

    image = models.ForeignKey(
        'segmentation.Image',
        on_delete=models.CASCADE,
        related_name='segmentation_tasks'
    )

    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='segmentation_tasks'
    )

    status = models.CharField(
        max_length=20,
        choices=TASK_STATUS_CHOICES,
        default='PENDING'
    )

    priority = models.CharField(
        max_length=10,
        choices=PRIORITY_CHOICES,
        default='MEDIUM'
    )

    # Time tracking
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)
    total_duration = models.DurationField(null=True, blank=True)

    feedback = models.TextField(
        null=True, 
        blank=True, 
        help_text="QA Feedback regarding rejection"
    )

    # Output paths
    mask_path = models.CharField(
        max_length=500,
        null=True,
        blank=True,
        help_text="Path to final segmentation mask"
    )

    metadata_path = models.CharField(
        max_length=500,
        null=True,
        blank=True,
        help_text="Path to segmentation metadata JSON"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['priority', 'created_at']

    def start_task(self):
        self.status = 'IN_PROGRESS'
        self.start_time = timezone.now()
        self.save(update_fields=['status', 'start_time'])

    def complete_task(self):
        self.status = 'SUBMITTED'
        self.end_time = timezone.now()
        if self.start_time:
            self.total_duration = self.end_time - self.start_time
        self.save(update_fields=['status', 'end_time', 'total_duration'])

    def __str__(self):
        return f"Task #{self.id} - {self.image.file_name}"


from django.conf import settings
from django.db import models


class ProjectEmployeeMapping(models.Model):
    ROLE_CHOICES = [
        ('SEGMENTER', 'Segmenter'),
        ('QC', 'Quality Control'),
        ('QA', 'Quality Assurance'),
    ]

    project = models.ForeignKey(
        'segmentation.Project',
        on_delete=models.CASCADE,
        related_name='employee_mappings'
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='project_mappings'
    )

    role_in_project = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES
    )

    capacity = models.PositiveIntegerField(
        default=10,
        help_text="Maximum active tasks allowed"
    )

    current_workload = models.PositiveIntegerField(
        default=0,
        help_text="Current active tasks count"
    )

    is_available = models.BooleanField(default=True)

    start_date = models.DateTimeField()
    end_date = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('project', 'user')
        ordering = ['project', 'role_in_project', 'current_workload']

    def capacity_percentage(self):
        if self.capacity == 0:
            return 100
        return round((self.current_workload / self.capacity) * 100, 2)

    def is_fully_occupied(self):
        return self.current_workload >= self.capacity

    def available_slots(self):
        return max(self.capacity - self.current_workload, 0)

    def __str__(self):
        return f"{self.user.username} @ {self.project.code} ({self.role_in_project})"



class Batch(models.Model):
    BATCH_STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('PROCESSING', 'Processing'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
    ]

    project = models.ForeignKey(
        'segmentation.Project',
        on_delete=models.CASCADE,
        related_name='batches'
    )

    dataset = models.ForeignKey(
        'segmentation.Dataset',
        on_delete=models.CASCADE,
        related_name='batches'
    )

    batch_id = models.CharField(
        max_length=100,
        unique=True,
        help_text="e.g. upload_20240115_143022"
    )

    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='uploaded_batches'
    )

    original_zip_path = models.CharField(max_length=500)

    total_images = models.PositiveIntegerField()

    status = models.CharField(
        max_length=20,
        choices=BATCH_STATUS_CHOICES,
        default='PENDING'
    )

    images_extracted = models.PositiveIntegerField(default=0)
    images_failed = models.PositiveIntegerField(default=0)

    total_tasks_created = models.PositiveIntegerField(default=0)
    assigned_tasks = models.PositiveIntegerField(default=0)
    unassigned_tasks = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def completion_percentage(self):
        if self.total_images == 0:
            return 0
        return round((self.images_extracted / self.total_images) * 100, 2)

    def __str__(self):
        return self.batch_id


class BatchImage(models.Model):
    IMAGE_STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('EXTRACTED', 'Extracted'),
        ('STORED', 'Stored'),
        ('FAILED', 'Failed'),
    ]

    batch = models.ForeignKey(
        'segmentation.Batch',
        on_delete=models.CASCADE,
        related_name='batch_images'
    )

    image = models.ForeignKey(
        'segmentation.Image',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='batch_records'
    )

    original_filename = models.CharField(max_length=500)

    status = models.CharField(
        max_length=20,
        choices=IMAGE_STATUS_CHOICES,
        default='PENDING'
    )

    error_message = models.TextField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.original_filename} ({self.status})"



class TaskReview(models.Model):
    REVIEW_TYPE_CHOICES = [
        ('QC', 'Quality Control'),
        ('QA', 'Quality Assurance'),
    ]

    DECISION_CHOICES = [
        ('APPROVED', 'Approved'),
        ('REJECT_EDIT', 'Reject - Edit Required'),
        ('REJECT_REDO', 'Reject - Full Redo'),
    ]

    task = models.ForeignKey(
        'segmentation.SegmentationTask', # String reference to avoid circular imports
        on_delete=models.CASCADE,
        related_name='reviews'
    )

    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT
    )

    review_type = models.CharField(
        max_length=5,
        choices=REVIEW_TYPE_CHOICES,
        default='QA'
    )

    decision = models.CharField(
        max_length=20,
        choices=DECISION_CHOICES
    )

    comments = models.TextField(
        help_text="Mandatory explanation for decision",
        null=True, 
        blank=True
    )

    # Tracks when the decision was made
    reviewed_at = models.DateTimeField(auto_now_add=True)

    start_time = models.DateTimeField(null=True, blank=True, help_text="When QA started")
    end_time = models.DateTimeField(null=True, blank=True, help_text="When QA finished")
    duration = models.DurationField(null=True, blank=True, help_text="Time taken for review")

    class Meta:
        ordering = ['-reviewed_at']

    def __str__(self):
        return f"{self.task.id} - {self.decision} by {self.reviewer}"