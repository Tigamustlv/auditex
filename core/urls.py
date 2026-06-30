from django.urls import path
from .views import home, upload, export_excel
from django.contrib.auth import views as auth_views


urlpatterns = [
    path('', home, name='Home'),
    path('upload-audit/', upload, name='Upload'),
    path('export/', export_excel, name='Export'),
    path('login/', auth_views.LoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
]



