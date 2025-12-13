import zipfile
import os
from PIL import Image as PILImage
from segmentation.models import Image
import uuid
import shutil
from django.conf import settings
import hashlib
from django.core.files.storage import default_storage
from segmentation.models import SegmentationTask
from django.db.models import F
from segmentation.models import ProjectEmployeeMapping
import time
from django.utils import timezone
from segmentation.models import Batch
from segmentation.models import Dataset

# Allowed image formats
ALLOWED_EXTENSIONS = ('.jpg', '.jpeg', '.png')

# Max ZIP size: 500 MB
MAX_ZIP_SIZE = 500 * 1024 * 1024  


def validate_zip_file(zip_file):
    """
    Validates uploaded ZIP file.
    Returns:
        (is_valid, result_dict)
    """

    # 1. File size check
    if zip_file.size > MAX_ZIP_SIZE:
        return False, {
            "error": "ZIP file exceeds 500MB limit"
        }

    # 2. ZIP integrity check
    try:
        with zipfile.ZipFile(zip_file) as zf:
            bad_file = zf.testzip()
            if bad_file:
                return False, {
                    "error": f"Corrupted file found: {bad_file}"
                }
    except zipfile.BadZipFile:
        return False, {
            "error": "Invalid ZIP file"
        }

    valid_images = []
    failed_images = []

    # 3. Validate image files inside ZIP
    with zipfile.ZipFile(zip_file) as zf:
        for file_name in zf.namelist():

            # Ignore folders
            if file_name.endswith('/'):
                continue

            # Extension check
            if not file_name.lower().endswith(ALLOWED_EXTENSIONS):
                failed_images.append({
                    "filename": file_name,
                    "error": "Unsupported file format"
                })
                continue

            # Try opening image
            try:
                with zf.open(file_name) as img_file:
                    img = PILImage.open(img_file)
                    width, height = img.size

                    if width < 256 or height < 256:
                        failed_images.append({
                            "filename": file_name,
                            "error": "Image dimensions below 256x256"
                        })
                        continue

                    valid_images.append({
                        "filename": file_name,
                        "width": width,
                        "height": height
                    })

            except Exception:
                failed_images.append({
                    "filename": file_name,
                    "error": "Unreadable image file"
                })

    return True, {
        "total_files": len(valid_images) + len(failed_images),
        "valid_images": valid_images,
        "failed_images": failed_images,
        "valid_count": len(valid_images),
        "failed_count": len(failed_images),
    }


def extract_zip_to_temp(zip_file, batch_id=None):
    """
    Extracts ZIP file to a temporary directory.
    Returns:
        temp_dir_path
    """

    # Generate batch id if not provided
    if not batch_id:
        batch_id = f"upload_{uuid.uuid4().hex[:8]}"

    temp_root = os.path.join(settings.MEDIA_ROOT, 'temp')
    temp_dir = os.path.join(temp_root, f'unzip_{batch_id}')

    # Ensure clean temp directory
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)

    os.makedirs(temp_dir, exist_ok=True)

    with zipfile.ZipFile(zip_file) as zf:
        zf.extractall(temp_dir)

    return temp_dir


def calculate_checksum(file_path):
    """Calculate SHA256 checksum of a file"""
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            sha256.update(chunk)
    return sha256.hexdigest()


def save_images_to_dataset(temp_dir, project, dataset):
    """
    Move images from temp directory to final dataset folder
    and create Image records.

    Returns:
        {
            "created": int,
            "duplicates": int,
            "failed": list
        }
    """

    created_count = 0
    duplicate_count = 0
    failed_images = []

    final_dir = os.path.join(
        project.storage_path,
        'datasets',
        dataset.code,
        'original_images'
    )

    os.makedirs(final_dir, exist_ok=True)

    for root, _, files in os.walk(temp_dir):
        for file_name in files:

            src_path = os.path.join(root, file_name)
            dest_path = os.path.join(final_dir, file_name)

            try:
                checksum = calculate_checksum(src_path)

                # Duplicate check (same dataset)
                if Image.objects.filter(
                    dataset=dataset,
                    checksum=checksum
                ).exists():
                    duplicate_count += 1
                    continue

                # Read image properties
                with PILImage.open(src_path) as img:
                    width, height = img.size

                file_size = os.path.getsize(src_path)

                # Move file
                shutil.move(src_path, dest_path)

                # Create DB record
                Image.objects.create(
                    dataset=dataset,
                    file_name=file_name,
                    file_path=dest_path,
                    width=width,
                    height=height,
                    file_size=file_size,
                    checksum=checksum,
                    status='UPLOADED'
                )

                created_count += 1

            except Exception as e:
                failed_images.append({
                    "filename": file_name,
                    "error": str(e)
                })

    return {
        "created": created_count,
        "duplicates": duplicate_count,
        "failed": failed_images
    }

def create_segmentation_tasks(images, priority='MEDIUM'):
    """
    Create segmentation tasks for given images.

    Args:
        images: QuerySet or list of Image objects
        priority: Task priority

    Returns:
        int: number of tasks created
    """

    tasks_created = 0

    for image in images:
        SegmentationTask.objects.create(
            image=image,
            status='PENDING',
            priority=priority
        )
        tasks_created += 1

    return tasks_created


