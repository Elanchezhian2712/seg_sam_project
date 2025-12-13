from django.conf import settings
import os


def media_path_to_url(file_path: str) -> str:
    """
    Convert absolute filesystem media path to MEDIA URL
    Works on Windows & Linux
    """
    media_root = os.path.normpath(str(settings.MEDIA_ROOT))
    file_path = os.path.normpath(file_path)

    relative_path = os.path.relpath(file_path, media_root)
    return settings.MEDIA_URL + relative_path.replace("\\", "/")
