# Tutorial de Autenticación en Django — Login/Logout Manual

Este tutorial cubre paso a paso la implementación de un sistema de autenticación en Django utilizando
el modelo Login/Logout manual (sin usar las vistas genéricas `LoginView`/`LogoutView` de Django),
junto con autorización y permisos.

---

## Índice

1. [Creación del entorno virtual e instalación](#1-creación-del-entorno-virtual-e-instalación)
2. [Creación del proyecto Django](#2-creación-del-proyecto-django)
3. [Configuración inicial (settings.py)](#3-configuración-inicial-settingspy)
4. [Creación de la app accounts](#4-creación-de-la-app-accounts)
5. [Modelo Profile con permiso personalizado](#5-modelo-profile-con-permiso-personalizado)
6. [Views de autenticación manuales](#6-views-de-autenticación-manuales)
7. [Templates](#7-templates)
8. [Protección de rutas](#8-protección-de-rutas)
9. [Configuración de URLs](#9-configuración-de-urls)
10. [Manejo de 403 (accesos no autorizados)](#10-manejo-de-403-accesos-no-autorizados)
11. [Admin personalizado](#11-admin-personalizado)
12. [Ejecución y verificación](#12-ejecución-y-verificación)

---

## 1. Creación del entorno virtual e instalación

```bash
python -m venv venv
source venv/bin/activate  # En Linux/Mac
# venv\Scripts\activate   # En Windows

pip install django
```

Verificar instalación:

```bash
python -m django --version
# Debería mostrar 6.x o superior
```

### ¿Qué acabamos de hacer?

- `python -m venv venv` crea un entorno virtual aislado para las dependencias del proyecto.
- `source venv/bin/activate` activa el entorno (el prompt cambia a `(venv)`).
- `pip install django` instala Django y todas sus dependencias dentro del entorno.

---

## 2. Creación del proyecto Django

```bash
django-admin startproject seguridad_acceso_django .
```

### ¿Qué acabamos de hacer?

- `startproject` crea la estructura base del proyecto.
- El `.` al final indica que lo cree en el directorio actual, no en una subcarpeta.

### Estructura generada

```
├── manage.py                  # Punto de entrada para comandos de Django
├── seguridad_acceso_django/   # Paquete de configuración del proyecto
│   ├── __init__.py
│   ├── asgi.py                # Servidor ASGI (async)
│   ├── settings.py            # Configuración del proyecto
│   ├── urls.py                # Enrutador principal
│   └── wsgi.py                # Servidor WSGI (sync)
```

---

## 3. Configuración inicial (settings.py)

Abrimos `seguridad_acceso_django/settings.py` y revisamos/configuramos:

### INSTALLED_APPS — ¿Qué hace cada app?

```python
INSTALLED_APPS = [
    "django.contrib.admin",         # Panel de administración
    "django.contrib.auth",          # Sistema de autenticación (usuarios, grupos, permisos)
    "django.contrib.contenttypes",  # Framework de tipos de contenido (necesario para permisos)
    "django.contrib.sessions",      # Manejo de sesiones (cookies)
    "django.contrib.messages",      # Sistema de mensajes flash
    "django.contrib.staticfiles",   # Archivos estáticos (CSS, JS)
    "accounts",                     # Nuestra app (la agregaremos después)
]
```

### MIDDLEWARE — ¿Qué hace cada middleware?

```python
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",         # Seguridad HTTP
    "django.contrib.sessions.middleware.SessionMiddleware",  # Maneja sesiones por cookie
    "django.middleware.common.CommonMiddleware",             # Varios (AppendSlash, etc.)
    "django.middleware.csrf.CsrfViewMiddleware",             # Protección CSRF en formularios
    "django.contrib.auth.middleware.AuthenticationMiddleware",# Pone request.user disponible
    "django.contrib.messages.middleware.MessageMiddleware",  # Maneja messages flash
    "django.middleware.clickjacking.XFrameOptionsMiddleware",# Protección clickjacking
]
```

**Atención especial a `AuthenticationMiddleware`**: es el que se ejecuta en cada request y
setea `request.user` con el usuario autenticado (o un `AnonymousUser` si no hay sesión). Sin él,
`request.user` no existiría.

### TEMPLATES

```python
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],  # Carpeta global de templates
        "APP_DIRS": True,                   # Busca templates dentro de cada app
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",       # request disponible en templates
                "django.contrib.auth.context_processors.auth",       # user y perms disponibles
                "django.contrib.messages.context_processors.messages",# messages disponibles
            ],
        },
    },
]
```

- `"DIRS": [BASE_DIR / "templates"]` → Django buscará templates también en la carpeta `templates/`
  en la raíz del proyecto.
- `context_processors` son funciones que inyectan variables en todos los templates.
  El auth context processor pone `{{ user }}` y `{{ perms }}` disponibles en todos los templates.

### Configuración de autenticación

```python
LOGIN_URL = "/accounts/login/"         # Dónde redirigir cuando se requiere login
LOGIN_REDIRECT_URL = "/"               # Dónde ir después de iniciar sesión (si no hay ?next)
LOGOUT_REDIRECT_URL = "/accounts/login/" # Dónde ir después de cerrar sesión
```

- `LOGIN_URL`: Cuando un decorador como `@login_required` detecta que el usuario no está autenticado,
  redirige a esta URL agregando `?next=/ruta-que-intentaba-acceder`.
- `LOGIN_REDIRECT_URL`: Si el login no tiene un parámetro `?next`, redirige aquí.

### Base de datos

```python
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}
```

SQLite3 es la base de datos por defecto. No requiere configuración adicional. Ideal para desarrollo.

---

## 4. Creación de la app accounts

```bash
python manage.py startapp accounts
```

### Registrar en INSTALLED_APPS

En `settings.py` agregamos:

```python
INSTALLED_APPS = [
    ...
    "accounts",
]
```

### Estructura de la app

```
accounts/
├── __init__.py
├── admin.py        # Registro de modelos en el admin
├── apps.py         # Configuración de la app
├── migrations/     # Migraciones de base de datos
├── models.py       # Modelos de datos
├── tests.py        # Tests
├── urls.py         # URLs de la app (lo crearemos)
└── views.py        # Vistas (lógica de negocio)
```

---

## 5. Modelo Profile con permiso personalizado

En `accounts/models.py`:

```python
from django.db import models
from django.contrib.auth.models import User


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    bio = models.TextField(blank=True)

    class Meta:
        permissions = [
            ("can_view_dashboard", "Puede ver el dashboard"),
        ]

    def __str__(self):
        return f"Perfil de {self.user.username}"
```

### Explicación

- **`OneToOneField`**: Cada usuario tiene UN perfil y cada perfil pertenece a UN usuario.
  La relación es 1 a 1. `on_delete=models.CASCADE` significa que si se elimina el usuario,
  también se elimina su perfil.
- **`class Meta`**: Aquí definimos metadatos del modelo, incluyendo permisos personalizados.
- **`permissions`**: Lista de tuplas `(codename, nombre_legible)`. Al ejecutar `migrate`,
  Django crea estos permisos en la tabla `auth_permission`.
- **`can_view_dashboard`**: Es el permiso que usaremos para proteger la vista del dashboard.

### Crear y aplicar migraciones

```bash
python manage.py makemigrations
python manage.py migrate
```

### ¿Qué creó esto en la base de datos?

- Tabla `accounts_profile` con columnas `id`, `user_id` (FK a `auth_user`), `bio`.
- Se insertaron registros en `auth_permission`:
  - `accounts.add_profile`
  - `accounts.change_profile`
  - `accounts.delete_profile`
  - `accounts.view_profile`
  - `accounts.can_view_dashboard` ← nuestro permiso personalizado

---

## 6. Views de autenticación manuales

### 6.1 login_view (FBV)

```python
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib import messages


def login_view(request):
    if request.method == "POST":
        # 1. Extraer credenciales del formulario
        username = request.POST["username"]
        password = request.POST["password"]

        # 2. Autenticar: verifica username y contraseña contra la BD
        user = authenticate(request, username=username, password=password)

        if user is not None:
            # 3. Iniciar sesión: crea sesión en servidor y cookie en navegador
            login(request, user)

            # 4. Redirigir a la URL original (?next=) o a la raíz
            next_url = request.GET.get("next", "/")
            return redirect(next_url)
        else:
            # 5. Credenciales inválidas → mensaje de error
            messages.error(request, "Usuario o contraseña incorrectos.")

    return render(request, "registration/login.html")
```

#### Explicación detallada del flujo

**`authenticate(request, username=..., password=...)`**:

1. Toma el username y password en texto plano.
2. Busca en `auth_user` un registro con ese username.
3. Si existe, **hashea la contraseña ingresada** usando el mismo algoritmo que Django usó para almacenarla.
4. Compara el hash resultante con el hash almacenado en `auth_user.password`.
5. Si coinciden → retorna el objeto `User`.
6. Si no coinciden (o el usuario no existe) → retorna `None`.

**`login(request, user)`**:

1. Toma el objeto `User` autenticado.
2. Crea una **sesión** en el servidor (tabla `django_session`).
3. Envía una cookie `sessionid` al navegador con el ID de sesión.
4. A partir de este momento, en cada request el `AuthenticationMiddleware` leerá la cookie
   `sessionid`, buscará la sesión en la BD, y seteará `request.user` con este usuario.

**`?next=`**:

- Cuando `@login_required` redirige a login, agrega `?next=/ruta-original`.
- En la vista de login, si existe `next` en los parámetros GET, redirigimos allí después del login.
- Esto permite que el usuario retorne exactamente a la página que quería visitar, después de loguearse.

### 6.2 logout_view (FBV)

```python
from django.contrib.auth import logout


def logout_view(request):
    logout(request)
    return redirect("accounts:login")
```

#### Explicación

**`logout(request)`**:

1. Elimina la sesión actual de la tabla `django_session`.
2. Elimina la cookie `sessionid` del navegador.
3. `request.user` pasa a ser `AnonymousUser` en el siguiente request.

### 6.3 signup_view (FBV)

```python
from django.contrib.auth.models import User


def signup_view(request):
    if request.method == "POST":
        username = request.POST["username"]
        password1 = request.POST["password1"]
        password2 = request.POST["password2"]

        # Validación: contraseñas deben coincidir
        if password1 != password2:
            messages.error(request, "Las contraseñas no coinciden.")

        # Validación: username no debe existir
        elif User.objects.filter(username=username).exists():
            messages.error(request, "El usuario ya existe.")

        else:
            # Crear usuario con contraseña hasheada
            user = User.objects.create_user(
                username=username, password=password1
            )
            # Iniciar sesión automáticamente después del registro
            login(request, user)
            return redirect("accounts:profile")

    return render(request, "registration/signup.html")
```

#### Explicación

- **`User.objects.create_user(username, password)`**: A diferencia de `User.objects.create()`,
  `create_user` **hashea la contraseña** automáticamente. NUNCA guardes contraseñas en texto plano.
- Después de crear el usuario, llamamos a `login(request, user)` para que quede autenticado
  inmediatamente, sin tener que ir a login.
- Las validaciones evitan que se creen usuarios duplicados o con contraseñas que no coinciden.

---

## 7. Templates

### 7.1 base.html (template base)

Ubicación: `templates/base.html`

```html
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>{% block title %}Seguridad Acceso Django{% endblock %}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body class="bg-light">
    <nav class="navbar navbar-expand-lg navbar-dark bg-dark mb-4">
        <div class="container">
            <a class="navbar-brand" href="{% url 'home' %}">Seguridad Django</a>
            <div class="collapse navbar-collapse" id="navbarNav">
                <ul class="navbar-nav ms-auto">
                    {% if user.is_authenticated %}
                        <li class="nav-item"><a class="nav-link" href="{% url 'accounts:profile' %}">Perfil</a></li>
                        <li class="nav-item"><a class="nav-link" href="{% url 'accounts:dashboard' %}">Dashboard</a></li>
                        <li class="nav-item"><a class="nav-link" href="{% url 'accounts:logout' %}">Cerrar sesión</a></li>
                    {% else %}
                        <li class="nav-item"><a class="nav-link" href="{% url 'accounts:login' %}">Iniciar sesión</a></li>
                        <li class="nav-item"><a class="nav-link" href="{% url 'accounts:signup' %}">Registrarse</a></li>
                    {% endif %}
                </ul>
            </div>
        </div>
    </nav>

    <div class="container">
        {% if messages %}
            {% for msg in messages %}
                <div class="alert alert-{% if msg.tags %}{{ msg.tags }}{% else %}danger{% endif %}">
                    {{ msg }}
                </div>
            {% endfor %}
        {% endif %}

        {% block content %}{% endblock %}
    </div>
</body>
</html>
```

#### Explicación

- **`{{ user.is_authenticated }}`**: Esta variable está disponible gracias al context processor
  `django.contrib.auth.context_processors.auth`. Es `True` si el usuario tiene una sesión activa,
  `False` si es un `AnonymousUser`.
- **`{% url 'accounts:logout' %}`**: Genera la URL usando el nombre de la URL y el namespace de la app.
- **`{% if messages %}`**: Itera sobre los mensajes flash (definidos con `messages.error()` en las vistas).
  Los tags de Bootstrap (`alert-danger`, `alert-success`) se corresponden con los level tags de Django.

### 7.2 registration/login.html

Ubicación: `accounts/templates/registration/login.html`

```html
{% extends "base.html" %}

{% block title %}Iniciar Sesión{% endblock %}

{% block content %}
<div class="row justify-content-center">
    <div class="col-md-4">
        <div class="card shadow-sm mt-5">
            <div class="card-body p-4">
                <h2 class="text-center mb-4">Iniciar Sesión</h2>
                <form method="POST">
                    {% csrf_token %}
                    <div class="mb-3">
                        <label class="form-label">Usuario</label>
                        <input type="text" name="username" class="form-control" required>
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Contraseña</label>
                        <input type="password" name="password" class="form-control" required>
                    </div>
                    <button type="submit" class="btn btn-primary w-100">Ingresar</button>
                </form>
                <p class="mt-3 text-center">
                    ¿No tenés cuenta? <a href="{% url 'accounts:signup' %}">Registrate</a>
                </p>
            </div>
        </div>
    </div>
</div>
{% endblock %}
```

#### Explicación

- **`{% csrf_token %}`**: Genera un token CSRF oculto. Django valida este token en cada POST.
  Sin esto, Django rechaza el formulario con error 403. Es obligatorio en todo formulario con `method="POST"`.
- **`name="username"`** y **`name="password"`**: Los nombres deben coincidir con los que leemos
  en la vista: `request.POST["username"]`, `request.POST["password"]`.

### 7.3 accounts/profile.html

Ubicación: `accounts/templates/accounts/profile.html`

```html
{% extends "base.html" %}

{% block title %}Mi Perfil{% endblock %}

{% block content %}
<h2>Mi Perfil</h2>
<p>Bienvenido, {{ user.username }}.</p>
<p class="text-muted">Vía: {{ via }}</p>
{% endblock %}
```

### 7.4 accounts/dashboard.html

Ubicación: `accounts/templates/accounts/dashboard.html`

```html
{% extends "base.html" %}

{% block title %}Dashboard{% endblock %}

{% block content %}
<h2>Dashboard</h2>
<p class="text-success">¡Tienes acceso al dashboard!</p>
<p class="text-muted">Vía: {{ via }}</p>
{% endblock %}
```

### 7.5 home.html (página principal)

Ubicación: `templates/home.html`

```html
{% extends "base.html" %}

{% block content %}
<div class="row justify-content-center">
    <div class="col-md-8 text-center">
        <h1>Sistema de Autenticación Django</h1>
        {% if user.is_authenticated %}
            <p>Estás logueado como <strong>{{ user.username }}</strong>.</p>
            <div class="d-flex justify-content-center gap-2">
                <a href="{% url 'accounts:profile' %}" class="btn btn-primary">Perfil</a>
                <a href="{% url 'accounts:dashboard' %}" class="btn btn-success">Dashboard</a>
                <a href="{% url 'accounts:logout' %}" class="btn btn-danger">Cerrar sesión</a>
            </div>
        {% else %}
            <p>No has iniciado sesión.</p>
            <a href="{% url 'accounts:login' %}" class="btn btn-primary">Iniciar sesión</a>
            <a href="{% url 'accounts:signup' %}" class="btn btn-secondary">Registrarse</a>
        {% endif %}
    </div>
</div>
{% endblock %}
```

---

## 8. Protección de rutas

Django ofrece 4 formas principales de proteger rutas. Aquí cubrimos las 4:

### 8.1 @login_required (decorador para vistas función)

```python
from django.contrib.auth.decorators import login_required


@login_required
def profile_fbv_view(request):
    return render(request, "accounts/profile.html", {"via": "FBV (decorador)"})
```

#### ¿Qué hace `@login_required` por dentro?

```
1. ¿request.user.is_authenticated?
   ├── Sí → ejecuta la vista normalmente
   └── No → redirect a settings.LOGIN_URL + "?next=" + request.path
            Ejemplo: /accounts/login/?next=/accounts/profile-fbv/
```

El decorador envuelve la función. Podríamos implementarlo manualmente así:

```python
def profile_fbv_view(request):
    if not request.user.is_authenticated:
        return redirect(f"{settings.LOGIN_URL}?next={request.path}")
    return render(request, "accounts/profile.html", {"via": "FBV (decorador)"})
```

`@login_required` es simplemente azúcar sintáctica para esta verificación.

### 8.2 LoginRequiredMixin (mixin para vistas clase)

```python
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView


class ProfileView(LoginRequiredMixin, TemplateView):
    template_name = "accounts/profile.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["via"] = "CBV (LoginRequiredMixin)"
        return context
```

#### Explicación

- **`LoginRequiredMixin`**: Es una clase que se mezcla (herencia múltiple) con una vista basada en clase.
- **Orden de herencia**: `LoginRequiredMixin` debe ir a la izquierda (primero). ¿Por qué?
  Django usa el MRO (Method Resolution Order) de Python. El mixin sobreescribe `dispatch()` para
  verificar autenticación antes de que la vista ejecute su lógica.
- Si el mixin se pone a la derecha, `TemplateView.dispatch()` se ejecutaría primero y no se haría
  la verificación de autenticación.
- Funcionalmente idéntico a `@login_required`, pero para CBV.

### 8.3 @permission_required (decorador)

```python
from django.contrib.auth.decorators import login_required, permission_required


@login_required
@permission_required("accounts.can_view_dashboard", raise_exception=True)
def dashboard_fbv_view(request):
    return render(request, "accounts/dashboard.html", {"via": "FBV (decoradores)"})
```

#### Explicación

- **`"accounts.can_view_dashboard"`**: Formato `app_label.codename`. Django busca este permiso
  en la tabla `auth_permission` uniendo con `content_type`.
- **`raise_exception=True`**: En lugar de redirigir silenciosamente, lanza `PermissionDenied` (HTTP 403).
  Sin este parámetro, Django redirigiría a login (lo cual es confuso cuando ya estás autenticado).
- **Orden de los decoradores**: `@login_required` debe ir arriba (se ejecuta primero).
  Si no está autenticado, no tiene sentido verificar permisos.

#### ¿Qué hace `@permission_required` por dentro?

```
1. ¿user.has_perm("accounts.can_view_dashboard")?
   ├── True → ejecuta la vista
   └── False → raise PermissionDenied → Django busca template 403.html
```

### 8.4 PermissionRequiredMixin (mixin para vistas clase)

```python
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.views.generic import TemplateView


class DashboardView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    template_name = "accounts/dashboard.html"
    permission_required = "accounts.can_view_dashboard"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["via"] = "CBV (LoginRequiredMixin + PermissionRequiredMixin)"
        return context
```

#### Explicación

- **Orden de herencia**: `LoginRequiredMixin` → `PermissionRequiredMixin` → `TemplateView`.
  Primero se verifica autenticación y luego permiso. Si están al revés, un usuario no autenticado
  recibiría 403 en lugar de redirect a login.
- **`permission_required`**: Atributo que define qué permiso(s) se requieren. Puede ser un string
  (un solo permiso) o una lista/tupla (varios permisos, deben cumplirse todos).

---

## 9. Configuración de URLs

### seguridad_acceso_django/urls.py

```python
from django.contrib import admin
from django.urls import path, include
from django.shortcuts import render


def home_view(request):
    return render(request, "home.html")


urlpatterns = [
    path("admin/", admin.site.urls),          # Panel de administración
    path("accounts/", include("accounts.urls")),  # URLs de la app accounts
    path("", home_view, name="home"),         # Página principal
]
```

### accounts/urls.py

```python
from django.urls import path
from . import views

app_name = "accounts"  # Namespace para usar {% url 'accounts:login' %}

urlpatterns = [
    # Autenticación
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("signup/", views.signup_view, name="signup"),

    # Protegidas con decoradores (FBV)
    path("profile-fbv/", views.profile_fbv_view, name="profile-fbv"),
    path("dashboard-fbv/", views.dashboard_fbv_view, name="dashboard-fbv"),

    # Protegidas con mixins (CBV)
    path("profile/", views.ProfileView.as_view(), name="profile"),
    path("dashboard/", views.DashboardView.as_view(), name="dashboard"),
]
```

#### Explicación del namespace

- `app_name = "accounts"` define un namespace para las URLs de esta app.
- En los templates usamos `{% url 'accounts:login' %}` (formato `app_name:url_name`).
- Esto permite que diferentes apps tengan URLs con el mismo nombre sin conflicto.
- También se puede referenciar desde vistas con `redirect("accounts:login")`.

---

## 10. Manejo de 403 (accesos no autorizados)

Cuando un usuario está autenticado pero no tiene el permiso requerido, Django lanza
`PermissionDenied`. Por defecto, Django muestra una página 403 genérica, pero podemos
personalizarla.

Crear `templates/403.html`:

```html
{% extends "base.html" %}

{% block title %}Acceso Denegado{% endblock %}

{% block content %}
<div class="row justify-content-center">
    <div class="col-md-6 text-center">
        <div class="card shadow-sm mt-5 border-danger">
            <div class="card-body p-5">
                <h1 class="display-1 text-danger">403</h1>
                <h2 class="card-title text-danger">Acceso Denegado</h2>
                <p class="card-text lead">No tienes los permisos necesarios para acceder a esta página.</p>
                <p class="text-muted">Contacta al administrador si crees que esto es un error.</p>
                <a href="{% url 'home' %}" class="btn btn-primary mt-3">Volver al inicio</a>
            </div>
        </div>
    </div>
</div>
{% endblock %}
```

#### ¿Cómo encuentra Django el template 403?

1. Cuando una vista lanza `PermissionDenied`, Django busca:
   - `templates/403.html` (en las carpetas definidas en TEMPLATES.DIRS)
   - Si no existe, usa la página 403 por defecto de Django (poco amigable).
2. No necesita configuración adicional. Django busca automáticamente `403.html`.

---

## 11. Admin personalizado

En `accounts/admin.py` registramos el modelo Profile junto con el User de Django:

```python
from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin
from .models import Profile


class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = "Perfiles"


class CustomUserAdmin(UserAdmin):
    inlines = (ProfileInline,)


admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)
```

#### Explicación

- **`ProfileInline`**: Muestra el formulario de Profile embebido dentro del formulario de User.
  `StackedInline` lo muestra en vertical (uno debajo de otro), `TabularInline` lo muestra en tabla.
- **`UserAdmin`**: La clase preconstruida que Django usa para mostrar usuarios en el admin.
  Sobrescribimos `inlines` para agregar nuestro perfil.
- **`admin.site.unregister(User)`**: Django ya registra User por defecto. Debemos
  desregistrarlo antes de volver a registrarlo con nuestra versión personalizada.

---

## 12. Ejecución y verificación

### Paso 1: Migrar la base de datos

```bash
python manage.py makemigrations
python manage.py migrate
```

### Paso 2: Crear superusuario

```bash
python manage.py createsuperuser
```

Completa username, email y contraseña.

### Paso 3: Iniciar el servidor

```bash
python manage.py runserver
```

### Paso 4: Probar las rutas

| Ruta | Comportamiento esperado |
|------|------------------------|
| `http://localhost:8000/` | Página principal. Si no hay sesión, muestra "Iniciar sesión". |
| `http://localhost:8000/accounts/login/` | Formulario de login. |
| `http://localhost:8000/accounts/signup/` | Formulario de registro. |
| `http://localhost:8000/accounts/profile/` | Redirige a login si no hay sesión. Muestra perfil si está autenticado. |
| `http://localhost:8000/accounts/dashboard/` | Redirige a login si no hay sesión. Muestra 403 si no tiene permiso. Muestra dashboard si tiene permiso. |
| `http://localhost:8000/admin/` | Login de administración (solo staff). |

### Paso 5: Asignar permisos desde el admin

1. Ir a `http://localhost:8000/admin/` y loguearse como superusuario.
2. Ir a "Grupos" → "Añadir grupo" → Nombre: "Visores Dashboard" →
   Seleccionar "accounts | Profile | Puede ver el dashboard" → Guardar.
3. Ir a "Usuarios" → Seleccionar un usuario → Asignar al grupo "Visores Dashboard" → Guardar.
4. Cerrar sesión y loguearse como ese usuario → `/accounts/dashboard/` debería funcionar.

---

## Resumen de conceptos cubiertos

| Concepto | Implementación |
|----------|---------------|
| Control de accesos | `@login_required` y `LoginRequiredMixin` protegen rutas según autenticación |
| Tablas modelo Auth | `auth_user`, `auth_permission`, `auth_user_groups`, `auth_user_user_permissions` |
| Autorización y permisos | `@permission_required` y `PermissionRequiredMixin` verifican permisos específicos |
| Redirección de accesos no autorizados | `LOGIN_URL` + `?next=` para no autenticados, `403.html` para sin permiso |
| Login manual | `authenticate()` + `login()` en vista propia (FBV) |
| Logout manual | `logout()` en vista propia (FBV) |
