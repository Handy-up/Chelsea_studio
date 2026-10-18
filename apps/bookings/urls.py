from django.urls import path
from . import views, configurator_views

app_name = 'bookings'

urlpatterns = [
    path('catalogue/', configurator_views.catalogue_view, name='catalogue'),
    path('configurer/', configurator_views.configure_view, name='configure'),
    path('pieces-jointes/<int:pk>/', configurator_views.attachment_view, name='attachment'),
    path('', views.booking_wizard_view, name='wizard'),
    path('disponibilites/', views.availability_api_view, name='disponibilites'),
    path('disponibilites/calendrier/', views.availability_calendar_view, name='disponibilites_mois'),
    path('confirmation/<uuid:public_id>/', views.booking_confirmation_view, name='confirmation'),
    path('annuler/<uuid:public_id>/<str:token>/', views.cancel_appointment_view, name='cancel'),
]
