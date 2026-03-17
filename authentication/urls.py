from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import GoogleLoginView, RegisterView, LoginView, StoreRegisterView, ChangePasswordView

urlpatterns = [
    path('google/', GoogleLoginView.as_view(), name='google_login'),
    path('login/', LoginView.as_view(), name='login'),
    path('refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('register/', RegisterView.as_view(), name='register'),
    path('store/register/', StoreRegisterView.as_view(), name='store_register'),
    path('change-password/', ChangePasswordView.as_view(), name='change_password'),
]
