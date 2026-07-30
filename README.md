# Matrix Inventario TI

Aplicación de escritorio local y portable para Windows 11 — control de inventario de TI y escaneo de hardware.

## Requisitos

- Windows 10/11
- Python 3.11+

## Instalación

```bash
pip install -r requirements.txt
```

## Ejecución

```bash
python main.py
```

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
| `gui.py` | Páginas y lógica de interfaz |

## Base de datos

Tablas: `unidades`, `funcionarios` (vinculados a unidad), `pcs`, `accesorios` (con etiqueta Monitor 1/2…), `pc_funcionario`.
