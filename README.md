# Sistema de Inventario - MAESTRANZA

Aplicación web de gestión de inventario desarrollada con Flask y SQLite, basada en historias de usuario específicas para el control de piezas, trazabilidad, alertas y gestión de usuarios.

## 🚀 Funcionalidades Principales

### ✅ Historia U001 - Registro de Piezas
- **Como Gestor de Inventario**: Registro completo de piezas con descripción, número de serie y ubicación física
- CRUD completo de piezas con validaciones
- Control de stock actual y mínimo

### ✅ Historia U002 - Trazabilidad de Movimientos
- **Como Encargado de Logística**: Rastreo en tiempo real de movimientos de inventario
- Registro de entradas y salidas con timestamp
- Historial completo de movimientos por pieza

### ✅ Historia U003 - Alertas Automáticas
- **Como Comprador**: Sistema automático de alertas cuando el stock alcanza niveles mínimos
- Dashboard con alertas activas
- Notificaciones visuales de stock bajo

### ✅ Historia U004 - Gestión de Kits
- **Como Jefe de Producción**: Consulta de disponibilidad de componentes agrupados en kits
- Creación y gestión de kits de mantenimiento
- Planificación de actividades

### ✅ Historia U005 - Control de Accesos
- **Como Administrador del Sistema**: Sistema de roles y permisos
- Autenticación segura con contraseñas hasheadas
- Diferentes niveles de acceso por rol

## 🛠️ Tecnologías Utilizadas

- **Backend**: Python Flask 2.3.3
- **Base de Datos**: SQLite (incluida)
- **Frontend**: HTML5, CSS3, JavaScript, Bootstrap 5
- **Autenticación**: Werkzeug Security
- **UI/UX**: Font Awesome, Gradientes modernos

## 📦 Instalación

### Requisitos previos
- Python 3.7 o superior
- pip (gestor de paquetes de Python)

### Pasos de instalación

1. **Clonar o descargar el proyecto**
   ```bash
   cd MAESTRANZA
   ```

2. **Instalar dependencias**
   ```bash
   pip install -r requirements.txt
   ```

3. **Ejecutar la aplicación**
   ```bash
   python app.py
   ```

4. **Acceder a la aplicación**
   - Abrir navegador en: `http://localhost:5000`

## 👥 Usuarios de Prueba

| Usuario | Contraseña | Rol | Permisos |
|---------|------------|-----|----------|
| `admin` | `admin123` | Administrador | Acceso completo, gestión de usuarios |
| `gestor` | `gestor123` | Gestor | Gestión de inventario, registro de piezas |
| `logistica` | `logistica123` | Logística | Movimientos, trazabilidad, kits |

## 🎯 Guía de Uso

### 1. Dashboard Principal
- Visualización de estadísticas generales
- Alertas de stock bajo en tiempo real
- Resumen de movimientos

### 2. Gestión de Piezas
- **Crear**: Agregar nuevas piezas con todos los datos
- **Leer**: Visualizar lista completa con estados
- **Actualizar**: Modificar información existente
- **Eliminar**: Remover piezas del sistema
- **Movimientos**: Registrar entradas/salidas directamente

### 3. Trazabilidad
- Historial completo de todos los movimientos
- Filtros por fecha, tipo y usuario
- Seguimiento detallado de cada transacción

### 4. Sistema de Alertas
- Alertas automáticas por stock mínimo
- Gestión de estados de alertas
- Estadísticas de niveles de stock

### 5. Gestión de Kits
- Creación de kits de mantenimiento
- Agrupación lógica de componentes
- Planificación de actividades

### 6. Administración de Usuarios (Solo Administradores)
- Visualización de todos los usuarios
- Control de roles y permisos
- Información detallada de accesos

## 🗂️ Estructura de la Base de Datos

```sql
- usuarios (id, username, password, rol, nombre, created_at)
- piezas (id, descripcion, numero_serie, ubicacion_fisica, stock_actual, stock_minimo, precio, created_at)
- movimientos (id, pieza_id, tipo_movimiento, cantidad, usuario_id, observaciones, created_at)
- kits (id, nombre, descripcion, created_at)
- kit_componentes (id, kit_id, pieza_id, cantidad_requerida)
- alertas (id, pieza_id, tipo_alerta, mensaje, estado, created_at)
```

## 🔧 Personalización

### Modificar datos iniciales
Editar la función `init_db()` en `app.py` para cambiar:
- Usuarios predeterminados
- Piezas de ejemplo
- Configuraciones iniciales

### Cambiar estilos
Los estilos están integrados en las plantillas HTML para facilidad de modificación.

## 📱 Responsive Design

La aplicación está optimizada para diferentes dispositivos:
- ✅ Desktop (1200px+)
- ✅ Tablet (768px - 1199px)
- ✅ Mobile (hasta 767px)

## 🔒 Seguridad

- Contraseñas hasheadas con Werkzeug
- Validación de sesiones en todas las rutas
- Control de acceso basado en roles
- Protección CSRF en formularios

## 🚀 Características Avanzadas

- **UI Moderna**: Diseño con gradientes y animaciones
- **Interacción AJAX**: Actualizaciones sin recarga de página
- **Notificaciones**: Sistema de alertas en tiempo real
- **Iconografía**: Font Awesome para mejor UX
- **Responsive**: Adaptable a todos los dispositivos

## 📈 Próximas Mejoras Sugeridas

1. Reportes en PDF/Excel
2. Sistema de notificaciones por email
3. API REST completa
4. Backup automático de base de datos
5. Panel de analytics avanzado

---

**Desarrollado para MAESTRANZA** - Sistema de gestión de inventario industrial

*¡Listo para usar en solo 3 comandos!* 