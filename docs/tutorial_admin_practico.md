# Tutorial Práctico — Administración de Usuarios y Permisos

Guía paso a paso para usar el sitio administrativo de Django. Solo las acciones concretas
con una línea de explicación por paso.

---

## Requisito

El proyecto `seguridad_acceso_django` debe estar funcionando:

```bash
source venv/bin/activate
python manage.py migrate
python manage.py runserver
```

---

## 1. Creación del superusuario

```bash
python manage.py createsuperuser
```

Completar:

```
Username: admin
Email: admin@example.com
Password: ********
Password (again): ********
```

**Explicación**: El superusuario tiene acceso total al admin y a todas las vistas del sistema.
`is_superuser=True` salta toda verificación de permisos.

---

## 2. Acceso al sitio administrativo

1. Abrir `http://localhost:8000/admin/` en el navegador.
2. Ingresar usuario: `admin`, contraseña: la que definiste.
3. Hacer clic en **"Iniciar sesión"**.

**Explicación**: El admin solo permite el ingreso a usuarios con `is_staff=True`.
El superusuario lo tiene por defecto.

---

## 3. Gestión de grupos

### 3.1 Crear un grupo

1. En el menú del admin, ir a **"Autenticación y Autorización" → "Grupos"**.
2. Hacer clic en **"Añadir grupo"** (botón superior derecho).
3. En **"Nombre"**, escribir: `Visores Dashboard`.

4. En **"Permisos disponibles"**, filtrar escribiendo `dashboard`:

   ```
   accounts | Profile | Puede ver el dashboard
   ```

5. Seleccionar el permiso y presionar la flecha derecha (→) para pasarlo a
   **"Permisos escogidos"**.
6. Hacer clic en **"Guardar"**.

**Explicación**: Los grupos agrupan permisos para asignarlos a varios usuarios de una vez.

### 3.2 Verificar el grupo creado

Aparece listado en la pantalla de grupos. Hacer clic en el nombre para ver sus detalles.

**Explicación**: El grupo ahora contiene el permiso `can_view_dashboard`.
Cualquier usuario asignado a este grupo lo heredará automáticamente.

---

## 4. Gestión de usuarios

### 4.1 Crear un usuario

1. En el menú del admin, ir a **"Autenticación y Autorización" → "Usuarios"**.
2. Hacer clic en **"Añadir usuario"**.

3. Completar:
   - **Username**: `juan_perez`
   - **Password**: `Clase2025!`
   - **Confirmación**: `Clase2025!`

4. Hacer clic en **"Guardar"**.

**Explicación**: Este primer formulario crea el usuario con lo mínimo (username y password).
Luego se abre un formulario detallado para completar el resto.

### 4.2 Completar datos del usuario

En el formulario detallado que se abre después de guardar:

#### Pestaña "Detalles del usuario"

| Campo | Valor |
|-------|-------|
| Nombre | `Juan` |
| Apellido | `Pérez` |
| Email | `juan@example.com` |

#### Pestaña "Permisos"

| Opción | Valor | Explicación |
|--------|-------|-------------|
| Activo | ☑ | Puede iniciar sesión en la web |
| Staff | ☐ | No necesita el admin |
| Superusuario | ☐ | No debe tener todos los permisos |
| Grupos | Seleccionar `Visores Dashboard` | Hereda el permiso del grupo |
| Permisos de usuario | (vacío) | No necesita permisos adicionales |

Hacer clic en **"Guardar"**.

**Explicación**: Al asignar el grupo, el usuario hereda todos sus permisos sin tener
que seleccionarlos uno por uno. Los permisos de usuario son solo para casos
excepcionales donde se necesita un permiso extra fuera del grupo.

### 4.3 Crear un segundo usuario (con permiso individual)

1. Repetir los pasos 4.1 y 4.2 para crear `maria_garcia`.
2. En la pestaña "Permisos":
   - NO asignar ningún grupo.
   - En **"Permisos de usuario"**, buscar y seleccionar:
     `accounts | Profile | Puede ver el dashboard`
3. Guardar.

**Explicación**: El permiso se asigna directamente al usuario sin pasar por un grupo.
Útil para excepciones o cuando solo uno o dos usuarios necesitan ese permiso.

### 4.4 Crear un tercer usuario (sin permisos)

1. Crear `pedro_lopez`.
2. En la pestaña "Permisos":
   - Activo: ☑
   - Staff: ☐
   - Superusuario: ☐
   - Grupos: ninguno
   - Permisos de usuario: ninguno
3. Guardar.

**Explicación**: Este usuario existe pero no tiene `can_view_dashboard`.
Servirá para probar que recibe error 403.

