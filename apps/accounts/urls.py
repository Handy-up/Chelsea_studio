from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('connexion/', views.ChelseaLoginView.as_view(), name='login'),
    path('deconnexion/', views.LogoutView.as_view(next_page='/'), name='logout'),
    path('', views.dashboard_view, name='dashboard'),
    path('rendez-vous/', views.appointment_list_view, name='gestion_appointments'),
    path('rendez-vous/<uuid:public_id>/', views.appointment_detail_view, name='gestion_appointment_detail'),
    path('calendrier/', views.calendar_view, name='gestion_calendar'),
    path('calendrier/partiel/', views.calendar_partial_view, name='gestion_calendar_partial'),
    path('services/', views.services_gestion_view, name='gestion_services'),
    path('galerie/', views.gallery_gestion_view, name='gestion_gallery'),
    path('horaires/', views.hours_gestion_view, name='gestion_hours'),
    path('blocages/', views.blocks_gestion_view, name='gestion_blocks'),
    path('parametres/', views.settings_gestion_view, name='gestion_settings'),
]
