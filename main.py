"""Inventario TI — Aplicación local portable para Windows 11."""

import database as db
from gui import InventarioApp


def main():
    db.init_db()
    app = InventarioApp()
    app.mainloop()


if __name__ == "__main__":
    main()
