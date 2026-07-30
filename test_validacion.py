"""Validaciones basicas de base de datos y escaner."""
import os
import tempfile
from pathlib import Path

import database as db
import paths


def run_tests():
    tmp = Path(tempfile.mkdtemp())
    original = paths.DB_PATH
    paths.DB_PATH = tmp / "test_inventario.db"
    db.DB_PATH = paths.DB_PATH
    errors = []

    try:
        db.init_db()

        uid = db.insert_unidad("Unidad Test", "CC-001", "Edificio A")
        if not uid:
            errors.append("insert_unidad fallo")

        fid = db.insert_funcionario("Cap", "Juan", "Perez", "123", "Analista", unidad_id=uid)
        funcs = db.get_funcionarios_by_unidad(uid)
        if len(funcs) != 1 or funcs[0]["unidad_id"] != uid:
            errors.append("relacion funcionario-unidad incorrecta")

        pc_id = db.insert_pc(uid, {
            "marca": "Dell", "modelo": "OptiPlex", "serie": "ABC123",
            "windows_version": "Win11", "procesador": "i7", "ram_gb": 16,
            "disco_detalle": "SSD 512GB", "office_version": "365",
            "ip_address": "192.168.1.10", "mac_address": "aa:bb:cc:dd:ee:ff",
            "ubicacion": "Oficina 101",
        })
        db.insert_accesorio(pc_id, "MONITOR", "LG", "24MP", "SN1", etiqueta="Monitor 1")
        db.insert_accesorio(pc_id, "MONITOR", "Samsung", "27", "SN2", etiqueta="Monitor 2")
        db.insert_accesorio(
            pc_id, "IMPRESORA", "HP", "LaserJet Pro", "",
            etiqueta="Impresora 1", ip_address="192.168.1.50", conexion="RED",
        )
        db.set_pc_funcionarios(pc_id, [fid])

        accs = db.get_accesorios_by_pc(pc_id)
        if len(accs) != 3:
            errors.append(f"esperados 3 accesorios, got {len(accs)}")
        imp = [a for a in accs if a["tipo"] == "IMPRESORA"]
        if not imp or imp[0]["ip_address"] != "192.168.1.50":
            errors.append("impresora no guardada correctamente")

        pcs = db.get_pcs_by_unidad(uid)
        if not pcs or pcs[0].get("ubicacion") != "Oficina 101":
            errors.append("ubicacion no guardada en equipo")

        stats = db.get_estadisticas_generales()
        if stats["total_pcs"] != 1 or stats["total_monitores"] != 2:
            errors.append("estadisticas incorrectas")
        if stats.get("total_impresoras") != 1:
            errors.append("total_impresoras incorrecto")
        if "total_parlantes" in stats:
            errors.append("parlantes no debe existir en stats")

        db.update_unidad(uid, "Unidad Test 2", "CC-002", "Edificio B")
        u = db.get_unidad_by_id(uid)
        if u["nombre_unidad"] != "Unidad Test 2":
            errors.append("update_unidad fallo")

        db.delete_pc(pc_id)
        if db.get_accesorios_by_pc(pc_id):
            errors.append("cascade delete accesorios fallo")

        from scanner import (
            _normalize_accesorios, _scan_network, _label_group_impresoras,
            classify_printer_port, _build_printer_record,
        )
        labeled = _normalize_accesorios(
            [{"tipo": "MONITOR", "marca": "A", "modelo": "B", "serie": "C"},
             {"tipo": "MONITOR", "marca": "D", "modelo": "E", "serie": "F"}],
            [],
        )
        if labeled[0]["etiqueta"] != "Monitor 1" or labeled[1]["etiqueta"] != "Monitor 2":
            errors.append("etiquetas de monitores incorrectas")
        if any(a["tipo"] == "PARLANTE" for a in labeled):
            errors.append("no debe haber parlantes")

        printers = _label_group_impresoras([
            {"marca": "HP", "modelo": "M404", "conexion": "USB", "ip_address": "N/A"},
        ])
        if not printers or printers[0]["etiqueta"] != "Impresora 1":
            errors.append("etiqueta impresora incorrecta")
        if _label_group_impresoras([]):
            errors.append("impresoras vacias debe retornar lista vacia")

        if classify_printer_port("USB001") != ("USB", "N/A"):
            errors.append("puerto USB mal clasificado")
        if classify_printer_port("IP_192.168.1.50") != ("RED", "192.168.1.50"):
            errors.append("puerto RED mal clasificado")
        if classify_printer_port("PORTPROMPT:") is not None:
            errors.append("puerto virtual no debe clasificarse")
        if classify_printer_port("nul:") is not None:
            errors.append("puerto nul no debe clasificarse")

        usb_pr = _build_printer_record("HP LaserJet", "USB002", "HP LaserJet Pro", "USB", "N/A")
        if not usb_pr or usb_pr["conexion"] != "USB":
            errors.append("registro USB fallo")
        red_pr = _build_printer_record("Canon MF", "IP_10.0.0.5", "Canon Generic", "RED", "10.0.0.5")
        if not red_pr or red_pr["conexion"] != "RED" or red_pr["ip_address"] != "10.0.0.5":
            errors.append("registro RED fallo")
        if _build_printer_record("PDF Printer", "PORTPROMPT:", "Microsoft", "RED", "N/A"):
            errors.append("impresora virtual no debe registrarse")

        ip, mac = _scan_network()
        if ip == "N/A":
            errors.append("IP no detectada")

        from gui import InventarioApp, MantenimientoPage
        from maintenance import format_bytes as fmt_b
        if fmt_b(1024) != "1.0 KB":
            errors.append("format_bytes fallo")
        print("GUI import OK")

        paths.BACKUP_DIR = tmp / "backups"
        backup_path = db.backup_database()
        if not backup_path.exists():
            errors.append("backup_database fallo")

    except Exception as ex:
        errors.append(str(ex))
    finally:
        paths.DB_PATH = original
        db.DB_PATH = original

    if errors:
        print("FALLO:", errors)
        return False
    print("Todas las validaciones pasaron.")
    return True


if __name__ == "__main__":
    import sys
    sys.exit(0 if run_tests() else 1)
