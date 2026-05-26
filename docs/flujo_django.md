# Flujo de Django — Sistema de Autenticación y Autorización

## Arquitectura general del proyecto

```mermaid
graph TB
    subgraph Cliente
        BROWSER[Navegador]
    end

    subgraph Django
        URL[urls.py]
        MIDDLEWARE[Middleware<br/>Session, Auth, CSRF]
        VIEWS[views.py]
        MODELS[(Modelos<br/>auth_user, Profile)]
        TEMPLATES[Template .html]
        AUTH[django.contrib.auth]
    end

    BROWSER -->|HTTP Request| MIDDLEWARE
    MIDDLEWARE -->|Resuelve ruta| URL
    URL -->|Llama a la vista| VIEWS
    VIEWS -->|authenticate / login / logout| AUTH
    AUTH -->|Consulta / Escribe| MODELS
    VIEWS -->|Renderiza| TEMPLATES
    TEMPLATES -->|HTTP Response| BROWSER
```

---

## 1. Flujo de Login (`/accounts/login/`)

```mermaid
sequenceDiagram
    actor U as Usuario
    participant N as Navegador
    participant D as Django (URL → View → Auth → Template)
    participant DB as Base de Datos (auth_user)

    Note over U,DB: GET /accounts/login/
    U->>N: Accede a /accounts/login/
    N->>D: GET /accounts/login/
    D->>D: urls.py → accounts/urls.py → login_view
    D->>D: request.method != "POST" → render(login.html)
    D-->>N: Página con formulario login
    N-->>U: Formulario HTML

    Note over U,DB: POST /accounts/login/ (envía credenciales)
    U->>N: Completa usuario/contraseña y hace submit
    N->>D: POST /accounts/login/<br/>(username + password)
    D->>D: urls.py → accounts/urls.py → login_view
    D->>D: authenticate(request, username, password)
    D->>DB: SELECT * FROM auth_user WHERE username = ?
    DB-->>D: User object o None
    alt Credenciales correctas
        D->>D: login(request, user) → crea sesión
        D->>D: Lee ?next= o redirige a "/"
        D-->>N: Redirect 302 a next o "/"
        N-->>U: Página de inicio logueado
    else Credenciales incorrectas
        D->>D: messages.error("Usuario o contraseña incorrectos")
        D-->>N: render(login.html) con mensaje de error
        N-->>U: Formulario con error visible
    end
```

### Login — Ruta por archivos

```mermaid
graph LR
    A[urls.py proyecto] -->|path accounts/| B[accounts/urls.py]
    B -->|path login/| C[accounts/views.py<br/>login_view]
    C -->|authenticate| D[django.contrib.auth]
    D -->|consulta| E[(auth_user)]
    C -->|render| F[accounts/templates/<br/>registration/login.html]
    F -->|HTTP Response| G[Navegador]
```

---

## 2. Flujo de Logout (`/accounts/logout/`)

```mermaid
sequenceDiagram
    actor U as Usuario (logueado)
    participant N as Navegador
    participant D as Django (URL → View)
    participant S as Sesión

    U->>N: Hace clic en "Cerrar sesión"
    N->>D: GET /accounts/logout/
    D->>D: urls.py → accounts/urls.py → logout_view
    D->>D: logout(request)
    D->>S: Elimina datos de sesión
    D-->>N: Redirect 302 a /accounts/login/
    N-->>U: Página de login
```

---

## 3. Flujo de Registro (`/accounts/signup/`)