def auto_assign_tasks(project, tasks):
    """
    Automatically assign segmentation tasks to available employees
    based on capacity and workload.

    Args:
        project: Project instance
        tasks: QuerySet or list of SegmentationTask objects

    Returns:
        dict summary
    """

    assigned_count = 0
    unassigned_tasks = []

    # Get available segmenters for this project
    employees = ProjectEmployeeMapping.objects.filter(
        project=project,
        role_in_project='SEGMENTER',
        is_available=True
    ).exclude(
        current_workload__gte=F('capacity')
    ).order_by('current_workload')

    if not employees.exists():
        return {
            "assigned": 0,
            "unassigned": len(tasks),
            "message": "No available segmenters"
        }

    employees = list(employees)

    emp_index = 0
    emp_count = len(employees)

    for task in tasks:
        assigned = False

        # Try assigning task
        for _ in range(emp_count):
            emp = employees[emp_index]

            if emp.current_workload < emp.capacity:
                task.assigned_to = emp.user
                task.status = 'ASSIGNED'
                task.save(update_fields=['assigned_to', 'status'])

                emp.current_workload += 1
                emp.save(update_fields=['current_workload'])

                assigned_count += 1
                assigned = True

                # Rotate to next employee
                emp_index = (emp_index + 1) % emp_count
                break

            emp_index = (emp_index + 1) % emp_count

        if not assigned:
            unassigned_tasks.append(task.id)

    return {
        "assigned": assigned_count,
        "unassigned": len(unassigned_tasks),
        "unassigned_task_ids": unassigned_tasks
    }


def process_batch_upload(
    *,
    zip_file,
    project,
    uploaded_by,
    priority='MEDIUM'
):
    """
    COMPLETE BATCH UPLOAD PIPELINE

    Design (LOCKED):
    - User uploads ZIP only
    - Dataset is auto-created (hidden)
    - 1 ZIP = 1 Dataset = 1 Batch
    """

    start_time = time.time()

    # --------------------------------------------------
    # 1. GENERATE BATCH ID
    # --------------------------------------------------
    batch_id = f"upload_{timezone.now().strftime('%Y%m%d_%H%M%S')}"

    # --------------------------------------------------
    # 2. VALIDATE ZIP
    # --------------------------------------------------
    is_valid, validation_result = validate_zip_file(zip_file)

    if not is_valid:
        return {
            "status": "failed",
            "error": validation_result.get("error", "ZIP validation failed")
        }

    # --------------------------------------------------
    # 3. AUTO-CREATE DATASET (SYSTEM ONLY)
    # --------------------------------------------------
    dataset_code = batch_id

    dataset_storage_path = os.path.join(
        settings.MEDIA_ROOT,
        'projects',
        project.code,
        'datasets',
        dataset_code
    )

    dataset = Dataset.objects.create(
        project=project,
        name=f"Dataset {dataset_code}",
        code=dataset_code,
        status='ACTIVE',
        storage_path=dataset_storage_path,
        created_by=uploaded_by
    )

    # --------------------------------------------------
    # 4. CREATE BATCH (DATASET IS REQUIRED)
    # --------------------------------------------------
    batch = Batch.objects.create(
        project=project,
        dataset=dataset,                 # ✅ NEVER NULL
        batch_id=batch_id,
        uploaded_by=uploaded_by,
        original_zip_path=zip_file.name,
        total_images=validation_result["total_files"],
        status='PROCESSING'
    )

    # --------------------------------------------------
    # 5. EXTRACT ZIP TO TEMP
    # --------------------------------------------------
    temp_dir = extract_zip_to_temp(
        zip_file=zip_file,
        batch_id=batch.batch_id
    )

    # --------------------------------------------------
    # 6. SAVE IMAGES + CREATE IMAGE RECORDS
    # --------------------------------------------------
    image_result = save_images_to_dataset(
        temp_dir=temp_dir,
        project=project,
        dataset=dataset
    )

    batch.images_extracted = image_result["created"]
    batch.images_failed = len(image_result["failed"])
    batch.save(update_fields=['images_extracted', 'images_failed'])

    # --------------------------------------------------
    # 7. CREATE SEGMENTATION TASKS
    # --------------------------------------------------
    images = Image.objects.filter(dataset=dataset)

    total_tasks = create_segmentation_tasks(
        images=images,
        priority=priority
    )

    batch.total_tasks_created = total_tasks
    batch.save(update_fields=['total_tasks_created'])

    # --------------------------------------------------
    # 8. AUTO-ASSIGN TASKS
    # --------------------------------------------------
    tasks = SegmentationTask.objects.filter(
        image__dataset=dataset,
        status='PENDING'
    )

    assignment_result = auto_assign_tasks(
        project=project,
        tasks=tasks
    )

    batch.assigned_tasks = assignment_result.get("assigned", 0)
    batch.unassigned_tasks = assignment_result.get("unassigned", 0)

    # --------------------------------------------------
    # 9. FINALIZE BATCH
    # --------------------------------------------------
    batch.status = 'COMPLETED'
    batch.completed_at = timezone.now()
    batch.save(update_fields=[
        'assigned_tasks',
        'unassigned_tasks',
        'status',
        'completed_at'
    ])

    end_time = time.time()

    # --------------------------------------------------
    # 10. RESPONSE (MATCHES YOUR REQUIREMENT)
    # --------------------------------------------------
    return {
        "batch_id": batch.batch_id,
        "project_id": project.id,
        "dataset_code": dataset.code,   # INTERNAL ONLY
        "total_images": batch.total_images,
        "successfully_extracted": batch.images_extracted,
        "failed_count": batch.images_failed,
        "failed_images": image_result["failed"],
        "duplicates_found": image_result["duplicates"],
        "total_tasks_created": batch.total_tasks_created,
        "assigned_tasks": batch.assigned_tasks,
        "unassigned_tasks": batch.unassigned_tasks,
        "extraction_time_seconds": round(end_time - start_time, 2),
        "storage_location": dataset.storage_path,
        "preview_generated": True
    }
