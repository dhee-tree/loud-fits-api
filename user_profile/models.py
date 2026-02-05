import uuid
from django.db import models
from user.models import User

# Create your models here.


class Profile(models.Model):
    class ShoppingPreference(models.TextChoices):
        MENSWEAR = 'Menswear', 'Menswear'
        WOMENSWEAR = 'Womenswear', 'Womenswear'
        UNISEX = 'Unisex', 'Unisex'
        NO_PREFERENCE = 'No Preference', 'No Preference'

    class AvatarSize(models.TextChoices):
        SMALL = 'Small', 'Small'
        MEDIUM = 'Medium', 'Medium'
        LARGE = 'Large', 'Large'

    uuid = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False, unique=True)
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name='profile')
    shopping_preference = models.CharField(
        max_length=15, choices=ShoppingPreference.choices, blank=True, null=True)
    avatar_size = models.CharField(
        max_length=10,
        choices=AvatarSize.choices,
        default=AvatarSize.MEDIUM,
    )
    profile_picture = models.ImageField(
        upload_to='profile_pictures/', blank=True, null=True)
    stylist_enabled = models.BooleanField(default=False)
    onboarding_completed = models.BooleanField(default=False)

    def __str__(self):
        return f"Profile of {self.user.email}"
