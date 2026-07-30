import sqlite3

import paths
from paths import backup_database, open_data_folder, ensure_portable_dirs

DB_PATH = paths.DB_PATH


def _dict_row(cursor, row):
    return {col[0]: row[i] for i, col in enumerate(cursor.description)}


def get_connection():
    conn = sqlite3.connect(paths.DB_PATH)
    conn.row_factory = _dict_row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _migrate(conn):
    func_cols = {c["name"] for c in conn.execute("PRAGMA table_info(funcionarios)").fetchall()}
    if "unidad_id" not in func_cols:
        conn.execute(
            "ALTER TABLE funcionarios ADD COLUMN unidad_id INTEGER REFERENCES unidades(id)"
        )

    acc_cols = {c["name"] for c in conn.execute("PRAGMA table_info(accesorios)").fetchall()}
    if "etiqueta" not in acc_cols:
        conn.execute("ALTER TABLE accesorios ADD COLUMN etiqueta TEXT")

    conn.execute("DELETE FROM accesorios WHERE tipo = 'PARLANTE'")

    row = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='accesorios'"
    ).fetchone()
    if row and "PARLANTE" in (row["sql"] or ""):
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS accesorios_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pc_id INTEGER NOT NULL,
                tipo TEXT NOT NULL CHECK(tipo IN ('MONITOR', 'WEBCAM')),
                etiqueta TEXT,
                marca TEXT,
                modelo TEXT,
                serie TEXT,
                FOREIGN KEY (pc_id) REFERENCES pcs(id) ON DELETE CASCADE
            );
            INSERT INTO accesorios_new (id, pc_id, tipo, etiqueta, marca, modelo, serie)
                SELECT id, pc_id, tipo, etiqueta, marca, modelo, serie FROM accesorios
                WHERE tipo IN ('MONITOR', 'WEBCAM');
            DROP TABLE accesorios;
            ALTER TABLE accesorios_new RENAME TO accesorios;
        """)

    pc_cols = {c["name"] for c in conn.execute("PRAGMA table_info(pcs)").fetchall()}
    if "ubicacion" not in pc_cols:
        conn.execute("ALTER TABLE pcs ADD COLUMN ubicacion TEXT")
        conn.execute("""
            UPDATE pcs SET ubicacion = (
                SELECT ubicacion FROM unidades WHERE unidades.id = pcs.unidad_id
            ) WHERE COALESCE(ubicacion, '') = ''
        """)


def init_db():
    ensure_portable_dirs()
    with get_connection() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS unidades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre_unidad TEXT NOT NULL UNIQUE,
                centro_costo TEXT,
                sap TEXT,
                ubicacion TEXT
            );

            CREATE TABLE IF NOT EXISTS funcionarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                unidad_id INTEGER,
                grado TEXT,
                nombre TEXT NOT NULL,
                apellido TEXT NOT NULL,
                dotacion TEXT,
                cargo TEXT,
                FOREIGN KEY (unidad_id) REFERENCES unidades(id) ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS pcs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                unidad_id INTEGER NOT NULL,
                marca TEXT,
                modelo TEXT,
                serie TEXT,
                windows_version TEXT,
                procesador TEXT,
                ram_gb REAL,
                disco_detalle TEXT,
                office_version TEXT,
                ip_address TEXT,
                mac_address TEXT,
                ubicacion TEXT,
                FOREIGN KEY (unidad_id) REFERENCES unidades(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS accesorios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pc_id INTEGER NOT NULL,
                tipo TEXT NOT NULL CHECK(tipo IN ('MONITOR', 'WEBCAM')),
                etiqueta TEXT,
                marca TEXT,
                modelo TEXT,
                serie TEXT,
                FOREIGN KEY (pc_id) REFERENCES pcs(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS pc_funcionario (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pc_id INTEGER NOT NULL,
                funcionario_id INTEGER NOT NULL,
                FOREIGN KEY (pc_id) REFERENCES pcs(id) ON DELETE CASCADE,
                FOREIGN KEY (funcionario_id) REFERENCES funcionarios(id) ON DELETE CASCADE,
                UNIQUE(pc_id, funcionario_id)
            );
        """)
        _migrate(conn)


# --- Unidades ---

def insert_unidad(nombre, centro_costo, ubicacion, sap=""):
    with get_connection() as conn:
        cur = conn.execute(
            """INSERT INTO unidades (nombre_unidad, centro_costo, sap, ubicacion)
               VALUES (?, ?, ?, ?)""",
            (nombre, centro_costo, sap, ubicacion),
        )
        return cur.lastrowid