```mermaid
sequenceDiagram
    actor U as Usuario nuevo
    participant N as Navegador
    participant D as Django (URL → View → Auth)
    participant DB as Base de Datos

    U->>N: GET /accounts/signup/
    N->>D: GET /accounts/signup/
    D->>D: signup_view → render(signup.html)
    D-->>N: Formulario de registro
    N-->>U: Formulario

    U->>N: Completa datos y hace submit
    N->>D: POST /accounts/signup/<br/>(username + password1 + password2)
    D->>D: Valida contraseñas coinciden
    D->>DB: Verifica si username existe
    alt Contraseñas no coinciden
        D->>D: messages.error
        D-->>N: render(signup.html) con error
    else Username ya existe
        D->>D: messages.error
        D-->>N: render(signup.html) con error
    else Éxito
        D->>D: User.objects.create_user(username, password)
        D->>DB: INSERT INTO auth_user ...
        D->>D: login(request, user) → sesión iniciada
        D-->>N: Redirect 302 a /accounts/profile/
        N-->>U: Perfil del nuevo usuario
    end
```

---

## 4. Flujo Perfil — CBV con `LoginRequiredMixin` (`/accounts/profile/`)

```mermaid
sequenceDiagram
    actor U as Usuario
    participant N as Navegador
    participant D as Django
    participant M as LoginRequiredMixin

    U->>N: GET /accounts/profile/
    N->>D: GET /accounts/profile/
    D->>D: urls.py → ProfileView.as_view()
    D->>M: Verifica request.user.is_authenticated
    alt No autenticado
        M->>D: Redirige a LOGIN_URL + ?next=/accounts/profile/
        D-->>N: Redirect 302 a /accounts/login/?next=/accounts/profile/
        N-->>U: Página de login
    else Autenticado
        M->>D: Continúa a ProfileView
        D->>D: get_context_data() → añade {{ via }}
        D->>D: render(profile.html)
        D-->>N: Página de perfil
        N-->>U: Perfil del usuario
    end
```

### LoginRequiredMixin — decisión interna

```mermaid
flowchart TD
    A[ProfileView<br/>LoginRequiredMixin] --> B{request.user<br/>is_authenticated?}
    B -->|No| C[Redirige a<br/>/accounts/login/?next=<ruta_original>]
    B -->|Sí| D[T <br/> TemplateView]
    D --> E[Renderiza<br/>profile.html]
```

---

## 5. Flujo Dashboard — CBV con `LoginRequiredMixin` + `PermissionRequiredMixin` (`/accounts/dashboard/`)

```mermaid
sequenceDiagram
    actor U as Usuario
    participant N as Navegador
    participant D as Django
    participant LM as LoginRequiredMixin
    participant PM as PermissionRequiredMixin

    U->>N: GET /accounts/dashboard/
    N->>D: GET /accounts/dashboard/
    D->>D: urls.py → DashboardView.as_view()
    D->>LM: Verifica autenticación
    alt No autenticado
        LM->>D: Redirect a login con ?next=
        D-->>N: Redirect 302
        N-->>U: Login
    else Autenticado
        LM->>PM: Verifica permiso accounts.can_view_dashboard
        PM->>DB: SELECT FROM auth_user_user_permissions JOIN auth_permission
        DB-->>PM: Tiene permiso o no
        alt Sin permiso
            PM->>D: raise PermissionDenied → 403.html
            D-->>N: HTTP 403 Forbidden
            N-->>U: Página 403 - Acceso Denegado
        else Con permiso
            PM->>D: Continúa a DashboardView
            D->>D: render(dashboard.html)
            D-->>N: Página de dashboard
            N-->>U: Dashboard con datos
        end
    end
```

### PermissionRequiredMixin — decisión interna

```mermaid
flowchart TD
    A[DashboardView<br/>LoginRequiredMixin + PermissionRequiredMixin] --> B{request.user<br/>is_authenticated?}
    B -->|No| C[Redirect a login]
    B -->|Sí| D{user.has_perm<br/>can_view_dashboard?}
    D -->|No| E[raise PermissionDenied<br/>HTTP 403]
    D -->|Sí| F[TemplateView]
    E --> G[Renderiza 403.html]
    F --> H[Renderiza dashboard.html]
```

---

## 6. Flujo Perfil — FBV con `@login_required` (`/accounts/profile-fbv/`)

