from django.urls import path
from . import views

app_name = 'tournaments'

urlpatterns = [
    path('', views.home, name='home'),
    path('categoria/<int:category_id>/', views.category_detail, name='category_detail'),
    path('categoria/<int:category_id>/ranking/', views.category_ranking, name='category_ranking'),
]
