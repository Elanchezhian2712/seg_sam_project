from django.apps import AppConfig


class AccountsConfig(AppConfig):
    name = 'accounts'

class SegmentationConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "segmentation"