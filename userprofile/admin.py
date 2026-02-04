from django.contrib import admin
from .models import Profile

# Register your models here.


class ProfileAdmin(admin.ModelAdmin):
    list_display = ('get_full_name', 'user', 'shopping_preference', 'avatar_size')
    search_fields = ('user__username', 'user__email')
    list_filter = ('shopping_preference', 'avatar_size')

    @admin.display(description='Full Name')
    def get_full_name(self, obj):
        return obj.user.get_full_name()


admin.site.register(Profile, ProfileAdmin)
