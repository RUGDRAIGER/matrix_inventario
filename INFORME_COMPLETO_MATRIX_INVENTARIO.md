# Informe Técnico Completo — Matrix Inventario TI

**Repositorio:** [https://github.com/RUGDRAIGER/matrix_inventario.git](https://github.com/RUGDRAIGER/matrix_inventario.git)  
**Versión analizada:** rama `main` (commit `0c9a850`)  
**Fecha del informe:** 30 de julio de 2026  
**Propósito del documento:** Entregar contexto integral a otra IA para continuidad de desarrollo, mantenimiento, integración o migración.

---

## 1. Resumen ejecutivo

**Matrix Inventario TI** es una aplicación de escritorio **100 % local y offline** para **Windows 10/11**, orientada al **control de inventario de equipos de TI** en organizaciones con estructura por **unidades organizacionales** y **funcionarios**. Permite:

- Escanear automáticamente hardware del PC (WMI + PowerShell).
- Registrar PCs, monitores, webcams e impresoras (USB/RED).
- Asignar equipos a unidades y funcionarios.
- Consultar estadísticas agregadas.
- Ejecutar tareas de mantenimiento del sistema operativo.
- Operar en **modo portable** (pendrive / disco externo) con SQLite embebido.

No requiere servidor, red ni autenticación. Toda la persistencia vive en un archivo `inventario.db` junto al ejecutable o scripts.

---

## 2. Objetivo del aplicativo

### 2.1 Objetivo principal

Digitalizar y centralizar el inventario de activos informáticos (PCs y periféricos) vinculados a unidades de costo y personal responsable, reduciendo el registro manual mediante **escaneo automático de hardware** en el propio equipo inventariado.

### 2.2 Problemas que resuelve

| Problema | Solución implementada |
|----------|-------------------------|
| Registro manual lento de specs de PC | Escaneo WMI/PowerShell con un clic |
| Inventario disperso en hojas de cálculo | Base SQLite relacional centralizada |
| Falta de trazabilidad unidad ↔ equipo ↔ funcionario | Modelo relacional con FK y tabla puente |
| Necesidad de operar sin infraestructura | App portable, sin dependencias de red |
| Mantenimiento básico del equipo | Módulo de limpieza y optimización Windows |

### 2.3 Usuarios objetivo

- Personal de soporte TI / mesa de ayuda.
- Administradores de activos informáticos.
- Auditores internos que necesitan inventario por unidad/centro de costo.

### 2.4 Alcance funcional (módulos)

1. **Escáner / Registro** — Detección + guardado de equipo nuevo.
2. **Unidades** — CRUD de unidades organizacionales.
3. **Equipos** — Listado, edición y eliminación por unidad.
4. **Funcionarios** — CRUD vinculado a unidad.
5. **Estadísticas** — Dashboard con totales y resumen por unidad.
6. **Mantenimiento** — Limpieza TEMP, navegadores, DNS, etc.
7. **Configuración** — Backup DB y acceso a carpeta de datos.

### 2.5 Fuera de alcance (actual)

- Sincronización en la nube o multi-usuario concurrente.
- API REST / servicios web.
- Soporte Linux/macOS.
- Autenticación, roles o permisos.
- Exportación a Excel/PDF (no implementada).
- Tipo de accesorio `PARLANTE` (eliminado en migraciones; solo MONITOR, WEBCAM, IMPRESORA).

---

## 3. Stack tecnológico

### 3.1 Plataforma y runtime

| Componente | Detalle |
|------------|---------|
| SO objetivo | Windows 10 / 11 |
| Lenguaje | Python 3.11+ |
| UI | CustomTkinter 5.2+ (sobre Tkinter/ttk) |
| Base de datos | SQLite3 (stdlib `sqlite3`) |
| Escaneo hardware | WMI (`wmi`), pywin32, subprocess → PowerShell |
| Empaquetado | PyInstaller (onefile, windowed) |
| Scripts auxiliares | PowerShell, Batch (.bat) |

### 3.2 Dependencias (`requirements.txt`)

```
customtkinter>=5.2.0
WMI>=1.5.1
pywin32>=306
```

**Dependencias implícitas:** `tkinter` (incluido con Python en Windows), stdlib (`sqlite3`, `subprocess`, `threading`, `json`, `pathlib`, etc.).

**Build (no en requirements):** `pyinstaller` — instalado on-the-fly por `build_exe.ps1`.

### 3.3 Arquitectura de capas

```
┌─────────────────────────────────────────────────────────┐
│  gui.py (Presentación)                                  │
│  - InventarioApp, páginas, modales                      │
│  - ui_components.py (tema Matrix, widgets)              │
├─────────────────────────────────────────────────────────┤
│  scanner.py / maintenance.py (Lógica de sistema)      │
│  - WMI, PowerShell, subprocess                          │
├─────────────────────────────────────────────────────────┤
│  database.py (Persistencia)                             │
│  - CRUD, migraciones, estadísticas                      │
├─────────────────────────────────────────────────────────┤
│  paths.py (Infraestructura portable)                    │
│  - Rutas, backups, carpetas                             │
└─────────────────────────────────────────────────────────┘
         │
         ▼
   inventario.db (SQLite)
   backups/ (copias timestamped)
```

### 3.4 Patrones de diseño utilizados

- **Separación por módulos** (UI / DB / Scanner / Paths).
- **Callbacks de refresco** entre páginas (`refresh_callbacks` en `ScannerPage`).
- **Operaciones largas en hilos daemon** (`threading.Thread`) para no bloquear la UI (escaneo, mantenimiento).
- **Migraciones incrementales** en `_migrate()` al iniciar DB.
- **Modal responsive** con scroll body + footer fijo (`ResponsiveModal`).

---

## 4. Estructura del proyecto

```
matrix_inventario/
├── main.py                 # Punto de entrada: init_db() + InventarioApp
├── gui.py                  # App principal, páginas, modales (~1180 líneas)
├── database.py             # SQLite: schema, migraciones, CRUD, stats
├── scanner.py              # Escaneo hardware WMI/PowerShell
├── maintenance.py          # Limpieza y optimización Windows
├── paths.py                # Rutas portables y backup
├── ui_components.py        # Tema Matrix y componentes reutilizables
├── test_validacion.py      # Tests de integración básicos
├── Iniciar.bat             # Launcher portable (exe o python main.py)
├── build_exe.ps1           # Compila Inventario.exe con PyInstaller
├── build_portable.ps1      # Genera ZIP portable
├── requirements.txt
├── README.md
├── .cursorrules            # Reglas de arquitectura para Cursor AI
├── .gitignore
└── docs/
    ├── index.html          # Landing Matrix (GitHub Pages)
    └── inventario.html     # Página de descarga
```

### 4.1 Historial de commits (evolución)

| Commit | Descripción |
|--------|-------------|
| `a4cbb68` | Implementación inicial: escaneo, unidades, funcionarios |
| `3977bfe` | Ubicación en equipos, escáner mejorado, páginas separadas |
| `3544035` | Modo portable, Configuración, respaldo DB |
| `02be4cb` | Landing GitHub Pages + script paquete portable |
| `a596964` | Inventario.exe (PyInstaller) + página descarga |
| `0b7262d` | Impresoras USB/RED, UI campos visibles |
| `0c9a850` | Página Mantenimiento (limpieza y optimización) |

---

## 5. Modelo de datos (SQLite)

### 5.1 Diagrama entidad-relación

```
unidades (1) ──< (N) funcionarios
    │
    └──< (N) pcs (1) ──< (N) accesorios
              │
              └──< (N) pc_funcionario >── (N) funcionarios
```

### 5.2 Tablas y columnas

#### `unidades`
| Columna | Tipo | Notas |
|---------|------|-------|
| id | INTEGER PK AUTOINCREMENT | |
| nombre_unidad | TEXT NOT NULL UNIQUE | |
| centro_costo | TEXT | |
| sap | TEXT | Código SAP (poco usado en UI actual) |
| ubicacion | TEXT | Ubicación física de la unidad |

#### `funcionarios`
| Columna | Tipo | Notas |
|---------|------|-------|
| id | INTEGER PK | |
| unidad_id | INTEGER FK → unidades(id) ON DELETE SET NULL | Agregado por migración |
| grado | TEXT | |
| nombre | TEXT NOT NULL | |
| apellido | TEXT NOT NULL | |
| dotacion | TEXT | Identificador interno |
| cargo | TEXT | |

#### `pcs`
| Columna | Tipo | Notas |
|---------|------|-------|
| id | INTEGER PK | |
| unidad_id | INTEGER FK NOT NULL → unidades ON DELETE CASCADE | |
| marca, modelo, serie | TEXT | |
| windows_version | TEXT | |
| procesador | TEXT | |
| ram_gb | REAL | |
| disco_detalle | TEXT | Ej: "SSD 512 GB \| NVMe/M.2 256 GB" |
| office_version | TEXT | |
| ip_address, mac_address | TEXT | |
| ubicacion | TEXT | Ubicación específica del equipo (migración) |

#### `accesorios`
| Columna | Tipo | Notas |
|---------|------|-------|
| id | INTEGER PK | |
| pc_id | INTEGER FK → pcs ON DELETE CASCADE | |
| tipo | TEXT CHECK IN ('MONITOR','WEBCAM','IMPRESORA') | |
| etiqueta | TEXT | Ej: "Monitor 1", "Impresora 1" |
| marca, modelo, serie | TEXT | |
| ip_address | TEXT | Impresoras RED |
| conexion | TEXT | 'USB' o 'RED' (impresoras) |

#### `pc_funcionario` (tabla puente)
| Columna | Tipo | Notas |
|---------|------|-------|
| id | INTEGER PK | |
| pc_id | INTEGER FK → pcs ON DELETE CASCADE | |
| funcionario_id | INTEGER FK → funcionarios ON DELETE CASCADE | |
| UNIQUE(pc_id, funcionario_id) | | |

**Nota:** La UI asigna **un solo funcionario** por PC (`set_pc_funcionarios` con lista de 0–1 elemento), aunque el esquema permite N.

### 5.3 Migraciones automáticas (`database._migrate`)

Al ejecutar `init_db()`:

1. Agrega `unidad_id` a `funcionarios` si no existe.
2. Agrega `etiqueta`, `ip_address`, `conexion` a `accesorios`.
3. Elimina registros `tipo='PARLANTE'`.
4. Recrea tabla `accesorios` si el CHECK no incluye IMPRESORA o aún permite PARLANTE.
5. Agrega `ubicacion` a `pcs` y la rellena desde `unidades.ubicacion` si está vacía.

### 5.4 Configuración SQLite

- `PRAGMA foreign_keys = ON`
- `row_factory` personalizado → filas como `dict`

---

## 6. Módulos de programación (detalle)

### 6.1 `main.py`

```python
def main():
    db.init_db()
    app = InventarioApp()
    app.mainloop()
```

Flujo mínimo: inicializar DB → lanzar GUI.

### 6.2 `paths.py` — Infraestructura portable

| Función / Variable | Descripción |
|--------------------|-------------|
| `get_app_dir()` | Directorio del `.exe` (frozen) o del script |
| `APP_DIR`, `DATA_DIR` | Misma carpeta que la app |
| `DB_PATH` | `{APP_DIR}/inventario.db` |
| `BACKUP_DIR` | `{APP_DIR}/backups/` |
| `ensure_portable_dirs()` | Crea `backups/` |
| `backup_database()` | Copia con timestamp `inventario_YYYYMMDD_HHMMSS.db` |
| `open_data_folder()` | `os.startfile(DATA_DIR)` |

**Implicación:** Copiar toda la carpeta del proyecto mueve app + datos + backups.

### 6.3 `scanner.py` — Motor de escaneo

**Función principal:** `scan_hardware(progress_callback=None) → dict`

Retorna:
```python
{
    "pc": { marca, modelo, serie, windows_version, procesador, ram_gb,
            disco_detalle, office_version, ip_address, mac_address },
    "accesorios": [ { tipo, etiqueta, marca, modelo, serie }, ... ],  # MONITOR, WEBCAM
    "impresoras": [ { tipo, etiqueta, marca, modelo, serie, ip_address, conexion }, ... ]
}
```

#### Fuentes de datos por componente

| Dato | Método |
|------|--------|
| Marca, modelo, RAM | `Win32_ComputerSystem` (WMI) |
| Serie | `Win32_BIOS.SerialNumber` |
| Procesador | `Win32_Processor` |
| Discos | `Win32_DiskDrive` → clasifica NVMe/SSD/HDD |
| Windows | `Win32_OperatingSystem` |
| IP/MAC | PowerShell `Get-NetRoute` + `Get-NetAdapter` (fallback socket + PS) |
| Office | Registro Windows (ClickToRun, Uninstall keys) |
| Monitores | `root\wmi.WmiMonitorID`, CIM, PnP, EnumDisplayDevices |
| Webcams | `Win32_PnPEntity` (camera/webcam/image) |
| Impresoras | `Get-Printer` (PS) + `Win32_Printer` (WMI), solo **en línea**, USB o RED |

#### Reglas de impresoras

- **Excluye virtuales:** PDF, OneNote, Fax, XPS, PORTPROMPT, NUL, etc.
- **Clasificación de puerto:** `classify_printer_port(port)` → `("USB","N/A")` o `("RED", ip)`
- Prefijos USB: `USB`, `DOT4`, `LPT`, `COM`
- Prefijos RED: `IP_`, `WSD-`, `TCP`, etc.
- Etiquetado automático: "Impresora 1", "Impresora 2"…

#### Progreso del escaneo (porcentajes)

| % | Etapa |
|---|-------|
| 0–5 | Inicio, conexión WMI |
| 15 | Datos del sistema |
| 45 | Red IP/MAC |
| 60 | Microsoft Office |
| 72 | Monitores |
| 88 | Webcams |
| 94 | Impresoras |
| 100 | Completado |

**Timeout PowerShell:** 90 s por script. Flag `CREATE_NO_WINDOW`.

### 6.4 `maintenance.py` — Mantenimiento del PC

**Función principal:** `run_maintenance(options, progress_cb=None) → { tasks, total_freed }`

| Opción (`options` key) | Acción |
|------------------------|--------|
| `clean_temp` | TEMP, %TEMP%, `C:\Windows\Temp` |
| `clean_prefetch` | `C:\Windows\Prefetch` |
| `clean_chrome` | Cache + cookies Chrome |
| `clean_edge` | Cache + cookies Edge |
| `empty_recycle` | `Clear-RecycleBin -Force` |
| `flush_dns` | `ipconfig /flushdns` |
| `high_performance` | Plan energía Alto rendimiento (GUID fijo) |
| `clean_thumbnails` | `thumbcache_*.db`, `iconcache_*.db` |
| `optimize_visual` | Desactiva transparencia y reduce efectos visuales (registro) |

Retorna lista de tareas con `{ name, ok, detail, freed }` y bytes totales liberados.

### 6.5 `gui.py` — Interfaz de usuario

#### Clase principal: `InventarioApp(ctk.CTk)`

- Ventana: 1200×800, mínimo 960×640.
- Sidebar navegación + área de contenido.
- Páginas en dict `self.pages`, navegación con `_show_page(key)`.

#### Páginas

| Key | Clase | Funcionalidad |
|-----|-------|---------------|
| scanner | `ScannerPage` | Escaneo, formulario PC, accesorios, impresoras, asignación |
| unidades | `UnidadesPage` | Treeview CRUD unidades |
| equipos | `EquiposPage` | Treeview PCs filtrado por unidad |
| funcionarios | `FuncionariosPage` | Treeview funcionarios por unidad |
| stats | `StatsPage` | Cards + resumen por unidad |
| mantenimiento | `MantenimientoPage` | Checkboxes + log + barra progreso |
| config | `ConfigPage` | Backup, abrir carpeta, info portable |

#### Modales

- `FuncionarioModal`, `UnidadModal`, `UnidadEditModal`, `PCEditModal`
- Heredan `ResponsiveModal` (scroll + botones Guardar/Cancelar fijos).

#### Validaciones UI relevantes

- Unidad obligatoria al guardar PC/funcionario.
- Nombre y apellido obligatorios en funcionario.
- Impresoras: requiere `conexion` USB o RED; IP = N/A si USB.
- Impresoras sin marca/modelo se omiten al guardar.

### 6.6 `ui_components.py` — Design system "Matrix"

| Token | Valor |
|-------|-------|
| BG | `#000000` |
| BG_ALT | `#0D0D0D` |
| PANEL | `#121212` |
| PANEL_ALT | `#1A1A1A` |
| ACCENT | `#00FF66` |
| ACCENT_DIM | `#00CC52` |
| Fuente UI | Segoe UI 13 |
| Fuente mono/títulos | Consolas |

Componentes: `StyledEntry`, `StyledButton`, `StyledCombo`, `StyledCheckBox`, `ProgressPanel`, `create_matrix_tree`, `form_field_grid`, `accessory_block`, `printer_block`, `page_toolbar`, `unit_selector`.

### 6.7 `test_validacion.py`

Tests sin pytest (script ejecutable):

- CRUD unidad, funcionario, PC, accesorios (incl. impresora RED).
- Cascade delete accesorios al borrar PC.
- Estadísticas (sin `total_parlantes`).
- Funciones scanner: etiquetas, clasificación puertos, impresoras virtuales.
- `_scan_network()` (requiere red real).
- Import GUI + `backup_database()`.

Ejecutar: `python test_validacion.py` → exit 0/1.

---

## 7. Configuración e instalación

### 7.1 Requisitos del sistema

- Windows 10 o 11 (64-bit recomendado).
- Python 3.11+ **o** `Inventario.exe` compilado.
- Permisos para ejecutar PowerShell y consultas WMI.
- ~50–100 MB espacio (más tamaño del .exe ~ decenas de MB).

### 7.2 Instalación desde código fuente

```bash
git clone https://github.com/RUGDRAIGER/matrix_inventario.git
cd matrix_inventario
pip install -r requirements.txt
python main.py
```

### 7.3 Modo portable (Python)

1. Copiar **toda la carpeta** del proyecto.
2. Doble clic en `Iniciar.bat`.
3. `inventario.db` y `backups/` se crean en la misma carpeta.

### 7.4 Modo portable (ejecutable)

1. Ejecutar `build_portable.ps1` (genera `dist/matrix_inventario_portable.zip`).
2. Contenido del ZIP: `Inventario.exe`, `Iniciar.bat`, `inventario.db`, `README.md`, `backups/`.
3. `Iniciar.bat` prioriza `Inventario.exe`; si no existe, usa `python main.py`.

### 7.5 Compilar solo el .exe

```powershell
.\build_exe.ps1
# Salida: dist/Inventario.exe
```

PyInstaller flags: `--onefile --windowed --hidden-import wmi --collect-all customtkinter`.

### 7.6 Configuración dentro de la app

Menú **Configuración**:

| Acción | Efecto |
|--------|--------|
| Copia de Seguridad | Copia `inventario.db` → `backups/inventario_YYYYMMDD_HHMMSS.db` |
| Abrir Carpeta de Datos | Explorador Windows en directorio de la app |

### 7.7 Variables de entorno

**Ninguna requerida.** Rutas derivadas de ubicación del ejecutable/script.

### 7.8 Archivos ignorados por Git (`.gitignore`)

- `*.db`, `backups/`, `dist/`, `build/`, `__pycache__/`, `.venv/`, `.env`

---

## 8. Flujos de usuario principales

### 8.1 Registrar un equipo nuevo

```
Usuario → Escáner/Registro → [Escanear]
    → scanner.scan_hardware() en hilo background
    → Campos PC + accesorios + impresoras rellenados (editables)
    → Seleccionar Unidad (+ opcional Funcionario, Ubicación)
    → [Guardar]
    → db.insert_pc + insert_accesorio + set_pc_funcionarios
    → Refresco páginas Unidades/Equipos/Funcionarios/Stats
```

### 8.2 Gestionar unidades y personal

- Crear unidad en **Unidades** o desde el escáner ("Nueva Unidad").
- Crear funcionario en **Funcionarios** o desde escáner ("+ Nuevo Funcionario").
- Funcionario **siempre** vinculado a una unidad.

### 8.3 Editar / eliminar equipo

- **Equipos** → filtrar por unidad → seleccionar → Editar (doble clic) o Eliminar.
- Eliminar PC cascada accesorios y asignaciones.

### 8.4 Mantenimiento del PC

- Seleccionar opciones → confirmación (cookies/sesiones web) → ejecución en hilo → log + espacio liberado.

---

## 9. Integraciones con el sistema operativo

| API / Herramienta | Uso |
|-------------------|-----|
| WMI (`wmi.WMI`) | PC, BIOS, CPU, discos, OS, PnP, impresoras |
| PowerShell | Red, Office, monitores, impresoras, mantenimiento |
| Registry (via PS) | Office, efectos visuales |
| `os.startfile` | Abrir carpeta de datos |
| `subprocess` | PowerShell, ipconfig, powercfg |
| Win32 API (via PS Add-Type) | EnumDisplayDevices para monitores |

**Consideraciones de seguridad:**

- PowerShell con `-ExecutionPolicy Bypass`.
- Mantenimiento borra archivos del sistema y cookies (requiere confirmación usuario).
- Sin elevación explícita de administrador (algunas operaciones pueden fallar sin permisos).

---

## 10. Estadísticas y consultas

### `get_estadisticas_generales()`

Retorna:
- `total_pcs`, `total_monitores`, `total_webcams`, `total_impresoras`
- `ram_groups`: dict `{ "16 GB": N, ... }`
- `disco_groups`: dict clasificado NVMe/M.2, SSD, HDD, Otro

### `get_resumen_por_unidades()`

Por cada unidad: total PCs, funcionarios, monitores, webcams, impresoras (LEFT JOINs + GROUP BY).

---

## 11. Documentación y assets web

- **`docs/index.html`**: Landing estilo Matrix (GitHub Pages).
- **`docs/inventario.html`**: Página de descarga del portable.
- **`.cursorrules`**: Especificación arquitectónica para agentes Cursor (tema, stack, modelo DB). **Nota:** `.cursorrules` aún menciona `PARLANTE`; el código actual lo eliminó.

---

## 12. Puntos de extensión sugeridos (para otra IA)

| Área | Idea |
|------|------|
| Exportación | CSV/Excel/PDF desde stats o equipos |
| Multi-asignación | Varios funcionarios por PC (UI ya limitada a 1) |
| Sincronización | Servidor central opcional |
| Auditoría | Tabla `historial_cambios` |
| Búsqueda global | Filtro cross-unidad por serie/IP |
| SAP | Exponer campo `sap` en UI de unidades |
| Tests | Migrar a pytest, mocks WMI/PS |
| i18n | Strings externalizados |
| Linux | Abstraer capa scanner (actualmente Windows-only) |

---

## 13. API interna de `database.py` (referencia rápida)

### Unidades
`insert_unidad`, `upsert_unidad`, `get_unidades`, `get_unidad_by_id`, `update_unidad`, `delete_unidad`, `get_unidad_id_by_name`

### Funcionarios
`insert_funcionario`, `update_funcionario`, `delete_funcionario`, `get_funcionarios`, `get_funcionarios_by_unidad`, `get_funcionario_by_id`

### PCs
`insert_pc`, `update_pc`, `delete_pc`, `get_pcs_by_unidad`, `get_pc_by_id`

### Accesorios
`insert_accesorio`, `delete_accesorios_by_pc`, `get_accesorios_by_pc`

### Asignaciones
`set_pc_funcionarios`, `get_funcionarios_by_pc`

### Utilidades
`init_db`, `get_connection`, `backup_database`, `open_data_folder` (re-export desde paths)

---

## 14. Comandos de referencia

```bash
# Ejecutar aplicación
python main.py

# Validación
python test_validacion.py

# Instalar dependencias
pip install -r requirements.txt

# Compilar (PowerShell)
.\build_exe.ps1
.\build_portable.ps1
```

---

## 15. Glosario

| Término | Significado en este proyecto |
|---------|------------------------------|
| Unidad | División organizacional (departamento, área) con centro de costo |
| Funcionario | Persona asignada a una unidad; puede estar a cargo de un PC |
| PC / Equipo | Computadora inventariada |
| Accesorio | Monitor, webcam o impresora vinculada a un PC |
| Modo portable | Ejecución desde carpeta móvil sin instalación |
| Escaneo | Detección automática de hardware vía WMI/PowerShell |

---

## 16. Conclusión para handoff a otra IA

Matrix Inventario TI es una **app monolítica Python modular** con **GUI CustomTkinter**, **SQLite embebido** y **escaneo nativo Windows**. El punto de entrada es `main.py`; la lógica de negocio está repartida en `database.py`, `scanner.py` y `gui.py`. No hay configuración externa: rutas y DB son relativas al directorio de la aplicación. Para modificar:

- **Datos/esquema** → `database.py` (+ migraciones en `_migrate`).
- **Detección hardware** → `scanner.py`.
- **Pantallas/flujos** → `gui.py` + `ui_components.py`.
- **Operaciones OS batch** → `maintenance.py`.
- **Portabilidad/backups** → `paths.py`.

Respetar el tema visual Matrix (`#00FF66` sobre fondo negro) y mantener operaciones bloqueantes fuera del hilo principal de Tkinter.

---

*Documento generado a partir del análisis del repositorio [RUGDRAIGER/matrix_inventario](https://github.com/RUGDRAIGER/matrix_inventario.git).*