```mermaid
sequenceDiagram
    actor U as Usuario
    participant N as Navegador
    participant D as Django
    participant Dec as @login_required

    U->>N: GET /accounts/profile-fbv/
    N->>D: GET /accounts/profile-fbv/
    D->>Dec: Verifica request.user.is_authenticated
    alt No autenticado
        Dec->>D: Redirige a login + ?next=
    else Autenticado
        Dec->>D: Ejecuta profile_fbv_view
        D->>D: render(profile.html, via="FBV (decorador)")
        D-->>N: Página de perfil
    end
```

---

## 7. Flujo Dashboard — FBV con `@login_required` + `@permission_required` (`/accounts/dashboard-fbv/`)

```mermaid
sequenceDiagram
    actor U as Usuario
    participant N as Navegador
    participant D as Django
    participant L as @login_required
    participant P as @permission_required

    U->>N: GET /accounts/dashboard-fbv/
    N->>D: GET /accounts/dashboard-fbv/
    D->>L: Verifica autenticación
    alt No autenticado
        L->>D: Redirect a login
    else Autenticado
        L->>P: Verifica permiso
        P->>DB: Consulta auth_user_user_permissions
        alt Sin permiso
            P->>D: raise PermissionDenied → 403
        else Con permiso
            P->>D: Ejecuta dashboard_fbv_view
            D->>D: render(dashboard.html, via="FBV (decoradores)")
            D-->>N: Dashboard
        end
    end
```

---

## 8. Mapa completo de rutas

```mermaid
graph TB
    subgraph Proyecto [seguridad_acceso_django/urls.py]
        R1[admin/] --> Admin
        R2[accounts/] --> AccountsURL
        R3["/ (vacío)"] --> HomeView
    end

    subgraph Accounts [accounts/urls.py]
        L1[login/] --> LoginView
        L2[logout/] --> LogoutView
        L3[signup/] --> SignupView
        L4[profile/] --> ProfileCBV
        L5[profile-fbv/] --> ProfileFBV
        L6[dashboard/] --> DashboardCBV
        L7[dashboard-fbv/] --> DashboardFBV
    end

    subgraph Views [accounts/views.py]
        LoginView[login_view] -->|POST| Auth[authenticate]
        LoginView -->|GET| TplLogin[login.html]
        LogoutView[logout_view] -->|Llama| Logout[logout]
        SignupView[signup_view] -->|POST| CreateUser[User.objects.create_user]
        CreateUser --> LoginAfter[login + redirect]
        ProfileCBV[ProfileView] -->|LoginRequiredMixin| TplProfile[profile.html]
        ProfileFBV[profile_fbv_view] -->|@login_required| TplProfile
        DashboardCBV[DashboardView] -->|LoginRequiredMixin + PermissionRequiredMixin| TplDash[dashboard.html]
        DashboardFBV[dashboard_fbv_view] -->|@login_required + @permission_required| TplDash
    end

    subgraph Templates [Templates]
        TplLogin
        TplProfile
        TplDash
        HomeView --> Home[home.html]
        Error403[403.html]
    end
```

---

## 9. Tabla de protección por ruta

| Ruta | Tipo | Protección | Qué pasa si no está autorizado |
|------|------|-----------|-------------------------------|
| `/` | Pública | — | — |
| `/accounts/signup/` | Pública | — | — |
| `/accounts/login/` | Pública | — | — |
| `/accounts/logout/` | Pública | — | — |
| `/accounts/profile/` | CBV | `LoginRequiredMixin` | Redirect a `/accounts/login/?next=/accounts/profile/` |
| `/accounts/profile-fbv/` | FBV | `@login_required` | Redirect a `/accounts/login/?next=/accounts/profile-fbv/` |
| `/accounts/dashboard/` | CBV | `LoginRequiredMixin` + `PermissionRequiredMixin` | No auth → redirect login. Sin permiso → HTTP 403 con `403.html` |
| `/accounts/dashboard-fbv/` | FBV | `@login_required` + `@permission_required` | No auth → redirect login. Sin permiso → HTTP 403 con `403.html` |
| `/admin/` | Django Admin | `is_staff` | Redirect a login admin |

