from django.urls import path
from .views import ProfileView, CreatorProfileView, CreatorFollowView, CreatorEnquiryView

urlpatterns = [
    path('', ProfileView.as_view(), name='profile'),
    path('creators/<str:username>/', CreatorProfileView.as_view(), name='creator_profile'),
    path('creators/<str:username>/follow/', CreatorFollowView.as_view(), name='creator_follow'),
    path('creators/<str:username>/enquiry/', CreatorEnquiryView.as_view(), name='creator_enquiry'),
]
