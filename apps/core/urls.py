from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.home_view, name='home'),
    path('politique-confidentialite/', views.privacy_policy_view, name='privacy'),
    path('politique-annulation/', views.cancellation_policy_view, name='cancellation'),
    path('conditions/', views.terms_view, name='terms'),
]
