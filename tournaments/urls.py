from django.urls import path
from . import views

app_name = 'tournaments'

urlpatterns = [
    path('', views.home, name='home'),
    path('ranking/<int:tournament_id>/', views.tournament_detail, name='tournament_detail'),
    path('categoria/<int:category_id>/', views.category_detail, name='category_detail'),
    path('categoria/<int:category_id>/ranking/', views.category_ranking, name='category_ranking'),
    path('torneios/', views.knockout_list, name='knockout_list'),
    path('torneio/<int:tournament_id>/', views.knockout_detail, name='knockout_detail'),
    path('torneio/<int:tournament_id>/chamada-pdf/', views.tournament_schedule_pdf, name='tournament_schedule_pdf'),
]
