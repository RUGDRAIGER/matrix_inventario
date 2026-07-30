# Matrix Inventario TI

Aplicación de escritorio local y portable para Windows 11 — control de inventario de TI y escaneo de hardware.

## Requisitos

- Windows 10/11
- Python 3.11+

## Instalación

```bash
pip install -r requirements.txt
```

## Ejecución portable (pendrive / disco externo)

1. Copie **toda la carpeta** del proyecto al pendrive.
2. En cualquier PC con Python 3.11+, haga doble clic en **`Iniciar.bat`**.
3. La base de datos `inventario.db` y las copias de seguridad (`/backups`) quedan en la misma carpeta — listas para mover entre equipos.

## Ejecución manual

```bash
python main.py
```

## Configuración

Menú **Configuración**:
- **Copia de Seguridad** — respaldo de `inventario.db` en `/backups`
- **Abrir Carpeta de Datos** — abre la carpeta donde está la base de datos

## Validación

```bash
python test_validacion.py
```

## Estructura

| Archivo | Descripción |
|---------|-------------|
| `main.py` | Punto de entrada |
| `database.py` | SQLite relacional con migraciones |
| `scanner.py` | Escaneo WMI/PowerShell con progreso |
| `ui_components.py` | Tema Matrix y componentes reutilizables |
| `paths.py` | Rutas portables y utilidades de respaldo |
| `gui.py` | Páginas y lógica de interfaz |

## Base de datos

Tablas: `unidades`, `funcionarios` (vinculados a unidad), `pcs`, `accesorios` (con etiqueta Monitor 1/2…), `pc_funcionario`.