---

## 5. Gestión de permisos

### 5.1 ¿Dónde se ven los permisos disponibles?

Hay dos lugares:

1. **Al crear/editar un grupo**: en "Permisos disponibles" se listan TODOS los permisos
   del sistema, agrupados por app.
2. **Al editar un usuario**: en "Permisos de usuario" se listan los mismos permisos.

### 5.2 Permisos que genera nuestro proyecto

Al ejecutar `migrate`, Django crea automáticamente:

| Permiso | Codename |
|---------|----------|
| Can add profile | `accounts.add_profile` |
| Can change profile | `accounts.change_profile` |
| Can delete profile | `accounts.delete_profile` |
| Can view profile | `accounts.view_profile` |
| Puede ver el dashboard | `accounts.can_view_dashboard` ← **personalizado** |

**Explicación**: Los primeros 4 son estándar (todo modelo los tiene).
El quinto lo definimos en `models.py` con `Meta.permissions`.

### 5.3 Asignar permiso vía grupo (recomendado)

| Paso | Acción |
|------|--------|
| 1 | Ir a "Grupos" → "Añadir grupo" |
| 2 | Nombre: `Visores Dashboard` |
| 3 | Asignar: `accounts.can_view_dashboard` |
| 4 | Guardar |
| 5 | Ir al usuario → asignar al grupo "Visores Dashboard" |

**Explicación**: Si necesitás que 10 usuarios tengan el mismo permiso,
lo asignás al grupo una vez y luego agregás los 10 usuarios al grupo.
Si después necesitás cambiar el permiso, lo cambiás en el grupo y
todos lo heredan automáticamente.

### 5.4 Asignar permiso individual (excepción)

| Paso | Acción |
|------|--------|
| 1 | Ir a "Usuarios" → seleccionar usuario |
| 2 | Ir a "Permisos de usuario" |
| 3 | Buscar y seleccionar el permiso |
| 4 | Guardar |

**Explicación**: Úsalo cuando solo 1 o 2 usuarios necesitan un permiso
que el resto del grupo no tiene. Para la mayoría de los casos, preferí grupo.

---

## 6. Verificación práctica

### 6.1 Probar usuario con permiso vía grupo

1. Cerrar sesión del admin.
2. Ir a `http://localhost:8000/accounts/login/`.
3. Loguearse como `juan_perez`.
4. Ir a `http://localhost:8000/accounts/dashboard/`.

**Resultado esperado**: ✅ Ve el dashboard (el permiso viene del grupo "Visores Dashboard").

### 6.2 Probar usuario con permiso individual

1. Cerrar sesión.
2. Loguearse como `maria_garcia`.
3. Ir a `http://localhost:8000/accounts/dashboard/`.

**Resultado esperado**: ✅ Ve el dashboard (el permiso está asignado directamente).

### 6.3 Probar usuario sin permiso

1. Cerrar sesión.
2. Loguearse como `pedro_lopez`.
3. Ir a `http://localhost:8000/accounts/dashboard/`.

**Resultado esperado**: ❌ Recibe página 403 "Acceso Denegado".

### 6.4 Probar acceso al admin

1. Loguearse como `juan_perez`.
2. Ir a `http://localhost:8000/admin/`.

**Resultado esperado**: ❌ No puede acceder (no tiene `is_staff=True`).

### 6.5 Resumen de resultados

| Usuario | ¿Puede ver dashboard? | ¿Puede entrar al admin? |¿Por qué? |
|---------|----------------------|------------------------|----------|
| `admin` (superuser) | Sí | Sí | `is_superuser=True` |
| `juan_perez` | Sí | No | Permiso vía grupo |
| `maria_garcia` | Sí | No | Permiso individual |
| `pedro_lopez` | No (403) | No | Sin permiso asignado |

---

## 7. Resumen visual del flujo

```
createsuperuser
      │
      ▼
  /admin/  ─── Login con superusuario
      │
      ├── → Grupos → Crear "Visores Dashboard"
      │                └── Asignar permiso can_view_dashboard
      │
      ├── → Usuarios → Crear "juan_perez"
      │                   └── Asignar al grupo "Visores Dashboard"
      │
      ├── → Usuarios → Crear "maria_garcia"
      │                   └── Asignar can_view_dashboard individual
      │
      └── → Usuarios → Crear "pedro_lopez"
                          └── Sin permisos

  ─── Prueba en navegador ───
  /accounts/dashboard/
      ├── juan_perez   → ✅ Dashboard
      ├── maria_garcia → ✅ Dashboard
      └── pedro_lopez  → ❌ 403
```