def upsert_unidad(nombre, centro_costo, sap, ubicacion):
    with get_connection() as conn:
        cur = conn.execute(
            "SELECT id FROM unidades WHERE nombre_unidad = ?", (nombre,)
        )
        row = cur.fetchone()
        if row:
            conn.execute(
                """UPDATE unidades SET centro_costo=?, sap=?, ubicacion=?
                   WHERE id=?""",
                (centro_costo, sap, ubicacion, row["id"]),
            )
            return row["id"]
        cur = conn.execute(
            """INSERT INTO unidades (nombre_unidad, centro_costo, sap, ubicacion)
               VALUES (?, ?, ?, ?)""",
            (nombre, centro_costo, sap, ubicacion),
        )
        return cur.lastrowid


def get_unidades():
    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM unidades ORDER BY nombre_unidad"
        ).fetchall()


def get_unidad_by_id(unidad_id):
    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM unidades WHERE id = ?", (unidad_id,)
        ).fetchone()


def update_unidad(unidad_id, nombre, centro_costo, ubicacion, sap=""):
    with get_connection() as conn:
        conn.execute(
            """UPDATE unidades SET nombre_unidad=?, centro_costo=?, sap=?, ubicacion=?
               WHERE id=?""",
            (nombre, centro_costo, sap, ubicacion, unidad_id),
        )


def delete_unidad(unidad_id):
    with get_connection() as conn:
        conn.execute("DELETE FROM unidades WHERE id = ?", (unidad_id,))


def get_unidad_id_by_name(nombre):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id FROM unidades WHERE nombre_unidad = ?", (nombre,)
        ).fetchone()
        return row["id"] if row else None


# --- Funcionarios ---

def insert_funcionario(grado, nombre, apellido, dotacion, cargo, unidad_id=None):
    with get_connection() as conn:
        cur = conn.execute(
            """INSERT INTO funcionarios (unidad_id, grado, nombre, apellido, dotacion, cargo)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (unidad_id, grado, nombre, apellido, dotacion, cargo),
        )
        return cur.lastrowid


def update_funcionario(fid, grado, nombre, apellido, dotacion, cargo, unidad_id=None):
    with get_connection() as conn:
        conn.execute(
            """UPDATE funcionarios SET unidad_id=?, grado=?, nombre=?, apellido=?,
               dotacion=?, cargo=? WHERE id=?""",
            (unidad_id, grado, nombre, apellido, dotacion, cargo, fid),
        )


def delete_funcionario(fid):
    with get_connection() as conn:
        conn.execute("DELETE FROM funcionarios WHERE id = ?", (fid,))


def get_funcionarios():
    with get_connection() as conn:
        return conn.execute("""
            SELECT f.*, u.nombre_unidad
            FROM funcionarios f
            LEFT JOIN unidades u ON u.id = f.unidad_id
            ORDER BY f.apellido, f.nombre
        """).fetchall()


def get_funcionarios_by_unidad(unidad_id):
    with get_connection() as conn:
        return conn.execute("""
            SELECT f.*, u.nombre_unidad
            FROM funcionarios f
            LEFT JOIN unidades u ON u.id = f.unidad_id
            WHERE f.unidad_id = ?
            ORDER BY f.apellido, f.nombre
        """, (unidad_id,)).fetchall()


def get_funcionario_by_id(fid):
    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM funcionarios WHERE id = ?", (fid,)
        ).fetchone()


# --- PCs ---

def insert_pc(unidad_id, data):
    with get_connection() as conn:
        cur = conn.execute(
            """INSERT INTO pcs (unidad_id, marca, modelo, serie, windows_version,
               procesador, ram_gb, disco_detalle, office_version, ip_address, mac_address, ubicacion)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                unidad_id,
                data.get("marca", ""),
                data.get("modelo", ""),
                data.get("serie", ""),
                data.get("windows_version", ""),
                data.get("procesador", ""),
                data.get("ram_gb"),
                data.get("disco_detalle", ""),
                data.get("office_version", ""),
                data.get("ip_address", ""),
                data.get("mac_address", ""),
                data.get("ubicacion", ""),
            ),
        )
        return cur.lastrowid


def update_pc(pc_id, unidad_id, data):
    with get_connection() as conn:
        conn.execute(
            """UPDATE pcs SET unidad_id=?, marca=?, modelo=?, serie=?, windows_version=?,
               procesador=?, ram_gb=?, disco_detalle=?, office_version=?, ip_address=?,
               mac_address=?, ubicacion=?
               WHERE id=?""",
            (
                unidad_id,
                data.get("marca", ""),
                data.get("modelo", ""),
                data.get("serie", ""),
                data.get("windows_version", ""),
                data.get("procesador", ""),
                data.get("ram_gb"),
                data.get("disco_detalle", ""),
                data.get("office_version", ""),
                data.get("ip_address", ""),
                data.get("mac_address", ""),
                data.get("ubicacion", ""),
                pc_id,
            ),
        )


