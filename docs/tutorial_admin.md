# Tutorial — Sitio Administrativo de Django

Este tutorial cubre el uso del sitio administrativo de Django para gestionar usuarios, grupos y
permisos, utilizando el proyecto `seguridad_acceso_django` desarrollado en la actividad anterior.

---

## Índice

1. [¿Qué es el sitio administrativo de Django?](#1-qué-es-el-sitio-administrativo-de-django)
2. [El modelo Auth por dentro](#2-el-modelo-auth-por-dentro)
3. [Jerarquía de permisos en Django](#3-jerarquía-de-permisos-en-django)
4. [Tipos de permisos estándar y personalizados](#4-tipos-de-permisos-estándar-y-personalizados)
5. [Creación del superusuario](#5-creación-del-superusuario)
6. [Registro de modelos en admin.py](#6-registro-de-modelos-en-adminpy)
7. [Flujo: Crear un grupo con permisos](#7-flujo-crear-un-grupo-con-permisos)
8. [Flujo: Crear un usuario y asignarlo a un grupo](#8-flujo-crear-un-usuario-y-asignarlo-a-un-grupo)
9. [Flujo: Asignar permiso individual (sin grupo)](#9-flujo-asignar-permiso-individual-sin-grupo)
10. [Prueba práctica](#10-prueba-práctica)
11. [Verificación desde la shell de Django](#11-verificación-desde-la-shell-de-django)
12. [Flujo completo de autorización en Django](#12-flujo-completo-de-autorización-en-django)
13. [Preguntas frecuentes](#13-preguntas-frecuentes)

---

## 1. ¿Qué es el sitio administrativo de Django?

El sitio administrativo (o **admin**) de Django es una interfaz web generada automáticamente a partir
de los modelos registrados. Permite realizar operaciones CRUD (Crear, Leer, Actualizar, Eliminar)
sobre los datos sin escribir una sola línea de HTML.

### Características principales

- **Generación automática**: Al registrar un modelo, el admin genera formularios, listados y vistas
  de detalle automáticamente.
- **Autenticación integrada**: Usa el sistema `django.contrib.auth`. Solo usuarios con
  `is_staff=True` pueden acceder.
- **Gestion de permisos**: Control granular sobre qué puede ver/editar cada usuario.
- **Gestion de grupos**: Permite agrupar permisos en roles.

### ¿Qué apps proveen el admin?

El admin depende de estas apps en `INSTALLED_APPS`:

```python
INSTALLED_APPS = [
    "django.contrib.admin",          # El admin en sí mismo
    "django.contrib.auth",           # Modelos User, Group, Permission
    "django.contrib.contenttypes",   # Necesario para los permisos (ContentType)
    "django.contrib.sessions",       # Sesiones para mantener login en admin
    "django.contrib.messages",       # Mensajes flash en el admin
]
```

---

## 2. El modelo Auth por dentro

El sistema de autenticación de Django se basa en varias tablas de base de datos.
Veamos cada una en detalle.

### 2.1 auth_user — La tabla de usuarios

Cada usuario registrado en el sistema tiene una fila aquí.

| Columna | Tipo SQL | Descripción |
|---------|----------|-------------|
| `id` | INTEGER (PK) | Identificador único autogenerado |
| `username` | VARCHAR(150) | Nombre de usuario único |
| `password` | VARCHAR(128) | Hash de la contraseña (PBKDF2/SHA256 por defecto) |
| `email` | VARCHAR(254) | Correo electrónico |
| `first_name` | VARCHAR(150) | Nombre |
| `last_name` | VARCHAR(150) | Apellido |
| `is_staff` | BOOLEAN | Puede acceder al sitio administrativo |
| `is_superuser` | BOOLEAN | Tiene todos los permisos sin verificación |
| `is_active` | BOOLEAN | Puede iniciar sesión (login) |
| `date_joined` | DATETIME | Fecha de registro |
| `last_login` | DATETIME | Último inicio de sesión |

```sql
-- Ejemplo de inserción (Django lo hace automáticamente)
INSERT INTO auth_user (username, password, is_staff, is_superuser, is_active, date_joined)
VALUES ('admin', 'pbkdf2_sha256$...', 1, 1, 1, '2025-01-01 00:00:00');
```

### 2.2 auth_group — La tabla de grupos

Los grupos son colecciones de permisos. Sirven para definir roles.

| Columna | Tipo SQL | Descripción |
|---------|----------|-------------|
| `id` | INTEGER (PK) | Identificador único |
| `name` | VARCHAR(150) | Nombre del grupo (único) |

### 2.3 auth_permission — La tabla de permisos

Cada permiso disponible en el sistema tiene una fila aquí.

| Columna | Tipo SQL | Descripción |
|---------|----------|-------------|
| `id` | INTEGER (PK) | Identificador único |
| `name` | VARCHAR(255) | Nombre legible (ej: "Puede ver el dashboard") |
| `content_type_id` | INTEGER (FK) | Referencia al modelo (tabla django_content_type) |
| `codename` | VARCHAR(100) | Identificador interno (ej: `can_view_dashboard`) |

### 2.4 django_content_type — La tabla de tipos de contenido

Cada modelo registrado en el proyecto tiene una fila aquí.
Es la tabla que relaciona permisos con modelos.

| Columna | Tipo SQL | Descripción |
|---------|----------|-------------|
| `id` | INTEGER (PK) | Identificador único |
| `app_label` | VARCHAR(100) | Nombre de la app (ej: `accounts`) |
| `model` | VARCHAR(100) | Nombre del modelo (ej: `profile`) |

### 2.5 Tablas intermedias (relaciones muchos a muchos)

#### auth_user_groups — Usuarios que pertenecen a grupos

| Columna | Tipo SQL |
|---------|----------|
| `user_id` | INTEGER (FK → auth_user.id) |
| `group_id` | INTEGER (FK → auth_group.id) |

#### auth_user_user_permissions — Permisos asignados directamente a usuarios

| Columna | Tipo SQL |
|---------|----------|
| `user_id` | INTEGER (FK → auth_user.id) |
| `permission_id` | INTEGER (FK → auth_permission.id) |

#### auth_group_permissions — Permisos asignados a grupos

| Columna | Tipo SQL |
|---------|----------|
| `group_id` | INTEGER (FK → auth_group.id) |
| `permission_id` | INTEGER (FK → auth_permission.id) |

### 2.6 Visualización de las relaciones

```
auth_user (Usuarios)
    │
    ├───< auth_user_groups >─── auth_group (Grupos)
    │                                │
    │                                └───< auth_group_permissions >───┐
    │                                                                 │
    └───< auth_user_user_permissions >────────────────────────────────┤
                                                                      │
                                                          auth_permission (Permisos)
                                                               │
                                                          django_content_type (Modelos)
```

---

## 3. Jerarquía de permisos en Django

### 3.1 ¿Cómo decide Django si un usuario tiene permiso?

Cuando en el código se ejecuta `user.has_perm("accounts.can_view_dashboard")`,
Django sigue este flujo:

```
user.has_perm("accounts.can_view_dashboard")
         │
         ├── ¿user.is_superuser es True?
         │   ├── SÍ → Retorna True inmediatamente.
         │   │         No consulta la BD. El superusuario tiene TODO.
         │   │
         │   └── NO → Continúa con la verificación.
         │
         ├── Buscar en auth_user_user_permissions
         │   ├── ¿Existe un registro con este user_id y permission.codename?
         │   │   ├── SÍ → Retorna True (permiso individual)
         │   │   └── NO → Continúa
         │
         ├── Buscar en auth_user_groups → auth_group_permissions
         │   ├── Obtener todos los grupos del usuario
         │   ├── Obtener todos los permisos de esos grupos
         │   ├── ¿El permiso solicitado está en esa lista?
         │   │   ├── SÍ → Retorna True (permiso vía grupo)
         │   │   └── NO → Retorna False
         │
         └── Retorna False
```

### 3.2 Ejemplo concreto con SQL

Para un usuario `juan` (id=1) que pertenece al grupo `Visores` (id=2) y el grupo tiene
el permiso `can_view_dashboard` (content_type_id=5, codename='can_view_dashboard'):

```sql
-- 1. Django busca permisos directos del usuario
SELECT * FROM auth_user_user_permissions WHERE user_id = 1;
-- (vacío — no tiene permisos individuales)

-- 2. Django busca los grupos del usuario
SELECT group_id FROM auth_user_groups WHERE user_id = 1;
-- Resultado: (2)

-- 3. Django busca permisos de esos grupos
SELECT * FROM auth_group_permissions WHERE group_id = 2;
-- Resultado: (group_id=2, permission_id=10)

-- 4. Django verifica si el permiso coincide
SELECT * FROM auth_permission WHERE id = 10 AND codename = 'can_view_dashboard';
-- Resultado: (id=10, codename='can_view_dashboard') → ¡Coincide!
-- → Retorna True
```

### 3.3 ¿Los permisos se acumulan?

SÍ. Los permisos de TODAS las fuentes (individuales + grupos) se combinan en un solo conjunto.
```python
user.has_perm("permiso_a")  # True si está en individuales O en algún grupo
```

No importa de dónde venga el permiso. Si existe en al menos una fuente, `has_perm()` retorna True.

---

## 4. Tipos de permisos estándar y personalizados

### 4.1 Permisos estándar (se crean automáticamente)

Por cada modelo registrado, Django crea 4 permisos estándar al ejecutar `migrate`:

| Permiso | Codename | Qué permite |
|---------|----------|-------------|
| Can add | `add_<modelo>` | Crear un nuevo registro |
| Can change | `change_<modelo>` | Editar un registro existente |
| Can delete | `delete_<modelo>` | Eliminar un registro |
| Can view | `view_<modelo>` | Ver un registro |

Ejemplo para nuestro modelo `Profile` (app `accounts`):

| Codename | Name |
|----------|------|
| `accounts.add_profile` | Can add Profile |
| `accounts.change_profile` | Can change Profile |
| `accounts.delete_profile` | Can delete Profile |
| `accounts.view_profile` | Can view Profile |

### 4.2 Permisos personalizados (se definen en el modelo)

En `accounts/models.py` definimos un permiso adicional en la clase `Meta`:

```python
class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    bio = models.TextField(blank=True)

    class Meta:
        permissions = [
            ("can_view_dashboard", "Puede ver el dashboard"),
        ]
```

Esto genera un quinto permiso:

| Codename | Name |
|----------|------|
| `accounts.can_view_dashboard` | Puede ver el dashboard |

### 4.3 ¿Dónde se almacenan?

En la tabla `auth_permission` se vería así:

```
id | name                      | content_type_id | codename
---|---------------------------|-----------------|----------------------------
1  | Can add profile           | 5               | add_profile
2  | Can change profile        | 5               | change_profile
3  | Can delete profile        | 5               | delete_profile
4  | Can view profile          | 5               | view_profile
5  | Puede ver el dashboard    | 5               | can_view_dashboard
```

Donde `content_type_id = 5` corresponde a `accounts | profile` en `django_content_type`.

---

## 5. Creación del superusuario

### 5.1 Comando

```bash
python manage.py createsuperuser
```

### 5.2 Interacción

```
Username: admin
Email address: admin@example.com
Password: ********
Password (again): ********
Superuser created successfully.
```

### 5.3 ¿Qué pasa internamente?

Cuando ejecutás `createsuperuser`, Django hace lo siguiente:

1. Pide username, email y password.
2. Crea un registro en `auth_user` con:
   - `username = "admin"`
   - `password = pbkdf2_sha256$...` (NUNCA texto plano)
   - `email = "admin@example.com"`
   - `is_staff = True` → Puede acceder al admin
   - `is_superuser = True` → Tiene todos los permisos
   - `is_active = True` → Puede iniciar sesión
3. Guarda en la BD.

### 5.4 ¿Por qué el superusuario no necesita permisos explícitos?

Porque `is_superuser=True` hace que Django retorne `True` en TODAS las verificaciones
de permisos sin consultar la BD. Es una puerta de acceso total.

### 5.5 ¿Cuántos superusuarios puedo tener?

Todos los que necesites. No hay límite. Puedes crear múltiples superusuarios.

### 5.6 Alternativa: crear superusuario desde la shell

```python
python manage.py shell
>>> from django.contrib.auth.models import User
>>> User.objects.create_superuser("admin2", "admin2@example.com", "password123")
```

---

## 6. Registro de modelos en admin.py

Para que un modelo aparezca en el admin, debe estar registrado en `accounts/admin.py`.

### 6.1 Registro básico

```python
from django.contrib import admin
from .models import Profile

admin.site.register(Profile)
```

Esto muestra Profile como una sección independiente en el admin.

### 6.2 Registro avanzado (inline dentro de User)

```python
from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin
from .models import Profile


class ProfileInline(admin.StackedInline):
    """Muestra el formulario de Profile embebido dentro del User."""
    model = Profile
    can_delete = False          # No permite eliminar desde el inline
    verbose_name_plural = "Perfiles"


class CustomUserAdmin(UserAdmin):
    """UserAdmin personalizado que incluye ProfileInline."""
    inlines = (ProfileInline,)


# Desregistrar User (ya registrado por defecto) y volver a registrar
admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)
```

#### Explicación línea por línea

- **`ProfileInline`**: Clase que define cómo se muestra el modelo Profile dentro de User.
  - `model = Profile`: El modelo a incluir.
  - `can_delete = False`: Oculta el checkbox "Eliminar" en el inline.
  - `StackedInline`: Muestra los campos en vertical (uno abajo del otro).
    Alternativa: `TabularInline` (formato tabla horizontal).
- **`CustomUserAdmin`**: Extiende `UserAdmin` (la clase que Django usa para mostrar usuarios).
  - `inlines = (ProfileInline,)`: Lista de inlines a mostrar.
- **`admin.site.unregister(User)`**: Django ya registra User automáticamente.
  Para cambiarlo, primero lo desregistramos.
- **`admin.site.register(User, CustomUserAdmin)`**: Lo registramos con nuestra versión.

### 6.3 Resultado visual en el admin

En `/admin/auth/user/1/change/` ahora verás:

```
Usuario: admin
├── [Detalles del usuario]  ← campos estándar
├── [Permisos]              ← grupos y permisos
├── [Fechas importantes]    ← date_joined, last_login
└── [Perfiles]              ← nuestro ProfileInline (campo "bio")
```

---

## 7. Flujo: Crear un grupo con permisos

### 7.1 ¿Qué es un grupo?

Un **grupo** es una colección de permisos. Sirve para definir **roles**:

- "Visores de Dashboard" → permiso `can_view_dashboard`
- "Editores" → permisos `add_profile`, `change_profile`, `view_profile`
- "Administradores" → todos los permisos de accounts

La ventaja de los grupos es que asignás un usuario a un grupo y automáticamente
hereda todos los permisos del grupo, sin tener que asignarlos uno por uno.

### 7.2 Paso a paso

1. Ir a `http://localhost:8000/admin/`.
2. Loguearse como superusuario.
3. Ir a **"Autenticación y Autorización" → "Grupos"**.

   ```
   Admin
   └── Autenticación y Autorización
       ├── Grupos        ← aquí
       └── Usuarios
   └── Accounts
       └── Perfiles
   ```

4. Hacer clic en **"Añadir grupo"** (botón superior derecho).

5. Completar:
   - **Nombre**: `Visores de Dashboard`

6. En **"Permisos disponibles"**, filtrar escribiendo `dashboard`:

   ```
   accounts | Profile | Puede ver el dashboard
   ```

7. Seleccionar el permiso y hacer clic en la flecha derecha (→) para pasarlo a
   **"Permisos escogidos"**.

8. Hacer clic en **"Guardar"**.

### 7.3 ¿Qué pasó en la base de datos?

```sql
-- 1. Se insertó el grupo
INSERT INTO auth_group (name) VALUES ('Visores de Dashboard');
-- id = 1

-- 2. Se vinculó el permiso al grupo
INSERT INTO auth_group_permissions (group_id, permission_id)
VALUES (1, <id_del_permiso_can_view_dashboard>);
```

### 7.4 Verificar desde la shell

```python
python manage.py shell
>>> from django.contrib.auth.models import Group, Permission
>>> group = Group.objects.get(name="Visores de Dashboard")
>>> group.permissions.all()
# <QuerySet [<Permission: accounts | Profile | Puede ver el dashboard>]>
>>> group.permissions.values_list("codename", flat=True)
# <QuerySet ['can_view_dashboard']>
```

---

## 8. Flujo: Crear un usuario y asignarlo a un grupo

### 8.1 Paso a paso

1. Ir a **"Autenticación y Autorización" → "Usuarios"**.
2. Hacer clic en **"Añadir usuario"**.

3. Completar los campos obligatorios:
   - **Username**: `juan_perez`
   - **Password**: `********`
   - **Confirmación**: `********`

4. Hacer clic en **"Guardar"**.

   > **Importante**: En este punto Django solo guardó los datos básicos.
   > Ahora se abre un formulario detallado con todas las opciones.

5. En el formulario detallado:

   #### Pestaña "Detalles del usuario"
   - **Nombre**: `Juan`
   - **Apellido**: `Pérez`
   - **Email**: `juan@example.com`

   #### Pestaña "Permisos"

   | Campo | Valor | Explicación |
   |-------|-------|-------------|
   | **Activo** | ☑ | Puede iniciar sesión. Si está desactivado, no puede loguearse. |
   | **Staff** | ☐ | No necesita acceder al admin. Solo usará la web pública. |
   | **Superusuario** | ☐ | No debe tener todos los permisos. |
   | **Grupos** | Seleccionar "Visores de Dashboard" | Heredará el permiso `can_view_dashboard`. |
   | **Permisos de usuario** | (vacío) | No necesita permisos individuales adicionales. |

   > **Aclaración sobre Staff**: `is_staff=True` solo es necesario para acceder al panel `/admin/`.
   > Para que `@login_required` y `PermissionRequiredMixin` funcionen en las vistas públicas,
   > solo se requiere `is_active=True`. El usuario juan_perez podrá loguearse en `/accounts/login/`
   > y acceder a `/accounts/dashboard/` sin ser staff.

6. Hacer clic en **"Guardar"**.

### 8.2 ¿Qué pasó en la base de datos?

```sql
-- 1. Se insertó el usuario
INSERT INTO auth_user (username, password, is_staff, is_superuser, is_active, date_joined)
VALUES ('juan_perez', 'pbkdf2_sha256$...', 0, 0, 1, '2025-01-01 00:00:00');

-- 2. Se vinculó el usuario al grupo
INSERT INTO auth_user_groups (user_id, group_id)
VALUES (<user_id>, <group_id_del_grupo_Visores>);
```

### 8.3 Verificar desde la shell

```python
python manage.py shell
>>> from django.contrib.auth.models import User
>>> user = User.objects.get(username="juan_perez")
>>> user.groups.all()
# <QuerySet [<Group: Visores de Dashboard>]>
>>> user.has_perm("accounts.can_view_dashboard")
# True
>>> user.get_group_permissions()
# {'accounts.can_view_dashboard'}
>>> user.is_staff
# False  ← no necesita ser staff para el dashboard público
>>> user.is_superuser
# False
```

### 8.4 ¿Qué pasa si agrego un permiso a un grupo después de asignar usuarios?

Los usuarios existentes heredan el nuevo permiso automáticamente.
No necesitas volver a guardarlos ni reasignarlos. La verificación es
**en tiempo real** (cada vez que se ejecuta `has_perm()`).

```python
# 1. Crear grupo sin permisos
# 2. Asignar juan_perez al grupo
# 3. Más tarde, agregar can_view_dashboard al grupo
# 4. Juan Pérez YA tiene el permiso sin necesidad de reasignarlo
```

---

## 9. Flujo: Asignar permiso individual (sin grupo)

A veces necesitás dar un permiso específico a un usuario sin crear un grupo completo.
Esto se hace en "Permisos de usuario".

### 9.1 ¿Cuándo usar permisos individuales?

- **Excepciones**: Un usuario necesita un permiso extra que su grupo no tiene.
- **Usuarios sin grupo**: Cuando querés asignar permisos uno por uno.
- **Casos específicos**: Un permiso que solo aplica a 1 o 2 usuarios.

### 9.2 Paso a paso

1. Ir a **"Usuarios"** → seleccionar un usuario (ej: `maria_garcia`).
2. Ir a la pestaña **"Permisos"**.
3. En **"Permisos de usuario"**, buscar `can_view_dashboard`:

   ```
   accounts | Profile | Puede ver el dashboard
   ```

4. Seleccionarlo y pasarlo a "Permisos escogidos" con la flecha (→).
5. Hacer clic en **"Guardar"**.

### 9.3 ¿Qué pasó en la base de datos?

```sql
INSERT INTO auth_user_user_permissions (user_id, permission_id)
VALUES (<user_id>, <id_del_permiso_can_view_dashboard>);
```

### 9.4 Diferencia entre grupo e individual

| Aspecto | Grupo | Individual |
|---------|-------|------------|
| Mantenimiento | Centralizado: cambiás el grupo y todos lo heredan | Hay que editar cada usuario |
| Escalabilidad | Ideal para roles (5, 50, 500 usuarios) | Solo para casos puntuales |
| Claridad | Sabés el rol del usuario de un vistazo | Más difícil de auditar |
| Cuándo usarlo | "Todos los visores" | "María necesita ver esto" |

### 9.5 Mezclar grupo + individual

Se puede perfectamente. Los permisos se **acumulan**:

```python
# Usuario en grupo "Visores" + permiso individual "add_profile"
user.get_all_permissions()
# {'accounts.can_view_dashboard', 'accounts.add_profile'}
```

---

## 10. Prueba práctica

### 10.1 Escenario 1: Usuario sin permiso → 403

**Objetivo**: Verificar que un usuario sin `can_view_dashboard` recibe error 403.

**Pasos**:

1. En el admin, crear usuario `test_user`:
   - Staff: NO
   - Superusuario: NO
   - Activo: SÍ
   - Grupos: ninguno
   - Permisos individuales: ninguno

2. Abrir una ventana de incógnito o cerrar sesión.

3. Ir a `/accounts/login/` y loguearse como `test_user`.

4. Ir a `/accounts/dashboard/`.

**Resultado esperado**:

```
┌────────────────────────────────────┐
│         403 Acceso Denegado        │
│                                    │
│  No tienes los permisos necesarios │
│  para acceder a esta página.       │
│                                    │
│  [Volver al inicio]                │
└────────────────────────────────────┘
```

**Explicación**: El `PermissionRequiredMixin` en `DashboardView` ejecuta
`user.has_perm("accounts.can_view_dashboard")`, que retorna `False`.
Entonces lanza `PermissionDenied` y Django renderiza `templates/403.html`.

### 10.2 Escenario 2: Usuario con permiso vía grupo → Dashboard

**Objetivo**: Verificar que un usuario asignado al grupo "Visores de Dashboard"
ve el dashboard correctamente.

**Pasos**:

1. Crear usuario `visor1`:
   - Staff: NO
   - Superusuario: NO
   - Activo: SÍ
   - Grupos: "Visores de Dashboard"
   - Permisos individuales: ninguno

2. Cerrar sesión y loguearse como `visor1`.

3. Ir a `/accounts/dashboard/`.

**Resultado esperado**:

```
┌───────────────────────────────────┐
│          Dashboard                │
│                                   │
│  ¡Tienes acceso al dashboard!     │
│                                   │
│  Vía: CBV (LoginRequiredMixin +   │
│        PermissionRequiredMixin)    │
└───────────────────────────────────┘
```

### 10.3 Escenario 3: Usuario con permiso individual → Dashboard

**Objetivo**: Verificar que asignar el permiso directamente al usuario (sin grupo)
también funciona.

**Pasos**:

1. Crear usuario `visor2`:
   - Staff: NO
   - Superusuario: NO
   - Activo: SÍ
   - Grupos: ninguno
   - **Permisos individuales**: buscar y seleccionar
     `accounts | Profile | Puede ver el dashboard`

2. Cerrar sesión y loguearse como `visor2`.

3. Ir a `/accounts/dashboard/`.

**Resultado esperado**: Misma pantalla de dashboard que en el escenario 2.

### 10.4 Escenario 4: Staff sin permiso → Admin pero no dashboard

**Objetivo**: Verificar que ser staff da acceso al admin pero NO a las vistas protegidas.

**Pasos**:

1. Crear usuario `admin_parcial`:
   - Staff: SÍ (puede entrar al admin)
   - Superusuario: NO
   - Activo: SÍ
   - Grupos: ninguno
   - Permisos: ninguno adicional

2. Ir a `/admin/` → puede acceder al panel de administración.
3. Ir a `/accounts/dashboard/` → **recibe 403** (no tiene `can_view_dashboard`).

**Conclusión**: `is_staff` solo controla el acceso al admin.
No tiene relación con los permisos de las vistas públicas.

### 10.5 Escenario 5: Superusuario → todo accesible

**Objetivo**: Verificar que el superusuario accede a todo sin restricciones.

**Pasos**:

1. Loguearse como `admin` (el superusuario creado con `createsuperuser`).
2. Ir a `/accounts/dashboard/`.
3. Ir a `/admin/`.

**Resultado**: Acceso completo a todo. El superusuario NUNCA recibe 403,
incluso si no tiene el permiso `can_view_dashboard` explícitamente asignado.

---

## 11. Verificación desde la shell de Django

Django provee una shell interactiva para verificar el estado de usuarios, grupos y permisos.

```bash
python manage.py shell
```

### 11.1 Consultar usuarios

```python
from django.contrib.auth.models import User

# Obtener todos los usuarios
User.objects.all()

# Buscar por username
user = User.objects.get(username="juan_perez")

# Ver atributos
user.username        # 'juan_perez'
user.is_staff        # False
user.is_superuser    # False
user.is_active       # True
user.date_joined     # datetime.datetime(...)
```

### 11.2 Verificar permisos

```python
# ¿Tiene el permiso específico?
user.has_perm("accounts.can_view_dashboard")  # True o False

# Ver TODOS los permisos del usuario (individuales + grupos)
user.get_all_permissions()
# {'accounts.can_view_dashboard', 'accounts.add_profile', ...}

# Ver solo los permisos que vienen de grupos
user.get_group_permissions()
# {'accounts.can_view_dashboard'}

# Ver solo los permisos individuales (asignados directamente)
user.user_permissions.all()
# <QuerySet []>  o  <QuerySet [<Permission: ...>]>
```

### 11.3 Consultar grupos

```python
from django.contrib.auth.models import Group

# Obtener grupos
Group.objects.all()
# <QuerySet [<Group: Visores de Dashboard>]>

# Obtener grupo por nombre
group = Group.objects.get(name="Visores de Dashboard")

# Ver permisos del grupo
group.permissions.all()
# <QuerySet [<Permission: accounts | Profile | Puede ver el dashboard>]>

# Ver solo codenames
group.permissions.values_list("codename", flat=True)
# <QuerySet ['can_view_dashboard']>

# Ver usuarios en el grupo
group.user_set.all()
# <QuerySet [<User: juan_perez>]>
```

### 11.4 Consultar permisos

```python
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType

# Todos los permisos
Permission.objects.all()

# Filtrar por app
Permission.objects.filter(content_type__app_label="accounts")

# Buscar permiso específico
perm = Permission.objects.get(codename="can_view_dashboard")
perm.name       # 'Puede ver el dashboard'
perm.content_type  # <ContentType: accounts | profile>
```

### 11.5 ¿De dónde viene el permiso?

```python
def origen_del_permiso(user, perm_codename):
    """Verifica si un permiso viene de grupo o individual."""
    # ¿Viene de grupo?
    for group in user.groups.all():
        if group.permissions.filter(codename=perm_codename).exists():
            print(f"Viene del grupo: {group.name}")
    # ¿Viene de individual?
    if user.user_permissions.filter(codename=perm_codename).exists():
        print("Viene de permiso individual")
    # ¿Es superusuario?
    if user.is_superuser:
        print("Es superusuario (tiene todos los permisos)")

origen_del_permiso(User.objects.get(username="juan_perez"), "can_view_dashboard")
# "Viene del grupo: Visores de Dashboard"
```

---

## 12. Flujo completo de autorización en Django

### 12.1 ¿Qué pasa desde que el usuario hace clic hasta que ve la página?

```
Usuario hace clic en "Dashboard"
         │
         ▼
   ┌─────────────────────────────────────┐
   │ Browser → GET /accounts/dashboard/  │
   └─────────────────────────────────────┘
         │
         ▼
   ┌─────────────────────────────────────┐
   │ Middleware                          │
   │ 1. SecurityMiddleware               │
   │ 2. SessionMiddleware → lee cookie   │
   │ 3. AuthMiddleware → setea user      │
   │ 4. CsrfViewMiddleware               │
   │ 5. MessageMiddleware                │
   └─────────────────────────────────────┘
         │
         ▼
   ┌─────────────────────────────────────┐
   │ URL resolver                        │
   │ seguridad_acceso_django/urls.py     │
   │ → accounts/urls.py                  │
   │ → path("dashboard/", DashboardView) │
   └─────────────────────────────────────┘
         │
         ▼
   ┌─────────────────────────────────────┐
   │ DashboardView.as_view()             │
   │ (LoginRequiredMixin +               │
   │  PermissionRequiredMixin +          │
   │  TemplateView)                      │
   └─────────────────────────────────────┘
         │
         ▼
   ┌─────────────────────────────────────┐
   │ dispatch() → ¿hereda de qué mixin?  │
   └─────────────────────────────────────┘
         │
    ┌────┴────┐
    │         │
    ▼         ▼
  ¿user.    ¿user.
  is_auth?  has_perm?
    │         │
    │    ┌────┴────┐
    │    │         │
    │    ▼         ▼
    │  False     True
    │    │         │
    │    ▼         ▼
    │  raise     Renderiza
    │  Permission dashboard.html
    │  Denied
    │    │
    └────┘
      │
      ▼
  Redirect a        Django busca
  /accounts/login/   403.html
  ?next=/accounts/    │
  dashboard/          ▼
      │            HTTP 403
      ▼            Forbidden
  Formulario
  de login
```

### 12.2 El rol de cada componente

| Componente | Clase/Método | Acción |
|-----------|-------------|--------|
| `SessionMiddleware` | Lee cookie `sessionid` | Recupera la sesión del usuario |
| `AuthenticationMiddleware` | Lee `request.session` | Setea `request.user` |
| `LoginRequiredMixin` | `dispatch()` | Verifica `request.user.is_authenticated` |
| `PermissionRequiredMixin` | `dispatch()` | Verifica `request.user.has_perm()` |
| `TemplateView` | `get()` / `get_context_data()` | Renderiza el template |

### 12.3 ¿Dónde se decide la redirección vs 403?

```python
# En LoginRequiredMixin (dispatch):
def dispatch(self, request, *args, **kwargs):
    if not request.user.is_authenticated:
        # Redirige a LOGIN_URL + ?next=
        return redirect_to_login(...)
    return super().dispatch(request, *args, **kwargs)

# En PermissionRequiredMixin (dispatch):
def dispatch(self, request, *args, **kwargs):
    if not self.has_permission():
        # Lanza HTTP 403
        raise PermissionDenied
    return super().dispatch(request, *args, **kwargs)
```

---

## 13. Preguntas frecuentes

### 13.1 ¿Un usuario necesita `is_staff` para que `@login_required` funcione?

**NO**. `is_staff` solo es necesario para acceder al panel `/admin/`.
Las vistas públicas protegidas con `@login_required` o `LoginRequiredMixin`
solo requieren que el usuario esté autenticado (`is_active=True` y sesión activa).

### 13.2 ¿Si creo un superusuario, puedo quitarle permisos específicos?

**NO**. `is_superuser=True` salta TODA verificación de permisos. El superusuario
tiene acceso completo a todo, sin importar qué permisos tenga o no en la tabla.
`has_perm()` siempre retorna `True` para superusuarios.

### 13.3 ¿Si agrego un permiso a un grupo, los usuarios ya asignados lo heredan?

**SÍ**. No necesitas volver a guardar los usuarios. La verificación de permisos
se hace en tiempo real (cada `has_perm()` consulta la BD en ese momento).

### 13.4 ¿Un usuario puede pertenecer a varios grupos?

**SÍ**. Los permisos se acumulan de TODOS los grupos. No hay límite de grupos.

```python
user.groups.all()
# <QuerySet [<Group: Visores>, <Group: Editores>]>
user.get_all_permissions()
# {'accounts.can_view_dashboard', 'accounts.add_profile', 'accounts.change_profile'}
```

### 13.5 ¿Puedo tener permisos duplicados (en grupo + individual)?

**SÍ**, no hay problema. Django usa un `set` (conjunto) internamente,
así que los permisos duplicados se ignoran. No hay conflictos.

### 13.6 ¿Qué pasa si un usuario no tiene `is_active`?

No puede iniciar sesión en `/accounts/login/`. `authenticate()` retorna `None`.
Es útil para desactivar cuentas sin eliminar el registro.

### 13.7 ¿Cómo verifico un permiso en un template?

Gracias al auth context processor, `{{ perms }}` está disponible en todos los templates:

```django
{% if perms.accounts.can_view_dashboard %}
    <a href="{% url 'accounts:dashboard' %}">Dashboard</a>
{% else %}
    <p class="text-muted">No tenés acceso al dashboard</p>
{% endif %}
```

### 13.8 ¿Cuál es la diferencia entre los 4 permisos estándar y los personalizados?

- **Estándar**: Django los crea automáticamente para cada modelo. Controlan acciones
  CRUD (crear, leer, actualizar, eliminar). Se usan en el admin.
- **Personalizados**: Los definís vos en `class Meta`. Sirven para acciones
  específicas de la aplicación (ej: `can_view_dashboard`, `can_approve_posts`, `can_export_data`).

### 13.9 ¿Cómo elimino un permiso personalizado si ya no lo necesito?

1. Eliminarlo del `Meta.permissions` en el modelo.
2. Crear y ejecutar una migración:
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```
   Django eliminará el registro de `auth_permission`.
   > **Precaución**: Si hay usuarios/grupos con ese permiso asignado, la migración fallará
   > o dejará referencias huérfanas. Mejor quitar el permiso de todos los usuarios/grupos
   > antes de eliminarlo.

### 13.10 ¿Puedo tener el admin en español?

Sí, en `settings.py`:

```python
LANGUAGE_CODE = "es"
```

Esto traduce todo el admin (y los mensajes de Django) al español.

---

## Resumen visual: Mapa conceptual del admin

```
┌─────────────────────────────────────────────────────────┐
│                   django.contrib.admin                   │
│                                                          │
│   ┌──────────────────────────────────────────────────┐  │
│   │  /admin/                                         │  │
│   │                                                  │  │
│   │  Autenticación y Autorización                    │  │
│   │  ├── Usuarios  → Crear / Editar / Permisos      │  │
│   │  │                ├── is_staff   → acceso admin  │  │
│   │  │                ├── is_superuser → todo        │  │
│   │  │                ├── Grupos     → hereda perms  │  │
│   │  │                └── Permisos   → individuales  │  │
│   │  │                                                  │  │
│   │  └── Grupos    → Crear / Editar / Permisos        │  │
│   │                   ├── name        → nombre        │  │
│   │                   └── permissions → lista de perms│  │
│   │                                                  │  │
│   │  Accounts                                        │  │
│   │  └── Perfiles  → CRUD de perfiles                │  │
│   └──────────────────────────────────────────────────┘  │
│                                                          │
│  Requisitos para acceder:                                │
│  - user.is_staff = True                                  │
│  - user.is_active = True                                 │
└─────────────────────────────────────────────────────────┘
```
