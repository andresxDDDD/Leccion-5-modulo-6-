from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth.models import User
from django.views.generic import TemplateView
from django.contrib import messages


# ─── FBV: Login ──────────────────────────────────────────────
def login_view(request):
    if request.method == "POST":
        username = request.POST["username"]
        password = request.POST["password"]
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            next_url = request.GET.get("next", "/")
            return redirect(next_url)
        else:
            messages.error(request, "Usuario o contraseña incorrectos.")
    return render(request, "registration/login.html")


# ─── FBV: Logout ─────────────────────────────────────────────
def logout_view(request):
    logout(request)
    return redirect("accounts:login")


# ─── FBV: Signup ─────────────────────────────────────────────
def signup_view(request):
    if request.method == "POST":
        username = request.POST["username"]
        password1 = request.POST["password1"]
        password2 = request.POST["password2"]
        if password1 != password2:
            messages.error(request, "Las contraseñas no coinciden.")
        elif User.objects.filter(username=username).exists():
            messages.error(request, "El usuario ya existe.")
        else:
            user = User.objects.create_user(
                username=username, password=password1
            )
            login(request, user)
            return redirect("accounts:profile")
    return render(request, "registration/signup.html")


# ─── FBV protegida con @login_required ───────────────────────
@login_required
def profile_fbv_view(request):
    return render(request, "accounts/profile.html", {"via": "FBV (decorador)"})


# ─── FBV protegida con @login_required + @permission_required ─
@login_required
@permission_required("accounts.can_view_dashboard", raise_exception=True)
def dashboard_fbv_view(request):
    return render(request, "accounts/dashboard.html", {"via": "FBV (decoradores)"})


# ─── CBV protegida con LoginRequiredMixin ────────────────────
class ProfileView(LoginRequiredMixin, TemplateView):
    template_name = "accounts/profile.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["via"] = "CBV (LoginRequiredMixin)"
        return context


# ─── CBV protegida con LoginRequiredMixin + PermissionRequiredMixin ─
class DashboardView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    template_name = "accounts/dashboard.html"
    permission_required = "accounts.can_view_dashboard"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["via"] = "CBV (LoginRequiredMixin + PermissionRequiredMixin)"
        return context
