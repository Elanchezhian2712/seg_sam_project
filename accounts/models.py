from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    ROLE_CHOICES = [
        ('ADMIN', 'Admin'),
        ('SEGMENTER', 'Segmenter'),
        ('QC', 'Quality Control'),
        ('QA', 'Quality Assurance'),
    ]

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='SEGMENTER'
    )

    team = models.CharField(
        max_length=100,
        null=True,
        blank=True
    )

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.username} ({self.role})"
