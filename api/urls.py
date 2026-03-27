from django.urls import path, include
from outfit.views import ExploreOutfitListView, RecommendedOutfitListView, TrendingOutfitListView

urlpatterns = [
    path('auth/', include('authentication.urls')),
    path('users/', include('user.urls')),
    path('profile/', include('user_profile.urls')),
    path('avatar/', include('avatar.urls')),
    path('store/', include('store.urls')),
    path('products/', include('product.urls')),
    path('outfits/', include('outfit.urls')),
    path('addresses/', include('address.urls')),
    path('cart/', include('cart.urls')),
    path('orders/', include('order.urls')),
    path('wardrobe/', include('wardrobe.urls')),
    path('store/payments/', include('payment.urls')),
    path('explore/outfits/recommended/', RecommendedOutfitListView.as_view(), name='recommended_outfits'),
    path('explore/outfits/trending/', TrendingOutfitListView.as_view(), name='trending_outfits'),
    path('explore/outfits/', ExploreOutfitListView.as_view(), name='explore_outfits'),
]
