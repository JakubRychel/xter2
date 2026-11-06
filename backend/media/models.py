import os
import uuid

from django.db import models
from django.utils import timezone


def media_upload_to(instance, filename):
    ext = os.path.splitext(filename)[1].lower()
    return f'media/{instance.id}/original{ext}'

class MediaAsset(models.Model):
    class Kind(models.TextChoices):
        IMAGE = 'image', 'Image'
        VIDEO = 'video', 'Video'
        GIFV = 'gifv', 'GIF (video)'

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        PROCESSING = 'processing', 'Processing'
        READY = 'ready', 'Ready'
        FAILED = 'failed', 'Failed'

    id = models.UUIDField(primary_key=True, default=uuid.uuid7, editable=False)

    owner = models.ForeignKey('profiles.Profile', on_delete=models.CASCADE, related_name='media_assets')
    uploaded_by = models.ForeignKey(
        'profiles.PersonalProfile', on_delete=models.SET_NULL, null=True, blank=True, related_name='uploaded_media'
    )

    kind = models.CharField(max_length=10, choices=Kind.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)

    file = models.FileField(upload_to=media_upload_to, max_length=255, blank=True)
    remote_url = models.CharField(max_length=2048, null=True, blank=True)

    mime_type = models.CharField(max_length=100, blank=True)
    file_size = models.PositiveBigIntegerField(null=True, blank=True)
    width = models.PositiveIntegerField(null=True, blank=True)
    height = models.PositiveIntegerField(null=True, blank=True)
    duration = models.FloatField(null=True, blank=True)
    blurhash = models.CharField(max_length=100, blank=True)
    alt_text = models.TextField(blank=True)

    created_at = models.DateTimeField(default=timezone.now)
    processed_at = models.DateTimeField(null=True, blank=True)

    @property
    def is_local(self):
        return self.remote_url is None

    def __str__(self):
        return f'{self.kind} {self.id} ({self.status})'