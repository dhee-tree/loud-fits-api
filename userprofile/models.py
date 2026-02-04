import uuid
from django.db import models
from user.models import User

# Create your models here.


class Profile(models.Model):
    class Gender(models.TextChoices):
        MALE = 'MALE', 'Male'
        FEMALE = 'FEMALE', 'Female'
        OTHER = 'OTHER', 'Other'

    class AvatarSize(models.TextChoices):
        SMALL = 'SMALL', 'Small'
        MEDIUM = 'MEDIUM', 'Medium'
        LARGE = 'LARGE', 'Large'

    uuid = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False, unique=True)
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name='profile')
    gender = models.CharField(
        max_length=10, choices=Gender.choices, blank=True, null=True)
    avatar_size = models.CharField(
        max_length=10,
        choices=AvatarSize.choices,
        default=AvatarSize.MEDIUM,
    )
    profile_picture = models.ImageField(
        upload_to='profile_pictures/', blank=True, null=True)
    stylist_enabled = models.BooleanField(default=False)

    def __str__(self):
        return f"Profile of {self.user.email}"
