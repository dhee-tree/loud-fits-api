import uuid

from django.conf import settings
from django.db import models


class AvatarProfile(models.Model):
    BODY_TYPE_SMALL = 'small'
    BODY_TYPE_MEDIUM = 'medium'
    BODY_TYPE_LARGE = 'large'

    SKIN_TONE_LIGHT = 'light'
    SKIN_TONE_MEDIUM = 'medium'
    SKIN_TONE_DEEP = 'deep'

    ALLOWED_BODY_TYPES = (
        BODY_TYPE_SMALL,
        BODY_TYPE_MEDIUM,
        BODY_TYPE_LARGE,
    )
    ALLOWED_SKIN_TONES = (
        SKIN_TONE_LIGHT,
        SKIN_TONE_MEDIUM,
        SKIN_TONE_DEEP,
    )

    uuid = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='avatar_profile',
    )
    config = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return f"Avatar profile for {self.user.email}"

    @classmethod
    def default_config(cls):
        return {
            'body_type': cls.BODY_TYPE_MEDIUM,
            'skin_tone': cls.SKIN_TONE_MEDIUM,
        }

    @classmethod
    def normalise_config(cls, config):
        baseline = cls.default_config()
        if not isinstance(config, dict):
            return baseline

        legacy_body_map = {
            'slim': cls.BODY_TYPE_SMALL,
            'regular': cls.BODY_TYPE_MEDIUM,
            'curvy': cls.BODY_TYPE_LARGE,
        }
        legacy_skin_map = {
            'fair': cls.SKIN_TONE_LIGHT,
            'tan': cls.SKIN_TONE_DEEP,
        }

        merged = {
            **baseline,
            **config,
        }

        body_type = merged.get('body_type')
        body_type = legacy_body_map.get(body_type, body_type)
        if body_type not in cls.ALLOWED_BODY_TYPES:
            body_type = baseline['body_type']

        skin_tone = merged.get('skin_tone')
        skin_tone = legacy_skin_map.get(skin_tone, skin_tone)
        if skin_tone not in cls.ALLOWED_SKIN_TONES:
            skin_tone = baseline['skin_tone']

        merged['body_type'] = body_type
        merged['skin_tone'] = skin_tone

        return merged
