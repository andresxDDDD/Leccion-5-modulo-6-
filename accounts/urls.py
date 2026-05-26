from django.urls import path
from . import views

app_name = "accounts"

urlpatterns = [
    # FBV: autenticación
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("signup/", views.signup_view, name="signup"),
    # FBV: protegidas
    path("profile-fbv/", views.profile_fbv_view, name="profile-fbv"),
    path("dashboard-fbv/", views.dashboard_fbv_view, name="dashboard-fbv"),
    # CBV: protegidas
    path("profile/", views.ProfileView.as_view(), name="profile"),
    path("dashboard/", views.DashboardView.as_view(), name="dashboard"),
]
