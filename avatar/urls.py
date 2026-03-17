from django.urls import path

from .views import AvatarMeView, AvatarTemplateListView


urlpatterns = [
    path('me/', AvatarMeView.as_view(), name='avatar_me'),
    path('templates/', AvatarTemplateListView.as_view(), name='avatar_templates'),
]

