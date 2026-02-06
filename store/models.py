import uuid
from django.db import models
from django.conf import settings


class Store(models.Model):
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='store'
    )
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    feed_last_uploaded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    def get_uuid(self):
        return self.uuid

    def get_owner(self):
        return self.owner

    def get_name(self):
        return self.name

    def get_slug(self):
        return self.slug

    def get_feed_last_uploaded_at(self):
        return self.feed_last_uploaded_at
