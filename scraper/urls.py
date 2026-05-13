from django.urls import path
from .views import (
    api_government_services,
    api_grants,
    api_index,
    api_india_portal_schemes,
    api_myscheme,
    api_scholarships,
    api_umang_schemes,
    home,
    run_all,
)

urlpatterns = [
    path('', home),
    path('run-all/', run_all),
    path('api/', api_index, name='api-index'),
    path('api/umang-schemes/', api_umang_schemes, name='api-umang-schemes'),
    path('api/government-services/', api_government_services, name='api-government-services'),
    path('api/myscheme/', api_myscheme, name='api-myscheme'),
    path('api/india-portal-schemes/', api_india_portal_schemes, name='api-india-portal-schemes'),
    path('api/scholarships/', api_scholarships, name='api-scholarships'),
    path('api/grants/', api_grants, name='api-grants'),
]
