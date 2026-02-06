from django.urls import path, include

urlpatterns = [
    path('auth/', include('authentication.urls')),
    path('users/', include('user.urls')),
    path('profile/', include('user_profile.urls')),
    path('store/', include('store.urls')),
]
