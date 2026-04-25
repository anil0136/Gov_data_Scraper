from django.urls import path
from .views import home, run_all

urlpatterns = [
    path('', home),
    path('run-all/', run_all),
]