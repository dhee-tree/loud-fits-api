from django.urls import path, include
from outfit.views import ExploreOutfitListView

urlpatterns = [
    path('auth/', include('authentication.urls')),
    path('users/', include('user.urls')),
    path('profile/', include('user_profile.urls')),
    path('avatar/', include('avatar.urls')),
    path('store/', include('store.urls')),
    path('products/', include('product.urls')),
    path('outfits/', include('outfit.urls')),
    path('explore/outfits/', ExploreOutfitListView.as_view(), name='explore_outfits'),
]
