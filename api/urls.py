from django.urls import path
from .views import GoogleLoginView

urlpatterns = [
    path('auth/google/', GoogleLoginView.as_view(), name='google_login'),
]