def delete_pc(pc_id):
    with get_connection() as conn:
        conn.execute("DELETE FROM pcs WHERE id = ?", (pc_id,))


def get_pcs_by_unidad(unidad_id):
    with get_connection() as conn:
        return conn.execute(
            """SELECT p.*, u.nombre_unidad
               FROM pcs p
               JOIN unidades u ON u.id = p.unidad_id
               WHERE p.unidad_id = ?
               ORDER BY p.marca, p.modelo""",
            (unidad_id,),
        ).fetchall()


def get_pc_by_id(pc_id):
    with get_connection() as conn:
        return conn.execute("SELECT * FROM pcs WHERE id = ?", (pc_id,)).fetchone()


# --- Accesorios ---

def insert_accesorio(pc_id, tipo, marca, modelo, serie, etiqueta=""):
    with get_connection() as conn:
        cur = conn.execute(
            """INSERT INTO accesorios (pc_id, tipo, etiqueta, marca, modelo, serie)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (pc_id, tipo, etiqueta, marca, modelo, serie),
        )
        return cur.lastrowid


def delete_accesorios_by_pc(pc_id):
    with get_connection() as conn:
        conn.execute("DELETE FROM accesorios WHERE pc_id = ?", (pc_id,))


def get_accesorios_by_pc(pc_id):
    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM accesorios WHERE pc_id = ? ORDER BY tipo, etiqueta",
            (pc_id,),
        ).fetchall()


# --- Asignaciones ---

def set_pc_funcionarios(pc_id, funcionario_ids):
    with get_connection() as conn:
        conn.execute("DELETE FROM pc_funcionario WHERE pc_id = ?", (pc_id,))
        for fid in funcionario_ids:
            if fid:
                conn.execute(
                    "INSERT INTO pc_funcionario (pc_id, funcionario_id) VALUES (?, ?)",
                    (pc_id, fid),
                )


def get_funcionarios_by_pc(pc_id):
    with get_connection() as conn:
        return conn.execute(
            """SELECT f.* FROM funcionarios f
               JOIN pc_funcionario pf ON f.id = pf.funcionario_id
               WHERE pf.pc_id = ?""",
            (pc_id,),
        ).fetchall()


# --- Estadísticas ---

def get_estadisticas_generales():
    with get_connection() as conn:
        total_pcs = conn.execute("SELECT COUNT(*) AS c FROM pcs").fetchone()["c"]
        total_monitores = conn.execute(
            "SELECT COUNT(*) AS c FROM accesorios WHERE tipo='MONITOR'"
        ).fetchone()["c"]
        total_webcams = conn.execute(
            "SELECT COUNT(*) AS c FROM accesorios WHERE tipo='WEBCAM'"
        ).fetchone()["c"]

        pcs = conn.execute("SELECT ram_gb, disco_detalle FROM pcs").fetchall()
        ram_groups, disco_groups = {}, {}
        for pc in pcs:
            ram = pc["ram_gb"]
            ram_key = f"{int(ram)} GB" if ram else "Sin dato"
            ram_groups[ram_key] = ram_groups.get(ram_key, 0) + 1
            disco = (pc["disco_detalle"] or "").upper()
            if "NVME" in disco or "M.2" in disco or "M2" in disco:
                dtype = "NVMe/M.2"
            elif "SSD" in disco:
                dtype = "SSD"
            elif "HDD" in disco:
                dtype = "HDD"
            else:
                dtype = "Otro/Sin dato"
            disco_groups[dtype] = disco_groups.get(dtype, 0) + 1

        return {
            "total_pcs": total_pcs,
            "total_monitores": total_monitores,
            "total_webcams": total_webcams,
            "ram_groups": ram_groups,
            "disco_groups": disco_groups,
        }


def get_resumen_por_unidades():
    with get_connection() as conn:
        return conn.execute("""
            SELECT u.id, u.nombre_unidad,
                   COUNT(DISTINCT p.id) AS total_pcs,
                   COUNT(DISTINCT f.id) AS total_funcionarios,
                   SUM(CASE WHEN a.tipo='MONITOR' THEN 1 ELSE 0 END) AS monitores,
                   SUM(CASE WHEN a.tipo='WEBCAM' THEN 1 ELSE 0 END) AS webcams
            FROM unidades u
            LEFT JOIN pcs p ON p.unidad_id = u.id
            LEFT JOIN funcionarios f ON f.unidad_id = u.id
            LEFT JOIN accesorios a ON a.pc_id = p.id
            GROUP BY u.id
            ORDER BY u.nombre_unidad
        """).fetchall()
