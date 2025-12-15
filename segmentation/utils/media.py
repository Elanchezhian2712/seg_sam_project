from django.conf import settings
import os


def media_path_to_url(file_path: str) -> str:
    """
    Convert absolute filesystem media path to MEDIA URL
    Safe: never produces ../ in URLs
    """
    media_root = os.path.abspath(settings.MEDIA_ROOT)
    file_path = os.path.abspath(file_path)

    # 🔒 Security + correctness check
    if not file_path.startswith(media_root):
        raise ValueError(
            f"File path is outside MEDIA_ROOT: {file_path}"
        )

    relative_path = file_path[len(media_root):].lstrip(os.sep)

    return settings.MEDIA_URL + relative_path.replace(os.sep, "/")