---

## 10. Modelo de datos (Auth)

```mermaid
erDiagram
    auth_user ||--o{ auth_user_user_permissions : tiene
    auth_user ||--o{ auth_user_groups : pertenece
    auth_user ||--o| accounts_profile : extiende
    auth_group ||--o{ auth_group_permissions : tiene
    auth_group }o--o{ auth_user_groups : agrupa
    auth_permission ||--o{ auth_user_user_permissions : asignado
    auth_permission ||--o{ auth_group_permissions : asignado

    auth_user {
        int id PK
        varchar username
        varchar password
        varchar email
        bool is_staff
        bool is_superuser
        bool is_active
    }

    accounts_profile {
        int id PK
        int user_id FK
        text bio
    }

    auth_permission {
        int id PK
        varchar codename
        varchar name
        int content_type_id FK
    }

    auth_group {
        int id PK
        varchar name
    }

    auth_user_user_permissions {
        int user_id FK
        int permission_id FK
    }
```

---

## 11. Ciclo completo de un request protegido (ej: Dashboard CBV)

```mermaid
flowchart LR
    REQ[Request del usuario] -->|HTTP| WSGI[WSGI / manage.py]
    WSGI --> MIDDLEWARE1[SecurityMiddleware]
    MIDDLEWARE1 --> MIDDLEWARE2[SessionMiddleware]
    MIDDLEWARE2 --> MIDDLEWARE3[CommonMiddleware]
    MIDDLEWARE3 --> MIDDLEWARE4[CsrfViewMiddleware]
    MIDDLEWARE4 --> MIDDLEWARE5[AuthMiddleware<br/>request.user disponible]
    MIDDLEWARE5 --> MIDDLEWARE6[MessageMiddleware]
    MIDDLEWARE6 --> URL_RESOLVER[URL resolver<br/>- seguridad_acceso_django/urls.py<br/>- accounts/urls.py]
    URL_RESOLVER --> VIEW[DashboardView<br/>accounts/views.py]

    VIEW --> CHECK_AUTH{LoginRequiredMixin<br/>user.is_authenticated?}
    CHECK_AUTH -->|No| REDIRECT[Redirect 302<br/>/accounts/login/?next=/dashboard/]
    REDIRECT --> RESPONSE[HTTP Response]

    CHECK_AUTH -->|Sí| CHECK_PERM{PermissionRequiredMixin<br/>user.has_perm?}
    CHECK_PERM -->|No| PERM_DENIED[PermissionDenied<br/>HTTP 403]
    PERM_DENIED --> RENDER_403[Render 403.html]
    RENDER_403 --> RESPONSE

    CHECK_PERM -->|Sí| GET[get_context_data]
    GET --> RENDER[Render dashboard.html]
    RENDER --> RESPONSE
    RESPONSE -->|HTTP Response| USER[Usuario ve la página]
```

---

## 12. Resumen de conceptos cubiertos

| Concepto | Dónde se implementa |
|---|---|
| Control de accesos | `LoginRequiredMixin` en `ProfileView` y `@login_required` en `profile_fbv_view` |
| Tablas modelo Auth | `auth_user`, `auth_permission`, `auth_user_user_permissions` usadas vía Django ORM |
| Autorización y permisos | `PermissionRequiredMixin` en `DashboardView` y `@permission_required` en `dashboard_fbv_view` |
| Redirección de accesos no autorizados | `LOGIN_URL` en `settings.py` + redirect con `?next=` + template `403.html` |
| `LoginRequiredMixin` | `accounts/views.py:49` — `class ProfileView(LoginRequiredMixin, TemplateView)` |
| `PermissionRequiredMixin` | `accounts/views.py:55` — `class DashboardView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView)` |
| Login manual | `login_view` sin usar `LoginView` genérico de Django |
| Logout manual | `logout_view` sin usar `LogoutView` genérico de Django |
