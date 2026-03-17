from django.contrib import admin

from .models import AvatarProfile


@admin.register(AvatarProfile)
class AvatarProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'created_at', 'updated_at')
    search_fields = ('user__email', 'user__username')
