from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from todos import views as todos_views


urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/login/", auth_views.LoginView.as_view(template_name="login.html"), name="login"),
    path("accounts/logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("accounts/register/", todos_views.register, name="register"),
    path("", include("todos.urls")),
]

