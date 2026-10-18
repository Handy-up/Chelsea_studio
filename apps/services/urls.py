from django.urls import path
from . import views

app_name = 'services'

urlpatterns = [
    path('', views.service_list_view, name='list'),
    path('hommes/', views.service_list_view, {'audience': 'men'}, name='men'),
    path('femmes/', views.service_list_view, {'audience': 'women'}, name='women'),
    path('<slug:slug>/', views.service_detail_view, name='detail'),
]
