"""Validaciones básicas de base de datos y escáner."""
import os
import tempfile
from pathlib import Path

import database as db


def run_tests():
    tmp = Path(tempfile.mkdtemp())
    original = db.DB_PATH
    db.DB_PATH = tmp / "test_inventario.db"
    errors = []

    try:
        db.init_db()

        uid = db.insert_unidad("Unidad Test", "CC-001", "Edificio A")
        if not uid:
            errors.append("insert_unidad falló")

        fid = db.insert_funcionario("Cap", "Juan", "Pérez", "123", "Analista", unidad_id=uid)
        funcs = db.get_funcionarios_by_unidad(uid)
        if len(funcs) != 1 or funcs[0]["unidad_id"] != uid:
            errors.append("relación funcionario-unidad incorrecta")

        pc_id = db.insert_pc(uid, {
            "marca": "Dell", "modelo": "OptiPlex", "serie": "ABC123",
            "windows_version": "Win11", "procesador": "i7", "ram_gb": 16,
            "disco_detalle": "SSD 512GB", "office_version": "365",
            "ip_address": "192.168.1.10", "mac_address": "aa:bb:cc:dd:ee:ff",
        })
        db.insert_accesorio(pc_id, "MONITOR", "LG", "24MP", "SN1", etiqueta="Monitor 1")
        db.insert_accesorio(pc_id, "MONITOR", "Samsung", "27", "SN2", etiqueta="Monitor 2")
        db.set_pc_funcionarios(pc_id, [fid])

        accs = db.get_accesorios_by_pc(pc_id)
        if len(accs) != 2:
            errors.append(f"esperados 2 monitores, got {len(accs)}")

        stats = db.get_estadisticas_generales()
        if stats["total_pcs"] != 1 or stats["total_monitores"] != 2:
            errors.append("estadísticas incorrectas")

        db.delete_pc(pc_id)
        if db.get_accesorios_by_pc(pc_id):
            errors.append("cascade delete accesorios falló")

        from scanner import scan_hardware, _normalize_accesorios
        labeled = _normalize_accesorios(
            [{"tipo": "MONITOR", "marca": "A", "modelo": "B", "serie": "C"},
             {"tipo": "MONITOR", "marca": "D", "modelo": "E", "serie": "F"}],
            [], [],
        )
        if labeled[0]["etiqueta"] != "Monitor 1" or labeled[1]["etiqueta"] != "Monitor 2":
            errors.append("etiquetas de monitores incorrectas")

        from gui import InventarioApp
        print("GUI import OK")

    except Exception as ex:
        errors.append(str(ex))
    finally:
        db.DB_PATH = original
        if db.DB_PATH.exists():
            os.remove(db.DB_PATH)

    if errors:
        print("FALLÓ:", errors)
        return False
    print("Todas las validaciones pasaron.")
    return True


if __name__ == "__main__":
    import sys
    sys.exit(0 if run_tests() else 1)
